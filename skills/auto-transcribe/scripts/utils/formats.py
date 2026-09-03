"""Output format handlers for transcripts."""

import json
import re
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Optional


@dataclass
class Segment:
    """A transcript segment with timing and speaker info."""

    start: float  # Start time in seconds
    end: float  # End time in seconds
    text: str
    speaker: Optional[str] = None
    confidence: Optional[float] = None
    words: list[dict] = field(default_factory=list)  # Word-level data


@dataclass
class Transcript:
    """Full transcript with metadata."""

    segments: list[Segment]
    language: Optional[str] = None
    duration: Optional[float] = None
    source_file: Optional[str] = None
    confidence_report: Optional[dict] = None


def format_timestamp(seconds: float, fmt: str = "hh:mm:ss") -> str:
    """
    Format seconds as timestamp string.

    Formats:
        hh:mm:ss - 01:23:45
        mm:ss - 23:45
        srt - 00:01:23,456
        vtt - 00:01:23.456
    """
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)

    if fmt == "hh:mm:ss":
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    elif fmt == "mm:ss":
        return f"{minutes:02d}:{secs:02d}"
    elif fmt == "srt":
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    elif fmt == "vtt":
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    else:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def to_markdown(transcript: Transcript, timestamp_fmt: str = "hh:mm:ss") -> str:
    """Export transcript to markdown format."""
    lines = []

    if transcript.source_file:
        lines.append(f"# Transcript: {Path(transcript.source_file).name}\n")
    else:
        lines.append("# Transcript\n")

    if transcript.language:
        lines.append(f"**Language:** {transcript.language}\n")

    if transcript.duration:
        lines.append(f"**Duration:** {format_timestamp(transcript.duration, timestamp_fmt)}\n")

    lines.append("")

    current_speaker = None
    for seg in transcript.segments:
        timestamp = format_timestamp(seg.start, timestamp_fmt)

        if seg.speaker and seg.speaker != current_speaker:
            lines.append(f"\n### {seg.speaker}\n")
            current_speaker = seg.speaker

        lines.append(f"**[{timestamp}]** {seg.text}\n")

    # Confidence report
    if transcript.confidence_report:
        lines.append("\n---\n## Confidence Report\n")
        report = transcript.confidence_report
        if "overall" in report:
            lines.append(f"- **Overall confidence:** {report['overall']:.1%}")
        if "low_confidence_count" in report:
            lines.append(f"- **Low confidence segments:** {report['low_confidence_count']}")
        if "inaudible_count" in report:
            lines.append(f"- **Inaudible sections:** {report['inaudible_count']}")

    return "\n".join(lines)


def to_srt(transcript: Transcript) -> str:
    """Export transcript to SRT subtitle format."""
    lines = []

    for i, seg in enumerate(transcript.segments, 1):
        start = format_timestamp(seg.start, "srt")
        end = format_timestamp(seg.end, "srt")

        text = seg.text
        if seg.speaker:
            text = f"[{seg.speaker}] {text}"

        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")

    return "\n".join(lines)


def to_vtt(transcript: Transcript) -> str:
    """Export transcript to WebVTT format."""
    lines = ["WEBVTT", ""]

    for seg in transcript.segments:
        start = format_timestamp(seg.start, "vtt")
        end = format_timestamp(seg.end, "vtt")

        text = seg.text
        if seg.speaker:
            text = f"<v {seg.speaker}>{text}"

        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")

    return "\n".join(lines)


def to_json(transcript: Transcript) -> str:
    """Export transcript to JSON format with full metadata."""
    data = {
        "language": transcript.language,
        "duration": transcript.duration,
        "source_file": transcript.source_file,
        "segments": [
            {
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
                "speaker": seg.speaker,
                "confidence": seg.confidence,
                "words": seg.words,
            }
            for seg in transcript.segments
        ],
        "confidence_report": transcript.confidence_report,
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def from_json(json_str: str) -> Transcript:
    """Load transcript from JSON string."""
    data = json.loads(json_str)
    segments = [
        Segment(
            start=s["start"],
            end=s["end"],
            text=s["text"],
            speaker=s.get("speaker"),
            confidence=s.get("confidence"),
            words=s.get("words", []),
        )
        for s in data["segments"]
    ]
    return Transcript(
        segments=segments,
        language=data.get("language"),
        duration=data.get("duration"),
        source_file=data.get("source_file"),
        confidence_report=data.get("confidence_report"),
    )


def export_transcript(
    transcript: Transcript, output_path: str | Path, fmt: str = "markdown"
) -> Path:
    """
    Export transcript to specified format.

    Args:
        transcript: Transcript object
        output_path: Output file path
        fmt: Format - 'markdown', 'srt', 'vtt', or 'json'

    Returns:
        Path to exported file
    """
    output_path = Path(output_path)
    formatters = {
        "markdown": (to_markdown, ".md"),
        "md": (to_markdown, ".md"),
        "srt": (to_srt, ".srt"),
        "vtt": (to_vtt, ".vtt"),
        "json": (to_json, ".json"),
    }

    if fmt not in formatters:
        raise ValueError(f"Unknown format: {fmt}. Use: {list(formatters.keys())}")

    formatter, ext = formatters[fmt]

    # Adjust extension if needed
    if output_path.suffix != ext:
        output_path = output_path.with_suffix(ext)

    content = formatter(transcript)
    output_path.write_text(content, encoding="utf-8")

    return output_path
