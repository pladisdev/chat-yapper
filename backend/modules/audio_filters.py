"""
Audio filters for post-processing TTS audio files.
Supports: reverb, echo, pitch shift, speed change, and random combinations.
"""
import os
import random
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class AudioFilterProcessor:
    """
    Process audio files with various effects using ffmpeg.
    All filters modify the audio file and return the new file path and duration.
    """
    
    def __init__(self):
        self.ffmpeg_available = self._check_ffmpeg()
        if not self.ffmpeg_available:
            logger.warning("ffmpeg not found - audio filters will be disabled")
    
    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"ffmpeg check failed: {e}")
            return False
    
    def _get_audio_duration(self, file_path: str) -> Optional[float]:
        """Get audio duration using ffprobe"""
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    file_path
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
        except Exception as e:
            logger.warning(f"Failed to get audio duration with ffprobe: {e}")
        return None
    
    def apply_filters(
        self,
        input_path: str,
        filter_settings: Dict[str, Any],
        random_filters: bool = False
    ) -> tuple[str, Optional[float]]:
        """
        Apply audio filters to the input file.
        Returns (output_path, duration) tuple.
        
        Args:
            input_path: Path to input audio file
            filter_settings: Dictionary of filter settings from config
            random_filters: If True, randomly select and apply filters
        
        Returns:
            Tuple of (output_file_path, audio_duration_in_seconds)
        """
        if not self.ffmpeg_available:
            logger.warning("ffmpeg not available, skipping filters")
            return input_path, None
        
        # Check if any filters are enabled
        if not random_filters and not self._has_enabled_filters(filter_settings):
            return input_path, None
        
        # Generate output filename
        input_file = Path(input_path)
        output_path = str(input_file.parent / f"{input_file.stem}_filtered{input_file.suffix}")
        
        # Build ffmpeg filter chain
        filters = []
        
        if random_filters:
            filters = self._build_random_filters(filter_settings)
            logger.info(f"🎲 Applying random filters: {', '.join(filters)}")
        else:
            filters = self._build_filters(filter_settings)
            if filters:
                logger.info(f"🎚️ Applying filters: {', '.join(filters)}")
        
        if not filters:
            return input_path, None
        
        # Apply filters using ffmpeg
        try:
            filter_complex = ",".join(filters)
            
            command = [
                "ffmpeg",
                "-i", input_path,
                "-af", filter_complex,
                "-y",  # Overwrite output file
                output_path
            ]
            
            logger.debug(f"Running ffmpeg command: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"ffmpeg failed: {result.stderr}")
                return input_path, None
            
            # Get duration of filtered audio
            duration = self._get_audio_duration(output_path)
            
            logger.info(f"✅ Audio filtered successfully: {output_path} (duration: {duration:.2f}s)")
            
            # Delete original file to save space
            try:
                os.remove(input_path)
                logger.debug(f"Deleted original audio file: {input_path}")
            except Exception as e:
                logger.warning(f"Failed to delete original file: {e}")
            
            return output_path, duration
            
        except subprocess.TimeoutExpired:
            logger.error("ffmpeg timed out while applying filters")
            return input_path, None
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            return input_path, None
    
    def _has_enabled_filters(self, settings: Dict[str, Any]) -> bool:
        """Check if any filters are enabled"""
        return any([
            settings.get("reverb", {}).get("enabled", False),
            settings.get("pitch", {}).get("enabled", False),
            settings.get("speed", {}).get("enabled", False),
        ])
    
    def _build_filters(self, settings: Dict[str, Any]) -> List[str]:
        """Build ffmpeg filter chain from settings"""
        filters = []
        
        # Reverb filter
        if settings.get("reverb", {}).get("enabled", False):
            reverb_amount = settings.get("reverb", {}).get("amount", 50) / 100.0  # 0.0 to 1.0
            # Use freeverb for reverb effect
            filters.append(f"afreqshift=shift=0,aecho=0.8:0.88:60:0.4,volume={1 + reverb_amount * 0.3}")
        
        # Pitch shift
        if settings.get("pitch", {}).get("enabled", False):
            semitones = settings.get("pitch", {}).get("semitones", 0)  # -12 to +12
            if semitones != 0:
                # Use rubberband for high-quality pitch shifting (if available)
                # Otherwise use asetrate for simple pitch shift
                cents = semitones * 100
                filters.append(f"asetrate=44100*2^({semitones}/12),aresample=44100")
        
        # Speed change (affects duration)
        if settings.get("speed", {}).get("enabled", False):
            speed = settings.get("speed", {}).get("multiplier", 1.0)  # 0.5 to 2.0
            if speed != 1.0:
                # atempo can only do 0.5 to 2.0, chain multiple for larger changes
                if 0.5 <= speed <= 2.0:
                    filters.append(f"atempo={speed}")
                elif speed < 0.5:
                    # Chain multiple atempo for very slow speeds
                    filters.append(f"atempo=0.5,atempo={speed/0.5}")
                else:  # speed > 2.0
                    # Chain multiple atempo for very fast speeds
                    filters.append(f"atempo=2.0,atempo={speed/2.0}")
        
        return filters
    
    def _build_random_filters(self, settings: Dict[str, Any]) -> List[str]:
        """Build a random set of filters with random values for variety, based on settings"""
        filters = []
        
        # Build list of available filters based on randomEnabled flag
        available_filters = []
        if settings.get("reverb", {}).get("randomEnabled", True):
            available_filters.append("reverb")
        if settings.get("pitch", {}).get("randomEnabled", True):
            available_filters.append("pitch")
        if settings.get("speed", {}).get("randomEnabled", True):
            available_filters.append("speed")
        
        if not available_filters:
            logger.warning("No effects enabled for random mode")
            return filters
        
        # Randomly decide how many filters to apply (1 to all available)
        num_filters = random.randint(1, min(3, len(available_filters)))
        
        # Randomly select which filters to apply
        selected = random.sample(available_filters, num_filters)
        
        for filter_type in selected:
            if filter_type == "reverb":
                # Get custom range or use defaults
                reverb_config = settings.get("reverb", {})
                random_range = reverb_config.get("randomRange", {"min": 20, "max": 80})
                min_val = random_range.get("min", 20)
                max_val = random_range.get("max", 80)
                
                # Random reverb amount within configured range
                amount = random.uniform(min_val / 100.0, max_val / 100.0)
                filters.append(f"afreqshift=shift=0,aecho=0.8:0.88:60:0.4,volume={1 + amount * 0.3}")
                logger.debug(f"Random reverb: {amount*100:.0f}% (range: {min_val}-{max_val}%)")
            
            elif filter_type == "pitch":
                # Get custom range or use defaults
                pitch_config = settings.get("pitch", {})
                random_range = pitch_config.get("randomRange", {"min": -8, "max": 8})
                min_val = random_range.get("min", -8)
                max_val = random_range.get("max", 8)
                
                # Random pitch shift within configured range (avoiding near-zero)
                possible_semitones = [s for s in range(int(min_val), int(max_val) + 1) if abs(s) > 1]
                if possible_semitones:
                    semitones = random.choice(possible_semitones)
                    filters.append(f"asetrate=44100*2^({semitones}/12),aresample=44100")
                    logger.debug(f"Random pitch: {semitones:+d} semitones (range: {min_val} to {max_val})")
            
            elif filter_type == "speed":
                # Get custom range or use defaults
                speed_config = settings.get("speed", {})
                random_range = speed_config.get("randomRange", {"min": 0.75, "max": 1.3})
                min_val = random_range.get("min", 0.75)
                max_val = random_range.get("max", 1.3)
                
                # Random speed within configured range (avoiding near-1.0)
                # Generate speed options in 0.05 increments, avoiding 0.95-1.05
                speed_options = []
                current = min_val
                while current <= max_val:
                    if current < 0.95 or current > 1.05:
                        speed_options.append(round(current, 2))
                    current += 0.05
                
                if speed_options:
                    speed = random.choice(speed_options)
                    filters.append(f"atempo={speed}")
                    logger.debug(f"Random speed: {speed:.2f}x (range: {min_val:.2f}x to {max_val:.2f}x)")
        
        return filters


# Global instance
_audio_filter_processor = None


def get_audio_filter_processor() -> AudioFilterProcessor:
    """Get or create the global audio filter processor instance"""
    global _audio_filter_processor
    if _audio_filter_processor is None:
        _audio_filter_processor = AudioFilterProcessor()
    return _audio_filter_processor
