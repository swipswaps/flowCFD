# flowCFD Video Editor

A modern, web-based video editor inspired by CapCut's simplicity, focusing on rapid clip selection and automated editing workflows. It provides a lightweight, browser-based interface for professional video editing, powered by a Python backend with FFmpeg processing and a React frontend.

## Features

- **🎬 Intuitive Clip Preview System**: Click any timeline clip to instantly preview that specific segment
- **⚡ Fast Video Processing**: Direct FFmpeg integration for efficient clip extraction and concatenation
- **🎯 Streamlined UI**: Clean interface with smart visual feedback and hover tooltips
- **📱 Modern Tech Stack**: FastAPI backend, React frontend with TypeScript, and SQLite database
- **🔄 Real-time Updates**: Live progress feedback and automatic thumbnail generation
- **💾 Persistent State**: Timeline and clip mode states survive page refreshes
- **🚀 One-Click Building**: Build and download complete timeline videos instantly

## How It Works

The application consists of a **FastAPI backend** for video processing and a **React frontend** for the user interface, working together to provide a seamless video editing experience.

### Backend Architecture

The backend handles all video processing, file management, and API operations:

1. **API Server (`app.py`)**: FastAPI application with RESTful endpoints for video upload, clip management, timeline operations, and project building
2. **Database (`database.py`, `models.py`)**: SQLite database with SQLAlchemy ORM for storing videos, clips, and project data
3. **Video Processing (`ffmpeg_utils.py`)**: Direct FFmpeg integration for:
   - Video duration detection and metadata extraction
   - Thumbnail generation with smart positioning
   - Clip-specific thumbnail creation
   - Timeline video building with encoder fallbacks
4. **File Management**: Secure handling of uploads, thumbnails, and exports with proper cleanup

### Frontend Architecture

The frontend provides an intuitive editing interface with modern web technologies:

1. **Main Editor (`Editor.tsx`)**: Central component handling video upload, playback, marking, and timeline management
2. **Video Player (`VideoPlayer.tsx`)**: Custom player with:
   - Clip preview mode with restricted playback boundaries
   - Visual timeline with trim markers and progress indicators
   - Keyboard shortcuts for efficient editing
3. **Timeline (`Timeline.tsx`)**: Interactive timeline with:
   - Click-to-preview functionality for instant clip playback
   - Drag-and-drop reordering capabilities
   - Visual feedback with hover effects and selection states
4. **State Management (`editorStore.ts`)**: Zustand-powered state with persistence for seamless user experience
5. **API Integration (`client.ts`)**: TanStack React Query for efficient data fetching and caching

## Project Structure

```
flowCFD/
├── backend/
│   ├── app.py              # FastAPI application and API endpoints
│   ├── database.py         # SQLite database setup
│   ├── models.py           # SQLAlchemy ORM models
│   ├── schemas.py          # Pydantic request/response schemas
│   ├── ffmpeg_utils.py     # FFmpeg video processing utilities
│   ├── requirements.txt    # Python dependencies
│   └── store/              # File storage directory
│       ├── uploads/        # Uploaded video files
│       ├── thumbnails/     # Generated thumbnails
│       └── exports/        # Built timeline videos
├── frontend/
│   ├── src/
│   │   ├── pages/Editor.tsx       # Main editor interface
│   │   ├── components/
│   │   │   ├── VideoPlayer.tsx    # Video player with clip preview
│   │   │   └── Timeline.tsx       # Interactive timeline component
│   │   ├── stores/editorStore.ts  # Zustand state management
│   │   ├── api/client.ts          # API client with React Query
│   │   └── utils/time.ts          # Time formatting utilities
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 16+** and **npm**
- **FFmpeg**: Must be installed and available in your system PATH

### Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd flowCFD
   ```

2. **Set up the backend:**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up the frontend:**
   ```bash
   cd frontend
   npm install
   ```

### Running the Application

1. **Start the backend server:**
   ```bash
   cd backend
   source .venv/bin/activate
   uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   ```
   The backend API will be available at `http://localhost:8000`

2. **Start the frontend development server:**
   ```bash
   cd frontend
   npm run dev
   ```
   The frontend will be available at `http://localhost:5173`

## User Guide

### 1. Upload Videos
- Click "📁 Upload Video" and select a video file
- The video will be processed and a thumbnail generated automatically
- Multiple videos can be uploaded for multi-source timeline editing

### 2. Mark and Create Clips
- Use the video player to navigate to your desired start time
- Click "📍 Mark IN" to set the beginning of your clip
- Navigate to the end time and click "📍 Mark OUT"
- Click "➕ Add to Timeline" to create the clip
- The clip appears instantly in the timeline below

### 3. Preview Clips
- **Click any clip in the timeline** to enter preview mode
- The video player will show "🎬 Previewing Clip" with clip boundaries
- Playback is restricted to just that clip segment
- Click "📺 Play Full Video" to exit preview mode

### 4. Manage Timeline
- **Reorder clips**: Drag clips to rearrange them
- **Clear timeline**: Use "Clear Timeline" to remove all clips
- **Visual feedback**: Hover over clips to see preview tooltips

### 5. Build Final Video
- Click "🚀 Build Timeline Video" when ready
- The system will extract and concatenate all clips using FFmpeg
- The final video downloads automatically when complete
- Built videos are saved with timestamps (e.g., `timeline_build_20250907_174304.mp4`)

## Key Features Explained

### Clip Preview System
The application's signature feature allows users to click any timeline clip to instantly preview that specific segment. When in preview mode:
- Video playback is restricted to the clip boundaries
- Visual indicators show the active clip timing and duration
- Easy exit with the prominent "Play Full Video" button

### Smart Visual Feedback
- **Timeline Clips**: Hover effects, scaling animations, and selection states
- **Interactive Tooltips**: "🎬 Click to preview this clip" appears on hover
- **Progress Indicators**: Real-time visual feedback during processing
- **Trim Markers**: Visual timeline showing IN/OUT points and current position

### Efficient Video Processing
- **Stream Copy First**: Attempts fast stream copying before re-encoding
- **Encoder Fallbacks**: Gracefully handles different FFmpeg configurations
- **Temporary File Management**: Secure processing with automatic cleanup
- **Clip-Specific Thumbnails**: Each clip gets its own thumbnail from the midpoint

## API Endpoints

### Video Management
- `POST /api/videos/upload` - Upload video files
- `GET /api/videos` - List all uploaded videos
- `GET /api/videos/{video_id}` - Get video details

### Clip Operations  
- `POST /api/clips/mark` - Create a new clip
- `GET /api/timeline/clips` - Get all timeline clips
- `DELETE /api/timeline/clear` - Clear all timeline clips

### Project Building
- `POST /api/projects/build` - Build timeline video from clips
- `GET /api/projects/download/{filename}` - Download built video

### Static Assets
- `GET /static/uploads/{filename}` - Access uploaded video files
- `GET /static/thumbnails/{filename}` - Access generated thumbnails

## Development

### Backend Development
- The backend uses **FastAPI** with automatic API documentation at `/docs`
- **SQLite** database with auto-creation of tables on startup
- **Background tasks** for thumbnail generation
- **File validation** and secure upload handling

### Frontend Development
- **React 18** with **TypeScript** for type safety
- **Vite** for fast development and hot module replacement
- **TanStack React Query** for server state management
- **Zustand** for client state with persistence middleware
- **React Hot Toast** for user notifications

### Testing the Application
The application includes comprehensive testing workflows that verify:
- Video upload and processing
- Clip creation and timeline management
- Video building and download functionality
- UI responsiveness and error handling

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly using the built-in workflows
5. Submit a pull request

## License

This project is designed for educational and development purposes, showcasing modern web-based video editing techniques with FFmpeg integration.