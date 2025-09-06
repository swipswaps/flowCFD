# flowCFD Video Editor

This project is a modern, web-based video editor inspired by CapCut's simplicity, focusing on rapid clip selection and automated editing workflows. It provides a lightweight, browser-based interface for a professional video editing experience, powered by a Python backend and a React frontend.

## How It Works

The application is composed of two main parts: a frontend web interface and a backend processing engine.

### Backend Architecture

The backend is a **FastAPI** application that handles all heavy lifting. Its primary responsibilities are managing project data, processing video files, and communicating progress back to the user.

1.  **API Server (`app.py`):** Exposes a RESTful API for all frontend operations. This includes endpoints for uploading videos, defining clips, building projects, and starting exports. It also hosts a WebSocket endpoint for real-time progress updates during video rendering.
2.  **Database (`database.py`, `models.py`):** Uses **SQLAlchemy** to manage a database (defaulting to SQLite) that stores information about uploaded videos, their associated clips, and export jobs.
3.  **Video Processing (`ffmpeg_utils.py`):** A utility module that wraps the powerful **FFmpeg** command-line tool to perform core tasks like getting video duration, generating thumbnails, and creating thumbnail strips for the UI.
4.  **Project Generation (`create_openshot_project.py`):** When a user wants to combine their clips, the backend uses this script to dynamically generate an **OpenShot** project file (`.osp`). This file is a JSON representation of the timeline, referencing the source video and the user-defined IN/OUT points for each clip.
5.  **Video Rendering (`direct_render.py`):** To export the final video, the backend uses this script. It reads the `.osp` file, uses FFmpeg to extract each individual clip into a temporary file, and then uses FFmpeg's concat feature to stitch them together into the final MP4. This method is robust and avoids needing the full OpenShot library for rendering.

### Frontend Architecture

The frontend is a modern **React** single-page application built with **Vite**. It is designed to be responsive and provide a smooth user experience.

1.  **Main View (`Editor.tsx`):** This is the central component where the user interacts with the application. It contains the logic for file uploads, video playback, and communicating with the backend API.
2.  **State Management (`stores/editorStore.ts`):** The application uses **Zustand**, a lightweight state management library, to handle global UI state. This includes tracking the active video, the user's current IN/OUT marks, and player status (like play/pause).
3.  **Server Communication (`api/client.ts`):** All communication with the backend is managed through a dedicated API client, which uses **TanStack React Query** to handle data fetching, caching, and mutations. This makes the UI more resilient and responsive.
4.  **Components (`components/`):**
    *   `VideoPlayer.tsx`: A reusable component that wraps `react-player` to provide video playback, seeking, and marking functionality.
    *   `Timeline.tsx`: Displays the clips that the user has added to the project.

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
│   ├── ... (React project files)
│   └── src/
│       ├── api/client.ts   # Frontend API client
│       ├── pages/Editor.tsx  # Main editor page component
│       └── stores/editorStore.ts # Zustand global state
└── ...
```

## Getting Started

Follow these instructions to set up and run the project locally.

### Prerequisites

- **Python 3.10+**
- **Node.js 16+** and **npm**
- **FFmpeg**: Must be installed and available in your system's PATH.

### Installation & Setup

1.  **Set up the backend:**

    The backend is powered by FastAPI. The `run.sh` script handles the installation of dependencies and starts the server.

    ```bash
    cd backend
    ./run.sh
    ```
    This will install the necessary Python packages in a local virtual environment (`.venv`) and start the backend server on `http://localhost:8000`.

2.  **Set up the frontend:**

    The frontend is a React application built with Vite. Open a **new terminal** for this step.

    ```bash
    cd frontend
    npm install
    npm run dev
    ```
    This will install the required npm packages and start the frontend development server, typically on `http://localhost:5173`.

## Step-by-Step User Guide

1.  **Access the Application:**
    Open your web browser and navigate to the address provided by the Vite development server (e.g., `http://localhost:5173`).

2.  **Upload a Video:**
    *   In the "1) Upload Video" section, click the "Choose File" button to select a video from your local machine.
    *   Once uploaded, you will see a thumbnail, the filename, and the video's total duration.

3.  **Mark Clips:**
    *   The video will load in the "2) Video Player & Clip Marking" section.
    *   Use the player controls to play and pause the video. You can click on the progress bar to seek to a specific time.
    *   **To mark an IN point:** Navigate to your desired start time and click the "Mark IN" button.
    *   **To mark an OUT point:** Navigate to your desired end time and click the "Mark OUT" button.
    *   Once both an IN and an OUT point are set, click the **"Add Clip to Timeline"** button. The clip will appear in the Timeline section below the player.
    *   Repeat this process to add as many clips as you need.

4.  **Build the Project:**
    *   After adding all your clips to the timeline, go to the "3) Build Project & Export" section.
    *   Click the **"Build .osp Project"** button. This tells the backend to generate an OpenShot project file from your clip list. This step is required before exporting.

5.  **Export the Video:**
    *   Once the project is built, click the **"Start Export"** button.
    *   The export process will begin on the server. You can monitor its progress in real-time via the status bar that appears. It will show the percentage complete and an estimated time remaining (ETA).

6.  **Download the Final Video:**
    *   When the export status reaches "completed" and the progress bar is at 100%, a **"Download Final MP4"** link will appear.
    *   Click this link to download your finished, edited video.

## Backend API

The backend exposes a RESTful API for the frontend to interact with. Here are the main endpoints:

- `POST /api/videos/upload`: Upload a video file.
- `POST /api/clips/mark`: Mark a new clip with start and end times.
- `POST /api/projects/build`: Build an OpenShot project from the marked clips.
- `POST /api/exports/start`: Start the export process for a project.
- `GET /api/exports/{export_id}/status`: Get the status of an export.
- `GET /api/exports/{export_id}/download`: Download the final rendered video.
- `WS /ws/exports/{export_id}`: WebSocket endpoint for real-time export progress.
