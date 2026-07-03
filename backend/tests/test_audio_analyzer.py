"""
Test the AudioAnalyzer in isolation.

Usage:
    cd speakwise/backend
    python tests/test_audio_analyzer.py path/to/your/video.mp4

If you don't have a video handy, it will generate a short silent test WAV.
"""

import asyncio
import sys
import json
import os
import wave
import struct

# Make sure the app package is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.audio_analyzer import AudioAnalyzer


def create_test_wav(out_path: str, duration_seconds: float = 3.0):
    """Create a minimal valid WAV file for testing (silence)."""
    sample_rate = 16000
    num_samples = int(sample_rate * duration_seconds)
    with wave.open(out_path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(struct.pack("<" + "h" * num_samples, *([0] * num_samples)))
    print(f"Created test WAV: {out_path}")


async def main():
    analyzer = AudioAnalyzer()

    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        print(f"\nAnalyzing: {video_path}\n")
    else:
        # Create a silent test WAV (Whisper will return empty transcript, but
        # all the audio metrics will still compute correctly)
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        create_test_wav(tmp.name, duration_seconds=5.0)
        video_path = tmp.name
        print(f"\nNo video provided — using silent test WAV: {video_path}\n")

    try:
        result = await analyzer.analyze(video_path)

        print("=" * 60)
        print("AUDIO ANALYSIS RESULT")
        print("=" * 60)

        print(f"\nTranscript:\n  {result['transcript'] or '(empty — silent file)'}")

        print(f"\nPace:")
        print(f"  Duration:         {result['duration_seconds']}s")
        print(f"  Word count:       {result['word_count']}")
        print(f"  Words per minute: {result['words_per_minute']}")

        print(f"\nFiller words:")
        print(f"  Total count:      {result['filler_word_count']}")
        print(f"  Rate (per min):   {result['filler_word_rate']}")
        print(f"  Breakdown:        {result['filler_words_detail']}")
        if result['filler_instances']:
            print(f"  First 3 instances:")
            for inst in result['filler_instances'][:3]:
                print(f"    '{inst['word']}' at {inst['start']}s–{inst['end']}s")

        print(f"\nPauses:")
        print(f"  Total pauses:     {result['pause_count']}")
        print(f"  Avg duration:     {result['avg_pause_duration']}s")
        print(f"  Long pauses:      {len(result['long_pauses'])}")

        print(f"\nAudio features:")
        print(f"  Pitch variation:  {result['pitch_variation']} Hz std dev")
        print(f"  Volume variation: {result['volume_variation']} RMS std dev")

        print(f"\nSegments ({len(result['segments'])} total):")
        for seg in result['segments'][:3]:
            print(f"  [{seg['start']}s → {seg['end']}s] {seg['text']}")
        if len(result['segments']) > 3:
            print(f"  ... and {len(result['segments']) - 3} more")

        print("\n✓ AudioAnalyzer working correctly!")

        # Optionally save full result to JSON
        out_file = "audio_analysis_result.json"
        with open(out_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Full result saved to: {out_file}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
