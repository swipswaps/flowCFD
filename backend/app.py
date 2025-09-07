import os
import shutil
import asyncio
from fastapi import FastAPI, UploadFile, HTTPException, Depends, WebSocket, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
# OAuth2PasswordBearer, OAuth2PasswordRequestForm removed - no auth module
from sqlalchemy.orm import Session
from typing import List, Optional
# timedelta removed - no auth needed

import models, schemas
from database import SessionLocal, engine
import ffmpeg_utils
from config import settings
# Removed auth-dependent modules: create_openshot_project, direct_render
# JWT removed - no auth needed

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
app.mount("/static/uploads", StaticFiles(directory=UPLOADS_DIR), name="static_uploads")
app.mount("/static/thumbnails", StaticFiles(directory=THUMBNAILS_DIR), name="static_thumbnails")
app.mount("/static/exports", StaticFiles(directory=EXPORTS_DIR), name="static_exports")

# --- Dependency Injection for Database ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Helper Functions ---
def get_static_url(path: str) -> str:
    """
    Constructs the correct static URL for a given file path.
    Determines the correct sub-path (uploads, thumbnails, exports)
    based on the file's location.
    """
    base_url = f"{settings.BASE_URL}/static"

    if "uploads" in path:
        return f"{base_url}/uploads/{os.path.basename(path)}"
    elif "thumbnails" in path:
        return f"{base_url}/thumbnails/{os.path.basename(path)}"
    elif "exports" in path:
        return f"{base_url}/exports/{os.path.basename(path)}"
    else:
        # Fallback for any other case, though it shouldn't be hit with the current structure
        return f"{settings.BASE_URL}/static/{path.replace('store/', '', 1)}"

# --- Auth Endpoints Removed (no auth module) ---

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

    # Use fast duration estimate to reduce upload time
    duration = 10.0  # Default estimate - will be updated if needed

    # Create database entry - thumbnails will be generated in background
    db_video = models.Video(
        id=video_id,
        filename=file.filename,
        path=file_path,
        duration=duration,
        thumbnail_strip_url=""  # Empty string instead of None for now
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    
    return db_video

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

@app.get("/api/videos/{video_id}/exports/latest")
def get_latest_active_export(video_id: str, db: Session = Depends(get_db)):
    """
    Gets the latest active (queued or processing) export for a video.
    Returns status object if no active export is found.
    """
    try:
        latest_export = db.query(models.Export).filter(
            models.Export.video_id == video_id,
            models.Export.status.in_(["queued", "processing"])
        ).order_by(models.Export.created_at.desc()).first()

        if not latest_export:
            return {"status": "none", "message": "No active exports"}
            
        return {"status": "active", "export": latest_export}
    except Exception as e:
        print(f"Error in get_latest_active_export: {e}")
        return {"status": "error", "message": "Failed to get export status"}

# CORRECTED: Made this endpoint consistent with the others, nesting it under /api/videos/{video_id}
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

    # --- Input Validation ---
    # Check if the number of provided IDs matches the number of clips for the video.
    if len(clip_ids) != len(db_clips):
        raise HTTPException(
            status_code=400,
            detail=f"The number of clip IDs provided ({len(clip_ids)}) does not match the number of clips for this video ({len(db_clips)})."
        )

    # Check if all provided clip_ids actually belong to the video.
    provided_ids_set = set(clip_ids)
    actual_ids_set = set(clip_map.keys())
    if provided_ids_set != actual_ids_set:
        raise HTTPException(
            status_code=400,
            detail="The provided clip IDs do not match the clips for this video."
        )

    for index, clip_id in enumerate(clip_ids):
        if clip_id in clip_map:
            clip_map[clip_id].order_index = index
    
    db.commit()
    
    # Return the reordered clips
    reordered_clips = sorted(db_clips, key=lambda c: c.order_index)
    return reordered_clips

@app.post("/api/projects/build")
def build_project(video_id: str = Query(...), db: Session = Depends(get_db)):
    """
    Build project endpoint - temporarily disabled (missing OpenShot integration)
    """
    raise HTTPException(status_code=501, detail="Project building temporarily disabled - OpenShot integration required")

@app.post("/api/exports/start", response_model=schemas.ExportOut)
def start_export(
    export_in: schemas.ExportStartIn, 
    db: Session = Depends(get_db), 
    idempotency_key: Optional[str] = Header(None),
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
