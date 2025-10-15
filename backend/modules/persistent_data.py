from sqlmodel import SQLModel, Session, select, create_engine
import os
import sys
import tempfile
import json
import hashlib
from datetime import datetime

from modules import logger, get_env_var, log_important

from modules.models import Setting, Voice, TwitchAuth, YouTubeAuth, AvatarImage, ProviderVoiceCache

def find_project_root():
    """Find the project root by looking for characteristic files"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Look for project markers that indicate the true project root
    # Use more specific markers to avoid stopping at backend directory
    markers = ['package.json', 'main.py', '.git']  # Removed requirements.txt as it exists in backend too
    
    while current_dir != os.path.dirname(current_dir):  # Not at filesystem root
        if any(os.path.exists(os.path.join(current_dir, marker)) for marker in markers):
            return current_dir
        current_dir = os.path.dirname(current_dir)
    
    # Fallback to going up two levels from the current file (backend/modules -> backend -> root)
    fallback_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return fallback_root

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

# Twitch OAuth Configuration - uses embedded config when running as executable
TWITCH_CLIENT_ID = get_env_var("TWITCH_CLIENT_ID", "")
TWITCH_CLIENT_SECRET = get_env_var("TWITCH_CLIENT_SECRET", "")
TWITCH_REDIRECT_URI = f"http://localhost:{os.environ.get('PORT', 8000)}/auth/twitch/callback"
TWITCH_SCOPE = "chat:read"

# YouTube OAuth Configuration
YOUTUBE_CLIENT_ID = get_env_var("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = get_env_var("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_REDIRECT_URI = f"http://localhost:{os.environ.get('PORT', 8000)}/auth/youtube/callback"
YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/youtube.force-ssl"

AUDIO_DIR = os.environ.get("AUDIO_DIR", os.path.join(find_project_root(), "audio"))
os.makedirs(AUDIO_DIR, exist_ok=True)

# Database setup
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})

# OAuth state tracking
oauth_states = {}

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
    """Save application settings to database (basic version without app-specific logic)"""
    import json
    try:
        with Session(engine) as session:
            row = session.exec(select(Setting).where(Setting.key == "settings")).first()
            if row:
                row.value_json = json.dumps(data)
                session.add(row)
                session.commit()
                logger.info(f"Settings saved to database: {DB_PATH}")
            else:
                logger.error("Could not find settings row to update!")
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        raise
    
def get_avatars():
    """Get all enabled avatar configurations from database"""
    from modules.models import AvatarImage
    
    try:
        with Session(engine) as session:
            # Get all enabled avatars from database
            avatars = session.exec(select(AvatarImage).where(AvatarImage.disabled == False)).all()

            return avatars
    except Exception as e:
        logger.error(f"Error loading avatars: {e}")
        return []

def get_all_avatars():
    """Get all avatar configurations from database (including disabled ones)"""
    from modules.models import AvatarImage
    
    try:
        with Session(engine) as session:
            # Get all avatars from database
            avatars = session.exec(select(AvatarImage)).all()
            return avatars
    except Exception as e:
        logger.error(f"Error loading all avatars: {e}")
        return []
    
def get_avatar(avatar_name, avatar_type):
    existing_avatar = None
    with Session(engine) as session:
        query = select(AvatarImage).where(
            AvatarImage.name == avatar_name,
            AvatarImage.avatar_type == avatar_type
        )
        existing_avatar = session.exec(query).first()
    return existing_avatar

def add_avatar(avatar: AvatarImage):
    with Session(engine) as session:
        # Create new avatar           
        session.add(avatar)
        session.commit()
        session.refresh(avatar)

def update_avatar(avatar: AvatarImage):
    """Update an existing avatar in the database"""
    with Session(engine) as session:
        session.add(avatar)
        session.commit()
        session.refresh(avatar)


def delete_avatar(avatar_id: int):
    with Session(engine) as session:
        avatar = session.get(AvatarImage, avatar_id)
        if not avatar:
            return {"error": "Avatar not found", "success": False}
        full_path = os.path.join(PERSISTENT_AVATARS_DIR, avatar.filename)
        if os.path.exists(full_path):
            os.remove(full_path)
            logger.info(f"🗑️  Deleted avatar file: {full_path}")
        session.delete(avatar)
        session.commit()
        return {"success": True}

def delete_avatar_group(group_id: str):
    with Session(engine) as session:
        if group_id.startswith('single_'):
            avatar_id = int(group_id.replace('single_', ''))
            avatars = [session.get(AvatarImage, avatar_id)]
            if not avatars[0]:
                return {"error": "Avatar not found", "success": False}
        else:
            avatars = session.exec(select(AvatarImage).where(AvatarImage.avatar_group_id == group_id)).all()
            if not avatars:
                return {"error": "Avatar group not found", "success": False}
        deleted_count = 0
        for avatar in avatars:
            if avatar:
                full_path = os.path.join(PERSISTENT_AVATARS_DIR, avatar.filename)
                if os.path.exists(full_path):
                    os.remove(full_path)
                    logger.info(f"🗑️  Deleted avatar file: {full_path}")
                session.delete(avatar)
                deleted_count += 1
        session.commit()
        return {"success": True, "deleted_count": deleted_count}

def update_avatar_group_position(group_id: str, spawn_position):
    with Session(engine) as session:
        if group_id.startswith('single_'):
            avatar_id = int(group_id.replace('single_', ''))
            avatars = [session.get(AvatarImage, avatar_id)]
            if not avatars[0]:
                return {"error": "Avatar not found", "success": False}
        else:
            avatars = session.exec(select(AvatarImage).where(AvatarImage.avatar_group_id == group_id)).all()
            if not avatars:
                return {"error": "Avatar group not found", "success": False}
        updated_count = 0
        for avatar in avatars:
            if avatar:
                avatar.spawn_position = spawn_position
                session.add(avatar)
                updated_count += 1
        session.commit()
        return {"success": True, "updated_count": updated_count}

def toggle_avatar_group_disabled(group_id: str):
    with Session(engine) as session:
        if group_id.startswith('single_'):
            avatar_id = int(group_id.replace('single_', ''))
            avatars = [session.get(AvatarImage, avatar_id)]
            if not avatars[0]:
                return {"error": "Avatar not found", "success": False}
        else:
            avatars = session.exec(select(AvatarImage).where(AvatarImage.avatar_group_id == group_id)).all()
            if not avatars:
                return {"error": "Avatar group not found", "success": False}
        any_enabled = any(not avatar.disabled for avatar in avatars if avatar)
        new_disabled_status = any_enabled
        updated_count = 0
        for avatar in avatars:
            if avatar:
                avatar.disabled = new_disabled_status
                session.add(avatar)
                updated_count += 1
        session.commit()
        return {
            "success": True,
            "group_id": group_id,
            "disabled": new_disabled_status,
            "updated_count": updated_count,
            "message": f"Avatar group {'disabled' if new_disabled_status else 'enabled'}"
        }
        
def get_auth():
    with Session(engine) as session:
        auth = session.exec(select(TwitchAuth)).first()
        return auth
    return None

def delete_twitch_auth():
    """Delete Twitch auth from database"""
    with Session(engine) as session:
        auth = session.exec(select(TwitchAuth)).first()
        if auth:
            session.delete(auth)
            session.commit()
            return {"success": True}
        return {"success": False, "error": "No connection found"}

def save_twitch_auth(user_info: dict, token_data: dict):
    """Store or update Twitch auth in database"""
    from datetime import datetime
    
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

def get_twitch_token():
    """Get current Twitch token for bot connection"""
    from datetime import datetime
    
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
    
    return None

# YouTube OAuth functions

def get_youtube_auth():
    """Get YouTube auth from database"""
    with Session(engine) as session:
        auth = session.exec(select(YouTubeAuth)).first()
        return auth
    return None

def delete_youtube_auth():
    """Delete YouTube auth from database"""
    with Session(engine) as session:
        auth = session.exec(select(YouTubeAuth)).first()
        if auth:
            session.delete(auth)
            session.commit()
            return {"success": True}
        return {"success": False, "error": "No connection found"}

def save_youtube_auth(channel_info: dict, token_data: dict):
    """Store or update YouTube auth in database"""
    from datetime import datetime
    
    with Session(engine) as session:
        # Check if auth already exists for this channel
        existing_auth = session.exec(
            select(YouTubeAuth).where(YouTubeAuth.channel_id == channel_info["id"])
        ).first()
        
        if existing_auth:
            # Update existing auth
            existing_auth.access_token = token_data["access_token"]
            existing_auth.refresh_token = token_data.get("refresh_token", "")
            existing_auth.channel_name = channel_info.get("snippet", {}).get("title", "Unknown")
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
            
            new_auth = YouTubeAuth(
                channel_id=channel_info["id"],
                channel_name=channel_info.get("snippet", {}).get("title", "Unknown"),
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", ""),
                expires_at=expires_at,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            session.add(new_auth)
        
        session.commit()
        logger.info(f"Stored YouTube auth for channel: {channel_info.get('snippet', {}).get('title', 'Unknown')}")

def get_youtube_token():
    """Get current YouTube token for bot connection"""
    from datetime import datetime
    
    with Session(engine) as session:
        auth = session.exec(select(YouTubeAuth)).first()
        if auth:
            # Check if token needs refresh (if expires_at is set and in the past)
            if auth.expires_at:
                expires_at = datetime.fromisoformat(auth.expires_at)
                if expires_at <= datetime.now():
                    logger.info("YouTube token expired, attempting refresh...")
                    # TODO: Implement token refresh
                    
            return {
                "access_token": auth.access_token,
                "refresh_token": auth.refresh_token,
                "channel_id": auth.channel_id,
                "channel_name": auth.channel_name
            }
    
    return None

def get_enabled_voices():
    with Session(engine) as session:
        enabled_voices = session.exec(select(Voice).where(Voice.enabled == True)).all()
        return enabled_voices
    return None

def get_voices():
    with Session(engine) as session:
        voices = session.exec(select(Voice)).all()
        return {"voices": [voice.dict() for voice in voices]}

def check_voice_exists(voice_id: str, provider: str):
    with Session(engine) as session:
        # Check if voice already exists
        existing = session.exec(
            select(Voice).where(
                Voice.voice_id == voice_id,
                Voice.provider == provider
            )
        ).first()
        return existing is not None

def get_voice_by_id(voice_id: int):
    with Session(engine) as session:
        voice = session.get(Voice, voice_id)
        return voice
    return None

def add_voice(new_voice: Voice):
    with Session(engine) as session:
        # Create new voice           
        session.add(new_voice)
        session.commit()
        session.refresh(new_voice)

def remove_voice(voice_id: int):
    """Remove a voice by its ID"""
    with Session(engine) as session:
        voice = session.get(Voice, voice_id)
        if voice:
            session.delete(voice)
            session.commit()

def Debug_Database():
    with Session(engine) as session:
            voice_count = session.exec(select(Voice)).all()
            avatar_count = session.exec(select(AvatarImage)).all()
            
            db_info["statistics"] = {
                "voices": len(voice_count),
                "avatars": len(avatar_count),
                "database_path": DB_PATH,
                "user_data_dir": USER_DATA_DIR
            }
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


# ---------- Provider Voice Cache Functions ----------

def get_cached_voices(provider: str, credentials_hash: str = None):
    """Get cached voice list for a provider"""
    with Session(engine) as session:
        query = select(ProviderVoiceCache).where(ProviderVoiceCache.provider == provider)
        cache = session.exec(query).first()
        
        if cache:
            # Check if credentials match (if hash provided)
            if credentials_hash and cache.credentials_hash != credentials_hash:
                logger.info(f"Credentials changed for {provider}, cache invalidated")
                return None
            
            try:
                voices = json.loads(cache.voices_json)
                logger.info(f"📦 Loaded {len(voices)} cached voices for {provider} (last updated: {cache.last_updated})")
                return voices
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse cached voices for {provider}: {e}")
                return None
        
        return None


def save_cached_voices(provider: str, voices: list, credentials_hash: str = None):
    """Save voice list to cache for a provider"""
    with Session(engine) as session:
        # Check if cache exists
        query = select(ProviderVoiceCache).where(ProviderVoiceCache.provider == provider)
        cache = session.exec(query).first()
        
        voices_json = json.dumps(voices)
        now = datetime.now().isoformat()
        
        if cache:
            # Update existing cache
            cache.voices_json = voices_json
            cache.last_updated = now
            cache.credentials_hash = credentials_hash
            session.add(cache)
        else:
            # Create new cache entry
            cache = ProviderVoiceCache(
                provider=provider,
                voices_json=voices_json,
                last_updated=now,
                credentials_hash=credentials_hash
            )
            session.add(cache)
        
        session.commit()
        logger.info(f"💾 Saved {len(voices)} voices to cache for {provider}")


def clear_voice_cache(provider: str = None):
    """Clear voice cache for a specific provider or all providers"""
    with Session(engine) as session:
        if provider:
            cache = session.exec(select(ProviderVoiceCache).where(ProviderVoiceCache.provider == provider)).first()
            if cache:
                session.delete(cache)
                session.commit()
                logger.info(f"🗑️ Cleared voice cache for {provider}")
        else:
            # Clear all caches
            caches = session.exec(select(ProviderVoiceCache)).all()
            for cache in caches:
                session.delete(cache)
            session.commit()
            logger.info("🗑️ Cleared all voice caches")


def hash_credentials(*credentials: str) -> str:
    """Create a hash of credentials to detect changes
    
    Args:
        *credentials: One or more credential strings to hash
        
    Examples:
        hash_credentials(api_key)  # For single credential (Google)
        hash_credentials(access_key, secret_key)  # For multiple credentials (Polly)
    """
    combined = ":".join(credentials)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


