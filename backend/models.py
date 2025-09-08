import uuid
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from database import Base

def uid() -> str:
    return str(uuid.uuid4())

class Video(Base):
    __tablename__ = "videos"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String, nullable=True)
    thumbnail_strip_url: Mapped[str] = mapped_column(String, nullable=False) # THIS MUST BE PRESENT
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    clips: Mapped[list["Clip"]] = relationship("Clip", back_populates="video", cascade="all, delete-orphan")
    exports: Mapped[list["Export"]] = relationship("Export", back_populates="video", cascade="all, delete-orphan")

class Track(Base):
    __tablename__ = "tracks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String, default="default")
    track_type: Mapped[str] = mapped_column(String, default="video")  # 'video', 'audio', 'overlay'
    track_name: Mapped[str] = mapped_column(String, nullable=False)
    track_order: Mapped[int] = mapped_column(Integer, default=1)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    volume: Mapped[float] = mapped_column(Float, default=1.0)
    opacity: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    clips: Mapped[list["Clip"]] = relationship("Clip", back_populates="track", cascade="all, delete-orphan")
    audio_clips: Mapped[list["AudioClip"]] = relationship("AudioClip", back_populates="track", cascade="all, delete-orphan")

class Clip(Base):
    __tablename__ = "clips"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    video_id: Mapped[str] = mapped_column(String, ForeignKey("videos.id", ondelete="CASCADE"))
    track_id: Mapped[int] = mapped_column(Integer, ForeignKey("tracks.id", ondelete="CASCADE"), default=1)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    timeline_position: Mapped[float] = mapped_column(Float, default=0.0)
    z_index: Mapped[int] = mapped_column(Integer, default=0)
    transition_in: Mapped[str] = mapped_column(String, default="none")
    transition_out: Mapped[str] = mapped_column(String, default="none")
    video: Mapped["Video"] = relationship("Video", back_populates="clips")
    track: Mapped["Track"] = relationship("Track", back_populates="clips")

class AudioClip(Base):
    __tablename__ = "audio_clips"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    video_id: Mapped[str] = mapped_column(String, ForeignKey("videos.id", ondelete="CASCADE"))
    track_id: Mapped[int] = mapped_column(Integer, ForeignKey("tracks.id", ondelete="CASCADE"))
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    timeline_position: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, default=1.0)
    fade_in: Mapped[float] = mapped_column(Float, default=0.0)
    fade_out: Mapped[float] = mapped_column(Float, default=0.0)
    audio_effects: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of effects
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    video: Mapped["Video"] = relationship("Video")
    track: Mapped["Track"] = relationship("Track", back_populates="audio_clips")

class Export(Base):
    __tablename__ = "exports"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    idempotency_key: Mapped[str | None] = mapped_column(String, nullable=True, unique=True) # NEW
    video_id: Mapped[str] = mapped_column(String, ForeignKey("videos.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String, default="queued")  # queued|processing|completed|error
    progress: Mapped[int] = mapped_column(Integer, default=0)      # 0..100
    download_url: Mapped[str | None] = mapped_column(String, nullable=True)
    settings: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    osp_path: Mapped[str | None] = mapped_column(String, nullable=True)
    output_path: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_time_remaining_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    video: Mapped["Video"] = relationship("Video", back_populates="exports")

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)