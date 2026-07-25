from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ── Enums ─────────────────────────────────────────────────────────────────────
class VideoStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Video ─────────────────────────────────────────────────────────────────────
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
    title: Optional[str] = None
    speaker_name: Optional[str] = None
    is_reference: bool = False
    error_message: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    class Config:
        from_attributes = True


class VideoList(BaseModel):
    videos: List[VideoDetail]
    total: int


# ── Score + metrics ───────────────────────────────────────────────────────────
class ScoreBreakdown(BaseModel):
    overall: Optional[float] = None
    content_quality: Optional[float] = None
    structure: Optional[float] = None
    delivery: Optional[float] = None
    confidence: Optional[float] = None
    emotional_presence: Optional[float] = None
    engagement: Optional[float] = None
    body_language: Optional[float] = None
    professionalism: Optional[float] = None
    pace: Optional[float] = None
    clarity: Optional[float] = None


class AudioMetrics(BaseModel):
    words_per_minute: Optional[float] = None
    filler_word_count: Optional[int] = None
    filler_word_rate: Optional[float] = None
    filler_words_detail: Optional[Dict[str, int]] = None
    pause_count: Optional[int] = None
    avg_pause_duration: Optional[float] = None
    pitch_variation: Optional[float] = None
    volume_variation: Optional[float] = None
    vocal_energy: Optional[float] = None
    duration_seconds: Optional[float] = None
    pace_sections: Optional[Dict[str, Any]] = None
    hesitation_patterns: Optional[List[Dict[str, Any]]] = None


class VisualMetrics(BaseModel):
    eye_contact_score: Optional[float] = None
    gesture_frequency: Optional[float] = None
    posture_score: Optional[float] = None
    camera_engagement: Optional[float] = None
    looking_away_count: Optional[int] = None
    confidence_signal: Optional[float] = None
    behavioral_patterns: Optional[List[str]] = None
    facial_expression_data: Optional[Dict[str, Any]] = None


# ── Feedback sub-models (all tolerant) ────────────────────────────────────────
class EmotionSignal(BaseModel):
    emotion: Optional[str] = None
    level: Optional[str] = None
    evidence: Optional[str] = None


class FrameworkPart(BaseModel):
    part: Optional[str] = None
    status: Optional[str] = None
    observation: Optional[str] = None
    verdict: Optional[str] = None


class FrameworkRecommendation(BaseModel):
    recommended: Optional[bool] = None
    name: Optional[str] = None
    reason: Optional[str] = None


class Observation(BaseModel):
    aspect: Optional[str] = None
    what_happened: Optional[str] = None
    evidence: Optional[str] = None
    why_it_matters: Optional[str] = None
    how_to_improve: Optional[str] = None


class MicroFeedback(BaseModel):
    observation: Optional[str] = None
    before: Optional[str] = None
    after: Optional[str] = None


class ImprovementPoint(BaseModel):
    area: Optional[str] = None
    what_happened: Optional[str] = None
    why_it_matters: Optional[str] = None
    how_to_fix: Optional[str] = None
    practice_exercise: Optional[str] = None
    issue: Optional[str] = None
    tip: Optional[str] = None
    reference_url: Optional[str] = None
    reference_speaker: Optional[str] = None
    reference_title: Optional[str] = None
    reference_why: Optional[str] = None


class ReferenceClip(BaseModel):
    speaker: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    why: Optional[str] = None
    skill: Optional[str] = None


class ComparisonChange(BaseModel):
    metric: Optional[str] = None
    change_pct: Optional[float] = None
    direction: Optional[str] = None
    text: Optional[str] = None


# ── Full analysis result ──────────────────────────────────────────────────────
class AnalysisResult(BaseModel):
    id: str
    video_id: str
    scores: ScoreBreakdown
    audio: AudioMetrics
    visual: VisualMetrics

    content_type: Optional[str] = None
    topic: Optional[str] = None
    scenario: Optional[str] = None
    framework: Optional[Dict[str, Any]] = None
    slides_summary: Optional[str] = None

    emotions: Optional[List[EmotionSignal]] = None

    feedback_summary: Optional[str] = None
    overall_score_label: Optional[str] = None
    polished_version: Optional[str] = None
    audience_perception: Optional[str] = None
    next_practice_topic: Optional[str] = None
    motivational_close: Optional[str] = None

    framework_breakdown: Optional[List[FrameworkPart]] = None
    framework_recommendation: Optional[FrameworkRecommendation] = None
    what_worked_well: Optional[List[str]] = None
    delivery_observations: Optional[List[Observation]] = None
    body_language_observations: Optional[List[Observation]] = None
    emotional_presence: Optional[Dict[str, Any]] = None
    micro_feedback: Optional[List[MicroFeedback]] = None
    challenge_questions: Optional[List[str]] = None
    improvement_points: Optional[List[ImprovementPoint]] = None
    reference_clips: Optional[List[ReferenceClip]] = None

    comparison: Optional[Dict[str, Any]] = None
    created_at: datetime
    class Config:
        from_attributes = True


class AnalysisStartResponse(BaseModel):
    analysis_id: str
    video_id: str
    message: str


# ── Coach ─────────────────────────────────────────────────────────────────────
class CoachMessage(BaseModel):
    analysis_id: Optional[str] = None
    video_id: Optional[str] = None
    message: str


class CoachResponse(BaseModel):
    reply: str
    suggestions: Optional[List[str]] = None
    referenced_clips: Optional[List[ReferenceClip]] = None


# ── Progress ──────────────────────────────────────────────────────────────────
class ProgressEntry(BaseModel):
    video_id: str
    date: Optional[str] = None
    scenario: Optional[str] = None
    topic: Optional[str] = None
    overall: Optional[float] = None
    confidence: Optional[float] = None
    body_language: Optional[float] = None
    emotional_presence: Optional[float] = None
    filler_word_rate: Optional[float] = None
    eye_contact: Optional[float] = None


class ProgressDashboard(BaseModel):
    entries: List[ProgressEntry]
    total_sessions: int
    improving: List[str]
    regressing: List[str]
    summary: Optional[str] = None
