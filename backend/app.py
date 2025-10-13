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
last_selected_voice_id = None  # Track last voice to prevent consecutive repeats

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

# Avatar Slot Management System
# Manages which avatars are assigned to which slots and tracks their active status
avatar_slot_assignments = []  # List of slot objects with avatar assignments
active_avatar_slots = {}  # slot_id -> {"user": str, "start_time": float, "audio_url": str, "audio_duration": float}
avatar_message_queue = []  # Queue for messages when all slots are busy
avatar_assignments_generation_id = 0  # Increments when assignments are regenerated

def get_max_avatar_positions():
    """Calculate the maximum number of avatar positions from settings"""
    settings = get_settings()
    avatar_rows = settings.get("avatarRows", 2)
    avatar_row_config = settings.get("avatarRowConfig", [6, 6])
    # Sum up avatars across all configured rows
    max_positions = sum(avatar_row_config[:avatar_rows])
    return max_positions

def get_available_avatars():
    """Get all enabled avatar configurations from database"""
    from modules.models import AvatarImage
    
    try:
        with Session(engine) as session:
            # Get all enabled avatars from database
            avatars = session.exec(select(AvatarImage).where(AvatarImage.disabled == False)).all()
            
            if not avatars:
                # Fallback to default avatars if no managed avatars
                return [
                    {
                        "name": "Default Avatar 1",
                        "defaultImage": "/voice_avatars/ava.png",
                        "speakingImage": "/voice_avatars/ava.png",
                        "isSingleImage": True,
                        "spawn_position": None,
                        "voice_id": None
                    },
                    {
                        "name": "Default Avatar 2", 
                        "defaultImage": "/voice_avatars/liam.png",
                        "speakingImage": "/voice_avatars/liam.png",
                        "isSingleImage": True,
                        "spawn_position": None,
                        "voice_id": None
                    }
                ]
            
            # Group avatars by avatar_group_id or create single groups
            grouped = {}
            for avatar in avatars:
                key = avatar.avatar_group_id or f"single_{avatar.id}"
                if key not in grouped:
                    grouped[key] = {
                        "name": avatar.name,
                        "images": {},
                        "spawn_position": avatar.spawn_position,
                        "voice_id": avatar.voice_id
                    }
                else:
                    # Update spawn_position and voice_id if not null
                    if avatar.spawn_position is not None:
                        grouped[key]["spawn_position"] = avatar.spawn_position
                    if avatar.voice_id is not None:
                        grouped[key]["voice_id"] = avatar.voice_id
                
                # Ensure file path is properly formatted for frontend access
                file_path = avatar.file_path
                if not file_path.startswith('http') and not file_path.startswith('/'):
                    file_path = f"/{file_path}"
                grouped[key]["images"][avatar.avatar_type] = file_path
            
            # Convert to avatar objects
            avatar_groups = []
            for group in grouped.values():
                avatar_groups.append({
                    "name": group["name"],
                    "defaultImage": group["images"].get("default", group["images"].get("speaking", "/voice_avatars/ava.png")),
                    "speakingImage": group["images"].get("speaking", group["images"].get("default", "/voice_avatars/ava.png")),
                    "isSingleImage": not group["images"].get("speaking") or not group["images"].get("default") or group["images"].get("speaking") == group["images"].get("default"),
                    "spawn_position": group["spawn_position"],  # None = random, number = specific slot
                    "voice_id": group["voice_id"]  # None = random voice
                })
            
            return avatar_groups
            
    except Exception as e:
        logger.error(f"Failed to load avatars: {e}")
        # Return default avatars on error
        return [
            {
                "name": "Default Avatar 1",
                "defaultImage": "/voice_avatars/ava.png",
                "speakingImage": "/voice_avatars/ava.png", 
                "isSingleImage": True,
                "spawn_position": None,
                "voice_id": None
            }
        ]

def generate_avatar_slot_assignments():
    """Generate randomized avatar assignments for all slots based on settings"""
    global avatar_slot_assignments, avatar_assignments_generation_id
    
    settings = get_settings()
    avatar_rows = settings.get("avatarRows", 2)
    avatar_row_config = settings.get("avatarRowConfig", [6, 6])
    
    # Debug logging for settings
    logger.info(f"🔧 Avatar settings from backend: avatarRows={avatar_rows}, avatarRowConfig={avatar_row_config}")
    
    available_avatars = get_available_avatars()
    if not available_avatars:
        logger.warning("No avatars available for assignment")
        avatar_slot_assignments = []
        return
    
    total_slots = sum(avatar_row_config[:avatar_rows])
    logger.info(f"🎭 Generating avatar assignments for {total_slots} slots with {len(available_avatars)} avatars")
    logger.info(f"📸 Available avatars: {[{'name': a['name'], 'defaultImage': a['defaultImage'][:50] + '...' if len(a['defaultImage']) > 50 else a['defaultImage']} for a in available_avatars]}")
    
    assignments = []
    
    # Handle avatars with specific spawn positions first
    slot_index = 0
    slots = []
    
    # Create all slots first
    for row_index in range(avatar_rows):
        avatars_in_row = avatar_row_config[row_index] if row_index < len(avatar_row_config) else 6
        logger.debug(f"🔧 Creating row {row_index} with {avatars_in_row} avatars")
        for col_index in range(avatars_in_row):
            slots.append({
                "id": f"slot_{slot_index}",
                "row": row_index,
                "col": col_index,
                "totalInRow": avatars_in_row,
                "avatarData": None,  # Will be assigned
                "isActive": False
            })
            slot_index += 1
    
    logger.info(f"🔧 Total slots created: {len(slots)}")
    
    # First pass: Handle avatars with specific spawn positions
    assigned_slots = set()
    for avatar in available_avatars:
        if avatar["spawn_position"] is not None:
            spawn_pos = avatar["spawn_position"] - 1  # Convert to 0-based index
            if 0 <= spawn_pos < len(slots) and spawn_pos not in assigned_slots:
                slots[spawn_pos]["avatarData"] = avatar.copy()
                assigned_slots.add(spawn_pos)
                logger.info(f"🎯 Assigned {avatar['name']} to specific position {spawn_pos + 1}")
    
    # Second pass: Randomly assign remaining avatars to unassigned slots
    unassigned_slots = [i for i in range(len(slots)) if i not in assigned_slots]
    
    # Create assignment pool - ensure each avatar appears at least once if we have enough slots
    assignment_pool = []
    if len(unassigned_slots) >= len(available_avatars):
        # Add each avatar at least once
        assignment_pool.extend(available_avatars)
        # Fill remaining with random avatars
        remaining = len(unassigned_slots) - len(available_avatars)
        for _ in range(remaining):
            assignment_pool.append(random.choice(available_avatars))
    else:
        # More avatars than slots, randomly select
        for _ in range(len(unassigned_slots)):
            assignment_pool.append(random.choice(available_avatars))
    
    # Shuffle the assignment pool
    random.shuffle(assignment_pool)
    
    # Assign to unassigned slots
    for i, slot_idx in enumerate(unassigned_slots):
        if i < len(assignment_pool):
            slots[slot_idx]["avatarData"] = assignment_pool[i].copy()
            logger.info(f"🎲 Randomly assigned {assignment_pool[i]['name']} to slot {slot_idx}")
    
    avatar_slot_assignments = slots
    avatar_assignments_generation_id += 1
    
    logger.info(f"✅ Generated {len(avatar_slot_assignments)} avatar slot assignments (gen #{avatar_assignments_generation_id})")
    
    # Log a sample of what will be sent to frontend for debugging
    if avatar_slot_assignments:
        sample_slot = avatar_slot_assignments[0]
        logger.info(f"📤 Sample slot data being sent to frontend: {sample_slot}")
    
    # Broadcast new avatar assignments to all WebSocket clients
    import asyncio
    
    async def broadcast_avatar_slots():
        await hub.broadcast({
            "type": "avatar_slots_updated",
            "slots": avatar_slot_assignments,
            "generationId": avatar_assignments_generation_id
        })
        logger.info("Avatar slot assignments broadcasted to WebSocket clients")
    
    # Schedule the broadcast if we're in an async context, or run in background
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcast_avatar_slots())
    except RuntimeError:
        # If no event loop is running, create one for this broadcast
        asyncio.run(broadcast_avatar_slots())
    
    return avatar_slot_assignments

def get_audio_duration(file_path: str) -> float:
    """
    Get the duration of an audio file in seconds.
    Returns the duration if successful, or None if it fails.
    """
    try:
        # Try using mutagen library for MP3 files (most common)
        try:
            from mutagen.mp3 import MP3
            audio = MP3(file_path)
            duration = audio.info.length
            logger.info(f"📏 Audio duration for {os.path.basename(file_path)}: {duration:.2f}s (mutagen)")
            return duration
        except ImportError:
            # mutagen not installed, try alternative method
            pass
        except Exception as e:
            logger.debug(f"Failed to get duration with mutagen: {e}")
        
        # Fallback: try to estimate from file size (very rough approximation)
        # MP3 bitrate is typically 128-320 kbps, we'll assume 192 kbps average
        try:
            file_size = os.path.getsize(file_path)
            # 192 kbps = 24 KB/s
            estimated_duration = file_size / (24 * 1024)
            logger.info(f"📏 Audio duration estimated for {os.path.basename(file_path)}: ~{estimated_duration:.2f}s (file size)")
            return estimated_duration
        except Exception as e:
            logger.debug(f"Failed to estimate duration from file size: {e}")
        
        return None
        
    except Exception as e:
        logger.warning(f"Failed to get audio duration: {e}")
        return None

def find_available_slot_for_tts(voice_id=None, user=None):
    """Find the best available slot for TTS based on voice matching and availability"""
    global active_avatar_slots
    
    if not avatar_slot_assignments:
        logger.warning("No avatar slot assignments available")
        return None
    
    # Get current timestamp for cleanup
    current_time = time.time()
    
    # Clean up expired active slots (safety mechanism in case frontend doesn't report end)
    expired_slots = []
    for slot_id, slot_info in active_avatar_slots.items():
        # Use audio duration + 5 second buffer, or fallback to 30 seconds if duration unknown
        audio_duration = slot_info.get("audio_duration", 30)
        expiry_time = audio_duration + 5  # Add 5 second buffer for network/processing delays
        if current_time - slot_info.get("start_time", 0) > expiry_time:
            expired_slots.append(slot_id)
            logger.info(f"🕐 Slot {slot_id} expired after {expiry_time}s (audio: {audio_duration}s + 5s buffer)")
    
    for slot_id in expired_slots:
        logger.info(f"🧹 Cleaning up expired active slot: {slot_id}")
        del active_avatar_slots[slot_id]
    
    # Find slots that match the voice_id if specified
    matching_slots = []
    available_slots = []
    
    for slot in avatar_slot_assignments:
        slot_id = slot["id"]
        avatar_data = slot["avatarData"]
        
        is_active = slot_id in active_avatar_slots
        
        if not is_active:
            available_slots.append(slot)
            
            # Check if this avatar matches the voice_id
            if voice_id and avatar_data and avatar_data.get("voice_id") == voice_id:
                matching_slots.append(slot)
    
    # Prefer voice-matched slots if available
    if matching_slots:
        selected_slot = random.choice(matching_slots)
        logger.info(f"🎯 Selected voice-matched slot {selected_slot['id']} for voice {voice_id}")
        return selected_slot
    
    # Use any available slot
    if available_slots:
        selected_slot = random.choice(available_slots)
        logger.info(f"🎲 Selected random available slot {selected_slot['id']} (no voice match)")
        return selected_slot
    
    # No available slots
    logger.info("⏳ All avatar slots are busy, message will be queued")
    return None

def reserve_avatar_slot(slot_id, user, audio_url, audio_duration=None):
    """Reserve an avatar slot for TTS playback"""
    global active_avatar_slots
    
    active_avatar_slots[slot_id] = {
        "user": user,
        "start_time": time.time(),
        "audio_url": audio_url,
        "audio_duration": audio_duration or 30  # Default to 30s if duration not provided
    }
    duration_info = f" (duration: {audio_duration}s)" if audio_duration else " (duration: unknown, using 30s default)"
    logger.info(f"🔒 Reserved slot {slot_id} for user {user}{duration_info} (active slots: {len(active_avatar_slots)})")

def release_avatar_slot(slot_id):
    """Release an avatar slot when TTS playback ends"""
    global active_avatar_slots
    
    if slot_id in active_avatar_slots:
        user = active_avatar_slots[slot_id]["user"]
        del active_avatar_slots[slot_id]
        logger.info(f"🔓 Released slot {slot_id} for user {user} (active slots: {len(active_avatar_slots)})")
        
        # Process queue if there are waiting messages
        process_avatar_message_queue()
    else:
        logger.warning(f"Attempted to release slot {slot_id} that wasn't reserved")

def queue_avatar_message(message_data):
    """Add a message to the avatar queue when all slots are busy"""
    global avatar_message_queue
    
    avatar_message_queue.append({
        "message_data": message_data,
        "queued_time": time.time()
    })
    logger.info(f"📥 Queued message for {message_data.get('user')} (queue length: {len(avatar_message_queue)})")

def process_avatar_message_queue():
    """Process queued messages if slots become available"""
    global avatar_message_queue
    
    if not avatar_message_queue:
        return
    
    # Try to process the oldest queued message
    queued_item = avatar_message_queue[0]
    message_data = queued_item["message_data"]
    
    # Check if message is too old (ignore messages older than 60 seconds)
    if time.time() - queued_item["queued_time"] > 60:
        avatar_message_queue.pop(0)
        logger.info(f"🗑️ Discarded old queued message for {message_data.get('user')}")
        # Try to process next message
        if avatar_message_queue:
            process_avatar_message_queue()
        return
    
    # Try to find an available slot
    voice_id = message_data.get("voice", {}).get("id") if message_data.get("voice") else None
    available_slot = find_available_slot_for_tts(voice_id, message_data.get("user"))
    
    if available_slot:
        # Remove from queue and process
        avatar_message_queue.pop(0)
        logger.info(f"📤 Processing queued message for {message_data.get('user')} in slot {available_slot['id']}")
        
        # Process the queued TTS message
        asyncio.create_task(process_queued_tts_message(message_data, available_slot))

async def process_queued_tts_message(message_data, target_slot):
    """Process a TTS message that was queued due to all slots being busy"""
    try:
        # Reserve the slot
        audio_url = message_data.get("audioUrl", "")
        user = message_data.get("user", "")
        
        # Try to get audio duration from the file
        audio_duration = None
        if audio_url:
            audio_filename = os.path.basename(audio_url)
            audio_path = os.path.join(AUDIO_DIR, audio_filename)
            if os.path.exists(audio_path):
                audio_duration = get_audio_duration(audio_path)
        
        reserve_avatar_slot(target_slot["id"], user, audio_url, audio_duration)
        
        # Add slot information to the message
        enriched_message = message_data.copy()
        enriched_message.update({
            "targetSlot": {
                "id": target_slot["id"],
                "row": target_slot["row"],
                "col": target_slot["col"],
                "totalInRow": target_slot["totalInRow"]
            },
            "avatarData": target_slot["avatarData"],
            "assignmentGeneration": avatar_assignments_generation_id
        })
        
        # Broadcast to clients
        await hub.broadcast(enriched_message)
        logger.info(f"📡 Broadcasted queued TTS for {user} in slot {target_slot['id']}")
        
    except Exception as e:
        logger.error(f"Failed to process queued TTS message: {e}")
        # Release the slot on error
        release_avatar_slot(target_slot["id"])

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

# Initialize avatar slot assignments on startup
logger.info("Initializing avatar slot assignments...")
generate_avatar_slot_assignments()
logger.info(f"Avatar slot management initialized with {len(avatar_slot_assignments)} slots")

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
            # Handle messages from frontend (avatar slot status updates, etc.)
            message = await ws.receive_text()
            logger.debug(f"WebSocket received message from {client_info}: {message}")
            
            try:
                data = json.loads(message)
                await handle_websocket_message(data)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from WebSocket: {message}")
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected from {client_info}. Remaining clients: {len(hub.clients)-1}")
        logger.info(f"WebSocket disconnected. Remaining clients: {len(hub.clients)-1}")
        hub.unregister(ws)
    except Exception as e:
        logger.error(f"WebSocket error from {client_info}: {e}")
        logger.info(f"WebSocket error: {e}")
        hub.unregister(ws)

async def handle_websocket_message(data: Dict[str, Any]):
    """Handle incoming WebSocket messages from frontend"""
    message_type = data.get("type", "")
    
    if message_type == "avatar_slot_ended":
        # Frontend reports that an avatar slot has finished playing
        slot_id = data.get("slot_id")
        if slot_id:
            release_avatar_slot(slot_id)
            logger.info(f"🔓 Avatar slot {slot_id} released by frontend")
    
    elif message_type == "avatar_slot_error":
        # Frontend reports an error with avatar slot playback
        slot_id = data.get("slot_id")
        if slot_id:
            release_avatar_slot(slot_id)
            logger.info(f"❌ Avatar slot {slot_id} released due to frontend error")
    
    elif message_type == "request_avatar_slots":
        # Frontend requests current avatar slot assignments (for page refresh)
        logger.info(f"📋 Frontend requested avatar slots - sending {len(avatar_slot_assignments)} slots")
        response = {
            "type": "avatar_slots_updated",
            "slots": avatar_slot_assignments,
            "assignmentGeneration": avatar_assignments_generation_id,
            "activeSlots": list(active_avatar_slots.keys()),
            "queueLength": len(avatar_message_queue)
        }
        # Send only to the requesting client (would need to track client in real implementation)
        # For now, broadcast to all clients
        await hub.broadcast(response)
        logger.info(f"📡 Sent avatar slots update to frontend: {len(avatar_slot_assignments)} slots (gen #{avatar_assignments_generation_id})")
    
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
    
    # Update global TTS state from settings (but don't call stop/resume here)
    # The toggle endpoint handles the actual stop/resume logic
    # This just ensures the tts_enabled flag stays in sync with saved settings
    global tts_enabled
    tts_control = data.get("ttsControl", {})
    new_tts_enabled = tts_control.get("enabled", True)
    tts_enabled = new_tts_enabled
    
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
            
            # Regenerate avatar assignments if layout changed
            if avatar_layout_changed:
                logger.info("🎭 Avatar layout settings changed, regenerating slot assignments...")
                # Clear active slots and queue to avoid conflicts
                global active_avatar_slots, avatar_message_queue
                active_avatar_slots.clear()
                avatar_message_queue.clear()
                
                # Regenerate assignments
                generate_avatar_slot_assignments()
                
                # Broadcast avatar slot update
                asyncio.create_task(hub.broadcast({
                    "type": "avatar_slots_updated",
                    "slots": avatar_slot_assignments,
                    "assignmentGeneration": avatar_assignments_generation_id,
                    "message": "Avatar layout updated"
                }))
            
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
        with Session(engine) as s:
            row = s.exec(select(Setting).where(Setting.key == "settings")).first()
            if row:
                row.value_json = json.dumps(settings)
                s.add(row)
                s.commit()
                logger.info(f"💾 TTS state saved to database: {new_state}")
    except Exception as e:
        logger.error(f"Failed to save TTS state to database: {e}")
    
    return new_state

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
        # Random selection from enabled voices, avoiding last selected voice if possible
        global last_selected_voice_id
        
        # If we have more than 2 voices, avoid selecting the same voice as last time
        if len(enabled_voices) >= 2 and last_selected_voice_id is not None:
            available_voices = [v for v in enabled_voices if v.id != last_selected_voice_id]
            if available_voices:
                selected_voice = random.choice(available_voices)
                logger.info(f"🎲 Random voice selected (avoiding last voice): {selected_voice.name} ({selected_voice.provider})")
            else:
                # Fallback if filtering didn't work
                selected_voice = random.choice(enabled_voices)
                logger.info(f"🎲 Random voice selected (fallback): {selected_voice.name} ({selected_voice.provider})")
        else:
            # Not enough voices to avoid repetition, or no last voice tracked
            selected_voice = random.choice(enabled_voices)
            logger.info(f"🎲 Random voice selected: {selected_voice.name} ({selected_voice.provider})")
        
        # Update last selected voice
        last_selected_voice_id = selected_voice.id
    else:
        logger.info(f"🎯 Special event voice selected: {selected_voice.name} ({selected_voice.provider})")
        # Don't update last_selected_voice_id for special events, so they don't affect the pattern
    
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
            logger.info(f"🎚️ Audio filters applied: {path} (new duration: {audio_duration:.2f}s)")
        else:
            # Get audio duration for accurate slot timeout (no filters applied)
            audio_duration = get_audio_duration(path)
        
        # Find available avatar slot for this TTS
        voice_id = selected_voice.id
        target_slot = find_available_slot_for_tts(voice_id, username)
        
        audio_url = f"/audio/{os.path.basename(path)}"
        
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
                    "row": target_slot["row"],
                    "col": target_slot["col"],
                    "totalInRow": target_slot["totalInRow"]
                },
                "avatarData": target_slot["avatarData"],
                "assignmentGeneration": avatar_assignments_generation_id
            })
            
            logger.info(f"📡 Broadcasting TTS with slot {target_slot['id']} to {len(hub.clients)} clients")
            await hub.broadcast(enhanced_payload)
        else:
            # No slots available - queue the message
            logger.info(f"⏳ All slots busy, queuing TTS for {username}")
            queue_avatar_message(base_payload)
            
            # Still broadcast a notification that the message is queued
            queue_notification = {
                "type": "tts_queued",
                "user": evt.get("user"),
                "message": evt.get("text"),
                "queuePosition": len(avatar_message_queue)
            }
            await hub.broadcast(queue_notification)
        
        # Clean up TTS job tracking
        if username_lower in active_tts_jobs:
            del active_tts_jobs[username_lower]
        logger.info(f"✅ TTS processing complete. Active TTS jobs: {list(active_tts_jobs.keys())}")
            
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

# ---------- Avatar Slot Management API ----------

@app.get("/api/avatar-slots")
async def api_get_avatar_slots():
    """Get current avatar slot assignments and active status"""
    try:
        slots_with_status = []
        for slot in avatar_slot_assignments:
            slot_data = slot.copy()
            slot_data["isActive"] = slot["id"] in active_avatar_slots
            if slot_data["isActive"]:
                active_info = active_avatar_slots[slot["id"]]
                slot_data["activeUser"] = active_info["user"]
                slot_data["activeSince"] = active_info["start_time"]
            slots_with_status.append(slot_data)
        
        return {
            "slots": slots_with_status,
            "assignmentGeneration": avatar_assignments_generation_id,
            "queueLength": len(avatar_message_queue),
            "activeSlots": len(active_avatar_slots)
        }
    except Exception as e:
        logger.error(f"Failed to get avatar slots: {e}")
        return {"slots": [], "assignmentGeneration": 0, "queueLength": 0, "activeSlots": 0}

@app.post("/api/avatar-slots/regenerate")
async def api_regenerate_avatar_slots():
    """Force regeneration of avatar slot assignments"""
    try:
        # Clear any active slots to avoid conflicts
        global active_avatar_slots, avatar_message_queue
        active_avatar_slots.clear()
        avatar_message_queue.clear()
        
        # Regenerate assignments
        generate_avatar_slot_assignments()
        
        # Broadcast to all clients to update their assignments
        await hub.broadcast({
            "type": "avatar_slots_updated",
            "slots": avatar_slot_assignments,
            "assignmentGeneration": avatar_assignments_generation_id
        })
        
        logger.info(f"🎲 Avatar slots regenerated (generation #{avatar_assignments_generation_id})")
        
        return {
            "success": True,
            "slots": avatar_slot_assignments,
            "assignmentGeneration": avatar_assignments_generation_id,
            "message": "Avatar slots regenerated"
        }
    except Exception as e:
        logger.error(f"Failed to regenerate avatar slots: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/avatar-slots/{slot_id}/release")
async def api_release_avatar_slot(slot_id: str):
    """Manually release an avatar slot (for debugging/management)"""
    try:
        if slot_id in active_avatar_slots:
            user = active_avatar_slots[slot_id]["user"]
            release_avatar_slot(slot_id)
            return {
                "success": True,
                "message": f"Released slot {slot_id} (was used by {user})"
            }
        else:
            return {
                "success": False,
                "message": f"Slot {slot_id} was not active"
            }
    except Exception as e:
        logger.error(f"Failed to release slot {slot_id}: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/avatar-slots/queue")
async def api_get_avatar_queue():
    """Get current avatar message queue status"""
    try:
        queue_info = []
        for i, item in enumerate(avatar_message_queue):
            queue_info.append({
                "position": i + 1,
                "user": item["message_data"].get("user", "unknown"),
                "text": item["message_data"].get("text", "")[:50] + "..." if len(item["message_data"].get("text", "")) > 50 else item["message_data"].get("text", ""),
                "queued_time": item["queued_time"],
                "wait_time": time.time() - item["queued_time"]
            })
        
        return {
            "queue": queue_info,
            "length": len(avatar_message_queue),
            "active_slots": len(active_avatar_slots),
            "total_slots": len(avatar_slot_assignments)
        }
    except Exception as e:
        logger.error(f"Failed to get avatar queue: {e}")
        return {"queue": [], "length": 0, "active_slots": 0, "total_slots": 0}

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