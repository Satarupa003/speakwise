from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────────────

class VideoStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Video schemas ─────────────────────────────────────────────────────────────

class VideoUploadResponse(BaseModel):
    id: str
    filename: str
    file_size_mb: float
    status: VideoStatus
    created_at: datetime

    class Config:
        from_attributes = True


class VideoDetail(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_size_mb: float
    duration_seconds: float
    status: VideoStatus
    title: Optional[str]
    speaker_name: Optional[str]
    is_reference: bool
    error_message: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


class VideoList(BaseModel):
    videos: List[VideoDetail]
    total: int


# ── Analysis schemas ──────────────────────────────────────────────────────────

class ScoreBreakdown(BaseModel):
    overall: Optional[float] = None
    pace: Optional[float] = None
    clarity: Optional[float] = None
    confidence: Optional[float] = None
    engagement: Optional[float] = None
    structure: Optional[float] = None
    body_language: Optional[float] = None


class AudioMetrics(BaseModel):
    words_per_minute: Optional[float] = None
    filler_word_count: Optional[int] = None
    filler_word_rate: Optional[float] = None
    filler_words_detail: Optional[Dict[str, int]] = None
    pause_count: Optional[int] = None
    avg_pause_duration: Optional[float] = None
    pitch_variation: Optional[float] = None
    volume_variation: Optional[float] = None


class VisualMetrics(BaseModel):
    eye_contact_score: Optional[float] = None
    gesture_frequency: Optional[float] = None
    posture_score: Optional[float] = None
    facial_expression_data: Optional[Dict[str, Any]] = None


class ImprovementPoint(BaseModel):
    area: str
    issue: str
    tip: str
    reference_video_id: Optional[str] = None
    reference_timestamp: Optional[float] = None
    reference_speaker: Optional[str] = None


class ReferenceClip(BaseModel):
    video_id: str
    speaker: str
    timestamp: float
    duration: float = 30.0
    reason: str


class AnalysisResult(BaseModel):
    id: str
    video_id: str
    scores: ScoreBreakdown
    audio: AudioMetrics
    visual: VisualMetrics
    transcript: Optional[str] = None
    transcript_segments: Optional[List[Dict]] = None
    feedback_summary: Optional[str] = None
    improvement_points: Optional[List[ImprovementPoint]] = None
    reference_clips: Optional[List[ReferenceClip]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AnalysisStartResponse(BaseModel):
    analysis_id: str
    video_id: str
    message: str
    status: str = "processing"


# ── Coach schemas ─────────────────────────────────────────────────────────────

class CoachMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    analysis_id: Optional[str] = None


class CoachResponse(BaseModel):
    reply: str
    suggestions: Optional[List[str]] = None
    referenced_clips: Optional[List[ReferenceClip]] = None


# ── Progress schemas ──────────────────────────────────────────────────────────

class ProgressEntry(BaseModel):
    video_id: str
    date: datetime
    overall_score: float
    scores: ScoreBreakdown


class ProgressDashboard(BaseModel):
    total_sessions: int
    avg_score: float
    best_score: float
    recent_sessions: List[ProgressEntry]
    score_trend: List[Dict[str, Any]]


# ── Pipeline schemas ──────────────────────────────────────────────────────────

class PipelineIngestRequest(BaseModel):
    video_path: str
    speaker_name: str
    title: Optional[str] = None
    source_url: Optional[str] = None


class PipelineStatus(BaseModel):
    total_reference_videos: int
    processed: int
    pending: int
    failed: int
