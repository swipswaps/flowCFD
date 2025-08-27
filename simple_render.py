#!/usr/bin/env python3
import json
import subprocess
import sys
import os

def render_from_osp(osp_path, output_path):
    """
    Renders an OpenShot project using available FFmpeg encoders.
    Uses mpeg4 video codec which is available in your FFmpeg build.
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
    
    # Build a single FFmpeg command with multiple inputs and a complex filter
    inputs = []
    filter_parts = []
    
    for i, clip in enumerate(clips):
        start_time = clip.get('start', 0)
        end_time = clip.get('end', 0)
        duration = end_time - start_time
        
        if duration <= 0:
            print(f"Skipping clip {i+1}: invalid duration")
            continue
        
        # Add input with seeking
        inputs.extend(['-ss', str(start_time), '-t', str(duration), '-i', source_video])
        
        # Add this input to the filter chain
        filter_parts.append(f"[{i}:v][{i}:a]")
    
    if not filter_parts:
        print("Error: No valid clips found")
        return False
    
    # Create the concat filter
    concat_filter = f"{''.join(filter_parts)}concat=n={len(filter_parts)}:v=1:a=1[outv][outa]"
    
    # Build the complete FFmpeg command
    cmd = ['ffmpeg', '-y'] + inputs + [
        '-filter_complex', concat_filter,
        '-map', '[outv]',
        '-map', '[outa]',
        '-c:v', 'mpeg4',  # Use available mpeg4 encoder
        '-c:a', 'aac',    # Use available aac encoder
        '-b:v', '2M',     # Set video bitrate
        '-b:a', '128k',   # Set audio bitrate
        output_path
    ]
    
    print(f"\nRendering {len(filter_parts)} clips into final video...")
    print("This may take a few minutes...")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"Success! Final video saved as: {output_path}")
        return True
    else:
        print(f"Error creating video: {result.stderr}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 simple_render.py <project.osp> <output_video.mp4>")
        print("Example: python3 simple_render.py my_project.osp final_video.mp4")
        sys.exit(1)
    
    osp_file = sys.argv[1]
    output_file = sys.argv[2]
    
    success = render_from_osp(osp_file, output_file)
    sys.exit(0 if success else 1)
