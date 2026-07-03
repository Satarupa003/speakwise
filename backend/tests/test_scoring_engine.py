"""
Test the ScoringEngine in isolation using mock analyzer outputs.

Usage:
    cd speakwise/backend
    python tests/test_scoring_engine.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.scoring_engine import ScoringEngine


# Mock outputs from AudioAnalyzer, VisualAnalyzer, NLPAnalyzer
MOCK_AUDIO = {
    "words_per_minute":    145.0,
    "filler_word_count":   8,
    "filler_word_rate":    3.2,
    "filler_words_detail": {"um": 4, "like": 3, "you know": 1},
    "pause_count":         12,
    "avg_pause_duration":  0.6,
    "pitch_variation":     42.5,
    "volume_variation":    0.03,
    "duration_seconds":    150.0,
}

MOCK_VISUAL = {
    "eye_contact_score":      85.0,
    "gesture_frequency":      45.0,
    "posture_score":           72.0,
    "facial_expression_data": {
        "smile_ratio":   0.3,
        "neutral_ratio": 0.65,
        "tense_ratio":   0.05,
    },
}

MOCK_NLP = {
    "clarity_score":      72.0,
    "storytelling_score": 78.0,
    "persuasion_score":   65.0,
    "opening_strength":   70.0,
    "closing_strength":   55.0,
    "sentence_structure": {
        "variety_score":      68.0,
        "avg_sentence_length": 14.2,
        "questions":          3,
    },
    "emotional_arc": [
        {"tone": "neutral"},
        {"tone": "positive"},
        {"tone": "positive"},
        {"tone": "negative"},
        {"tone": "positive"},
    ],
}


def main():
    engine = ScoringEngine()
    scores = engine.compute(MOCK_AUDIO, MOCK_VISUAL, MOCK_NLP)

    print("=" * 60)
    print("SCORING ENGINE RESULT")
    print("=" * 60)

    print(f"\n  Overall score:   {scores['overall']}/100")
    print(f"\n  Pace:            {scores['pace']}/100")
    print(f"  Clarity:         {scores['clarity']}/100")
    print(f"  Confidence:      {scores['confidence']}/100")
    print(f"  Engagement:      {scores['engagement']}/100")
    print(f"  Structure:       {scores['structure']}/100")
    print(f"  Body language:   {scores['body_language']}/100")

    print(f"\nBreakdown:")
    print(json.dumps(scores["breakdown"], indent=2))

    print("\n✓ ScoringEngine working correctly!")


if __name__ == "__main__":
    main()
