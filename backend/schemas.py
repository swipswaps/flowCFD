from pydantic import BaseModel, Field
from typing import Optional, List, Literal # NEW: Import Literal

class VideoOut(BaseModel):
    id: str
    filename: str
    duration: Optional[float] = None
    thumbnail_url: Optional[str] = None
    url: Optional[str] = None # Public URL for video playback in the frontend
    thumbnail_strip_url: Optional[str] = None # NEW: URL for video thumbnail strip
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
    # CORRECTED: Use a tuple or typing.Literal for string enums in Pydantic
    status: Literal["queued", "processing", "completed", "error"] # Changed from "queued" | "processing" | ...
    progress: int
    download_url: Optional[str] = None
    class Config:
        from_attributes = True

class ExportStatusOut(BaseModel):
    id: str
    # CORRECTED: Use a tuple or typing.Literal for string enums in Pydantic
    status: Literal["queued", "processing", "completed", "error"] # Changed from "queued" | "processing" | ...
    progress: int
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    estimated_time_remaining_seconds: Optional[float] = None # NEW: ETA for export