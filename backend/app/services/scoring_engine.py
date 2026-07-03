"""
ScoringEngine
=============
Combines audio, visual, and NLP analysis results into
clean 0-100 scores per dimension.

Dimensions scored:
  1. pace          — speaking speed, pauses
  2. clarity       — filler words, sentence structure, NLP clarity
  3. confidence    — volume variation, eye contact, posture
  4. engagement    — pitch variation, gestures, emotional arc
  5. structure     — opening/closing strength, storytelling
  6. body_language — eye contact, posture, gesture frequency
  7. overall       — weighted average of all dimensions

Output dict shape:
{
    "overall":       float,  # 0-100
    "pace":          float,
    "clarity":       float,
    "confidence":    float,
    "engagement":    float,
    "structure":     float,
    "body_language": float,
    "breakdown":     dict,   # detailed sub-scores for each dimension
}
"""

from typing import Any


# ── Ideal ranges ─────────────────────────────────────────────────────────────
# Based on research on great speakers:
#   WPM:        120-160 is ideal (conversational but authoritative)
#   Filler rate: <2 per minute is excellent, >5 is poor
#   Pauses:     some pauses are good (shows confidence)
#   Pitch var:  >30 Hz std dev = expressive, <10 = monotone
#   Gestures:   20-80 per minute is natural

IDEAL_WPM_MIN   = 120
IDEAL_WPM_MAX   = 160
IDEAL_FILLER_RATE_GOOD = 2.0   # per minute — excellent
IDEAL_FILLER_RATE_OK   = 5.0   # per minute — acceptable
IDEAL_PITCH_VAR_MIN    = 30.0  # Hz std dev
IDEAL_GESTURE_MIN      = 20.0  # per minute
IDEAL_GESTURE_MAX      = 80.0  # per minute

# ── Dimension weights for overall score ──────────────────────────────────────
WEIGHTS = {
    "pace":          0.15,
    "clarity":       0.25,
    "confidence":    0.20,
    "engagement":    0.15,
    "structure":     0.15,
    "body_language": 0.10,
}


class ScoringEngine:

    def compute(
        self,
        audio: dict[str, Any],
        visual: dict[str, Any],
        nlp: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Main entry point.
        Takes outputs from AudioAnalyzer, VisualAnalyzer, NLPAnalyzer.
        Returns scores dict.
        """
        print("[ScoringEngine] Computing scores...")

        pace          = self._score_pace(audio)
        clarity       = self._score_clarity(audio, nlp)
        confidence    = self._score_confidence(audio, visual)
        engagement    = self._score_engagement(audio, visual, nlp)
        structure     = self._score_structure(nlp)
        body_language = self._score_body_language(visual)

        # Weighted overall
        overall = (
            pace          * WEIGHTS["pace"] +
            clarity       * WEIGHTS["clarity"] +
            confidence    * WEIGHTS["confidence"] +
            engagement    * WEIGHTS["engagement"] +
            structure     * WEIGHTS["structure"] +
            body_language * WEIGHTS["body_language"]
        )

        scores = {
            "overall":       round(overall, 1),
            "pace":          round(pace, 1),
            "clarity":       round(clarity, 1),
            "confidence":    round(confidence, 1),
            "engagement":    round(engagement, 1),
            "structure":     round(structure, 1),
            "body_language": round(body_language, 1),
            "breakdown":     self._breakdown(audio, visual, nlp),
        }

        print(
            f"[ScoringEngine] ✓ Overall: {scores['overall']}/100 | "
            f"Pace: {scores['pace']} | Clarity: {scores['clarity']} | "
            f"Confidence: {scores['confidence']} | Engagement: {scores['engagement']}"
        )
        return scores

    # ── Dimension scorers ────────────────────────────────────────────────────

    def _score_pace(self, audio: dict) -> float:
        """
        Score speaking pace.
        Ideal: 120-160 WPM
        Too fast (>180) or too slow (<100) both hurt score.
        Also rewards good pause usage.
        """
        wpm = audio.get("words_per_minute", 0)
        score = 50.0

        if wpm == 0:
            return 50.0

        # WPM scoring
        if IDEAL_WPM_MIN <= wpm <= IDEAL_WPM_MAX:
            score = 90.0
        elif wpm < IDEAL_WPM_MIN:
            # Too slow — linear drop below 120
            ratio = wpm / IDEAL_WPM_MIN
            score = 90.0 * ratio
        else:
            # Too fast — linear drop above 160
            over = wpm - IDEAL_WPM_MAX
            score = max(20, 90.0 - over * 0.5)

        # Pause bonus — deliberate pauses are good
        pause_count = audio.get("pause_count", 0)
        duration    = audio.get("duration_seconds", 1)
        pause_rate  = pause_count / (duration / 60)

        if 3 <= pause_rate <= 10:
            score = min(100, score + 5)   # good pause rhythm
        elif pause_rate > 15:
            score = max(0, score - 10)    # too many pauses = hesitant

        return round(min(100, max(0, score)), 1)

    def _score_clarity(self, audio: dict, nlp: dict) -> float:
        """
        Score speech clarity.
        Combines: filler word rate, sentence variety, NLP clarity score.
        """
        # Filler word score (40% of clarity)
        filler_rate = audio.get("filler_word_rate", 0)
        if filler_rate <= IDEAL_FILLER_RATE_GOOD:
            filler_score = 100.0
        elif filler_rate <= IDEAL_FILLER_RATE_OK:
            # Linear drop from 100 to 60 between 2 and 5 per min
            filler_score = 100 - (filler_rate - 2) * (40 / 3)
        else:
            # Linear drop from 60 to 0 above 5 per min
            filler_score = max(0, 60 - (filler_rate - 5) * 10)

        # Sentence variety score (20% of clarity)
        ss = nlp.get("sentence_structure", {})
        variety_score = ss.get("variety_score", 50)

        # NLP clarity from Claude (40% of clarity)
        nlp_clarity = nlp.get("clarity_score", 50)

        clarity = (
            filler_score  * 0.40 +
            variety_score * 0.20 +
            nlp_clarity   * 0.40
        )
        return round(min(100, max(0, clarity)), 1)

    def _score_confidence(self, audio: dict, visual: dict) -> float:
        """
        Score speaker confidence.
        Combines: volume variation, eye contact, posture.
        """
        # Volume variation — confident speakers have steady volume
        vol_var = audio.get("volume_variation", 0)
        if vol_var == 0:
            vol_score = 50.0
        elif vol_var < 0.01:
            vol_score = 60.0   # very flat = nervous monotone
        elif vol_var < 0.05:
            vol_score = 90.0   # good dynamic range
        else:
            vol_score = max(40, 90 - (vol_var - 0.05) * 500)

        # Eye contact (strong confidence signal)
        eye_score = visual.get("eye_contact_score", 50)

        # Posture
        posture_score = visual.get("posture_score", 50)

        confidence = (
            vol_score    * 0.30 +
            eye_score    * 0.40 +
            posture_score * 0.30
        )
        return round(min(100, max(0, confidence)), 1)

    def _score_engagement(
        self,
        audio: dict,
        visual: dict,
        nlp: dict,
    ) -> float:
        """
        Score audience engagement potential.
        Combines: pitch variation, gestures, persuasion, emotional arc.
        """
        # Pitch variation — expressive speakers vary their pitch
        pitch_var = audio.get("pitch_variation", 0)
        if pitch_var >= IDEAL_PITCH_VAR_MIN:
            pitch_score = 90.0
        elif pitch_var > 0:
            pitch_score = (pitch_var / IDEAL_PITCH_VAR_MIN) * 90
        else:
            pitch_score = 30.0

        # Gesture frequency
        gesture_freq = visual.get("gesture_frequency", 0)
        if IDEAL_GESTURE_MIN <= gesture_freq <= IDEAL_GESTURE_MAX:
            gesture_score = 90.0
        elif gesture_freq < IDEAL_GESTURE_MIN:
            gesture_score = max(30, (gesture_freq / IDEAL_GESTURE_MIN) * 90)
        else:
            # Too many gestures = distracting
            over = gesture_freq - IDEAL_GESTURE_MAX
            gesture_score = max(30, 90 - over * 0.3)

        # Persuasion score from Claude
        persuasion = nlp.get("persuasion_score", 50)

        # Emotional arc variety bonus
        arc = nlp.get("emotional_arc", [])
        tones = set(e.get("tone") for e in arc)
        arc_bonus = 10 if len(tones) > 1 else 0

        engagement = (
            pitch_score   * 0.30 +
            gesture_score * 0.25 +
            persuasion    * 0.35 +
            arc_bonus     * 0.10
        ) + arc_bonus * 0.1

        return round(min(100, max(0, engagement)), 1)

    def _score_structure(self, nlp: dict) -> float:
        """
        Score speech structure and storytelling.
        Combines: opening strength, closing strength, storytelling score.
        """
        opening      = nlp.get("opening_strength", 50)
        closing      = nlp.get("closing_strength", 50)
        storytelling = nlp.get("storytelling_score", 50)

        structure = (
            opening      * 0.30 +
            closing      * 0.30 +
            storytelling * 0.40
        )
        return round(min(100, max(0, structure)), 1)

    def _score_body_language(self, visual: dict) -> float:
        """
        Score body language.
        Combines: eye contact, posture, facial expressiveness.
        """
        eye_contact = visual.get("eye_contact_score", 50)
        posture     = visual.get("posture_score", 50)

        # Facial expression bonus — smiling is engaging
        exp = visual.get("facial_expression_data", {})
        smile_ratio = exp.get("smile_ratio", 0)
        expression_score = min(100, 50 + smile_ratio * 100)

        body = (
            eye_contact      * 0.40 +
            posture          * 0.40 +
            expression_score * 0.20
        )
        return round(min(100, max(0, body)), 1)

    # ── Breakdown ────────────────────────────────────────────────────────────

    def _breakdown(
        self,
        audio: dict,
        visual: dict,
        nlp: dict,
    ) -> dict:
        """
        Return detailed sub-scores so the frontend can show
        exactly what contributed to each dimension score.
        """
        return {
            "pace": {
                "words_per_minute": audio.get("words_per_minute"),
                "ideal_range":      f"{IDEAL_WPM_MIN}-{IDEAL_WPM_MAX} WPM",
                "pause_count":      audio.get("pause_count"),
            },
            "clarity": {
                "filler_word_rate": audio.get("filler_word_rate"),
                "filler_words":     audio.get("filler_words_detail"),
                "sentence_variety": nlp.get("sentence_structure", {}).get("variety_score"),
                "nlp_clarity":      nlp.get("clarity_score"),
            },
            "confidence": {
                "volume_variation": audio.get("volume_variation"),
                "eye_contact":      visual.get("eye_contact_score"),
                "posture":          visual.get("posture_score"),
            },
            "engagement": {
                "pitch_variation":  audio.get("pitch_variation"),
                "gesture_frequency": visual.get("gesture_frequency"),
                "persuasion":       nlp.get("persuasion_score"),
            },
            "structure": {
                "opening_strength": nlp.get("opening_strength"),
                "closing_strength": nlp.get("closing_strength"),
                "storytelling":     nlp.get("storytelling_score"),
            },
            "body_language": {
                "eye_contact":      visual.get("eye_contact_score"),
                "posture":          visual.get("posture_score"),
                "smile_ratio":      visual.get("facial_expression_data", {}).get("smile_ratio"),
            },
        }
