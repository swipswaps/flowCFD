#!/usr/bin/env python3
import json
import subprocess
import sys
import os

def render_from_osp(osp_path, output_path):
    """
    Reads an OpenShot project file and renders it using FFmpeg directly.
    This bypasses all OpenShot export issues.
    """
    
    if not os.path.exists(osp_path):
        print(f"Error: Project file '{osp_path}' not found")
        return False
    
    # Load the project file
    try:
        with open(osp_path, 'r') as f:
            project = json.load(f)
    except Exception as e:
        print(f"Error reading project file: {e}")
        return False
    
    # Get the source video file
    if not project.get('files') or len(project['files']) == 0:
        print("Error: No source files found in project")
        return False
    
    source_video = project['files'][0]['path']
    if not os.path.exists(source_video):
        print(f"Error: Source video '{source_video}' not found")
        return False
    
    # Get all clips from the project
    clips = project.get('clips', [])
    if not clips:
        print("Error: No clips found in project")
        return False
    
    print(f"Found {len(clips)} clips in project")
    print(f"Source video: {source_video}")
    
    # Create a temporary file list for FFmpeg concat
    concat_file = "temp_concat.txt"
    temp_files = []
    
    try:
        # Extract each clip as a temporary file
        for i, clip in enumerate(clips):
            start_time = clip.get('start', 0)
            end_time = clip.get('end', 0)
            duration = end_time - start_time
            
            if duration <= 0:
                print(f"Skipping clip {i+1}: invalid duration")
                continue
            
            temp_filename = f"temp_clip_{i:03d}.mp4"
            temp_files.append(temp_filename)
            
            # Extract this clip using FFmpeg
            cmd = [
                'ffmpeg', '-y',  # -y to overwrite existing files
                '-i', source_video,
                '-ss', str(start_time),
                '-t', str(duration),
                '-c:v', 'libx264',  # CPU-based video encoding
                '-c:a', 'aac',      # Standard audio codec
                '-avoid_negative_ts', 'make_zero',
                temp_filename
            ]
            
            print(f"Extracting clip {i+1}/{len(clips)}: {start_time:.3f}s to {end_time:.3f}s")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Error extracting clip {i+1}: {result.stderr}")
                continue
        
        if not temp_files:
            print("Error: No clips were successfully extracted")
            return False
        
        # Create concat file for FFmpeg
        with open(concat_file, 'w') as f:
            for temp_file in temp_files:
                f.write(f"file '{temp_file}'\n")
        
        # Concatenate all clips into final video
        final_cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-movflags', '+faststart',  # Optimize for web playback
            output_path
        ]
        
        print(f"\nCombining {len(temp_files)} clips into final video...")
        result = subprocess.run(final_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Success! Final video saved as: {output_path}")
            return True
        else:
            print(f"Error creating final video: {result.stderr}")
            return False
            
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        if os.path.exists(concat_file):
            os.remove(concat_file)
    
    return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 direct_render.py <project.osp> <output_video.mp4>")
        print("Example: python3 direct_render.py my_project.osp final_video.mp4")
        sys.exit(1)
    
    osp_file = sys.argv[1]
    output_file = sys.argv[2]
    
    success = render_from_osp(osp_file, output_file)
    sys.exit(0 if success else 1)
