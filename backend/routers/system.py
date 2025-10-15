"""
System, settings, stats, and debug router
"""
import json
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from modules import logger
from modules.persistent_data import get_settings, Debug_Database, DB_PATH

router = APIRouter()

@router.get("/api/settings")
async def api_get_settings():
    logger.info("API: GET /api/settings called")
    settings = get_settings()
    logger.info(f"API: Returning settings: {len(json.dumps(settings))} characters")
    return settings

@router.post("/api/settings")
async def api_set_settings(payload: Dict[str, Any]):
    logger.info("API: POST /api/settings called")
    
    # Log volume changes specifically for debugging
    if 'volume' in payload:
        logger.info(f"🔊 Volume setting changed to: {payload['volume']} ({round(payload['volume'] * 100)}%)")
    
    # Use app_save_settings which handles TTS state and Twitch bot restart
    from app import app_save_settings
    app_save_settings(payload)
    logger.info("Settings saved successfully")
    
    return {"ok": True}

@router.get("/api/status")
async def api_get_status():
    """Simple status check endpoint"""
    logger.info("API: GET /api/status called")
    
    # Import hub when needed to avoid circular imports
    from app import hub
    
    status = {
        "status": "running",
        "websocket_clients": len(hub.clients),
        "message": "Chat Yapper backend is running!"
    }
    logger.info(f"API: Returning status: {status}")
    return status

@router.get("/api/test")
async def api_test():
    """Simple test endpoint for debugging"""
    logger.info("API: GET /api/test called - React app is working!")
    return {"success": True, "message": "API connection successful"}

@router.get("/api/voice-stats")
async def api_voice_stats():
    """Get voice usage distribution statistics"""
    try:
        # Import global stats when needed
        from app import voice_usage_stats, voice_selection_count
        from modules.tts import fallback_voice_stats, fallback_selection_count
        
        # Calculate percentages for main voice selections
        main_stats = {}
        if voice_selection_count > 0:
            total_main = sum(voice_usage_stats.values())
            for voice_name, count in voice_usage_stats.items():
                main_stats[voice_name] = {
                    "count": count,
                    "percentage": (count / total_main) * 100 if total_main > 0 else 0
                }
        
        # Calculate percentages for fallback selections
        fallback_stats = {}
        if fallback_selection_count > 0:
            total_fallback = sum(fallback_voice_stats.values())
            for voice_name, count in fallback_voice_stats.items():
                fallback_stats[voice_name] = {
                    "count": count,
                    "percentage": (count / total_fallback) * 100 if total_fallback > 0 else 0
                }
        
        return {
            "main_selections": {
                "total_count": voice_selection_count,
                "distribution": main_stats
            },
            "fallback_selections": {
                "total_count": fallback_selection_count,
                "distribution": fallback_stats
            }
        }
    except Exception as e:
        logger.error(f"Failed to get voice stats: {e}", exc_info=True)
        return {"error": str(e)}

@router.delete("/api/voice-stats")
async def api_reset_voice_stats():
    """Reset voice usage distribution statistics"""
    try:
        # Import functions and variables when needed
        from app import voice_usage_stats, voice_selection_count
        from modules.tts import reset_fallback_stats
        
        # Reset global stats - need to import and modify the actual global variables
        import app
        app.voice_usage_stats.clear()
        app.voice_selection_count = 0
        
        # Reset fallback stats
        reset_fallback_stats()
        
        logger.info("Voice distribution statistics have been reset")
        return {"ok": True, "message": "Voice statistics reset successfully"}
    except Exception as e:
        logger.error(f"Failed to reset voice stats: {e}", exc_info=True)
        return {"error": str(e)}

@router.get("/api/debug/per-user-queuing")
async def api_debug_per_user_queuing():
    """Debug endpoint to check per-user queuing setting"""
    try:
        # Import global variables when needed
        from app import active_tts_jobs
        
        settings = get_settings()
        filtering = settings.get("messageFiltering", {})
        ignore_if_user_speaking = filtering.get("ignoreIfUserSpeaking", True)
        
        return {
            "ignoreIfUserSpeaking": ignore_if_user_speaking,
            "messageFiltering": filtering,
            "activeJobsByUser": list(active_tts_jobs.keys()),
            "totalActiveJobs": len(active_tts_jobs)
        }
    except Exception as e:
        return {"error": str(e)}

@router.post("/api/message-filter/test")
async def api_test_message_filter(test_data: dict):
    """Test message filtering with a sample message"""
    try:
        # Import function when needed to avoid circular imports
        from app import should_process_message
        
        settings = get_settings()
        test_message = test_data.get("message", "")
        test_username = test_data.get("username", "")
        # Note: Test endpoint doesn't have real Twitch tags, so emote filtering won't work in tests
        # Real messages from Twitch will have proper tags with emote information
        
        should_process, filtered_text = should_process_message(test_message, settings, test_username, None, None)
        
        return {
            "success": True,
            "original_message": test_message,
            "test_username": test_username,
            "filtered_message": filtered_text,
            "should_process": should_process,
            "was_modified": filtered_text != test_message,
            "filtering_settings": settings.get("messageFiltering", {}),
            "note": "Emote filtering uses Twitch tags which are not available in test mode"
        }
    except Exception as e:
        logger.error(f"Message filter test failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@router.get("/api/debug/database")
async def api_debug_database():
    """Get database information for debugging"""
    try:
        from modules.db_migration import get_database_info
        db_info = get_database_info(DB_PATH)
        
        # Also get some basic stats
        Debug_Database()
        
        return {"success": True, "database": db_info}
    except Exception as e:
        logger.error(f"Failed to get database info: {e}", exc_info=True)
        return {"success": False, "error": str(e), "database_path": DB_PATH}