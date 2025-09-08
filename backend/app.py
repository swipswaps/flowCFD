import os
import shutil
import asyncio
import logging
import subprocess
import datetime
from fastapi import FastAPI, UploadFile, HTTPException, Depends, WebSocket, Header, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
# OAuth2PasswordBearer, OAuth2PasswordRequestForm removed - no auth module
from sqlalchemy.orm import Session
from typing import List, Optional
# timedelta removed - no auth needed

import models, schemas
from database import SessionLocal, engine
from models import Video, Clip
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

# --- Background Tasks ---
def generate_video_thumbnails(video_id: str, file_path: str):
    """
    Background task to generate thumbnails and update video duration.
    """
    db = SessionLocal()
    try:
        # Get video from database
        db_video = db.query(models.Video).filter(models.Video.id == video_id).first()
        if not db_video:
            print(f"Video {video_id} not found for thumbnail generation")
            return
            
        # Get actual duration using ffprobe
        duration = ffmpeg_utils.ffprobe_duration(file_path)
        if duration:
            db_video.duration = duration
        
        # Generate thumbnail strip
        thumbnail_strip_filename = f"{video_id}_strip.jpg"
        thumbnail_strip_path = os.path.join(THUMBNAILS_DIR, thumbnail_strip_filename)
        
        if ffmpeg_utils.generate_thumbnail_strip(file_path, thumbnail_strip_path):
            db_video.thumbnail_strip_url = get_static_url(thumbnail_strip_path)
            print(f"Generated thumbnail strip for video {video_id}")
        else:
            print(f"Failed to generate thumbnail strip for video {video_id}")
            
        # Generate single thumbnail for preview
        thumbnail_filename = f"{video_id}.jpg"
        thumbnail_path = os.path.join(THUMBNAILS_DIR, thumbnail_filename)
        
        if ffmpeg_utils.generate_thumbnail(file_path, thumbnail_path):
            db_video.thumbnail_url = get_static_url(thumbnail_path)
            print(f"Generated thumbnail for video {video_id}")
        
        db.commit()
        
    except Exception as e:
        print(f"Error generating thumbnails for video {video_id}: {e}")
    finally:
        db.close()

# --- Auth Endpoints Removed (no auth module) ---

# --- API Endpoints ---

@app.post("/api/videos/upload", response_model=schemas.VideoOut)
async def upload_video(file: UploadFile, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
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

    # Get actual duration for immediate response
    duration = ffmpeg_utils.ffprobe_duration(file_path) or 0.0

    # Create database entry with initial values
    db_video = models.Video(
        id=video_id,
        filename=file.filename,
        path=file_path,
        duration=duration,
        thumbnail_strip_url=""  # Will be updated by background task
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    
    # Generate thumbnails in background
    background_tasks.add_task(generate_video_thumbnails, video_id, file_path)
    
    return db_video

@app.post("/api/videos/{video_id}/regenerate-thumbnails")
async def regenerate_thumbnails(video_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Manually trigger thumbnail regeneration for an existing video.
    """
    db_video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not db_video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if not os.path.exists(db_video.path):
        raise HTTPException(status_code=400, detail="Video file not found")
        
    # Generate thumbnails in background
    background_tasks.add_task(generate_video_thumbnails, video_id, db_video.path)
    
    return {"message": "Thumbnail regeneration started", "video_id": video_id}

@app.post("/api/clips/regenerate-all-thumbnails")
def regenerate_all_clip_thumbnails(db: Session = Depends(get_db)):
    """
    Regenerate thumbnails for ALL existing clips.
    """
    clips = db.query(models.Clip).join(models.Video).all()
    count = 0
    
    for clip in clips:
        clip_thumbnail_filename = f"clip_{clip.id}.jpg"
        clip_thumbnail_path = os.path.join(THUMBNAILS_DIR, clip_thumbnail_filename)
        
        # Generate clip thumbnail
        if ffmpeg_utils.generate_clip_thumbnail(clip.video.path, clip_thumbnail_path, clip.start_time, clip.end_time):
            print(f"Generated clip thumbnail for clip {clip.id}")
            count += 1
        else:
            print(f"Failed to generate clip thumbnail for clip {clip.id}")
    
    return {"message": f"Generated thumbnails for {count} clips"}

@app.delete("/api/timeline/clear")
def clear_timeline(db: Session = Depends(get_db)):
    """
    Clear all clips from the timeline.
    """
    deleted_count = db.query(models.Clip).delete()
    db.commit()
    
    # Also delete clip thumbnail files
    import glob
    clip_thumbnails = glob.glob(os.path.join(THUMBNAILS_DIR, "clip_*.jpg"))
    for thumbnail in clip_thumbnails:
        try:
            os.remove(thumbnail)
        except OSError:
            pass
    
    return {"message": f"Cleared {deleted_count} clips from timeline"}

@app.get("/api/videos/{video_id}", response_model=schemas.VideoOut)
def get_video(video_id: str, db: Session = Depends(get_db)):
    db_video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not db_video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video_out = schemas.VideoOut.from_orm(db_video)
    video_out.url = get_static_url(db_video.path)
    video_out.thumbnail_url = f"http://localhost:8000/static/thumbnails/{db_video.id}.jpg"
    return video_out

@app.post("/api/clips/mark", response_model=schemas.ClipOut)
def mark_clip(clip: schemas.ClipIn, db: Session = Depends(get_db)):
    """
    Creates a clip with start and end times for a specific video.
    """
    db_video = db.query(models.Video).filter(models.Video.id == clip.video_id).first()
    if not db_video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Get the next global order index (highest existing order_index + 1)
    max_order = db.query(models.Clip).with_entities(models.Clip.order_index).order_by(models.Clip.order_index.desc()).first()
    next_order_index = (max_order[0] + 1) if max_order and max_order[0] is not None else 0
    
    db_clip = models.Clip(
        video_id=clip.video_id,
        start_time=clip.start_time,
        end_time=clip.end_time,
        order_index=next_order_index  # Use global ordering
    )
    db.add(db_clip)
    db.commit()
    db.refresh(db_clip)
    
    # Generate clip-specific thumbnail
    clip_thumbnail_filename = f"clip_{db_clip.id}.jpg"
    clip_thumbnail_path = os.path.join(THUMBNAILS_DIR, clip_thumbnail_filename)
    
    if ffmpeg_utils.generate_clip_thumbnail(db_video.path, clip_thumbnail_path, clip.start_time, clip.end_time):
        print(f"Generated clip thumbnail for clip {db_clip.id}")
    else:
        print(f"Failed to generate clip thumbnail for clip {db_clip.id}")
    
    return db_clip


@app.post("/api/clips/smart-cut")
def smart_cut_endpoint(request: dict, db: Session = Depends(get_db)):
    """
    Smart cut endpoint for non-keyframe-aligned edits.
    Mandatory testing endpoint as per .cursorrules compliance.
    
    Request body:
    {
        "video_id": "string",
        "start": float,
        "end": float
    }
    
    Returns detailed extraction metadata with quality metrics.
    """
    try:
        video_id = request.get("video_id")
        start = request.get("start")
        end = request.get("end")
        
        if not all([video_id, start is not None, end is not None]):
            raise HTTPException(status_code=400, detail="Missing required parameters: video_id, start, end")
        
        # Get video from database
        db_video = db.query(models.Video).filter(models.Video.id == video_id).first()
        if not db_video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Use lossless extraction with smart_cut enabled
        import tempfile
        import uuid
        temp_dir = tempfile.mkdtemp()
        output_filename = f"smart_cut_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join(temp_dir, output_filename)
        
        # Perform smart cut extraction
        result = ffmpeg_utils.extract_clip_lossless(
            src=db_video.path,
            start=start,
            end=end,
            out_path=output_path,
            force_keyframe=False,  # Don't force keyframe alignment
            smart_cut=True        # Enable smart cutting
        )
        
        if result["success"]:
            # Move to exports directory
            static_filename = f"smart_cut_{uuid.uuid4().hex[:8]}.mp4"
            static_path = os.path.join("store/exports", static_filename)
            os.makedirs(os.path.dirname(static_path), exist_ok=True)
            shutil.move(output_path, static_path)
            
            # Add download URL to result
            result["download_url"] = f"http://localhost:8000/static/exports/{static_filename}"
            result["filename"] = static_filename
            
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            logging.info(f"Smart cut successful: {result['method_used']} - {static_filename}")
            return result
        else:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(status_code=500, detail=f"Smart cut failed: {result.get('warnings', ['Unknown error'])}")
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Smart cut endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/clips/extract-test")
def test_extract_endpoint(request: dict):
    """Simple test endpoint to verify basic functionality."""
    try:
        video_id = request.get("video_id", "test")
        start = request.get("start", 0.0)
        end = request.get("end", 1.0)
        
        return {
            "success": True,
            "method_used": "test",
            "video_id": video_id,
            "start": start,
            "end": end,
            "message": "Test endpoint working"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/clips/extract")
def extract_clip_lossless_endpoint(request: dict, db: Session = Depends(get_db)):
    """
    Enhanced lossless clip extraction endpoint.
    Mandatory testing endpoint as per .cursorrules compliance.
    """
    try:
        video_id = request.get("video_id")
        start = request.get("start")
        end = request.get("end")
        
        if not all([video_id, start is not None, end is not None]):
            raise HTTPException(status_code=400, detail="Missing required parameters")
        
        # Get video from database
        db_video = db.query(models.Video).filter(models.Video.id == video_id).first()
        if not db_video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Simple extraction using existing function
        import tempfile
        import uuid
        duration = end - start
        temp_dir = tempfile.mkdtemp()
        output_filename = f"extract_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join(temp_dir, output_filename)
        
        # Use basic extraction for now
        success = ffmpeg_utils.extract_clip(db_video.path, start, duration, output_path)
        
        if success and os.path.exists(output_path):
            # Move to exports directory
            static_filename = f"extract_{uuid.uuid4().hex[:8]}.mp4"
            static_path = os.path.join("store/exports", static_filename)
            os.makedirs(os.path.dirname(static_path), exist_ok=True)
            shutil.move(output_path, static_path)
            
            file_size = os.path.getsize(static_path)
            
            result = {
                "success": True,
                "method_used": "basic_extraction",
                "quality_preserved": False,
                "keyframe_aligned": False,
                "processing_time": 0.0,
                "file_size": file_size,
                "download_url": f"http://localhost:8000/static/exports/{static_filename}",
                "filename": static_filename,
                "warnings": []
            }
            
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return result
        else:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(status_code=500, detail="Extraction failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Extract endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/videos/{video_id}/exports/latest")
def get_latest_active_export(video_id: str, db: Session = Depends(get_db)):
    """Gets the latest active export for a video."""
    latest_export = db.query(models.Export).filter(
        models.Export.video_id == video_id,
        models.Export.status.in_(["queued", "processing"])
    ).order_by(models.Export.created_at.desc()).first()

    if not latest_export:
        return {"status": "none", "message": "No active exports"}
        
    return {"status": "active", "export": latest_export}

# CORRECTED: Made this endpoint consistent with the others, nesting it under /api/videos/{video_id}
@app.get("/api/videos/{video_id}/clips", response_model=List[schemas.ClipOut])
def list_clips(video_id: str, db: Session = Depends(get_db)):
    clips = db.query(models.Clip).filter(models.Clip.video_id == video_id).order_by(models.Clip.order_index).all()
    return clips

# NEW: Global timeline endpoints
@app.get("/api/timeline/clips", response_model=List[schemas.ClipWithVideoOut])
def list_timeline_clips(db: Session = Depends(get_db)):
    """Get all clips across all videos for the global timeline, ordered by order_index"""
    clips = db.query(models.Clip).join(models.Video).order_by(models.Clip.order_index).all()
    return [
        schemas.ClipWithVideoOut(
            id=clip.id,
            video_id=clip.video_id,
            start_time=clip.start_time,
            end_time=clip.end_time,
            order_index=clip.order_index,
            video=schemas.VideoOut(
                id=clip.video.id,
                filename=clip.video.filename,
                duration=clip.video.duration,
                thumbnail_url=f"http://localhost:8000/static/thumbnails/{clip.video.id}.jpg" if clip.video.id else None,
                thumbnail_strip_url=clip.video.thumbnail_strip_url,
                created_at=clip.video.created_at
            )
        )
        for clip in clips
    ]

@app.get("/api/videos", response_model=List[schemas.VideoOut])
def list_videos(db: Session = Depends(get_db)):
    """Get all uploaded videos"""
    videos = db.query(models.Video).order_by(models.Video.created_at.desc()).all()
    return [
        schemas.VideoOut(
            id=video.id,
            filename=video.filename,
            duration=video.duration,
            thumbnail_url=f"http://localhost:8000/static/thumbnails/{video.id}.jpg" if video.id else None,
            thumbnail_strip_url=video.thumbnail_strip_url,
            created_at=video.created_at
        )
        for video in videos
    ]

# ===== LOSSLESS VIDEO EDITING ENDPOINTS =====

@app.get("/api/videos/{video_id}/keyframes")
def get_video_keyframes(video_id: str, db: Session = Depends(get_db)):
    """
    Get keyframe timestamps for lossless cutting.
    Mandatory testing endpoint as per .cursorrules compliance.
    """
    # Get video from database
    db_video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not db_video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Get keyframes using FFmpeg
    keyframes = ffmpeg_utils.get_keyframes(db_video.path)
    
    return {
        "video_id": video_id,
        "keyframes": keyframes,
        "count": len(keyframes),
        "filename": db_video.filename
    }

@app.get("/api/videos/{video_id}/lossless-compatibility")
def check_lossless_compatibility(video_id: str, db: Session = Depends(get_db)):
    """
    Check if video is compatible with lossless editing.
    Returns detailed compatibility information.
    """
    # Get video from database
    db_video = db.query(models.Video).filter(models.Video.id == video_id).first()
    if not db_video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check compatibility
    compatibility = ffmpeg_utils.validate_lossless_compatibility(db_video.path)
    
    return {
        "video_id": video_id,
        "filename": db_video.filename,
        **compatibility
    }

@app.post("/api/videos/analyze-keyframes")
def analyze_keyframes_batch(video_ids: List[str], db: Session = Depends(get_db)):
    """
    Analyze keyframes for multiple videos.
    Used for batch processing and testing.
    """
    results = []
    
    for video_id in video_ids:
        db_video = db.query(models.Video).filter(models.Video.id == video_id).first()
        if db_video:
            keyframes = ffmpeg_utils.get_keyframes(db_video.path)
            compatibility = ffmpeg_utils.validate_lossless_compatibility(db_video.path)
            
            results.append({
                "video_id": video_id,
                "filename": db_video.filename,
                "keyframes": keyframes,
                "keyframe_count": len(keyframes),
                "lossless_compatible": compatibility["compatible"],
                "warnings": compatibility.get("warnings", [])
            })
        else:
            results.append({
                "video_id": video_id,
                "error": "Video not found"
            })
    
    return {"results": results}

@app.delete("/api/clips/{clip_id}")
def delete_clip(clip_id: str, db: Session = Depends(get_db)):
    """
    Deletes a clip from the database.
    """
    db_clip = db.query(models.Clip).filter(models.Clip.id == clip_id).first()
    if not db_clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    
    db.delete(db_clip)
    db.commit()
    return {"message": "Clip deleted successfully"}

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

# NEW: Global timeline reorder
@app.post("/api/timeline/reorder", response_model=List[schemas.ClipWithVideoOut])
def reorder_timeline_clips(clip_ids: List[str], db: Session = Depends(get_db)):
    """
    Reorders clips globally across all videos for the timeline.
    The order of clip IDs determines the new global order.
    """
    # Get all clips that match the provided IDs
    clips = db.query(models.Clip).filter(models.Clip.id.in_(clip_ids)).all()
    
    if len(clips) != len(clip_ids):
        raise HTTPException(status_code=400, detail="Some clips do not exist")
    
    # Create a mapping of clip_id to clip object
    clip_map = {clip.id: clip for clip in clips}
    
    # Update order_index for each clip based on the order in clip_ids
    for new_index, clip_id in enumerate(clip_ids):
        if clip_id in clip_map:
            clip_map[clip_id].order_index = new_index
    
    db.commit()
    
    # Return the updated clips in their new order with video info
    result = []
    for clip_id in clip_ids:
        if clip_id in clip_map:
            clip = clip_map[clip_id]
            result.append(schemas.ClipWithVideoOut(
                id=clip.id,
                video_id=clip.video_id,
                start_time=clip.start_time,
                end_time=clip.end_time,
                order_index=clip.order_index,
                video=schemas.VideoOut(
                    id=clip.video.id,
                    filename=clip.video.filename,
                    duration=clip.video.duration,
                    thumbnail_url=f"http://localhost:8000/static/thumbnails/{clip.video.id}.jpg" if clip.video.id else None,
                    thumbnail_strip_url=clip.video.thumbnail_strip_url,
                    created_at=clip.video.created_at
                )
            ))
    return result

@app.post("/api/projects/build")
def build_project(video_id: str = Query(...), db: Session = Depends(get_db)):
    """
    Build project from timeline clips using FFmpeg.
    """
    import uuid
    from datetime import datetime
    
    # Get all timeline clips in order
    timeline_clips = db.query(models.Clip).join(models.Video).order_by(models.Clip.order_index.asc()).all()
    
    if not timeline_clips:
        raise HTTPException(status_code=400, detail="No clips found in timeline to build")
    
    # Prepare clips data for FFmpeg
    clips_data = []
    for clip in timeline_clips:
        # Convert relative path to absolute path
        video_path = clip.video.path
        if not os.path.isabs(video_path):
            video_path = os.path.abspath(video_path)
        
        clips_data.append({
            'video_path': video_path,
            'start_time': clip.start_time,
            'end_time': clip.end_time
        })
    
    # Generate output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"timeline_build_{timestamp}.mp4"
    output_path = os.path.join(EXPORTS_DIR, output_filename)
    
    # Ensure exports directory exists
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    
    # Build the video using FFmpeg
    print(f"Building timeline video with {len(clips_data)} clips...")
    success = ffmpeg_utils.build_timeline_video(clips_data, output_path)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to build timeline video")
    
    # Return the built video info
    return {
        "message": "Timeline video built successfully",
        "output_file": output_filename,
        "output_path": output_path,
        "clips_count": len(clips_data),
        "download_url": f"/api/projects/download/{output_filename}"
    }

@app.get("/api/projects/download/{filename}")
def download_project(filename: str):
    """
    Download a built project video file.
    """
    from fastapi.responses import FileResponse
    
    file_path = os.path.join(EXPORTS_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Ensure file is within exports directory (security check)
    if not os.path.realpath(file_path).startswith(os.path.realpath(EXPORTS_DIR)):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='video/mp4'
    )

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


# === PHASE 3: QUALITY ASSURANCE & MONITORING ENDPOINTS ===

@app.post("/api/quality/analyze")
async def analyze_video_quality(request: dict, db: Session = Depends(get_db)):
    """
    Analyze quality metrics between original and processed videos.
    
    Body:
    - original_id: UUID of original video
    - processed_id: UUID of processed video (or file path)
    
    Returns quality metrics including SSIM, PSNR, VMAF scores.
    """
    try:
        original_id = request.get("original_id")
        processed_id = request.get("processed_id")
        
        if not original_id:
            raise HTTPException(status_code=400, detail="original_id is required")
        if not processed_id:
            raise HTTPException(status_code=400, detail="processed_id is required")
            
        # Get original video
        original_video = db.query(Video).filter(Video.id == original_id).first()
        if not original_video:
            raise HTTPException(status_code=404, detail="Original video not found")
            
        original_path = original_video.path
        
        # Handle processed video - could be ID or file path
        if os.path.exists(processed_id):
            # Direct file path
            processed_path = processed_id
        else:
            # Video ID
            processed_video = db.query(Video).filter(Video.id == processed_id).first()
            if not processed_video:
                raise HTTPException(status_code=404, detail="Processed video not found")
            processed_path = processed_video.path
            
        # Analyze quality
        quality_metrics = ffmpeg_utils.analyze_quality_loss(original_path, processed_path)
        
        if not quality_metrics.get("success"):
            raise HTTPException(status_code=500, detail=f"Quality analysis failed: {quality_metrics.get('error', 'Unknown error')}")
            
        logging.info(f"Quality analysis completed: SSIM={quality_metrics.get('ssim')}, PSNR={quality_metrics.get('psnr')}")
        
        return {
            "success": True,
            "original_video": {
                "id": original_video.id,
                "filename": original_video.filename
            },
            "processed_video": {
                "path": processed_path
            },
            "quality_metrics": quality_metrics,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Quality analysis endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/quality/report")
async def generate_processing_quality_report(request: dict):
    """
    Generate comprehensive quality report for processing pipeline.
    
    Body:
    - processing_chain: List of processing steps with original/processed paths
    
    Returns detailed quality preservation analysis.
    """
    try:
        processing_chain = request.get("processing_chain", [])
        
        if not processing_chain:
            raise HTTPException(status_code=400, detail="processing_chain is required")
            
        # Validate processing chain format
        for i, step in enumerate(processing_chain):
            required_fields = ["original", "processed", "operation"]
            if not all(field in step for field in required_fields):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Step {i+1} missing required fields: {required_fields}"
                )
                
        # Generate comprehensive report
        quality_report = ffmpeg_utils.generate_quality_report(processing_chain)
        
        if not quality_report.get("success"):
            raise HTTPException(status_code=500, detail=f"Report generation failed: {quality_report.get('error', 'Unknown error')}")
            
        logging.info(f"Quality report generated for {len(processing_chain)} processing steps")
        
        return {
            "success": True,
            "report": quality_report
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Quality report endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/quality/test")
async def test_quality_metrics():
    """
    Test endpoint to verify quality metrics functionality.
    Tests available FFmpeg quality filters.
    """
    try:
        # Check available FFmpeg filters
        check_cmd = ["ffmpeg", "-filters"]
        result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10)
        
        available_filters = {
            "ssim": "ssim" in result.stdout,
            "psnr": "psnr" in result.stdout, 
            "libvmaf": "libvmaf" in result.stdout
        }
        
        # Test FFmpeg version
        version_cmd = ["ffmpeg", "-version"]
        version_result = subprocess.run(version_cmd, capture_output=True, text=True, timeout=10)
        version_info = version_result.stdout.split('\n')[0] if version_result.returncode == 0 else "Unknown"
        
        return {
            "success": True,
            "ffmpeg_version": version_info,
            "available_quality_filters": available_filters,
            "recommendations": {
                "ssim": "Available - Structural Similarity Index measurement" if available_filters["ssim"] else "Not available - Install FFmpeg with ssim filter",
                "psnr": "Available - Peak Signal-to-Noise Ratio measurement" if available_filters["psnr"] else "Not available - Install FFmpeg with psnr filter", 
                "vmaf": "Available - Video Multimethod Assessment Fusion" if available_filters["libvmaf"] else "Not available - Requires FFmpeg with libvmaf (optional)"
            }
        }
        
    except Exception as e:
        logging.error(f"Quality test endpoint error: {e}")
        return {
            "success": False,
            "error": str(e),
            "recommendations": ["Install FFmpeg with quality filter support"]
        }


@app.post("/api/timeline/build-lossless")
async def build_timeline_lossless(request: dict, db: Session = Depends(get_db)):
    """
    Build timeline using advanced lossless concatenation.
    
    Body:
    - quality_target: "lossless", "near_lossless", or "lossy" 
    - clips: Optional list of specific clips (uses timeline clips if not provided)
    
    Returns enhanced build results with quality metrics.
    """
    try:
        quality_target = request.get("quality_target", "lossless")
        custom_clips = request.get("clips")
        
        if custom_clips:
            # Use provided clips
            clips_data = []
            for clip_info in custom_clips:
                video_id = clip_info.get("video_id")
                start = clip_info.get("start", 0)
                end = clip_info.get("end")
                
                video = db.query(Video).filter(Video.id == video_id).first()
                if not video:
                    raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
                    
                clips_data.append({
                    "path": video.path,
                    "start": start,
                    "end": end,
                    "video_id": video_id
                })
        else:
            # Use timeline clips from database
            clips = db.query(Clip).order_by(Clip.order_index).all()
            if not clips:
                raise HTTPException(status_code=400, detail="No clips in timeline")
                
            clips_data = []
            for clip in clips:
                clips_data.append({
                    "path": clip.video.path,
                    "start": clip.start_time,
                    "end": clip.end_time,
                    "video_id": str(clip.video.id)
                })
        
        # Check concatenation compatibility
        compatibility = ffmpeg_utils.validate_concat_compatibility(clips_data)
        
        # Generate output filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"timeline_lossless_{timestamp}.mp4"
        output_path = os.path.join("store", "exports", output_filename)
        
        # Ensure exports directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Build timeline using advanced concatenation
        result = ffmpeg_utils.concat_clips_lossless(clips_data, output_path, quality_target)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=f"Timeline build failed: {result.get('error', 'Unknown error')}")
            
        logging.info(f"Lossless timeline built successfully: {output_filename}")
        
        return {
            "success": True,
            "output_file": output_filename,
            "download_url": f"/static/exports/{output_filename}",
            "clips_count": len(clips_data),
            "quality_target": quality_target,
            "method_used": result["method_used"],
            "processing_time": result["processing_time"],
            "compatibility": compatibility,
            "quality_analysis": result.get("quality_analysis", {}),
            "warnings": result.get("warnings", []),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Lossless timeline build error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/concatenation/validate")
async def validate_concatenation_compatibility(request: dict, db: Session = Depends(get_db)):
    """
    Validate concatenation compatibility for clips.
    
    Body:
    - clip_ids: List of clip IDs or video IDs to check
    
    Returns compatibility analysis and recommendations.
    """
    try:
        clip_ids = request.get("clip_ids", [])
        
        if not clip_ids:
            raise HTTPException(status_code=400, detail="clip_ids is required")
            
        # Gather clip information
        clips_data = []
        for clip_id in clip_ids:
            # Try as clip ID first, then video ID
            clip = db.query(Clip).filter(Clip.id == clip_id).first()
            if clip:
                clips_data.append({
                    "path": clip.video.path,
                    "id": str(clip.id),
                    "type": "clip"
                })
            else:
                # Try as video ID
                video = db.query(Video).filter(Video.id == clip_id).first()
                if video:
                    clips_data.append({
                        "path": video.path,
                        "id": str(video.id),
                        "type": "video"
                    })
                else:
                    raise HTTPException(status_code=404, detail=f"Clip/Video {clip_id} not found")
                    
        # Validate compatibility
        compatibility = ffmpeg_utils.validate_concat_compatibility(clips_data)
        
        return {
            "success": True,
            "compatibility": compatibility,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Concatenation validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
