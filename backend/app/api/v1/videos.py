from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import shutil
import uuid
import os

from app.core.database import get_db
from app.core.config import settings
from app.models.video import Video, VideoStatus
from app.schemas.schemas import VideoUploadResponse, VideoDetail, VideoList
from app.tasks.analysis_task import run_analysis_pipeline

router = APIRouter()


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a user speech video and trigger analysis."""

    # Validate file type
    allowed_types = ["video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"]
    if file.content_type not in allowed_types:
        raise HTTPException(400, f"File type {file.content_type} not allowed. Use MP4, WebM, MOV, or AVI.")

    # Check file size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_VIDEO_SIZE_MB:
        raise HTTPException(400, f"File too large ({size_mb:.1f}MB). Max is {settings.MAX_VIDEO_SIZE_MB}MB.")

    # Save file
    video_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1] or ".mp4"
    saved_filename = f"{video_id}{ext}"
    file_path = settings.USER_UPLOADS_DIR / saved_filename

    with open(file_path, "wb") as f:
        f.write(content)

    # Create DB record
    video = Video(
        id=video_id,
        filename=saved_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size_mb=round(size_mb, 2),
        mime_type=file.content_type,
        status=VideoStatus.UPLOADED,
    )
    db.add(video)
    await db.flush()

    # Queue analysis
    background_tasks.add_task(run_analysis_pipeline, video_id)

    return video


@router.get("", response_model=VideoList)
async def list_videos(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List uploaded videos."""
    result = await db.execute(
        select(Video)
        .where(Video.is_reference == False)  # noqa: E712
        .order_by(Video.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    videos = result.scalars().all()
    return {"videos": videos, "total": len(videos)}


@router.get("/{video_id}", response_model=VideoDetail)
async def get_video(video_id: str, db: AsyncSession = Depends(get_db)):
    """Get video details and processing status."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "Video not found")
    return video


@router.delete("/{video_id}")
async def delete_video(video_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a video and its file."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "Video not found")

    # Delete file from disk
    if os.path.exists(video.file_path):
        os.remove(video.file_path)

    await db.delete(video)
    return {"message": f"Video {video_id} deleted"}
