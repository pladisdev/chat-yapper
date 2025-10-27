import asyncio
import os
import uuid
import time
from dataclasses import dataclass
import aiohttp
import random
from collections import defaultdict

from modules import logger
from modules.persistent_data import AUDIO_DIR

# Fallback voice usage tracking for distribution analysis
fallback_voice_stats = defaultdict(int)
fallback_selection_count = 0

def reset_fallback_stats():
    """Reset fallback voice statistics"""
    global fallback_voice_stats, fallback_selection_count
    fallback_voice_stats.clear()
    fallback_selection_count = 0

# Provider 1: MonsterAPI TTS (async, great quality)
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except Exception:
    AIOHTTP_AVAILABLE = False

# Provider 2: Edge TTS (fallback)
try:
    import edge_tts  # type: ignore
except Exception:
    edge_tts = None

@dataclass
class TTSJob:
    text: str
    voice: str
    audio_format: str = "mp3"

class TTSProvider:
    async def synth(self, job: TTSJob) -> str:
        raise NotImplementedError

class MonsterTTSProvider(TTSProvider):
    def __init__(self, api_key: str, voice_id: str = None):
        self.api_key = api_key
        self.voice_id = voice_id
        self.base_url = "https://api.console.tts.monster/generate"
        self.last_request_time = 0
        self.rate_limit_seconds = 2  # 1 request every 2 seconds (30/min)
    
    def can_process_now(self) -> bool:
        """Check if we can make a MonsterTTS request without violating rate limits"""
        current_time = time.time()
        return (current_time - self.last_request_time) >= self.rate_limit_seconds
    
    async def _cleanup_file_after_delay(self, filepath: str, delay_seconds: int):
        """Clean up temporary audio file after delay"""
        import asyncio
        await asyncio.sleep(delay_seconds)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Cleaned up temporary file: {filepath}")
        except Exception as e:
            logger.info(f"Failed to cleanup file {filepath}: {e}")
    
    async def synth(self, job: TTSJob) -> str:
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp not available for MonsterTTS")
        
        if not self.api_key:
            raise RuntimeError("MonsterTTS API key not configured")
        
        # Check rate limit (but be more permissive for debugging)
        if not self.can_process_now():
            time_since_last = time.time() - self.last_request_time
            logger.info(f"MonsterTTS rate limit check: {time_since_last:.2f}s since last request (need {self.rate_limit_seconds}s)")
            raise RuntimeError(f"MonsterTTS rate limit exceeded (wait {self.rate_limit_seconds - time_since_last:.1f}s)")
        
        outpath = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}.{job.audio_format}")
        logger.info(f"MonsterTTS Output Path: {outpath}")
        
        headers = {
            "Authorization": self.api_key,  # Direct token format: ttsm_12345-abcdef
            "Content-Type": "application/json"
        }
        
        payload = {
            "voice_id": job.voice if job.voice else self.voice_id,
            "message": job.text
        }
        
        logger.info(f"MonsterTTS Request Payload: {payload}")
        logger.info(f"MonsterTTS API URL: {self.base_url}")
        
        # Update last request time before making the request
        self.last_request_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, headers=headers, json=payload) as response:
                logger.info(f"MonsterTTS Response Status: {response.status}")
                logger.info(f"MonsterTTS Response Headers: {dict(response.headers)}")
                
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"MonsterTTS error ({response.status}): {error_text}")
                
                # Check if the response is actually audio data
                content_type = response.headers.get('content-type', '')
                logger.info(f"MonsterTTS Content-Type: {content_type}")
                
                audio_data = await response.read()
                logger.info(f"MonsterTTS Audio Data Length: {len(audio_data)} bytes")
                
                # Check if we got JSON response with URL (MonsterTTS format)
                if audio_data.startswith(b'{') or audio_data.startswith(b'['):
                    # Parse JSON response to get audio URL
                    import json
                    try:
                        response_json = json.loads(audio_data.decode('utf-8'))
                        logger.info(f"MonsterTTS JSON Response: {response_json}")
                        
                        if 'url' in response_json:
                            audio_url = response_json['url']
                            logger.info(f"Downloading audio from: {audio_url}")
                            
                            # Download the actual audio file
                            async with session.get(audio_url) as audio_response:
                                if audio_response.status == 200:
                                    actual_audio_data = await audio_response.read()
                                    logger.info(f"Downloaded audio: {len(actual_audio_data)} bytes")
                                    
                                    # Update audio_data for the rest of the processing
                                    audio_data = actual_audio_data
                                else:
                                    raise RuntimeError(f"Failed to download audio from URL: {audio_response.status}")
                        else:
                            # JSON without URL, probably an error
                            raise RuntimeError(f"MonsterTTS returned JSON without URL: {response_json}")
                    except json.JSONDecodeError:
                        # Not valid JSON, treat as error
                        error_text = audio_data.decode('utf-8')
                        raise RuntimeError(f"MonsterTTS returned invalid JSON: {error_text}")
                
                # Ensure we have some data
                if len(audio_data) < 100:  # Audio files should be much larger
                    raise RuntimeError(f"MonsterTTS returned suspiciously small audio data: {len(audio_data)} bytes")
                
                # Write audio to temporary file
                with open(outpath, 'wb') as f:
                    f.write(audio_data)
                
                # Basic audio format validation
                if job.audio_format.lower() == 'mp3':
                    # MP3 files should start with ID3 tag or MP3 frame sync
                    if not (audio_data.startswith(b'ID3') or audio_data[0:2] == b'\xff\xfb' or audio_data[0:2] == b'\xff\xf3'):
                        logger.info(f"Warning: Audio data doesn't look like valid MP3")
                
                logger.info(f"MonsterTTS audio ready: {outpath} ({len(audio_data)} bytes)")
                
                # Schedule file cleanup after a short delay (enough time for frontend to fetch)
                import asyncio
                asyncio.create_task(self._cleanup_file_after_delay(outpath, 30))  # 30 seconds
                
                return outpath
    
    async def list_voices(self, use_cache: bool = True) -> list:
        """Fetch available voices from MonsterTTS API with caching support
        
        Args:
            use_cache: If True, return cached voices if available and credentials haven't changed.
                      If False, force refresh from MonsterTTS API.
        """
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp not available for MonsterTTS")
        
        if not self.api_key:
            raise RuntimeError("MonsterTTS API key not configured")
        
        # Check cache first if requested
        if use_cache:
            from modules.persistent_data import get_cached_voices, hash_credentials
            credentials_hash = hash_credentials(self.api_key)
            cached_voices = get_cached_voices("monstertts", credentials_hash)
            if cached_voices:
                logger.info(f"Using cached MonsterTTS voices ({len(cached_voices)} voices)")
                return cached_voices
        
        logger.info(f"Fetching MonsterTTS voices from API...")
        
        headers = {
            "Authorization": self.api_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.console.tts.monster/voices", headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"MonsterTTS list voices error ({response.status}): {error_text}")
                
                voices_data = await response.json()
                logger.info(f"MonsterTTS API Response: {voices_data}")
                
                # Transform the API response to our format
                voices = []
                
                # Handle different response formats
                if isinstance(voices_data, list):
                    # Response is a list of voices
                    for voice in voices_data:
                        if isinstance(voice, dict):
                            voices.append({
                                "voice_id": voice.get("id", voice.get("voice_id", voice.get("uuid", "unknown"))),
                                "name": voice.get("name", voice.get("display_name", f"Voice {voice.get('id', 'Unknown')[:8]}"))
                            })
                elif isinstance(voices_data, dict):
                    # Response might be wrapped in an object
                    voices_list = voices_data.get("voices", voices_data.get("data", [voices_data]))
                    for voice in voices_list:
                        if isinstance(voice, dict):
                            voices.append({
                                "voice_id": voice.get("id", voice.get("voice_id", voice.get("uuid", "unknown"))),
                                "name": voice.get("name", voice.get("display_name", f"Voice {voice.get('id', 'Unknown')[:8]}"))
                            })
                
                logger.info(f"Fetched {len(voices)} MonsterTTS voices from API")
                
                # Save to cache
                from modules.persistent_data import save_cached_voices, hash_credentials
                credentials_hash = hash_credentials(self.api_key)
                save_cached_voices("monstertts", voices, credentials_hash)
                logger.info(f"Cached {len(voices)} MonsterTTS voices")
                
                return voices

class EdgeTTSProvider(TTSProvider):
    async def list_voices(self, use_cache: bool = True) -> list:
        """Fetch available voices from Edge TTS with caching support
        
        Args:
            use_cache: If True, return cached voices if available.
                      If False, force refresh from Edge TTS.
        
        Note: Edge TTS is free and doesn't require credentials.
        """
        if edge_tts is None:
            raise RuntimeError("edge-tts not available")
        
        # Check cache first if requested (no credential hash needed for free service)
        if use_cache:
            from modules.persistent_data import get_cached_voices
            cached_voices = get_cached_voices("edge", "")
            if cached_voices:
                logger.info(f"Using cached Edge TTS voices ({len(cached_voices)} voices)")
                return cached_voices
        
        logger.info(f"Fetching Edge TTS voices from API...")
        
        try:
            # Get all voices from edge-tts
            all_voices = await edge_tts.list_voices()
        except Exception as e:
            logger.error(f"Failed to fetch voices from Edge TTS API: {e}")
            raise RuntimeError("edge-tts not available")
        
        english_voices = []
        for v in all_voices:
            locale = v.get('Locale') if isinstance(v, dict) else getattr(v, 'Locale', None)
            if locale and locale.startswith('en'):
                english_voices.append(v)
        
        voices = []
        for voice in english_voices:
            try:
                # Try dict access first, then attribute access
                if isinstance(voice, dict):
                    short_name = voice.get('ShortName', voice.get('Name', 'Unknown'))
                    # Some versions use FriendlyName instead of DisplayName
                    display_name = voice.get('DisplayName', voice.get('FriendlyName', voice.get('LocalName', short_name)))
                    gender = voice.get('Gender', 'Unknown')
                    locale = voice.get('Locale', 'en-US')
                else:
                    # Handle object attributes
                    short_name = getattr(voice, 'ShortName', getattr(voice, 'Name', 'Unknown'))
                    display_name = getattr(voice, 'DisplayName', getattr(voice, 'FriendlyName', getattr(voice, 'LocalName', short_name)))
                    gender = getattr(voice, 'Gender', 'Unknown')
                    locale = getattr(voice, 'Locale', 'en-US')
                
                clean_name = display_name
                if 'Microsoft' in display_name:
                    parts = display_name.replace('Microsoft ', '').split(' Online')
                    if parts:
                        clean_name = parts[0].strip()
                
                # Format: "Jenny - Female (en-US)"
                voices.append({
                    "voice_id": short_name,
                    "name": f"{clean_name} - {gender} ({locale})",
                    "gender": gender,
                    "locale": locale
                })
            except Exception as e:
                logger.warning(f"Failed to parse voice data: {e}, voice data: {voice}")
                continue
        
        logger.info(f"Fetched {len(voices)} English Edge TTS voices from API")
        
        from modules.persistent_data import save_cached_voices
        save_cached_voices("edge", voices, "")
        logger.info(f"Cached {len(voices)} Edge TTS voices")
        
        return voices
    
    async def synth(self, job: TTSJob) -> str:
        if edge_tts is None:
            raise RuntimeError("edge-tts not available")
        
        # Validate text
        if not job.text or not job.text.strip():
            raise ValueError("Cannot synthesize empty text")
        
        # Validate voice ID
        if not job.voice:
            logger.warning("No voice ID provided, using default")
            job.voice = self.voice_id
        
        # Validate that the voice exists (optional but recommended)
        try:
            # Quick validation: check if voice is in our cached list or API list
            available_voices = await self.list_voices(use_cache=True)
            voice_ids = [v['voice_id'] for v in available_voices]
            
            if job.voice not in voice_ids:
                logger.warning(f"Voice '{job.voice}' not found in available voices list")
                # Don't fail here, let Edge TTS try anyway (in case our list is outdated)
        except Exception as e:
            logger.debug(f"Could not validate voice (continuing anyway): {e}")
        
        outpath = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}.{job.audio_format}")
        
        try:
            communicate = edge_tts.Communicate(job.text, job.voice)
            await communicate.save(outpath)
        except edge_tts.exceptions.NoAudioReceived as e:
            logger.error(f"Edge TTS NoAudioReceived error - Voice: {job.voice}, Text: '{job.text[:50]}...'")
            
            # Try to suggest valid voices
            try:
                available_voices = await self.list_voices(use_cache=True)
                logger.info(f"Hint: There are {len(available_voices)} valid Edge TTS voices available. Refresh the voice list in settings.")
            except:
                pass
            
            # Try with default voice as fallback
            if job.voice != self.voice_id:
                logger.warning(f"Voice '{job.voice}' appears to be invalid or deprecated. Retrying with default voice: {self.voice_id}")
                try:
                    communicate = edge_tts.Communicate(job.text, self.voice_id)
                    await communicate.save(outpath)
                    logger.info(f"Successfully synthesized with fallback voice: {self.voice_id}")
                except edge_tts.exceptions.NoAudioReceived:
                    raise RuntimeError(f"Edge TTS failed with both '{job.voice}' and fallback '{self.voice_id}'. The voices may be invalid or Edge TTS service is unavailable. Please refresh your voice list in Settings → TTS → Edge TTS.")
            else:
                raise RuntimeError(f"Edge TTS failed: {str(e)}. Voice '{job.voice}' may be invalid or deprecated. Please refresh your voice list in Settings → TTS → Edge TTS and select a different voice.")
        except Exception as e:
            logger.error(f"Edge TTS synthesis failed: {e}")
            raise
        
        # Schedule cleanup after 30 seconds
        asyncio.create_task(self._cleanup_file_after_delay(outpath, 30))
        
        logger.info(f'Edge TTS audio ready: {outpath}')
        return outpath
    
    async def _cleanup_file_after_delay(self, filepath: str, delay_seconds: int):
        """Clean up temporary audio file after delay"""
        import asyncio
        await asyncio.sleep(delay_seconds)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Cleaned up temporary file: {filepath}")
        except Exception as e:
            logger.info(f"Failed to cleanup file {filepath}: {e}")

class GoogleTTSProvider(TTSProvider):
    """Google Cloud Text-to-Speech provider"""
    
    def __init__(self, api_key: str, voice_id: str = "en-US-Neural2-F"):
        self.api_key = api_key
        self.voice_id = voice_id
        self.base_url = "https://texttospeech.googleapis.com/v1/text:synthesize"
    
    async def list_voices(self, use_cache: bool = True) -> list:
        """Fetch available voices from Google Cloud TTS API with caching support
        
        Args:
            use_cache: If True, return cached voices if available and credentials haven't changed.
                      If False, force refresh from Google API.
        """
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp not available for Google TTS")
        
        if not self.api_key:
            raise RuntimeError("Google TTS API key not configured")
        
        # Check cache first if requested
        if use_cache:
            from modules.persistent_data import get_cached_voices, hash_credentials
            credentials_hash = hash_credentials(self.api_key)
            cached_voices = get_cached_voices("google", credentials_hash)
            if cached_voices:
                logger.info(f"Using cached Google TTS voices ({len(cached_voices)} voices)")
                return cached_voices
        
        list_voices_url = "https://texttospeech.googleapis.com/v1/voices"
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        logger.info(f"Fetching Google TTS voices from API...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(list_voices_url, headers=headers) as response:
                logger.info(f"Google TTS List Voices Response Status: {response.status}")
                
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Google TTS list voices error ({response.status}): {error_text}")
                
                response_data = await response.json()
                
                voices = []
                skipped_voices = []
                if 'voices' in response_data:
                    for voice in response_data['voices']:
                        # Get the voice name and language codes
                        voice_name = voice.get('name', 'Unknown')
                        language_codes = voice.get('languageCodes', [])
                        ssml_gender = voice.get('ssmlGender', 'UNSPECIFIED')
                        natural_sample_rate = voice.get('naturalSampleRateHertz', 24000)
                        
                        # Only include English voices (starting with "en")
                        # Standard English voices follow patterns like: en-US-Standard-A, en-US-Wavenet-A, en-US-Neural2-A, en-GB-Neural2-B, etc.
                        voice_lower = voice_name.lower()
                        
                        # Check if voice starts with "en" (English)
                        voice_parts = voice_name.split('-')
                        is_english = len(voice_parts) >= 3 and voice_parts[0] == 'en'
                        
                        # Skip non-English voices and unsupported voices (Journey, Chirp, etc.)
                        if not is_english or any(unsupported in voice_lower for unsupported in [
                            'journey', 'chirp', 
                            # Star names (Journey voices)
                            'alnilam', 'vega', 'altair', 'bellatrix', 'rigel', 'sirius', 'procyon', 'capella', 'arcturus', 'aldebaran',
                            # Moon/Saturn names (additional preview voices)
                            'iapetus', 'titan', 'rhea', 'dione', 'tethys', 'enceladus', 'mimas', 'hyperion', 'phoebe'
                        ]):
                            skipped_voices.append(voice_name)
                            continue
                        
                        # Create a friendly display name
                        gender_map = {
                            'MALE': 'Male',
                            'FEMALE': 'Female', 
                            'NEUTRAL': 'Neutral',
                            'SSML_VOICE_GENDER_UNSPECIFIED': 'Unspecified'
                        }
                        gender_display = gender_map.get(ssml_gender, 'Unknown')
                        
                        # Add each language code as a separate voice option
                        for lang_code in language_codes:
                            display_name = f"{voice_name} - {gender_display} ({lang_code})"
                            voices.append({
                                "voice_id": voice_name,
                                "name": display_name,
                                "language_code": lang_code,
                                "gender": ssml_gender,
                                "sample_rate": natural_sample_rate
                            })
                
                if skipped_voices:
                    logger.info(f"Skipped {len(skipped_voices)} non-English/unsupported Google TTS voices: {', '.join(skipped_voices[:5])}{' and more...' if len(skipped_voices) > 5 else ''}")
                logger.info(f"Fetched {len(voices)} English Google TTS voices from API")
                
                # Save to cache
                from modules.persistent_data import save_cached_voices, hash_credentials
                credentials_hash = hash_credentials(self.api_key)
                save_cached_voices("google", voices, credentials_hash)
                logger.info(f"Cached {len(voices)} Google TTS voices")
                
                return voices

    async def synth(self, job: TTSJob) -> str:
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp not available for Google TTS")
        
        if not self.api_key:
            raise RuntimeError("Google TTS API key not configured")
        
        outpath = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}.{job.audio_format}")
        
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Parse voice ID to get language and voice name
        voice_parts = job.voice.split('-')
        language_code = '-'.join(voice_parts[:2]) if len(voice_parts) >= 2 else "en-US"
        
        payload = {
            "input": {"text": job.text},
            "voice": {
                "languageCode": language_code,
                "name": job.voice
            },
            "audioConfig": {
                "audioEncoding": "MP3" if job.audio_format.lower() == "mp3" else "LINEAR16"
            }
        }
        
        logger.info(f"Google TTS Request: {payload}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, headers=headers, json=payload) as response:
                logger.info(f"Google TTS Response Status: {response.status}")
                
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Google TTS error ({response.status}): {error_text}")
                
                response_data = await response.json()
                
                if 'audioContent' in response_data:
                    import base64
                    audio_data = base64.b64decode(response_data['audioContent'])
                    logger.info(f"Google TTS audio decoded: {len(audio_data)} bytes")
                    
                    with open(outpath, 'wb') as f:
                        f.write(audio_data)
                    
                    # Schedule cleanup after 30 seconds
                    asyncio.create_task(self._cleanup_file_after_delay(outpath, 30))
                    
                    logger.info(f"Google TTS audio ready: {outpath}")
                    return outpath
                else:
                    raise RuntimeError(f"Google TTS response missing audioContent: {response_data}")
    
    async def _cleanup_file_after_delay(self, filepath: str, delay_seconds: int):
        """Clean up temporary audio file after delay"""
        import asyncio
        await asyncio.sleep(delay_seconds)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Cleaned up temporary file: {filepath}")
        except Exception as e:
            logger.info(f"Failed to cleanup file {filepath}: {e}")

class AmazonPollyProvider(TTSProvider):
    """Amazon Polly Text-to-Speech provider"""
    
    def __init__(self, aws_access_key: str, aws_secret_key: str, aws_region: str = "us-east-1", voice_id: str = "Joanna"):
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_region = aws_region
        self.voice_id = voice_id
        self.base_url = f"https://polly.{aws_region}.amazonaws.com/"
    
    async def list_voices(self, use_cache: bool = True) -> list:
        """Fetch available voices from Amazon Polly API"""
        try:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError
        except ImportError:
            raise RuntimeError("boto3 not installed. Run: pip install boto3")
        
        if not self.aws_access_key or not self.aws_secret_key:
            raise RuntimeError("Amazon Polly credentials not configured")
        
        # Check cache first
        if use_cache:
            from modules.persistent_data import get_cached_voices, hash_credentials, clear_voice_cache
            credentials_hash = hash_credentials(self.aws_access_key, self.aws_secret_key)
            cached_voices = get_cached_voices("polly", credentials_hash)
            if cached_voices:
                # Check if cache has old format (using 'id' instead of 'voice_id')
                needs_migration = any('id' in voice and 'voice_id' not in voice for voice in cached_voices)
                if needs_migration:
                    logger.info("Old Polly cache format detected, clearing cache to refresh...")
                    clear_voice_cache("polly")
                    cached_voices = None  # Force refresh
                else:
                    logger.info(f"Using cached Polly voices ({len(cached_voices)} voices)")
                    return cached_voices
        
        try:
            # Create Polly client
            polly_client = boto3.client(
                'polly',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region
            )
            
            logger.info(f"Fetching voices from Amazon Polly API (region: {self.aws_region})...")
            
            # Get all voices
            response = polly_client.describe_voices()
            
            # Format voices for our system
            polly_voices = []
            for voice in response.get('Voices', []):
                polly_voices.append({
                    'voice_id': voice['Id'],  # Use voice_id for consistency with other providers
                    'name': voice['Name'],
                    'gender': voice.get('Gender', 'Unknown'),
                    'language': voice.get('LanguageName', 'Unknown'),
                    'language_code': voice.get('LanguageCode', ''),
                    'engine': ', '.join(voice.get('SupportedEngines', [])),
                    'provider': 'polly'
                })
            
            logger.info(f"Fetched {len(polly_voices)} voices from Amazon Polly")
            
            # Save to cache
            from modules.persistent_data import save_cached_voices, hash_credentials
            credentials_hash = hash_credentials(self.aws_access_key, self.aws_secret_key)
            save_cached_voices("polly", polly_voices, credentials_hash)
            
            return polly_voices
            
        except (BotoCoreError, ClientError) as error:
            error_msg = f"Amazon Polly API error: {str(error)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Failed to fetch Polly voices: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    async def synth(self, job: TTSJob) -> str:
        """Synthesize speech using Amazon Polly"""
        try:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError
        except ImportError:
            raise RuntimeError("boto3 not installed. Run: pip install boto3")
        
        if not self.aws_access_key or not self.aws_secret_key:
            raise RuntimeError("Amazon Polly credentials not configured")
        
        outpath = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}.{job.audio_format}")
        
        try:
            # Create Polly client
            polly_client = boto3.client(
                'polly',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region
            )
            
            # Determine output format
            output_format = 'mp3' if job.audio_format == 'mp3' else 'ogg_vorbis'
            
            logger.info(f"Amazon Polly: Synthesizing '{job.text[:50]}...' with voice '{job.voice or self.voice_id}'")
            
            # Synthesize speech
            response = polly_client.synthesize_speech(
                Text=job.text,
                OutputFormat=output_format,
                VoiceId=job.voice or self.voice_id,
                Engine='neural' if job.voice in ['Joanna', 'Matthew', 'Ruth', 'Stephen'] else 'standard'
            )
            
            # Save audio stream to file
            if 'AudioStream' in response:
                with open(outpath, 'wb') as f:
                    f.write(response['AudioStream'].read())
                
                logger.info(f"Amazon Polly: Audio generated successfully: {outpath}")
                
                # Schedule cleanup after 30 seconds
                asyncio.create_task(self._cleanup_file_after_delay(outpath, 30))
                
                return outpath
            else:
                raise RuntimeError("Amazon Polly response missing AudioStream")
                
        except (BotoCoreError, ClientError) as error:
            raise RuntimeError(f"Amazon Polly error: {str(error)}")
        except Exception as e:
            raise RuntimeError(f"Amazon Polly synthesis failed: {str(e)}")
    
    async def _cleanup_file_after_delay(self, filepath: str, delay_seconds: int):
        """Clean up temporary audio file after delay"""
        import asyncio
        await asyncio.sleep(delay_seconds)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Cleaned up temporary file: {filepath}")
        except Exception as e:
            logger.info(f"Failed to cleanup file {filepath}: {e}")
    
    async def _cleanup_file_after_delay(self, filepath: str, delay_seconds: int):
        """Clean up temporary audio file after delay"""
        import asyncio
        await asyncio.sleep(delay_seconds)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Cleaned up temporary file: {filepath}")
        except Exception as e:
            logger.info(f"Failed to cleanup file {filepath}: {e}")

class HybridTTSProvider(TTSProvider):
    """Hybrid provider that uses MonsterTTS when available and under rate limit,
    falls back to random configured voices when rate limited or MonsterTTS unavailable."""
    
    def __init__(self, monster_api_key: str = None, monster_voice_id: str = None, edge_voice_id: str = None, 
                 fallback_voices: list = None, google_api_key: str = None, polly_config: dict = None):
        self.monster_provider = None
        self.edge_provider = None
        self.google_provider = None
        self.polly_provider = None
        self.fallback_voices = fallback_voices or []
        
        # Initialize MonsterTTS if API key provided
        if monster_api_key and AIOHTTP_AVAILABLE:
            self.monster_provider = MonsterTTSProvider(monster_api_key, monster_voice_id or "9aad4a1b-f04e-43a1-8ff5-4830115a10a8")
        
        # Initialize Edge TTS as fallback
        if edge_tts is not None:
            self.edge_provider = EdgeTTSProvider()
        
        # Initialize Google TTS if API key provided
        if google_api_key and AIOHTTP_AVAILABLE:
            self.google_provider = GoogleTTSProvider(google_api_key)
        
        # Initialize Amazon Polly if credentials provided
        if polly_config and polly_config.get('accessKey') and polly_config.get('secretKey') and AIOHTTP_AVAILABLE:
            self.polly_provider = AmazonPollyProvider(
                polly_config['accessKey'],
                polly_config['secretKey'],
                polly_config.get('region', 'us-east-1')
            )
        
        self.edge_voice_id = edge_voice_id
        self.monster_voice_id = monster_voice_id
    
    async def synth(self, job: TTSJob) -> str:
        # Determine which provider to use based on the job's voice
        # The job.voice should be the actual voice_id from the selected voice
        
        # First, check if we have a MonsterTTS voice and can use MonsterTTS
        if (self.monster_provider and self.monster_voice_id and 
            job.voice == self.monster_voice_id and self.monster_provider.can_process_now()):
            try:
                logger.info("Using MonsterTTS")
                return await self.monster_provider.synth(job)
            except Exception as e:
                logger.info(f"MonsterTTS failed: {e}, falling back")
        
        # If we have an Edge TTS voice, use Edge TTS directly
        if self.edge_provider and self.edge_voice_id and job.voice == self.edge_voice_id:
            logger.info("Using Edge TTS")
            return await self.edge_provider.synth(job)
        
        # If the voice doesn't match our configured voices, try to find it in fallback voices
        if self.fallback_voices:
            # Find the voice in fallback_voices that matches the job.voice
            matching_voice = next((v for v in self.fallback_voices if v.voice_id == job.voice), None)
            
            if matching_voice:
                logger.info(f"Using configured voice: {matching_voice.name} ({matching_voice.provider})")
                
                if matching_voice.provider == "edge" and self.edge_provider:
                    return await self.edge_provider.synth(job)
                elif matching_voice.provider == "monstertts" and self.monster_provider:
                    # Check rate limit for MonsterTTS voices
                    if self.monster_provider.can_process_now():
                        try:
                            return await self.monster_provider.synth(job)
                        except Exception as e:
                            logger.info(f"MonsterTTS voice failed: {e}, trying random fallback")
                    else:
                        logger.info("MonsterTTS rate limited, trying random fallback")
                elif matching_voice.provider == "google" and self.google_provider:
                    try:
                        return await self.google_provider.synth(job)
                    except Exception as e:
                        logger.info(f"Google TTS voice failed: {e}, trying random fallback")
                elif matching_voice.provider == "polly" and self.polly_provider:
                    try:
                        return await self.polly_provider.synth(job)
                    except Exception as e:
                        logger.info(f"Amazon Polly voice failed: {e}, trying random fallback")
            
            # Random fallback from enabled voices
            fallback_voice = random.choice(self.fallback_voices)
            
            # Track fallback voice usage for distribution analysis
            global fallback_voice_stats, fallback_selection_count
            fallback_key = f"{fallback_voice.name} ({fallback_voice.provider})"
            fallback_voice_stats[fallback_key] += 1
            fallback_selection_count += 1
            
            logger.info(f"Using random fallback voice: {fallback_voice.name} ({fallback_voice.provider})")
            
            # Log fallback distribution every 5 selections
            if fallback_selection_count % 5 == 0:
                logger.info(f"\nFallback Voice Distribution Summary (after {fallback_selection_count} fallbacks):")
                total_fallbacks = sum(fallback_voice_stats.values())
                for voice_name, count in sorted(fallback_voice_stats.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / total_fallbacks) * 100
                    logger.info(f"   {voice_name}: {count} times ({percentage:.1f}%)")
                logger.info("---")
            
            fallback_job = TTSJob(
                text=job.text,
                voice=fallback_voice.voice_id,
                audio_format=job.audio_format
            )
            
            if fallback_voice.provider == "edge" and self.edge_provider:
                return await self.edge_provider.synth(fallback_job)
            elif fallback_voice.provider == "monstertts" and self.monster_provider:
                # For random fallback, ignore rate limit temporarily
                try:
                    return await self.monster_provider.synth(fallback_job)
                except Exception as e:
                    logger.info(f"MonsterTTS random fallback failed: {e}")
            elif fallback_voice.provider == "google" and self.google_provider:
                try:
                    return await self.google_provider.synth(fallback_job)
                except Exception as e:
                    logger.info(f"Google TTS random fallback failed: {e}")
            elif fallback_voice.provider == "polly" and self.polly_provider:
                try:
                    return await self.polly_provider.synth(fallback_job)
                except Exception as e:
                    logger.info(f"Amazon Polly random fallback failed: {e}")
        
        # Final fallback to Edge TTS with default voice
        if self.edge_provider:
            logger.info("Using Edge TTS with default voice")
            default_job = TTSJob(
                text=job.text,
                voice="en-US-AvaNeural",
                audio_format=job.audio_format
            )
            return await self.edge_provider.synth(default_job)
        

        return None

# Factory functions
async def get_hybrid_provider(monster_api_key: str = None, monster_voice_id: str = None, edge_voice_id: str = None, 
                             fallback_voices: list = None, google_api_key: str = None, polly_config: dict = None) -> HybridTTSProvider:
    """Get a hybrid provider that uses all TTS providers with intelligent fallback"""
    return HybridTTSProvider(monster_api_key, monster_voice_id, edge_voice_id, fallback_voices, google_api_key, polly_config)

async def get_provider(api_key: str = None, voice_id: str = "9aad4a1b-f04e-43a1-8ff5-4830115a10a8") -> TTSProvider:
    """Legacy factory - Try MonsterTTS first if API key is provided, otherwise Edge TTS"""
    # Try MonsterTTS first if API key is provided
    if api_key and AIOHTTP_AVAILABLE:
        return MonsterTTSProvider(api_key, voice_id)
    
    # Fallback to Edge TTS
    if edge_tts is not None:
        return EdgeTTSProvider()
    
    # Final fallback to fake tone
    return None

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
            logger.info(f"Audio duration for {os.path.basename(file_path)}: {duration:.2f}s (mutagen)")
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
            logger.info(f"Audio duration estimated for {os.path.basename(file_path)}: ~{estimated_duration:.2f}s (file size)")
            return estimated_duration
        except Exception as e:
            logger.debug(f"Failed to estimate duration from file size: {e}")
        
        return None
        
    except Exception as e:
        logger.warning(f"Failed to get audio duration: {e}")
        return None