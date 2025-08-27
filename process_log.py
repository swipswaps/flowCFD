import sys
import subprocess
import json

def hms_to_seconds(t):
    """Converts HH:MM:SS.ms time string to seconds."""
    if not t:
        return 0.0
    parts = t.split(':')
    try:
        h = int(parts[0])
        m = int(parts[1])
        s = float(parts[2])
        return float(h * 3600 + m * 60 + s)
    except (ValueError, IndexError):
        print(f"Warning: Could not parse timestamp '{t}'. Skipping.")
        return None

def get_video_duration(video_path):
    """Gets the duration of a video file in seconds using ffprobe."""
    command = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        print(f"Error getting video duration: {e}")
        return None

def process_log_for_openshot(log_file_path, video_file_path, output_csv_path):
    """
    Reads a log file, pairs timestamps, and if an odd one exists,
    uses the video duration as the final OUT point.
    """
    with open(log_file_path, 'r') as f:
        lines = [line.strip().replace(',', '') for line in f if line.strip()]

    pairs = []
    for i in range(0, len(lines) - (len(lines) % 2), 2):
        pairs.append((lines[i], lines[i+1]))

    # Handle the final odd timestamp if it exists
    if len(lines) % 2 != 0:
        print("Odd number of timestamps found. Using video duration for the final OUT point.")
        duration = get_video_duration(video_file_path)
        if duration is not None:
            last_in_point_str = lines[-1]
            last_in_point_sec = hms_to_seconds(last_in_point_str)
            if last_in_point_sec is not None and last_in_point_sec < duration:
                # ffprobe returns duration as a float, which is what we need
                pairs.append((last_in_point_str, str(duration)))
            else:
                print(f"Warning: Final IN point '{last_in_point_str}' is after the video ends. Discarding.")
        else:
             print("Warning: Could not get video duration. The last timestamp will be ignored.")


    with open(output_csv_path, 'w') as f:
        f.write("# IN,OUT (seconds)\n")
        for start_str, end_str in pairs:
            start_sec = hms_to_seconds(start_str)
            # The end string could be HMS format or a float from ffprobe
            if ':' in end_str:
                end_sec = hms_to_seconds(end_str)
            else:
                end_sec = float(end_str)

            if start_sec is not None and end_sec is not None:
                if end_sec <= start_sec:
                    print(f"Warning: OUT point '{end_str}' is not after IN point '{start_str}'. Skipping pair.")
                    continue
                f.write(f"{start_sec},{end_sec}\n")
    
    print(f"Successfully processed log file and created '{output_csv_path}'")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python3 process_log.py <input_log_file> <path_to_video> <output_csv_file>")
        sys.exit(1)
    
    input_log = sys.argv[1]
    video_path = sys.argv[2]
    output_csv = sys.argv[3]
    process_log_for_openshot(input_log, video_path, output_csv)
