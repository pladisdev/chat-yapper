"""
System, settings, stats, and debug router
"""
import json
import os
import platform
from pathlib import Path
from typing import Dict, Any, List

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
        logger.info(f"Volume setting changed to: {payload['volume']} ({round(payload['volume'] * 100)}%)")
    
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

def get_system_fonts() -> List[Dict[str, str]]:
    """
    Detect installed system fonts on Windows and Linux.
    Returns a list of dicts with 'name' and 'family' keys.
    """
    fonts = []
    system = platform.system()
    
    try:
        if system == "Windows":
            # Windows fonts are typically in C:\Windows\Fonts
            font_dir = Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'Fonts'
            if font_dir.exists():
                # Common font extensions
                extensions = {'.ttf', '.otf', '.ttc'}
                seen_families = set()
                
                for font_file in font_dir.iterdir():
                    if font_file.suffix.lower() in extensions:
                        # Extract font family name from filename
                        name = font_file.stem
                        # Clean up common suffixes
                        for suffix in [' Bold', ' Italic', ' Regular', ' Light', ' Medium', 
                                      'BD', 'BI', 'I', 'Z', 'L', 'M']:
                            if name.endswith(suffix):
                                name = name[:-len(suffix)].strip()
                        
                        # Remove common variations
                        name = name.replace('MT', '').strip()
                        
                        if name and name not in seen_families:
                            seen_families.add(name)
                            # Create CSS-friendly font family string
                            family = f'"{name}", sans-serif' if ' ' in name else f'{name}, sans-serif'
                            fonts.append({'name': name, 'family': family})
        
        elif system == "Linux":
            # Linux fonts are typically in these directories
            font_dirs = [
                Path('/usr/share/fonts'),
                Path('/usr/local/share/fonts'),
                Path.home() / '.fonts',
                Path.home() / '.local/share/fonts'
            ]
            
            extensions = {'.ttf', '.otf', '.ttc'}
            seen_families = set()
            
            for base_dir in font_dirs:
                if base_dir.exists():
                    # Recursively search for font files
                    for font_file in base_dir.rglob('*'):
                        if font_file.suffix.lower() in extensions:
                            name = font_file.stem
                            # Clean up common suffixes
                            for suffix in ['-Bold', '-Italic', '-Regular', '-Light', '-Medium',
                                          'Bold', 'Italic', 'Regular', 'Light', 'Medium']:
                                if name.endswith(suffix):
                                    name = name[:-len(suffix)].strip('-')
                            
                            if name and name not in seen_families:
                                seen_families.add(name)
                                family = f'"{name}", sans-serif' if ' ' in name else f'{name}, sans-serif'
                                fonts.append({'name': name, 'family': family})
        
        # Sort alphabetically
        fonts.sort(key=lambda x: x['name'].lower())
        
        # Add common web-safe fonts that might not be detected
        web_safe = [
            {'name': 'Arial', 'family': 'Arial, sans-serif'},
            {'name': 'Helvetica', 'family': 'Helvetica, sans-serif'},
            {'name': 'Times New Roman', 'family': '"Times New Roman", Times, serif'},
            {'name': 'Courier New', 'family': '"Courier New", Courier, monospace'},
            {'name': 'Verdana', 'family': 'Verdana, sans-serif'},
            {'name': 'Georgia', 'family': 'Georgia, serif'},
        ]
        
        # Add web-safe fonts if not already in the list
        existing_names = {f['name'] for f in fonts}
        for ws_font in web_safe:
            if ws_font['name'] not in existing_names:
                fonts.insert(0, ws_font)
        
        logger.info(f"Detected {len(fonts)} system fonts on {system}")
        
    except Exception as e:
        logger.error(f"Error detecting system fonts: {e}")
        # Return basic web-safe fonts as fallback
        fonts = [
            {'name': 'Arial', 'family': 'Arial, sans-serif'},
            {'name': 'Helvetica', 'family': 'Helvetica, sans-serif'},
            {'name': 'Verdana', 'family': 'Verdana, sans-serif'},
            {'name': 'Georgia', 'family': 'Georgia, serif'},
            {'name': 'Times New Roman', 'family': '"Times New Roman", Times, serif'},
            {'name': 'Courier New', 'family': '"Courier New", Courier, monospace'},
        ]
    
    return fonts

@router.get("/api/system/fonts")
async def api_get_system_fonts():
    """Get list of installed system fonts"""
    logger.info("API: GET /api/system/fonts called")
    fonts = get_system_fonts()
    return {"fonts": fonts, "count": len(fonts)}

@router.get("/api/debug/tts-state")
async def api_debug_tts_state():
    """Debug endpoint to check TTS counter state"""
    from app import total_active_tts_count, active_tts_jobs
    from modules.avatars import get_active_avatar_slots
    
    active_slots = get_active_avatar_slots()
    
    state = {
        "total_active_tts_count": total_active_tts_count,
        "active_tts_jobs_count": len(active_tts_jobs),
        "active_tts_jobs_users": list(active_tts_jobs.keys()),
        "active_avatar_slots_count": len(active_slots),
        "active_avatar_slots": list(active_slots.keys()),
        "mismatch": total_active_tts_count != len(active_tts_jobs)
    }
    
    logger.info(f"DEBUG TTS State: {state}")
    print(f"DEBUG TTS State: {state}")
    return state

@router.post("/api/debug/reset-tts-counter")
async def api_debug_reset_tts_counter():
    """Debug endpoint to reset TTS counter to match active jobs"""
    from app import total_active_tts_count, active_tts_jobs, sync_tts_count
    
    old_count = total_active_tts_count
    sync_tts_count()
    new_count = total_active_tts_count
    
    result = {
        "old_count": old_count,
        "new_count": new_count,
        "active_jobs": len(active_tts_jobs),
        "reset": True
    }
    
    logger.info(f"DEBUG: Reset TTS counter from {old_count} to {new_count}")
    print(f"DEBUG: Reset TTS counter from {old_count} to {new_count}")
    return result

@router.post("/api/debug/force-reset-tts")
async def api_debug_force_reset_tts():
    """Debug endpoint to force reset TTS counter to 0 (emergency reset)"""
    from app import force_reset_tts_counter, total_active_tts_count, active_tts_jobs
    
    old_count = total_active_tts_count
    old_jobs = len(active_tts_jobs)
    
    force_reset_tts_counter()
    
    result = {
        "old_count": old_count,
        "old_jobs": old_jobs,
        "new_count": 0,
        "new_jobs": 0,
        "force_reset": True
    }
    
    return result

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
        from app import active_tts_jobs, total_active_tts_count
        
        settings = get_settings()
        filtering = settings.get("messageFiltering", {})
        ignore_if_user_speaking = filtering.get("ignoreIfUserSpeaking", True)
        
        return {
            "ignoreIfUserSpeaking": ignore_if_user_speaking,
            "messageFiltering": filtering,
            "activeJobsByUser": list(active_tts_jobs.keys()),
            "totalActiveJobs": total_active_tts_count
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

@router.get("/api/test/message-history")
async def api_get_message_history():
    """Get message history for testing and replay"""
    try:
        from app import message_history
        
        # Convert deque to list and format timestamps
        history_list = []
        for msg in message_history:
            history_list.append({
                "timestamp": msg["timestamp"],
                "username": msg["username"],
                "original_text": msg["original_text"],
                "filtered_text": msg["filtered_text"],
                "event_type": msg["event_type"],
                "was_filtered": msg["was_filtered"]
            })
        
        # Return in reverse order (newest first)
        return {"success": True, "messages": list(reversed(history_list))}
    except Exception as e:
        logger.error(f"Failed to get message history: {e}", exc_info=True)
        return {"success": False, "error": str(e), "messages": []}

@router.post("/api/test/replay-message")
async def api_replay_message(payload: Dict[str, Any]):
    """Replay a message through the TTS pipeline for testing"""
    try:
        from app import handle_event
        import asyncio
        
        # Extract message data
        username = payload.get("username", "TestUser")
        text = payload.get("text", "")
        event_type = payload.get("eventType", "chat")
        
        if not text:
            return {"success": False, "error": "No text provided"}
        
        # Create event object
        event = {
            "user": username,
            "text": text,
            "eventType": event_type,
            "tags": {}  # Empty tags for replay
        }
        
        # Process the message
        asyncio.create_task(handle_event(event))
        
        logger.info(f"Replaying message from {username}: {text[:50]}...")
        
        return {"success": True, "message": "Message sent for processing"}
    except Exception as e:
        logger.error(f"Failed to replay message: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@router.post("/api/test/clearchat")
async def api_test_clearchat(payload: Dict[str, Any]):
    """Simulate a Twitch CLEARCHAT event (ban/timeout) for testing"""
    try:
        from app import handle_moderation_event
        import asyncio
        
        # Extract parameters
        target_user = payload.get("target_user", "TestUser")
        event_type = payload.get("eventType", "ban")  # "ban" or "timeout"
        duration = payload.get("duration", 600)  # Default 600 seconds (10 minutes) for timeout
        
        if not target_user:
            return {"success": False, "error": "No target_user provided"}
        
        # Validate event type
        if event_type not in ["ban", "timeout"]:
            return {"success": False, "error": "eventType must be 'ban' or 'timeout'"}
        
        # Create moderation event object that matches CLEARCHAT structure
        event = {
            "type": "moderation",
            "eventType": event_type,
            "target_user": target_user,
            "duration": int(duration) if event_type == "timeout" else None,
            "tags": {
                "login": target_user,
                "target-user-id": target_user,
                "ban-duration": str(duration) if event_type == "timeout" else None
            }
        }
        
        # Process the moderation event directly (not as a chat message)
        asyncio.create_task(handle_moderation_event(event))
        
        logger.info(f"Test CLEARCHAT: {event_type} for {target_user}" + (f" ({duration}s)" if event_type == "timeout" else ""))
        
        return {
            "success": True, 
            "message": f"Simulated {event_type} for {target_user}",
            "event": event
        }
    except Exception as e:
        logger.error(f"Failed to simulate CLEARCHAT: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@router.post("/api/test-parallel-limit")
async def test_parallel_limit():
    """Test parallel message limiting by sending multiple messages rapidly"""
    try:
        import asyncio
        import time
        from app import handle_event
        
        # Get current settings to check limits
        settings = get_settings()
        parallel_limit = settings.get("parallelMessageLimit", 5)
        queue_overflow = settings.get("queueOverflowMessages", True)
        
        logger.info(f"Testing parallel limit: {parallel_limit} messages, queue overflow: {queue_overflow}")
        
        # Create test messages to exceed the parallel limit (if there is one)
        test_messages = []
        if parallel_limit and parallel_limit > 0:
            num_messages = parallel_limit + 3  # Send 3 more than the limit
        else:
            num_messages = 8  # Send 8 messages for unlimited test
        
        for i in range(num_messages):
            test_messages.append({
                "type": "chat",
                "user": f"TestUser{i + 1}",
                "text": f"This is test message number {i + 1} to test parallel limiting.",
                "eventType": "chat",
                "tags": {}
            })
        
        # Send all messages rapidly
        start_time = time.time()
        tasks = []
        for msg in test_messages:
            task = asyncio.create_task(handle_event(msg))
            tasks.append(task)
        
        # Wait for all tasks to complete (or be queued/ignored)
        await asyncio.gather(*tasks, return_exceptions=True)
        
        duration = time.time() - start_time
        
        # Import queue info
        from app import active_tts_jobs, parallel_message_queue, total_active_tts_count
        
        result = {
            "success": True,
            "message": f"Sent {num_messages} messages in {duration:.2f}s",
            "config": {
                "parallelLimit": parallel_limit,
                "queueOverflowMessages": queue_overflow
            },
            "results": {
                "messagesProcessed": total_active_tts_count,
                "messagesQueued": len(parallel_message_queue),
                "activeTtsJobs": list(active_tts_jobs.keys()),
                "queuedUsers": [item["message_data"]["user"] for item in parallel_message_queue]
            }
        }
        
        logger.info(f"Parallel limit test completed: {result['results']}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to test parallel limit: {e}", exc_info=True)
        return {"success": False, "error": str(e)}