from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid
import enum


class VideoStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=True)

    # File info
    filename: Mapped[str] = mapped_column(String)
    original_filename: Mapped[str] = mapped_column(String)
    file_path: Mapped[str] = mapped_column(String)
    file_size_mb: Mapped[float] = mapped_column(Float, default=0.0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    mime_type: Mapped[str] = mapped_column(String, default="video/mp4")

    # Processing
    status: Mapped[VideoStatus] = mapped_column(
        SAEnum(VideoStatus), default=VideoStatus.UPLOADED
    )
    error_message: Mapped[str] = mapped_column(String, nullable=True)

    # Metadata
    title: Mapped[str] = mapped_column(String, nullable=True)
    speaker_name: Mapped[str] = mapped_column(String, nullable=True)
    is_reference: Mapped[bool] = mapped_column(default=False)  # True = great speaker video

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    processed_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="videos")  # noqa: F821
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="video", uselist=False)  # noqa: F821
