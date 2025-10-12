"""
Shared dependencies and utilities for routers
"""
import os
import sys
import tempfile
from sqlmodel import Session, create_engine, select, SQLModel
from modules.models import Setting, Voice, AvatarImage, TwitchAuth
from modules.backend_logging import setup_backend_logging

def is_executable():
    """Detect if running as PyInstaller executable"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def get_env_var(key, default=""):
    """Get environment variable, checking embedded config if running as executable"""
    # First try regular environment variables
    value = os.environ.get(key)
    if value:
        return value
    
    # If running as executable, try embedded config
    if is_executable():
        try:
            from embedded_config import get_embedded_env
            return get_embedded_env(key, default)
        except ImportError:
            # Embedded config not found, use default
            pass
    
    return default

# Initialize logging
logger = setup_backend_logging()

def get_user_data_dir():
    """Get a persistent directory for user data"""
    if os.name == 'nt':  # Windows
        base_dir = os.path.join(os.environ.get('LOCALAPPDATA', tempfile.gettempdir()), 'ChatYapper')
    else:  # Linux/Mac
        base_dir = os.path.join(os.path.expanduser('~'), '.chatyapper')
    
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

# User data directory and paths
USER_DATA_DIR = get_user_data_dir()
DB_PATH = os.environ.get("DB_PATH", os.path.join(USER_DATA_DIR, "app.db"))
PERSISTENT_AVATARS_DIR = os.path.join(USER_DATA_DIR, "voice_avatars")
PUBLIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public"))

# Create directories
os.makedirs(PERSISTENT_AVATARS_DIR, exist_ok=True)

# Database setup
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})

def get_database_session():
    """Get database session for dependency injection"""
    with Session(engine) as session:
        yield session

def get_settings() -> dict:
    """Get application settings from database"""
    import json
    try:
        with Session(engine) as session:
            row = session.exec(select(Setting).where(Setting.key == "settings")).first()
            if row:
                settings = json.loads(row.value_json)
                logger.info(f"Loaded settings from database: {DB_PATH}")
                return settings
            else:
                logger.error("No settings found in database!")
                return {}
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        return {}

def save_settings(data: dict):
    """Save application settings to database"""
    import json
    import asyncio
    try:
        with Session(engine) as session:
            row = session.exec(select(Setting).where(Setting.key == "settings")).first()
            if row:
                row.value_json = json.dumps(data)
                session.add(row)
                session.commit()
                logger.info(f"Settings saved to database: {DB_PATH}")
                
                # Import and use functions to update global state
                from app import restart_twitch_if_needed, hub
                
                # Restart Twitch bot if settings changed
                asyncio.create_task(restart_twitch_if_needed(data))
                
                # Broadcast refresh message to update Yappers page with new settings
                asyncio.create_task(hub.broadcast({
                    "type": "settings_updated",
                    "message": "Settings updated"
                }))
            else:
                logger.error("Could not find settings row to update!")
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        raise

# Twitch OAuth Configuration - uses embedded config when running as executable
TWITCH_CLIENT_ID = get_env_var("TWITCH_CLIENT_ID", "")
TWITCH_CLIENT_SECRET = get_env_var("TWITCH_CLIENT_SECRET", "")
TWITCH_REDIRECT_URI = f"http://localhost:{os.environ.get('PORT', 8000)}/auth/twitch/callback"
TWITCH_SCOPE = "chat:read"

# OAuth state tracking
oauth_states = {}