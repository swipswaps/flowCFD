import sys
import os
from libopenshot import openshot

def render_project(osp_path, output_path):
    """
    Renders an OpenShot project file (.osp) from the command line,
    bypassing the GUI. This is a robust method to export a video
    using CPU-based encoding.
    """
    if not os.path.exists(osp_path):
        print(f"Error: Project file not found at '{osp_path}'")
        return

    try:
        # Create a Timeline object from the .osp file
        timeline = openshot.Timeline(osp_path)
        
        # Set up the exporter
        exporter = openshot.Exporter(timeline)
        
        # --- Configure the export settings ---
        # These settings are for a standard 1080p 29.97fps MP4 file
        exporter.SetVideoOptions(True, "libx264", timeline.Width(), timeline.Height(), timeline.FPS(), 15000000, 2, "mp4")
        exporter.SetAudioOptions(True, "aac", timeline.SampleRate(), timeline.Channels(), timeline.ChannelLayout(), 192000)
        
        # Set the output path for the final video
        exporter.SetOutputPath(output_path)

        print(f"Starting export of '{osp_path}' to '{output_path}'...")
        print("This may take some time. Please be patient.")
        
        # Start the export process
        exporter.Start()

        # Wait for the export to complete, printing progress
        while exporter.GetStatus() == openshot.STATUS_EXPORTING:
            progress = exporter.GetProgress()
            sys.stdout.write(f"\rProgress: {progress:.2f}%")
            sys.stdout.flush()

        print("\nExport finished.")

        if exporter.GetStatus() == openshot.STATUS_COMPLETED:
            print("Video successfully exported.")
        else:
            print("An error occurred during export.")

    except Exception as e:
        print(f"A critical error occurred: {e}")
        print("\nPlease ensure the 'python3-libopenshot' package is installed ('sudo dnf install python3-libopenshot').")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 render.py <path_to_project.osp> <output_video.mp4>")
        sys.exit(1)

    project_file = sys.argv[1]
    output_file = sys.argv[2]
    render_project(project_file, output_file)
