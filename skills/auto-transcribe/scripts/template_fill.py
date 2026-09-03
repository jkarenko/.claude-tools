#!/usr/bin/env python3
"""
AI-powered template extraction from transcripts.

Features:
- Fill templates with questions/topics from transcript content
- Support for various placeholder formats
- Live mode for continuous updates
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from utils.formats import Transcript, from_json


def parse_template(template_path: str) -> dict:
    """
    Parse a template file and extract fillable sections.

    Supports formats:
    - Q: What was discussed? -> Question format
    - ## Topic Name -> Section headers
    - {{PLACEHOLDER}} -> Mustache-style placeholders
    - - Topic: -> Bullet points with colons
    """
    template_path = Path(template_path)
    content = template_path.read_text()

    sections = []

    # Find Q: format questions
    for match in re.finditer(r"^Q:\s*(.+?)\s*$", content, re.MULTILINE):
        sections.append(
            {
                "type": "question",
                "text": match.group(1),
                "start": match.start(),
                "end": match.end(),
                "placeholder": match.group(0),
            }
        )

    # Find {{PLACEHOLDER}} format
    for match in re.finditer(r"\{\{([A-Z_]+)\}\}", content):
        sections.append(
            {
                "type": "placeholder",
                "text": match.group(1).replace("_", " ").title(),
                "start": match.start(),
                "end": match.end(),
                "placeholder": match.group(0),
            }
        )

    # Find "- Topic:" bullet points
    for match in re.finditer(r"^-\s+([^:]+):\s*$", content, re.MULTILINE):
        sections.append(
            {
                "type": "bullet",
                "text": match.group(1),
                "start": match.start(),
                "end": match.end(),
                "placeholder": match.group(0),
            }
        )

    # Find ## Section headers followed by empty content
    for match in re.finditer(r"^##\s+(.+?)\s*\n\s*\n", content, re.MULTILINE):
        sections.append(
            {
                "type": "section",
                "text": match.group(1),
                "start": match.start(),
                "end": match.end(),
                "placeholder": match.group(0),
            }
        )

    return {"content": content, "sections": sections, "path": str(template_path)}


def build_extraction_prompt(
    transcript_text: str,
    sections: list[dict],
    speakers: Optional[list[str]] = None,
) -> str:
    """
    Build a prompt for Claude to extract template answers.
    """
    section_list = "\n".join(
        f'{i+1}. [{s["type"]}] {s["text"]}' for i, s in enumerate(sections)
    )

    speaker_hint = ""
    if speakers:
        speaker_hint = f"\nSpeakers in the transcript: {', '.join(speakers)}"

    return f"""You are extracting information from a meeting transcript to fill a template.

For each section below, find the relevant information in the transcript and provide a concise answer.
{speaker_hint}

Template sections to fill:
{section_list}

Transcript:
---
{transcript_text}
---

Respond with a JSON array in this exact format:
[
  {{"section": 1, "answer": "Extracted answer here", "source": "Brief quote or timestamp reference", "confidence": "high/medium/low"}},
  ...
]

Guidelines:
- Be concise but complete
- If information is not found, set answer to "[Not discussed]"
- Include relevant speaker attributions when helpful
- For action items, list them clearly with owners if mentioned
- For decisions, state what was decided and by whom
"""


def extract_with_claude(
    transcript: Transcript,
    sections: list[dict],
    api_key: Optional[str] = None,
    model: str = "claude-sonnet-4-20250514",
) -> list[dict]:
    """
    Use Claude to extract template answers from transcript.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    # Build transcript text with timestamps and speakers
    lines = []
    for seg in transcript.segments:
        timestamp = f"[{int(seg.start // 3600):02d}:{int((seg.start % 3600) // 60):02d}:{int(seg.start % 60):02d}]"
        speaker = f"{seg.speaker}: " if seg.speaker else ""
        lines.append(f"{timestamp} {speaker}{seg.text}")

    transcript_text = "\n".join(lines)

    # Get unique speakers
    speakers = list(set(seg.speaker for seg in transcript.segments if seg.speaker))

    prompt = build_extraction_prompt(transcript_text, sections, speakers)

    response = client.messages.create(
        model=model,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    # Parse response
    try:
        response_text = response.content[0].text
        json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except (json.JSONDecodeError, IndexError) as e:
        print(f"Warning: Could not parse extraction response: {e}")

    return []


def fill_template(
    template_content: str,
    sections: list[dict],
    extractions: list[dict],
) -> str:
    """
    Fill template with extracted content.
    """
    filled = template_content

    # Sort by position in reverse to preserve indices
    paired = list(zip(sections, extractions))
    paired.sort(key=lambda x: x[0]["start"], reverse=True)

    for section, extraction in paired:
        answer = extraction.get("answer", "[Not extracted]")

        if section["type"] == "question":
            # Q: Question? -> Q: Question?\nA: Answer
            replacement = f'{section["placeholder"]}\nA: {answer}'
        elif section["type"] == "placeholder":
            # {{PLACEHOLDER}} -> Answer
            replacement = answer
        elif section["type"] == "bullet":
            # - Topic: -> - Topic: Answer
            replacement = f'- {section["text"]}: {answer}'
        elif section["type"] == "section":
            # ## Section\n\n -> ## Section\n\nContent
            replacement = f'{section["placeholder"]}{answer}\n\n'
        else:
            replacement = answer

        filled = filled[: section["start"]] + replacement + filled[section["end"] :]

    return filled


def fill_from_transcript(
    transcript_path: str,
    template_path: str,
    output_path: Optional[str] = None,
    model: str = "claude-sonnet-4-20250514",
) -> str:
    """
    Main template filling function.

    Args:
        transcript_path: Path to transcript JSON
        template_path: Path to template file
        output_path: Output path (default: {template}_filled.md)
        model: Claude model to use

    Returns:
        Filled template content
    """
    transcript_path = Path(transcript_path)
    template_path = Path(template_path)

    if not transcript_path.exists():
        raise FileNotFoundError(f"Transcript not found: {transcript_path}")
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    # Load transcript
    with open(transcript_path) as f:
        transcript = from_json(f.read())

    # Parse template
    template = parse_template(template_path)
    sections = template["sections"]

    if not sections:
        print("Warning: No fillable sections found in template.")
        return template["content"]

    print(f"Filling template: {template_path.name}")
    print(f"Found {len(sections)} sections to fill")

    # Extract answers
    extractions = extract_with_claude(transcript, sections, model=model)

    # Match extractions to sections
    if len(extractions) != len(sections):
        print(f"Warning: Got {len(extractions)} extractions for {len(sections)} sections")
        # Pad with empty extractions if needed
        while len(extractions) < len(sections):
            extractions.append({"answer": "[Extraction failed]"})

    # Fill template
    filled = fill_template(template["content"], sections, extractions)

    # Output
    if output_path:
        output_path = Path(output_path)
    else:
        output_path = template_path.with_stem(f"{template_path.stem}_filled")

    output_path.write_text(filled)
    print(f"Filled template saved to: {output_path}")

    return filled


def main():
    parser = argparse.ArgumentParser(
        description="Fill template from transcript using AI"
    )
    parser.add_argument("transcript", help="Path to transcript JSON file")
    parser.add_argument("template", help="Path to template file")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-20250514",
        help="Claude model for extraction",
    )

    args = parser.parse_args()

    fill_from_transcript(
        args.transcript,
        args.template,
        output_path=args.output,
        model=args.model,
    )


if __name__ == "__main__":
    main()
