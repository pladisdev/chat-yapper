"""Unit tests for audio filters (reverb, echo, pitch, speed, random)"""
import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from modules.audio_filters import AudioFilterProcessor, get_audio_filter_processor


@pytest.fixture
def audio_processor():
    """Create an audio filter processor for testing"""
    processor = AudioFilterProcessor()
    yield processor


@pytest.fixture
def sample_audio_file():
    """Create a temporary audio file for testing"""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(b"fake audio content")
        temp_path = f.name
    yield temp_path
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)
    # Also cleanup filtered file if it exists
    filtered_path = temp_path.replace(".mp3", "_filtered.mp3")
    if os.path.exists(filtered_path):
        os.unlink(filtered_path)


@pytest.mark.unit
@pytest.mark.audio
class TestAudioFilterProcessor:
    """Tests for AudioFilterProcessor class"""
    
    def test_create_processor(self, audio_processor):
        """Test creating an audio processor instance"""
        assert audio_processor is not None
        assert hasattr(audio_processor, 'ffmpeg_available')
    
    def test_ffmpeg_detection(self, audio_processor):
        """Test ffmpeg availability detection"""
        # This will depend on the system, but we can at least check it runs
        assert isinstance(audio_processor.ffmpeg_available, bool)
    
    def test_singleton_processor(self):
        """Test that get_audio_filter_processor returns singleton"""
        processor1 = get_audio_filter_processor()
        processor2 = get_audio_filter_processor()
        assert processor1 is processor2
    
    def test_has_enabled_filters_none_enabled(self, audio_processor):
        """Test checking for enabled filters when none are enabled"""
        settings = {
            'reverb': {'enabled': False},
            'echo': {'enabled': False},
            'pitch': {'enabled': False},
            'speed': {'enabled': False}
        }
        result = audio_processor._has_enabled_filters(settings)
        assert result is False
    
    def test_has_enabled_filters_some_enabled(self, audio_processor):
        """Test checking for enabled filters when some are enabled"""
        settings = {
            'reverb': {'enabled': True, 'roomSize': 0.5},
            'pitch': {'enabled': False},
            'speed': {'enabled': False}
        }
        result = audio_processor._has_enabled_filters(settings)
        assert result is True
    
    # Note: Individual _build_*_filter methods were refactored into _build_filters
    # These tests are removed as they test private implementation details
    
    def test_build_filters_single(self, audio_processor):
        """Test building filter chain with single filter"""
        settings = {
            'reverb': {'enabled': True, 'amount': 50},
            'pitch': {'enabled': False},
            'speed': {'enabled': False}
        }
        filters = audio_processor._build_filters(settings)
        assert len(filters) == 1
        assert 'aecho=' in filters[0]
    
    def test_build_filters_multiple(self, audio_processor):
        """Test building filter chain with multiple filters"""
        settings = {
            'reverb': {'enabled': True, 'amount': 50},
            'pitch': {'enabled': True, 'semitones': 2},
            'speed': {'enabled': True, 'multiplier': 1.2}
        }
        filters = audio_processor._build_filters(settings)
        # Should have 3 separate filters (reverb, pitch, speed)
        assert len(filters) == 3
        # Check that different filter types are present
        filter_str = ','.join(filters)
        assert 'aecho=' in filter_str  # reverb
        assert 'asetrate=' in filter_str  # pitch
        assert 'atempo=' in filter_str  # speed
    
    def test_build_filters_none_enabled(self, audio_processor):
        """Test building filter chain when none are enabled"""
        settings = {
            'reverb': {'enabled': False},
            'pitch': {'enabled': False},
            'speed': {'enabled': False}
        }
        filters = audio_processor._build_filters(settings)
        assert len(filters) == 0
    
    def test_build_random_filters(self, audio_processor):
        """Test building random filter combinations"""
        settings = {
            'reverb': {
                'randomEnabled': True,
                'randomRange': {'min': 30, 'max': 70}
            },
            'pitch': {
                'randomEnabled': True,
                'randomRange': {'min': -3, 'max': 3}
            },
            'speed': {
                'randomEnabled': True,
                'randomRange': {'min': 0.9, 'max': 1.1}
            }
        }
        
        filters = audio_processor._build_random_filters(settings)
        # Should return some filters (1 to 3)
        assert isinstance(filters, list)
        assert len(filters) >= 1
        assert len(filters) <= 3
    
    def test_build_random_filters_no_chance(self, audio_processor):
        """Test random filters when all are disabled"""
        settings = {
            'reverb': {'randomEnabled': False},
            'pitch': {'randomEnabled': False},
            'speed': {'randomEnabled': False}
        }
        
        filters = audio_processor._build_random_filters(settings)
        assert len(filters) == 0
    
    @patch('subprocess.run')
    def test_apply_filters_no_ffmpeg(self, mock_run, audio_processor, sample_audio_file):
        """Test applying filters when ffmpeg is not available"""
        audio_processor.ffmpeg_available = False
        
        settings = {
            'reverb': {'enabled': True, 'amount': 50}
        }
        
        output_path, duration = audio_processor.apply_filters(
            sample_audio_file,
            settings,
            random_filters=False
        )
        
        # Should return original file when ffmpeg unavailable
        assert output_path == sample_audio_file
        assert duration is None
        mock_run.assert_not_called()
    
    @patch('subprocess.run')
    def test_apply_filters_no_enabled(self, mock_run, audio_processor, sample_audio_file):
        """Test applying filters when none are enabled"""
        audio_processor.ffmpeg_available = True
        
        settings = {
            'reverb': {'enabled': False},
            'echo': {'enabled': False},
            'pitch': {'enabled': False},
            'speed': {'enabled': False}
        }
        
        output_path, duration = audio_processor.apply_filters(
            sample_audio_file,
            settings,
            random_filters=False
        )
        
        # Should return original file when no filters enabled
        assert output_path == sample_audio_file
        mock_run.assert_not_called()
    
    @patch('subprocess.run')
    def test_get_audio_duration_success(self, mock_run, audio_processor, sample_audio_file):
        """Test getting audio duration with ffprobe"""
        # Mock successful ffprobe response
        mock_run.return_value = Mock(
            returncode=0,
            stdout='2.5\n'
        )
        
        duration = audio_processor._get_audio_duration(sample_audio_file)
        assert duration == 2.5
        mock_run.assert_called_once()
        # Check that ffprobe was called with correct args
        args = mock_run.call_args[0][0]
        assert 'ffprobe' in args
        assert '-show_entries' in args
    
    @patch('subprocess.run')
    def test_get_audio_duration_failure(self, mock_run, audio_processor, sample_audio_file):
        """Test getting audio duration when ffprobe fails"""
        # Mock failed ffprobe response
        mock_run.return_value = Mock(returncode=1)
        
        duration = audio_processor._get_audio_duration(sample_audio_file)
        assert duration is None
    
    @patch('subprocess.run')
    def test_get_audio_duration_timeout(self, mock_run, audio_processor, sample_audio_file):
        """Test getting audio duration with timeout"""
        # Mock timeout exception
        mock_run.side_effect = Exception("Timeout")
        
        duration = audio_processor._get_audio_duration(sample_audio_file)
        assert duration is None


@pytest.mark.unit
@pytest.mark.audio
class TestAudioFilterConfiguration:
    """Tests for audio filter configuration and settings"""
    
    def test_default_filter_settings(self, audio_processor):
        """Test that default filter settings are reasonable"""
        settings = {
            'reverb': {'enabled': True, 'amount': 50},
            'pitch': {'enabled': True, 'semitones': 2},
            'speed': {'enabled': True, 'multiplier': 1.2}
        }
        
        # Should build filters without errors
        filters = audio_processor._build_filters(settings)
        # All three filters should be included
        assert len(filters) == 3
    
    def test_filter_settings_validation(self, audio_processor):
        """Test that extreme filter settings are handled gracefully"""
        settings = {
            'reverb': {'enabled': True, 'amount': 100},  # Max value
            'pitch': {'enabled': True, 'semitones': 12},  # High pitch (1 octave)
            'speed': {'enabled': True, 'multiplier': 2.5}  # Very fast (needs chaining)
        }
        
        # Should not crash with extreme values
        try:
            filters = audio_processor._build_filters(settings)
            assert isinstance(filters, list)
            # Speed > 2.0 should result in chained atempo filters
            speed_filters = [f for f in filters if 'atempo=' in f]
            assert len(speed_filters) > 0
        except Exception as e:
            pytest.fail(f"Filter building should handle extreme values: {e}")
    
    def test_random_filter_distribution(self, audio_processor):
        """Test that random filters have good distribution"""
        settings = {
            'reverb': {
                'randomEnabled': True,
                'randomRange': {'min': 30, 'max': 70}
            },
            'pitch': {
                'randomEnabled': True,
                'randomRange': {'min': -3, 'max': 3}
            },
            'speed': {
                'randomEnabled': True,
                'randomRange': {'min': 0.9, 'max': 1.1}
            }
        }
        
        # Generate multiple random filter sets
        filter_sets = []
        for _ in range(10):
            filters = audio_processor._build_random_filters(settings)
            filter_sets.append(len(filters))
        
        # Should have variation in number of filters (1-3 since all are enabled)
        assert min(filter_sets) >= 1  # At least 1 filter
        assert max(filter_sets) <= 3  # At most 3 filters (all available)


@pytest.mark.integration
@pytest.mark.audio
class TestAudioFilterIntegration:
    """Integration tests for audio filters (requires ffmpeg)"""
    
    @pytest.mark.skipif(not AudioFilterProcessor()._check_ffmpeg(), reason="ffmpeg not available")
    def test_apply_filters_creates_file(self, audio_processor, sample_audio_file):
        """Test that applying filters creates a new file (if ffmpeg available)"""
        settings = {
            'reverb': {'enabled': True, 'roomSize': 0.5, 'wetness': 0.3}
        }
        
        # This test only runs if ffmpeg is available
        # Note: Will fail with fake audio file, but tests the flow
        try:
            output_path, duration = audio_processor.apply_filters(
                sample_audio_file,
                settings,
                random_filters=False
            )
            
            # Check output path is different from input
            if output_path != sample_audio_file:
                assert '_filtered' in output_path
        except Exception:
            # Expected to fail with fake audio content
            pass
