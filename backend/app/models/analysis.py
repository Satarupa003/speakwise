from sqlalchemy import String, DateTime, Float, ForeignKey, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id: Mapped[str] = mapped_column(String, ForeignKey("videos.id"), unique=True)

    # ── 8-dimension Communication Score (0–100) ─────────────────
    overall_score: Mapped[float] = mapped_column(Float, nullable=True)
    content_quality_score: Mapped[float] = mapped_column(Float, nullable=True)
    structure_score: Mapped[float] = mapped_column(Float, nullable=True)
    delivery_score: Mapped[float] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)
    emotional_presence_score: Mapped[float] = mapped_column(Float, nullable=True)
    engagement_score: Mapped[float] = mapped_column(Float, nullable=True)
    body_language_score: Mapped[float] = mapped_column(Float, nullable=True)
    professionalism_score: Mapped[float] = mapped_column(Float, nullable=True)
    # legacy dims kept for compatibility
    pace_score: Mapped[float] = mapped_column(Float, nullable=True)
    clarity_score: Mapped[float] = mapped_column(Float, nullable=True)

    # ── Audio metrics ────────────────────────────────────────────
    words_per_minute: Mapped[float] = mapped_column(Float, nullable=True)
    filler_word_count: Mapped[int] = mapped_column(Integer, nullable=True)
    filler_word_rate: Mapped[float] = mapped_column(Float, nullable=True)
    pause_count: Mapped[int] = mapped_column(Integer, nullable=True)
    avg_pause_duration: Mapped[float] = mapped_column(Float, nullable=True)
    pitch_variation: Mapped[float] = mapped_column(Float, nullable=True)
    volume_variation: Mapped[float] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=True)
    filler_words_detail: Mapped[dict] = mapped_column(JSON, nullable=True)
    pace_sections: Mapped[dict] = mapped_column(JSON, nullable=True)   # fastest/slowest/consistency

    # ── Transcript (stored, not centerpiece) ────────────────────
    transcript: Mapped[str] = mapped_column(Text, nullable=True)
    transcript_segments: Mapped[list] = mapped_column(JSON, nullable=True)

    # ── Visual metrics ───────────────────────────────────────────
    eye_contact_score: Mapped[float] = mapped_column(Float, nullable=True)
    gesture_frequency: Mapped[float] = mapped_column(Float, nullable=True)
    posture_score: Mapped[float] = mapped_column(Float, nullable=True)
    behavioral_patterns: Mapped[list] = mapped_column(JSON, nullable=True)   # detected patterns
    visual_metrics: Mapped[dict] = mapped_column(JSON, nullable=True)        # full visual detail

    # ── Emotion & behavioral analysis ────────────────────────────
    emotions: Mapped[list] = mapped_column(JSON, nullable=True)  # [{emotion, level, evidence}]

    # ── Context ──────────────────────────────────────────────────
    content_type: Mapped[str] = mapped_column(String, nullable=True)
    topic: Mapped[str] = mapped_column(String, nullable=True)
    scenario: Mapped[str] = mapped_column(String, nullable=True)
    slides_summary: Mapped[str] = mapped_column(Text, nullable=True)

    # ── AI Mentor Feedback ───────────────────────────────────────
    feedback_summary: Mapped[str] = mapped_column(Text, nullable=True)
    overall_score_label: Mapped[str] = mapped_column(String, nullable=True)
    polished_version: Mapped[str] = mapped_column(Text, nullable=True)
    next_practice_topic: Mapped[str] = mapped_column(Text, nullable=True)
    motivational_close: Mapped[str] = mapped_column(Text, nullable=True)
    audience_perception: Mapped[str] = mapped_column(Text, nullable=True)

    framework: Mapped[dict] = mapped_column(JSON, nullable=True)
    framework_breakdown: Mapped[list] = mapped_column(JSON, nullable=True)
    framework_recommendation: Mapped[dict] = mapped_column(JSON, nullable=True)
    what_worked_well: Mapped[list] = mapped_column(JSON, nullable=True)
    challenge_questions: Mapped[list] = mapped_column(JSON, nullable=True)
    micro_feedback: Mapped[list] = mapped_column(JSON, nullable=True)          # before/after
    improvement_points: Mapped[list] = mapped_column(JSON, nullable=True)
    delivery_analysis: Mapped[dict] = mapped_column(JSON, nullable=True)       # deep voice coaching
    body_language_analysis: Mapped[dict] = mapped_column(JSON, nullable=True)  # deep body coaching
    emotional_presence: Mapped[dict] = mapped_column(JSON, nullable=True)
    reference_clips: Mapped[list] = mapped_column(JSON, nullable=True)

    # ── Memory / comparison with previous attempts ───────────────
    comparison: Mapped[dict] = mapped_column(JSON, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    video: Mapped["Video"] = relationship("Video", back_populates="analysis")  # noqa: F821
