"""
EmotionAnalyzer — text/voice-timing only (visual disabled)
Emits evidence-backed signals derived from pace, fillers and pauses.
"""
from typing import Any


class EmotionAnalyzer:
    def analyze(self, audio: dict[str, Any], visual: dict[str, Any]) -> list[dict]:
        wpm = audio.get("words_per_minute", 0) or 0
        filler = audio.get("filler_word_rate", 0) or 0
        longs = len(audio.get("long_pauses", []) or [])
        hes = len(audio.get("hesitation_patterns", []) or [])
        cons = (audio.get("pace_sections") or {}).get("consistency", 0) or 0
        out = []

        def add(e, lvl, ev): out.append({"emotion": e, "level": lvl, "evidence": ev})

        pts = sum([filler < 3, 110 <= wpm <= 170, cons < 40, longs < 3])
        add("Fluency & composure", "high" if pts >= 4 else "moderate" if pts >= 2 else "low",
            f"{wpm:.0f} WPM, {filler:.1f} fillers/min, pace varies +/-{cons:.0f} WPM, {longs} long pauses.")

        if filler > 5 or hes >= 3:
            add("Hesitation", "high" if filler > 7 else "moderate",
                f"{filler:.1f} fillers/min and {hes} hesitation events detected.")
        else:
            add("Conviction", "high" if filler < 2 else "moderate",
                f"Low filler usage ({filler:.1f}/min) supports a confident, decided tone.")

        if wpm > 180:
            add("Rushed delivery", "moderate", f"{wpm:.0f} WPM is above the 120-160 comfort range.")
        elif 0 < wpm < 100:
            add("Slow pacing", "moderate", f"{wpm:.0f} WPM may read as hesitant or low-energy.")

        return out
