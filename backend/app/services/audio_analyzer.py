"""
AudioAnalyzer — MINIMAL (transcription only)
=============================================
faster-whisper transcription + word-timing metrics computed in pure Python.
No librosa, no numpy-heavy DSP → no NumPy binary conflicts.

Still produces: transcript, segments, WPM, filler words + timestamps,
pauses, pace sections. Pitch/volume are stubbed at 0.
"""

import os
import subprocess
import tempfile
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from app.core.config import settings

FILLER_SINGLE = {"um", "uh", "er", "ah", "like", "basically", "literally",
                 "actually", "honestly", "right", "okay"}
FILLER_MULTI = {"you know", "i mean", "kind of", "sort of", "okay so", "so um", "and uh"}

LONG_PAUSE_THRESHOLD = 2.0
MIN_PAUSE_DURATION = 0.4
PACE_WINDOW_SECONDS = 20.0


class AudioAnalyzer:

    def __init__(self):
        self._model = None

    async def analyze(self, video_path: str) -> dict[str, Any]:
        video_path = str(video_path)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        print(f"[AudioAnalyzer] Extracting audio from {Path(video_path).name}")
        with tempfile.TemporaryDirectory() as tmp:
            audio_path = os.path.join(tmp, "audio.wav")
            self._extract_audio(video_path, audio_path)

            print("[AudioAnalyzer] Transcribing with faster-whisper...")
            segments_raw, info = self._transcribe(audio_path)
            metrics = self._compute(segments_raw, info)

        print(f"[AudioAnalyzer] Done - {metrics['words_per_minute']:.0f} WPM, "
              f"{metrics['filler_word_count']} fillers, {metrics['pause_count']} pauses")
        return metrics

    def _extract_audio(self, video_path, out_path):
        cmd = ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
               "-ar", "16000", "-ac", "1", out_path]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"FFmpeg failed:\n{r.stderr}")

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            name = getattr(settings, "WHISPER_MODEL", "base")
            print(f"[AudioAnalyzer] Loading faster-whisper '{name}'...")
            self._model = WhisperModel(name, device="cpu", compute_type="int8")
        return self._model

    def _transcribe(self, audio_path):
        model = self._load()
        segments, info = model.transcribe(audio_path, word_timestamps=True, language="en")
        return list(segments), info

    def _compute(self, segments_raw, info) -> dict[str, Any]:
        words, parts = [], []
        for seg in segments_raw:
            parts.append(seg.text.strip())
            for w in (seg.words or []):
                words.append({"word": w.word.strip().lower(),
                              "start": round(float(w.start), 3),
                              "end": round(float(w.end), 3)})

        transcript = " ".join(parts)
        duration = float(getattr(info, "duration", 0)) or (words[-1]["end"] if words else 0.0)
        wpm = (len(words) / duration * 60) if duration > 0 else 0.0

        fillers, detail = self._fillers(words)
        filler_rate = (len(fillers) / duration * 60) if duration > 0 else 0.0
        pauses, long_pauses = self._pauses(words)
        avg_pause = statistics.fmean([p["duration"] for p in pauses]) if pauses else 0.0

        hesitations = [{"type": "long_pause", "at": p["start"], "duration": p["duration"]}
                       for p in long_pauses[:5]]
        for i in range(len(fillers) - 1):
            if fillers[i + 1]["start"] - fillers[i]["start"] < 5:
                hesitations.append({"type": "filler_cluster", "at": fillers[i]["start"],
                                    "words": [fillers[i]["word"], fillers[i + 1]["word"]]})

        return {
            "transcript": transcript,
            "segments": self._package(segments_raw),
            "duration_seconds": round(duration, 2),
            "word_count": len(words),
            "words_per_minute": round(wpm, 1),
            "filler_word_count": len(fillers),
            "filler_word_rate": round(filler_rate, 2),
            "filler_words_detail": dict(detail),
            "filler_instances": fillers,
            "pause_count": len(pauses),
            "avg_pause_duration": round(avg_pause, 3),
            "long_pauses": long_pauses,
            "pitch_variation": 0.0,      # disabled (no librosa)
            "volume_variation": 0.0,     # disabled
            "vocal_energy": 0.0,         # disabled
            "pace_sections": self._pace(words, duration),
            "hesitation_patterns": hesitations[:8],
        }

    def _pace(self, words, duration) -> dict:
        if not words or duration <= 0:
            return {"windows": [], "fastest": None, "slowest": None,
                    "consistency": 0.0, "avg_wpm": 0.0}
        windows, t = [], 0.0
        while t < duration:
            end = min(t + PACE_WINDOW_SECONDS, duration)
            n = sum(1 for w in words if t <= w["start"] < end)
            span = max(end - t, 1e-6)
            windows.append({"start": round(t, 1), "end": round(end, 1),
                            "wpm": round(n / span * 60, 1)})
            t = end
        wpms = [w["wpm"] for w in windows if w["wpm"] > 0] or [0.0]
        nonzero = [w for w in windows if w["wpm"] > 0] or windows
        return {
            "windows": windows,
            "fastest": max(windows, key=lambda w: w["wpm"]),
            "slowest": min(nonzero, key=lambda w: w["wpm"]),
            "consistency": round(statistics.pstdev(wpms) if len(wpms) > 1 else 0.0, 1),
            "avg_wpm": round(statistics.fmean(wpms), 1),
        }

    def _package(self, segments_raw):
        out = []
        for i, seg in enumerate(segments_raw):
            out.append({
                "id": i,
                "start": round(float(seg.start), 3),
                "end": round(float(seg.end), 3),
                "text": seg.text.strip(),
                "words": [{"word": w.word.strip(), "start": round(float(w.start), 3),
                           "end": round(float(w.end), 3)} for w in (seg.words or [])],
            })
        return out

    def _fillers(self, words):
        found, detail, n, i = [], Counter(), len(words), 0
        while i < n:
            token = words[i]["word"].strip(".,!?\"'")
            matched = False
            for phrase in FILLER_MULTI:
                p = phrase.split()
                if i + len(p) <= n:
                    cand = " ".join(words[i + j]["word"].strip(".,!?\"'") for j in range(len(p)))
                    if cand == phrase:
                        found.append({"word": phrase, "start": words[i]["start"],
                                      "end": words[i + len(p) - 1]["end"]})
                        detail[phrase] += 1
                        i += len(p)
                        matched = True
                        break
            if not matched:
                if token in FILLER_SINGLE:
                    found.append({"word": token, "start": words[i]["start"], "end": words[i]["end"]})
                    detail[token] += 1
                i += 1
        return found, detail

    def _pauses(self, words):
        pauses, longs = [], []
        for i in range(1, len(words)):
            gap = words[i]["start"] - words[i - 1]["end"]
            if gap >= MIN_PAUSE_DURATION:
                e = {"start": round(words[i - 1]["end"], 3),
                     "end": round(words[i]["start"], 3), "duration": round(gap, 3)}
                pauses.append(e)
                if gap >= LONG_PAUSE_THRESHOLD:
                    longs.append(e)
        return pauses, longs
