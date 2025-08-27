import json
import uuid
import os
import sys
import subprocess
import copy

# This is a complete, default clip object structure derived from a real .osp file.
# It includes all the necessary keys that OpenShot expects to be present.
CLIP_TEMPLATE = {
    "alpha": {"Points": [{"co": {"X": 1.0, "Y": 1.0}, "handle_left": {"X": 0.5, "Y": 1.0}, "handle_right": {"X": 0.5, "Y": 0.0}, "handle_type": 0, "interpolation": 0}]},
    "anchor": 0,
    "channel_filter": {"Points": [{"co": {"X": 1.0, "Y": -1.0}, "handle_left": {"X": 0.5, "Y": 1.0}, "handle_right": {"X": 0.5, "Y": 0.0}, "handle_type": 0, "interpolation": 0}]},
    "channel_mapping": {"Points": [{"co": {"X": 1.0, "Y": -1.0}, "handle_left": {"X": 0.5, "Y": 1.0}, "handle_right": {"X": 0.5, "Y": 0.0}, "handle_type": 0, "interpolation": 0}]},
    "display": 0,
    "effects": [],
    "gravity": 4,
    "has_audio": {"Points": [{"co": {"X": 1.0, "Y": -1.0}, "handle_left": {"X": 0.5, "Y": 1.0}, "handle_right": {"X": 0.5, "Y": 0.0}, "handle_type": 0, "interpolation": 0}]},
    "has_video": {"Points": [{"co": {"X": 1.0, "Y": -1.0}, "handle_left": {"X": 0.5, "Y": 1.0}, "handle_right": {"X": 0.5, "Y": 0.0}, "handle_type": 0, "interpolation": 0}]},
    "location_x": {"Points": [{"co": {"X": 1.0, "Y": 0.0}, "handle_left": {"X": 0.5, "Y": 1.0}, "handle_right": {"X": 0.5, "Y": 0.0}, "handle_type": 0, "interpolation": 0}]},
    "location_y": {"Points": [{"co": {"X": 1.0, "Y": 0.0}, "handle_left": {"X": 0.5, "Y": 1.0}, "handle_right": {"X": 0.5, "Y": 0.0}, "handle_type": 0, "interpolation": 0}]},
    "mixing": 0,
    "scale_x": {"Points": [{"co": {"X": 1.0, "Y": 1.0}, "handle_left": {"X": 0.5, "Y": 1.0}, "handle_right": {"X": 0.5, "Y": 0.0}, "handle_type": 0, "interpolation": 0}]},
    "scale_y": {"Points": [{"co": {"X": 1.0, "Y": 1.0}, "handle_left": {"X": 0.5, "Y": 1.0}, "handle_right": {"X": 0.5, "Y": 0.0}, "handle_type": 0, "interpolation": 0}]},
    "time": {"Points": [{"co": {"X": 1.0, "Y": 1.0}, "handle_left": {"X": 0.5, "Y": 1.0}, "handle_right": {"X": 0.5, "Y": 0.0}, "handle_type": 0, "interpolation": 0}]},
    "volume": {"Points": [{"co": {"X": 1.0, "Y": 1.0}, "handle_left": {"X": 0.5, "Y": 1.0}, "handle_right": {"X": 0.5, "Y": 0.0}, "handle_type": 0, "interpolation": 0}]},
    "waveform": False,
}

def get_video_info(video_path):
    """Gets detailed video information using ffprobe."""
    command = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', video_path]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Error getting video info from ffprobe: {e}")
        return None

def create_openshot_project(csv_file_path, video_file_path, output_osp_path):
    video_info = get_video_info(video_file_path)
    if not video_info:
        print("Could not get video information. Aborting.")
        return

    video_stream = next((s for s in video_info['streams'] if s['codec_type'] == 'video'), None)
    if not video_stream:
        print("No video stream found in the file. Aborting.")
        return

    # --- Create the main File object, which OpenShot calls a "Reader" ---
    file_id = str(uuid.uuid4()).upper()
    file_reader_object = {
        "path": os.path.abspath(video_file_path),
        "id": file_id,
        "media_type": "video",
        "type": "FFmpegReader",
        "duration": float(video_info['format']['duration']),
        "width": video_stream.get('width'),
        "height": video_stream.get('height'),
        "vcodec": video_stream.get('codec_name'),
        "fps": {"num": int(video_stream['r_frame_rate'].split('/')[0]), "den": int(video_stream['r_frame_rate'].split('/')[1])}
    }

    # --- Basic Project Structure ---
    fps_num, fps_den = video_stream['r_frame_rate'].split('/')
    fps_float = int(fps_num) / int(fps_den)
    
    project = {
        "id": str(uuid.uuid4()).upper(),
        "width": video_stream.get('width', 1920),
        "height": video_stream.get('height', 1080),
        "fps": {"num": int(fps_num), "den": int(fps_den)},
        "profile": f"HD {video_stream.get('height', 1080)}p {round(fps_float)} fps",
        "files": [file_reader_object],
        "clips": [],
        "layers": [{"id": f"L{i}", "label": "", "number": i * 1000000, "y": 0, "lock": False} for i in range(1, 6)],
        "version": {"openshot-qt": "3.3.0", "libopenshot": "0.4.0"}
    }

    timeline_position = 0.0

    with open(csv_file_path, 'r') as f:
        for line in f:
            if line.strip().startswith('#') or not line.strip():
                continue
            
            parts = line.strip().split(',')
            try:
                start_time = float(parts[0])
                end_time = float(parts[1])
            except (ValueError, IndexError):
                print(f"Warning: Could not parse line '{line.strip()}'. Skipping.")
                continue

            duration = end_time - start_time
            if duration <= 0:
                continue

            # Create a full clip object by copying the template
            new_clip = copy.deepcopy(CLIP_TEMPLATE)
            
            # Update the specific fields for this clip
            new_clip.update({
                "id": str(uuid.uuid4()).upper(),
                "file_id": file_id,
                "layer": 1,
                "position": timeline_position,
                "start": start_time,
                "end": end_time,
                "duration": file_reader_object["duration"],
                "title": os.path.basename(video_file_path),
                "reader": file_reader_object # Embed reader info in the clip as per sample
            })
            
            project["clips"].append(new_clip)
            timeline_position += duration

    with open(output_osp_path, 'w') as f:
        json.dump(project, f, indent=4)
        
    print(f"Successfully created OpenShot project: {output_osp_path}")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python3 create_openshot_project.py <input_csv_file> <path_to_video> <output_osp_file>")
        sys.exit(1)
        
    csv_input = sys.argv[1]
    video_input = sys.argv[2]
    osp_output = sys.argv[3]
    create_openshot_project(csv_input, video_input, osp_output)
