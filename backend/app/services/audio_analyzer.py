"""
AudioAnalyzer
=============
Extracts everything audible from a speech video:

  1. Audio extraction      — pulls audio track from video via FFmpeg
  2. Transcription         — OpenAI Whisper (local, free) → full transcript + word timestamps
  3. Pace analysis         — words per minute, per-segment pace
  4. Filler word detection — "um", "uh", "like", "you know", etc. with timestamps
  5. Pause detection       — silence gaps between words, duration stats
  6. Pitch analysis        — fundamental frequency variation (librosa)
  7. Volume analysis       — RMS energy variation (librosa)
  8. Segment packaging     — timestamped chunks ready for NLP + frontend

Output dict shape:
{
    "transcript":        str,
    "segments":          list[dict],   # [{start, end, text, words}]
    "words_per_minute":  float,
    "filler_word_count": int,
    "filler_word_rate":  float,        # per minute
    "filler_words_detail": dict,       # {"um": 5, "uh": 3, ...}
    "filler_instances":  list[dict],   # [{word, start, end}]
    "pause_count":       int,
    "avg_pause_duration": float,       # seconds
    "long_pauses":       list[dict],   # pauses > 2s [{start, end, duration}]
    "pitch_variation":   float,        # std dev of F0 in Hz
    "volume_variation":  float,        # std dev of RMS energy
    "duration_seconds":  float,
}
"""

import os
import re
import tempfile
import subprocess
from pathlib import Path
from collections import Counter
from typing import Any

import numpy as np

from app.core.config import settings


# ---------------------------------------------------------------------------
# Filler word config
# ---------------------------------------------------------------------------

FILLER_WORDS = {
    "um", "uh", "er", "ah",
    "like", "basically", "literally", "actually", "honestly",
    "you know", "i mean", "kind of", "sort of", "right",
    "okay so", "so um", "and uh",
}

# Single-token fillers (fast lookup)
FILLER_SINGLE = {w for w in FILLER_WORDS if " " not in w}

# Multi-token fillers — checked across consecutive word pairs
FILLER_MULTI = {w for w in FILLER_WORDS if " " in w}

# Pauses longer than this (seconds) are flagged as "long"
LONG_PAUSE_THRESHOLD = 2.0

# Gap between words (seconds) to count as a deliberate pause
MIN_PAUSE_DURATION = 0.4


# ---------------------------------------------------------------------------
# AudioAnalyzer
# ---------------------------------------------------------------------------

class AudioAnalyzer:
    """
    Analyzes the audio track of a speech video.
    All heavy imports (whisper, librosa) happen inside methods so the
    service starts fast even if the models haven't loaded yet.
    """

    def __init__(self):
        self._whisper_model = None   # lazy-loaded on first use

    # ── Public API ──────────────────────────────────────────────────────────

    async def analyze(self, video_path: str) -> dict[str, Any]:
        """
        Main entry point. Accepts a video file path, returns the full
        audio analysis dict.
        """
        video_path = str(video_path)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        print(f"[AudioAnalyzer] Extracting audio from {Path(video_path).name}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = os.path.join(tmp_dir, "audio.wav")

            # Step 1: extract audio
            self._extract_audio(video_path, audio_path)

            # Step 2: transcribe
            print("[AudioAnalyzer] Transcribing with Whisper...")
            whisper_result = self._transcribe(audio_path)

            # Step 3: derive all metrics from transcript + raw audio
            print("[AudioAnalyzer] Computing metrics...")
            metrics = self._compute_metrics(audio_path, whisper_result)

        print(f"[AudioAnalyzer] ✓ Done — {metrics['words_per_minute']:.0f} WPM, "
              f"{metrics['filler_word_count']} fillers, "
              f"{metrics['pause_count']} pauses")
        return metrics

    # ── Step 1: Audio extraction ─────────────────────────────────────────────

    def _extract_audio(self, video_path: str, out_path: str):
        """
        Use FFmpeg to pull the audio track as a 16 kHz mono WAV.
        16 kHz mono is exactly what Whisper and librosa expect.
        """
        cmd = [
            "ffmpeg", "-y",           # overwrite output
            "-i", video_path,         # input
            "-vn",                    # no video
            "-acodec", "pcm_s16le",   # 16-bit PCM
            "-ar", "16000",           # 16 kHz sample rate
            "-ac", "1",               # mono
            out_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg audio extraction failed:\n{result.stderr}")

    # ── Step 2: Transcription ────────────────────────────────────────────────

    def _load_whisper(self):
        """Lazy-load Whisper model (slow first time, cached after)."""
        if self._whisper_model is None:
            import whisper
            print(f"[AudioAnalyzer] Loading Whisper model '{settings.WHISPER_MODEL}'...")
            self._whisper_model = whisper.load_model(settings.WHISPER_MODEL)
        return self._whisper_model

    def _transcribe(self, audio_path: str) -> dict:
        """
        Run Whisper transcription with word-level timestamps.
        Returns Whisper's native result dict.
        """
        model = self._load_whisper()
        result = model.transcribe(
            audio_path,
            word_timestamps=True,   # gives us per-word start/end times
            language="en",          # force English (remove for auto-detect)
            verbose=False,
        )
        return result

    # ── Step 3: Metrics ──────────────────────────────────────────────────────

    def _compute_metrics(self, audio_path: str, whisper_result: dict) -> dict[str, Any]:
        """Compute all metrics from Whisper result + raw audio waveform."""

        # ── Extract word list with timestamps ─────────────────────────────
        all_words = []
        for segment in whisper_result.get("segments", []):
            for word_info in segment.get("words", []):
                all_words.append({
                    "word":  word_info["word"].strip().lower(),
                    "start": round(word_info["start"], 3),
                    "end":   round(word_info["end"], 3),
                })

        # ── Basic stats ───────────────────────────────────────────────────
        transcript = whisper_result.get("text", "").strip()
        duration   = self._get_duration(whisper_result)
        word_count = len(all_words)
        wpm        = (word_count / duration * 60) if duration > 0 else 0

        # ── Package segments for frontend ─────────────────────────────────
        segments = self._package_segments(whisper_result)

        # ── Filler words ──────────────────────────────────────────────────
        filler_instances, filler_detail = self._detect_fillers(all_words)
        filler_count = len(filler_instances)
        filler_rate  = (filler_count / duration * 60) if duration > 0 else 0

        # ── Pauses ────────────────────────────────────────────────────────
        pauses, long_pauses = self._detect_pauses(all_words)
        avg_pause = (
            float(np.mean([p["duration"] for p in pauses]))
            if pauses else 0.0
        )

        # ── Pitch + Volume (librosa) ──────────────────────────────────────
        pitch_var, volume_var = self._compute_audio_features(audio_path)

        return {
            "transcript":          transcript,
            "segments":            segments,
            "duration_seconds":    round(duration, 2),
            "word_count":          word_count,
            "words_per_minute":    round(wpm, 1),
            "filler_word_count":   filler_count,
            "filler_word_rate":    round(filler_rate, 2),
            "filler_words_detail": dict(filler_detail),
            "filler_instances":    filler_instances,
            "pause_count":         len(pauses),
            "avg_pause_duration":  round(avg_pause, 3),
            "long_pauses":         long_pauses,
            "pitch_variation":     round(float(pitch_var), 2),
            "volume_variation":    round(float(volume_var), 4),
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_duration(self, whisper_result: dict) -> float:
        """Infer speech duration from last segment end time."""
        segments = whisper_result.get("segments", [])
        if not segments:
            return 0.0
        return float(segments[-1].get("end", 0.0))

    def _package_segments(self, whisper_result: dict) -> list[dict]:
        """
        Convert Whisper segments to clean frontend-ready format.
        Each segment = one sentence-ish chunk with start/end/text/words.
        """
        segments = []
        for seg in whisper_result.get("segments", []):
            words = [
                {
                    "word":  w["word"].strip(),
                    "start": round(w["start"], 3),
                    "end":   round(w["end"], 3),
                }
                for w in seg.get("words", [])
            ]
            segments.append({
                "id":    seg.get("id", 0),
                "start": round(seg["start"], 3),
                "end":   round(seg["end"], 3),
                "text":  seg["text"].strip(),
                "words": words,
            })
        return segments

    def _detect_fillers(
        self, words: list[dict]
    ) -> tuple[list[dict], Counter]:
        """
        Scan word list for filler words (single and multi-token).
        Returns:
          - filler_instances: [{word, start, end}]
          - filler_detail:    Counter {"um": 5, "uh": 3, ...}
        """
        instances = []
        detail    = Counter()
        n         = len(words)

        i = 0
        while i < n:
            token = words[i]["word"].lower().strip(".,!?\"'")

            # Check multi-token fillers first (e.g. "you know")
            matched_multi = False
            for phrase in FILLER_MULTI:
                parts = phrase.split()
                if i + len(parts) <= n:
                    candidate = " ".join(
                        words[i + j]["word"].lower().strip(".,!?\"'")
                        for j in range(len(parts))
                    )
                    if candidate == phrase:
                        instances.append({
                            "word":  phrase,
                            "start": words[i]["start"],
                            "end":   words[i + len(parts) - 1]["end"],
                        })
                        detail[phrase] += 1
                        i += len(parts)
                        matched_multi = True
                        break

            if not matched_multi:
                if token in FILLER_SINGLE:
                    instances.append({
                        "word":  token,
                        "start": words[i]["start"],
                        "end":   words[i]["end"],
                    })
                    detail[token] += 1
                i += 1

        return instances, detail

    def _detect_pauses(
        self, words: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        """
        Find silence gaps between consecutive words.
        A pause = gap >= MIN_PAUSE_DURATION seconds.
        A long pause = gap >= LONG_PAUSE_THRESHOLD seconds.
        """
        pauses      = []
        long_pauses = []

        for i in range(1, len(words)):
            gap = words[i]["start"] - words[i - 1]["end"]
            if gap >= MIN_PAUSE_DURATION:
                entry = {
                    "start":    round(words[i - 1]["end"], 3),
                    "end":      round(words[i]["start"], 3),
                    "duration": round(gap, 3),
                }
                pauses.append(entry)
                if gap >= LONG_PAUSE_THRESHOLD:
                    long_pauses.append(entry)

        return pauses, long_pauses

    def _compute_audio_features(
        self, audio_path: str
    ) -> tuple[float, float]:
        """
        Use librosa to compute:
          - pitch_variation:  std dev of fundamental frequency (F0) in Hz
          - volume_variation: std dev of RMS energy

        These two numbers together reveal:
          - Monotone speaking  → low pitch_variation
          - Inconsistent volume → high or low volume_variation
        """
        import librosa

        y, sr = librosa.load(audio_path, sr=16000, mono=True)

        # ── Pitch (F0) via pyin ───────────────────────────────────────────
        # pyin gives voiced/unvoiced tracking + F0 per frame
        f0, voiced_flag, _ = librosa.pyin(
            y,
            fmin=librosa.note_to_hz("C2"),   # ~65 Hz  (low male voice)
            fmax=librosa.note_to_hz("C7"),   # ~2093 Hz (high female voice)
            sr=sr,
        )
        # Only include voiced frames (filter out NaN / unvoiced)
        voiced_f0 = f0[voiced_flag & ~np.isnan(f0)]
        pitch_var = float(np.std(voiced_f0)) if len(voiced_f0) > 0 else 0.0

        # ── Volume (RMS energy) ───────────────────────────────────────────
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
        volume_var = float(np.std(rms))

        return pitch_var, volume_var
