"""
Test the KnowledgeBase in isolation.

Usage:
    cd speakwise/backend
    python tests/test_knowledge_base.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.knowledge_base import KnowledgeBase


# Mock audio data for 3 famous speakers
SPEAKERS = [
    {
        "video_id":    "ted-001",
        "speaker_name": "Simon Sinek",
        "title":       "How Great Leaders Inspire Action",
        "audio_data": {
            "words_per_minute":  124.0,
            "filler_word_rate":  0.8,
            "pause_count":       18,
            "pitch_variation":   52.3,
            "volume_variation":  0.028,
            "duration_seconds":  1080,
            "transcript":        "Start with why. People don't buy what you do, they buy why you do it...",
        },
        "file_path": "data/speaker_videos/simon_sinek.mp4",
    },
    {
        "video_id":    "ted-002",
        "speaker_name": "Brene Brown",
        "title":       "The Power of Vulnerability",
        "audio_data": {
            "words_per_minute":  138.0,
            "filler_word_rate":  1.2,
            "pause_count":       22,
            "pitch_variation":   61.7,
            "volume_variation":  0.035,
            "duration_seconds":  1260,
            "transcript":        "Connection is why we are here. It is what gives purpose and meaning to our lives...",
        },
        "file_path": "data/speaker_videos/brene_brown.mp4",
    },
    {
        "video_id":    "ted-003",
        "speaker_name": "Ken Robinson",
        "title":       "Do Schools Kill Creativity",
        "audio_data": {
            "words_per_minute":  156.0,
            "filler_word_rate":  0.5,
            "pause_count":       15,
            "pitch_variation":   44.2,
            "volume_variation":  0.031,
            "duration_seconds":  1140,
            "transcript":        "Creativity is as important in education as literacy and we should treat it with the same status...",
        },
        "file_path": "data/speaker_videos/ken_robinson.mp4",
    },
]


async def main():
    kb = KnowledgeBase()

    print("=" * 60)
    print("KNOWLEDGE BASE TEST")
    print("=" * 60)

    # Step 1: Add speakers
    print("\n1. Adding great speakers to knowledge base...")
    for sp in SPEAKERS:
        await kb.add_speaker(
            video_id=sp["video_id"],
            speaker_name=sp["speaker_name"],
            title=sp["title"],
            audio_data=sp["audio_data"],
            file_path=sp["file_path"],
        )

    print(f"\nTotal speakers in KB: {kb.count()}")

    # Step 2: Find similar speakers to a user with specific metrics
    print("\n2. Finding similar speakers for a user who speaks too fast...")
    similar = await kb.find_similar_speakers(
        target_metrics={
            "words_per_minute":  185.0,   # too fast
            "filler_word_rate":  4.5,     # too many fillers
            "pitch_variation":   20.0,    # monotone
            "volume_variation":  0.02,
            "pause_count":       3,
        },
        n_results=2,
    )
    for sp in similar:
        print(f"  → {sp['speaker_name']} — {sp['title']} "
              f"(similarity: {sp['similarity']})")

    # Step 3: Find speakers by skill
    print("\n3. Finding best speakers for 'engagement' skill...")
    by_skill = await kb.find_by_skill("engagement", n_results=2)
    for sp in by_skill:
        print(f"  → {sp['speaker_name']} — {sp['title']}")
        print(f"     Reason: {sp['reason']}")

    # Step 4: List all
    print("\n4. All speakers in knowledge base:")
    all_speakers = await kb.get_all_speakers()
    for sp in all_speakers:
        print(f"  • {sp['speaker_name']} — {sp['title']} "
              f"({sp['duration']:.0f}s)")

    print("\n✓ KnowledgeBase working correctly!")


if __name__ == "__main__":
    asyncio.run(main())
