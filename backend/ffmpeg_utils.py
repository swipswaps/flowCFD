import os
import subprocess
import math
import tempfile
import shutil

from typing import Iterable

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

def generate_thumbnail(video_path: str, output_thumbnail_path: str, time_offset: float = 1.0) -> bool:
    """
    Generates a single thumbnail for a video at a specific time offset.
    """
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(time_offset),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2", # quality (2 is good)
        "-f", "image2",
        output_thumbnail_path
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error generating thumbnail: {e.stderr}")
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
    Known-to-work pattern for trimming with re-encode for stable concat.
    """
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start}",
        "-t", f"{duration}",
        "-i", src,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-avoid_negative_ts", "make_zero",
        out_path
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode == 0

def concat_mp4s(filelist_path: str, output_path: str) -> bool:
    """
    ffmpeg concat demuxer (file list).
    """
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", filelist_path,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        output_path
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode == 0