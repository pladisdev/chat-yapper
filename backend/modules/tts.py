import asyncio
import logging
import os
import uuid
import time
from dataclasses import dataclass
from typing import Optional
import aiohttp
import json
import random
from collections import defaultdict

# Get logger for this module
logger = logging.getLogger('ChatYapper.TTS')

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

AUDIO_DIR = os.environ.get("AUDIO_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "audio")))
os.makedirs(AUDIO_DIR, exist_ok=True)

@dataclass
class TTSJob:
    text: str
    voice: str
    audio_format: str = "mp3"

class TTSProvider:
    async def synth(self, job: TTSJob) -> str:
        raise NotImplementedError

class MonsterTTSProvider(TTSProvider):
    def __init__(self, api_key: str, voice_id: str = "9aad4a1b-f04e-43a1-8ff5-4830115a10a8"):
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

class EdgeTTSProvider(TTSProvider):
    async def synth(self, job: TTSJob) -> str:
        if edge_tts is None:
            raise RuntimeError("edge-tts not available")
        outpath = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}.{job.audio_format}")
        communicate = edge_tts.Communicate(job.text, job.voice)
        await communicate.save(outpath)
        
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
    
    async def list_voices(self) -> list:
        """Fetch available voices from Google Cloud TTS API"""
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp not available for Google TTS")
        
        if not self.api_key:
            raise RuntimeError("Google TTS API key not configured")
        
        list_voices_url = "https://texttospeech.googleapis.com/v1/voices"
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        logger.info(f"Fetching Google TTS voices...")
        
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
                        
                        # Skip voices that don't follow standard naming convention
                        # Standard Google voices follow patterns like: en-US-Standard-A, en-US-Wavenet-A, en-US-Neural2-A, etc.
                        # Non-standard voices (Journey, Chirp, star/moon names) aren't supported by v1 API
                        voice_lower = voice_name.lower()
                        
                        # Check if voice has standard prefix (language-region-type format)
                        voice_parts = voice_name.split('-')
                        has_standard_format = len(voice_parts) >= 3 and voice_parts[0] in ['en', 'es', 'fr', 'de', 'it', 'pt', 'ja', 'ko', 'zh', 'ar', 'hi', 'ru', 'nl', 'pl', 'sv', 'da', 'fi', 'no', 'tr', 'uk', 'cs', 'el', 'he', 'id', 'ms', 'th', 'vi', 'bn', 'ta', 'te', 'mr', 'gu', 'kn', 'ml', 'ur', 'af', 'bg', 'ca', 'hr', 'et', 'fil', 'hu', 'is', 'lv', 'lt', 'ro', 'sk', 'sl', 'sr', 'cmn', 'yue']
                        
                        # Skip non-standard voices (including star/moon names like Alnilam, Iapetus, etc.)
                        if not has_standard_format or any(unsupported in voice_lower for unsupported in [
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
                    logger.info(f"Skipped {len(skipped_voices)} unsupported Google TTS voices (Journey/Chirp): {', '.join(skipped_voices[:5])}{' and more...' if len(skipped_voices) > 5 else ''}")
                logger.info(f"Fetched {len(voices)} Google TTS voices")
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
    
    async def list_voices(self) -> list:
        """Fetch available voices from Amazon Polly API"""
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp not available for Amazon Polly")
        
        if not self.aws_access_key or not self.aws_secret_key:
            raise RuntimeError("Amazon Polly credentials not configured")
        
        # For simplicity, return a comprehensive list of Polly voices
        # In a full implementation, we'd make an API call to DescribeVoices
        polly_voices = [
            # US English voices
            {"voice_id": "Joanna", "name": "Joanna - Female US", "language": "en-US", "gender": "Female"},
            {"voice_id": "Matthew", "name": "Matthew - Male US", "language": "en-US", "gender": "Male"},
            {"voice_id": "Ivy", "name": "Ivy - Female US (Child)", "language": "en-US", "gender": "Female"},
            {"voice_id": "Justin", "name": "Justin - Male US (Child)", "language": "en-US", "gender": "Male"},
            {"voice_id": "Kendra", "name": "Kendra - Female US", "language": "en-US", "gender": "Female"},
            {"voice_id": "Kimberly", "name": "Kimberly - Female US", "language": "en-US", "gender": "Female"},
            {"voice_id": "Salli", "name": "Salli - Female US", "language": "en-US", "gender": "Female"},
            {"voice_id": "Joey", "name": "Joey - Male US", "language": "en-US", "gender": "Male"},
            {"voice_id": "Ruth", "name": "Ruth - Female US", "language": "en-US", "gender": "Female"},
            {"voice_id": "Stephen", "name": "Stephen - Male US", "language": "en-US", "gender": "Male"},
            
            # UK English voices
            {"voice_id": "Amy", "name": "Amy - Female GB", "language": "en-GB", "gender": "Female"},
            {"voice_id": "Emma", "name": "Emma - Female GB", "language": "en-GB", "gender": "Female"},
            {"voice_id": "Brian", "name": "Brian - Male GB", "language": "en-GB", "gender": "Male"},
            {"voice_id": "Arthur", "name": "Arthur - Male GB", "language": "en-GB", "gender": "Male"},
            
            # Australian English voices
            {"voice_id": "Nicole", "name": "Nicole - Female AU", "language": "en-AU", "gender": "Female"},
            {"voice_id": "Russell", "name": "Russell - Male AU", "language": "en-AU", "gender": "Male"},
            {"voice_id": "Olivia", "name": "Olivia - Female AU", "language": "en-AU", "gender": "Female"},
            
            # Other English variants
            {"voice_id": "Aria", "name": "Aria - Female NZ", "language": "en-NZ", "gender": "Female"},
            {"voice_id": "Ayanda", "name": "Ayanda - Female ZA", "language": "en-ZA", "gender": "Female"},
            {"voice_id": "Aditi", "name": "Aditi - Female IN", "language": "en-IN", "gender": "Female"},
            {"voice_id": "Raveena", "name": "Raveena - Female IN", "language": "en-IN", "gender": "Female"},
            
            # Spanish voices
            {"voice_id": "Conchita", "name": "Conchita - Female ES", "language": "es-ES", "gender": "Female"},
            {"voice_id": "Enrique", "name": "Enrique - Male ES", "language": "es-ES", "gender": "Male"},
            {"voice_id": "Lucia", "name": "Lucia - Female ES", "language": "es-ES", "gender": "Female"},
            {"voice_id": "Mia", "name": "Mia - Female MX", "language": "es-MX", "gender": "Female"},
            {"voice_id": "Miguel", "name": "Miguel - Male US Spanish", "language": "es-US", "gender": "Male"},
            {"voice_id": "Penelope", "name": "Penelope - Female US Spanish", "language": "es-US", "gender": "Female"},
            
            # French voices
            {"voice_id": "Celine", "name": "Celine - Female FR", "language": "fr-FR", "gender": "Female"},
            {"voice_id": "Mathieu", "name": "Mathieu - Male FR", "language": "fr-FR", "gender": "Male"},
            {"voice_id": "Lea", "name": "Lea - Female FR", "language": "fr-FR", "gender": "Female"},
            {"voice_id": "Chantal", "name": "Chantal - Female CA", "language": "fr-CA", "gender": "Female"},
            
            # German voices
            {"voice_id": "Marlene", "name": "Marlene - Female DE", "language": "de-DE", "gender": "Female"},
            {"voice_id": "Hans", "name": "Hans - Male DE", "language": "de-DE", "gender": "Male"},
            {"voice_id": "Vicki", "name": "Vicki - Female DE", "language": "de-DE", "gender": "Female"},
            
            # Italian voices
            {"voice_id": "Carla", "name": "Carla - Female IT", "language": "it-IT", "gender": "Female"},
            {"voice_id": "Giorgio", "name": "Giorgio - Male IT", "language": "it-IT", "gender": "Male"},
            {"voice_id": "Bianca", "name": "Bianca - Female IT", "language": "it-IT", "gender": "Female"},
            
            # Portuguese voices
            {"voice_id": "Ines", "name": "Ines - Female PT", "language": "pt-PT", "gender": "Female"},
            {"voice_id": "Cristiano", "name": "Cristiano - Male PT", "language": "pt-PT", "gender": "Male"},
            {"voice_id": "Vitoria", "name": "Vitoria - Female BR", "language": "pt-BR", "gender": "Female"},
            {"voice_id": "Ricardo", "name": "Ricardo - Male BR", "language": "pt-BR", "gender": "Male"},
            
            # Asian voices
            {"voice_id": "Mizuki", "name": "Mizuki - Female JP", "language": "ja-JP", "gender": "Female"},
            {"voice_id": "Takumi", "name": "Takumi - Male JP", "language": "ja-JP", "gender": "Male"},
            {"voice_id": "Seoyeon", "name": "Seoyeon - Female KR", "language": "ko-KR", "gender": "Female"},
            {"voice_id": "Zhiyu", "name": "Zhiyu - Female CN", "language": "zh-CN", "gender": "Female"},
        ]
        
        logger.info(f"Returning {len(polly_voices)} Amazon Polly voices")
        return polly_voices

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

class WebSpeechTTSProvider(TTSProvider):
    """Web Speech API provider (client-side, returns placeholder)"""
    
    def __init__(self, voice_id: str = "en-US"):
        self.voice_id = voice_id
    
    async def synth(self, job: TTSJob) -> str:
        # Web Speech API runs on the client side, so we return a special marker
        # The frontend will handle this differently
        outpath = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}_webspeech.json")
        
        # Create a JSON file with instructions for the frontend
        webspeech_data = {
            "provider": "webspeech",
            "text": job.text,
            "voice": job.voice or self.voice_id,
            "format": job.audio_format
        }
        
        import json
        with open(outpath, 'w') as f:
            json.dump(webspeech_data, f)
        
        # Schedule cleanup after 30 seconds
        asyncio.create_task(self._cleanup_file_after_delay(outpath, 30))
        
        logger.info(f"Web Speech API instruction ready: {outpath}")
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

class FakeToneProvider(TTSProvider):
    """Offline fallback that generates a short tone + text length dependent duration.
    Not real speech—just for overlapping playback/dev.
    """
    async def synth(self, job: TTSJob) -> str:
        import wave, struct, math
        framerate = 24000
        duration = min(8.0, max(1.0, len(job.text) / 12.0))
        frequency = 440 if hash(job.voice) % 2 == 0 else 554
        nframes = int(duration * framerate)
        outpath = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}.wav")
        with wave.open(outpath, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(framerate)
            for i in range(nframes):
                val = int(32767 * 0.2 * math.sin(2 * math.pi * frequency * (i / framerate)))
                wf.writeframes(struct.pack('<h', val))
        return outpath

class HybridTTSProvider(TTSProvider):
    """Hybrid provider that uses MonsterTTS when available and under rate limit,
    falls back to random configured voices when rate limited or MonsterTTS unavailable."""
    
    def __init__(self, monster_api_key: str = None, monster_voice_id: str = None, edge_voice_id: str = None, 
                 fallback_voices: list = None, google_api_key: str = None, polly_config: dict = None):
        self.monster_provider = None
        self.edge_provider = None
        self.google_provider = None
        self.polly_provider = None
        self.webspeech_provider = None
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
        
        # Initialize Web Speech API (always available for client-side)
        self.webspeech_provider = WebSpeechTTSProvider()
        
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
                elif matching_voice.provider == "webspeech" and self.webspeech_provider:
                    return await self.webspeech_provider.synth(job)
            
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
            elif fallback_voice.provider == "webspeech" and self.webspeech_provider:
                return await self.webspeech_provider.synth(fallback_job)
        
        # Final fallback to Edge TTS with default voice
        if self.edge_provider:
            logger.info("Using Edge TTS with default voice")
            default_job = TTSJob(
                text=job.text,
                voice="en-US-AvaNeural",
                audio_format=job.audio_format
            )
            return await self.edge_provider.synth(default_job)
        
        # Ultimate fallback
        logger.info("No TTS providers available, using FakeTone")
        fake_provider = FakeToneProvider()
        return await fake_provider.synth(job)

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
    return FakeToneProvider()
