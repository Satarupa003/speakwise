"""
Test the VisualAnalyzer in isolation.

Usage:
    cd speakwise/backend
    python tests/test_visual_analyzer.py path/to/your/video.mp4
"""

import asyncio
import sys
import json
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.visual_analyzer import VisualAnalyzer


async def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/test_visual_analyzer.py path/to/video.mp4")
        print("\nNo video provided. Please pass a video file path.")
        sys.exit(1)

    video_path = sys.argv[1]
    if not os.path.exists(video_path):
        print(f"File not found: {video_path}")
        sys.exit(1)

    print(f"\nAnalyzing: {video_path}\n")

    analyzer = VisualAnalyzer()

    try:
        result = await analyzer.analyze(video_path)

        print("=" * 60)
        print("VISUAL ANALYSIS RESULT")
        print("=" * 60)

        print(f"\nScores:")
        print(f"  Eye contact:       {result['eye_contact_score']}/100")
        print(f"  Posture:           {result['posture_score']}/100")
        print(f"  Gesture frequency: {result['gesture_frequency']} moves/min")

        print(f"\nFacial expressions:")
        exp = result['facial_expression_data']
        print(f"  Smiling:  {exp['smile_ratio']*100:.0f}% of time")
        print(f"  Neutral:  {exp['neutral_ratio']*100:.0f}% of time")
        print(f"  Tense:    {exp['tense_ratio']*100:.0f}% of time")

        print(f"\nProcessing stats:")
        print(f"  Total frames:    {result['frame_count']}")
        print(f"  Analyzed frames: {result['analyzed_frames']}")
        print(f"  Duration:        {result['duration_seconds']}s")

        print(f"\nEye contact timeline (first 5):")
        for entry in result['eye_contact_timeline'][:5]:
            status = "👁 Looking at camera" if entry['looking_at_camera'] else "👀 Looking away"
            print(f"  {entry['time']}s — {status}")

        print(f"\nPosture timeline (first 5):")
        for entry in result['posture_timeline'][:5]:
            print(f"  {entry['time']}s — score: {entry['posture_score']}")

        # Save full result
        out_file = "visual_analysis_result.json"
        with open(out_file, "w") as f:
            json.dump(result, f, indent=2, default=lambda x: bool(x) if hasattr(x, 'item') else str(x))
        print(f"\nFull result saved to: {out_file}")
        print("\n✓ VisualAnalyzer working correctly!")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
