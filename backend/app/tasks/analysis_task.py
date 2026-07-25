"""
Analysis pipeline — MINIMAL: Whisper -> Ollama
===============================================
Body language (OpenCV) and audio DSP (librosa) are disabled.
Flow: transcribe -> text stats -> signals -> scores -> Ollama feedback -> save.
"""
import traceback
from datetime import datetime
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.video import Video, VideoStatus
from app.models.analysis import Analysis


async def run_analysis_pipeline(video_id: str, content_type: str = "speech", topic: str = ""):
    async with AsyncSessionLocal() as db:
        try:
            await _set_status(db, video_id, VideoStatus.PROCESSING)
            print(f"[Pipeline] Starting analysis for {video_id}")

            res = await db.execute(select(Video).where(Video.id == video_id))
            video = res.scalar_one_or_none()
            if not video:
                print(f"[Pipeline] Video {video_id} not found")
                return

            from app.services.audio_analyzer import AudioAnalyzer
            from app.services.visual_analyzer import VisualAnalyzer
            from app.services.nlp_analyzer import NLPAnalyzer
            from app.services.emotion_analyzer import EmotionAnalyzer
            from app.services.scoring_engine import ScoringEngine
            from app.services.feedback_engine import FeedbackEngine

            print("[Pipeline] Transcribing...")
            audio = await AudioAnalyzer().analyze(video.file_path)

            visual = await VisualAnalyzer().analyze(video.file_path)   # disabled stub

            print("[Pipeline] Text analysis...")
            nlp = await NLPAnalyzer().analyze(audio["transcript"], audio.get("segments"))

            print("[Pipeline] Signals...")
            emotions = EmotionAnalyzer().analyze(audio, visual)

            print("[Pipeline] Scoring...")
            scores = ScoringEngine().compute(audio, visual, nlp)

            existing = await db.execute(select(Analysis).where(Analysis.video_id == video_id))
            analysis = existing.scalar_one_or_none()
            if not analysis:
                analysis = Analysis(video_id=video_id)
                db.add(analysis)

            _store_metrics(analysis, audio, visual, nlp, scores, emotions, content_type, topic)
            await db.flush()

            print("[Pipeline] Generating feedback with Ollama...")
            feedback = await FeedbackEngine().generate(
                audio=audio, visual=visual, nlp=nlp, scores=scores,
                emotions=emotions, content_type=content_type, topic=topic)

            _store_feedback(analysis, feedback)
            await db.commit()

            await _set_status(db, video_id, VideoStatus.COMPLETED, set_processed=True)
            print(f"[Pipeline] Complete for {video_id}. Overall {scores['overall']}")

        except Exception as e:
            print(f"[Pipeline] Error: {e}")
            traceback.print_exc()
            await _set_status(db, video_id, VideoStatus.FAILED, error=str(e))


def _store_metrics(a, audio, visual, nlp, scores, emotions, content_type, topic):
    a.overall_score            = scores.get("overall")
    a.content_quality_score    = scores.get("content_quality")
    a.structure_score          = scores.get("structure")
    a.delivery_score           = scores.get("delivery")
    a.confidence_score         = scores.get("confidence")
    a.emotional_presence_score = scores.get("emotional_presence")
    a.engagement_score         = scores.get("engagement")
    a.body_language_score      = scores.get("body_language")
    a.professionalism_score    = scores.get("professionalism")
    a.pace_score               = scores.get("pace")
    a.clarity_score            = scores.get("clarity")

    a.words_per_minute    = audio.get("words_per_minute")
    a.filler_word_count   = audio.get("filler_word_count")
    a.filler_word_rate    = audio.get("filler_word_rate")
    a.filler_words_detail = audio.get("filler_words_detail")
    a.pause_count         = audio.get("pause_count")
    a.avg_pause_duration  = audio.get("avg_pause_duration")
    a.pitch_variation     = audio.get("pitch_variation")
    a.volume_variation    = audio.get("volume_variation")
    a.duration_seconds    = audio.get("duration_seconds")
    a.pace_sections       = audio.get("pace_sections")
    a.transcript          = audio.get("transcript")
    a.transcript_segments = audio.get("segments")

    a.eye_contact_score   = visual.get("eye_contact_score")
    a.gesture_frequency   = visual.get("gesture_frequency")
    a.posture_score       = visual.get("posture_score")
    a.behavioral_patterns = visual.get("behavioral_patterns") or []
    a.visual_metrics      = visual

    a.emotions      = emotions
    a.content_type  = content_type
    a.topic         = topic or None


def _store_feedback(a, fb):
    a.scenario                 = fb.get("scenario")
    a.framework                = fb.get("framework")
    a.feedback_summary         = fb.get("overall_assessment", "")
    a.overall_score_label      = fb.get("overall_score_label", "")
    a.polished_version         = fb.get("polished_version", "")
    a.audience_perception      = fb.get("audience_perception", "")
    a.next_practice_topic      = fb.get("next_practice_topic", "")
    a.motivational_close       = fb.get("motivational_close", "")
    a.framework_breakdown      = fb.get("framework_breakdown", [])
    a.framework_recommendation = fb.get("framework_recommendation", {})
    a.what_worked_well         = fb.get("what_worked_well", [])
    a.challenge_questions      = fb.get("challenge_questions", [])
    a.micro_feedback           = fb.get("micro_feedback", [])
    a.improvement_points       = fb.get("improvement_points", [])
    a.delivery_analysis        = {"observations": fb.get("delivery_observations", [])}
    a.body_language_analysis   = {"observations": fb.get("body_language_observations", [])}
    a.emotional_presence       = fb.get("emotional_presence", {})
    a.reference_clips          = fb.get("reference_clips", [])


async def _set_status(db, video_id, status, set_processed=False, error=None):
    res = await db.execute(select(Video).where(Video.id == video_id))
    v = res.scalar_one_or_none()
    if v:
        v.status = status
        if set_processed:
            v.processed_at = datetime.utcnow()
        if error:
            v.error_message = error[:500]
        await db.commit()
