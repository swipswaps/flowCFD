# backend/models.py
import uuid
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from .database import Base

def uid() -> str:
    return str(uuid.uuid4())

class Video(Base):
    __tablename__ = "videos"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String, nullable=True) # NEW: thumbnail
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    clips: Mapped[list["Clip"]] = relationship("Clip", back_populates="video", cascade="all, delete-orphan")
    exports: Mapped[list["Export"]] = relationship("Export", back_populates="video", cascade="all, delete-orphan")

class Clip(Base):
    __tablename__ = "clips"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    video_id: Mapped[str] = mapped_column(String, ForeignKey("videos.id", ondelete="CASCADE"))
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    video: Mapped["Video"] = relationship("Video", back_populates="clips")

class Export(Base):
    __tablename__ = "exports"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
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

    video: Mapped["Video"] = relationship("Video", back_populates="exports")