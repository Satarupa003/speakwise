"""
Test the CoachEngine — interactive chat session.

Usage:
    cd speakwise/backend
    python tests/test_coach_engine.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.coach_engine import CoachEngine


# Mock analysis object
class MockAnalysis:
    overall_score       = 61.0
    pace_score          = 52.0
    clarity_score       = 48.0
    confidence_score    = 72.0
    engagement_score    = 55.0
    structure_score     = 46.0
    body_language_score = 78.0
    words_per_minute    = 182.0
    filler_word_count   = 18
    filler_word_rate    = 6.5
    filler_words_detail = {"um": 8, "like": 6, "you know": 4}
    feedback_summary    = (
        "You show strong confidence and eye contact, but your pace "
        "is too fast and filler words are significantly reducing your clarity."
    )
    improvement_points  = [
        {"area": "pace",    "issue": "Speaking at 182 WPM, above the ideal 120-160 range."},
        {"area": "clarity", "issue": "Using 6.5 filler words per minute, well above the 2/min target."},
        {"area": "structure", "issue": "Opening and closing need stronger hooks."},
    ]
    transcript = (
        "Um, hi everyone, so today I'm going to, like, talk about "
        "the importance of, you know, communication in the workplace..."
    )


async def main():
    engine = CoachEngine()
    analysis = MockAnalysis()

    print("=" * 60)
    print("SPEAKWISE COACH — Interactive Test")
    print("=" * 60)
    print("Type your questions. Type 'quit' to exit.\n")

    # Run a few preset questions automatically first
    preset_questions = [
        "What's the most important thing I should work on?",
        "Give me a specific exercise to reduce my filler words",
        "Why is my pace score so low and how do I fix it?",
    ]

    for question in preset_questions:
        print(f"You: {question}")
        response = await engine.chat(question, analysis)
        print(f"\nCoach: {response.reply}")
        if response.suggestions:
            print(f"\nSuggested follow-ups:")
            for s in response.suggestions:
                print(f"  • {s}")
        print("\n" + "-" * 60 + "\n")

    # Interactive mode
    print("Now you can ask anything:\n")
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input or user_input.lower() in ["quit", "exit", "q"]:
                print("Ending session. Keep practicing!")
                break

            response = await engine.chat(user_input, analysis)
            print(f"\nCoach: {response.reply}")
            if response.suggestions:
                print(f"\nSuggested follow-ups:")
                for s in response.suggestions:
                    print(f"  • {s}")
            print()

        except KeyboardInterrupt:
            print("\nSession ended.")
            break


if __name__ == "__main__":
    asyncio.run(main())
