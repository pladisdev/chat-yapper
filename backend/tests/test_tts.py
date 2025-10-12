"""Unit tests for TTS functionality"""
import os
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import aiohttp

# Import TTS classes
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.tts import (
    TTSJob, 
    TTSProvider, 
    MonsterTTSProvider,
    get_provider,
    reset_fallback_stats
)


@pytest.mark.unit
@pytest.mark.tts
class TestTTSJob:
    """Tests for TTSJob dataclass"""
    
    def test_create_tts_job_minimal(self):
        """Test creating a TTS job with minimal parameters"""
        job = TTSJob(text="Hello world", voice="test-voice")
        
        assert job.text == "Hello world"
        assert job.voice == "test-voice"
        assert job.audio_format == "mp3"  # Default value
    
    def test_create_tts_job_full(self):
        """Test creating a TTS job with all parameters"""
        job = TTSJob(
            text="Test message",
            voice="custom-voice",
            audio_format="wav"
        )
        
        assert job.text == "Test message"
        assert job.voice == "custom-voice"
        assert job.audio_format == "wav"


@pytest.mark.unit
@pytest.mark.tts
class TestTTSProvider:
    """Tests for base TTSProvider class"""
    
    @pytest.mark.asyncio
    async def test_base_provider_not_implemented(self):
        """Test that base provider synth raises NotImplementedError"""
        provider = TTSProvider()
        job = TTSJob(text="test", voice="test")
        
        with pytest.raises(NotImplementedError):
            await provider.synth(job)


@pytest.mark.unit
@pytest.mark.tts
class TestMonsterTTSProvider:
    """Tests for MonsterTTS provider"""
    
    def test_create_provider(self):
        """Test creating MonsterTTS provider"""
        provider = MonsterTTSProvider(
            api_key="test_key",
            voice_id="test_voice"
        )
        
        assert provider.api_key == "test_key"
        assert provider.voice_id == "test_voice"
        assert provider.base_url == "https://api.console.tts.monster/generate"
        assert provider.rate_limit_seconds == 2
    
    def test_rate_limit_check_initial(self):
        """Test that rate limit allows first request"""
        provider = MonsterTTSProvider(api_key="test_key")
        
        assert provider.can_process_now() is True
    
    def test_rate_limit_check_after_request(self):
        """Test rate limit after recent request"""
        import time
        
        provider = MonsterTTSProvider(api_key="test_key")
        provider.last_request_time = time.time()
        
        # Should be rate limited immediately after
        assert provider.can_process_now() is False
    
    def test_rate_limit_check_after_delay(self):
        """Test rate limit allows request after sufficient delay"""
        import time
        
        provider = MonsterTTSProvider(api_key="test_key")
        provider.last_request_time = time.time() - 3  # 3 seconds ago
        
        # Should be allowed after delay
        assert provider.can_process_now() is True
    
    @pytest.mark.asyncio
    async def test_synth_missing_api_key(self):
        """Test that synth fails without API key"""
        provider = MonsterTTSProvider(api_key="")
        job = TTSJob(text="test", voice="test-voice")
        
        with pytest.raises(RuntimeError, match="API key not configured"):
            await provider.synth(job)
    
    @pytest.mark.asyncio
    async def test_synth_rate_limit_exceeded(self):
        """Test that synth respects rate limits"""
        import time
        
        provider = MonsterTTSProvider(api_key="test_key")
        provider.last_request_time = time.time()  # Just made a request
        
        job = TTSJob(text="test", voice="test-voice")
        
        with pytest.raises(RuntimeError, match="rate limit exceeded"):
            await provider.synth(job)
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_synth_success_with_url(self, tmp_path):
        """Test successful synthesis with URL response"""
        provider = MonsterTTSProvider(api_key="test_key")
        job = TTSJob(text="test message", voice="test-voice")
        
        # Mock audio data (needs to be larger than minimum threshold)
        mock_audio = b"fake audio data" * 100  # Make it larger to pass validation
        mock_json_response = b'{"url": "https://example.com/audio.mp3"}'
        
        # Mock the HTTP responses
        with patch('aiohttp.ClientSession') as mock_session:
            # Create mock context managers for async with statements
            mock_post_response = AsyncMock()
            mock_post_response.status = 200
            mock_post_response.headers = {'content-type': 'application/json'}
            mock_post_response.read = AsyncMock(return_value=mock_json_response)
            mock_post_response.__aenter__ = AsyncMock(return_value=mock_post_response)
            mock_post_response.__aexit__ = AsyncMock(return_value=None)
            
            mock_get_response = AsyncMock()
            mock_get_response.status = 200
            mock_get_response.read = AsyncMock(return_value=mock_audio)
            mock_get_response.__aenter__ = AsyncMock(return_value=mock_get_response)
            mock_get_response.__aexit__ = AsyncMock(return_value=None)
            
            mock_session_instance = AsyncMock()
            mock_session_instance.post = Mock(return_value=mock_post_response)
            mock_session_instance.get = Mock(return_value=mock_get_response)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            
            mock_session.return_value = mock_session_instance
            
            # Set AUDIO_DIR to temp directory
            with patch('modules.tts.AUDIO_DIR', str(tmp_path)):
                result = await provider.synth(job)
                
                # Verify result is a file path
                assert result.endswith('.mp3')
                assert os.path.exists(result)


@pytest.mark.unit
@pytest.mark.tts
class TestGetProvider:
    """Tests for get_provider factory function"""
    
    @pytest.mark.asyncio
    async def test_get_provider_edge(self):
        """Test getting Edge TTS provider"""
        config = {
            "provider": "edge",
            "voice_id": "en-US-GuyNeural"
        }
        
        provider = await get_provider(config)
        
        # Should return some provider (actual type depends on availability)
        assert provider is not None
    
    @pytest.mark.asyncio
    async def test_get_provider_elevenlabs(self):
        """Test getting ElevenLabs provider configuration"""
        config = {
            "provider": "elevenlabs",
            "api_key": "test_key",
            "voice_id": "test_voice"
        }
        
        provider = await get_provider(config)
        
        # Should return some provider
        assert provider is not None
    
    @pytest.mark.asyncio
    async def test_get_provider_openai(self):
        """Test getting OpenAI provider configuration"""
        config = {
            "provider": "openai",
            "api_key": "test_key",
            "voice_id": "alloy"
        }
        
        provider = await get_provider(config)
        
        # Should return some provider
        assert provider is not None
    
    @pytest.mark.asyncio
    async def test_get_provider_invalid(self):
        """Test getting provider with invalid configuration"""
        config = {
            "provider": "invalid_provider"
        }
        
        # Should handle gracefully or raise appropriate error
        try:
            provider = await get_provider(config)
            # If it doesn't raise, should at least return something
            assert provider is not None
        except (ValueError, KeyError, RuntimeError):
            # These errors are acceptable
            pass


@pytest.mark.unit
@pytest.mark.tts
class TestFallbackStats:
    """Tests for fallback voice statistics"""
    
    def test_reset_fallback_stats(self):
        """Test resetting fallback statistics"""
        from modules.tts import fallback_voice_stats, fallback_selection_count
        
        # Add some fake data
        fallback_voice_stats["voice1"] = 10
        fallback_voice_stats["voice2"] = 5
        
        # Reset
        reset_fallback_stats()
        
        # Verify cleared
        assert len(fallback_voice_stats) == 0
        assert fallback_selection_count == 0


@pytest.mark.integration
@pytest.mark.tts
@pytest.mark.slow
class TestTTSIntegration:
    """Integration tests for TTS system (requires actual providers)"""
    
    @pytest.mark.skip(reason="Requires actual Edge TTS installation")
    @pytest.mark.asyncio
    async def test_edge_tts_integration(self, tmp_path):
        """Test actual Edge TTS synthesis"""
        config = {
            "provider": "edge",
            "voice_id": "en-US-GuyNeural"
        }
        
        provider = get_provider(config)
        job = TTSJob(text="Hello, this is a test.", voice="en-US-GuyNeural")
        
        with patch('modules.tts.AUDIO_DIR', str(tmp_path)):
            result = await provider.synth(job)
            
            assert os.path.exists(result)
            assert os.path.getsize(result) > 0
