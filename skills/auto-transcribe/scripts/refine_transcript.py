#!/usr/bin/env python3
"""
Context-aware transcript refinement.

Second-pass processing that uses Claude to:
- Resolve [word?] uncertain annotations
- Fill in [inaudible] sections where possible
- Improve overall accuracy using context
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from utils.config import load_vocabulary
from utils.formats import Transcript, Segment, from_json, to_json, export_transcript


def extract_uncertain_sections(transcript: Transcript) -> list[dict]:
    """
    Extract sections with uncertainty markers for refinement.

    Returns list of:
    - segment index
    - uncertain word/phrase
    - surrounding context
    """
    uncertain = []
    pattern = r"\[([^\]]+\?|\binaudible\b)\]"

    for i, seg in enumerate(transcript.segments):
        matches = list(re.finditer(pattern, seg.text))
        for match in matches:
            # Get context: previous and next segments
            context_before = ""
            context_after = ""

            if i > 0:
                context_before = transcript.segments[i - 1].text
            if i < len(transcript.segments) - 1:
                context_after = transcript.segments[i + 1].text

            uncertain.append(
                {
                    "segment_index": i,
                    "match_start": match.start(),
                    "match_end": match.end(),
                    "uncertain_text": match.group(1),
                    "full_segment": seg.text,
                    "context_before": context_before,
                    "context_after": context_after,
                    "speaker": seg.speaker,
                }
            )

    return uncertain


def build_refinement_prompt(
    uncertain_sections: list[dict],
    vocabulary: list[str],
    overall_context: str = "",
) -> str:
    """
    Build a prompt for Claude to refine uncertain sections.
    """
    vocab_hint = ""
    if vocabulary:
        vocab_hint = f"\n\nDomain vocabulary that may appear: {', '.join(vocabulary[:30])}"

    sections_text = []
    for i, section in enumerate(uncertain_sections):
        sections_text.append(
            f"""
Section {i + 1}:
- Uncertain: "{section['uncertain_text']}"
- In context: "...{section['context_before'][-50:]} {section['full_segment']} {section['context_after'][:50]}..."
- Speaker: {section.get('speaker', 'Unknown')}
"""
        )

    return f"""You are refining a transcript with uncertain sections.

For each section below, determine the most likely word or phrase based on:
1. The surrounding context
2. What makes grammatical sense
3. Common speech patterns
4. The domain vocabulary provided

{overall_context}
{vocab_hint}

Uncertain sections to refine:
{''.join(sections_text)}

For each section, respond with a JSON array in this exact format:
[
  {{"section": 1, "original": "word?", "refined": "word", "confidence": "high/medium/low", "reasoning": "brief explanation"}},
  ...
]

If you cannot determine a reasonable replacement for an [inaudible] section, keep it as "[inaudible]".
For uncertain words like "[word?]", select the most likely interpretation or keep the word without the question mark.
"""


def apply_refinements(transcript: Transcript, refinements: list[dict]) -> Transcript:
    """
    Apply refinement suggestions to transcript.

    Args:
        transcript: Original transcript
        refinements: List of refinement suggestions from Claude

    Returns:
        Refined transcript
    """
    # Group refinements by segment index
    by_segment = {}
    for ref in refinements:
        seg_idx = ref.get("segment_index", ref.get("section", 1) - 1)
        if seg_idx not in by_segment:
            by_segment[seg_idx] = []
        by_segment[seg_idx].append(ref)

    # Apply refinements (in reverse order to preserve indices)
    for seg_idx in sorted(by_segment.keys(), reverse=True):
        if seg_idx >= len(transcript.segments):
            continue

        seg = transcript.segments[seg_idx]
        text = seg.text

        # Sort refinements by position in reverse
        segment_refs = sorted(
            by_segment[seg_idx], key=lambda x: x.get("match_start", 0), reverse=True
        )

        for ref in segment_refs:
            original = ref.get("original", "")
            refined = ref.get("refined", original)

            if original and refined:
                # Replace [original?] or [inaudible] with refined text
                pattern = rf"\[{re.escape(original)}\]"
                text = re.sub(pattern, refined, text, count=1)

        transcript.segments[seg_idx].text = text

    return transcript


def refine_with_claude(
    transcript: Transcript,
    api_key: Optional[str] = None,
    model: str = "claude-sonnet-4-20250514",
) -> Transcript:
    """
    Use Claude API to refine uncertain sections.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    # Extract uncertain sections
    uncertain = extract_uncertain_sections(transcript)

    if not uncertain:
        print("No uncertain sections found - transcript is clean.")
        return transcript

    print(f"Found {len(uncertain)} uncertain sections to refine.")

    # Get vocabulary
    vocabulary = load_vocabulary()

    # Build overall context from first few segments
    context_segments = transcript.segments[:10]
    overall_context = "Overall topic: " + " ".join(
        seg.text[:100] for seg in context_segments
    )[:500]

    # Process in batches (max 20 at a time)
    batch_size = 20
    all_refinements = []

    for i in range(0, len(uncertain), batch_size):
        batch = uncertain[i : i + batch_size]
        prompt = build_refinement_prompt(batch, vocabulary, overall_context)

        print(f"Processing batch {i // batch_size + 1}...")

        response = client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse response
        try:
            response_text = response.content[0].text
            # Extract JSON from response
            json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
            if json_match:
                batch_refinements = json.loads(json_match.group())
                # Add segment indices
                for j, ref in enumerate(batch_refinements):
                    ref["segment_index"] = batch[j]["segment_index"]
                    ref["match_start"] = batch[j]["match_start"]
                all_refinements.extend(batch_refinements)
        except (json.JSONDecodeError, IndexError) as e:
            print(f"Warning: Could not parse refinements for batch: {e}")

    # Apply all refinements
    if all_refinements:
        print(f"Applying {len(all_refinements)} refinements...")
        transcript = apply_refinements(transcript, all_refinements)

    return transcript


def refine_transcript(
    input_path: str,
    output_path: Optional[str] = None,
    use_api: bool = True,
    model: str = "claude-sonnet-4-20250514",
) -> Transcript:
    """
    Main refinement function.

    Args:
        input_path: Path to transcript JSON
        output_path: Output path (default: {name}_refined.json)
        use_api: Use Claude API for refinement
        model: Claude model to use

    Returns:
        Refined transcript
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Transcript not found: {input_path}")

    # Load transcript
    with open(input_path) as f:
        transcript = from_json(f.read())

    print(f"Refining transcript: {input_path.name}")
    print(f"Segments: {len(transcript.segments)}")

    if use_api:
        transcript = refine_with_claude(transcript, model=model)
    else:
        # Basic rule-based refinement (remove question marks from high-confidence words)
        for seg in transcript.segments:
            # Simple cleanup: remove ? from words that are likely correct
            seg.text = re.sub(r"\[(\w+)\?\]", r"\1", seg.text)

    # Output
    if output_path:
        output_path = Path(output_path)
    else:
        output_path = input_path.with_stem(f"{input_path.stem}_refined")

    export_transcript(transcript, output_path, "json")
    print(f"Refined transcript saved to: {output_path}")

    # Also save markdown version
    md_path = output_path.with_suffix(".md")
    export_transcript(transcript, md_path, "markdown")
    print(f"Markdown version saved to: {md_path}")

    return transcript


def main():
    parser = argparse.ArgumentParser(
        description="Refine transcript using context-aware AI"
    )
    parser.add_argument("transcript", help="Path to transcript JSON file")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument(
        "--no-api", action="store_true", help="Skip API refinement (basic rules only)"
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-20250514",
        help="Claude model for refinement",
    )

    args = parser.parse_args()

    refine_transcript(
        args.transcript,
        output_path=args.output,
        use_api=not args.no_api,
        model=args.model,
    )


if __name__ == "__main__":
    main()
