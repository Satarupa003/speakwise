"""
Analysis pipeline orchestrator.
Called as a FastAPI BackgroundTask — runs all analysis services in sequence
and saves results to the database.
"""
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.video import Video, VideoStatus
from app.models.analysis import Analysis


async def run_analysis_pipeline(video_id: str):
    """Full pipeline for a user-uploaded speech video."""
    async with AsyncSessionLocal() as db:
        try:
            await _set_status(db, video_id, VideoStatus.PROCESSING)
            print(f"[Pipeline] Starting analysis for video {video_id}")

            # 1. Load video record
            result = await db.execute(select(Video).where(Video.id == video_id))
            video = result.scalar_one_or_none()
            if not video:
                print(f"[Pipeline] Video {video_id} not found")
                return

            video_path = video.file_path
            print(f"[Pipeline] Processing: {video_path}")

            # 2. Run analysis services (imported here to avoid circular imports)
            from app.services.audio_analyzer import AudioAnalyzer
            from app.services.visual_analyzer import VisualAnalyzer
            from app.services.nlp_analyzer import NLPAnalyzer
            from app.services.scoring_engine import ScoringEngine
            from app.services.feedback_engine import FeedbackEngine

            audio_analyzer = AudioAnalyzer()
            visual_analyzer = VisualAnalyzer()
            nlp_analyzer = NLPAnalyzer()
            scoring_engine = ScoringEngine()
            feedback_engine = FeedbackEngine()

            # Run audio and visual in parallel
            print("[Pipeline] Running audio + visual analysis...")
            audio_result, visual_result = await asyncio.gather(
                audio_analyzer.analyze(video_path),
                visual_analyzer.analyze(video_path),
            )

            # NLP needs transcript from audio
            print("[Pipeline] Running NLP analysis...")
            nlp_result = await nlp_analyzer.analyze(
                transcript=audio_result["transcript"],
                segments=audio_result["segments"],
            )

            # Score everything
            print("[Pipeline] Computing scores...")
            scores = scoring_engine.compute(audio_result, visual_result, nlp_result)

            # Generate AI feedback + reference clips
            print("[Pipeline] Generating AI feedback...")
            feedback = await feedback_engine.generate(
                audio=audio_result,
                visual=visual_result,
                nlp=nlp_result,
                scores=scores,
            )

            # Save analysis to DB
            existing = await db.execute(select(Analysis).where(Analysis.video_id == video_id))
            analysis = existing.scalar_one_or_none()
            if not analysis:
                analysis = Analysis(video_id=video_id)
                db.add(analysis)

            # Scores
            analysis.overall_score = scores["overall"]
            analysis.pace_score = scores["pace"]
            analysis.clarity_score = scores["clarity"]
            analysis.confidence_score = scores["confidence"]
            analysis.engagement_score = scores["engagement"]
            analysis.structure_score = scores["structure"]
            analysis.body_language_score = scores["body_language"]

            # Audio
            analysis.words_per_minute = audio_result["words_per_minute"]
            analysis.filler_word_count = audio_result["filler_word_count"]
            analysis.filler_word_rate = audio_result["filler_word_rate"]
            analysis.filler_words_detail = audio_result["filler_words_detail"]
            analysis.pause_count = audio_result["pause_count"]
            analysis.avg_pause_duration = audio_result["avg_pause_duration"]
            analysis.pitch_variation = audio_result["pitch_variation"]
            analysis.volume_variation = audio_result["volume_variation"]
            analysis.transcript = audio_result["transcript"]
            analysis.transcript_segments = audio_result["segments"]

            # NLP
            analysis.sentence_structure = nlp_result["sentence_structure"]
            analysis.emotional_arc = nlp_result["emotional_arc"]

            # Visual
            analysis.eye_contact_score = visual_result["eye_contact_score"]
            analysis.gesture_frequency = visual_result["gesture_frequency"]
            analysis.posture_score = visual_result["posture_score"]
            analysis.facial_expression_data = visual_result["facial_expression_data"]

            # Feedback
            analysis.feedback_summary = feedback["summary"]
            analysis.improvement_points = feedback["improvement_points"]
            analysis.reference_clips = feedback["reference_clips"]

            await db.commit()

            # Update video status
            await _set_status(db, video_id, VideoStatus.COMPLETED, set_processed=True)
            print(f"[Pipeline] ✓ Analysis complete for {video_id}. Overall score: {scores['overall']}")

        except Exception as e:
            print(f"[Pipeline] ✗ Error processing {video_id}: {e}")
            import traceback
            traceback.print_exc()
            await _set_status(db, video_id, VideoStatus.FAILED, error=str(e))


async def run_reference_pipeline(video_id: str):
    """Pipeline for ingesting a great speaker video into the knowledge base."""
    async with AsyncSessionLocal() as db:
        try:
            await _set_status(db, video_id, VideoStatus.PROCESSING)
            print(f"[Reference Pipeline] Ingesting reference video {video_id}")

            result = await db.execute(select(Video).where(Video.id == video_id))
            video = result.scalar_one_or_none()
            if not video:
                return

            from app.services.audio_analyzer import AudioAnalyzer
            from app.services.knowledge_base import KnowledgeBase

            audio_analyzer = AudioAnalyzer()
            kb = KnowledgeBase()

            # Extract features
            audio_result = await audio_analyzer.analyze(video.file_path)

            # Store in ChromaDB knowledge base
            await kb.add_speaker(
                video_id=video_id,
                speaker_name=video.speaker_name or "Unknown",
                title=video.title or "",
                audio_data=audio_result,
                file_path=video.file_path,
            )

            await _set_status(db, video_id, VideoStatus.COMPLETED, set_processed=True)
            print(f"[Reference Pipeline] ✓ Ingested {video.speaker_name} — {video.title}")

        except Exception as e:
            print(f"[Reference Pipeline] ✗ Error: {e}")
            await _set_status(db, video_id, VideoStatus.FAILED, error=str(e))


async def _set_status(
    db: AsyncSession,
    video_id: str,
    status: VideoStatus,
    error: str = None,
    set_processed: bool = False,
):
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if video:
        video.status = status
        if error:
            video.error_message = error
        if set_processed:
            video.processed_at = datetime.utcnow()
        await db.commit()
