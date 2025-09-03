import os
import uuid
import json
import asyncio
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from typing import List

# --- Corrected Imports: Changed from relative to absolute ---
from backend.database import Base, engine, SessionLocal
from backend.models import Video, Clip, Export
from backend.schemas import VideoOut, ClipIn, ClipOut, ExportStartIn, ExportOut, ExportStatusOut
from backend.ffmpeg_utils import ffprobe_duration, generate_thumbnail, extract_clip, concat_mp4s
# -----------------------------------------------------------

# ---- Paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
STORE = os.path.join(ROOT, "store")
UPLOADS = os.path.join(STORE, "uploads")
EXPORTS = os.path.join(STORE, "exports")
PROJECTS = os.path.join(STORE, "projects")
THUMBNAILS = os.path.join(STORE, "thumbnails")
os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(EXPORTS, exist_ok=True)
os.makedirs(PROJECTS, exist_ok=True)
os.makedirs(THUMBNAILS, exist_ok=True)

# ---- DB init
Base.metadata.create_all(bind=engine)

# ---- App + CORS
app = FastAPI(title="CapCut-Lite Backend", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # lock down in prod: e.g., ["http://localhost:5173", "https://yourdomain.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Helpers (db() function MUST be defined before any routes use Depends(db))
def db() -> Session:
    return SessionLocal()

def edits_csv_path(video_id: str) -> str:
    return os.path.join(PROJECTS, f"{video_id}_edits.csv")

def osp_path_for(video_id: str) -> str:
    return os.path.join(PROJECTS, f"{video_id}.osp")

def output_path_for(export: Export) -> str:
    return os.path.join(EXPORTS, f"{export.id}.mp4")

def thumbnail_path_for(video_id: str) -> str:
    return os.path.join(THUMBNAILS, f"{video_id}.jpg")

def rewrite_csv_for_video(s: Session, video_id: str):
    """Rewrites the edits CSV file for a given video based on current clips in DB."""
    csv_path = edits_csv_path(video_id)
    stmt = select(Clip).where(Clip.video_id == video_id).order_by(Clip.order_index, Clip.start_time)
    rows = s.execute(stmt).scalars().all()
    with open(csv_path, "w") as f:
        f.write("# IN,OUT (seconds)\n")
        for r in rows:
            f.write(f"{r.start_time},{r.end_time}\n")

# ---- Simple in-memory WS broadcaster per export_id (MUST be defined before any routes use it)
class ExportBus:
    def __init__(self):
        self._subscribers: dict[str, set[WebSocket]] = {}

    def ensure(self, export_id: str):
        self._subscribers.setdefault(export_id, set())

    async def subscribe(self, export_id: str, ws: WebSocket):
        self.ensure(export_id)
        await ws.accept()
        self._subscribers[export_id].add(ws)

    def unsubscribe(self, export_id: str, ws: WebSocket):
        try:
            self._subscribers.get(export_id, set()).remove(ws)
        except KeyError:
            pass

    async def publish(self, export_id: str, payload: dict):
        for ws in list(self._subscribers.get(export_id, set())):
            try:
                await ws.send_json(payload)
            except Exception:
                self.unsubscribe(export_id, ws)

bus = ExportBus()

# ------------------------
# Static File Serving Endpoints
# ------------------------
@app.get("/static/thumbnails/{filename:path}")
async def serve_thumbnail(filename: str):
    file_path = os.path.join(THUMBNAILS, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(file_path)

@app.get("/static/uploads/{video_id}/{filename:path}")
async def serve_uploaded_video(video_id: str, filename: str, s: Session = Depends(db)):
    video = s.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found in DB.")
    
    stored_filename = os.path.basename(video.path)
    if stored_filename != filename:
        raise HTTPException(status_code=400, detail="Filename mismatch or unauthorized access attempt.")
    
    file_path = video.path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video file not found on disk.")
    
    return FileResponse(file_path, filename=filename, media_type="video/mp4")


# ------------------------
# Video Management
# ------------------------
@app.post("/api/videos/upload", response_model=VideoOut)
async def upload_video(file: UploadFile = File(...), s: Session = Depends(db)): # Inject db session here too
    file_id = str(uuid.uuid4())
    filename_stem, file_extension = os.path.splitext(file.filename)
    file_extension = file_extension.lower()

    if file_extension not in (".mp4", ".mov", ".avi", ".m4v"):
        raise HTTPException(400, "Unsupported file type")

    video_path = os.path.join(UPLOADS, f"{file_id}{file_extension}")
    os.makedirs(os.path.dirname(video_path), exist_ok=True)
    with open(video_path, "wb") as f:
        f.write(await file.read())

    dur = ffprobe_duration(video_path)
    if dur is None:
        os.remove(video_path)
        raise HTTPException(500, "Could not determine video duration. File might be corrupted.")

    thumbnail_full_path = thumbnail_path_for(file_id)
    thumbnail_time = 1.0 if dur >= 1.0 else (dur / 2.0 if dur > 0 else 0.1)
    thumbnail_url_to_save = None
    if generate_thumbnail(video_path, thumbnail_full_path, thumbnail_time):
        thumbnail_url_to_save = f"/static/thumbnails/{os.path.basename(thumbnail_full_path)}"
    else:
        print(f"Warning: Could not generate thumbnail for {video_path}")
    
    vid = Video(
        id=file_id,
        filename=file.filename,
        path=video_path,
        duration=dur,
        thumbnail_url=thumbnail_url_to_save
    )

    s.add(vid)
    s.commit()
    s.refresh(vid)

    vid_out = VideoOut.from_orm(vid)
    vid_out.url = f"/static/uploads/{vid.id}/{os.path.basename(vid.path)}"
    
    with open(edits_csv_path(vid.id), "w") as f:
        f.write("# IN,OUT (seconds)\n")

    return vid_out

@app.get("/api/videos/{video_id}", response_model=VideoOut)
def get_video(video_id: str, s: Session = Depends(db)): # Inject db session here too
    v = s.get(Video, video_id)
    if not v:
        raise HTTPException(404, "Video not found")
    
    vid_out = VideoOut.from_orm(v)
    vid_out.url = f"/static/uploads/{v.id}/{os.path.basename(v.path)}"
    return vid_out

@app.delete("/api/videos/{video_id}")
def delete_video(video_id: str, s: Session = Depends(db)): # Inject db session here too
    v = s.get(Video, video_id)
    if not v:
        raise HTTPException(404, "Video not found")
    
    try:
        if os.path.exists(v.path):
            os.remove(v.path)
        csv_path = edits_csv_path(v.id)
        if os.path.exists(csv_path):
            os.remove(csv_path)
        osp_p = osp_path_for(v.id)
        if os.path.exists(osp_p):
            os.remove(osp_p)
        if v.thumbnail_url:
            thumb_file = os.path.basename(v.thumbnail_url)
            thumb_path = os.path.join(THUMBNAILS, thumb_file)
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
    except Exception as e:
        print(f"Warning: Failed to clean up files for video {video_id}: {e}")

    s.delete(v)
    s.commit()
    return {"ok": True}

# ------------------------
# Clip Operations
# ------------------------
@app.post("/api/clips/mark", response_model=ClipOut)
def mark_clip(payload: ClipIn, s: Session = Depends(db)): # Inject db session here too
    if payload.end_time <= payload.start_time:
        raise HTTPException(400, "End time must be greater than start time.")
    v = s.get(Video, payload.video_id)
    if not v:
        raise HTTPException(404, "Video not found")
    if payload.end_time > v.duration:
        raise HTTPException(400, f"End time ({payload.end_time:.2f}s) exceeds video duration ({v.duration:.2f}s).")

    c = Clip(
        video_id=v.id,
        start_time=float(payload.start_time),
        end_time=float(payload.end_time),
        order_index=int(payload.order_index),
    )
    s.add(c)
    s.commit()
    s.refresh(c)

    rewrite_csv_for_video(s, v.id)

    return c

@app.get("/api/clips/{video_id}", response_model=List[ClipOut])
def list_clips(video_id: str, s: Session = Depends(db)): # Inject db session here too
    stmt = select(Clip).where(Clip.video_id == video_id).order_by(Clip.order_index, Clip.start_time)
    rows = s.execute(stmt).scalars().all()
    return rows

@app.put("/api/clips/{clip_id}", response_model=ClipOut)
def update_clip(clip_id: str, payload: ClipIn, s: Session = Depends(db)): # Inject db session here too
    if payload.end_time <= payload.start_time:
        raise HTTPException(400, "End time must be greater than start time.")
    c = s.get(Clip, clip_id)
    if not c:
        raise HTTPException(404, "Clip not found")
    v = s.get(Video, c.video_id)
    if not v:
        raise HTTPException(404, "Associated video not found")
    if payload.end_time > v.duration:
        raise HTTPException(400, f"End time ({payload.end_time:.2f}s) exceeds video duration ({v.duration:.2f}s).")

    c.start_time = float(payload.start_time)
    c.end_time = float(payload.end_time)
    c.order_index = int(payload.order_index)
    s.commit()
    s.refresh(c)

    rewrite_csv_for_video(s, v.id)
    return c

@app.post("/api/clips/reorder/{video_id}", response_model=List[ClipOut])
def reorder_clips(video_id: str, clip_ids: List[str], s: Session = Depends(db)): # Inject db session here too
    v = s.get(Video, video_id)
    if not v:
        raise HTTPException(404, "Video not found")
    
    current_clips = {c.id: c for c in v.clips}
    ordered_clips = []

    for i, clip_id in enumerate(clip_ids):
        if clip_id not in current_clips:
            raise HTTPException(400, f"Clip ID {clip_id} not found for video {video_id}")
        
        clip = current_clips[clip_id]
        if clip.order_index != i:
            clip.order_index = i
        ordered_clips.append(clip)
    
    s.bulk_save_objects(ordered_clips)
    s.commit()
    
    rewrite_csv_for_video(s, v.id)
    
    return [ClipOut.from_orm(c) for c in ordered_clips]


@app.delete("/api/clips/{clip_id}")
def delete_clip(clip_id: str, s: Session = Depends(db)): # Inject db session here too
    c = s.get(Clip, clip_id)
    if not c:
        raise HTTPException(404, "Clip not found")
    
    vid_id = c.video_id
    s.delete(c)
    s.commit()

    remaining_clips = s.execute(select(Clip).where(Clip.video_id == vid_id).order_by(Clip.order_index, Clip.start_time)).scalars().all()
    for i, clip in enumerate(remaining_clips):
        if clip.order_index != i:
            clip.order_index = i
    s.bulk_save_objects(remaining_clips)
    s.commit()

    rewrite_csv_for_video(s, vid_id)
    return {"ok": True}


# ------------------------
# Project Build (.osp via your script)
# ------------------------
@app.post("/api/projects/build")
async def build_project(video_id: str = Form(...), s: Session = Depends(db)): # Inject db session here too
    """
    Uses your create_openshot_project.py to generate an .osp
    from the DB-backed CSV we maintain.
    """
    v = s.get(Video, video_id)
    if not v:
        raise HTTPException(404, "Video not found")
    if not s.execute(select(Clip).where(Clip.video_id == video_id)).first():
        raise HTTPException(400, "No clips marked for this video. Add clips before building the project.")

    csv_path = edits_csv_path(v.id)
    if not os.path.exists(csv_path) or os.stat(csv_path).st_size == len("# IN,OUT (seconds)\n"):
        raise HTTPException(400, "No valid edits found in CSV. Ensure clips are marked.")

    osp_out = osp_path_for(v.id)
    cmd = [
        "python3", os.path.join(ROOT, "create_openshot_project.py"),
        csv_path, v.path, osp_out
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise HTTPException(
                500,
                f"OSP build failed. Stderr: {stderr.decode().strip()} Stdout: {stdout.decode().strip()}"
            )
        print(f"OSP build stdout: {stdout.decode().strip()}")
        print(f"OSP build stderr: {stderr.decode().strip()}")

    except Exception as e:
        raise HTTPException(500, f"A critical error occurred during OSP build: {e}")

    return {"video_id": v.id, "osp": osp_out}

# ------------------------
# Export System (Background + WS)
# ------------------------
async def export_worker(export_id: str):
    """
    Known-to-work export strategy:
    1) Read .osp for source path & clips (already generated by your script).
    2) Extract each clip with ffmpeg into temp files (progress by count).
    3) Concat all clips into final .mp4
    4) Update Export row + WebSocket messages.
    """
    await asyncio.sleep(0)

    # Use a new session for the worker to avoid conflicts with request-bound sessions
    worker_db_session = SessionLocal()
    try:
        exp = worker_db_session.get(Export, export_id)
        if not exp:
            return
        vid = worker_db_session.get(Video, exp.video_id)
        if not vid:
            exp.status = "error"
            exp.error_message = "Video not found"
            worker_db_session.commit()
            return

        exp.status = "processing"
        exp.progress = 1
        exp.updated_at = datetime.utcnow()
        worker_db_session.commit()

        await bus.publish(export_id, {"status": "processing", "progress": 1, "error_message": None})

        osp_path = osp_path_for(vid.id)
        if not os.path.exists(osp_path):
            exp.status = "error"
            exp.error_message = "OSP file not found. Please build project first."
            worker_db_session.commit()
            await bus.publish(export_id, {"status": "error", "progress": 0, "error_message": "OSP file not found"})
            return

        with open(osp_path, "r") as f:
            project = json.load(f)

        files = project.get("files", [])
        if not files:
            exp.status = "error"
            exp.error_message = "No source files found in project"
            worker_db_session.commit()
            await bus.publish(export_id, {"status": "error", "progress": 0, "error_message": "No files in project"})
            return

        src = files[0]["path"]
        if not os.path.exists(src):
            exp.status = "error"
            exp.error_message = f"Source video file '{src}' not found on server."
            worker_db_session.commit()
            await bus.publish(export_id, {"status": "error", "progress": 0, "error_message": "Source video not found"})
            return

        clips = project.get("clips", [])
        if not clips:
            exp.status = "error"
            exp.error_message = "No clips found in project. Add clips before exporting."
            worker_db_session.commit()
            await bus.publish(export_id, {"status": "error", "progress": 0, "error_message": "No clips"})
            return

        tmpdir = tempfile.mkdtemp(prefix=f"exp_{export_id}_")
        filelist = os.path.join(tmpdir, "concat.txt")
        out_path = output_path_for(Export(id=export_id, video_id=vid.id))
        
        exp.output_path = out_path
        worker_db_session.commit()

        ok_count = 0
        total = len(clips)
        clip_paths = []
        for i, clip in enumerate(clips):
            start = float(clip.get("start", 0))
            end = float(clip.get("end", 0))
            dur = max(0.0, end - start)
            if dur <= 0.0:
                print(f"Skipping clip {i} due to non-positive duration: {dur}")
                continue
            out_clip = os.path.join(tmpdir, f"clip_{i:03d}.mp4")
            success = extract_clip(src, start, dur, out_clip)
            if success:
                clip_paths.append(out_clip)
                ok_count += 1
            else:
                print(f"Failed to extract clip {i} from {start}s to {end}s.")
            
            prog = int(5 + (i + 1) * 70 / total)
            exp.progress = prog
            exp.updated_at = datetime.utcnow()
            worker_db_session.commit()
            await bus.publish(export_id, {"status": "processing", "progress": prog, "error_message": None})

        if not clip_paths:
            exp.status = "error"
            exp.error_message = "No valid clips were extracted. Check video source or clip times."
            worker_db_session.commit()
            await bus.publish(export_id, {"status": "error", "progress": 0, "error_message": "Extraction failed"})
            return

        with open(filelist, "w") as f:
            for p in clip_paths:
                f.write(f"file '{p}'\n")

        concat_ok = concat_mp4s(filelist, out_path)
        
        if concat_ok and os.path.exists(out_path):
            exp.status = "completed"
            exp.progress = 100
            exp.download_url = f"/api/exports/{export_id}/download"
            exp.error_message = None
        else:
            exp.status = "error"
            exp.error_message = "Video concatenation failed during FFmpeg process."
        exp.updated_at = datetime.utcnow()
        worker_db_session.commit()

        status_payload = {
            "status": "completed" if concat_ok else "error",
            "progress": 100 if concat_ok else 0,
            "download_url": f"/api/exports/{export_id}/download" if concat_ok else None,
            "error_message": exp.error_message if exp else "Unknown error"
        }
        await bus.publish(export_id, status_payload)

    except Exception as e:
        print(f"Critical error in export_worker for {export_id}: {e}")
        try:
            exp = worker_db_session.get(Export, export_id)
            if exp:
                exp.status = "error"
                exp.error_message = f"Unexpected error during export: {e}"
                exp.updated_at = datetime.utcnow()
                worker_db_session.commit()
            await bus.publish(export_id, {"status": "error", "progress": exp.progress if exp else 0, "error_message": exp.error_message if exp else f"Unexpected error: {e}"})
        except Exception as rollback_e:
            print(f"Error updating export status on worker failure: {rollback_e}")
    finally:
        worker_db_session.close()
        try:
            import shutil
            if 'tmpdir' in locals() and os.path.exists(tmpdir):
                shutil.rmtree(tmpdir)
        except Exception as e:
            print(f"Warning: Failed to clean up temp directory {tmpdir}: {e}")


# Start export
@app.post("/api/exports/start", response_model=ExportOut)
async def start_export(payload: ExportStartIn, s: Session = Depends(db)): # Inject db session here too
    v = s.get(Video, payload.video_id)
    if not v:
        raise HTTPException(404, "Video not found")
    osp_p = osp_path_for(v.id)
    if not os.path.exists(osp_p):
        raise HTTPException(400, "Project has not been built yet. Call /api/projects/build first.")
    
    if not s.execute(select(Clip).where(Clip.video_id == v.id)).first():
        raise HTTPException(400, "No clips marked for this video. Add clips and build project before exporting.")

    exp = Export(video_id=v.id, status="queued", progress=0, osp_path=osp_p)
    s.add(exp)
    s.commit()
    s.refresh(exp)
    export_id = exp.id

    asyncio.create_task(export_worker(export_id))
    return exp

@app.get("/api/exports/{export_id}/status", response_model=ExportStatusOut)
def export_status(export_id: str, s: Session = Depends(db)): # Inject db session here too
    exp = s.get(Export, export_id)
    if not exp:
        raise HTTPException(404, "Export not found")
    return ExportStatusOut(
        id=exp.id, status=exp.status, progress=exp.progress,
        download_url=exp.download_url, error_message=exp.error_message
    )

@app.get("/api/exports/{export_id}/download")
def export_download(export_id: str, s: Session = Depends(db)): # Inject db session here too
    exp = s.get(Export, export_id)
    if not exp or exp.status != "completed" or not exp.output_path or not os.path.exists(exp.output_path):
        raise HTTPException(404, "Export not ready or file not found.")
    return FileResponse(exp.output_path, filename=f"{exp.video_id}-{export_id}.mp4", media_type="video/mp4")

# WebSocket for progress
@app.websocket("/ws/exports/{export_id}")
async def ws_exports(websocket: WebSocket, export_id: str):
    await bus.subscribe(export_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        bus.unsubscribe(export_id, websocket)
    except Exception as e:
        print(f"WebSocket error for {export_id}: {e}")
        bus.unsubscribe(export_id, websocket)