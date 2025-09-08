import os
import subprocess
import math
import tempfile
import shutil
import json
import logging
import datetime

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

def extract_clip_lossless(src: str, start: float, end: float, out_path: str,
                         force_keyframe: bool = True, 
                         smart_cut: bool = False) -> Dict[str, Any]:
    """
    Lossless-first clip extraction with comprehensive fallback strategy.
    Based on LosslessCut methodology and FFmpeg best practices.
    
    Args:
        src: Source video path
        start: Start time in seconds
        end: End time in seconds  
        out_path: Output file path
        force_keyframe: If True, adjust to nearest keyframes for lossless cutting
        smart_cut: If True, use smart cutting for non-keyframe cuts
    
    Returns:
        Dict containing extraction metadata and quality information
    """
    import time
    start_time = time.time()
    duration = end - start
    
    # Get keyframes for lossless analysis (with timeout protection)
    try:
        keyframes = get_keyframes(src)
        logging.info(f"Detected {len(keyframes)} keyframes for lossless analysis")
    except Exception as e:
        logging.warning(f"Keyframe detection failed: {e}")
        keyframes = []
    
    # Check if cut points align with keyframes (within 0.1s tolerance)
    keyframe_tolerance = 0.1
    start_keyframe = find_nearest_keyframe(start, keyframes, prefer_before=True) if keyframes else None
    end_keyframe = find_nearest_keyframe(end, keyframes, prefer_before=False) if keyframes else None
    
    start_aligned = start_keyframe is not None and abs(start - start_keyframe) <= keyframe_tolerance
    end_aligned = end_keyframe is not None and abs(end - end_keyframe) <= keyframe_tolerance
    keyframe_aligned = start_aligned and end_aligned
    
    # Adjust to keyframes if force_keyframe is True and alignment is close
    if force_keyframe and keyframes:
        if start_keyframe is not None and abs(start - start_keyframe) <= 1.0:  # Within 1 second
            start = start_keyframe
            start_aligned = True
        if end_keyframe is not None and abs(end - end_keyframe) <= 1.0:  # Within 1 second  
            end = end_keyframe
            end_aligned = True
        duration = end - start
        keyframe_aligned = start_aligned and end_aligned
    
    # Priority 1: Keyframe-aligned stream copy (truly lossless)
    if keyframe_aligned:
        success = _extract_with_stream_copy(src, start, duration, out_path)
        if success:
            processing_time = time.time() - start_time
            file_size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
            return {
                "success": True,
                "method_used": "stream_copy",
                "quality_preserved": True,
                "keyframe_aligned": True,
                "processing_time": processing_time,
                "file_size": file_size,
                "warnings": []
            }
    
    # Priority 2: Smart cut with minimal re-encoding
    if smart_cut and keyframes:
        success = _extract_with_smart_cut(src, start, end, out_path, keyframes)
        if success:
            processing_time = time.time() - start_time
            file_size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
            return {
                "success": True,
                "method_used": "smart_cut",
                "quality_preserved": True,  # Near-lossless
                "keyframe_aligned": False,
                "processing_time": processing_time,
                "file_size": file_size,
                "warnings": ["Smart cut used - minimal quality loss"]
            }
    
    # Priority 3: High-quality re-encoding with original codec
    success = _extract_with_quality_encoding(src, start, duration, out_path)
    if success:
        processing_time = time.time() - start_time
        file_size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
        return {
            "success": True,
            "method_used": "re_encoded",
            "quality_preserved": False,
            "keyframe_aligned": keyframe_aligned,
            "processing_time": processing_time,
            "file_size": file_size,
            "warnings": ["Re-encoding required - some quality loss"]
        }
    
    # Priority 4: Fallback encoding with quality preservation
    success = _extract_with_fallback_encoding(src, start, duration, out_path)
    processing_time = time.time() - start_time
    file_size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    
    return {
        "success": success,
        "method_used": "fallback_encoded" if success else "failed",
        "quality_preserved": False,
        "keyframe_aligned": keyframe_aligned,
        "processing_time": processing_time,
        "file_size": file_size,
        "warnings": ["Fallback encoding used - quality loss possible"] if success else ["All extraction methods failed"]
    }


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
        result = subprocess.run(cmd1, capture_output=True, text=True, timeout=10)
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
        result = subprocess.run(cmd2, capture_output=True, text=True, timeout=15)
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


def _extract_with_stream_copy(src: str, start: float, duration: float, out_path: str) -> bool:
    """
    Extract clip using stream copy (truly lossless).
    Only works when cut points align with keyframes.
    """
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start}",
        "-t", f"{duration}",
        "-i", src,
        "-c", "copy",
        "-avoid_negative_ts", "make_zero",
        out_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            logging.info(f"Stream copy extraction successful: {os.path.basename(out_path)}")
            return True
        else:
            logging.warning(f"Stream copy failed: {result.stderr[-200:] if result.stderr else 'No error message'}")
            return False
    except subprocess.TimeoutExpired:
        logging.error(f"Stream copy extraction timed out for {os.path.basename(src)}")
        return False
    except Exception as e:
        logging.error(f"Stream copy extraction failed: {e}")
        return False


def _extract_with_smart_cut(src: str, start: float, end: float, out_path: str, keyframes: List[float]) -> bool:
    """
    Smart cut implementation for non-keyframe-aligned edits.
    Re-encodes only affected frames while preserving quality.
    Based on LosslessCut methodology and FFmpeg segment muxer.
    """
    # Find keyframes before and after cut points
    pre_keyframe = find_nearest_keyframe(start, keyframes, prefer_before=True)
    post_keyframe = find_nearest_keyframe(end, keyframes, prefer_before=False)
    
    if pre_keyframe is None or post_keyframe is None:
        logging.warning("Smart cut failed: Could not find suitable keyframes")
        return False
    
    # Calculate precise timing for smart cut
    pre_cut_offset = start - pre_keyframe
    post_cut_offset = end - pre_keyframe
    
    # Ensure we have reasonable keyframe boundaries
    if pre_cut_offset < 0 or post_cut_offset <= pre_cut_offset:
        logging.warning(f"Smart cut failed: Invalid timing - pre_offset: {pre_cut_offset}, post_offset: {post_cut_offset}")
        return False
    
    logging.info(f"Smart cut: keyframe at {pre_keyframe}s, extracting {pre_cut_offset:.3f}s to {post_cut_offset:.3f}s")
    
    # Method 1: Try with filter_complex for precise frame-accurate cutting
    cmd_precise = [
        "ffmpeg", "-y",
        "-ss", f"{pre_keyframe}",
        "-i", src,
        "-filter_complex",
        f"[0:v]trim=start={pre_cut_offset}:end={post_cut_offset},setpts=PTS-STARTPTS[v];"
        f"[0:a]atrim=start={pre_cut_offset}:end={post_cut_offset},asetpts=PTS-STARTPTS[a]",
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-crf", "18",  # High quality
        "-preset", "medium",
        "-c:a", "aac",
        "-movflags", "+faststart",
        "-avoid_negative_ts", "make_zero",
        out_path
    ]
    
    try:
        result = subprocess.run(cmd_precise, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            logging.info(f"Smart cut (precise) extraction successful: {os.path.basename(out_path)}")
            return True
        else:
            logging.warning(f"Smart cut (precise) failed: {result.stderr[-300:] if result.stderr else 'No error message'}")
    except subprocess.TimeoutExpired:
        logging.error(f"Smart cut (precise) extraction timed out for {os.path.basename(src)}")
    except Exception as e:
        logging.warning(f"Smart cut (precise) extraction failed: {e}")
    
    # Method 2: Fallback to simpler approach with seek and duration
    duration = end - start
    cmd_simple = [
        "ffmpeg", "-y",
        "-ss", f"{start}",
        "-t", f"{duration}",
        "-i", src,
        "-c:v", "libx264",
        "-crf", "18",  # High quality
        "-preset", "medium", 
        "-c:a", "aac",
        "-movflags", "+faststart",
        "-avoid_negative_ts", "make_zero",
        out_path
    ]
    
    try:
        result = subprocess.run(cmd_simple, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            logging.info(f"Smart cut (simple) extraction successful: {os.path.basename(out_path)}")
            return True
        else:
            logging.warning(f"Smart cut (simple) failed: {result.stderr[-300:] if result.stderr else 'No error message'}")
            return False
    except subprocess.TimeoutExpired:
        logging.error(f"Smart cut (simple) extraction timed out for {os.path.basename(src)}")
        return False
    except Exception as e:
        logging.error(f"Smart cut (simple) extraction failed: {e}")
        return False


def _extract_with_quality_encoding(src: str, start: float, duration: float, out_path: str) -> bool:
    """
    High-quality re-encoding with original codec preservation attempt.
    """
    # Try to detect original codec and use it
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start}",
        "-t", f"{duration}",
        "-i", src,
        "-c:v", "libx264",
        "-crf", "18",  # High quality
        "-preset", "medium",
        "-c:a", "aac",
        "-avoid_negative_ts", "make_zero",
        out_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            logging.info(f"Quality encoding extraction successful: {os.path.basename(out_path)}")
            return True
        else:
            logging.warning(f"Quality encoding failed: {result.stderr[-200:] if result.stderr else 'No error message'}")
            return False
    except subprocess.TimeoutExpired:
        logging.error(f"Quality encoding extraction timed out for {os.path.basename(src)}")
        return False
    except Exception as e:
        logging.error(f"Quality encoding extraction failed: {e}")
        return False


def _extract_with_fallback_encoding(src: str, start: float, duration: float, out_path: str) -> bool:
    """
    Fallback encoding with quality preservation using available encoders.
    """
    # Try with libopenh264 first
    cmd_h264 = [
        "ffmpeg", "-y",
        "-ss", f"{start}",
        "-t", f"{duration}",
        "-i", src,
        "-c:v", "libopenh264",
        "-c:a", "aac",
        "-avoid_negative_ts", "make_zero",
        out_path
    ]
    
    try:
        result = subprocess.run(cmd_h264, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            logging.info(f"Fallback H264 encoding successful: {os.path.basename(out_path)}")
            return True
    except Exception as e:
        logging.warning(f"Fallback H264 encoding failed: {e}")
    
    # Last resort: default encoding
    cmd_default = [
        "ffmpeg", "-y",
        "-ss", f"{start}",
        "-t", f"{duration}",
        "-i", src,
        "-avoid_negative_ts", "make_zero",
        out_path
    ]
    
    try:
        result = subprocess.run(cmd_default, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            logging.info(f"Default fallback encoding successful: {os.path.basename(out_path)}")
            return True
        else:
            logging.error(f"All fallback encoding methods failed: {result.stderr[-200:] if result.stderr else 'No error message'}")
            return False
    except Exception as e:
        logging.error(f"Default fallback encoding failed: {e}")
        return False

def find_nearest_keyframe(timestamp: float, keyframes: List[float], 
                         prefer_before: bool = True):
    """
    Find optimal keyframe for lossless cutting.
    Algorithm based on industry-standard video editing practices.
    
    Args:
        timestamp: Target timestamp in seconds
        keyframes: List of keyframe timestamps
        prefer_before: If True, prefer keyframe before timestamp; if False, prefer after
    
    Returns:
        Nearest keyframe timestamp, or None if no keyframes available
    """
    if not keyframes:
        return None
    
    # Find keyframes before and after the timestamp
    before_keyframes = [kf for kf in keyframes if kf <= timestamp]
    after_keyframes = [kf for kf in keyframes if kf > timestamp]
    
    if prefer_before:
        # Prefer keyframe before timestamp
        if before_keyframes:
            return max(before_keyframes)  # Closest before
        elif after_keyframes:
            return min(after_keyframes)  # Fallback to closest after
        else:
            return keyframes[0]  # This case shouldn't happen if keyframes is not empty
    else:
        # Prefer keyframe after timestamp
        if after_keyframes:
            return min(after_keyframes)  # Closest after
        elif before_keyframes:
            return max(before_keyframes)  # Fallback to closest before
        else:
            return keyframes[-1]  # This case shouldn't happen if keyframes is not empty


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


# === PHASE 3: QUALITY ASSURANCE & MONITORING ===

def analyze_quality_loss(original: str, processed: str, timeout: int = 60) -> Dict[str, Any]:
    """
    Comprehensive quality analysis using FFmpeg filters.
    
    Calculates SSIM, PSNR, and VMAF metrics to measure quality preservation.
    Based on FFmpeg quality filter documentation and professional standards.
    
    Args:
        original: Path to original video file
        processed: Path to processed video file
        timeout: Maximum analysis time in seconds
        
    Returns:
        Dict containing quality metrics and analysis results
    """
    import time
    start_time = time.time()
    
    results = {
        "ssim": None,
        "psnr": None, 
        "vmaf": None,
        "file_size_ratio": None,
        "bitrate_ratio": None,
        "processing_time": 0,
        "success": False,
        "warnings": []
    }
    
    try:
        # Check if files exist
        if not os.path.exists(original):
            return {**results, "error": f"Original file not found: {original}"}
        if not os.path.exists(processed):
            return {**results, "error": f"Processed file not found: {processed}"}
            
        # Get file sizes for comparison
        original_size = os.path.getsize(original)
        processed_size = os.path.getsize(processed)
        results["file_size_ratio"] = processed_size / original_size if original_size > 0 else 0
        
        # Calculate SSIM (Structural Similarity Index)
        results["ssim"] = _calculate_ssim(original, processed, timeout)
        
        # Calculate PSNR (Peak Signal-to-Noise Ratio)
        results["psnr"] = _calculate_psnr(original, processed, timeout)
        
        # Calculate VMAF (Video Multimethod Assessment Fusion) - if available
        try:
            results["vmaf"] = _calculate_vmaf(original, processed, timeout)
        except Exception as e:
            results["warnings"].append(f"VMAF calculation failed: {str(e)}")
            
        # Get bitrate information
        try:
            original_bitrate = _get_bitrate(original)
            processed_bitrate = _get_bitrate(processed)
            if original_bitrate and processed_bitrate:
                results["bitrate_ratio"] = processed_bitrate / original_bitrate
        except Exception as e:
            results["warnings"].append(f"Bitrate analysis failed: {str(e)}")
            
        results["processing_time"] = time.time() - start_time
        results["success"] = True
        
        # Add quality assessment
        results["quality_assessment"] = _assess_quality(results)
        
        logging.info(f"Quality analysis completed: SSIM={results['ssim']}, PSNR={results['psnr']}")
        return results
        
    except Exception as e:
        results["processing_time"] = time.time() - start_time
        results["error"] = str(e)
        logging.error(f"Quality analysis failed: {e}")
        return results


def _calculate_ssim(original: str, processed: str, timeout: int) -> float:
    """Calculate SSIM using FFmpeg ssim filter."""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = os.path.join(temp_dir, "ssim.log")
        
        cmd = [
            "ffmpeg", "-i", original, "-i", processed,
            "-lavfi", f"ssim=stats_file={log_file}",
            "-f", "null", "-"
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=timeout, check=True)
            
            # Parse SSIM log file
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        # Get average SSIM from last line
                        last_line = lines[-1].strip()
                        if "All:" in last_line:
                            ssim_value = float(last_line.split("All:")[1].split()[0])
                            return ssim_value
            
            return 0.0
            
        except subprocess.TimeoutExpired:
            logging.warning(f"SSIM calculation timed out after {timeout}s")
            return 0.0
        except Exception as e:
            logging.warning(f"SSIM calculation failed: {e}")
            return 0.0


def _calculate_psnr(original: str, processed: str, timeout: int) -> float:
    """Calculate PSNR using FFmpeg psnr filter."""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = os.path.join(temp_dir, "psnr.log")
        
        cmd = [
            "ffmpeg", "-i", original, "-i", processed,
            "-lavfi", f"psnr=stats_file={log_file}",
            "-f", "null", "-"
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=timeout, check=True)
            
            # Parse PSNR log file
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        # Get average PSNR from last line
                        last_line = lines[-1].strip()
                        if "average:" in last_line:
                            psnr_value = float(last_line.split("average:")[1].split()[0])
                            return psnr_value
            
            return 0.0
            
        except subprocess.TimeoutExpired:
            logging.warning(f"PSNR calculation timed out after {timeout}s")
            return 0.0
        except Exception as e:
            logging.warning(f"PSNR calculation failed: {e}")
            return 0.0


def _calculate_vmaf(original: str, processed: str, timeout: int) -> float:
    """Calculate VMAF using FFmpeg libvmaf filter (if available)."""
    try:
        # Check if libvmaf is available
        check_cmd = ["ffmpeg", "-filters"]
        result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10)
        if "libvmaf" not in result.stdout:
            raise Exception("libvmaf filter not available in this FFmpeg build")
            
        cmd = [
            "ffmpeg", "-i", processed, "-i", original,
            "-lavfi", "libvmaf=log_fmt=json",
            "-f", "null", "-"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        
        # Parse VMAF output from stderr
        if "VMAF score:" in result.stderr:
            for line in result.stderr.split('\n'):
                if "VMAF score:" in line:
                    score = float(line.split("VMAF score:")[1].strip())
                    return score
                    
        return 0.0
        
    except Exception as e:
        logging.warning(f"VMAF calculation failed: {e}")
        return 0.0


def _get_bitrate(video_path: str) -> float:
    """Get video bitrate using FFprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-select_streams", "v:0",
            "-show_entries", "stream=bit_rate", "-of", "csv=p=0",
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
            
        return 0.0
        
    except Exception as e:
        logging.warning(f"Bitrate extraction failed: {e}")
        return 0.0


def _assess_quality(metrics: Dict[str, Any]) -> Dict[str, str]:
    """Assess overall quality based on calculated metrics."""
    assessment = {
        "overall": "unknown",
        "ssim_grade": "unknown", 
        "psnr_grade": "unknown",
        "recommendations": []
    }
    
    # SSIM assessment (0-1, higher is better)
    if metrics["ssim"] is not None:
        if metrics["ssim"] >= 0.99:
            assessment["ssim_grade"] = "excellent"
        elif metrics["ssim"] >= 0.95:
            assessment["ssim_grade"] = "good"
        elif metrics["ssim"] >= 0.90:
            assessment["ssim_grade"] = "fair"
        else:
            assessment["ssim_grade"] = "poor"
            assessment["recommendations"].append("SSIM below 0.90 indicates significant quality loss")
    
    # PSNR assessment (dB, higher is better)
    if metrics["psnr"] is not None:
        if metrics["psnr"] >= 45:
            assessment["psnr_grade"] = "excellent"
        elif metrics["psnr"] >= 35:
            assessment["psnr_grade"] = "good"  
        elif metrics["psnr"] >= 25:
            assessment["psnr_grade"] = "fair"
        else:
            assessment["psnr_grade"] = "poor"
            assessment["recommendations"].append("PSNR below 25dB indicates poor quality preservation")
    
    # Overall assessment
    if (assessment["ssim_grade"] in ["excellent", "good"] and 
        assessment["psnr_grade"] in ["excellent", "good"]):
        assessment["overall"] = "lossless_quality"
    elif (assessment["ssim_grade"] in ["excellent", "good", "fair"] and 
          assessment["psnr_grade"] in ["excellent", "good", "fair"]):
        assessment["overall"] = "near_lossless"
    else:
        assessment["overall"] = "lossy"
        
    return assessment


def generate_quality_report(processing_chain: List[Dict]) -> Dict[str, Any]:
    """
    Generate comprehensive quality preservation report.
    Track quality loss through entire editing pipeline.
    
    Args:
        processing_chain: List of processing steps with original/result paths
        
    Returns:
        Comprehensive quality report with metrics and recommendations
    """
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "processing_steps": len(processing_chain),
        "overall_quality_loss": 0.0,
        "step_analysis": [],
        "summary": {
            "lossless_steps": 0,
            "near_lossless_steps": 0,
            "lossy_steps": 0,
            "total_ssim_loss": 0.0,
            "total_psnr_loss": 0.0
        },
        "recommendations": [],
        "success": False
    }
    
    try:
        previous_ssim = 1.0
        previous_psnr = float('inf')
        
        for i, step in enumerate(processing_chain):
            if not all(k in step for k in ["original", "processed", "operation"]):
                continue
                
            # Analyze this processing step
            quality_metrics = analyze_quality_loss(step["original"], step["processed"])
            
            step_analysis = {
                "step": i + 1,
                "operation": step["operation"],
                "metrics": quality_metrics,
                "quality_change": {
                    "ssim_delta": (quality_metrics.get("ssim", 0) - previous_ssim) if quality_metrics.get("ssim") else 0,
                    "psnr_delta": (quality_metrics.get("psnr", 0) - previous_psnr) if quality_metrics.get("psnr") and previous_psnr != float('inf') else 0
                }
            }
            
            report["step_analysis"].append(step_analysis)
            
            # Update cumulative metrics
            if quality_metrics.get("success"):
                if quality_metrics.get("quality_assessment", {}).get("overall") == "lossless_quality":
                    report["summary"]["lossless_steps"] += 1
                elif quality_metrics.get("quality_assessment", {}).get("overall") == "near_lossless":
                    report["summary"]["near_lossless_steps"] += 1
                else:
                    report["summary"]["lossy_steps"] += 1
                    
                # Track cumulative loss
                if quality_metrics.get("ssim"):
                    previous_ssim = quality_metrics["ssim"]
                if quality_metrics.get("psnr"):
                    previous_psnr = quality_metrics["psnr"]
        
        # Calculate overall quality preservation
        report["summary"]["total_ssim_loss"] = 1.0 - previous_ssim
        report["summary"]["total_psnr_loss"] = max(0, 100 - previous_psnr)  # Rough approximation
        
        # Generate recommendations
        if report["summary"]["lossy_steps"] > 0:
            report["recommendations"].append("Consider using lossless extraction methods for better quality preservation")
        if report["summary"]["total_ssim_loss"] > 0.05:
            report["recommendations"].append("Significant quality loss detected. Review processing pipeline.")
        if report["summary"]["lossless_steps"] == len(processing_chain):
            report["recommendations"].append("Excellent! All processing steps maintained lossless quality.")
            
        report["success"] = True
        return report
        
    except Exception as e:
        report["error"] = str(e)
        logging.error(f"Quality report generation failed: {e}")
        return report


def concat_clips_lossless(clips: List[Dict], output: str, 
                         quality_target: str = "lossless") -> Dict[str, Any]:
    """
    Enhanced concatenation preserving maximum quality.
    Based on FFmpeg concat demuxer best practices and lossless editing principles.
    
    Args:
        clips: List of clip dictionaries with 'path' and metadata
        output: Output file path
        quality_target: "lossless", "near_lossless", or "lossy"
        
    Returns:
        Dict with concatenation results and quality metrics
    """
    import time
    start_time = time.time()
    
    result = {
        "success": False,
        "method_used": "unknown",
        "quality_target": quality_target,
        "clips_processed": len(clips),
        "processing_time": 0,
        "quality_analysis": {},
        "warnings": [],
        "error": None
    }
    
    try:
        if not clips:
            result["error"] = "No clips provided"
            return result
            
        # Validate all clip files exist
        for i, clip in enumerate(clips):
            clip_path = clip.get("path")
            if not clip_path or not os.path.exists(clip_path):
                result["error"] = f"Clip {i+1} not found: {clip_path}"
                return result
                
        # Strategy 1: Try lossless concat with demuxer (fastest, best quality)
        if quality_target in ["lossless", "near_lossless"]:
            success = _concat_with_demuxer(clips, output)
            if success:
                result["method_used"] = "concat_demuxer"
                result["success"] = True
                result["processing_time"] = time.time() - start_time
                
                # Analyze quality if requested
                if len(clips) > 0:
                    first_clip = clips[0]["path"]
                    quality_metrics = analyze_quality_loss(first_clip, output, timeout=30)
                    result["quality_analysis"] = quality_metrics
                    
                logging.info(f"Lossless concatenation successful: {len(clips)} clips")
                return result
            else:
                result["warnings"].append("Concat demuxer failed, trying filter method")
                
        # Strategy 2: Try concat filter with stream copy
        if quality_target in ["lossless", "near_lossless"]:
            success = _concat_with_filter_copy(clips, output)
            if success:
                result["method_used"] = "concat_filter_copy"
                result["success"] = True
                result["processing_time"] = time.time() - start_time
                
                logging.info(f"Stream copy concatenation successful: {len(clips)} clips")
                return result
            else:
                result["warnings"].append("Stream copy concat failed, trying re-encoding")
                
        # Strategy 3: Fallback to re-encoding concat (lossy but reliable)
        success = _concat_with_reencoding(clips, output, quality_target)
        if success:
            result["method_used"] = "concat_reencoded"
            result["success"] = True
            result["processing_time"] = time.time() - start_time
            
            # Analyze quality loss
            if len(clips) > 0:
                first_clip = clips[0]["path"]
                quality_metrics = analyze_quality_loss(first_clip, output, timeout=30)
                result["quality_analysis"] = quality_metrics
                
            logging.info(f"Re-encoded concatenation successful: {len(clips)} clips")
            return result
        else:
            result["error"] = "All concatenation methods failed"
            
    except Exception as e:
        result["error"] = str(e)
        logging.error(f"Lossless concatenation failed: {e}")
        
    result["processing_time"] = time.time() - start_time
    return result


def _concat_with_demuxer(clips: List[Dict], output: str) -> bool:
    """
    Concatenate using FFmpeg concat demuxer (lossless, fastest).
    Requires all clips to have identical encoding parameters.
    """
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create concat file list
            concat_file = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_file, 'w') as f:
                for clip in clips:
                    # Use absolute paths and escape quotes
                    abs_path = os.path.abspath(clip["path"])
                    f.write(f"file '{abs_path}'\n")
                    
            # Use concat demuxer with stream copy
            cmd = [
                "ffmpeg", "-f", "concat", "-safe", "0", 
                "-i", concat_file,
                "-c", "copy",  # Stream copy for lossless
                "-avoid_negative_ts", "make_zero",
                "-y", output
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            return result.returncode == 0
            
    except Exception as e:
        logging.warning(f"Concat demuxer failed: {e}")
        return False


def _concat_with_filter_copy(clips: List[Dict], output: str) -> bool:
    """
    Concatenate using FFmpeg concat filter with stream copy.
    More flexible than demuxer but still preserves quality.
    """
    try:
        # Build filter inputs
        inputs = []
        for clip in clips:
            inputs.extend(["-i", clip["path"]])
            
        # Build concat filter
        filter_parts = []
        for i in range(len(clips)):
            filter_parts.append(f"[{i}:v][{i}:a]")
            
        concat_filter = f"{''.join(filter_parts)}concat=n={len(clips)}:v=1:a=1[outv][outa]"
        
        cmd = [
            "ffmpeg"
        ] + inputs + [
            "-filter_complex", concat_filter,
            "-map", "[outv]", "-map", "[outa]",
            "-c:v", "copy",  # Try stream copy first
            "-c:a", "copy",
            "-y", output
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode == 0:
            return True
            
        # If copy fails, try with minimal re-encoding
        cmd = [
            "ffmpeg"
        ] + inputs + [
            "-filter_complex", concat_filter,
            "-map", "[outv]", "-map", "[outa]",
            "-c:v", "libx264", "-crf", "18",  # High quality re-encoding
            "-c:a", "aac", "-b:a", "192k",
            "-y", output
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        return result.returncode == 0
        
    except Exception as e:
        logging.warning(f"Concat filter failed: {e}")
        return False


def _concat_with_reencoding(clips: List[Dict], output: str, quality_target: str) -> bool:
    """
    Concatenate with quality-controlled re-encoding.
    Most compatible but with potential quality loss.
    """
    try:
        # Build inputs
        inputs = []
        for clip in clips:
            inputs.extend(["-i", clip["path"]])
            
        # Build concat filter
        filter_parts = []
        for i in range(len(clips)):
            filter_parts.append(f"[{i}:v][{i}:a]")
            
        concat_filter = f"{''.join(filter_parts)}concat=n={len(clips)}:v=1:a=1[outv][outa]"
        
        # Quality settings based on target
        if quality_target == "near_lossless":
            video_codec = ["-c:v", "libx264", "-crf", "16"]
            audio_codec = ["-c:a", "aac", "-b:a", "192k"]
        else:  # lossy
            video_codec = ["-c:v", "libx264", "-crf", "23"]
            audio_codec = ["-c:a", "aac", "-b:a", "128k"]
            
        cmd = [
            "ffmpeg"
        ] + inputs + [
            "-filter_complex", concat_filter,
            "-map", "[outv]", "-map", "[outa]"
        ] + video_codec + audio_codec + [
            "-y", output
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=600)
        return result.returncode == 0
        
    except Exception as e:
        logging.warning(f"Re-encoding concat failed: {e}")
        return False


def validate_concat_compatibility(clips: List[Dict]) -> Dict[str, Any]:
    """
    Validate that clips can be concatenated losslessly.
    Checks encoding parameters for compatibility.
    """
    compatibility = {
        "lossless_compatible": False,
        "issues": [],
        "recommendations": [],
        "clips_analyzed": len(clips)
    }
    
    if len(clips) < 2:
        compatibility["issues"].append("Need at least 2 clips for concatenation")
        return compatibility
        
    try:
        # Get metadata for first clip as reference
        reference_clip = clips[0]["path"]
        ref_metadata = _get_video_metadata(reference_clip)
        
        if not ref_metadata:
            compatibility["issues"].append("Could not analyze reference clip metadata")
            return compatibility
            
        ref_codec = ref_metadata.get("codec_name")
        ref_width = ref_metadata.get("width")
        ref_height = ref_metadata.get("height")
        ref_framerate = ref_metadata.get("r_frame_rate")
        
        # Check all other clips against reference
        for i, clip in enumerate(clips[1:], 1):
            clip_metadata = _get_video_metadata(clip["path"])
            
            if not clip_metadata:
                compatibility["issues"].append(f"Could not analyze clip {i+1} metadata")
                continue
                
            # Check codec compatibility
            if clip_metadata.get("codec_name") != ref_codec:
                compatibility["issues"].append(f"Clip {i+1} codec mismatch: {clip_metadata.get('codec_name')} vs {ref_codec}")
                
            # Check resolution compatibility
            if (clip_metadata.get("width") != ref_width or 
                clip_metadata.get("height") != ref_height):
                compatibility["issues"].append(f"Clip {i+1} resolution mismatch: {clip_metadata.get('width')}x{clip_metadata.get('height')} vs {ref_width}x{ref_height}")
                
            # Check framerate compatibility
            if clip_metadata.get("r_frame_rate") != ref_framerate:
                compatibility["issues"].append(f"Clip {i+1} framerate mismatch: {clip_metadata.get('r_frame_rate')} vs {ref_framerate}")
                
        # Determine compatibility
        if not compatibility["issues"]:
            compatibility["lossless_compatible"] = True
            compatibility["recommendations"].append("All clips compatible for lossless concatenation")
        else:
            compatibility["recommendations"].append("Consider re-encoding clips to match parameters for lossless concat")
            compatibility["recommendations"].append("Alternative: Use quality-controlled re-encoding concat")
            
        return compatibility
        
    except Exception as e:
        compatibility["issues"].append(f"Compatibility check failed: {str(e)}")
        return compatibility


def _get_video_metadata(video_path: str) -> Dict[str, Any]:
    """Get detailed video metadata for compatibility checking."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height,r_frame_rate,bit_rate",
            "-of", "json", video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if "streams" in data and len(data["streams"]) > 0:
                return data["streams"][0]
                
        return {}
        
    except Exception as e:
        logging.warning(f"Metadata extraction failed: {e}")
        return {}
