from __future__ import annotations
import asyncio
import json
import os
import random
import time
from datetime import datetime
from typing import Dict, Any, List
from collections import defaultdict
import builtins

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()  # Load .env file from current directory or parent directories

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from modules.tts import get_hybrid_provider, TTSJob, get_audio_duration
from modules.message_filter import get_message_history, should_process_message
from modules.persistent_data import get_settings, save_settings, get_auth, get_enabled_voices, AUDIO_DIR, PUBLIC_DIR
from modules.avatars import (
    generate_avatar_slot_assignments,
    reserve_avatar_slot,
    find_available_slot_for_tts,
    release_avatar_slot,
    get_avatar_assignments_generation_id,
    get_avatar_slot_assignments,
    get_active_avatar_slots
)
from modules import queue_manager
from modules.queue_manager import (
    queue_avatar_message,
    queue_parallel_message,
    get_avatar_queue_length,
    get_parallel_queue_length
)

from modules import logger
# TTS Cancellation System:
# - Tracks active TTS jobs by username in active_tts_jobs dict
# - Detects Twitch ban/timeout events via CLEARCHAT IRC messages
# - Cancels ongoing TTS synthesis and removes from queue for banned/timed-out users
# - Provides API endpoints for manual testing and management

# Voice usage tracking for distribution analysis
voice_usage_stats = defaultdict(int)
voice_selection_count = 0
last_selected_voice_id = None  # Track last voice to prevent consecutive repeats

# TTS job tracking for cancellation support - supports parallel audio with per-user queuing
# Multiple users can have TTS playing simultaneously, only stopped by:
# 1. Global TTS stop button (stops all)
# 2. Individual user ban/timeout (stops only that user)
# 3. New TTS from same user is ignored if their previous TTS is still playing
# Track active TTS tasks for cancellation only (simplified - no timers)
# username -> {"task": asyncio.Task, "message": str}
active_tts_jobs = {}
total_active_tts_count = 0  # Total count of active TTS jobs (for parallel limiting)
parallel_message_queue = []  # Queue for messages when parallel limit is reached

def increment_tts_count():
    """Increment the TTS count for parallel limiting"""
    global total_active_tts_count
    total_active_tts_count += 1

def decrement_tts_count():
    """Safely decrement the TTS count, preventing negative values"""
    global total_active_tts_count
    if total_active_tts_count > 0:
        total_active_tts_count -= 1

# sync_tts_count function removed - using simple audio duration-based limiting

def force_reset_tts_counter():
    """Force reset TTS counter to 0 and clear active jobs (emergency reset)"""
    global total_active_tts_count
    old_count = total_active_tts_count
    old_jobs = len(active_tts_jobs)
    
    total_active_tts_count = 0
    active_tts_jobs.clear()
    
    print(f"FORCE RESET: TTS counter {old_count}→0, cleared {old_jobs} active jobs")
    logger.warning(f"FORCE RESET: TTS counter {old_count}→0, cleared {old_jobs} active jobs")

# Global TTS control
tts_enabled = True  # Global flag to control TTS processing

# Message History for Testing and Replay
# Stores last 100 processed messages with original and filtered text
from collections import deque
message_history = deque(maxlen=100)  # Automatically removes oldest when full

def add_to_message_history(username: str, original_text: str, filtered_text: str, 
                           event_type: str = "chat", tags: Dict[str, Any] = None):
    """Add a message to the history for replay testing"""
    message_history.append({
        "timestamp": time.time(),
        "username": username,
        "original_text": original_text,
        "filtered_text": filtered_text,
        "event_type": event_type,
        "was_filtered": original_text != filtered_text,
        "tags": tags or {}
    })

# Avatar Slot Management System
# Manages which avatars are assigned to which slots and tracks their active status

# Queue processing wrapper functions that inject dependencies
def process_parallel_message_queue():
    """Process queued messages if parallel slots become available"""
    queue_manager.process_parallel_message_queue(
        app_get_settings,
        process_tts_message,
        active_tts_jobs,
        total_active_tts_count,
        increment_tts_count,
        decrement_tts_count
    )

def process_avatar_message_queue():
    """Process queued messages if avatar slots become available"""
    queue_manager.process_avatar_message_queue(process_queued_tts_message)

async def process_queued_tts_message(message_data, target_slot):
    """Process a TTS message that was queued due to all slots being busy"""
    await queue_manager.process_queued_tts_message(
        message_data, 
        target_slot, 
        hub, 
        process_avatar_message_queue
    )
    
logger.info("Initializing FastAPI application")
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add middleware to log all requests for debugging
from fastapi import Request
import time

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    # Only log important requests, not headers
    logger.info(f"HTTP Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} (took {process_time:.2f}s)")
    
    return response

# Include routers
from routers.tts import router as tts_router
from routers.avatars import router as avatars_router
from routers.auth import router as auth_router
from routers.static import router as static_router
from routers.voices import router as voices_router
from routers.system import router as system_router
from routers.config_backup import router as config_backup_router
app.include_router(tts_router)
app.include_router(avatars_router)
app.include_router(auth_router)
app.include_router(static_router)
app.include_router(voices_router)
app.include_router(system_router)
app.include_router(config_backup_router)

# Serve generated audio files under /audio
# Use AUDIO_DIR from TTS module to ensure consistency
logger.info(f"=== MOUNTING AUDIO DIRECTORY ===")
logger.info(f"Audio directory: {AUDIO_DIR}")
logger.info(f"Audio directory exists: {os.path.isdir(AUDIO_DIR)}")
if os.path.isdir(AUDIO_DIR):
    try:
        files = os.listdir(AUDIO_DIR)
        logger.info(f"Files in audio directory: {len(files)} files")
    except Exception as e:
        logger.error(f"Error listing audio directory: {e}")
        
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")
logger.info(f"=== AUDIO MOUNT COMPLETE ===")


# Debug: List files in the public directory
if os.path.isdir(PUBLIC_DIR):
    logger.info("Files in static directory:")
    for root, dirs, files in os.walk(PUBLIC_DIR):
        level = root.replace(PUBLIC_DIR, '').count(os.sep)
        indent = ' ' * 2 * level
        logger.info(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            logger.info(f"{subindent}{file}")
else:
    logger.info("Static files directory not found")

# ---------- Global State ----------
twitch_auth_error = None
youtube_auth_error = None
# Track if we've attempted a token refresh in this session to prevent infinite retries
twitch_refresh_attempted = False
youtube_refresh_attempted = False

# ---------- WebSocket Hub ----------
class Hub:
    def __init__(self):
        self.clients: List[WebSocket] = []
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.append(ws)
    def unregister(self, ws: WebSocket):
        if ws in self.clients:
            self.clients.remove(ws)
    async def broadcast(self, payload: Dict[str, Any]):
        logger.debug(f"Hub.broadcast called with payload type: {payload.get('type')}")
        logger.debug(f"Broadcasting to {len(self.clients)} clients")
        dead = []
        sent_count = 0
        for ws in self.clients:
            try:
                await ws.send_text(json.dumps(payload))
                sent_count += 1
                logger.debug(f"Sent message to client {sent_count}/{len(self.clients)}")
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                dead.append(ws)
        for d in dead:
            self.unregister(d)
        logger.debug(f"Broadcast complete: {sent_count} succeeded, {len(dead)} failed")

# Use a singleton pattern to prevent hub from being recreated on module reload
# This is critical for .exe builds where imports can cause module reinitialization
# We store the hub in builtins which is truly global and survives module reloads
if not hasattr(builtins, '_chatyapper_hub_instance'):
    logger.info("Creating new Hub instance (first initialization)")
    hub = Hub()
    builtins._chatyapper_hub_instance = hub
else:
    hub = builtins._chatyapper_hub_instance
    logger.info(f"Hub already exists with {len(hub.clients)} clients (module reload detected)")

async def broadcast_avatar_slots():
    await hub.broadcast({
        "type": "avatar_slots_updated",
        "slots": get_avatar_slot_assignments(),
        "generationId": get_avatar_assignments_generation_id()
    })
    logger.info("Avatar slot assignments broadcasted to WebSocket clients")

# Initialize avatar slot assignments on startup
logger.info("Initializing avatar slot assignments...")
generate_avatar_slot_assignments()
# Note: Avatar slots will be broadcasted during the startup event

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    client_info = f"{ws.client.host}:{ws.client.port}" if ws.client else "unknown"
    logger.info(f"WebSocket connection attempt from {client_info}")
    try:
        await hub.connect(ws)
        logger.info(f"WebSocket connected successfully. Total clients: {len(hub.clients)}")
        
        # Reset refresh attempt tracking on new WebSocket connection (indicates page refresh)
        global twitch_refresh_attempted
        if twitch_refresh_attempted:
            logger.info("Resetting token refresh attempt tracking due to new WebSocket connection (page refresh)")
            twitch_refresh_attempted = False
            youtube_refresh_attempted = False
        
        # Send a welcome message to confirm connection
        welcome_msg = {
            "type": "connection",
            "message": "WebSocket connected successfully",
            "client_count": len(hub.clients)
        }
        await ws.send_text(json.dumps(welcome_msg))
        logger.info(f"Sent welcome message to WebSocket client {client_info}")
        
        # Send any pending auth error to the new client
        global twitch_auth_error, youtube_auth_error
        if twitch_auth_error:
            logger.info(f"Sending pending Twitch auth error to new client {client_info}")
            await ws.send_text(json.dumps(twitch_auth_error))
        if youtube_auth_error:
            logger.info(f"Sending pending YouTube auth error to new client {client_info}")
            await ws.send_text(json.dumps(youtube_auth_error))
        
        while True:
            # Handle messages from frontend (avatar slot status updates, etc.)
            message = await ws.receive_text()
            logger.debug(f"WebSocket received message from {client_info}: {message}")
            
            try:
                data = json.loads(message)
                await handle_websocket_message(data)
            except json.JSONDecodeError:
                # Handle plain text messages (like connection tests)
                if message.strip().lower() in ['hello', 'ping', 'test']:
                    logger.debug(f"Received connection test message: {message}")
                    # Optionally send a response
                    await ws.send_text(json.dumps({"type": "pong", "message": "ok"}))
                else:
                    logger.warning(f"Invalid JSON received from WebSocket: {message}")
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected from {client_info}. Remaining clients: {len(hub.clients)-1}")
        hub.unregister(ws)
    except Exception as e:
        logger.error(f"WebSocket error from {client_info}: {e}")
        hub.unregister(ws)

async def handle_websocket_message(data: Dict[str, Any]):
    """Handle incoming WebSocket messages from frontend"""
    message_type = data.get("type", "")
    
    if message_type == "avatar_slot_ended":
        # Frontend reports that an avatar slot has finished playing
        slot_id = data.get("slot_id")
        logger.info(f"Avatar slot ended: slot_id={slot_id}")
        if slot_id:
            # DISABLED: WebSocket decrement to avoid conflict with auto-decrement
            # The auto-decrement based on audio duration is more reliable
            
            release_avatar_slot(slot_id)
            process_avatar_message_queue()
            logger.info(f"Avatar slot {slot_id} released by frontend")
    
    elif message_type == "avatar_slot_error":
        # Frontend reports an error with avatar slot playback
        slot_id = data.get("slot_id")
        logger.info(f"Avatar slot error: slot_id={slot_id}")
        if slot_id:
            # DISABLED: WebSocket decrement to avoid conflict with auto-decrement
            
            release_avatar_slot(slot_id)
            process_avatar_message_queue()
            logger.info(f"Avatar slot {slot_id} released due to frontend error")
    
    elif message_type == "request_avatar_slots":
        # Frontend requests current avatar slot assignments (for page refresh)
        slots = get_avatar_slot_assignments()
        logger.info(f"Frontend requested avatar slots - sending {len(slots)} slots")
        response = {
            "type": "avatar_slots_updated",
            "slots": slots,
            "generationId": get_avatar_assignments_generation_id(),
            "activeSlots": list(get_active_avatar_slots().keys()),
            "queueLength": get_avatar_queue_length()
        }
        # Send only to the requesting client (would need to track client in real implementation)
        # For now, broadcast to all clients
        await hub.broadcast(response)
        logger.info(f"Sent avatar slots update to frontend: {len(slots)} slots (gen #{get_avatar_assignments_generation_id()})")
    
    elif message_type == "ping":
        # Simple ping/pong for connection health
        await hub.broadcast({"type": "pong"})
    
    else:
        logger.info(f"Unknown WebSocket message type: {message_type}")

# ---------- Settings with App-specific Logic ----------

def app_get_settings() -> Dict[str, Any]:
    """App-specific wrapper for get_settings with TTS state initialization"""
    settings = get_settings()
    
    # Initialize global TTS state from settings
    global tts_enabled
    tts_control = settings.get("ttsControl", {})
    tts_enabled = tts_control.get("enabled", True)
    
    return settings

def app_save_settings(data: Dict[str, Any]):
    """App-specific wrapper for save_settings with TTS and Twitch bot management"""
    # Check if avatar layout settings have changed
    old_settings = app_get_settings()
    avatar_layout_changed = (
        data.get("avatarRows") != old_settings.get("avatarRows") or
        data.get("avatarRowConfig") != old_settings.get("avatarRowConfig")
    )
    
    # Check if TTS enabled state changed
    old_tts_enabled = old_settings.get("ttsControl", {}).get("enabled", True)
    new_tts_control = data.get("ttsControl", {})
    new_tts_enabled = new_tts_control.get("enabled", True)
    tts_state_changed = old_tts_enabled != new_tts_enabled
    
    # Update global TTS state and call stop/resume if it changed
    global tts_enabled
    if tts_state_changed:
        if new_tts_enabled:
            resume_all_tts()
        else:
            stop_all_tts()
        logger.info(f"TTS state changed via settings: {'enabled' if new_tts_enabled else 'disabled'}")
    else:
        # Just sync the flag if no change
        tts_enabled = new_tts_enabled
    
    # Check if Twitch settings have changed
    old_twitch_config = old_settings.get("twitch", {})
    new_twitch_config = data.get("twitch", {})
    twitch_settings_changed = (
        old_twitch_config.get("enabled") != new_twitch_config.get("enabled") or
        old_twitch_config.get("channel") != new_twitch_config.get("channel")
    )
    
    # Check if YouTube settings have changed
    old_youtube_config = old_settings.get("youtube", {})
    new_youtube_config = data.get("youtube", {})
    youtube_settings_changed = (
        old_youtube_config.get("enabled") != new_youtube_config.get("enabled") or
        old_youtube_config.get("channel") != new_youtube_config.get("channel")
    )
    
    # Use the modules save_settings function but without circular import
    # Save settings first
    save_settings(data)
            
    # Restart Twitch bot only if Twitch settings changed
    if twitch_settings_changed:
        logger.info("Twitch settings changed, restarting bot...")
        asyncio.create_task(restart_twitch_if_needed(data))
    else:
        logger.debug("Twitch settings unchanged, skipping bot restart")
    
    # Restart YouTube bot only if YouTube settings changed
    if youtube_settings_changed:
        logger.info("YouTube settings changed, restarting bot...")
        asyncio.create_task(restart_youtube_if_needed(data))
    else:
        logger.debug("YouTube settings unchanged, skipping bot restart")
    
    # Regenerate avatar assignments if layout changed
    if avatar_layout_changed:
        logger.info("Avatar layout settings changed, regenerating slot assignments...")
        # Clear active slots and queue to avoid conflicts
        get_active_avatar_slots().clear()
        queue_manager.clear_all_queues()
        
        # Regenerate assignments
        generate_avatar_slot_assignments()

        # Broadcast avatar slots update
        asyncio.create_task(broadcast_avatar_slots())
        
    
    # Broadcast refresh message to update Yappers page with new settings
    asyncio.create_task(hub.broadcast({
        "type": "settings_updated",
        "message": "Settings updated"
    }))

async def restart_twitch_if_needed(settings: Dict[str, Any]):
    """Restart Twitch bot when settings change"""
    global TwitchTask
    try:
        # Stop existing task if running
        if TwitchTask and not TwitchTask.done():
            logger.info("Stopping existing Twitch bot")
            TwitchTask.cancel()
            try:
                await TwitchTask
            except asyncio.CancelledError:
                logger.info("Twitch bot task cancelled successfully")
            except Exception as e:
                # Catch any other errors during cancellation (e.g., twitchio internal errors)
                logger.warning(f"Error while cancelling Twitch bot task: {e}")
            
            # Give it a moment to fully clean up
            await asyncio.sleep(0.1)
        
        # Start new task if enabled
        if run_twitch_bot and settings.get("twitch", {}).get("enabled"):
            logger.info("Restarting Twitch bot with new settings")
            
            # Get OAuth token from database
            token_info = await get_twitch_token_for_bot()
            if not token_info:
                logger.warning("No Twitch OAuth token found. Cannot restart bot.")
                TwitchTask = None
                return
                
            twitch_config = settings.get("twitch", {})
            channel = twitch_config.get("channel") or token_info["username"]
            
            # Test Twitch connection first to detect auth issues early
            connection_test_passed = await test_twitch_connection(token_info)
            
            if not connection_test_passed:
                logger.warning("Twitch connection test failed during restart - not starting bot")
                TwitchTask = None
                return
            
            # Event router to handle different event types
            async def route_twitch_event(e):
                event_type = e.get("type", "")
                if event_type == "moderation":
                    await handle_moderation_event(e)
                else:
                    # Default to chat event handler
                    await handle_event(e)
            
            # Create Twitch bot task with shared error handling
            TwitchTask = await create_twitch_bot_task(
                token_info=token_info,
                channel=channel,
                route_twitch_event=route_twitch_event,
                context_name="restart"
            )
        else:
            TwitchTask = None
            logger.info("Twitch bot disabled")
    except Exception as e:
        logger.error(f"Failed to restart Twitch bot: {e}", exc_info=True)



def create_twitch_task_exception_handler(context_name: str):
    """Create a Twitch task exception handler with consistent error handling logic"""
    def handle_twitch_task_exception(task):
        logger.info(f"=== TWITCH TASK EXCEPTION HANDLER CALLED ({context_name.upper()}) ===")
        try:
            result = task.result()
            logger.info("Task completed successfully")
        except asyncio.CancelledError:
            logger.info("Twitch bot task was cancelled")
        except Exception as e:
            logger.error(f"Twitch bot task failed: {e}", exc_info=True)
            logger.info(f"ERROR: Twitch bot task failed: {e}")
            logger.info(f"Exception type: {type(e).__name__}")
            logger.info(f"Exception class: {e.__class__.__name__}")
            
            # Check if this is an authentication error
            error_str = str(e).lower()
            is_auth_error = (
                "authentication" in error_str or 
                "unauthorized" in error_str or 
                "invalid" in error_str or
                "access token" in error_str or
                e.__class__.__name__ == "AuthenticationError"
            )
            
            logger.info(f"Is auth error check: {is_auth_error}")
            
            if is_auth_error:
                # Attempt automatic token refresh before showing error
                async def handle_auth_error_with_refresh():
                    global twitch_refresh_attempted, twitch_auth_error
                    
                    logger.warning(f"=== AUTHENTICATION ERROR DETECTED IN {context_name.upper()} ===")
                    
                    # Only attempt refresh once per session to prevent infinite retries
                    if not twitch_refresh_attempted:
                        logger.info("Attempting automatic token refresh...")
                        twitch_refresh_attempted = True
                        
                        try:
                            # Import here to avoid circular imports
                            from routers.auth import get_auth, refresh_twitch_token, get_twitch_user_info, store_twitch_auth
                            
                            auth = get_auth()
                            if auth and auth.refresh_token:
                                logger.info("Refresh token available, attempting refresh...")
                                refreshed_token_data = await refresh_twitch_token(auth.refresh_token)
                                
                                if refreshed_token_data:
                                    # Get updated user info to ensure account is still valid
                                    user_info = await get_twitch_user_info(refreshed_token_data["access_token"])
                                    if user_info:
                                        # Store the refreshed token
                                        await store_twitch_auth(user_info, refreshed_token_data)
                                        logger.info("Successfully refreshed token, attempting to restart Twitch bot...")
                                        
                                        # Clear any existing auth error since we have a fresh token
                                        twitch_auth_error = None
                                        
                                        # Restart the Twitch bot with new token
                                        settings = get_settings()
                                        await restart_twitch_if_needed(settings)
                                        logger.info("Twitch bot restarted after token refresh")
                                        return  # Success! Don't show error
                                    else:
                                        logger.error("Failed to get user info after token refresh")
                                else:
                                    logger.error("Token refresh failed")
                            else:
                                logger.warning("No refresh token available for automatic refresh")
                        except Exception as refresh_error:
                            logger.error(f"Error during automatic token refresh: {refresh_error}")
                    else:
                        logger.warning("Token refresh already attempted in this session, skipping automatic retry")
                    
                    # If we reach here, refresh failed or was already attempted - show error
                    logger.info(f"WebSocket clients available: {len(hub.clients)}")
                    
                    # Store the error globally so new WebSocket connections can be notified
                    twitch_auth_error = {
                        "type": "twitch_auth_error",
                        "message": "Twitch authentication failed. Please reconnect your account.",
                        "error": str(e)
                    }
                    logger.info(f"=== STORED GLOBAL AUTH ERROR ({context_name.upper()}) ===")
                    logger.info(f"Auth error message: {twitch_auth_error['message']}")
                    
                    # Try to broadcast the error
                    try:
                        await hub.broadcast(twitch_auth_error)
                        logger.info(f"Auth error broadcast completed ({context_name})")
                    except Exception as broadcast_error:
                        logger.error(f"Failed to broadcast auth error: {broadcast_error}")
                
                # Schedule the auth error handling
                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_running():
                        asyncio.create_task(handle_auth_error_with_refresh())
                        logger.info(f"Scheduled auth error handling with refresh ({context_name})")
                except Exception as loop_error:
                    logger.warning(f"Could not schedule auth error handling: {loop_error}")
    
    return handle_twitch_task_exception

async def handle_twitch_task_creation_error(create_error: Exception, context_name: str):
    """Handle errors that occur during Twitch task creation with consistent logic"""
    logger.error(f"Failed to create Twitch task during {context_name}: {create_error}")
    logger.info(f"ERROR: Failed to create Twitch task during {context_name}: {create_error}")
    
    # Check if the creation error itself is an auth error
    error_str = str(create_error).lower()
    is_auth_error = (
        "authentication" in error_str or 
        "unauthorized" in error_str or 
        "invalid" in error_str or
        "access token" in error_str
    )
    
    if is_auth_error:
        logger.warning(f"=== AUTHENTICATION ERROR DURING TASK CREATION ({context_name.upper()}) ===")
        
        # Attempt automatic token refresh before showing error
        global twitch_refresh_attempted, twitch_auth_error
        
        # Only attempt refresh once per session to prevent infinite retries
        if not twitch_refresh_attempted:
            logger.info("Attempting automatic token refresh during task creation...")
            twitch_refresh_attempted = True
            
            try:
                # Import here to avoid circular imports
                from routers.auth import get_auth, refresh_twitch_token, get_twitch_user_info, store_twitch_auth
                
                auth = get_auth()
                if auth and auth.refresh_token:
                    logger.info("Refresh token available, attempting refresh...")
                    refreshed_token_data = await refresh_twitch_token(auth.refresh_token)
                    
                    if refreshed_token_data:
                        # Get updated user info to ensure account is still valid
                        user_info = await get_twitch_user_info(refreshed_token_data["access_token"])
                        if user_info:
                            # Store the refreshed token
                            await store_twitch_auth(user_info, refreshed_token_data)
                            logger.info("Successfully refreshed token during task creation, will retry bot startup")
                            
                            # Clear any existing auth error since we have a fresh token
                            twitch_auth_error = None
                            return  # Success! Let the caller retry
                        else:
                            logger.error("Failed to get user info after token refresh during task creation")
                    else:
                        logger.error("Token refresh failed during task creation")
                else:
                    logger.warning("No refresh token available for automatic refresh during task creation")
            except Exception as refresh_error:
                logger.error(f"Error during automatic token refresh in task creation: {refresh_error}")
        else:
            logger.warning("Token refresh already attempted in this session, showing error for task creation")
        
        # If we reach here, refresh failed or was already attempted - store and broadcast error
        twitch_auth_error = {
            "type": "twitch_auth_error", 
            "message": "Twitch authentication failed. Please reconnect your account.",
            "error": str(create_error)
        }
        
        # Try to broadcast immediately
        try:
            await hub.broadcast(twitch_auth_error)
            logger.info(f"Auth error broadcast completed ({context_name} creation error)")
        except Exception as broadcast_error:
            logger.error(f"Failed to broadcast auth error during {context_name}: {broadcast_error}")

async def handle_youtube_auth_error():
    """Handle YouTube authentication errors with automatic token refresh"""
    logger.warning("=== YOUTUBE AUTHENTICATION ERROR ===")
    
    global youtube_refresh_attempted, youtube_auth_error
    
    try:
        # Import here to avoid circular imports
        from routers.auth import get_youtube_auth, refresh_youtube_token, get_youtube_channel_info, store_youtube_auth
        
        auth = get_youtube_auth()
        if auth and auth.refresh_token:
            logger.info("YouTube refresh token available, attempting refresh...")
            refreshed_token_data = await refresh_youtube_token(auth.refresh_token)
            
            if refreshed_token_data:
                # Get updated channel info to ensure account is still valid
                channel_info = await get_youtube_channel_info(refreshed_token_data["access_token"])
                if channel_info:
                    # Store the refreshed token
                    await store_youtube_auth(channel_info, refreshed_token_data)
                    logger.info("Successfully refreshed YouTube token, attempting to restart YouTube bot...")
                    
                    # Clear any existing auth error since we have a fresh token
                    youtube_auth_error = None
                    
                    # Try to restart the YouTube bot with current settings
                    from modules.persistent_data import get_settings
                    current_settings = get_settings()
                    await restart_youtube_if_needed(current_settings)
                    logger.info("YouTube bot restarted after token refresh")
                    return
                else:
                    logger.error("Failed to get channel info after YouTube token refresh")
            else:
                logger.error("YouTube token refresh failed")
        else:
            logger.warning("No YouTube refresh token available for automatic refresh")
    except Exception as refresh_error:
        logger.error(f"Error during automatic YouTube token refresh: {refresh_error}")
    
    # If we reach here, refresh failed - store and broadcast error
    youtube_auth_error = {
        "type": "youtube_auth_error",
        "message": "YouTube authentication failed. Please reconnect your YouTube account.",
        "action": "reconnect"
    }
    
    # Try to broadcast immediately
    try:
        await hub.broadcast(youtube_auth_error)
        logger.info("YouTube auth error broadcast completed")
    except Exception as broadcast_error:
        logger.error(f"Failed to broadcast YouTube auth error: {broadcast_error}")

async def test_twitch_connection(token_info: dict):
    """Test Twitch connection without starting the full bot to detect auth issues early"""
    # Import and use the shared test function from twitch_utils
    from modules.twitch_listener import test_twitch_connection as twitch_utils_test
    return await twitch_utils_test(token_info)

async def create_twitch_bot_task(token_info: dict, channel: str, route_twitch_event, context_name: str):
    """Create a Twitch bot task with consistent error handling"""
    try:
        logger.info(f"Creating Twitch bot task ({context_name}) with user_id: {token_info.get('user_id')}")
        
        # Create the task and monitor it for auth errors immediately
        # Use the authenticated username for TwitchIO compatibility, display name handled separately
        task = asyncio.create_task(run_twitch_bot(
            token=token_info["token"],
            nick=token_info["username"],
            channel=channel,
            on_event=lambda e: asyncio.create_task(route_twitch_event(e)),
            user_id=token_info.get("user_id")
        ))
        
        logger.info(f"Twitch bot task created, attaching error handler...")
        
        # Attach the error handler
        task.add_done_callback(create_twitch_task_exception_handler(context_name))
        logger.info(f"Twitch bot started with comprehensive error handling ({context_name})")
        
        return task
        
    except Exception as create_error:
        await handle_twitch_task_creation_error(create_error, context_name)
        return None

async def get_twitch_token_for_bot():
    """Get current Twitch token for bot connection with automatic refresh"""
    try:
        # Import here to avoid circular imports
        from routers.auth import get_twitch_token_for_bot as auth_get_token
        return await auth_get_token()
    except Exception as e:
        logger.error(f"Error getting Twitch token: {e}")
        return None

async def restart_youtube_if_needed(settings: Dict[str, Any]):
    """Restart YouTube bot when settings change"""
    global YouTubeTask
    try:
        # Stop existing task if running
        if YouTubeTask and not YouTubeTask.done():
            logger.info("Stopping existing YouTube bot")
            YouTubeTask.cancel()
            try:
                await YouTubeTask
            except asyncio.CancelledError:
                logger.info("YouTube bot task cancelled successfully")
            except Exception as e:
                logger.warning(f"Error while cancelling YouTube bot task: {e}")
            
            # Give it a moment to fully clean up
            await asyncio.sleep(0.1)
        
        # Start new task if enabled
        if run_youtube_bot and settings.get("youtube", {}).get("enabled"):
            logger.info("Restarting YouTube bot with new settings")
            
            # Get OAuth token from database
            token_info = await get_youtube_token_for_bot()
            if not token_info:
                logger.warning("No YouTube OAuth token found. Cannot restart bot.")
                YouTubeTask = None
                return
                
            youtube_config = settings.get("youtube", {})
            video_id = youtube_config.get("channel")  # Can be video/stream ID or None for auto-detect
            
            # Event router to handle different event types
            async def route_youtube_event(e):
                event_type = e.get("type", "")
                if event_type == "moderation":
                    await handle_moderation_event(e)
                else:
                    # Default to chat event handler
                    await handle_event(e)
            
            YouTubeTask = asyncio.create_task(run_youtube_bot(
                credentials=token_info["credentials"],
                video_id=video_id,
                on_event=lambda e: asyncio.create_task(route_youtube_event(e)),
                settings=settings
            ))
            logger.info("YouTube bot restarted")
        else:
            YouTubeTask = None
            logger.info("YouTube bot disabled")
    except Exception as e:
        logger.error(f"Failed to restart YouTube bot: {e}", exc_info=True)


async def get_youtube_token_for_bot():
    """Get current YouTube token for bot connection"""
    try:
        from modules.persistent_data import get_youtube_auth
        auth = get_youtube_auth()
        if auth:
            # Return credentials object for YouTube API
            from google.oauth2.credentials import Credentials
            from modules.persistent_data import YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET
            
            credentials = Credentials(
                token=auth.access_token,
                refresh_token=auth.refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=YOUTUBE_CLIENT_ID,
                client_secret=YOUTUBE_CLIENT_SECRET
            )
            
            return {
                "credentials": credentials,
                "channel_id": auth.channel_id,
                "channel_name": auth.channel_name
            }
    except Exception as e:
        logger.error(f"Error getting YouTube token: {e}")
    
    return None

# ---------- Message Filtering ----------

def cancel_user_tts(username: str):
    """
    Cancel any active TTS for a specific user.
    """
    username_lower = username.lower()
    logger.info(f"Attempting to cancel TTS for user: {username}")
    
    # Cancel active TTS job if exists
    if username_lower in active_tts_jobs:
        job_info = active_tts_jobs[username_lower]
        if job_info["task"] and not job_info["task"].done():
            job_info["task"].cancel()
            logger.info(f"Cancelled active TTS for user: {username} (message: {job_info['message'][:50]}...)")
        del active_tts_jobs[username_lower]
        # Note: Counter will be decremented by the cancelled task's exception handler
        
        # Process any queued parallel messages now that a slot is free
        process_parallel_message_queue()
    else:
        logger.info(f"No active TTS found for user: {username}")
    
    # Broadcast cancellation to clients with stop command
    asyncio.create_task(hub.broadcast({
        "type": "tts_cancelled",
        "user": username,
        "message": f"TTS cancelled for {username}",
        "stop_audio": True  # Tell frontend to stop playing audio immediately
    }))

def stop_all_tts():
    """
    Stop all TTS jobs
    """
    global active_tts_jobs, tts_enabled, total_active_tts_count
    
    logger.info(f"Stopping all TTS - {total_active_tts_count} active jobs")
    
    # Cancel all active TTS jobs
    cancelled_count = 0
    for username, job_info in list(active_tts_jobs.items()):
        if job_info["task"] and not job_info["task"].done():
            job_info["task"].cancel()
            cancelled_count += 1
            logger.info(f"Cancelled TTS for user: {username}")
    
    # Clear all data structures
    active_tts_jobs.clear()
    queue_manager.clear_all_queues()  # Clear both queues
    total_active_tts_count = 0
    
    # Disable TTS processing
    tts_enabled = False
    
    logger.info(f"All TTS stopped - cancelled {cancelled_count} active jobs")
    
    # Broadcast global stop to clients with immediate stop command
    asyncio.create_task(hub.broadcast({
        "type": "tts_global_stopped",
        "message": "All TTS stopped",
        "cancelled_count": cancelled_count,
        "stop_all_audio": True  # Tell frontend to stop all playing audio immediately
    }))

def resume_all_tts():
    """
    Resume TTS processing (doesn't restore cancelled jobs, just allows new ones)
    """
    global tts_enabled
    
    tts_enabled = True
    logger.info("TTS processing resumed")
    
    # Broadcast resume to clients
    asyncio.create_task(hub.broadcast({
        "type": "tts_global_resumed", 
        "message": "TTS processing resumed"
    }))

def toggle_tts():
    """
    Toggle TTS on/off and save state to database
    """
    global tts_enabled
    
    if tts_enabled:
        stop_all_tts()
        new_state = False
    else:
        resume_all_tts()
        new_state = True
    
    # Save the new state to database settings
    try:
        settings = get_settings()
        settings['ttsControl'] = {'enabled': new_state}
        save_settings(settings)
    except Exception as e:
        logger.error(f"Failed to save TTS state to database: {e}")
    
    return new_state

# ---------- TTS Pipeline ----------

async def handle_test_voice_event(evt: Dict[str, Any]):
    """Handle test voice events - bypasses parallel limits for testing"""
    logger.info(f"Handling test voice event: {evt}")
    
    # Check if TTS is globally enabled
    if not tts_enabled:
        logger.info(f"TTS is disabled - skipping test voice message from {evt.get('user', 'unknown')}")
        return
    
    # Test voices bypass parallel limits (they're just for testing)
    
    # After parallel limiting check passes, set up variables for TTS processing
    username = evt.get('user', 'unknown')
    username_lower = username.lower()
    settings = app_get_settings()
    
    # Track this job for cancellation
    task = asyncio.current_task()
    
    # Check if user already has an active job and cancel it
    if username_lower in active_tts_jobs:
        old_task = active_tts_jobs[username_lower].get("task")
        if old_task and not old_task.done():
            old_task.cancel()
            logger.info(f"Cancelled previous TTS for test user {username}")
    
    active_tts_jobs[username_lower] = {
        "task": task,
        "message": evt.get('text', '')
    }
    
    try:
        audio_format = settings.get("audioFormat", "mp3")
        
        test_voice_data = evt.get("testVoice")
        if not test_voice_data:
            logger.info("No test voice data provided")
            return
        
        # Create a temporary voice object for testing
        class TestVoice:
            def __init__(self, data):
                self.id = "test"
                self.name = data.get("name", "Test Voice")
                self.provider = data.get("provider", "unknown")
                self.voice_id = data.get("voice_id", "")
                self.avatar_image = None
                self.enabled = True
        
        selected_voice = TestVoice(test_voice_data)
        logger.info(f"Test voice: {selected_voice.name} ({selected_voice.provider})")

        # Get TTS configuration
        tts_config = settings.get("tts", {})
        monstertts_config = tts_config.get("monstertts", {})
        monster_api_key = monstertts_config.get("apiKey", "")
        google_config = tts_config.get("google", {})
        google_api_key = google_config.get("apiKey", "")
        polly_config = tts_config.get("polly", {})
        
        # Use hybrid provider
        provider = await get_hybrid_provider(
            monster_api_key=monster_api_key if monster_api_key else None,
            monster_voice_id=selected_voice.voice_id if selected_voice.provider == "monstertts" else None,
            edge_voice_id=selected_voice.voice_id if selected_voice.provider == "edge" else None,
            fallback_voices=[selected_voice],
            google_api_key=google_api_key if google_api_key else None,
            polly_config=polly_config if polly_config.get("accessKey") and polly_config.get("secretKey") else None
        )
        
        # Create and process TTS job
        job = TTSJob(text=evt.get('text', '').strip(), voice=selected_voice.voice_id, audio_format=audio_format)
        logger.info(f"Test TTS Job: text='{job.text}', voice='{selected_voice.name}' ({selected_voice.provider}:{selected_voice.voice_id})")

        logger.info(f"Starting test TTS synthesis...")
        path = await provider.synth(job)
        logger.info(f"Test TTS generated: {path}")
        
        # Broadcast to clients
        voice_info = {
            "id": selected_voice.id,
            "name": selected_voice.name,
            "provider": selected_voice.provider,
            "avatar": selected_voice.avatar_image
        }
        payload = {
            "type": "play",
            "user": evt.get("user"),
            "message": evt.get("text"),
            "eventType": evt.get("eventType", "chat"),
            "voice": voice_info,
            "audioUrl": f"/audio/{os.path.basename(path)}"
        }
        logger.info(f"Broadcasting test voice to {len(hub.clients)} clients")
        await hub.broadcast(payload)
        
        # Clean up TTS job tracking (test voices don't affect counter)
        if username_lower in active_tts_jobs:
            del active_tts_jobs[username_lower]
        logger.info(f"Test TTS complete. Counter unaffected: {total_active_tts_count}")
        
    except asyncio.CancelledError:
        logger.info(f"Test TTS cancelled for user: {evt.get('user')}")
        if username_lower in active_tts_jobs:
            del active_tts_jobs[username_lower]
        logger.info(f"Cleaned up cancelled test job. Counter unaffected: {total_active_tts_count}")
        raise
    except Exception as e:
        logger.error(f"Test TTS error for {username_lower}: {e}", exc_info=True)
        if username_lower in active_tts_jobs:
            del active_tts_jobs[username_lower]
        logger.info(f"Cleaned up failed test job. Counter unaffected: {total_active_tts_count}")
        # Test voices don't affect parallel limit counter

async def check_parallel_limits_and_process(evt: Dict[str, Any], is_test_voice: bool = False):
    """
    Audio duration-based parallel limiting - simple and reliable.
    No WebSocket dependencies, no job tracking complexity.
    """
    global total_active_tts_count
    
    username = evt.get('user', 'unknown')
    settings = app_get_settings()
    parallel_limit = settings.get("parallelMessageLimit", 5)
    queue_overflow = settings.get("queueOverflowMessages", True)
    current_active = total_active_tts_count
    
    # Check if we have a limit and if it's exceeded
    if parallel_limit is not None and isinstance(parallel_limit, (int, float)) and parallel_limit > 0 and current_active >= parallel_limit:
        logger.info(f"Parallel limit reached ({current_active}/{parallel_limit}) for {username}")
        
        if queue_overflow and not is_test_voice:  # Don't queue test voices
            queue_parallel_message(evt)
            logger.info(f"Message queued due to parallel limit (queue size: {len(parallel_message_queue)})")
        else:
            logger.info(f"Message from {username} ignored due to parallel limit")
        return False
    
    # Accept message - increment counter and process
    increment_tts_count()
    
    try:
        await process_tts_message(evt)
        return True
    except Exception as e:
        # If processing failed, decrement counter
        decrement_tts_count()
        logger.error(f"TTS processing failed for {username}: {e}", exc_info=True)
        return False

async def handle_event(evt: Dict[str, Any]):
    """Handle regular chat events with message filtering and parallel limiting"""
    logger.info(f"Handling event: {evt}")
    
    # Check if TTS is globally enabled
    if not tts_enabled:
        logger.info(f"TTS is disabled - skipping message from {evt.get('user', 'unknown')}")
        return

    settings = app_get_settings()
    # Apply message filtering
    original_text = evt.get('text', '').strip()
    username = evt.get('user', '')
    tags = evt.get('tags', {})  # Get Twitch tags for emote detection
    event_type = evt.get('eventType', 'chat')
    should_process, filtered_text = should_process_message(original_text, settings, username, active_tts_jobs, tags)
    
    # Add to message history for testing/replay (even if not processed)
    add_to_message_history(username, original_text, filtered_text, event_type, tags)
    
    if not should_process:
        logger.info(f"Skipping message due to filtering: {original_text[:50]}... (user: {username})")
        return
    
    # Update event with filtered text before processing
    evt_filtered = evt.copy()
    evt_filtered['text'] = filtered_text
    
    # Check parallel limits and process if allowed (this handles the entire processing)
    await check_parallel_limits_and_process(evt_filtered, is_test_voice=False)
    
    if filtered_text != original_text:
        logger.info(f"Text after filtering: '{filtered_text}'")

async def process_tts_message(evt: Dict[str, Any]):
    """Process TTS message with simple audio duration-based limiting"""
    username = evt.get('user', 'unknown')
    username_lower = username.lower()
    
    # Skip TTS if there's no text to speak
    text = evt.get("text", "").strip()
    if not text:
        event_type = evt.get("eventType", "chat")
        logger.info(f"Skipping TTS for {username} - no text to speak (eventType: {event_type})")
        # Counter was already incremented, so decrement it
        decrement_tts_count()
        return

    # Track this task for cancellation (simple - just task and message)
    task = asyncio.current_task()
    active_tts_jobs[username_lower] = {
        "task": task,
        "message": text
    }
    
    settings = app_get_settings()
    audio_format = settings.get("audioFormat", "mp3")
    special = settings.get("specialVoices", {})
    
    # Get enabled voices from database
    enabled_voices = get_enabled_voices()

    if not enabled_voices:
        logger.info("No enabled voices found in database. Please add voices through the settings page.")
        return

    event_type = evt.get("eventType", "chat")
    
    # First, find an available avatar slot (without voice filtering)
    # This will be used to determine which voice to use
    target_slot = find_available_slot_for_tts(voice_id=None, user=username)
    
    if not target_slot:
        logger.info(f"No available avatar slots for {username}, message will be queued")
        decrement_tts_count()
        return
    
    # Now determine the voice to use based on priority:
    # 1. Slot's assigned voice (if voice_id is set and valid)
    # 2. Special event voice mapping
    # 3. Random voice (avoiding last voice if no slot assignment)
    
    selected_voice = None
    slot_voice_id = target_slot.get("voice_id")
    
    # Check if slot has an assigned voice
    if slot_voice_id is not None:
        selected_voice = next((v for v in enabled_voices if v.id == slot_voice_id), None)
        if selected_voice:
            logger.info(f"Using slot-assigned voice: {selected_voice.name} ({selected_voice.provider}) for slot {target_slot['id']}")
        else:
            logger.warning(f"Slot {target_slot['id']} has voice_id {slot_voice_id} but voice not found in enabled voices, will select randomly")
    
    # If no slot voice, check special event mapping
    if not selected_voice and event_type in special:
        vid = special[event_type].get("voiceId")
        # Validate vid is a proper integer/string ID, not a function name or corrupted value
        if vid and not str(vid).isdigit() and str(vid) not in ["get_by_id", "null", "undefined", ""]:
            logger.warning(f"Invalid voice ID '{vid}' in special event mapping for {event_type}, will use random voice instead")
            vid = None
        # Try to find the voice by database ID
        if vid:
            selected_voice = next((v for v in enabled_voices if str(v.id) == str(vid)), None)
            if not selected_voice:
                logger.warning(f"Special event voice ID {vid} for {event_type} not found in enabled voices, will use random voice instead")
            else:
                logger.info(f"Special event voice selected: {selected_voice.name} ({selected_voice.provider})")
    
    # If still no voice selected, choose randomly (avoiding last voice if possible)
    if not selected_voice:
        global last_selected_voice_id
        
        # If we have more than 2 voices, avoid selecting the same voice as last time
        if len(enabled_voices) >= 2 and last_selected_voice_id is not None:
            available_voices = [v for v in enabled_voices if v.id != last_selected_voice_id]
            if available_voices:
                selected_voice = random.choice(available_voices)
                logger.info(f"Random voice selected (avoiding last voice): {selected_voice.name} ({selected_voice.provider})")
            else:
                # Fallback if filtering didn't work
                selected_voice = random.choice(enabled_voices)
                logger.info(f"Random voice selected (fallback): {selected_voice.name} ({selected_voice.provider})")
        else:
            # Not enough voices to avoid repetition, or no last voice tracked
            selected_voice = random.choice(enabled_voices)
            logger.info(f"Random voice selected: {selected_voice.name} ({selected_voice.provider})")
        
        # Update last selected voice only when randomly selected (not for slot-assigned or special event voices)
        last_selected_voice_id = selected_voice.id
    
    # Track voice usage for distribution analysis
    global voice_usage_stats, voice_selection_count
    voice_key = f"{selected_voice.name} ({selected_voice.provider})"
    voice_usage_stats[voice_key] += 1
    voice_selection_count += 1

    logger.info(f"Selected voice: {selected_voice.name} ({selected_voice.provider})")

    # Get TTS configuration
    tts_config = settings.get("tts", {})
    
    # Get TTS provider configurations
    monstertts_config = tts_config.get("monstertts", {})
    monster_api_key = monstertts_config.get("apiKey", "")
    
    edge_config = tts_config.get("edge", {})
    
    google_config = tts_config.get("google", {})
    google_api_key = google_config.get("apiKey", "")
    
    polly_config = tts_config.get("polly", {})
    
    # Use hybrid provider that handles all providers with rate limiting and fallback
    provider = await get_hybrid_provider(
        monster_api_key=monster_api_key if monster_api_key else None,
        monster_voice_id=selected_voice.voice_id if selected_voice.provider == "monstertts" else None,
        edge_voice_id=selected_voice.voice_id if selected_voice.provider == "edge" else None,
        fallback_voices=enabled_voices,
        google_api_key=google_api_key if google_api_key else None,
        polly_config=polly_config if polly_config.get("accessKey") and polly_config.get("secretKey") else None
    )
    
    # Create TTS job with the selected voice
    job = TTSJob(text=evt.get('text', '').strip(), voice=selected_voice.voice_id, audio_format=audio_format)
    logger.info(f"TTS Job: text='{job.text}', voice='{selected_voice.name}' ({selected_voice.provider}:{selected_voice.voice_id}), format='{job.audio_format}'")
    
    try:
        logger.info(f"Starting TTS synthesis for {evt.get('user')}...")
        path = await provider.synth(job)
        logger.info(f"TTS generated: {path}")
        
        # Apply audio filters if enabled
        audio_filter_settings = settings.get("audioFilters", {})
        if audio_filter_settings.get("enabled", False):
            from modules.audio_filters import get_audio_filter_processor
            
            filter_processor = get_audio_filter_processor()
            random_filters = audio_filter_settings.get("randomFilters", False)
            
            # Apply filters (returns new path and duration)
            filtered_path, filtered_duration = filter_processor.apply_filters(
                path,
                audio_filter_settings,
                random_filters=random_filters
            )
            
            # Use filtered audio and its duration
            path = filtered_path
            audio_duration = filtered_duration
            
            # If filter didn't return duration, it means no filters were applied
            if audio_duration is None:
                audio_duration = get_audio_duration(path)
                if path == filtered_path:
                    # Path unchanged means filters were skipped (no effects enabled)
                    logger.debug("Audio filters skipped (no individual effects enabled)")
                else:
                    # Path changed but no duration means filter processing had an issue
                    logger.info(f"Audio filters applied: {path}")
            else:
                logger.info(f"Audio filters applied: {path} (new duration: {audio_duration:.2f}s)")
        else:
            # Get audio duration for accurate slot timeout (no filters applied)
            audio_duration = get_audio_duration(path)
        
        # We already found the slot earlier (before voice selection)
        # No need to find it again here
        
        audio_url = f"/audio/{os.path.basename(path)}"
        
        # Debug logging for .exe troubleshooting
        logger.info(f"=== TTS AUDIO GENERATED ===")
        logger.info(f"Audio file path: {path}")
        logger.info(f"Audio file exists: {os.path.exists(path)}")
        logger.info(f"Audio file size: {os.path.getsize(path) if os.path.exists(path) else 'N/A'} bytes")
        logger.info(f"Audio URL: {audio_url}")
        logger.info(f"Audio duration: {audio_duration}s")
        logger.info(f"AUDIO_DIR: {AUDIO_DIR}")
        
        # Create base payload
        voice_info = {
            "id": selected_voice.id,
            "name": selected_voice.name,
            "provider": selected_voice.provider,
            "avatar": selected_voice.avatar_image
        }
        
        base_payload = {
            "type": "play",
            "user": evt.get("user"),
            "message": evt.get("text"),
            "eventType": event_type,
            "voice": voice_info,
            "audioUrl": audio_url
        }
        
        if target_slot:
            # Slot available - reserve it and send enhanced payload
            reserve_avatar_slot(target_slot["id"], username, audio_url, audio_duration)
            
            enhanced_payload = base_payload.copy()
            enhanced_payload.update({
                "targetSlot": {
                    "id": target_slot["id"],
                    "x_position": target_slot.get("x_position", 50),
                    "y_position": target_slot.get("y_position", 50),
                    "size": target_slot.get("size", 100)
                },
                "avatarData": target_slot["avatarData"],
                "generationId": get_avatar_assignments_generation_id()
            })
            
            logger.info(f"Broadcasting TTS with slot {target_slot['id']} to {len(hub.clients)} clients")
            logger.info(f"=== BROADCASTING WEBSOCKET MESSAGE ===")
            logger.info(f"Message type: play")
            logger.info(f"Target slot: {target_slot['id']}")
            logger.info(f"Audio URL in payload: {enhanced_payload.get('audioUrl')}")
            logger.info(f"Connected WebSocket clients: {len(hub.clients)}")
            logger.info(f"Payload keys: {list(enhanced_payload.keys())}")
            
            await hub.broadcast(enhanced_payload)
            logger.info(f"=== BROADCAST COMPLETE ===")
        else:
            # No slots available - queue the message
            logger.info(f"All slots busy, queuing TTS for {username}")
            queue_avatar_message(base_payload)
            
            # Still broadcast a notification that the message is queued
            queue_notification = {
                "type": "tts_queued",
                "user": evt.get("user"),
                "message": evt.get("text"),
                "queuePosition": get_avatar_queue_length()
            }
            await hub.broadcast(queue_notification)
        
        # Simple audio duration-based parallel limiting
        # Schedule decrement after audio finishes (based on duration)
        decrement_delay = audio_duration + 0.5 if audio_duration and audio_duration > 0 else 5.0
        
        async def decrement_after_audio():
            await asyncio.sleep(decrement_delay)
            decrement_tts_count()
            # Process any queued messages now that a slot is free
            process_parallel_message_queue()
        
        # Start the decrement timer (fire and forget - no tracking needed)
        asyncio.create_task(decrement_after_audio())
        
        # Clean up job tracking (we only needed it for potential cancellation during processing)
        if username_lower in active_tts_jobs:
            del active_tts_jobs[username_lower]
        
        logger.info(f"TTS generation complete for {username}. Counter: {total_active_tts_count}")
            
    except asyncio.CancelledError:
        logger.info(f"TTS synthesis cancelled for user: {username}")
        # Clean up job tracking
        if username_lower in active_tts_jobs:
            del active_tts_jobs[username_lower]
        # Counter was already incremented, so decrement it on cancellation
        decrement_tts_count()
        raise  # Re-raise to properly handle cancellation
    except Exception as e:
        logger.error(f"TTS synthesis error for {username}: {e}", exc_info=True)
        # Clean up job tracking
        if username_lower in active_tts_jobs:
            del active_tts_jobs[username_lower]
        # Counter was already incremented, so decrement it on error
        decrement_tts_count()
        # Process any queued parallel messages now that a slot is free
        process_parallel_message_queue()

# ---------- Simulate messages (for local testing) ----------

async def handle_moderation_event(evt: Dict[str, Any]):
    """Handle Twitch moderation events (bans, timeouts)"""
    logger.info(f"Handling moderation event: {evt}")
    
    event_type = evt.get("eventType", "")
    target_user = evt.get("target_user", "")
    duration = evt.get("duration")  # None for permanent ban, seconds for timeout
    
    if not target_user:
        logger.info("No target user specified in moderation event")
        return
    
    if event_type in ["ban", "timeout"]:
        logger.info(f"User {event_type}: {target_user}" + (f" for {duration}s" if duration else ""))
        
        # Cancel any active TTS for this user (this includes immediate audio stop)
        cancel_user_tts(target_user)
        
        # Broadcast moderation event to clients with additional audio stop command
        await hub.broadcast({
            "type": "moderation",
            "eventType": event_type,
            "target_user": target_user,
            "duration": duration,
            "message": f"User {target_user} has been {'timed out' if event_type == 'timeout' else 'banned'}",
            "stop_user_audio": target_user  # Tell frontend to immediately stop this user's audio
        })
        
        logger.info(f"Processed {event_type} for user: {target_user} - TTS cancelled and audio stopped")
    else:
        logger.info(f"Unknown moderation event type: {event_type}")

# ---------- Twitch integration (optional) ----------
TwitchTask = None
try:
    from modules.twitch_listener import run_twitch_bot
    logger.info("Twitch listener imported successfully")
except Exception as e:
    logger.error(f"Failed to import twitch_listener: {e}")
    logger.info(f"Failed to import Twitch listener: {e}")
    run_twitch_bot = None

# ---------- YouTube integration (optional) ----------
YouTubeTask = None
try:
    from modules.youtube_listener import run_youtube_bot
    logger.info("YouTube listener imported successfully")
except Exception as e:
    logger.error(f"Failed to import youtube_listener: {e}")
    logger.info(f"Failed to import YouTube listener: {e}")
    run_youtube_bot = None

# ---------- Avatar Slot Management API ----------
# Avatar slot endpoints have been moved to routers/avatars.py

@app.on_event("startup")
async def startup():
    logger.info("FastAPI startup event triggered")
    try:
        # Broadcast initial avatar slot assignments to any connected clients
        await broadcast_avatar_slots()
        logger.info("Initial avatar slot assignments broadcasted")
        
        settings = app_get_settings()
        logger.info(f"Settings loaded, Twitch enabled: {settings.get('twitch', {}).get('enabled')}")
        
        if run_twitch_bot and settings.get("twitch", {}).get("enabled"):
            logger.info("Starting Twitch bot...")
            
            # Get OAuth token from database (with automatic refresh if needed)
            token_info = await get_twitch_token_for_bot()
            if not token_info:
                # Check if auth exists at all to provide better error message
                from modules.persistent_data import get_auth
                existing_auth = get_auth()
                
                if existing_auth:
                    # Auth exists but token refresh failed or token expired without refresh token
                    logger.error("Twitch token expired and could not be refreshed. Please reconnect your Twitch account.")
                    
                    # Broadcast error to frontend
                    global twitch_auth_error
                    twitch_auth_error = {
                        "type": "twitch_auth_error",
                        "message": "Your Twitch connection has expired. Please reconnect your account in settings.",
                        "error": "Token expired and refresh failed"
                    }
                    await hub.broadcast(twitch_auth_error)
                else:
                    # No auth exists at all
                    logger.warning("No Twitch OAuth token found. Please connect your Twitch account.")
                return
                
            twitch_config = settings.get("twitch", {})
            channel = twitch_config.get("channel") or token_info["username"]
            
            logger.info(f"Twitch config: channel={channel}, nick={token_info['username']} (displayed as Chat Yapper), token={'***' if token_info['token'] else 'None'}")
            
            # Test Twitch connection first to detect auth issues early
            connection_test_passed = await test_twitch_connection(token_info)
            
            if not connection_test_passed:
                logger.warning("Twitch connection test failed - not starting full bot")
                # Don't return here, let the auth error be handled by the test function
                # The error will already be broadcast to clients
                return
            
            # Event router to handle different event types
            async def route_twitch_event(e):
                event_type = e.get("type", "")
                if event_type == "moderation":
                    await handle_moderation_event(e)
                else:
                    # Default to chat event handler
                    await handle_event(e)
            
            global TwitchTask
            
            # Create Twitch bot task with shared error handling
            TwitchTask = await create_twitch_bot_task(
                token_info=token_info,
                channel=channel,
                route_twitch_event=route_twitch_event,
                context_name="startup"
            )
        else:
            if not run_twitch_bot:
                logger.warning("Twitch bot not available (import failed)")
            else:
                logger.info("Twitch integration disabled in settings")
        
        # Start YouTube bot if enabled
        logger.info(f"YouTube enabled: {settings.get('youtube', {}).get('enabled')}")
        if run_youtube_bot and settings.get("youtube", {}).get("enabled"):
            logger.info("Starting YouTube bot...")
            
            # Get OAuth token from database
            token_info = await get_youtube_token_for_bot()
            if not token_info:
                logger.warning("No YouTube OAuth token found. Please connect your YouTube account.")
            else:
                youtube_config = settings.get("youtube", {})
                video_id = youtube_config.get("channel")  # Can be video/stream ID or None
                
                logger.info(f"YouTube config: video_id={video_id or 'auto-detect'}, channel={token_info.get('channel_name', 'Unknown')}")
                
                # Event router to handle different event types
                async def route_youtube_event(e):
                    event_type = e.get("type", "")
                    if event_type == "moderation":
                        await handle_moderation_event(e)
                    else:
                        # Default to chat event handler
                        await handle_event(e)
                
                global YouTubeTask
                yt = asyncio.create_task(run_youtube_bot(
                    credentials=token_info["credentials"],
                    video_id=video_id,
                    on_event=lambda e: asyncio.create_task(route_youtube_event(e)),
                    settings=settings
                ))
                
                # Add error handler for the YouTube task
                def handle_youtube_task_exception(task):
                    try:
                        task.result()
                    except asyncio.CancelledError:
                        logger.info("YouTube bot task was cancelled")
                    except Exception as e:
                        logger.error(f"YouTube bot task failed: {e}", exc_info=True)
                        logger.info(f"ERROR: YouTube bot task failed: {e}")
                        
                        # Handle authentication errors
                        error_message = str(e).lower()
                        if "401" in error_message or "unauthorized" in error_message or "credential" in error_message:
                            global youtube_auth_error, youtube_refresh_attempted
                            
                            # Check if we should attempt automatic token refresh
                            if not youtube_refresh_attempted:
                                youtube_refresh_attempted = True
                                logger.info("YouTube authentication error detected, attempting automatic token refresh...")
                                
                                # Attempt token refresh in a separate task
                                asyncio.create_task(handle_youtube_auth_error())
                            else:
                                logger.warning("YouTube token refresh already attempted, skipping automatic retry")
                                
                                # Set auth error for frontend notification
                                youtube_auth_error = {
                                    "type": "youtube_auth_error",
                                    "message": "YouTube authentication failed. Please reconnect your YouTube account.",
                                    "action": "reconnect"
                                }
                                
                                # Broadcast to connected clients
                                if hub:
                                    asyncio.create_task(hub.broadcast(youtube_auth_error))
                
                yt.add_done_callback(handle_youtube_task_exception)
                YouTubeTask = yt
                logger.info("YouTube bot task created")
        else:
            if not run_youtube_bot:
                logger.warning("YouTube bot not available (import failed)")
            else:
                logger.info("YouTube integration disabled in settings")

    except Exception as e:
        logger.error(f"Startup event failed: {e}", exc_info=True)

# Mount static files AFTER all API routes and WebSocket endpoints are defined
# This ensures that /api/* and /ws routes take precedence over static file serving
# Use static router's mount function for static files
from routers.static import mount_static_files
mount_static_files(app)

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 8008))
    debug_mode = os.environ.get('DEBUG', '').lower() in ('true', '1', 'yes', 'on')
    uvicorn.run("app:app", host=host, port=port, reload=debug_mode)
