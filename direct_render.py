#!/usr/bin/env python3
import json
import subprocess
import sys
import os
import tempfile # NEW: Import tempfile module

def render_from_osp(osp_path, output_path):
    """
    Reads an OpenShot project file and renders it using FFmpeg directly.
    This bypasses all OpenShot export issues and uses a secure temporary directory.
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
    
    # NEW: Use a temporary directory for all intermediate files
    with tempfile.TemporaryDirectory() as temp_dir:
        concat_file_path = os.path.join(temp_dir, "concat.txt")
        temp_files = []
        
        # Extract each clip as a temporary file inside the temp_dir
        for i, clip in enumerate(clips):
            start_time = clip.get('start', 0)
            end_time = clip.get('end', 0)
            duration = end_time - start_time
            
            if duration <= 0:
                print(f"Skipping clip {i+1}: invalid duration")
                continue
            
            # Securely create temp filename in our temp directory
            temp_filename = os.path.join(temp_dir, f"clip_{i:03d}.mp4")
            temp_files.append(temp_filename)
            
            cmd = [
                'ffmpeg', '-y',
                '-i', source_video,
                '-ss', str(start_time),
                '-t', str(duration),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-avoid_negative_ts', 'make_zero',
                temp_filename
            ]
            
            print(f"Extracting clip {i+1}/{len(clips)}: {start_time:.3f}s to {end_time:.3f}s")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Error extracting clip {i+1}: {result.stderr}")
                # Using a context manager means we don't need to manually clean up here
                return False # Exit early on failure
        
        if not temp_files:
            print("Error: No clips were successfully extracted")
            return False
        
        # Create concat file for FFmpeg
        with open(concat_file_path, 'w') as f:
            for temp_file in temp_files:
                # FFmpeg concat requires a specific format
                f.write(f"file '{os.path.abspath(temp_file)}'\n")
        
        # Concatenate all clips into final video
        final_cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file_path,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-movflags', '+faststart',
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
            
    # The temporary directory and its contents are automatically removed here
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
