from pydantic import BaseModel, Field
from typing import Optional, List

class VideoOut(BaseModel):
    id: str
    filename: str
    path: str # Internal server path, not directly exposed to frontend for playback
    duration: Optional[float] = None
    thumbnail_url: Optional[str] = None
    url: Optional[str] = None # NEW: Public URL for video playback in the frontend
    class Config:
        from_attributes = True

class ClipIn(BaseModel):
    video_id: str
    start_time: float
    end_time: float
    order_index: int = 0

class ClipOut(BaseModel):
    id: str
    video_id: str
    start_time: float
    end_time: float
    order_index: int
    class Config:
        from_attributes = True

class ExportStartIn(BaseModel):
    video_id: str
    # optional export settings in future
    preset: Optional[str] = "web_hd"

class ExportOut(BaseModel):
    id: str
    video_id: str
    status: str
    progress: int
    download_url: Optional[str] = None
    class Config:
        from_attributes = True

class ExportStatusOut(BaseModel):
    id: str
    status: str
    progress: int
    download_url: Optional[str] = None
    error_message: Optional[str] = None