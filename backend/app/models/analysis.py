from sqlalchemy import String, DateTime, Float, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id: Mapped[str] = mapped_column(String, ForeignKey("videos.id"), unique=True)

    # ── Scores (0–100) ──────────────────────────────────────────
    overall_score: Mapped[float] = mapped_column(Float, nullable=True)
    pace_score: Mapped[float] = mapped_column(Float, nullable=True)
    clarity_score: Mapped[float] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)
    engagement_score: Mapped[float] = mapped_column(Float, nullable=True)
    structure_score: Mapped[float] = mapped_column(Float, nullable=True)
    body_language_score: Mapped[float] = mapped_column(Float, nullable=True)

    # ── Audio metrics ────────────────────────────────────────────
    words_per_minute: Mapped[float] = mapped_column(Float, nullable=True)
    filler_word_count: Mapped[int] = mapped_column(nullable=True)
    filler_word_rate: Mapped[float] = mapped_column(Float, nullable=True)  # per minute
    pause_count: Mapped[int] = mapped_column(nullable=True)
    avg_pause_duration: Mapped[float] = mapped_column(Float, nullable=True)
    pitch_variation: Mapped[float] = mapped_column(Float, nullable=True)
    volume_variation: Mapped[float] = mapped_column(Float, nullable=True)

    # ── Transcript + NLP ─────────────────────────────────────────
    transcript: Mapped[str] = mapped_column(Text, nullable=True)
    filler_words_detail: Mapped[dict] = mapped_column(JSON, nullable=True)
    # e.g. {"um": 12, "uh": 5, "like": 8, "you know": 3}

    transcript_segments: Mapped[list] = mapped_column(JSON, nullable=True)
    # e.g. [{"start": 0.0, "end": 3.2, "text": "...", "words": [...]}]

    sentence_structure: Mapped[dict] = mapped_column(JSON, nullable=True)
    emotional_arc: Mapped[list] = mapped_column(JSON, nullable=True)

    # ── Visual metrics ───────────────────────────────────────────
    eye_contact_score: Mapped[float] = mapped_column(Float, nullable=True)
    gesture_frequency: Mapped[float] = mapped_column(Float, nullable=True)
    posture_score: Mapped[float] = mapped_column(Float, nullable=True)
    facial_expression_data: Mapped[dict] = mapped_column(JSON, nullable=True)

    # ── AI Feedback ──────────────────────────────────────────────
    feedback_summary: Mapped[str] = mapped_column(Text, nullable=True)
    improvement_points: Mapped[list] = mapped_column(JSON, nullable=True)
    # e.g. [{"area": "pace", "issue": "...", "tip": "...", "reference_video_id": "...", "reference_timestamp": 42.0}]

    reference_clips: Mapped[list] = mapped_column(JSON, nullable=True)
    # e.g. [{"video_id": "...", "speaker": "...", "timestamp": 120, "reason": "..."}]

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    video: Mapped["Video"] = relationship("Video", back_populates="analysis")  # noqa: F821
