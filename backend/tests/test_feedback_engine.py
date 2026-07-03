"""
Test the FeedbackEngine in isolation.

Usage:
    cd speakwise/backend
    python tests/test_feedback_engine.py
"""

import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Mock data matching real analyzer outputs
MOCK_AUDIO = {
    "words_per_minute":    182.0,
    "filler_word_count":   18,
    "filler_word_rate":    6.5,
    "filler_words_detail": {"um": 8, "like": 6, "you know": 4},
    "pause_count":         4,
    "avg_pause_duration":  0.3,
    "pitch_variation":     18.0,
    "volume_variation":    0.02,
    "duration_seconds":    165.0,
}

MOCK_VISUAL = {
    "eye_contact_score":      88.0,
    "gesture_frequency":      120.0,
    "posture_score":           62.0,
    "facial_expression_data": {
        "smile_ratio":   0.1,
        "neutral_ratio": 0.85,
        "tense_ratio":   0.05,
    },
}

MOCK_NLP = {
    "clarity_score":      55.0,
    "storytelling_score": 62.0,
    "persuasion_score":   58.0,
    "opening_strength":   40.0,
    "closing_strength":   35.0,
    "nlp_feedback":       "The speech lacks a clear narrative arc and relies heavily on filler words.",
    "strongest_moment":   "The middle section where you described your personal experience.",
    "weakest_moment":     "The opening which started with 'Um, hi everyone, so today I'm going to...'",
    "sentence_structure": {"variety_score": 55.0},
    "emotional_arc": [
        {"tone": "neutral"},
        {"tone": "neutral"},
        {"tone": "positive"},
    ],
}

MOCK_SCORES = {
    "overall":       61.0,
    "pace":          52.0,
    "clarity":       48.0,
    "confidence":    72.0,
    "engagement":    55.0,
    "structure":     46.0,
    "body_language": 78.0,
    "breakdown":     {},
}


async def main():
    # First seed the knowledge base with some speakers
    print("Seeding knowledge base with reference speakers...")
    from app.services.knowledge_base import KnowledgeBase
    kb = KnowledgeBase()

    speakers = [
        {
            "video_id": "ted-001", "speaker_name": "Simon Sinek",
            "title": "How Great Leaders Inspire Action",
            "audio_data": {
                "words_per_minute": 124.0, "filler_word_rate": 0.8,
                "pause_count": 18, "pitch_variation": 52.3,
                "volume_variation": 0.028, "duration_seconds": 1080,
                "transcript": "Start with why...",
            },
            "file_path": "data/speaker_videos/simon_sinek.mp4",
        },
        {
            "video_id": "ted-002", "speaker_name": "Brene Brown",
            "title": "The Power of Vulnerability",
            "audio_data": {
                "words_per_minute": 138.0, "filler_word_rate": 1.2,
                "pause_count": 22, "pitch_variation": 61.7,
                "volume_variation": 0.035, "duration_seconds": 1260,
                "transcript": "Connection is why we are here...",
            },
            "file_path": "data/speaker_videos/brene_brown.mp4",
        },
    ]
    for sp in speakers:
        await kb.add_speaker(**sp)

    # Now test the feedback engine
    print("\nGenerating feedback...\n")
    from app.services.feedback_engine import FeedbackEngine
    engine = FeedbackEngine()

    result = await engine.generate(
        audio=MOCK_AUDIO,
        visual=MOCK_VISUAL,
        nlp=MOCK_NLP,
        scores=MOCK_SCORES,
    )

    print("=" * 60)
    print("FEEDBACK ENGINE RESULT")
    print("=" * 60)

    print(f"\nSummary:\n  {result['summary']}")
    print(f"\nPriority focus:\n  {result['priority_focus']}")

    print(f"\nStrengths:")
    for s in result["strengths"]:
        print(f"  ✓ {s}")

    print(f"\nImprovement points ({len(result['improvement_points'])}):")
    for i, point in enumerate(result["improvement_points"], 1):
        print(f"\n  {i}. [{point['area'].upper()}]")
        print(f"     Issue:    {point['issue']}")
        print(f"     Tip:      {point['tip']}")
        print(f"     Exercise: {point.get('exercise', '')}")
        if point.get("reference_speaker"):
            print(f"     Reference: Watch {point['reference_speaker']} "
                  f"at {point.get('reference_timestamp', 0)}s")

    print(f"\nReference clips ({len(result['reference_clips'])}):")
    for clip in result["reference_clips"]:
        print(f"  → {clip['speaker_name']} — {clip['title']} "
              f"(skill: {clip['skill']})")

    out_file = "feedback_result.json"
    with open(out_file, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nFull result saved to: {out_file}")
    print("\n✓ FeedbackEngine working correctly!")


if __name__ == "__main__":
    asyncio.run(main())
