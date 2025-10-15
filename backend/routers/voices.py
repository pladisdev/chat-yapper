"""
Voice management router
"""
import datetime

import aiohttp
from fastapi import APIRouter

from modules import logger
from modules.models import Voice

from modules.persistent_data import get_voices, check_voice_exists, add_voice, get_voice_by_id, remove_voice
router = APIRouter()

@router.get("/api/voices")
async def api_get_voices():
    """Get all configured voices"""
    return get_voices()

@router.post("/api/voices")
async def api_add_voice(voice_data: dict):
    """Add a new voice"""

    Voice.voice_id == voice_data["voice_id"],
    Voice.provider == voice_data["provider"]


    existing = check_voice_exists(voice_data["voice_id"], voice_data["provider"])

    if existing:
        return {"error": "Voice already exists", "voice": existing.dict()}
    
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

    add_voice(new_voice)
    return {"success": True, "voice": new_voice.dict()}

@router.put("/api/voices/{voice_id}")
async def api_update_voice(voice_id: int, voice_data: dict):
    """Update a voice (enable/disable, change avatar, etc.)"""

    voice = get_voice_by_id(voice_id)
   
    if not voice:
        return {"error": "Voice not found"}
        
    # Update fields
    if "name" in voice_data:
        voice.name = voice_data["name"]
    if "enabled" in voice_data:
        voice.enabled = voice_data["enabled"]
    if "avatar_image" in voice_data:
        voice.avatar_image = voice_data["avatar_image"]

    add_voice(voice)

    return {"success": True, "voice": voice.dict()}

@router.delete("/api/voices/{voice_id}")
async def api_delete_voice(voice_id: int):
    """Delete a voice"""
    remove_voice(voice_id)

    return {"success": True}

@router.get("/api/available-voices/{provider}")
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
            from modules.tts import GoogleTTSProvider
            google_provider = GoogleTTSProvider(api_key)
            voices = await google_provider.list_voices()
            return {"voices": voices}
        except Exception as e:
            return {"error": f"Error fetching Google TTS voices: {str(e)}"}
    else:
        return {"error": "Unknown provider"}

@router.post("/api/available-voices/polly")
async def api_get_polly_voices(credentials: dict):
    """Get available voices from Amazon Polly (with caching)"""
    try:
        from modules.tts import AmazonPollyProvider
        from modules import logger
        
        refresh = credentials.get('refresh', False)
        use_cache = not refresh
        
        polly_provider = AmazonPollyProvider(
            credentials.get('accessKey', ''),
            credentials.get('secretKey', ''),
            credentials.get('region', 'us-east-1')
        )
        
        if refresh:
            logger.info("🔄 Force refresh requested for Polly voices")
        
        voices = await polly_provider.list_voices(use_cache=use_cache)
        
        # Get cache info
        from modules.persistent_data import get_cached_voices, hash_credentials
        credentials_hash = hash_credentials(credentials.get('accessKey', ''), credentials.get('secretKey', ''))
        
        # Get the cache entry to find last_updated
        from modules.persistent_data import Session, engine, select, ProviderVoiceCache
        with Session(engine) as session:
            cache = session.exec(select(ProviderVoiceCache).where(ProviderVoiceCache.provider == "polly")).first()
            last_updated = cache.last_updated if cache else None
        
        return {
            "voices": voices,
            "cached": use_cache and len(voices) > 0,
            "last_updated": last_updated
        }
    except Exception as e:
        from modules import logger
        logger.error(f"Error fetching Polly voices: {e}")
        return {"error": f"Error fetching Polly voices: {str(e)}"}

@router.post("/api/available-voices/google")
async def api_get_google_voices(credentials: dict):
    """Get available voices from Google Cloud TTS (with caching)"""
    try:
        from modules.tts import GoogleTTSProvider
        from modules import logger
        
        api_key = credentials.get('apiKey', '')
        if not api_key:
            return {"error": "API key required for Google TTS voices"}
        
        refresh = credentials.get('refresh', False)
        use_cache = not refresh
        
        google_provider = GoogleTTSProvider(api_key)
        
        if refresh:
            logger.info("🔄 Force refresh requested for Google TTS voices")
        
        voices = await google_provider.list_voices(use_cache=use_cache)
        
        # Get cache info
        from modules.persistent_data import get_cached_voices, hash_credentials
        credentials_hash = hash_credentials(api_key)
        
        # Get the cache entry to find last_updated
        from modules.persistent_data import Session, engine, select, ProviderVoiceCache
        with Session(engine) as session:
            cache = session.exec(select(ProviderVoiceCache).where(ProviderVoiceCache.provider == "google")).first()
            last_updated = cache.last_updated if cache else None
        
        return {
            "voices": voices,
            "cached": use_cache and len(voices) > 0,
            "last_updated": last_updated
        }
    except Exception as e:
        from modules import logger
        logger.error(f"Error fetching Google TTS voices: {e}")
        return {"error": f"Error fetching Google TTS voices: {str(e)}"}

@router.post("/api/available-voices/monstertts")
async def api_get_monstertts_voices(credentials: dict):
    """Get available voices from MonsterTTS (with caching)"""
    try:
        from modules.tts import MonsterTTSProvider
        from modules import logger
        
        api_key = credentials.get('apiKey', '')
        if not api_key:
            return {"error": "API key required for MonsterTTS voices"}
        
        refresh = credentials.get('refresh', False)
        use_cache = not refresh
        
        monster_provider = MonsterTTSProvider(api_key)
        
        if refresh:
            logger.info("🔄 Force refresh requested for MonsterTTS voices")
        
        voices = await monster_provider.list_voices(use_cache=use_cache)
        
        # Get cache info
        from modules.persistent_data import get_cached_voices, hash_credentials
        credentials_hash = hash_credentials(api_key)
        
        # Get the cache entry to find last_updated
        from modules.persistent_data import Session, engine, select, ProviderVoiceCache
        with Session(engine) as session:
            cache = session.exec(select(ProviderVoiceCache).where(ProviderVoiceCache.provider == "monstertts")).first()
            last_updated = cache.last_updated if cache else None
        
        return {
            "voices": voices,
            "cached": use_cache and len(voices) > 0,
            "last_updated": last_updated
        }
    except Exception as e:
        from modules import logger
        logger.error(f"Error fetching MonsterTTS voices: {e}")
        return {"error": f"Error fetching MonsterTTS voices: {str(e)}"}

@router.post("/api/available-voices/edge")
async def api_get_edge_voices(request: dict = None):
    """Get available voices from Edge TTS (with caching)
    
    Note: Edge TTS is free and doesn't require credentials.
    """
    try:
        from modules.tts import EdgeTTSProvider
        from modules import logger
        
        # Edge TTS doesn't need credentials, but we support refresh parameter
        refresh = request.get('refresh', False) if request else False
        use_cache = not refresh
        
        edge_provider = EdgeTTSProvider()
        
        if refresh:
            logger.info("🔄 Force refresh requested for Edge TTS voices")
        
        voices = await edge_provider.list_voices(use_cache=use_cache)
        
        # Get cache info (no credential hash for free service)
        from modules.persistent_data import Session, engine, select, ProviderVoiceCache
        with Session(engine) as session:
            cache = session.exec(select(ProviderVoiceCache).where(ProviderVoiceCache.provider == "edge")).first()
            last_updated = cache.last_updated if cache else None
        
        return {
            "voices": voices,
            "cached": use_cache and len(voices) > 0,
            "last_updated": last_updated
        }
    except Exception as e:
        from modules import logger
        logger.error(f"Error fetching Edge TTS voices: {e}")
        return {"error": f"Error fetching Edge TTS voices: {str(e)}"}