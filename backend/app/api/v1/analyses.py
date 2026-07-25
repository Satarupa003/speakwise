from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.video import Video, VideoStatus
from app.schemas.schemas import (
    AnalysisResult, AnalysisStartResponse, ScoreBreakdown, AudioMetrics,
    VisualMetrics, EmotionSignal, FrameworkPart, FrameworkRecommendation,
    Observation, MicroFeedback, ImprovementPoint, ReferenceClip,
)
from app.tasks.analysis_task import run_analysis_pipeline

router = APIRouter()


def _clean_list(items, model):
    out = []
    for it in (items or []):
        if isinstance(it, dict):
            out.append(model(**{k: v for k, v in it.items() if k in model.model_fields}))
    return out


@router.post("/start/{video_id}", response_model=AnalysisStartResponse)
async def start_analysis(video_id: str, background_tasks: BackgroundTasks,
                         db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "Video not found")
    if video.status == VideoStatus.PROCESSING:
        raise HTTPException(409, "Analysis already in progress")
    background_tasks.add_task(run_analysis_pipeline, video_id,
                             video.speaker_name or "speech", video.title or "")
    return AnalysisStartResponse(analysis_id="pending", video_id=video_id,
                                 message="Analysis started.")


@router.get("/{video_id}", response_model=AnalysisResult)
async def get_analysis(video_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Analysis).where(Analysis.video_id == video_id))
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Analysis not found. Video may still be processing.")

    dev = (a.delivery_analysis or {}).get("observations", [])
    bod = (a.body_language_analysis or {}).get("observations", [])

    return AnalysisResult(
        id=a.id, video_id=a.video_id,
        scores=ScoreBreakdown(
            overall=a.overall_score, content_quality=a.content_quality_score,
            structure=a.structure_score, delivery=a.delivery_score,
            confidence=a.confidence_score, emotional_presence=a.emotional_presence_score,
            engagement=a.engagement_score, body_language=a.body_language_score,
            professionalism=a.professionalism_score, pace=a.pace_score, clarity=a.clarity_score),
        audio=AudioMetrics(
            words_per_minute=a.words_per_minute, filler_word_count=a.filler_word_count,
            filler_word_rate=a.filler_word_rate, filler_words_detail=a.filler_words_detail,
            pause_count=a.pause_count, avg_pause_duration=a.avg_pause_duration,
            pitch_variation=a.pitch_variation, volume_variation=a.volume_variation,
            duration_seconds=a.duration_seconds, pace_sections=a.pace_sections),
        visual=VisualMetrics(
            eye_contact_score=a.eye_contact_score, gesture_frequency=a.gesture_frequency,
            posture_score=a.posture_score,
            camera_engagement=(a.visual_metrics or {}).get("camera_engagement"),
            looking_away_count=(a.visual_metrics or {}).get("looking_away_count"),
            confidence_signal=(a.visual_metrics or {}).get("confidence_signal"),
            behavioral_patterns=a.behavioral_patterns),
        content_type=a.content_type, topic=a.topic, scenario=a.scenario,
        framework=a.framework, slides_summary=a.slides_summary,
        emotions=_clean_list(a.emotions, EmotionSignal),
        feedback_summary=a.feedback_summary, overall_score_label=a.overall_score_label,
        polished_version=a.polished_version, audience_perception=a.audience_perception,
        next_practice_topic=a.next_practice_topic, motivational_close=a.motivational_close,
        framework_breakdown=_clean_list(a.framework_breakdown, FrameworkPart),
        framework_recommendation=(FrameworkRecommendation(**{
            k: v for k, v in (a.framework_recommendation or {}).items()
            if k in FrameworkRecommendation.model_fields}) if a.framework_recommendation else None),
        what_worked_well=a.what_worked_well or [],
        delivery_observations=_clean_list(dev, Observation),
        body_language_observations=_clean_list(bod, Observation),
        emotional_presence=a.emotional_presence or {},
        micro_feedback=_clean_list(a.micro_feedback, MicroFeedback),
        challenge_questions=a.challenge_questions or [],
        improvement_points=_clean_list(a.improvement_points, ImprovementPoint),
        reference_clips=_clean_list(a.reference_clips, ReferenceClip),
        comparison=a.comparison or {},
        created_at=a.created_at,
    )
