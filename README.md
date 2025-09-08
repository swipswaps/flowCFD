# flowCFD Video Editor

A professional-grade, web-based video editor with advanced lossless editing capabilities, focusing on rapid clip selection, keyframe-aware cutting, and quality-preserving workflows. It provides a browser-based interface for professional video editing with industry-standard quality metrics, powered by a Python backend with FFmpeg processing and a React frontend.

## Features

### 🎯 **Professional Lossless Editing**
- **🔬 Keyframe Detection**: Automatic keyframe analysis for optimal cutting points
- **⚡ Smart Cutting**: Frame-accurate cuts with minimal quality loss
- **🎯 Lossless Extract**: True lossless cutting when keyframe-aligned
- **📊 Quality Metrics**: SSIM, PSNR, VMAF analysis for professional quality assessment
- **🌟 Advanced Concatenation**: Multi-strategy timeline building with quality preservation

### 🎬 **Intuitive Video Editing**
- **📺 Clip Preview System**: Click any timeline clip to instantly preview that specific segment
- **⚡ Fast Video Processing**: Direct FFmpeg integration with encoder fallbacks
- **🎯 Streamlined UI**: Clean interface with real-time quality indicators
- **📱 Modern Tech Stack**: FastAPI backend, React frontend with TypeScript, and SQLite database
- **🔄 Real-time Updates**: Live progress feedback and automatic thumbnail generation
- **💾 Persistent State**: Timeline and clip mode states survive page refreshes
- **🚀 Professional Building**: Multiple build options from standard to lossless quality

## How It Works

The application consists of a **FastAPI backend** for video processing and a **React frontend** for the user interface, working together to provide a seamless video editing experience.

### Backend Architecture

The backend handles all video processing, file management, and API operations:

1. **API Server (`app.py`)**: FastAPI application with RESTful endpoints for video upload, clip management, timeline operations, and project building
2. **Database (`database.py`, `models.py`)**: SQLite database with SQLAlchemy ORM for storing videos, clips, and project data
3. **Video Processing (`ffmpeg_utils.py`)**: Advanced FFmpeg integration for:
   - Keyframe detection and analysis for lossless cutting
   - Video duration detection and metadata extraction
   - Thumbnail generation with smart positioning
   - Clip-specific thumbnail creation
   - Lossless clip extraction with quality preservation
   - Smart cutting for non-keyframe-aligned edits
   - Quality metrics calculation (SSIM, PSNR, VMAF)
   - Advanced concatenation with multiple strategies
   - Timeline video building with encoder fallbacks
4. **File Management**: Secure handling of uploads, thumbnails, and exports with proper cleanup

### Frontend Architecture

The frontend provides an intuitive editing interface with modern web technologies:

1. **Main Editor (`Editor.tsx`)**: Central component handling video upload, playback, marking, timeline management, and professional lossless tools
2. **Video Player (`VideoPlayer.tsx`)**: Custom player with:
   - Clip preview mode with restricted playback boundaries
   - Visual timeline with trim markers and progress indicators
   - Keyboard shortcuts for efficient editing
3. **Timeline (`Timeline.tsx`)**: Interactive timeline with:
   - Click-to-preview functionality for instant clip playback
   - Drag-and-drop reordering capabilities
   - Visual feedback with hover effects and selection states
4. **Professional Components**:
   - **Keyframe Timeline (`KeyframeTimeline.tsx`)**: Visual keyframe indicators with snap-to functionality
   - **Lossless Indicator (`LosslessIndicator.tsx`)**: Real-time quality status feedback
5. **State Management (`editorStore.ts`)**: Zustand-powered state with persistence for seamless user experience
6. **API Integration (`client.ts`)**: TanStack React Query with advanced lossless editing endpoints

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
│   │   ├── pages/Editor.tsx       # Main editor interface with lossless tools
│   │   ├── components/
│   │   │   ├── VideoPlayer.tsx    # Video player with clip preview
│   │   │   ├── Timeline.tsx       # Interactive timeline component
│   │   │   ├── KeyframeTimeline.tsx  # Professional keyframe visualization
│   │   │   └── LosslessIndicator.tsx # Real-time quality feedback
│   │   ├── stores/editorStore.ts  # Zustand state management with persistence
│   │   ├── api/client.ts          # API client with lossless editing endpoints
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

### 5. Advanced Extraction Tools
- **🎯 Lossless Extract**: True lossless cutting when clips are keyframe-aligned (green indicator)
- **✂️ Smart Cut**: Frame-accurate cutting with minimal quality loss (orange indicator)
- Quality indicators show real-time assessment of cutting precision

### 6. Professional Timeline Building
- **🚀 Build Timeline**: Standard concatenation (compatible but may lose quality)
- **🌟 Lossless Build**: Professional-grade concatenation with quality preservation
- Processing method and timing displayed in real-time
- Built videos auto-download with descriptive filenames

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
- `GET /api/videos/{video_id}/keyframes` - Get keyframe timestamps for lossless cutting

### Professional Clip Operations  
- `POST /api/clips/mark` - Create a new clip
- `POST /api/clips/extract` - Professional lossless clip extraction
- `POST /api/clips/smart-cut` - Frame-accurate smart cutting
- `GET /api/timeline/clips` - Get all timeline clips
- `DELETE /api/timeline/clear` - Clear all timeline clips

### Professional Quality & Building
- `POST /api/quality/analyze` - Analyze quality metrics (SSIM, PSNR, VMAF)
- `POST /api/quality/report` - Generate comprehensive quality reports
- `GET /api/quality/test` - Test FFmpeg filter availability
- `POST /api/timeline/build-lossless` - Professional lossless timeline concatenation
- `POST /api/concatenation/validate` - Validate clip compatibility for lossless concat
- `POST /api/projects/build` - Standard timeline video building

### Static Assets
- `GET /static/uploads/{filename}` - Access uploaded video files
- `GET /static/thumbnails/{filename}` - Access generated thumbnails
- `GET /static/exports/{filename}` - Access built timeline videos

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