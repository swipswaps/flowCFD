import os
import subprocess
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
    Generates a thumbnail for a video at a specific time offset.
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