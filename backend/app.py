# backend/app.py
import os
import uuid
import json
import asyncio
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from .database import Base, engine, SessionLocal
from .models import Video, Clip, Export
from .schemas import VideoOut, ClipIn, ClipOut, ExportStartIn, ExportOut, ExportStatusOut
from .ffmpeg_utils import ffprobe_duration, extract_clip, concat_mp4s

# ---- Paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
STORE = os.path.join(ROOT, "store")
UPLOADS = os.path.join(STORE, "uploads")
EXPORTS = os.path.join(STORE, "exports")
PROJECTS = os.path.join(STORE, "projects")
os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(EXPORTS, exist_ok=True)
os.makedirs(PROJECTS, exist_ok=True)

# ---- DB init
Base.metadata.create_all(bind=engine)

# ---- App + CORS
app = FastAPI(title="CapCut-Lite Backend", version="1.0.0")

# ---- Static Files Mount
app.mount("/uploads", StaticFiles(directory=UPLOADS), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # lock down in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Simple in-memory WS broadcaster per export_id
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

# ---- Helpers
def db() -> Session:
    return SessionLocal()

def edits_csv_path(video: Video) -> str:
    return os.path.join(PROJECTS, f"{video.id}_edits.csv")

def osp_path_for(video: Video) -> str:
    return os.path.join(PROJECTS, f"{video.id}.osp")

def output_path_for(export: Export) -> str:
    return os.path.join(EXPORTS, f"{export.id}.mp4")

# ------------------------
# Video Management
# ------------------------
@app.post("/api/videos/upload", response_model=VideoOut)
async def upload_video(file: UploadFile = File(...)):
    suffix = file.filename.split(".")[-1].lower()
    if suffix not in ("mp4", "mov", "avi", "m4v"):
        raise HTTPException(400, "Unsupported file type")

    vid = Video(filename=file.filename, path=os.path.join(UPLOADS, f"{uuid.uuid4()}_{file.filename}"))
    # write file
    os.makedirs(os.path.dirname(vid.path), exist_ok=True)
    with open(vid.path, "wb") as f:
        f.write(await file.read())

    # duration
    dur = ffprobe_duration(vid.path)
    vid.duration = dur

    with db() as s:
        s.add(vid)
        s.commit()
        s.refresh(vid)

    # create empty CSV with header matching your script
    with open(edits_csv_path(vid), "w") as f:
        f.write("# IN,OUT (seconds)\n")

    return vid

@app.get("/api/videos/{video_id}", response_model=VideoOut)
def get_video(video_id: str):
    with db() as s:
        v = s.get(Video, video_id)
        if not v:
            raise HTTPException(404, "Video not found")
        return v

@app.delete("/api/videos/{video_id}")
def delete_video(video_id: str):
    with db() as s:
        v = s.get(Video, video_id)
        if not v:
            raise HTTPException(404, "Video not found")
        # cascade will remove clips/exports rows
        s.delete(v)
        s.commit()
    # best-effort file cleanup
    return {"ok": True}

# ------------------------
# Clip Operations
# ------------------------
@app.post("/api/clips/mark", response_model=ClipOut)
def mark_clip(payload: ClipIn):
    if payload.end_time <= payload.start_time:
        raise HTTPException(400, "end_time must be > start_time")
    with db() as s:
        v = s.get(Video, payload.video_id)
        if not v:
            raise HTTPException(404, "Video not found")

        c = Clip(
            video_id=v.id,
            start_time=float(payload.start_time),
            end_time=float(payload.end_time),
            order_index=int(payload.order_index),
        )
        s.add(c)
        s.commit()
        s.refresh(c)

        # append to CSV for compatibility with your pipeline
        csv_path = edits_csv_path(v)
        with open(csv_path, "a") as f:
            f.write(f"{c.start_time},{c.end_time}\n")

        return c

@app.get("/api/clips/{video_id}", response_model=list[ClipOut])
def list_clips(video_id: str):
    with db() as s:
        stmt = select(Clip).where(Clip.video_id == video_id).order_by(Clip.order_index, Clip.start_time)
        rows = s.execute(stmt).scalars().all()
        return rows

@app.put("/api/clips/{clip_id}", response_model=ClipOut)
def update_clip(clip_id: str, payload: ClipIn):
    with db() as s:
        c = s.get(Clip, clip_id)
        if not c:
            raise HTTPException(404, "Clip not found")
        c.start_time = float(payload.start_time)
        c.end_time = float(payload.end_time)
        c.order_index = int(payload.order_index)
        s.commit()
        s.refresh(c)

        # rewrite CSV (source of truth: DB)
        v = s.get(Video, c.video_id)
        csv_path = edits_csv_path(v)
        stmt = select(Clip).where(Clip.video_id == v.id).order_by(Clip.order_index, Clip.start_time)
        rows = s.execute(stmt).scalars().all()
        with open(csv_path, "w") as f:
            f.write("# IN,OUT (seconds)\n")
            for r in rows:
                f.write(f"{r.start_time},{r.end_time}\n")
        return c

@app.delete("/api/clips/{clip_id}")
def delete_clip(clip_id: str):
    with db() as s:
        c = s.get(Clip, clip_id)
        if not c:
            raise HTTPException(404, "Clip not found")
        vid = c.video_id
        s.delete(c)
        s.commit()
        # rewrite CSV
        v = s.get(Video, vid)
        if v:
            csv_path = edits_csv_path(v)
            stmt = select(Clip).where(Clip.video_id == v.id).order_by(Clip.order_index, Clip.start_time)
            rows = s.execute(stmt).scalars().all()
            with open(csv_path, "w") as f:
                f.write("# IN,OUT (seconds)\n")
                for r in rows:
                    f.write(f"{r.start_time},{r.end_time}\n")
    return {"ok": True}

# ------------------------
# Project Build (.osp via your script)
# ------------------------
@app.post("/api/projects/build")
def build_project(video_id: str = Form(...)):
    """
    Uses your create_openshot_project.py to generate an .osp
    from the DB-backed CSV we maintain.
    """
    with db() as s:
        v = s.get(Video, video_id)
        if not v:
            raise HTTPException(404, "Video not found")
    csv_path = edits_csv_path(v)
    if not os.path.exists(csv_path):
        raise HTTPException(400, "No edits CSV found for this video")

    osp_out = osp_path_for(v)
    cmd = [
        "python3", os.path.join(ROOT, "create_openshot_project.py"),
        csv_path, v.path, osp_out
    ]
    import subprocess
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(500, f"OSP build failed: {e.stderr or e.stdout}")

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
    await asyncio.sleep(0)  # yield

    from pathlib import Path
    import tempfile

    with db() as s:
        exp = s.get(Export, export_id)
        if not exp:
            return
        vid = s.get(Video, exp.video_id)
        if not vid:
            exp.status = "error"
            exp.error_message = "Video not found"
            s.commit()
            return

        exp.status = "processing"
        exp.progress = 1
        exp.updated_at = datetime.utcnow()
        s.commit()

    await bus.publish(export_id, {"status": "processing", "progress": 1})

    # Load OSP
    try:
        with open(osp_path_for(vid), "r") as f:
            project = json.load(f)
    except Exception as e:
        with db() as s:
            exp = s.get(Export, export_id)
            exp.status = "error"
            exp.error_message = f"Failed to read OSP: {e}"
            exp.updated_at = datetime.utcnow()
            s.commit()
        await bus.publish(export_id, {"status": "error", "progress": 0, "error_message": "OSP read failed"})
        return

    files = project.get("files", [])
    if not files:
        with db() as s:
            exp = s.get(Export, export_id)
            exp.status = "error"
            exp.error_message = "No files in project"
            exp.updated_at = datetime.utcnow()
            s.commit()
        await bus.publish(export_id, {"status": "error", "progress": 0, "error_message": "No files in project"})
        return

    src = files[0]["path"]
    clips = project.get("clips", [])
    if not clips:
        with db() as s:
            exp = s.get(Export, export_id)
            exp.status = "error"
            exp.error_message = "No clips in project"
            exp.updated_at = datetime.utcnow()
            s.commit()
        await bus.publish(export_id, {"status": "error", "progress": 0, "error_message": "No clips"})
        return

    # temp workspace
    tmpdir = tempfile.mkdtemp(prefix=f"exp_{export_id}_")
    filelist = os.path.join(tmpdir, "concat.txt")
    out_path = output_path_for(Export(id=export_id, video_id=vid.id))
    # actual row update (ensure record has out_path)
    with db() as s:
        exp = s.get(Export, export_id)
        exp.output_path = out_path
        s.commit()

    # Extract each clip
    ok_count = 0
    total = len(clips)
    clip_paths = []
    for i, clip in enumerate(clips):
        start = float(clip.get("start", 0))
        end = float(clip.get("end", 0))
        dur = max(0.0, end - start)
        if dur <= 0.0:
            continue
        out_clip = os.path.join(tmpdir, f"clip_{i:03d}.mp4")
        success = extract_clip(src, start, dur, out_clip)
        if success:
            clip_paths.append(out_clip)
            ok_count += 1
        prog = int(5 + (i + 1) * 70 / total)  # 5-75% during extraction
        with db() as s:
            exp = s.get(Export, export_id)
            exp.progress = prog
            exp.updated_at = datetime.utcnow()
            s.commit()
        await bus.publish(export_id, {"status": "processing", "progress": prog})

    if not clip_paths:
        with db() as s:
            exp = s.get(Export, export_id)
            exp.status = "error"
            exp.error_message = "No valid clips extracted"
            exp.updated_at = datetime.utcnow()
            s.commit()
        await bus.publish(export_id, {"status": "error", "progress": 0, "error_message": "Extraction failed"})
        return

    # Write concat list
    with open(filelist, "w") as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")

    # Concat
    concat_ok, stderr = concat_mp4s(filelist, out_path)
    with db() as s:
        exp = s.get(Export, export_id)
        if concat_ok and os.path.exists(out_path):
            exp.status = "completed"
            exp.progress = 100
            exp.download_url = f"/api/exports/{export_id}/download"
        else:
            exp.status = "error"
            exp.error_message = f"Concat failed: {stderr or 'Unknown error'}"
        exp.updated_at = datetime.utcnow()
        s.commit()

    status_payload = {
        "status": "completed" if concat_ok else "error",
        "progress": 100 if concat_ok else 0,
        "download_url": f"/api/exports/{export_id}/download" if concat_ok else None,
        "error_message": f"Concat failed: {stderr or 'Unknown error'}" if not concat_ok else None
    }
    await bus.publish(export_id, status_payload)

# Start export
@app.post("/api/exports/start", response_model=ExportOut)
async def start_export(payload: ExportStartIn):
    with db() as s:
        v = s.get(Video, payload.video_id)
        if not v:
            raise HTTPException(404, "Video not found")
        # ensure OSP exists
        osp = osp_path_for(v)
        if not os.path.exists(osp):
            raise HTTPException(400, "Project has not been built yet. Call /api/projects/build first.")
        exp = Export(video_id=v.id, status="queued", progress=0, osp_path=osp)
        s.add(exp)
        s.commit()
        s.refresh(exp)
        export_id = exp.id

    # fire and forget (no background scheduler dependency)
    asyncio.create_task(export_worker(export_id))
    return exp

@app.get("/api/exports/{export_id}/status", response_model=ExportStatusOut)
def export_status(export_id: str):
    with db() as s:
        exp = s.get(Export, export_id)
        if not exp:
            raise HTTPException(404, "Export not found")
        return ExportStatusOut(
            id=exp.id, status=exp.status, progress=exp.progress,
            download_url=exp.download_url, error_message=exp.error_message
        )

@app.get("/api/exports/{export_id}/download")
def export_download(export_id: str):
    with db() as s:
        exp = s.get(Export, export_id)
        if not exp or exp.status != "completed" or not exp.output_path or not os.path.exists(exp.output_path):
            raise HTTPException(404, "Export not ready")
        return FileResponse(exp.output_path, filename=f"{export_id}.mp4", media_type="video/mp4")

# WebSocket for progress
@app.websocket("/ws/exports/{export_id}")
async def ws_exports(websocket: WebSocket, export_id: str):
    await bus.subscribe(export_id, websocket)
    try:
        while True:
            # keep alive; client may send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        bus.unsubscribe(export_id, websocket)
