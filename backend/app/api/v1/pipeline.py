from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.video import Video, VideoStatus
from app.schemas.schemas import PipelineIngestRequest, PipelineStatus
from app.tasks.analysis_task import run_reference_pipeline
import uuid
import os

router = APIRouter()


@router.post("/ingest")
async def ingest_reference_video(
    payload: PipelineIngestRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Ingest a great speaker video into the knowledge base."""
    if not os.path.exists(payload.video_path):
        raise HTTPException(404, f"Video file not found: {payload.video_path}")

    video_id = str(uuid.uuid4())
    filename = os.path.basename(payload.video_path)

    video = Video(
        id=video_id,
        filename=filename,
        original_filename=filename,
        file_path=payload.video_path,
        file_size_mb=round(os.path.getsize(payload.video_path) / (1024 * 1024), 2),
        speaker_name=payload.speaker_name,
        title=payload.title,
        is_reference=True,
        status=VideoStatus.UPLOADED,
    )
    db.add(video)
    await db.flush()

    background_tasks.add_task(run_reference_pipeline, video_id)

    return {"video_id": video_id, "message": f"Ingesting {filename} for {payload.speaker_name}"}


@router.get("/status", response_model=PipelineStatus)
async def pipeline_status(db: AsyncSession = Depends(get_db)):
    """Check knowledge base ingestion status."""
    result = await db.execute(
        select(Video.status, func.count(Video.id))
        .where(Video.is_reference == True)  # noqa: E712
        .group_by(Video.status)
    )
    rows = result.all()
    counts = {row[0]: row[1] for row in rows}

    total = sum(counts.values())
    return PipelineStatus(
        total_reference_videos=total,
        processed=counts.get(VideoStatus.COMPLETED, 0),
        pending=counts.get(VideoStatus.UPLOADED, 0) + counts.get(VideoStatus.PROCESSING, 0),
        failed=counts.get(VideoStatus.FAILED, 0),
    )
