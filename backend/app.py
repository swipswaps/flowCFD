import os
import shutil
import asyncio
from fastapi import FastAPI, UploadFile, HTTPException, Depends, WebSocket, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional

from . import models, schemas
from .database import SessionLocal, engine
from . import ffmpeg_utils
from .config import settings
from ..create_openshot_project import create_openshot_project
from ..direct_render import render_from_osp

# Create database tables
models.Base.metadata.create_all(bind=engine)

# --- FastAPI App Initialization ---
app = FastAPI()

# CORS Middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","), # Use settings
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Directory Setup ---
# Create necessary directories for storage
UPLOADS_DIR = "store/uploads"
THUMBNAILS_DIR = "store/thumbnails"
PROJECTS_DIR = "store/projects"
EXPORTS_DIR = "store/exports"

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(THUMBNAILS_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

# Serve static files (uploads, thumbnails, exports)
app.mount("/static", StaticFiles(directory="store"), name="static")


# --- Dependency Injection for Database ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Helper Functions ---
def get_static_url(path: str) -> str:
    # This is a simplistic approach. In a real production app, you would
    # use a configurable BASE_URL from settings.
    # For this project, assuming the server runs at localhost:8000 is sufficient.
    return f"http://localhost:8000/static/{path.replace('store/', '', 1)}"

# --- API Endpoints ---

@app.post("/api/videos/upload", response_model=schemas.VideoOut)
async def upload_video(file: UploadFile, db: Session = Depends(get_db)):
    """
    Handles video file uploads, saves the file with a secure name,
    generates thumbnails, and creates a corresponding entry in the database.
    """
    # Secure filename generation
    video_id = models.uid()
    _, file_extension = os.path.splitext(file.filename)
    secure_filename = f"{video_id}{file_extension}"
    file_path = os.path.join(UPLOADS_DIR, secure_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Get video duration
    duration = ffmpeg_utils.ffprobe_duration(file_path)
    if duration is None:
        raise HTTPException(status_code=400, detail="Could not process video file to get duration.")

    # Generate thumbnail and thumbnail strip
    thumb_path = os.path.join(THUMBNAILS_DIR, f"{video_id}.jpg")
    strip_path = os.path.join(THUMBNAILS_DIR, f"{video_id}_strip.jpg")
    
    thumb_success = ffmpeg_utils.generate_thumbnail(file_path, thumb_path)
    strip_success = ffmpeg_utils.generate_thumbnail_strip(file_path, strip_path)

    if not thumb_success or not strip_success:
        # Clean up if thumbnail generation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail="Failed to generate thumbnails.")

    # Create database entry
    db_video = models.Video(
        id=video_id,
        filename=file.filename, # Keep original filename for display purposes
        path=file_path,
        duration=duration,
        thumbnail_url=get_static_url(thumb_path),
        thumbnail_strip_url=get_static_url(strip_path)
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    
    # Add public URL to response
    video_out = schemas.VideoOut.from_orm(db_video)
    video_out.url = get_static_url(db_video.path)
    return video_out

@app.get("/api/videos/{video_id}", response_model=schemas.VideoOut)
def get_video(video_id: str, db: Session = Depends(get_db)):
    db_video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not db_video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video_out = schemas.VideoOut.from_orm(db_video)
    video_out.url = get_static_url(db_video.path)
    return video_out

@app.post("/api/clips/mark", response_model=schemas.ClipOut)
def mark_clip(clip: schemas.ClipIn, db: Session = Depends(get_db)):
    """
    Creates a clip with start and end times for a specific video.
    """
    db_video = db.query(models.Video).filter(models.Video.id == clip.video_id).first()
    if not db_video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    db_clip = models.Clip(**clip.dict())
    db.add(db_clip)
    db.commit()
    db.refresh(db_clip)
    return db_clip

@app.get("/api/videos/{video_id}/exports/latest", response_model=schemas.ExportOut, response_model_exclude_none=True)
def get_latest_active_export(video_id: str, db: Session = Depends(get_db)):
    """
    Gets the latest active (queued or processing) export for a video.
    Returns null if no active export is found.
    """
    latest_export = db.query(models.Export).filter(
        models.Export.video_id == video_id,
        models.Export.status.in_(["queued", "processing"])
    ).order_by(models.Export.created_at.desc()).first()

    if not latest_export:
        return None # FastAPI will correctly return a null body
        
    return latest_export

@app.get("/api/videos/{video_id}/clips", response_model=List[schemas.ClipOut])
def list_clips(video_id: str, db: Session = Depends(get_db)):
    clips = db.query(models.Clip).filter(models.Clip.video_id == video_id).order_by(models.Clip.order_index).all()
    return clips

@app.delete("/api/clips/{clip_id}", status_code=204)
def delete_clip(clip_id: str, db: Session = Depends(get_db)):
    """
    Deletes a clip from the database.
    """
    db_clip = db.query(models.Clip).filter(models.Clip.id == clip_id).first()
    if not db_clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    
    db.delete(db_clip)
    db.commit()
    return

@app.post("/api/clips/reorder/{video_id}", response_model=List[schemas.ClipOut])
def reorder_clips(video_id: str, clip_ids: List[str], db: Session = Depends(get_db)):
    """
    Updates the order_index for all clips of a video based on a new sorted list of IDs.
    """
    db_clips = db.query(models.Clip).filter(models.Clip.video_id == video_id).all()
    
    clip_map = {clip.id: clip for clip in db_clips}

    for index, clip_id in enumerate(clip_ids):
        if clip_id in clip_map:
            clip_map[clip_id].order_index = index
    
    db.commit()
    
    # Return the reordered clips
    reordered_clips = sorted(db_clips, key=lambda c: c.order_index)
    return reordered_clips

@app.post("/api/projects/build")
def build_project(video_id: str, db: Session = Depends(get_db)):
    """
    Generates an OpenShot (.osp) project file from the video's clips.
    """
    db_video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not db_video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    clips = db.query(models.Clip).filter(models.Clip.video_id == video_id).order_by(models.Clip.order_index).all()
    if not clips:
        raise HTTPException(status_code=400, detail="No clips found for this video to build a project.")

    # Create a CSV-like structure in memory for the script
    csv_path = os.path.join(PROJECTS_DIR, f"{video_id}_edits.csv")
    with open(csv_path, 'w') as f:
        for c in clips:
            f.write(f"{c.start_time},{c.end_time}\n")

    osp_path = os.path.join(PROJECTS_DIR, f"{video_id}.osp")
    
    try:
        create_openshot_project(csv_path, db_video.path, osp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create .osp file: {e}")

    return {"message": "Project built successfully", "osp_path": osp_path}

@app.post("/api/exports/start", response_model=schemas.ExportOut)
def start_export(
    export_in: schemas.ExportStartIn, 
    db: Session = Depends(get_db), 
    idempotency_key: Optional[str] = Header(None)
):
    """
    Starts the video export process for a given video.
    This endpoint is idempotent. If the same idempotency_key is used
    for the same video_id, it will return the original export status.
    """
    if idempotency_key:
        # Check if an export with this key already exists
        existing_export = db.query(models.Export).filter(
            models.Export.idempotency_key == idempotency_key,
            models.Export.video_id == export_in.video_id
        ).first()
        if existing_export:
            return existing_export

    db_video = db.query(models.Video).filter(models.Video.id == export_in.video_id).first()
    if not db_video:
        raise HTTPException(status_code=404, detail="Video not found")

    osp_path = os.path.join(PROJECTS_DIR, f"{export_in.video_id}.osp")
    if not os.path.exists(osp_path):
        raise HTTPException(status_code=400, detail="Project file (.osp) not found. Please build the project first.")
        
    output_filename = f"{export_in.video_id}_export.mp4"
    output_path = os.path.join(EXPORTS_DIR, output_filename)

    db_export = models.Export(
        video_id=export_in.video_id,
        idempotency_key=idempotency_key, # Save the key
        osp_path=osp_path,
        output_path=output_path,
        status="queued"
    )
    db.add(db_export)
    db.commit()
    db.refresh(db_export)
    
    # Run the render task in the background
    asyncio.create_task(run_render_task(db_export.id, osp_path, output_path))
    
    return db_export

async def run_render_task(export_id: str, osp_path: str, output_path: str):
    """
    Background task to run the rendering process in a separate thread
    and update the database, preventing the event loop from blocking.
    """
    db = SessionLocal()
    try:
        db_export = db.query(models.Export).filter(models.Export.id == export_id).first()
        if not db_export:
            return

        db_export.status = "processing"
        db.commit()

        # Run the blocking, CPU-bound function in a separate thread
        success = await asyncio.to_thread(render_from_osp, osp_path, output_path)

        if success:
            db_export.status = "completed"
            db_export.progress = 100
            db_export.download_url = get_static_url(output_path)
        else:
            db_export.status = "error"
            db_export.error_message = "Rendering failed. Check server logs for details."
        
        db.commit()
    finally:
        db.close()

@app.get("/api/exports/{export_id}/status", response_model=schemas.ExportStatusOut)
def get_export_status(export_id: str, db: Session = Depends(get_db)):
    db_export = db.query(models.Export).filter(models.Export.id == export_id).first()
    if not db_export:
        raise HTTPException(status_code=404, detail="Export not found")
    return db_export

@app.get("/api/exports/{export_id}/download")
def download_export(export_id: str, db: Session = Depends(get_db)):
    # This endpoint is now largely illustrative, as the static URL is provided directly.
    # It could be used for auth checks in the future.
    db_export = db.query(models.Export).filter(models.Export.id == export_id).first()
    if not db_export or db_export.status != "completed":
        raise HTTPException(status_code=404, detail="Export not found or not completed")
    
    return {"download_url": db_export.download_url}

@app.websocket("/ws/exports/{export_id}")
async def websocket_endpoint(websocket: WebSocket, export_id: str):
    await websocket.accept()
    db = SessionLocal()
    try:
        while True:
            db_export = db.query(models.Export).filter(models.Export.id == export_id).first()
            if not db_export:
                await websocket.close(code=4004, reason="Export not found")
                break
                
            status_data = schemas.ExportStatusOut.from_orm(db_export).dict()
            await websocket.send_json(status_data)

            if db_export.status in ["completed", "error"]:
                break
            
            await asyncio.sleep(2) # Poll every 2 seconds
    except Exception:
        await websocket.close(code=1011)
    finally:
        db.close()
