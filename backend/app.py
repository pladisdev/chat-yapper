from __future__ import annotations
import asyncio
import json
import logging
import os
import random
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict
import aiohttp

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()  # Load .env file from current directory or parent directories

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Session, select, create_engine

from modules.models import Setting, Voice, AvatarImage, TwitchAuth
from modules.tts import get_provider, get_hybrid_provider, TTSJob, AUDIO_DIR
from modules.message_filter import get_message_history
from modules.backend_logging import log_important
from modules import (
    is_executable, logger, get_env_var, get_user_data_dir, 
    USER_DATA_DIR, DB_PATH, engine, get_settings, save_settings
)

# TTS Cancellation System:
# - Tracks active TTS jobs by username in active_tts_jobs dict
# - Detects Twitch ban/timeout events via CLEARCHAT IRC messages
# - Cancels ongoing TTS synthesis and removes from queue for banned/timed-out users
# - Provides API endpoints for manual testing and management



# Voice usage tracking for distribution analysis
voice_usage_stats = defaultdict(int)
voice_selection_count = 0

# TTS job tracking for cancellation support - supports parallel audio with per-user queuing
# Multiple users can have TTS playing simultaneously, only stopped by:
# 1. Global TTS stop button (stops all)
# 2. Individual user ban/timeout (stops only that user)
# 3. New TTS from same user is ignored if their previous TTS is still playing
# Track active TTS tasks for cancellation only
# username -> {"task": asyncio.Task, "message": str}
active_tts_jobs = {}

# Global TTS control
tts_enabled = True  # Global flag to control TTS processing

def get_max_avatar_positions():
    """Calculate the maximum number of avatar positions from settings"""
    settings = app_get_settings()
    avatar_rows = settings.get("avatarRows", 2)
    avatar_row_config = settings.get("avatarRowConfig", [6, 6])
    # Sum up avatars across all configured rows
    max_positions = sum(avatar_row_config[:avatar_rows])
    return max_positions

# ---------- Config & DB ----------
# Database and user directory setup is now handled in modules/__init__.py
logger.info(f"Database path: {DB_PATH}")
logger.info(f"User data directory: {USER_DATA_DIR}")

# Run database migrations BEFORE creating engine and tables
# This ensures old databases are updated to the new schema
try:
    from modules.db_migration import run_all_migrations, get_database_info
    logger.info("Running database migration check...")
    run_all_migrations(DB_PATH)
    
    # Log database info for debugging
    db_info = get_database_info(DB_PATH)
    if db_info.get("exists"):
        logger.info(f"Database tables: {list(db_info.get('tables', {}).keys())}")
    
except Exception as e:
    logger.error(f"Database migration failed: {e}")
    log_important(f"Database migration error: {e}")
    # Continue anyway - SQLModel.metadata.create_all will create missing tables

# Ensure tables exist (engine is imported from modules)
SQLModel.metadata.create_all(engine)

# Seed settings if empty
DEFAULTS_PATH = os.path.join(os.path.dirname(__file__), "settings_defaults.json")
logger.info(f"Looking for settings defaults at: {DEFAULTS_PATH}")
if not os.path.exists(DEFAULTS_PATH):
    logger.error(f"Missing settings_defaults.json at {DEFAULTS_PATH}")
    raise SystemExit("Missing settings_defaults.json")
else:
    logger.info("Found settings_defaults.json")

with Session(engine) as s:
    exists = s.exec(select(Setting).where(Setting.key == "settings")).first()
    if not exists:
        logger.info(f"No settings found, creating default settings from {DEFAULTS_PATH}")
        default_settings = open(DEFAULTS_PATH, "r", encoding="utf-8").read()
        s.add(Setting(key="settings", value_json=default_settings))
        s.commit()
        logger.info("Default settings created and saved to database")
    else:
        logger.info("Existing settings found in database")

# Voice database starts empty - users need to add voices manually
logger.info("Voice management system initialized - users can add voices through the settings page")
log_important("Voice management system initialized")

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
app.include_router(tts_router)
app.include_router(avatars_router)
app.include_router(auth_router)
app.include_router(static_router)
app.include_router(voices_router)
app.include_router(system_router)

# Serve generated audio files under /audio
# Use AUDIO_DIR from TTS module to ensure consistency
logger.info(f"Audio directory: {AUDIO_DIR}")
logger.info(f"Audio directory exists: {os.path.isdir(AUDIO_DIR)}")
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

# Store PUBLIC_DIR for mounting later (after routes are defined)
PUBLIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "public"))
logger.info(f"Static files directory: {PUBLIC_DIR}")
logger.info(f"Directory exists: {os.path.isdir(PUBLIC_DIR)}")

PERSISTENT_AVATARS_DIR = os.path.join(USER_DATA_DIR, "voice_avatars")
os.makedirs(PERSISTENT_AVATARS_DIR, exist_ok=True)
logger.info(f"Persistent avatars directory: {PERSISTENT_AVATARS_DIR}")

# Debug: List files in the public directory
if os.path.isdir(PUBLIC_DIR):
    logger.info("📂 Files in static directory:")
    for root, dirs, files in os.walk(PUBLIC_DIR):
        level = root.replace(PUBLIC_DIR, '').count(os.sep)
        indent = ' ' * 2 * level
        logger.info(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            logger.info(f"{subindent}{file}")
else:
    logger.info("Static files directory not found")

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
        dead = []
        for ws in self.clients:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(ws)
        for d in dead:
            self.unregister(d)

hub = Hub()

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    client_info = f"{ws.client.host}:{ws.client.port}" if ws.client else "unknown"
    logger.info(f"WebSocket connection attempt from {client_info}")
    logger.info(f"WebSocket connection attempt from {ws.client}")
    try:
        await hub.connect(ws)
        logger.info(f"WebSocket connected successfully. Total clients: {len(hub.clients)}")
        logger.info(f"WebSocket connected successfully. Total clients: {len(hub.clients)}")
        
        # Send a welcome message to confirm connection
        welcome_msg = {
            "type": "connection",
            "message": "WebSocket connected successfully",
            "client_count": len(hub.clients)
        }
        await ws.send_text(json.dumps(welcome_msg))
        logger.info(f"Sent welcome message to WebSocket client {client_info}")
        logger.info(f"Sent welcome message to WebSocket client")
        
        while True:
            # In this app, server pushes; but you can accept pings or config messages:
            message = await ws.receive_text()
            logger.debug(f"WebSocket received message from {client_info}: {message}")
            logger.info(f"WebSocket received: {message}")
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected from {client_info}. Remaining clients: {len(hub.clients)-1}")
        logger.info(f"WebSocket disconnected. Remaining clients: {len(hub.clients)-1}")
        hub.unregister(ws)
    except Exception as e:
        logger.error(f"WebSocket error from {client_info}: {e}")
        logger.info(f"WebSocket error: {e}")
        hub.unregister(ws)

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
    # Update global TTS state from settings
    global tts_enabled
    tts_control = data.get("ttsControl", {})
    new_tts_enabled = tts_control.get("enabled", True)
    
    if new_tts_enabled != tts_enabled:
        if new_tts_enabled:
            resume_all_tts()
        else:
            stop_all_tts()
    
    # Use the modules save_settings function but without circular import
    # Save settings first
    with Session(engine) as s:
        row = s.exec(select(Setting).where(Setting.key == "settings")).first()
        if row:
            row.value_json = json.dumps(data)
            s.add(row)
            s.commit()
            logger.info(f"Settings saved to database: {DB_PATH}")
            
            # Restart Twitch bot if settings changed
            asyncio.create_task(restart_twitch_if_needed(data))
            
            # Broadcast refresh message to update Yappers page with new settings
            asyncio.create_task(hub.broadcast({
                "type": "settings_updated",
                "message": "Settings updated"
            }))
        else:
            logger.error("Could not find settings row to update!")

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
                pass
        
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
            
            # Event router to handle different event types
            async def route_twitch_event(e):
                event_type = e.get("type", "")
                if event_type == "moderation":
                    await handle_moderation_event(e)
                else:
                    # Default to chat event handler
                    await handle_event(e)
            
            TwitchTask = asyncio.create_task(run_twitch_bot(
                token=token_info["token"],
                nick=token_info["username"],
                channel=channel,
                on_event=lambda e: asyncio.create_task(route_twitch_event(e))
            ))
            logger.info("Twitch bot restarted")
        else:
            TwitchTask = None
            logger.info("Twitch bot disabled")
    except Exception as e:
        logger.error(f"Failed to restart Twitch bot: {e}", exc_info=True)



async def get_twitch_token_for_bot():
    """Get current Twitch token for bot connection"""
    try:
        with Session(engine) as session:
            auth = session.exec(select(TwitchAuth)).first()
            if auth:
                # Check if token needs refresh (if expires_at is set and in the past)
                if auth.expires_at:
                    expires_at = datetime.fromisoformat(auth.expires_at)
                    if expires_at <= datetime.now():
                        logger.info("Twitch token expired, attempting refresh...")
                        # TODO: Implement token refresh
                        
                return {
                    "token": auth.access_token,
                    "username": auth.username,
                    "user_id": auth.twitch_user_id
                }
    except Exception as e:
        logger.error(f"Error getting Twitch token: {e}")
    
    return None

# ---------- Message Filtering ----------

def cancel_user_tts(username: str):
    """
    Cancel any active TTS for a specific user.
    """
    global active_tts_jobs
    
    username_lower = username.lower()
    logger.info(f"Attempting to cancel TTS for user: {username}")
    logger.info(f"🛑 Attempting to cancel TTS for user: {username}")
    
    # Cancel active TTS job if exists
    if username_lower in active_tts_jobs:
        job_info = active_tts_jobs[username_lower]
        if job_info["task"] and not job_info["task"].done():
            job_info["task"].cancel()
            logger.info(f"Cancelled active TTS for user: {username} (message: {job_info['message'][:50]}...)")
            logger.info(f"✅ Cancelled active TTS for user: {username}")
        del active_tts_jobs[username_lower]
    else:
        logger.info(f"ℹ️  No active TTS found for user: {username}")
    
    # Broadcast cancellation to clients with stop command
    asyncio.create_task(hub.broadcast({
        "type": "tts_cancelled",
        "user": username,
        "message": f"TTS cancelled for {username}",
        "stop_audio": True  # Tell frontend to stop playing audio immediately
    }))

def stop_all_tts():
    """
    Stop all active TTS jobs
    """
    global active_tts_jobs, tts_enabled
    
    logger.info("Stopping all TTS - cancelling active jobs")
    logger.info(f"🛑 Stopping all TTS - {len(active_tts_jobs)} active jobs")
    
    # Cancel all active TTS jobs
    cancelled_count = 0
    for username, job_info in list(active_tts_jobs.items()):
        if job_info["task"] and not job_info["task"].done():
            job_info["task"].cancel()
            cancelled_count += 1
            logger.info(f"Cancelled TTS for user: {username}")
    
    # Clear all data structures
    active_tts_jobs.clear()
    
    # Disable TTS processing
    tts_enabled = False
    
    logger.info(f"All TTS stopped - cancelled {cancelled_count} active jobs")
    logger.info(f"✅ All TTS stopped - cancelled {cancelled_count} active jobs")
    
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
    logger.info("▶️ TTS processing resumed")
    
    # Broadcast resume to clients
    asyncio.create_task(hub.broadcast({
        "type": "tts_global_resumed", 
        "message": "TTS processing resumed"
    }))

def toggle_tts():
    """
    Toggle TTS on/off
    """
    if tts_enabled:
        stop_all_tts()
        return False
    else:
        resume_all_tts()
        return True

def should_process_message(text: str, settings: Dict[str, Any], username: str = None, active_tts_jobs: Dict[str, Any] = None) -> tuple[bool, str]:
    """
    Check if a message should be processed based on filtering settings.
    Returns (should_process, filtered_text)
    """
    filtering = settings.get("messageFiltering", {})
    
    if not filtering.get("enabled", True):
        return True, text
    
    # Skip ignored users
    if username and filtering.get("ignoredUsers"):
        ignored_users = filtering.get("ignoredUsers", [])
        # Case-insensitive comparison
        if any(username.lower() == ignored_user.lower() for ignored_user in ignored_users):
            logger.info(f"Skipping message from ignored user: {username}")
            return False, text
    
    # Skip commands if enabled (messages starting with ! or /)
    if filtering.get("skipCommands", True):
        stripped = text.strip()
        if stripped.startswith('!') or stripped.startswith('/'):
            logger.info(f"Skipping command message: {text[:50]}...")
            return False, text
    
    # Skip emote-only messages if enabled
    if filtering.get("skipEmotes", False):
        # Simple check for common emote patterns
        import re
        # Remove common emote patterns and whitespace
        clean_text = re.sub(r'\b\w+\d+\b', '', text)  # Remove emotes like PogChamp123
        clean_text = re.sub(r'[^\w\s]', '', clean_text)  # Remove special characters
        clean_text = clean_text.strip()
        
        if not clean_text:
            logger.info(f"Skipping emote-only message: {text[:50]}...")
            return False, text
    
    # Remove URLs if enabled
    filtered_text = text
    if filtering.get("removeUrls", True):
        import re
        # URL regex pattern that matches http/https, www, and common TLDs
        url_pattern = r'https?://[^\s]+|www\.[^\s]+|[^\s]+\.(com|org|net|edu|gov|mil|int|co|io|ly|me|tv|fm|gg|tk|ml|ga|cf)[^\s]*'
        original_length = len(filtered_text)
        filtered_text = re.sub(url_pattern, '', filtered_text, flags=re.IGNORECASE)
        filtered_text = re.sub(r'\s+', ' ', filtered_text).strip()  # Clean up extra spaces
        
        if len(filtered_text) != original_length:
            logger.info(f"Removed URLs from message: '{text[:50]}...' -> '{filtered_text[:50]}...'")
    
    # Apply profanity filter if enabled
    profanity_config = filtering.get("profanityFilter", {})
    if profanity_config.get("enabled", False):
        custom_words = profanity_config.get("customWords", [])
        replacement = profanity_config.get("replacement", "beep")
        
        if custom_words:
            import re
            original_text = filtered_text
            
            for word in custom_words:
                if not word.strip():
                    continue
                    
                # Escape special regex characters in the word
                escaped_word = re.escape(word.strip())
                
                # Full replacement with word boundaries for case-insensitive matching
                pattern = r'\b' + escaped_word + r'\b'
                filtered_text = re.sub(pattern, replacement, filtered_text, flags=re.IGNORECASE)
            
            if filtered_text != original_text:
                logger.info(f"Applied profanity filter: '{original_text[:50]}...' -> '{filtered_text[:50]}...'")
    
    # Check minimum length (after URL removal)
    min_length = filtering.get("minLength", 1)
    if len(filtered_text) < min_length:
        logger.info(f"Skipping message too short after filtering ({len(filtered_text)} < {min_length}): {filtered_text}")
        return False, filtered_text
    
    # Truncate if over maximum length
    max_length = filtering.get("maxLength", 500)
    if len(filtered_text) > max_length:
        truncated_text = filtered_text[:max_length].strip()
        # Try to end at a word boundary
        if ' ' in truncated_text:
            last_space = truncated_text.rfind(' ')
            if last_space > max_length * 0.8:  # Only use word boundary if it's not too short
                truncated_text = truncated_text[:last_space]
        
        logger.info(f"Truncating message from {len(filtered_text)} to {len(truncated_text)} characters")
        return True, truncated_text
    
    if filtering.get("ignoreIfUserSpeaking", False) and active_tts_jobs is not None:
        username_lower = username.lower()
        
        # Check if user has any active TTS jobs
        user_has_active_tts = username_lower in active_tts_jobs
        
        logger.info(f"🔍 User {username}: active_tts={user_has_active_tts}")
        
        if user_has_active_tts:
            logger.info(f"🚫 Ignoring new message from {username} - user already has active TTS (per-user queuing enabled)")
            logger.info(f"Ignored message from {username} due to active TTS: {filtered_text[:50]}...")
            return False, filtered_text

    # Check for spam (single user rate limiting)
    if username and filtering.get("enableSpamFilter", True):
        message_history = get_message_history()
        spam_threshold = filtering.get("spamThreshold", 5)
        spam_window = filtering.get("spamTimeWindow", 10)
        
        is_spam, reason = message_history.is_spam(
            username, 
            max_messages=spam_threshold, 
            time_window_seconds=spam_window
        )
        
        if is_spam:
            logger.info(f"Skipping spam message: {reason}")
            return False, filtered_text
    
    # Add message to history for rate limiting tracking (but not for duplicate detection)
    if username and filtering.get("enableSpamFilter", True):
        message_history = get_message_history()
        message_history.add_message(username, filtered_text)
    
    return True, filtered_text

# ---------- TTS Pipeline ----------

async def handle_test_voice_event(evt: Dict[str, Any]):
    """Handle test voice events - similar to handle_event but uses the provided test voice"""
    logger.info(f"🎵 Handling test voice event: {evt}")
    settings = app_get_settings()
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

    # Get TTS configuration - Use hybrid provider that handles all providers
    tts_config = settings.get("tts", {})
    
    # Get TTS provider configurations
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
        fallback_voices=[selected_voice],  # Use test voice as fallback
        google_api_key=google_api_key if google_api_key else None,
        polly_config=polly_config if polly_config.get("accessKey") and polly_config.get("secretKey") else None
    )
    
    # Create TTS job with the test voice
    job = TTSJob(text=evt.get('text', '').strip(), voice=selected_voice.voice_id, audio_format=audio_format)
    logger.info(f"Test TTS Job: text='{job.text}', voice='{selected_voice.name}' ({selected_voice.provider}:{selected_voice.voice_id}), format='{job.audio_format}'")

    # Fire-and-forget to allow overlap
    async def _run():
        try:
            logger.info(f"Starting test TTS synthesis...")
            path = await provider.synth(job)
            logger.info(f"Test TTS generated: {path}")
            
            # Broadcast to clients to play
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
            logger.info(f"Broadcasting test voice to {len(hub.clients)} clients: {payload}")
            await hub.broadcast(payload)
        except Exception as e:
            logger.info(f"Test TTS synthesis error: {e}")

    asyncio.create_task(_run())

async def handle_event(evt: Dict[str, Any]):
    logger.info(f"🎵 Handling event: {evt}")
    
    # Check if TTS is globally enabled
    if not tts_enabled:
        logger.info(f"🔇 TTS is disabled - skipping message from {evt.get('user', 'unknown')}")
        return
    
    settings = app_get_settings()
    
    # Apply message filtering
    original_text = evt.get('text', '').strip()
    username = evt.get('user', '')
    should_process, filtered_text = should_process_message(original_text, settings, username, active_tts_jobs)
    
    if not should_process:
        logger.info(f"Skipping message due to filtering: {original_text[:50]}... (user: {username})")
        return
    
    # Update event with filtered text before processing
    evt_filtered = evt.copy()
    evt_filtered['text'] = filtered_text
    
    # Process immediately - no queuing
    username = evt.get('user', 'unknown')
    logger.info(f"📬 Message received from {username}: processing immediately")
    if filtered_text != original_text:
        logger.info(f"🔧 Text after filtering: '{filtered_text}'")
    await process_tts_message(evt_filtered)
    return

async def process_tts_message(evt: Dict[str, Any]):
    """Process TTS message - voice selection, synthesis, and broadcast"""
    username = evt.get('user', 'unknown')
    username_lower = username.lower()
    
    # Track this job for cancellation
    task = asyncio.current_task()
    active_tts_jobs[username_lower] = {
        "task": task,
        "message": evt.get("text", "")
    }
    
    settings = app_get_settings()
    audio_format = settings.get("audioFormat", "mp3")
    special = settings.get("specialVoices", {})
    
    # Get enabled voices from database
    with Session(engine) as session:
        enabled_voices = session.exec(select(Voice).where(Voice.enabled == True)).all()
    
    if not enabled_voices:
        logger.info("No enabled voices found in database. Please add voices through the settings page.")
        return

    event_type = evt.get("eventType", "chat")
    # Select voice: special mapping else random
    selected_voice = None
    if event_type in special:
        vid = special[event_type].get("voiceId")
        # Try to find the voice by database ID
        selected_voice = next((v for v in enabled_voices if str(v.id) == str(vid)), None)
    
    if not selected_voice:
        # Random selection from enabled voices
        selected_voice = random.choice(enabled_voices)
        logger.info(f"🎲 Random voice selected: {selected_voice.name} ({selected_voice.provider})")
    else:
        logger.info(f"🎯 Special event voice selected: {selected_voice.name} ({selected_voice.provider})")
    
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
        
        # Broadcast to clients to play
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
            "eventType": event_type,
            "voice": voice_info,
            "audioUrl": f"/audio/{os.path.basename(path)}"
        }
        logger.info(f"Broadcasting to {len(hub.clients)} clients: {payload}")
        await hub.broadcast(payload)
        
        # Clean up - frontend handles playback independently
        if username_lower in active_tts_jobs:
            del active_tts_jobs[username_lower]
        logger.info(f"✅ TTS broadcast complete. Active users: {list(active_tts_jobs.keys())}")
            
    except asyncio.CancelledError:
        logger.info(f"TTS synthesis cancelled for user: {evt.get('user')}")
        if username_lower in active_tts_jobs:
            del active_tts_jobs[username_lower]
        logger.info(f"🧹 Cleaned up cancelled job. Remaining jobs: {len(active_tts_jobs)}")
        raise  # Re-raise to properly handle cancellation
    except Exception as e:
        logger.info(f"TTS Error: {e}")
        logger.error(f"TTS synthesis error for {username_lower}: {e}", exc_info=True)
        if username_lower in active_tts_jobs:
            del active_tts_jobs[username_lower]
        logger.info(f"🧹 Cleaned up failed job. Remaining jobs: {len(active_tts_jobs)}")

# ---------- Simulate messages (for local testing) ----------

async def handle_moderation_event(evt: Dict[str, Any]):
    """Handle Twitch moderation events (bans, timeouts)"""
    logger.info(f"🔨 Handling moderation event: {evt}")
    
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
        
        logger.info(f"✅ Processed {event_type} for user: {target_user} - TTS cancelled and audio stopped")
    else:
        logger.info(f"Unknown moderation event type: {event_type}")

# ---------- Twitch integration (optional) ----------
TwitchTask = None
try:
    from modules.twitch_listener import run_twitch_bot
    logger.info("Twitch listener imported successfully")
except Exception as e:
    logger.error(f"Failed to import twitch_listener: {e}")
    logger.info(f"❌ Failed to import Twitch listener: {e}")
    run_twitch_bot = None

@app.on_event("startup")
async def startup():
    logger.info("FastAPI startup event triggered")
    try:
        settings = app_get_settings()
        logger.info(f"Settings loaded, Twitch enabled: {settings.get('twitch', {}).get('enabled')}")
        
        if run_twitch_bot and settings.get("twitch", {}).get("enabled"):
            logger.info("Starting Twitch bot...")
            
            # Get OAuth token from database
            token_info = await get_twitch_token_for_bot()
            if not token_info:
                logger.warning("No Twitch OAuth token found. Please connect your Twitch account.")
                return
                
            twitch_config = settings.get("twitch", {})
            channel = twitch_config.get("channel") or token_info["username"]
            
            logger.info(f"Twitch config: channel={channel}, nick={token_info['username']}, token={'***' if token_info['token'] else 'None'}")
            
            # Event router to handle different event types
            async def route_twitch_event(e):
                event_type = e.get("type", "")
                if event_type == "moderation":
                    await handle_moderation_event(e)
                else:
                    # Default to chat event handler
                    await handle_event(e)
            
            global TwitchTask
            t = asyncio.create_task(run_twitch_bot(
                token=token_info["token"],
                nick=token_info["username"], 
                channel=channel,
                on_event=lambda e: asyncio.create_task(route_twitch_event(e))
            ))
            
            # Add error handler for the Twitch task
            def handle_twitch_task_exception(task):
                try:
                    task.result()
                except asyncio.CancelledError:
                    logger.info("Twitch bot task was cancelled")
                except Exception as e:
                    logger.error(f"Twitch bot task failed: {e}", exc_info=True)
                    logger.info(f"ERROR: Twitch bot task failed: {e}")
            
            t.add_done_callback(handle_twitch_task_exception)
            TwitchTask = t
            logger.info("Twitch bot task created")
        else:
            if not run_twitch_bot:
                logger.warning("Twitch bot not available (import failed)")
            else:
                logger.info("Twitch integration disabled in settings")
        

    except Exception as e:
        logger.error(f"Startup event failed: {e}", exc_info=True)
        logger.info(f"❌ Startup failed: {e}")

# Mount static files AFTER all API routes and WebSocket endpoints are defined
# This ensures that /api/* and /ws routes take precedence over static file serving
# Use static router's mount function for static files
from routers.static import mount_static_files
mount_static_files(app)

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 8000))
    debug_mode = os.environ.get('DEBUG', '').lower() in ('true', '1', 'yes', 'on')
    uvicorn.run("app:app", host=host, port=port, reload=debug_mode)