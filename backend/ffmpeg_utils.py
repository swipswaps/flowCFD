import os
import subprocess
import math
import tempfile
import shutil
import json
import logging

from typing import Iterable, List, Dict, Any

def ffprobe_duration(path: str) -> float | None:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=nokey=1:noprint_wrappers=1",
        path
    ]
    try:
        out = subprocess.check_output(cmd, text=True).strip()
        return float(out)
    except Exception:
        return None

def generate_thumbnail(video_path: str, output_thumbnail_path: str, time_offset: float = None) -> bool:
    """
    Generates a single thumbnail for a video at a specific time offset.
    If time_offset is None, uses 10% of video duration for better uniqueness.
    """
    if time_offset is None:
        # Use video filename hash to create deterministic but unique offsets
        import hashlib
        import os
        
        duration = ffprobe_duration(video_path)
        if duration and duration > 1.0:
            # Create a hash from the video filename for deterministic uniqueness
            filename = os.path.basename(video_path)
            hash_obj = hashlib.md5(filename.encode())
            hash_int = int(hash_obj.hexdigest()[:8], 16)  # Use first 8 chars as int
            # Convert hash to percentage between 15% and 85% of video duration
            percentage = 0.15 + (hash_int % 1000) / 1000.0 * 0.7  # 15% to 85%
            time_offset = min(duration * percentage, duration - 0.5)
        else:
            time_offset = 0.5  # Fallback for very short videos
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(time_offset),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2", # quality (2 is good)
        "-f", "image2",
        "-pix_fmt", "yuvj420p",  # Force compatible pixel format
        output_thumbnail_path
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error generating thumbnail: {e}")
        return False

def generate_clip_thumbnail(video_path: str, output_thumbnail_path: str, start_time: float, end_time: float) -> bool:
    """
    Generates a thumbnail specifically for a clip's time range.
    Uses the midpoint of the clip's start/end time for a representative frame.
    """
    clip_midpoint = (start_time + end_time) / 2
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(clip_midpoint),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        "-f", "image2",
        "-pix_fmt", "yuvj420p",
        output_thumbnail_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error generating clip thumbnail: {e}")
        return False

def generate_thumbnail_strip(video_path: str, output_strip_path: str, frame_interval_seconds: int = 5, strip_height: int = 80) -> bool:
    """
    Generates a horizontal strip of thumbnails for a video using a secure temporary directory.
    """
    duration = ffprobe_duration(video_path)
    if not duration or duration == 0:
        print(f"Error: Could not get duration for video {video_path} for thumbnail strip.")
        return False
    
    num_frames_estimate = math.ceil(duration / frame_interval_seconds)
    if num_frames_estimate == 0:
        return False

    # Get video width/height for aspect ratio
    probe_cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0', video_path]
    try:
        size_str = subprocess.check_output(probe_cmd, text=True).strip()
        width, height = map(int, size_str.split('x'))
        aspect_ratio = width / height
    except Exception as e:
        print(f"Warning: Could not determine video dimensions for thumbnail strip, defaulting to 16:9. Error: {e}")
        aspect_ratio = 16 / 9
    
    frame_width = math.ceil(strip_height * aspect_ratio)

    # Use a temporary directory for frames
    with tempfile.TemporaryDirectory() as temp_dir:
        frame_cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"fps=1/{frame_interval_seconds},scale={frame_width}:{strip_height}:force_original_aspect_ratio=increase,crop={frame_width}:{strip_height}",
            os.path.join(temp_dir, "frame%04d.jpg")
        ]

        try:
            subprocess.run(frame_cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Error generating individual frames for strip: {e.stderr}")
            return False

        # Build list of generated frames
        generated_frames = sorted([os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.endswith('.jpg')])
        
        if not generated_frames:
            print("Error: No frames successfully generated for thumbnail strip.")
            return False
            
        num_frames = len(generated_frames)
        
        # Handle case where only one frame was generated
        if num_frames == 1:
            try:
                # Simply copy the single frame as the strip
                shutil.copy2(generated_frames[0], output_strip_path)
                return True
            except Exception as e:
                print(f"Error copying single frame for thumbnail strip: {e}")
                return False
        
        # Multiple frames - use hstack
        hstack_inputs = []
        for frame_file in generated_frames:
            hstack_inputs.extend(['-i', frame_file])

        hstack_cmd = [
            "ffmpeg", "-y",
            *hstack_inputs,
            "-filter_complex", f"hstack={num_frames}",
            output_strip_path
        ]
        
        try:
            subprocess.run(hstack_cmd, check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error stacking frames for thumbnail strip: {e.stderr}")
            return False
    # Temp directory is cleaned up automatically

def extract_clip(src: str, start: float, duration: float, out_path: str) -> bool:
    """
    Extract a clip from a video with fallback encoder support.
    """
    # Try stream copy first (fastest)
    cmd_copy = [
        "ffmpeg", "-y",
        "-ss", f"{start}",
        "-t", f"{duration}",
        "-i", src,
        "-c", "copy",
        "-avoid_negative_ts", "make_zero",
        out_path
    ]
    
    p = subprocess.run(cmd_copy, capture_output=True, text=True)
    if p.returncode == 0:
        return True
    
    # Stream copy failed, try with re-encoding using available encoder
    print(f"Stream copy failed, trying with re-encoding. Error: {p.stderr[-200:] if p.stderr else 'No error message'}")
    
    # Try with libopenh264 (common alternative to libx264)
    cmd_encode = [
        "ffmpeg", "-y",
        "-ss", f"{start}",
        "-t", f"{duration}",
        "-i", src,
        "-c:v", "libopenh264",
        "-c:a", "aac",
        "-avoid_negative_ts", "make_zero",
        out_path
    ]
    
    p = subprocess.run(cmd_encode, capture_output=True, text=True)
    if p.returncode == 0:
        return True
    
    print(f"Re-encoding with libopenh264 failed: {p.stderr[-200:] if p.stderr else 'No error message'}")
    
    # Last resort: try with default encoder
    cmd_default = [
        "ffmpeg", "-y",
        "-ss", f"{start}",
        "-t", f"{duration}",
        "-i", src,
        "-avoid_negative_ts", "make_zero",
        out_path
    ]
    
    p = subprocess.run(cmd_default, capture_output=True, text=True)
    print(f"Default encoding result: {p.returncode}, stderr: {p.stderr[-200:] if p.stderr else 'No error'}")
    return p.returncode == 0

def concat_mp4s(filelist_path: str, output_path: str) -> bool:
    """
    ffmpeg concat demuxer (file list) with encoder fallbacks.
    """
    # Try stream copy first (fastest, no quality loss)
    cmd_copy = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", filelist_path,
        "-c", "copy",
        "-movflags", "+faststart",
        output_path
    ]
    
    p = subprocess.run(cmd_copy, capture_output=True, text=True)
    if p.returncode == 0:
        return True
    
    print(f"Stream copy concat failed, trying with re-encoding. Error: {p.stderr[-200:] if p.stderr else 'No error message'}")
    
    # Try with libopenh264
    cmd_encode = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", filelist_path,
        "-c:v", "libopenh264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        output_path
    ]
    
    p = subprocess.run(cmd_encode, capture_output=True, text=True)
    if p.returncode == 0:
        return True
    
    print(f"Re-encoding concat with libopenh264 failed: {p.stderr[-200:] if p.stderr else 'No error message'}")
    
    # Last resort: default encoders
    cmd_default = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", filelist_path,
        "-movflags", "+faststart",
        output_path
    ]
    
    p = subprocess.run(cmd_default, capture_output=True, text=True)
    print(f"Default concat result: {p.returncode}, stderr: {p.stderr[-200:] if p.stderr else 'No error'}")
    return p.returncode == 0

def build_timeline_video(clips_data: list, output_path: str, temp_dir: str = None) -> bool:
    """
    Build a final video from timeline clips using FFmpeg.
    
    Args:
        clips_data: List of dicts with keys: 'video_path', 'start_time', 'end_time'
        output_path: Path for the final compiled video
        temp_dir: Directory for temporary clip files (optional)
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not clips_data:
        print("Error: No clips provided for timeline video build")
        return False
    
    # Use provided temp_dir or create a temporary one
    cleanup_temp = temp_dir is None
    if temp_dir is None:
        temp_dir = tempfile.mkdtemp(prefix="timeline_build_")
    
    try:
        clip_files = []
        filelist_lines = []
        
        # Extract each clip to a temporary file
        for i, clip in enumerate(clips_data):
            video_path = clip['video_path']
            start_time = clip['start_time']
            end_time = clip['end_time']
            duration = end_time - start_time
            
            if duration <= 0:
                print(f"Warning: Skipping clip {i} with invalid duration: {duration}")
                continue
            
            # Create temporary clip file
            clip_filename = f"clip_{i:04d}.mp4"
            clip_path = os.path.join(temp_dir, clip_filename)
            
            print(f"Extracting clip {i}: {start_time}s-{end_time}s from {os.path.basename(video_path)}")
            
            # Extract the clip
            if extract_clip(video_path, start_time, duration, clip_path):
                clip_files.append(clip_path)
                # Add to concat filelist (escape path for FFmpeg)
                escaped_path = clip_path.replace("'", "'\"'\"'")
                filelist_lines.append(f"file '{escaped_path}'")
                print(f"Successfully extracted clip {i}")
            else:
                print(f"Failed to extract clip {i}")
                return False
        
        if not clip_files:
            print("Error: No clips were successfully extracted")
            return False
        
        # Create filelist for FFmpeg concat
        filelist_path = os.path.join(temp_dir, "filelist.txt")
        with open(filelist_path, 'w') as f:
            f.write('\n'.join(filelist_lines))
        
        print(f"Concatenating {len(clip_files)} clips into final video...")
        
        # Concatenate all clips
        success = concat_mp4s(filelist_path, output_path)
        
        if success:
            print(f"Successfully built timeline video: {output_path}")
        else:
            print("Failed to concatenate clips")
            
        return success
        
    except Exception as e:
        print(f"Error building timeline video: {e}")
        return False
    finally:
        # Clean up temporary directory if we created it
        if cleanup_temp and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                print(f"Warning: Could not clean up temporary directory {temp_dir}: {e}")

# ===== LOSSLESS VIDEO EDITING FUNCTIONS =====

def get_keyframes(video_path: str) -> List[float]:
    """
    Extract keyframe timestamps for lossless cutting.
    Based on FFmpeg official documentation and LosslessCut implementation.
    Uses multiple detection methods for better compatibility.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        List of keyframe timestamps in seconds, empty list if error
    """
    if not os.path.exists(video_path):
        logging.warning(f"Video file not found: {video_path}")
        return []
    
    # Method 1: Try skip_frame nokey (fastest, but may not work for all formats)
    cmd1 = [
        "ffprobe", "-v", "quiet", "-select_streams", "v:0",
        "-show_entries", "frame=pkt_pts_time",
        "-of", "csv=p=0", "-skip_frame", "nokey", video_path
    ]
    
    try:
        result = subprocess.run(cmd1, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            keyframes = []
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line and line != 'N/A':
                    try:
                        timestamp = float(line)
                        keyframes.append(timestamp)
                    except ValueError:
                        continue
            
            if keyframes:
                keyframes = sorted(list(set(keyframes)))
                logging.info(f"Detected {len(keyframes)} keyframes using skip_frame method")
                return keyframes
    except (subprocess.TimeoutExpired, Exception) as e:
        logging.warning(f"Skip_frame method failed: {e}")
    
    # Method 2: Analyze frame types (more reliable but slower)
    cmd2 = [
        "ffprobe", "-v", "quiet", "-select_streams", "v:0",
        "-show_entries", "frame=best_effort_timestamp_time,pict_type",
        "-of", "csv=p=0", video_path
    ]
    
    try:
        result = subprocess.run(cmd2, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            keyframes = []
            for line in result.stdout.strip().split('\n'):
                parts = line.strip().split(',')
                if len(parts) == 2:
                    timestamp_str, frame_type = parts
                    if frame_type == 'I' and timestamp_str != 'N/A':
                        try:
                            timestamp = float(timestamp_str)
                            keyframes.append(timestamp)
                        except ValueError:
                            continue
            
            if keyframes:
                keyframes = sorted(list(set(keyframes)))
                logging.info(f"Detected {len(keyframes)} keyframes using frame analysis method")
                return keyframes
    except (subprocess.TimeoutExpired, Exception) as e:
        logging.warning(f"Frame analysis method failed: {e}")
    
    # Method 3: Fallback - create synthetic keyframes based on GOP size
    try:
        # Get video duration and estimate keyframes every 2 seconds (common GOP size)
        duration = ffprobe_duration(video_path)
        if duration and duration > 0:
            keyframes = [0.0]  # Always include start
            current = 2.0
            while current < duration:
                keyframes.append(current)
                current += 2.0
            
            logging.warning(f"Using synthetic keyframes for {os.path.basename(video_path)} - {len(keyframes)} estimated keyframes")
            return keyframes
    except Exception as e:
        logging.error(f"Synthetic keyframe generation failed: {e}")
    
    logging.error(f"All keyframe detection methods failed for {video_path}")
    return []

def validate_lossless_compatibility(video_path: str) -> Dict[str, Any]:
    """
    Validate video format for lossless editing capability.
    Reference: FFmpeg documentation on stream copy limitations.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Dictionary with compatibility information
    """
    if not os.path.exists(video_path):
        return {"compatible": False, "reason": "File not found"}
    
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", video_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return {"compatible": False, "reason": "Failed to analyze video"}
        
        data = json.loads(result.stdout)
        video_stream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
        audio_stream = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
        
        if not video_stream:
            return {"compatible": False, "reason": "No video stream found"}
        
        # Check for lossless-friendly codecs
        lossless_video_codecs = ["h264", "h265", "hevc", "vp9", "av1", "mpeg4"]
        lossless_audio_codecs = ["aac", "mp3", "ac3", "flac", "pcm_s16le"]
        
        video_codec = video_stream.get("codec_name", "").lower()
        audio_codec = audio_stream.get("codec_name", "").lower() if audio_stream else "none"
        
        video_compatible = video_codec in lossless_video_codecs
        audio_compatible = not audio_stream or audio_codec in lossless_audio_codecs
        
        # Check for B-frames (affects lossless cutting)
        has_b_frames = video_stream.get("has_b_frames", 0) > 0
        
        # Get container format
        container_format = data.get("format", {}).get("format_name", "").lower()
        container_compatible = any(fmt in container_format for fmt in ["mp4", "mov", "mkv", "avi"])
        
        overall_compatible = video_compatible and audio_compatible and container_compatible
        
        return {
            "compatible": overall_compatible,
            "video_codec": video_codec,
            "audio_codec": audio_codec,
            "container_format": container_format,
            "has_b_frames": has_b_frames,
            "video_compatible": video_compatible,
            "audio_compatible": audio_compatible,
            "container_compatible": container_compatible,
            "warnings": [w for w in [
                "B-frames present - may require re-encoding for precise cuts" if has_b_frames else None,
                f"Video codec '{video_codec}' may not support stream copy" if not video_compatible else None,
                f"Audio codec '{audio_codec}' may not support stream copy" if not audio_compatible else None,
                f"Container '{container_format}' may have limitations" if not container_compatible else None
            ] if w is not None]
        }
        
    except json.JSONDecodeError:
        return {"compatible": False, "reason": "Invalid video metadata"}
    except subprocess.TimeoutExpired:
        return {"compatible": False, "reason": "Analysis timeout"}
    except Exception as e:
        logging.error(f"Compatibility check error: {e}")
        return {"compatible": False, "reason": f"Analysis error: {str(e)}"}

def find_nearest_keyframe(timestamp: float, keyframes: List[float], prefer_before: bool = True) -> float:
    """
    Find optimal keyframe for lossless cutting.
    Algorithm based on industry-standard video editing practices.
    
    Args:
        timestamp: Target timestamp in seconds
        keyframes: List of keyframe timestamps
        prefer_before: If True, prefer keyframe before timestamp, else after
        
    Returns:
        Nearest keyframe timestamp
    """
    if not keyframes:
        return timestamp
    
    if prefer_before:
        # Find the closest keyframe before or at the timestamp
        valid_keyframes = [kf for kf in keyframes if kf <= timestamp]
        if valid_keyframes:
            return max(valid_keyframes)
        else:
            # No keyframe before, return first keyframe
            return keyframes[0]
    else:
        # Find the closest keyframe after or at the timestamp
        valid_keyframes = [kf for kf in keyframes if kf >= timestamp]
        if valid_keyframes:
            return min(valid_keyframes)
        else:
            # No keyframe after, return last keyframe
            return keyframes[-1]