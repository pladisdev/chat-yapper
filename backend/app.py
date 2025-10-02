from __future__ import annotations
import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Session, select, create_engine

from models import Setting, Voice, AvatarImage
from tts import get_provider, get_hybrid_provider, TTSJob

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
        
        # Console handler - only errors and warnings
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
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

# Voice usage tracking for distribution analysis
voice_usage_stats = defaultdict(int)
voice_selection_count = 0

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
    print(f"HTTP Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    print(f"Response: {response.status_code} (took {process_time:.2f}s)")
    
    return response

# Serve generated audio files under /audio
AUDIO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "audio"))
os.makedirs(AUDIO_DIR, exist_ok=True)
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

# Store PUBLIC_DIR for mounting later (after routes are defined)
PUBLIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "public"))
print(f"Static files directory: {PUBLIC_DIR}")
print(f"Directory exists: {os.path.isdir(PUBLIC_DIR)}")

PERSISTENT_AVATARS_DIR = os.path.join(USER_DATA_DIR, "voice_avatars")
os.makedirs(PERSISTENT_AVATARS_DIR, exist_ok=True)
logger.info(f"Persistent avatars directory: {PERSISTENT_AVATARS_DIR}")

# Debug: List files in the public directory
if os.path.isdir(PUBLIC_DIR):
    print("📂 Files in static directory:")
    for root, dirs, files in os.walk(PUBLIC_DIR):
        level = root.replace(PUBLIC_DIR, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f"{subindent}{file}")
else:
    print("Static files directory not found")

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
    print(f"WebSocket connection attempt from {ws.client}")
    try:
        await hub.connect(ws)
        logger.info(f"WebSocket connected successfully. Total clients: {len(hub.clients)}")
        print(f"WebSocket connected successfully. Total clients: {len(hub.clients)}")
        
        # Send a welcome message to confirm connection
        welcome_msg = {
            "type": "connection",
            "message": "WebSocket connected successfully",
            "client_count": len(hub.clients)
        }
        await ws.send_text(json.dumps(welcome_msg))
        logger.info(f"Sent welcome message to WebSocket client {client_info}")
        print(f"Sent welcome message to WebSocket client")
        
        while True:
            # In this app, server pushes; but you can accept pings or config messages:
            message = await ws.receive_text()
            logger.debug(f"WebSocket received message from {client_info}: {message}")
            print(f"WebSocket received: {message}")
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected from {client_info}. Remaining clients: {len(hub.clients)-1}")
        print(f"WebSocket disconnected. Remaining clients: {len(hub.clients)-1}")
        hub.unregister(ws)
    except Exception as e:
        logger.error(f"WebSocket error from {client_info}: {e}")
        print(f"WebSocket error: {e}")
        hub.unregister(ws)

# ---------- Settings CRUD ----------

def get_settings() -> Dict[str, Any]:
    with Session(engine) as s:
        row = s.exec(select(Setting).where(Setting.key == "settings")).first()
        if row:
            settings = json.loads(row.value_json)
            logger.info(f"Loaded settings from database: {DB_PATH}")
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
            
            # Restart Twitch bot if settings changed
            asyncio.create_task(restart_twitch_if_needed(data))
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
            twitch_config = settings["twitch"]
            TwitchTask = asyncio.create_task(run_twitch_bot(
                token=twitch_config["token"],
                nick=twitch_config["nick"],
                channel=twitch_config["channel"],
                on_event=lambda e: asyncio.create_task(handle_event(e))
            ))
            logger.info("Twitch bot restarted")
        else:
            TwitchTask = None
            logger.info("Twitch bot disabled")
    except Exception as e:
        logger.error(f"Failed to restart Twitch bot: {e}", exc_info=True)

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
    print("API: GET /api/status called")
    status = {
        "status": "running",
        "websocket_clients": len(hub.clients),
        "message": "Chat Yapper backend is running!"
    }
    print(f"API: Returning status: {status}")
    return status

@app.get("/api/test")
async def api_test():
    """Simple test endpoint for debugging"""
    print("API: GET /api/test called - React app is working!")
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
            print(f"Error reading built-in avatars: {e}")
    
    # Get user-uploaded avatars from the persistent directory
    if os.path.exists(PERSISTENT_AVATARS_DIR):
        try:
            for filename in os.listdir(PERSISTENT_AVATARS_DIR):
                if any(filename.lower().endswith(ext) for ext in valid_extensions):
                    avatar_files.append(f"/user_avatars/{filename}")
        except Exception as e:
            print(f"Error reading user avatars: {e}")
    
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
        print(f"Saving avatar to persistent directory: {avatars_dir}")
        
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
            print(f"Warning: Failed to resize image: {e}")
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
                        "avatar_group_id": avatar.avatar_group_id
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
                print(f"🗑️  Deleted avatar file: {full_path}")
            
            # Delete from database
            session.delete(avatar)
            session.commit()
            
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
                        print(f"🗑️  Deleted avatar file: {full_path}")
                    session.delete(avatar)
            
            session.commit()
            return {"success": True, "deleted_count": len([a for a in avatars if a])}
    
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
                        print(f"MonsterTTS API Response: {voices_data}")
                        
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
                                    print(f"Unexpected voice format: {voice} (type: {type(voice)})")
                        elif isinstance(voices_data, dict):
                            # Response might be wrapped in an object
                            voices_list = voices_data.get("voices", voices_data.get("data", [voices_data]))
                            for voice in voices_list:
                                if isinstance(voice, dict):
                                    monster_voices.append({
                                        "voice_id": voice.get("id", voice.get("voice_id", voice.get("uuid", "unknown"))),
                                        "name": voice.get("name", voice.get("display_name", f"Voice {voice.get('id', 'Unknown')[:8]}"))
                                    })
                        
                        print(f"Parsed {len(monster_voices)} MonsterTTS voices")
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
    
@app.get("/api/available-voices/webspeech") 
async def api_get_webspeech_voices():
    """Get available voices for Web Speech API"""
    # These are handled client-side, so we return language options
    webspeech_voices = [
        {"voice_id": "en-US", "name": "Default US English"},
        {"voice_id": "en-GB", "name": "Default UK English"},
        {"voice_id": "en-CA", "name": "Default Canadian English"},
        {"voice_id": "en-AU", "name": "Default Australian English"},
        {"voice_id": "es-ES", "name": "Spanish"},
        {"voice_id": "fr-FR", "name": "French"},
        {"voice_id": "de-DE", "name": "German"},
        {"voice_id": "it-IT", "name": "Italian"},
        {"voice_id": "pt-BR", "name": "Portuguese"},
        {"voice_id": "ja-JP", "name": "Japanese"},
        {"voice_id": "ko-KR", "name": "Korean"},
        {"voice_id": "zh-CN", "name": "Chinese"}
    ]
    return {"voices": webspeech_voices}

# ---------- TTS Pipeline ----------

async def handle_test_voice_event(evt: Dict[str, Any]):
    """Handle test voice events - similar to handle_event but uses the provided test voice"""
    print(f"🎵 Handling test voice event: {evt}")
    settings = get_settings()
    audio_format = settings.get("audioFormat", "mp3")
    
    test_voice_data = evt.get("testVoice")
    if not test_voice_data:
        print("No test voice data provided")
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
    print(f"Test voice: {selected_voice.name} ({selected_voice.provider})")

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
    print(f"Test TTS Job: text='{job.text}', voice='{selected_voice.name}' ({selected_voice.provider}:{selected_voice.voice_id}), format='{job.audio_format}'")

    # Fire-and-forget to allow overlap
    async def _run():
        try:
            print(f"Starting test TTS synthesis...")
            path = await provider.synth(job)
            print(f"Test TTS generated: {path}")
            
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
            print(f"Broadcasting test voice to {len(hub.clients)} clients: {payload}")
            await hub.broadcast(payload)
        except Exception as e:
            print(f"Test TTS synthesis error: {e}")

    asyncio.create_task(_run())

async def handle_event(evt: Dict[str, Any]):
    print(f"🎵 Handling event: {evt}")
    settings = get_settings()
    audio_format = settings.get("audioFormat", "mp3")
    special = settings.get("specialVoices", {})

    # Get enabled voices from database
    with Session(engine) as session:
        enabled_voices = session.exec(select(Voice).where(Voice.enabled == True)).all()
    
    if not enabled_voices:
        print("No enabled voices found in database. Please add voices through the settings page.")
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
        print(f"Random voice selected: {selected_voice.name} ({selected_voice.provider})")
    else:
        print(f"Special event voice selected: {selected_voice.name} ({selected_voice.provider})")
    
    # Track voice usage for distribution analysis
    global voice_usage_stats, voice_selection_count
    voice_key = f"{selected_voice.name} ({selected_voice.provider})"
    voice_usage_stats[voice_key] += 1
    voice_selection_count += 1
    
    # Log distribution every 10 selections
    if voice_selection_count % 10 == 0:
        print(f"\nVoice Distribution Summary (after {voice_selection_count} selections):")
        total_usage = sum(voice_usage_stats.values())
        for voice_name, count in sorted(voice_usage_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_usage) * 100
            print(f"   {voice_name}: {count} times ({percentage:.1f}%)")
        print("---")
    
    print(f"Selected voice: {selected_voice.name} ({selected_voice.provider})")

    # Get TTS configuration - Use hybrid provider that handles both MonsterTTS and Edge TTS
    tts_config = settings.get("tts", {})
    
    # Get TTS provider configurations
    monstertts_config = tts_config.get("monstertts", {})
    monster_api_key = monstertts_config.get("apiKey", "")
    
    edge_config = tts_config.get("edge", {})
    
    google_config = tts_config.get("google", {})
    google_api_key = google_config.get("apiKey", "")
    
    polly_config = tts_config.get("polly", {})
    
    # Use hybrid provider that handles all providers with rate limiting and fallback
    # Pass enabled voices so the hybrid provider can choose randomly when needed
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
    print(f"TTS Job: text='{job.text}', voice='{selected_voice.name}' ({selected_voice.provider}:{selected_voice.voice_id}), format='{job.audio_format}'")

    # Fire-and-forget to allow overlap
    async def _run():
        try:
            print(f"Starting TTS synthesis...")
            path = await provider.synth(job)
            print(f"TTS generated: {path}")
            
            # Broadcast to clients to play
            # Use the selected voice from database
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
            print(f"Broadcasting to {len(hub.clients)} clients: {payload}")
            await hub.broadcast(payload)
        except Exception as e:
            print(f"TTS Error: {e}")
    asyncio.create_task(_run())

# ---------- Simulate messages (for local testing) ----------
@app.post("/api/simulate")
async def api_simulate(
    user: str = Form(...), 
    text: str = Form(...), 
    eventType: str = Form("chat"),
    testVoice: str = Form(None)
):
    print(f"Simulate request: user={user}, text={text}, eventType={eventType}, testVoice={testVoice}")
    
    # If testVoice is provided, parse it and use it directly
    if testVoice:
        try:
            test_voice_data = json.loads(testVoice)
            await handle_test_voice_event({
                "user": user, 
                "text": text, 
                "eventType": eventType,
                "testVoice": test_voice_data
            })
        except json.JSONDecodeError:
            print("Invalid testVoice JSON data")
            return {"ok": False, "error": "Invalid testVoice data"}
    else:
        await handle_event({"user": user, "text": text, "eventType": eventType})
    
    return {"ok": True}

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
    
    print("Voice distribution statistics have been reset")
    return {"ok": True, "message": "Voice statistics reset successfully"}

# ---------- Twitch integration (optional) ----------
TwitchTask = None
try:
    from twitch_listener import run_twitch_bot
    logger.info("Twitch listener imported successfully")
except Exception as e:
    logger.error(f"Failed to import twitch_listener: {e}")
    print(f"❌ Failed to import Twitch listener: {e}")
    run_twitch_bot = None

@app.on_event("startup")
async def startup():
    logger.info("FastAPI startup event triggered")
    try:
        settings = get_settings()
        logger.info(f"Settings loaded, Twitch enabled: {settings.get('twitch', {}).get('enabled')}")
        
        if run_twitch_bot and settings.get("twitch", {}).get("enabled"):
            logger.info("Starting Twitch bot...")
            twitch_config = settings["twitch"]
            logger.info(f"Twitch config: channel={twitch_config.get('channel')}, nick={twitch_config.get('nick')}, token={'***' if twitch_config.get('token') else 'None'}")
            
            global TwitchTask
            t = asyncio.create_task(run_twitch_bot(
                token=twitch_config["token"],
                nick=twitch_config["nick"], 
                channel=twitch_config["channel"],
                on_event=lambda e: asyncio.create_task(handle_event(e))
            ))
            TwitchTask = t
            logger.info("Twitch bot task created")
        else:
            if not run_twitch_bot:
                logger.warning("Twitch bot not available (import failed)")
            else:
                logger.info("Twitch integration disabled in settings")
    except Exception as e:
        logger.error(f"Startup event failed: {e}", exc_info=True)
        print(f"❌ Startup failed: {e}")

# Mount static files AFTER all API routes and WebSocket endpoints are defined
# This ensures that /api/* and /ws routes take precedence over static file serving
if os.path.isdir(PUBLIC_DIR):
    print(f"Mounting static files from: {PUBLIC_DIR}")
    
    from fastapi import Request
    from fastapi.responses import FileResponse
    
    # Handle assets manually with proper MIME types
    assets_dir = os.path.join(PUBLIC_DIR, "assets")
    if os.path.isdir(assets_dir):
        print(f"Assets directory found: {assets_dir}")
        print(f"Assets directory contents: {os.listdir(assets_dir)}")
        
        @app.get("/assets/{filename}")
        async def serve_assets(filename: str):
            """Serve assets with correct MIME types"""
            file_path = os.path.join(assets_dir, filename)
            print(f"Assets request: {filename} -> {file_path}")
            
            if not os.path.isfile(file_path):
                print(f"Asset file not found: {file_path}")
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Asset not found")
            
            # Determine MIME type based on file extension
            media_type = None
            if filename.endswith('.js'):
                media_type = 'application/javascript'
                print(f"Setting JavaScript MIME type for: {filename}")
            elif filename.endswith('.css'):
                media_type = 'text/css'
                print(f"Setting CSS MIME type for: {filename}")
            elif filename.endswith('.map'):
                media_type = 'application/json'
            
            print(f"Serving asset: {filename} with MIME type: {media_type}")
            return FileResponse(file_path, media_type=media_type)
    else:
        print(f"Assets directory not found: {assets_dir}")
    
    # Mount built-in voice avatars
    voice_avatars_dir = os.path.join(PUBLIC_DIR, "voice_avatars")
    if os.path.isdir(voice_avatars_dir):
        print(f"Mounting /voice_avatars from: {voice_avatars_dir}")
        app.mount("/voice_avatars", StaticFiles(directory=voice_avatars_dir), name="voice_avatars")
    else:
        print(f"Built-in voice avatars directory not found: {voice_avatars_dir}")
    
    # Mount user-uploaded avatars from persistent directory
    if os.path.isdir(PERSISTENT_AVATARS_DIR):
        print(f"Mounting /user_avatars from: {PERSISTENT_AVATARS_DIR}")
        app.mount("/user_avatars", StaticFiles(directory=PERSISTENT_AVATARS_DIR), name="user_avatars")
    else:
        print(f"User avatars directory not found: {PERSISTENT_AVATARS_DIR}")
    
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
    print(f"Static files directory not found: {PUBLIC_DIR}")

@app.post("/api/twitch/test")
async def api_test_twitch():
    """Test Twitch connection manually"""
    try:
        settings = get_settings()
        twitch_config = settings.get("twitch", {})
        
        if not twitch_config.get("enabled"):
            return {"success": False, "error": "Twitch not enabled in settings"}
        
        if not all([twitch_config.get("token"), twitch_config.get("nick"), twitch_config.get("channel")]):
            return {"success": False, "error": "Missing Twitch configuration (token, nick, or channel)"}
        
        # Force restart Twitch connection
        await restart_twitch_if_needed(settings)
        
        return {"success": True, "message": "Twitch connection test initiated"}
    except Exception as e:
        logger.error(f"Twitch test failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)