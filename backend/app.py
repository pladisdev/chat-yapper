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
import secrets
import urllib.parse

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()  # Load .env file from current directory or parent directories

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, Form, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Session, select, create_engine

from models import Setting, Voice, AvatarImage, TwitchAuth
from tts import get_provider, get_hybrid_provider, TTSJob
from message_filter import get_message_history

def is_executable():
    """
    Detect if we're running as a PyInstaller executable.
    Returns True if running from .exe, False if running from source.
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# TTS Cancellation System:
# - Tracks active TTS jobs by username in active_tts_jobs dict
# - Detects Twitch ban/timeout events via CLEARCHAT IRC messages
# - Cancels ongoing TTS synthesis and removes from queue for banned/timed-out users
# - Provides API endpoints for manual testing and management

# Set up backend logging
def setup_backend_logging():
    """Set up logging for the backend"""
    # Create logs directory
    logs_dir = Path("../logs") if Path("../logs").exists() else Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = logs_dir / f"backend_{timestamp}.log"
    
    # Configure logging for this module
    backend_logger = logging.getLogger('ChatYapper.Backend')
    backend_logger.setLevel(logging.INFO)
    
    # Only add handlers if not already configured
    if not backend_logger.handlers:
        # File handler - logs everything
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        
        # Console handler - adjust level based on environment
        console_handler = logging.StreamHandler()
        if is_executable():
            # Production (.exe) - only show errors
            console_handler.setLevel(logging.ERROR)
            backend_logger.info("Production mode detected (.exe) - console logging set to ERROR level only")
        else:
            # Development - show warnings and errors
            console_handler.setLevel(logging.WARNING)
            backend_logger.info("Development mode detected - console logging set to WARNING level")
        
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        
        # Add handlers
        backend_logger.addHandler(file_handler)
        backend_logger.addHandler(console_handler)
    
    backend_logger.info(f"Backend logging initialized - log file: {log_filename}")
    return backend_logger

# Initialize backend logging
logger = setup_backend_logging()

def log_important(message):
    """Log important messages that should appear in both console and file"""
    logger.warning(f"IMPORTANT: {message}")  # WARNING level ensures console output

# Twitch OAuth Configuration
# For Twitch Developer Console, set redirect URL to: http://localhost:{PORT}/auth/twitch/callback
TWITCH_CLIENT_ID = os.environ.get("TWITCH_CLIENT_ID", "")
TWITCH_CLIENT_SECRET = os.environ.get("TWITCH_CLIENT_SECRET", "")
TWITCH_REDIRECT_URI = f"http://localhost:{os.environ.get('PORT', 8000)}/auth/twitch/callback"
TWITCH_SCOPE = "chat:read"  # Permissions needed

# OAuth state tracking to prevent CSRF attacks
oauth_states = {}  # state -> user session info

# Configuration validation and logging
if TWITCH_CLIENT_ID:
    logger.info(f"✅ Twitch OAuth configured - Client ID: {TWITCH_CLIENT_ID[:8]}... (masked)")
else:
    logger.warning("⚠️  Twitch Client ID not configured!")
    logger.warning("   💡 Create a .env file with TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET")
    logger.warning("   💡 See .env.example for template")
    logger.warning("   💡 Or set environment variables directly")

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
    settings = get_settings()
    avatar_rows = settings.get("avatarRows", 2)
    avatar_row_config = settings.get("avatarRowConfig", [6, 6])
    # Sum up avatars across all configured rows
    max_positions = sum(avatar_row_config[:avatar_rows])
    return max_positions

# Create a persistent directory for user-uploaded avatars
# This will be in the user's AppData/Local/ChatYapper directory
import tempfile
import getpass

def get_user_data_dir():
    """Get a persistent directory for user data"""
    if os.name == 'nt':  # Windows
        base_dir = os.path.join(os.environ.get('LOCALAPPDATA', tempfile.gettempdir()), 'ChatYapper')
    else:  # Linux/Mac
        base_dir = os.path.join(os.path.expanduser('~'), '.chatyapper')
    
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

# ---------- Config & DB ----------
# Use persistent user data directory for database (same as avatars)
USER_DATA_DIR = get_user_data_dir()
DB_PATH = os.environ.get("DB_PATH", os.path.join(USER_DATA_DIR, "app.db"))
logger.info(f"Database path: {DB_PATH}")
logger.info(f"User data directory: {USER_DATA_DIR}")

# Run database migrations BEFORE creating engine and tables
# This ensures old databases are updated to the new schema
try:
    from db_migration import run_all_migrations, get_database_info
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

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
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

# Serve generated audio files under /audio
AUDIO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "audio"))
os.makedirs(AUDIO_DIR, exist_ok=True)
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

# ---------- Settings CRUD ----------

def get_settings() -> Dict[str, Any]:
    with Session(engine) as s:
        row = s.exec(select(Setting).where(Setting.key == "settings")).first()
        if row:
            settings = json.loads(row.value_json)
            logger.info(f"Loaded settings from database: {DB_PATH}")
            
            # Initialize global TTS state from settings
            global tts_enabled
            tts_control = settings.get("ttsControl", {})
            tts_enabled = tts_control.get("enabled", True)
            
            return settings
        else:
            logger.error("No settings found in database!")
            return {}

def save_settings(data: Dict[str, Any]):
    with Session(engine) as s:
        row = s.exec(select(Setting).where(Setting.key == "settings")).first()
        if row:
            row.value_json = json.dumps(data)
            s.add(row)
            s.commit()
            logger.info(f"Settings saved to database: {DB_PATH}")
            
            # Update global TTS state from settings
            global tts_enabled
            tts_control = data.get("ttsControl", {})
            new_tts_enabled = tts_control.get("enabled", True)
            
            if new_tts_enabled != tts_enabled:
                if new_tts_enabled:
                    resume_all_tts()
                else:
                    stop_all_tts()
            
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

# Twitch OAuth Endpoints

@app.get("/auth/twitch")
async def twitch_auth_start():
    """Start Twitch OAuth flow"""
    # Check if Twitch credentials are configured
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        logger.warning("Twitch OAuth attempted but credentials not configured")
        return RedirectResponse(url="/settings?error=twitch_not_configured")
    
    # Generate a random state to prevent CSRF attacks
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {"timestamp": time.time()}
    
    # Build Twitch OAuth URL
    params = {
        "client_id": TWITCH_CLIENT_ID,
        "redirect_uri": TWITCH_REDIRECT_URI,
        "response_type": "code",
        "scope": TWITCH_SCOPE,
        "state": state
    }
    
    auth_url = "https://id.twitch.tv/oauth2/authorize?" + urllib.parse.urlencode(params)
    logger.info(f"Starting Twitch OAuth flow with state: {state}")
    
    return RedirectResponse(url=auth_url)

@app.get("/auth/twitch/callback")
async def twitch_auth_callback(code: str = None, state: str = None, error: str = None):
    """Handle Twitch OAuth callback"""
    try:
        # Check for OAuth errors
        if error:
            logger.error(f"Twitch OAuth error: {error}")
            return RedirectResponse(url="/?error=oauth_denied")
        
        if not code or not state:
            logger.error("Missing code or state in OAuth callback")
            return RedirectResponse(url="/?error=invalid_callback")
        
        # Verify state to prevent CSRF
        if state not in oauth_states:
            logger.error(f"Invalid OAuth state: {state}")
            return RedirectResponse(url="/?error=invalid_state")
        
        # Clean up used state
        del oauth_states[state]
        
        # Exchange code for access token
        token_data = await exchange_code_for_token(code)
        if not token_data:
            return RedirectResponse(url="/?error=token_exchange_failed")
        
        # Get user information
        user_info = await get_twitch_user_info(token_data["access_token"])
        if not user_info:
            return RedirectResponse(url="/?error=user_info_failed")
        
        # Store auth in database
        await store_twitch_auth(user_info, token_data)
        
        logger.info(f"Successfully connected Twitch account: {user_info['login']}")
        return RedirectResponse(url="/settings?twitch=connected")
        
    except Exception as e:
        logger.error(f"Error in Twitch OAuth callback: {e}", exc_info=True)
        return RedirectResponse(url="/?error=callback_error")

@app.get("/api/twitch/status")
async def twitch_auth_status():
    """Get current Twitch connection status"""
    try:
        with Session(engine) as session:
            auth = session.exec(select(TwitchAuth)).first()
            if auth:
                return {
                    "connected": True,
                    "username": auth.username,
                    "display_name": auth.display_name,
                    "user_id": auth.twitch_user_id
                }
            return {"connected": False}
    except Exception as e:
        logger.error(f"Error checking Twitch status: {e}")
        return {"connected": False, "error": str(e)}

@app.delete("/api/twitch/disconnect")
async def twitch_disconnect():
    """Disconnect Twitch account"""
    try:
        with Session(engine) as session:
            auth = session.exec(select(TwitchAuth)).first()
            if auth:
                session.delete(auth)
                session.commit()
                logger.info("Twitch account disconnected")
                return {"success": True}
            return {"success": False, "error": "No connection found"}
    except Exception as e:
        logger.error(f"Error disconnecting Twitch: {e}")
        return {"success": False, "error": str(e)}

# Helper functions for OAuth

async def exchange_code_for_token(code: str) -> Dict[str, Any]:
    """Exchange OAuth code for access token"""
    try:
        data = {
            "client_id": TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": TWITCH_REDIRECT_URI
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post("https://id.twitch.tv/oauth2/token", data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info("Successfully exchanged code for token")
                    return result
                else:
                    logger.error(f"Token exchange failed: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error exchanging code for token: {e}")
        return None

async def get_twitch_user_info(access_token: str) -> Dict[str, Any]:
    """Get user info from Twitch API"""
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Client-Id": TWITCH_CLIENT_ID
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.twitch.tv/helix/users", headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    users = result.get("data", [])
                    if users:
                        return users[0]
                    logger.error("No user data returned from Twitch API")
                    return None
                else:
                    logger.error(f"User info request failed: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        return None

async def store_twitch_auth(user_info: Dict[str, Any], token_data: Dict[str, Any]):
    """Store Twitch auth in database"""
    try:
        with Session(engine) as session:
            # Check if auth already exists for this user
            existing_auth = session.exec(
                select(TwitchAuth).where(TwitchAuth.twitch_user_id == user_info["id"])
            ).first()
            
            if existing_auth:
                # Update existing auth
                existing_auth.access_token = token_data["access_token"]
                existing_auth.refresh_token = token_data.get("refresh_token", "")
                existing_auth.username = user_info["login"]
                existing_auth.display_name = user_info["display_name"]
                existing_auth.updated_at = datetime.now().isoformat()
                if "expires_in" in token_data:
                    expires_at = datetime.now().timestamp() + token_data["expires_in"]
                    existing_auth.expires_at = datetime.fromtimestamp(expires_at).isoformat()
            else:
                # Create new auth
                expires_at = None
                if "expires_in" in token_data:
                    expires_at = datetime.fromtimestamp(
                        datetime.now().timestamp() + token_data["expires_in"]
                    ).isoformat()
                
                new_auth = TwitchAuth(
                    twitch_user_id=user_info["id"],
                    username=user_info["login"],
                    display_name=user_info["display_name"],
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token", ""),
                    expires_at=expires_at,
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat()
                )
                session.add(new_auth)
            
            session.commit()
            logger.info(f"Stored Twitch auth for user: {user_info['login']}")
            
    except Exception as e:
        logger.error(f"Error storing Twitch auth: {e}")
        raise

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



@app.get("/api/settings")
async def api_get_settings():
    logger.info("API: GET /api/settings called")
    settings = get_settings()
    logger.info(f"API: Returning settings: {len(json.dumps(settings))} characters")
    return settings

@app.post("/api/settings")
async def api_set_settings(payload: Dict[str, Any]):
    logger.info("API: POST /api/settings called")
    save_settings(payload)
    logger.info("Settings saved successfully")
    return {"ok": True}

@app.get("/api/status")
async def api_get_status():
    """Simple status check endpoint"""
    logger.info("API: GET /api/status called")
    status = {
        "status": "running",
        "websocket_clients": len(hub.clients),
        "message": "Chat Yapper backend is running!"
    }
    logger.info(f"API: Returning status: {status}")
    return status

@app.get("/api/test")
async def api_test():
    """Simple test endpoint for debugging"""
    logger.info("API: GET /api/test called - React app is working!")
    return {"success": True, "message": "API connection successful"}

@app.get("/api/avatars")
async def api_get_avatars():
    """Return list of available avatar images from both built-in and user-uploaded"""
    avatar_files = []
    valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
    
    # Get built-in avatars from the static directory
    builtin_avatars_dir = os.path.join(PUBLIC_DIR, "voice_avatars")
    if os.path.exists(builtin_avatars_dir):
        try:
            for filename in os.listdir(builtin_avatars_dir):
                if any(filename.lower().endswith(ext) for ext in valid_extensions):
                    avatar_files.append(f"/voice_avatars/{filename}")
        except Exception as e:
            logger.info(f"Error reading built-in avatars: {e}")
    
    # Get user-uploaded avatars from the persistent directory
    if os.path.exists(PERSISTENT_AVATARS_DIR):
        try:
            for filename in os.listdir(PERSISTENT_AVATARS_DIR):
                if any(filename.lower().endswith(ext) for ext in valid_extensions):
                    avatar_files.append(f"/user_avatars/{filename}")
        except Exception as e:
            logger.info(f"Error reading user avatars: {e}")
    
    # Sort for consistent ordering
    avatar_files.sort()
    return {"avatars": avatar_files}

@app.post("/api/avatars/upload")
async def api_upload_avatar(file: UploadFile, avatar_name: str = Form(...), avatar_type: str = Form("default"), avatar_group_id: str = Form(None)):
    """Upload a new avatar image"""
    logger.info(f"API: POST /api/avatars/upload called - name: {avatar_name}, type: {avatar_type}, group: {avatar_group_id}")
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            logger.error(f"Invalid file type uploaded: {file.content_type}")
            return {"error": "File must be an image", "success": False}
        
        # Validate file size (max 5MB)
        if file.size and file.size > 5 * 1024 * 1024:
            return {"error": "File size must be less than 5MB", "success": False}
        
        # Check for existing avatar with same name and type for replacement
        existing_avatar = None
        with Session(engine) as session:
            query = select(AvatarImage).where(
                AvatarImage.name == avatar_name,
                AvatarImage.avatar_type == avatar_type
            )
            existing_avatar = session.exec(query).first()
        
        # Use the persistent avatars directory for uploads
        avatars_dir = PERSISTENT_AVATARS_DIR
        logger.info(f"Saving avatar to persistent directory: {avatars_dir}")
        
        # Generate unique filename or reuse existing if replacing
        import uuid
        from pathlib import Path
        file_extension = Path(file.filename or "image.png").suffix
        
        if existing_avatar:
            # Replace existing avatar - reuse filename
            unique_filename = existing_avatar.filename
            file_path = os.path.join(avatars_dir, unique_filename)
        else:
            # New avatar - generate unique filename
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(avatars_dir, unique_filename)
        
        # Read and process image
        content = await file.read()
        
        # Resize image if larger than 200px on any side
        try:
            from PIL import Image
            import io
            
            # Open image from bytes
            image = Image.open(io.BytesIO(content))
            
            # Calculate new size maintaining aspect ratio
            max_size = 200
            if image.width > max_size or image.height > max_size:
                # Calculate resize dimensions
                ratio = min(max_size / image.width, max_size / image.height)
                new_width = int(image.width * ratio)
                new_height = int(image.height * ratio)
                
                # Resize image
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert back to bytes
                output = io.BytesIO()
                # Preserve original format, default to PNG if unknown
                format = image.format or 'PNG'
                if format not in ['JPEG', 'PNG', 'GIF', 'WEBP']:
                    format = 'PNG'
                image.save(output, format=format, optimize=True, quality=85)
                content = output.getvalue()
            
        except ImportError:
            # Pillow not available, skip resizing
            pass
        except Exception as e:
            logger.info(f"Warning: Failed to resize image: {e}")
            # Continue with original image
        
        # Save processed file
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Save to database (update existing or create new)
        with Session(engine) as session:
            if existing_avatar:
                # Update existing avatar
                existing_avatar.upload_date = str(int(time.time()))
                existing_avatar.file_size = len(content)
                existing_avatar.avatar_group_id = avatar_group_id or existing_avatar.avatar_group_id
                session.add(existing_avatar)
                session.commit()
                session.refresh(existing_avatar)
                avatar = existing_avatar
            else:
                # Create new avatar
                avatar = AvatarImage(
                    name=avatar_name,
                    filename=unique_filename,
                    file_path=f"/user_avatars/{unique_filename}",
                    upload_date=str(int(time.time())),
                    file_size=len(content),
                    avatar_type=avatar_type,
                    avatar_group_id=avatar_group_id
                )
                session.add(avatar)
                session.commit()
                session.refresh(avatar)
        
        # Broadcast refresh message to all connected clients
        asyncio.create_task(hub.broadcast({
            "type": "avatar_updated",
            "message": f"Avatar '{avatar.name}' uploaded"
        }))
        
        return {
            "success": True, 
            "avatar": {
                "id": avatar.id,
                "name": avatar.name,
                "filename": avatar.filename,
                "file_path": avatar.file_path,
                "file_size": avatar.file_size,
                "avatar_type": avatar.avatar_type,
                "avatar_group_id": avatar_group_id
            }
        }
    
    except Exception as e:
        return {"error": str(e), "success": False}

@app.get("/api/avatars/managed")
async def api_get_managed_avatars():
    """Get list of user-uploaded avatar images"""
    try:
        with Session(engine) as session:
            avatars = session.exec(select(AvatarImage)).all()
            return {
                "avatars": [
                    {
                        "id": avatar.id,
                        "name": avatar.name,
                        "filename": avatar.filename,
                        "file_path": avatar.file_path,
                        "file_size": avatar.file_size,
                        "upload_date": avatar.upload_date,
                        "avatar_type": avatar.avatar_type,
                        "avatar_group_id": avatar.avatar_group_id,
                        "voice_id": avatar.voice_id,
                        "spawn_position": avatar.spawn_position,
                        "disabled": avatar.disabled
                    }
                    for avatar in avatars
                ]
            }
    except Exception as e:
        return {"avatars": [], "error": str(e)}

@app.delete("/api/avatars/{avatar_id}")
async def api_delete_avatar(avatar_id: int):
    """Delete an uploaded avatar image"""
    try:
        with Session(engine) as session:
            avatar = session.get(AvatarImage, avatar_id)
            if not avatar:
                return {"error": "Avatar not found", "success": False}
            
            # Delete file from disk (user-uploaded avatars are in persistent directory)
            full_path = os.path.join(PERSISTENT_AVATARS_DIR, avatar.filename)
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"🗑️  Deleted avatar file: {full_path}")
            
            # Delete from database
            session.delete(avatar)
            session.commit()
            
            # Broadcast refresh message to all connected clients
            asyncio.create_task(hub.broadcast({
                "type": "avatar_updated",
                "message": "Avatar deleted"
            }))
            
            return {"success": True}
    
    except Exception as e:
        return {"error": str(e), "success": False}

@app.delete("/api/avatars/group/{group_id}")
async def api_delete_avatar_group(group_id: str):
    """Delete an entire avatar group (all avatars with the same group_id)"""
    try:
        with Session(engine) as session:
            # Find all avatars in the group
            if group_id.startswith('single_'):
                # Handle single avatars (group_id is like "single_123")
                avatar_id = int(group_id.replace('single_', ''))
                avatars = [session.get(AvatarImage, avatar_id)]
                if not avatars[0]:
                    return {"error": "Avatar not found", "success": False}
            else:
                # Handle grouped avatars
                avatars = session.exec(
                    select(AvatarImage).where(AvatarImage.avatar_group_id == group_id)
                ).all()
                
                if not avatars:
                    return {"error": "Avatar group not found", "success": False}
            
            # Delete files from disk and database
            for avatar in avatars:
                if avatar:  # Check in case of single avatar that might be None
                    full_path = os.path.join(PERSISTENT_AVATARS_DIR, avatar.filename)
                    if os.path.exists(full_path):
                        os.remove(full_path)
                        logger.info(f"🗑️  Deleted avatar file: {full_path}")
                    session.delete(avatar)
            
            session.commit()
            
            # Broadcast refresh message to all connected clients
            asyncio.create_task(hub.broadcast({
                "type": "avatar_updated",
                "message": "Avatar group deleted"
            }))
            
            return {"success": True, "deleted_count": len([a for a in avatars if a])}
    
    except Exception as e:
        return {"error": str(e), "success": False}



@app.put("/api/avatars/group/{group_id}/position")
async def api_update_avatar_position(group_id: str, position_data: dict):
    """Update spawn position assignment for an avatar group"""
    try:
        spawn_position = position_data.get("spawn_position")  # None means random, 1-6 means specific slot
        
        with Session(engine) as session:
            # Find all avatars in the group
            if group_id.startswith('single_'):
                # Handle single avatars
                avatar_id = int(group_id.replace('single_', ''))
                avatars = [session.get(AvatarImage, avatar_id)]
                if not avatars[0]:
                    return {"error": "Avatar not found", "success": False}
            else:
                # Handle grouped avatars
                avatars = session.exec(
                    select(AvatarImage).where(AvatarImage.avatar_group_id == group_id)
                ).all()
                
                if not avatars:
                    return {"error": "Avatar group not found", "success": False}
            
            # Update spawn_position for all avatars in the group
            for avatar in avatars:
                if avatar:
                    avatar.spawn_position = spawn_position
                    session.add(avatar)
            
            session.commit()
            
            # Broadcast refresh message to all connected clients
            asyncio.create_task(hub.broadcast({
                "type": "avatar_updated",
                "message": "Avatar spawn position updated"
            }))
            
            return {"success": True, "updated_count": len([a for a in avatars if a])}
    
    except Exception as e:
        return {"error": str(e), "success": False}

@app.put("/api/avatars/{avatar_id}/toggle-disabled")
async def api_toggle_avatar_disabled(avatar_id: int):
    """Toggle the disabled status of an avatar"""
    try:
        with Session(engine) as session:
            avatar = session.get(AvatarImage, avatar_id)
            if not avatar:
                return {"error": "Avatar not found", "success": False}
            
            # Toggle the disabled status
            avatar.disabled = not avatar.disabled
            session.add(avatar)
            session.commit()
            
            # Broadcast refresh message to all connected clients
            asyncio.create_task(hub.broadcast({
                "type": "avatar_updated",
                "message": f"Avatar {'disabled' if avatar.disabled else 'enabled'}"
            }))
            
            return {
                "success": True,
                "avatar_id": avatar_id,
                "disabled": avatar.disabled,
                "message": f"Avatar {'disabled' if avatar.disabled else 'enabled'}"
            }
    
    except Exception as e:
        return {"error": str(e), "success": False}

@app.put("/api/avatars/group/{group_id}/toggle-disabled")
async def api_toggle_avatar_group_disabled(group_id: str):
    """Toggle the disabled status of an entire avatar group"""
    try:
        with Session(engine) as session:
            # Find all avatars in the group
            if group_id.startswith('single_'):
                # Handle single avatars (group_id is like "single_123")
                avatar_id = int(group_id.replace('single_', ''))
                avatars = [session.get(AvatarImage, avatar_id)]
                if not avatars[0]:
                    return {"error": "Avatar not found", "success": False}
            else:
                # Handle grouped avatars (pairs)
                avatars = session.exec(
                    select(AvatarImage).where(AvatarImage.avatar_group_id == group_id)
                ).all()
                
                if not avatars:
                    return {"error": "Avatar group not found", "success": False}
            
            # Check current disabled status - if any avatar is enabled, we disable all
            # If all are disabled, we enable all
            any_enabled = any(not avatar.disabled for avatar in avatars if avatar)
            new_disabled_status = any_enabled  # If any enabled, disable all; if all disabled, enable all
            
            # Update disabled status for all avatars in the group
            updated_count = 0
            for avatar in avatars:
                if avatar:
                    avatar.disabled = new_disabled_status
                    session.add(avatar)
                    updated_count += 1
            
            session.commit()
            
            # Broadcast refresh message to all connected clients
            asyncio.create_task(hub.broadcast({
                "type": "avatar_updated",
                "message": f"Avatar group {'disabled' if new_disabled_status else 'enabled'}"
            }))
            
            return {
                "success": True,
                "group_id": group_id,
                "disabled": new_disabled_status,
                "updated_count": updated_count,
                "message": f"Avatar group {'disabled' if new_disabled_status else 'enabled'}"
            }
    
    except Exception as e:
        return {"error": str(e), "success": False}

@app.get("/api/voices")
async def api_get_voices():
    """Get all configured voices"""
    with Session(engine) as session:
        voices = session.exec(select(Voice)).all()
        return {"voices": [voice.dict() for voice in voices]}

@app.post("/api/voices")
async def api_add_voice(voice_data: dict):
    """Add a new voice"""
    with Session(engine) as session:
        # Check if voice already exists
        existing = session.exec(
            select(Voice).where(
                Voice.voice_id == voice_data["voice_id"],
                Voice.provider == voice_data["provider"]
            )
        ).first()
        
        if existing:
            return {"error": "Voice already exists", "voice": existing.dict()}
        
        # Create new voice
        import datetime
        new_voice = Voice(
            name=voice_data["name"],
            voice_id=voice_data["voice_id"],
            provider=voice_data["provider"],
            enabled=voice_data.get("enabled", True),
            avatar_image=voice_data.get("avatar_image"),  # Keep for backward compatibility
            avatar_default=voice_data.get("avatar_default"),
            avatar_speaking=voice_data.get("avatar_speaking"),
            avatar_mode=voice_data.get("avatar_mode", "single"),
            created_at=datetime.datetime.now().isoformat()
        )
        
        session.add(new_voice)
        session.commit()
        session.refresh(new_voice)
        
        return {"success": True, "voice": new_voice.dict()}

@app.put("/api/voices/{voice_id}")
async def api_update_voice(voice_id: int, voice_data: dict):
    """Update a voice (enable/disable, change avatar, etc.)"""
    with Session(engine) as session:
        voice = session.get(Voice, voice_id)
        if not voice:
            return {"error": "Voice not found"}
        
        # Update fields
        if "name" in voice_data:
            voice.name = voice_data["name"]
        if "enabled" in voice_data:
            voice.enabled = voice_data["enabled"]
        if "avatar_image" in voice_data:
            voice.avatar_image = voice_data["avatar_image"]
        
        session.add(voice)
        session.commit()
        session.refresh(voice)
        
        return {"success": True, "voice": voice.dict()}

@app.delete("/api/voices/{voice_id}")
async def api_delete_voice(voice_id: int):
    """Delete a voice"""
    with Session(engine) as session:
        voice = session.get(Voice, voice_id)
        if not voice:
            return {"error": "Voice not found"}
        
        session.delete(voice)
        session.commit()
        
        return {"success": True}

@app.get("/api/available-voices/{provider}")
async def api_get_available_voices(provider: str, api_key: str = None):
    """Get available voices from a specific provider"""
    if provider == "edge":
        # Return common Edge TTS voices
        edge_voices = [
            {"voice_id": "en-US-AvaNeural", "name": "Ava - Female US"},
            {"voice_id": "en-US-BrianNeural", "name": "Brian - Male US"},
            {"voice_id": "en-US-EmmaNeural", "name": "Emma - Female US"},
            {"voice_id": "en-US-JennyNeural", "name": "Jenny - Female US"},
            {"voice_id": "en-US-GuyNeural", "name": "Guy - Male US"},
            {"voice_id": "en-US-AriaNeural", "name": "Aria - Female US"},
            {"voice_id": "en-US-DavisNeural", "name": "Davis - Male US"},
            {"voice_id": "en-US-JaneNeural", "name": "Jane - Female US"},
            {"voice_id": "en-US-JasonNeural", "name": "Jason - Male US"},
            {"voice_id": "en-US-SaraNeural", "name": "Sara - Female US"},
            {"voice_id": "en-US-TonyNeural", "name": "Tony - Male US"},
            {"voice_id": "en-US-NancyNeural", "name": "Nancy - Female US"},
            {"voice_id": "en-US-AmberNeural", "name": "Amber - Female US"},
            {"voice_id": "en-US-AshleyNeural", "name": "Ashley - Female US"},
            {"voice_id": "en-US-BrandonNeural", "name": "Brandon - Male US"},
            {"voice_id": "en-US-ChristopherNeural", "name": "Christopher - Male US"},
            {"voice_id": "en-US-CoraNeural", "name": "Cora - Female US"},
            {"voice_id": "en-US-ElizabethNeural", "name": "Elizabeth - Female US"},
            {"voice_id": "en-US-EricNeural", "name": "Eric - Male US"},
            {"voice_id": "en-US-JacobNeural", "name": "Jacob - Male US"},
            {"voice_id": "en-US-MichelleNeural", "name": "Michelle - Female US"},
            {"voice_id": "en-US-MonicaNeural", "name": "Monica - Female US"},
            {"voice_id": "en-US-RogerNeural", "name": "Roger - Male US"}
        ]
        return {"voices": edge_voices}
    elif provider == "monstertts":
        # Fetch MonsterTTS voices from their API if API key is provided
        if not api_key:
            return {"error": "API key required for MonsterTTS voices"}
        
        try:
            import aiohttp
            headers = {
                "Authorization": api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.console.tts.monster/voices", headers=headers) as response:
                    if response.status == 200:
                        voices_data = await response.json()
                        logger.info(f"MonsterTTS API Response: {voices_data}")
                        
                        # Transform the API response to our format
                        monster_voices = []
                        
                        # Handle different response formats
                        if isinstance(voices_data, list):
                            # Response is a list of voices
                            for voice in voices_data:
                                if isinstance(voice, dict):
                                    monster_voices.append({
                                        "voice_id": voice.get("id", voice.get("voice_id", voice.get("uuid", "unknown"))),
                                        "name": voice.get("name", voice.get("display_name", f"Voice {voice.get('id', 'Unknown')[:8]}"))
                                    })
                                else:
                                    logger.info(f"Unexpected voice format: {voice} (type: {type(voice)})")
                        elif isinstance(voices_data, dict):
                            # Response might be wrapped in an object
                            voices_list = voices_data.get("voices", voices_data.get("data", [voices_data]))
                            for voice in voices_list:
                                if isinstance(voice, dict):
                                    monster_voices.append({
                                        "voice_id": voice.get("id", voice.get("voice_id", voice.get("uuid", "unknown"))),
                                        "name": voice.get("name", voice.get("display_name", f"Voice {voice.get('id', 'Unknown')[:8]}"))
                                    })
                        
                        logger.info(f"Parsed {len(monster_voices)} MonsterTTS voices")
                        return {"voices": monster_voices}
                    else:
                        error_text = await response.text()
                        return {"error": f"Failed to fetch MonsterTTS voices: {error_text}"}
        except Exception as e:
            return {"error": f"Error fetching MonsterTTS voices: {str(e)}"}
    elif provider == "google":
        # Fetch Google TTS voices dynamically
        if not api_key:
            return {"error": "API key required for Google TTS voices"}
        
        try:
            from tts import GoogleTTSProvider
            google_provider = GoogleTTSProvider(api_key)
            voices = await google_provider.list_voices()
            return {"voices": voices}
        except Exception as e:
            return {"error": f"Error fetching Google TTS voices: {str(e)}"}
    else:
        return {"error": "Unknown provider"}

@app.post("/api/available-voices/polly")
async def api_get_polly_voices(credentials: dict):
    """Get available voices from Amazon Polly"""
    try:
        from tts import AmazonPollyProvider
        polly_provider = AmazonPollyProvider(
            credentials.get('accessKey', ''),
            credentials.get('secretKey', ''),
            credentials.get('region', 'us-east-1')
        )
        voices = await polly_provider.list_voices()
        return {"voices": voices}
    except Exception as e:
        return {"error": f"Error fetching Polly voices: {str(e)}"}

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
    settings = get_settings()
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
    
    settings = get_settings()
    
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
    
    settings = get_settings()
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
@app.post("/api/simulate")
async def api_simulate(
    user: str = Form(...), 
    text: str = Form(...), 
    eventType: str = Form("chat"),
    testVoice: str = Form(None)
):
    """Simulate a chat message"""
    logger.info(f"Simulate request: user={user}, text={text}, eventType={eventType}, testVoice={testVoice}")
    
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

@app.post("/api/simulate/moderation")
async def api_simulate_moderation(
    target_user: str = Form(...),
    eventType: str = Form("timeout"),  # "ban" or "timeout"
    duration: int = Form(None)  # seconds for timeout, None for ban
):
    """Simulate a moderation event (ban/timeout) with immediate audio stop"""
    logger.info(f"Simulate moderation: target_user={target_user}, eventType={eventType}, duration={duration}")
    
    try:
        await handle_moderation_event({
            "type": "moderation",
            "eventType": eventType,
            "target_user": target_user,
            "duration": duration
        })
        
        return {
            "ok": True, 
            "message": f"Moderation event simulated: {eventType} for {target_user}" + (f" ({duration}s)" if duration else "") + " - TTS stopped immediately"
        }
    except Exception as e:
        logger.error(f"Moderation simulation failed: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}

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

# ---------- Voice Distribution Stats ----------
@app.get("/api/voice-stats")
async def api_voice_stats():
    """Get voice usage distribution statistics"""
    from tts import fallback_voice_stats, fallback_selection_count
    
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

@app.delete("/api/voice-stats")
async def api_reset_voice_stats():
    """Reset voice usage distribution statistics"""
    from tts import reset_fallback_stats
    
    global voice_usage_stats, voice_selection_count
    voice_usage_stats.clear()
    voice_selection_count = 0
    
    # Reset fallback stats
    reset_fallback_stats()
    
    logger.info("Voice distribution statistics have been reset")
    return {"ok": True, "message": "Voice statistics reset successfully"}

# ---------- Twitch integration (optional) ----------
TwitchTask = None
try:
    from twitch_listener import run_twitch_bot
    logger.info("Twitch listener imported successfully")
except Exception as e:
    logger.error(f"Failed to import twitch_listener: {e}")
    logger.info(f"❌ Failed to import Twitch listener: {e}")
    run_twitch_bot = None

@app.on_event("startup")
async def startup():
    logger.info("FastAPI startup event triggered")
    try:
        settings = get_settings()
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

# Add favicon endpoint to handle browser favicon requests
@app.get("/favicon.ico")
async def favicon():
    """Serve the favicon.ico file"""
    favicon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/x-icon")
    else:
        # Return a 204 No Content if favicon doesn't exist
        from fastapi.responses import Response
        return Response(status_code=204)

# Mount static files AFTER all API routes and WebSocket endpoints are defined
# This ensures that /api/* and /ws routes take precedence over static file serving
if os.path.isdir(PUBLIC_DIR):
    logger.info(f"Mounting static files from: {PUBLIC_DIR}")
    
    from fastapi import Request
    from fastapi.responses import FileResponse
    
    # Handle assets manually with proper MIME types
    assets_dir = os.path.join(PUBLIC_DIR, "assets")
    if os.path.isdir(assets_dir):
        logger.info(f"Assets directory found: {assets_dir}")
        logger.info(f"Assets directory contents: {os.listdir(assets_dir)}")
        
        @app.get("/assets/{filename}")
        async def serve_assets(filename: str):
            """Serve assets with correct MIME types"""
            file_path = os.path.join(assets_dir, filename)
            logger.info(f"Assets request: {filename} -> {file_path}")
            
            if not os.path.isfile(file_path):
                logger.info(f"Asset file not found: {file_path}")
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Asset not found")
            
            # Determine MIME type based on file extension
            media_type = None
            if filename.endswith('.js'):
                media_type = 'application/javascript'
                logger.info(f"Setting JavaScript MIME type for: {filename}")
            elif filename.endswith('.css'):
                media_type = 'text/css'
                logger.info(f"Setting CSS MIME type for: {filename}")
            elif filename.endswith('.map'):
                media_type = 'application/json'
            
            logger.info(f"Serving asset: {filename} with MIME type: {media_type}")
            return FileResponse(file_path, media_type=media_type)
    else:
        logger.info(f"Assets directory not found: {assets_dir}")
    
    # Mount built-in voice avatars
    voice_avatars_dir = os.path.join(PUBLIC_DIR, "voice_avatars")
    if os.path.isdir(voice_avatars_dir):
        logger.info(f"Mounting /voice_avatars from: {voice_avatars_dir}")
        app.mount("/voice_avatars", StaticFiles(directory=voice_avatars_dir), name="voice_avatars")
    else:
        logger.info(f"Built-in voice avatars directory not found: {voice_avatars_dir}")
    
    # Mount user-uploaded avatars from persistent directory
    if os.path.isdir(PERSISTENT_AVATARS_DIR):
        logger.info(f"Mounting /user_avatars from: {PERSISTENT_AVATARS_DIR}")
        app.mount("/user_avatars", StaticFiles(directory=PERSISTENT_AVATARS_DIR), name="user_avatars")
    else:
        logger.info(f"User avatars directory not found: {PERSISTENT_AVATARS_DIR}")
    
    # Handle specific routes for SPA
    @app.get("/settings")
    async def serve_settings():
        """Serve settings page"""
        index_path = os.path.join(PUBLIC_DIR, "index.html")
        return FileResponse(index_path, media_type='text/html')
    
    @app.get("/yappers")
    async def serve_yappers():
        """Serve yappers page"""
        index_path = os.path.join(PUBLIC_DIR, "index.html")
        return FileResponse(index_path, media_type='text/html')
    
    # Handle vite.svg specifically
    @app.get("/vite.svg")
    async def serve_vite_svg():
        """Serve vite.svg placeholder"""
        from fastapi.responses import Response
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <path d="m9 12 2 2 4-4"/>
        </svg>'''
        return Response(content=svg_content, media_type="image/svg+xml")
    
    # Handle root path
    @app.get("/")
    async def serve_root():
        """Serve root page"""
        index_path = os.path.join(PUBLIC_DIR, "index.html")
        return FileResponse(index_path, media_type='text/html')
else:
    logger.info(f"Static files directory not found: {PUBLIC_DIR}")

@app.get("/api/debug/per-user-queuing")
async def api_debug_per_user_queuing():
    """Debug endpoint to check per-user queuing setting"""
    try:
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

@app.post("/api/twitch/test")
async def api_test_twitch():
    """Test Twitch connection manually using OAuth"""
    try:
        settings = get_settings()
        twitch_config = settings.get("twitch", {})
        
        if not twitch_config.get("enabled"):
            return {"success": False, "error": "Twitch not enabled in settings"}
        
        # Check OAuth token
        token_info = await get_twitch_token_for_bot()
        if not token_info:
            return {"success": False, "error": "No Twitch account connected. Please connect your account first."}
        
        channel = twitch_config.get("channel") or token_info["username"]
        if not channel:
            return {"success": False, "error": "No channel specified in settings"}
        
        # Force restart Twitch connection with OAuth
        await restart_twitch_if_needed(settings)
        
        return {"success": True, "message": f"Twitch connection test initiated for {token_info['username']} -> #{channel}"}
    except Exception as e:
        logger.error(f"Twitch test failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@app.post("/api/message-filter/test")
async def api_test_message_filter(test_data: dict):
    """Test message filtering with a sample message"""
    try:
        settings = get_settings()
        test_message = test_data.get("message", "")
        test_username = test_data.get("username", "")
        
        should_process, filtered_text = should_process_message(test_message, settings, test_username)
        
        return {
            "success": True,
            "original_message": test_message,
            "test_username": test_username,
            "filtered_message": filtered_text,
            "should_process": should_process,
            "was_modified": filtered_text != test_message,
            "filtering_settings": settings.get("messageFiltering", {})
        }
    except Exception as e:
        logger.error(f"Message filter test failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@app.post("/api/avatars/re-randomize")
async def api_re_randomize_avatars():
    """Trigger avatar re-randomization on the Yappers page"""
    try:
        # Broadcast a message to all WebSocket clients to re-randomize avatars
        asyncio.create_task(hub.broadcast({
            "type": "re_randomize_avatars",
            "message": "Avatar assignments re-randomized"
        }))
        
        logger.info("Avatar re-randomization triggered")
        return {"success": True, "message": "Avatar assignments will be re-randomized"}
    except Exception as e:
        logger.error(f"Avatar re-randomization failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@app.post("/api/tts/cancel")
async def api_cancel_user_tts(cancel_data: dict):
    """Cancel TTS for a specific user (for testing or moderation)"""
    try:
        username = cancel_data.get("username", "")
        if not username:
            return {"success": False, "error": "Username is required"}
        
        cancel_user_tts(username)
        logger.info(f"TTS cancelled for user via API: {username}")
        return {"success": True, "message": f"TTS cancelled for user: {username}"}
    except Exception as e:
        logger.error(f"TTS cancellation failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@app.get("/api/tts/active")
async def api_get_active_tts():
    """Get list of currently active TTS jobs"""
    try:
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

@app.post("/api/tts/stop-all")
async def api_stop_all_tts():
    """Stop all TTS activity"""
    try:
        stop_all_tts()
        return {"success": True, "message": "All TTS stopped", "tts_enabled": tts_enabled}
    except Exception as e:
        logger.error(f"Failed to stop all TTS: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@app.post("/api/tts/resume-all")
async def api_resume_all_tts():
    """Resume TTS processing"""
    try:
        resume_all_tts()
        return {"success": True, "message": "TTS processing resumed", "tts_enabled": tts_enabled}
    except Exception as e:
        logger.error(f"Failed to resume TTS: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@app.post("/api/tts/toggle")
async def api_toggle_tts():
    """Toggle TTS on/off"""
    try:
        new_state = toggle_tts()
        message = "TTS enabled" if new_state else "TTS disabled"
        return {"success": True, "message": message, "tts_enabled": tts_enabled}
    except Exception as e:
        logger.error(f"Failed to toggle TTS: {e}", exc_info=True)

@app.get("/api/debug/database")
async def api_debug_database():
    """Get database information for debugging"""
    try:
        from db_migration import get_database_info
        db_info = get_database_info(DB_PATH)
        
        # Also get some basic stats
        with Session(engine) as session:
            voice_count = session.exec(select(Voice)).all()
            avatar_count = session.exec(select(AvatarImage)).all()
            
            db_info["statistics"] = {
                "voices": len(voice_count),
                "avatars": len(avatar_count),
                "database_path": DB_PATH,
                "user_data_dir": USER_DATA_DIR
            }
        
        return {"success": True, "database": db_info}
    except Exception as e:
        logger.error(f"Failed to get database info: {e}", exc_info=True)
        return {"success": False, "error": str(e), "database_path": DB_PATH}
        return {"success": False, "error": str(e)}

@app.get("/api/tts/status")
async def api_get_tts_status():
    """Get current TTS status"""
    try:
        return {
            "success": True,
            "tts_enabled": tts_enabled,
            "active_jobs_count": len(active_tts_jobs)
        }
    except Exception as e:
        logger.error(f"Failed to get TTS status: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 8000))
    debug_mode = os.environ.get('DEBUG', '').lower() in ('true', '1', 'yes', 'on')
    uvicorn.run("app:app", host=host, port=port, reload=debug_mode)
