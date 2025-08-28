# flowCFD Video Editor

This project is a modern, web-based video editor inspired by CapCut's simplicity, focusing on rapid clip selection and automated editing workflows. It provides a lightweight, browser-based interface for a professional video editing experience.

## Features

- **Video Upload**: Drag-and-drop or browse to upload source video files (MP4, MOV, AVI).
- **Video Preview**: Precisely preview and mark IN/OUT points for clips.
- **Timeline Management**: Automatically generate a timeline with selected clips.
- **One-Click Export**: Export the final video with real-time progress tracking.
- **Backend API**: A robust FastAPI backend to handle video processing and project management.
- **Real-time Updates**: WebSocket integration for live progress updates on video exports.

## Project Structure

```
.
├── backend/
│   ├── app.py              # FastAPI application, API endpoints
│   ├── database.py         # SQLAlchemy database setup
│   ├── ffmpeg_utils.py     # FFmpeg helper functions
│   ├── models.py           # SQLAlchemy ORM models
│   ├── requirements.txt    # Python dependencies
│   ├── run.sh              # Backend start script
│   └── schemas.py          # Pydantic data schemas
├── create_openshot_project.py # Script to create OpenShot projects
├── direct_render.py        # Direct rendering script using FFmpeg
├── frontend/
│   ├── index.html          # Main HTML entry point
│   ├── package.json        # Node.js dependencies and scripts
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts   # Frontend API client for backend communication
│   │   ├── pages/
│   │   │   └── Editor.tsx  # Main editor page component
│   │   ├── App.tsx         # Root React component
│   │   └── main.tsx        # React application entry point
│   ├── tsconfig.json       # TypeScript configuration
│   └── vite.config.ts      # Vite configuration
├── process_log.py          # Script to process log files for editing
├── README.md               # This file
├── render.py               # Main rendering script
└── simple_render.py        # Simplified rendering script
```

## Getting Started

Follow these instructions to set up and run the project locally.

### Prerequisites

- **Python 3.10+**
- **Node.js 16+** and **npm**
- **FFmpeg**: Must be installed and available in your system's PATH.
- **GitHub CLI (`gh`)**: Required for creating the GitHub repository.

### Installation & Setup

1.  **Clone the repository (if applicable):**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Set up the backend:**

    The backend is powered by FastAPI. The `run.sh` script handles the installation of dependencies and starts the server.

    ```bash
    cd backend
    ./run.sh
    ```
    This will install the necessary Python packages and start the backend server on `http://localhost:8000`.

3.  **Set up the frontend:**

    The frontend is a React application built with Vite.

    ```bash
    cd frontend
    npm install
    npm run dev
    ```
    This will install the required npm packages and start the frontend development server, typically on `http://localhost:5173`.

### How to Use the Application

1.  **Access the application:**
    Open your web browser and navigate to the address provided by the Vite development server (e.g., `http://localhost:5173`).

2.  **Upload a Video:**
    - Click the "Choose File" button to select a video from your local machine.
    - The uploaded video will be displayed with its filename and duration.

3.  **Mark Clips:**
    - The current MVP includes a "Mark Demo Clip" button which marks a 2-second clip from the beginning of the video.
    - In future versions, you will be able to use a video player to mark your desired IN and OUT points.

4.  **Build the Project:**
    - After marking your clips, click the "Build .osp" button. This sends the clip information to the backend, which then generates an OpenShot project file (`.osp`).

5.  **Export the Video:**
    - Click the "Start Export" button to begin the video rendering process.
    - You can monitor the export progress in real-time. The status and progress percentage will be displayed.

6.  **Download the Final Video:**
    - Once the export is complete, a "Download MP4" link will appear. Click it to download your edited video.

## Backend API

The backend exposes a RESTful API for the frontend to interact with. Here are the main endpoints:

- `POST /api/videos/upload`: Upload a video file.
- `POST /api/clips/mark`: Mark a new clip with start and end times.
- `POST /api/projects/build`: Build an OpenShot project from the marked clips.
- `POST /api/exports/start`: Start the export process for a project.
- `GET /api/exports/{export_id}/status`: Get the status of an export.
- `GET /api/exports/{export_id}/download`: Download the final rendered video.
- `WS /ws/exports/{export_id}`: WebSocket endpoint for real-time export progress.
