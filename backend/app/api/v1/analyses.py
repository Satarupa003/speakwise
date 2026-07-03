from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.video import Video, VideoStatus
from app.schemas.schemas import AnalysisResult, AnalysisStartResponse, ScoreBreakdown, AudioMetrics, VisualMetrics, ImprovementPoint, ReferenceClip
from app.tasks.analysis_task import run_analysis_pipeline

router = APIRouter()


@router.post("/start/{video_id}", response_model=AnalysisStartResponse)
async def start_analysis(
    video_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger analysis for a video."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "Video not found")

    if video.status == VideoStatus.PROCESSING:
        raise HTTPException(409, "Analysis already in progress")

    # Re-run analysis
    analysis_result = await db.execute(select(Analysis).where(Analysis.video_id == video_id))
    existing = analysis_result.scalar_one_or_none()
    analysis_id = existing.id if existing else "pending"

    background_tasks.add_task(run_analysis_pipeline, video_id)

    return AnalysisStartResponse(
        analysis_id=analysis_id,
        video_id=video_id,
        message="Analysis started. Poll GET /analyses/{video_id} for results.",
    )


@router.get("/{video_id}", response_model=AnalysisResult)
async def get_analysis(video_id: str, db: AsyncSession = Depends(get_db)):
    """Get analysis results for a video."""
    result = await db.execute(select(Analysis).where(Analysis.video_id == video_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(404, "Analysis not found. Video may still be processing.")

    # Map flat model to nested response schema
    return AnalysisResult(
        id=analysis.id,
        video_id=analysis.video_id,
        scores=ScoreBreakdown(
            overall=analysis.overall_score,
            pace=analysis.pace_score,
            clarity=analysis.clarity_score,
            confidence=analysis.confidence_score,
            engagement=analysis.engagement_score,
            structure=analysis.structure_score,
            body_language=analysis.body_language_score,
        ),
        audio=AudioMetrics(
            words_per_minute=analysis.words_per_minute,
            filler_word_count=analysis.filler_word_count,
            filler_word_rate=analysis.filler_word_rate,
            filler_words_detail=analysis.filler_words_detail,
            pause_count=analysis.pause_count,
            avg_pause_duration=analysis.avg_pause_duration,
            pitch_variation=analysis.pitch_variation,
            volume_variation=analysis.volume_variation,
        ),
        visual=VisualMetrics(
            eye_contact_score=analysis.eye_contact_score,
            gesture_frequency=analysis.gesture_frequency,
            posture_score=analysis.posture_score,
            facial_expression_data=analysis.facial_expression_data,
        ),
        transcript=analysis.transcript,
        transcript_segments=analysis.transcript_segments,
        feedback_summary=analysis.feedback_summary,
        improvement_points=[ImprovementPoint(**p) for p in (analysis.improvement_points or [])],
        reference_clips=[ReferenceClip(**c) for c in (analysis.reference_clips or [])],
        created_at=analysis.created_at,
    )
