"""
Advanced Audio Effects Engine for flowCFD
Provides professional-grade audio processing, effects chains, and real-time manipulation.
"""

import subprocess
import os
import tempfile
import json
import math
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class EffectType(Enum):
    VOLUME = "volume"
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    NORMALIZE = "normalize"
    EQUALIZER = "equalizer"
    COMPRESSOR = "compressor"
    REVERB = "reverb"
    CHORUS = "chorus"
    DISTORTION = "distortion"
    NOISE_REDUCTION = "noise_reduction"
    PITCH_SHIFT = "pitch_shift"
    TIME_STRETCH = "time_stretch"
    GATE = "gate"
    LIMITER = "limiter"
    FILTER = "filter"

@dataclass
class AudioEffect:
    """Represents a single audio effect with parameters."""
    effect_type: EffectType
    parameters: Dict[str, Any]
    enabled: bool = True
    order: int = 0

@dataclass
class EffectChain:
    """Represents a chain of audio effects."""
    effects: List[AudioEffect]
    name: str = "Default Chain"
    
    def to_ffmpeg_filter(self) -> str:
        """Convert effect chain to FFmpeg filter string."""
        filters = []
        
        for effect in sorted(self.effects, key=lambda x: x.order):
            if not effect.enabled:
                continue
                
            filter_str = self._effect_to_filter(effect)
            if filter_str:
                filters.append(filter_str)
        
        return ",".join(filters) if filters else "anull"
    
    def _effect_to_filter(self, effect: AudioEffect) -> str:
        """Convert single effect to FFmpeg filter."""
        params = effect.parameters
        
        if effect.effect_type == EffectType.VOLUME:
            return f"volume={params.get('level', 1.0)}"
        
        elif effect.effect_type == EffectType.FADE_IN:
            duration = params.get('duration', 1.0)
            return f"afade=t=in:d={duration}"
        
        elif effect.effect_type == EffectType.FADE_OUT:
            duration = params.get('duration', 1.0)
            start = params.get('start_time', 0)
            return f"afade=t=out:st={start}:d={duration}"
        
        elif effect.effect_type == EffectType.NORMALIZE:
            target = params.get('target_lufs', -23)
            return f"loudnorm=I={target}:TP=-1.5:LRA=11"
        
        elif effect.effect_type == EffectType.EQUALIZER:
            # Multi-band EQ with frequency and gain
            freq = params.get('frequency', 1000)
            gain = params.get('gain', 0)
            q_factor = params.get('q', 1.0)
            return f"equalizer=f={freq}:g={gain}:q={q_factor}"
        
        elif effect.effect_type == EffectType.COMPRESSOR:
            threshold = params.get('threshold', -20)
            ratio = params.get('ratio', 4)
            attack = params.get('attack', 5)
            release = params.get('release', 50)
            makeup = params.get('makeup_gain', 0)
            return f"acompressor=threshold={threshold}dB:ratio={ratio}:attack={attack}:release={release}:makeup={makeup}dB"
        
        elif effect.effect_type == EffectType.REVERB:
            room_size = params.get('room_size', 0.5)
            damping = params.get('damping', 0.5)
            wet_level = params.get('wet_level', 0.3)
            return f"aecho=0.8:0.88:{int(room_size*1000)}:{wet_level}:0.6:0.4:{int(damping*500)}:0.3"
        
        elif effect.effect_type == EffectType.CHORUS:
            delay = params.get('delay', 40)
            decay = params.get('decay', 0.5)
            speed = params.get('speed', 0.5)
            depth = params.get('depth', 2)
            return f"chorus=0.5:0.9:{delay}:0.4:{speed}:{depth}:0.25"
        
        elif effect.effect_type == EffectType.DISTORTION:
            gain = params.get('gain', 20)
            colour = params.get('colour', 20)
            return f"overdrive=gain={gain}:colour={colour}"
        
        elif effect.effect_type == EffectType.NOISE_REDUCTION:
            strength = params.get('strength', 0.5)
            return f"anlmdn=s={strength}"
        
        elif effect.effect_type == EffectType.PITCH_SHIFT:
            semitones = params.get('semitones', 0)
            return f"asetrate=44100*2^({semitones}/12),aresample=44100"
        
        elif effect.effect_type == EffectType.TIME_STRETCH:
            tempo = params.get('tempo', 1.0)
            return f"atempo={tempo}"
        
        elif effect.effect_type == EffectType.GATE:
            threshold = params.get('threshold', -30)
            ratio = params.get('ratio', 2)
            attack = params.get('attack', 20)
            release = params.get('release', 250)
            return f"agate=threshold={threshold}dB:ratio={ratio}:attack={attack}:release={release}"
        
        elif effect.effect_type == EffectType.LIMITER:
            threshold = params.get('threshold', -6)
            release = params.get('release', 50)
            return f"alimiter=level_in=1:level_out=1:limit={threshold}dB:release={release}"
        
        elif effect.effect_type == EffectType.FILTER:
            filter_type = params.get('type', 'lowpass')
            frequency = params.get('frequency', 1000)
            if filter_type == 'lowpass':
                return f"lowpass=f={frequency}"
            elif filter_type == 'highpass':
                return f"highpass=f={frequency}"
            elif filter_type == 'bandpass':
                width = params.get('width', 100)
                return f"bandpass=f={frequency}:w={width}"
        
        return ""

class AudioProcessor:
    """Advanced audio processing engine with effect chains and real-time capabilities."""
    
    def __init__(self):
        self.presets = self._load_effect_presets()
    
    def apply_effect_chain(self, input_path: str, output_path: str, 
                          effect_chain: EffectChain, 
                          preserve_video: bool = True) -> Dict[str, Any]:
        """
        Apply a complete effect chain to an audio/video file.
        
        Args:
            input_path: Path to input file
            output_path: Path for output file
            effect_chain: EffectChain object with effects to apply
            preserve_video: Whether to preserve video stream (if present)
            
        Returns:
            Dictionary with processing results and metadata
        """
        try:
            filter_chain = effect_chain.to_ffmpeg_filter()
            
            if filter_chain == "anull":
                # No effects to apply, just copy
                cmd = ['ffmpeg', '-i', input_path, '-c', 'copy', '-y', output_path]
            else:
                cmd = ['ffmpeg', '-i', input_path]
                
                if preserve_video:
                    # Apply audio effects while preserving video
                    cmd.extend([
                        '-filter:a', filter_chain,
                        '-c:v', 'copy',  # Copy video stream unchanged
                        '-c:a', 'aac',   # Re-encode audio with effects
                    ])
                else:
                    # Audio-only processing
                    cmd.extend([
                        '-vn',  # No video
                        '-filter:a', filter_chain,
                        '-c:a', 'aac',
                    ])
                
                cmd.extend(['-y', output_path])
            
            logging.info(f"Applying effect chain '{effect_chain.name}' with {len(effect_chain.effects)} effects")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Effect processing failed: {result.stderr}",
                    "filter_chain": filter_chain
                }
            
            # Analyze the processed file
            analysis = self._analyze_processed_audio(output_path)
            
            return {
                "success": True,
                "output_path": output_path,
                "effect_chain": effect_chain.name,
                "effects_applied": len([e for e in effect_chain.effects if e.enabled]),
                "filter_chain": filter_chain,
                "analysis": analysis,
                "file_size": os.path.getsize(output_path),
                "processing_time": "completed"
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Audio processing timed out"}
        except Exception as e:
            logging.error(f"Audio processing error: {e}")
            return {"success": False, "error": str(e)}
    
    def create_effect_preset(self, name: str, effects: List[Dict]) -> EffectChain:
        """Create an effect chain from a list of effect dictionaries."""
        audio_effects = []
        
        for i, effect_dict in enumerate(effects):
            try:
                effect_type = EffectType(effect_dict.get('type'))
                parameters = effect_dict.get('parameters', {})
                enabled = effect_dict.get('enabled', True)
                
                audio_effects.append(AudioEffect(
                    effect_type=effect_type,
                    parameters=parameters,
                    enabled=enabled,
                    order=i
                ))
            except ValueError:
                logging.warning(f"Unknown effect type: {effect_dict.get('type')}")
                continue
        
        return EffectChain(effects=audio_effects, name=name)
    
    def get_available_effects(self) -> Dict[str, Dict]:
        """Get list of available effects with their parameters."""
        return {
            "volume": {
                "name": "Volume Control",
                "parameters": {
                    "level": {"type": "float", "min": 0.0, "max": 3.0, "default": 1.0, "description": "Volume level multiplier"}
                }
            },
            "fade_in": {
                "name": "Fade In",
                "parameters": {
                    "duration": {"type": "float", "min": 0.1, "max": 10.0, "default": 1.0, "description": "Fade in duration (seconds)"}
                }
            },
            "fade_out": {
                "name": "Fade Out", 
                "parameters": {
                    "duration": {"type": "float", "min": 0.1, "max": 10.0, "default": 1.0, "description": "Fade out duration (seconds)"},
                    "start_time": {"type": "float", "min": 0.0, "max": 3600.0, "default": 0.0, "description": "Start time for fade out"}
                }
            },
            "normalize": {
                "name": "Audio Normalization",
                "parameters": {
                    "target_lufs": {"type": "float", "min": -50.0, "max": -10.0, "default": -23.0, "description": "Target loudness (LUFS)"}
                }
            },
            "equalizer": {
                "name": "Equalizer",
                "parameters": {
                    "frequency": {"type": "float", "min": 20.0, "max": 20000.0, "default": 1000.0, "description": "Center frequency (Hz)"},
                    "gain": {"type": "float", "min": -20.0, "max": 20.0, "default": 0.0, "description": "Gain (dB)"},
                    "q": {"type": "float", "min": 0.1, "max": 10.0, "default": 1.0, "description": "Q factor (bandwidth)"}
                }
            },
            "compressor": {
                "name": "Dynamic Range Compressor",
                "parameters": {
                    "threshold": {"type": "float", "min": -60.0, "max": 0.0, "default": -20.0, "description": "Threshold (dB)"},
                    "ratio": {"type": "float", "min": 1.0, "max": 20.0, "default": 4.0, "description": "Compression ratio"},
                    "attack": {"type": "float", "min": 0.1, "max": 100.0, "default": 5.0, "description": "Attack time (ms)"},
                    "release": {"type": "float", "min": 1.0, "max": 1000.0, "default": 50.0, "description": "Release time (ms)"},
                    "makeup_gain": {"type": "float", "min": -20.0, "max": 20.0, "default": 0.0, "description": "Makeup gain (dB)"}
                }
            },
            "reverb": {
                "name": "Reverb",
                "parameters": {
                    "room_size": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.5, "description": "Room size"},
                    "damping": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.5, "description": "High frequency damping"},
                    "wet_level": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.3, "description": "Wet signal level"}
                }
            },
            "distortion": {
                "name": "Distortion/Overdrive",
                "parameters": {
                    "gain": {"type": "float", "min": 1.0, "max": 100.0, "default": 20.0, "description": "Distortion gain"},
                    "colour": {"type": "float", "min": 1.0, "max": 100.0, "default": 20.0, "description": "Harmonic coloration"}
                }
            },
            "pitch_shift": {
                "name": "Pitch Shift",
                "parameters": {
                    "semitones": {"type": "float", "min": -12.0, "max": 12.0, "default": 0.0, "description": "Pitch shift (semitones)"}
                }
            },
            "time_stretch": {
                "name": "Time Stretch",
                "parameters": {
                    "tempo": {"type": "float", "min": 0.5, "max": 2.0, "default": 1.0, "description": "Tempo multiplier"}
                }
            }
        }
    
    def _load_effect_presets(self) -> Dict[str, EffectChain]:
        """Load predefined effect presets."""
        presets = {}
        
        # Voice Enhancement Preset
        presets["voice_enhancement"] = EffectChain([
            AudioEffect(EffectType.NOISE_REDUCTION, {"strength": 0.3}, order=0),
            AudioEffect(EffectType.EQUALIZER, {"frequency": 2500, "gain": 3, "q": 0.7}, order=1),
            AudioEffect(EffectType.COMPRESSOR, {"threshold": -18, "ratio": 3, "attack": 3, "release": 30}, order=2),
            AudioEffect(EffectType.NORMALIZE, {"target_lufs": -16}, order=3)
        ], "Voice Enhancement")
        
        # Music Mastering Preset
        presets["music_mastering"] = EffectChain([
            AudioEffect(EffectType.EQUALIZER, {"frequency": 60, "gain": -2, "q": 0.7}, order=0),   # Reduce low mud
            AudioEffect(EffectType.EQUALIZER, {"frequency": 3000, "gain": 1.5, "q": 0.8}, order=1), # Presence boost
            AudioEffect(EffectType.COMPRESSOR, {"threshold": -12, "ratio": 2.5, "attack": 10, "release": 100}, order=2),
            AudioEffect(EffectType.LIMITER, {"threshold": -1, "release": 5}, order=3),
            AudioEffect(EffectType.NORMALIZE, {"target_lufs": -14}, order=4)
        ], "Music Mastering")
        
        # Podcast Processing Preset
        presets["podcast"] = EffectChain([
            AudioEffect(EffectType.GATE, {"threshold": -35, "ratio": 10, "attack": 1, "release": 100}, order=0),
            AudioEffect(EffectType.EQUALIZER, {"frequency": 100, "gain": -6, "q": 0.7}, order=1),    # High-pass
            AudioEffect(EffectType.EQUALIZER, {"frequency": 2800, "gain": 2, "q": 1.0}, order=2),    # Speech clarity
            AudioEffect(EffectType.COMPRESSOR, {"threshold": -20, "ratio": 6, "attack": 2, "release": 40}, order=3),
            AudioEffect(EffectType.NORMALIZE, {"target_lufs": -16}, order=4)
        ], "Podcast Processing")
        
        # Creative Effects Preset
        presets["creative_fx"] = EffectChain([
            AudioEffect(EffectType.CHORUS, {"delay": 50, "decay": 0.4, "speed": 0.8, "depth": 3}, order=0),
            AudioEffect(EffectType.REVERB, {"room_size": 0.8, "damping": 0.3, "wet_level": 0.4}, order=1),
            AudioEffect(EffectType.PITCH_SHIFT, {"semitones": 0.5}, order=2)
        ], "Creative Effects")
        
        return presets
    
    def get_preset(self, preset_name: str) -> Optional[EffectChain]:
        """Get a predefined effect preset."""
        return self.presets.get(preset_name)
    
    def get_available_presets(self) -> List[str]:
        """Get list of available preset names."""
        return list(self.presets.keys())
    
    def _analyze_processed_audio(self, file_path: str) -> Dict[str, Any]:
        """Analyze the processed audio file for quality metrics."""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_streams', '-select_streams', 'a:0',
                '-show_entries', 'stream=sample_rate,channels,duration,bit_rate',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data.get('streams'):
                    stream = data['streams'][0]
                    return {
                        "sample_rate": int(stream.get('sample_rate', 0)),
                        "channels": int(stream.get('channels', 0)),
                        "duration": float(stream.get('duration', 0)),
                        "bitrate": int(stream.get('bit_rate', 0)) if stream.get('bit_rate') else None
                    }
            
            return {"error": "Could not analyze processed audio"}
            
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

# Global audio processor instance
audio_processor = AudioProcessor()
