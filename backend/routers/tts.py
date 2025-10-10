"""
TTS (Text-to-Speech) control and simulation router
"""
import json
from typing import Dict, Any

from fastapi import APIRouter, Form, HTTPException

from .dependencies import logger, get_settings

router = APIRouter()

@router.post("/api/simulate")
async def api_simulate(
    user: str = Form(...), 
    text: str = Form(...), 
    eventType: str = Form("chat"),
    testVoice: str = Form(None)
):
    """Simulate a chat message"""
    logger.info(f"Simulate request: user={user}, text={text}, eventType={eventType}, testVoice={testVoice}")
    
    # Import functions when needed to avoid circular imports
    from app import handle_event, handle_test_voice_event, should_process_message
    
    # Apply message filtering for simulation as well
    settings = get_settings()
    should_process, filtered_text = should_process_message(text, settings, user)
    
    if not should_process:
        logger.info(f"Simulation message filtered out: {text} (user: {user})")
        return {"ok": False, "message": "Message was filtered out", "reason": "Message filtering"}
          
    # Use filtered text
    final_text = filtered_text
    
    # If testVoice is provided, parse it and use it directly
    if testVoice:
        try:
            test_voice_data = json.loads(testVoice)
            await handle_test_voice_event({
                "user": user, 
                "text": final_text, 
                "eventType": eventType,
                "testVoice": test_voice_data
            })
        except json.JSONDecodeError:
            logger.info("Invalid testVoice JSON data")
            return {"ok": False, "error": "Invalid testVoice data"}
    else:
        await handle_event({"user": user, "text": final_text, "eventType": eventType})
    
    result = {"ok": True}
    if final_text != text:
        result["filtered"] = True
        result["original_text"] = text
        result["filtered_text"] = final_text
    
    return result

@router.post("/api/simulate/moderation")
async def api_simulate_moderation(
    target_user: str = Form(...),
    eventType: str = Form("timeout"),  # "ban" or "timeout"
    duration: int = Form(None)  # seconds for timeout, None for ban
):
    """Simulate a moderation event (ban/timeout) with immediate audio stop"""
    logger.info(f"Simulate moderation: target_user={target_user}, eventType={eventType}, duration={duration}")
    
    try:
        # Import function when needed to avoid circular imports
        from app import handle_moderation_event
        
        await handle_moderation_event({
            "type": "moderation",
            "eventType": eventType,
            "target_user": target_user,
            "duration": duration
        })
        
        return {"ok": True, "message": f"Moderation event simulated for {target_user}"}
    except Exception as e:
        logger.error(f"Moderation simulation failed: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}

@router.post("/api/tts/cancel")
async def api_cancel_user_tts(cancel_data: dict):
    """Cancel TTS for a specific user (for testing or moderation)"""
    try:
        username = cancel_data.get("username", "")
        if not username:
            return {"success": False, "error": "Username is required"}
        
        # Import function when needed to avoid circular imports
        from app import cancel_user_tts
        
        cancel_user_tts(username)
        logger.info(f"TTS cancelled for user via API: {username}")
        return {"success": True, "message": f"TTS cancelled for user: {username}"}
    except Exception as e:
        logger.error(f"TTS cancellation failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@router.get("/api/tts/active")
async def api_get_active_tts():
    """Get list of currently active TTS jobs"""
    try:
        # Import global variables when needed
        from app import active_tts_jobs, tts_enabled
        
        active_jobs = {}
        for username, job_info in active_tts_jobs.items():
            active_jobs[username] = {
                "job_id": job_info["job_id"],
                "message": job_info["message"][:100] + "..." if len(job_info["message"]) > 100 else job_info["message"],
                "is_running": not job_info["task"].done() if job_info["task"] else False
            }
        
        return {
            "success": True,
            "active_jobs": active_jobs,
            "total_active": len(active_jobs),
            "tts_enabled": tts_enabled
        }
    except Exception as e:
        logger.error(f"Failed to get active TTS jobs: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@router.post("/api/tts/stop-all")
async def api_stop_all_tts():
    """Stop all TTS activity"""
    try:
        # Import function when needed to avoid circular imports
        from app import stop_all_tts, tts_enabled
        
        stop_all_tts()
        return {"success": True, "message": "All TTS stopped", "tts_enabled": tts_enabled}
    except Exception as e:
        logger.error(f"Failed to stop all TTS: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@router.post("/api/tts/resume-all")
async def api_resume_all_tts():
    """Resume TTS processing"""
    try:
        # Import function when needed to avoid circular imports
        from app import resume_all_tts, tts_enabled
        
        resume_all_tts()
        return {"success": True, "message": "TTS processing resumed", "tts_enabled": tts_enabled}
    except Exception as e:
        logger.error(f"Failed to resume TTS: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@router.post("/api/tts/toggle")
async def api_toggle_tts():
    """Toggle TTS on/off"""
    try:
        # Import function when needed to avoid circular imports
        from app import toggle_tts, tts_enabled
        
        new_state = toggle_tts()
        message = "TTS enabled" if new_state else "TTS disabled"
        return {"success": True, "message": message, "tts_enabled": tts_enabled}
    except Exception as e:
        logger.error(f"Failed to toggle TTS: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@router.get("/api/tts/status")
async def api_get_tts_status():
    """Get current TTS status"""
    try:
        # Import global variables when needed
        from app import active_tts_jobs, tts_enabled
        
        return {
            "success": True,
            "tts_enabled": tts_enabled,
            "active_jobs_count": len(active_tts_jobs)
        }
    except Exception as e:
        logger.error(f"Failed to get TTS status: {e}", exc_info=True)
        return {"success": False, "error": str(e)}