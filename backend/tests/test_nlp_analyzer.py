"""
Test the NLPAnalyzer in isolation.

Usage:
    cd speakwise/backend
    python tests/test_nlp_analyzer.py
    python tests/test_nlp_analyzer.py path/to/transcript.txt
"""

import asyncio
import sys
import json
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Sample speech transcript for testing
SAMPLE_TRANSCRIPT = """
Imagine waking up one day and realizing that everything you thought you knew
about success was wrong. That happened to me three years ago.

I had the job, the salary, the title. But I was miserable. And I couldn't
figure out why. You know, I kept telling myself it would get better. Basically
I was lying to myself every single day.

Then I met someone who changed everything. She said something I'll never forget.
She said: the problem isn't where you are. The problem is that you've never
decided where you want to go.

That one sentence transformed my life. I quit my job, started my own company,
and within two years we had grown to a team of fifty people serving clients
across twenty countries.

Here's what I learned: clarity is everything. When you know exactly what you
want, the universe has a funny way of helping you get there. But you have to
be specific. You have to be bold. And most importantly, you have to start today.

So I want to ask you one question before I leave you today. What is the one
thing you've been putting off that could change everything for you? Whatever
that answer is — start tomorrow morning. Not next week. Tomorrow.

Thank you.
"""


async def main():
    # Load transcript from file if provided
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.exists(path):
            with open(path) as f:
                transcript = f.read()
            print(f"Using transcript from: {path}")
        else:
            print(f"File not found: {path}, using sample transcript")
            transcript = SAMPLE_TRANSCRIPT
    else:
        print("No file provided — using sample transcript\n")
        transcript = SAMPLE_TRANSCRIPT

    from app.services.nlp_analyzer import NLPAnalyzer
    analyzer = NLPAnalyzer()

    print("Analyzing transcript...\n")

    try:
        result = await analyzer.analyze(transcript)

        print("=" * 60)
        print("NLP ANALYSIS RESULT")
        print("=" * 60)

        print(f"\nAI Scores (Claude API):")
        print(f"  Storytelling:  {result['storytelling_score']:.0f}/100")
        print(f"  Clarity:       {result['clarity_score']:.0f}/100")
        print(f"  Persuasion:    {result['persuasion_score']:.0f}/100")

        print(f"\nKey themes: {', '.join(result['key_themes'])}")

        print(f"\nOpening strength: {result['opening_strength']}/100")
        print(f"Closing strength:  {result['closing_strength']}/100")

        ss = result['sentence_structure']
        print(f"\nSentence structure:")
        print(f"  Total sentences:    {ss.get('total_sentences')}")
        print(f"  Avg length:         {ss.get('avg_sentence_length')} words")
        print(f"  Variety score:      {ss.get('variety_score')}/100")
        print(f"  Questions asked:    {ss.get('questions')}")

        vocab = result['vocabulary']
        print(f"\nVocabulary:")
        print(f"  Total words:   {vocab.get('total_words')}")
        print(f"  Unique words:  {vocab.get('unique_words')}")
        print(f"  Richness (TTR): {vocab.get('ttr')} ({vocab.get('ttr_score')}/100)")

        fp = result['filler_phrases']
        print(f"\nFiller phrases found: {fp['total_count']}")
        if fp['phrases_found']:
            for phrase, count in fp['phrases_found'].items():
                print(f"  '{phrase}': {count}x")

        print(f"\nAI Feedback:")
        print(f"  {result['nlp_feedback']}")

        print(f"\nStructure feedback:")
        print(f"  {result['structure_feedback']}")

        print(f"\nStrongest moment: {result['strongest_moment']}")
        print(f"Weakest moment:   {result['weakest_moment']}")

        print(f"\nEmotional arc ({len(result['emotional_arc'])} segments):")
        for entry in result['emotional_arc'][:5]:
            print(f"  [{entry['start']}s] {entry['tone']} "
                  f"(score: {entry['sentiment_score']})")

        # Save result
        out_file = "nlp_analysis_result.json"
        with open(out_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nFull result saved to: {out_file}")
        print("\n✓ NLPAnalyzer working correctly!")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
