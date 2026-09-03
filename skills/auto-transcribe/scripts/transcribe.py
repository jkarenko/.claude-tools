#!/usr/bin/env python3
"""
Core transcription engine with confidence scoring.

Uses mlx-whisper for Apple Silicon optimization with word-level confidence.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

import numpy as np

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.audio import load_audio, get_audio_info
from utils.config import load_settings, load_vocabulary
from utils.formats import Segment, Transcript, export_transcript, to_markdown


def transcribe_with_mlx(
    audio_path: str,
    model_name: str = "mlx-community/whisper-large-v3-mlx",
    language: str = "auto",
    vocab_hints: Optional[list[str]] = None,
) -> dict:
    """
    Transcribe audio using mlx-whisper with word-level timestamps.

    Returns raw transcription result with segments and word data.
    """
    import mlx_whisper

    # Build initial prompt from vocabulary hints
    initial_prompt = None
    if vocab_hints:
        # Use vocabulary as initial prompt to bias recognition
        initial_prompt = ", ".join(vocab_hints[:50])  # Limit to avoid token overflow

    # Transcribe with word timestamps
    result = mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo=model_name,
        language=None if language == "auto" else language,
        word_timestamps=True,
        initial_prompt=initial_prompt,
    )

    return result


def transcribe_with_openai(
    audio_path: str,
    language: str = "auto",
) -> dict:
    """
    Fallback transcription using OpenAI Whisper API.
    """
    import openai

    client = openai.OpenAI()

    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"],
            language=None if language == "auto" else language,
        )

    # Convert to consistent format
    result = {
        "text": response.text,
        "language": response.language,
        "segments": [],
    }

    for seg in response.segments:
        segment_data = {
            "start": seg.start,
            "end": seg.end,
            "text": seg.text,
            "words": [],
        }
        # OpenAI doesn't provide per-word confidence, estimate from segment
        if hasattr(seg, "words"):
            for w in seg.words:
                segment_data["words"].append(
                    {
                        "word": w.word,
                        "start": w.start,
                        "end": w.end,
                        "probability": 0.8,  # Default confidence
                    }
                )
        result["segments"].append(segment_data)

    return result


def annotate_confidence(
    segments: list[dict],
    high_threshold: float = 0.7,
    low_threshold: float = 0.4,
) -> tuple[list[Segment], dict]:
    """
    Process segments and add confidence annotations.

    Words with confidence:
    - >= high_threshold: Normal output
    - between thresholds: Annotate as [word1/word2]
    - < low_threshold: Mark as [inaudible]

    Returns:
        Tuple of (annotated segments, confidence report)
    """
    processed_segments = []
    total_words = 0
    low_confidence_words = 0
    inaudible_words = 0
    confidence_sum = 0

    for seg in segments:
        words = seg.get("words", [])
        if not words:
            # No word-level data, use segment text as-is
            processed_segments.append(
                Segment(
                    start=seg["start"],
                    end=seg["end"],
                    text=seg.get("text", "").strip(),
                    confidence=seg.get("avg_logprob"),
                    words=[],
                )
            )
            continue

        annotated_words = []
        word_data = []

        for w in words:
            word = w.get("word", "").strip()
            prob = w.get("probability", 0.8)

            total_words += 1
            confidence_sum += prob

            if prob < low_threshold:
                annotated_words.append("[inaudible]")
                inaudible_words += 1
            elif prob < high_threshold:
                # Mark as uncertain
                annotated_words.append(f"[{word}?]")
                low_confidence_words += 1
            else:
                annotated_words.append(word)

            word_data.append(
                {
                    "word": word,
                    "start": w.get("start"),
                    "end": w.get("end"),
                    "confidence": prob,
                }
            )

        # Reconstruct text
        text = " ".join(annotated_words)
        # Clean up spacing around punctuation
        text = text.replace(" ,", ",").replace(" .", ".").replace(" ?", "?")
        text = text.replace("  ", " ").strip()

        avg_confidence = sum(w.get("probability", 0.8) for w in words) / len(words)

        processed_segments.append(
            Segment(
                start=seg["start"],
                end=seg["end"],
                text=text,
                confidence=avg_confidence,
                words=word_data,
            )
        )

    # Build confidence report
    report = {
        "total_words": total_words,
        "overall": confidence_sum / total_words if total_words > 0 else 0,
        "low_confidence_count": low_confidence_words,
        "inaudible_count": inaudible_words,
        "high_threshold": high_threshold,
        "low_threshold": low_threshold,
    }

    return processed_segments, report


def transcribe(
    audio_path: str,
    output_path: Optional[str] = None,
    output_format: str = "markdown",
    use_api: bool = False,
    language: str = "auto",
    model: Optional[str] = None,
) -> Transcript:
    """
    Main transcription function.

    Args:
        audio_path: Path to audio file
        output_path: Optional output file path
        output_format: Output format (markdown, srt, vtt, json)
        use_api: Use OpenAI API instead of local model
        language: Language code or 'auto'
        model: Override model from settings

    Returns:
        Transcript object
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Load settings
    settings = load_settings()
    vocab = load_vocabulary()

    trans_settings = settings["transcription"]
    thresholds = trans_settings["confidence_thresholds"]

    model_name = model or trans_settings["model"]
    lang = language if language != "auto" else trans_settings["language"]

    # Get audio info
    info = get_audio_info(audio_path)
    print(f"Transcribing: {audio_path.name}")
    print(f"Duration: {info['duration']:.1f}s, Channels: {info['channels']}")

    # Transcribe
    try:
        if use_api:
            print("Using OpenAI Whisper API...")
            result = transcribe_with_openai(str(audio_path), lang)
        else:
            print(f"Using local model: {model_name}")
            result = transcribe_with_mlx(str(audio_path), model_name, lang, vocab)
    except Exception as e:
        # Fallback to API if local fails and configured
        if not use_api and trans_settings.get("fallback_api") == "openai":
            print(f"Local transcription failed ({e}), falling back to API...")
            result = transcribe_with_openai(str(audio_path), lang)
        else:
            raise

    # Process confidence
    segments, confidence_report = annotate_confidence(
        result.get("segments", []),
        high_threshold=thresholds["high"],
        low_threshold=thresholds["low"],
    )

    # Build transcript
    transcript = Transcript(
        segments=segments,
        language=result.get("language"),
        duration=info["duration"],
        source_file=str(audio_path),
        confidence_report=confidence_report,
    )

    # Output
    if output_path:
        output_path = Path(output_path)
    else:
        # Default: same name, different extension
        ext_map = {"markdown": ".md", "srt": ".srt", "vtt": ".vtt", "json": ".json"}
        output_path = audio_path.with_suffix(ext_map.get(output_format, ".md"))

    export_transcript(transcript, output_path, output_format)
    print(f"\nTranscript saved to: {output_path}")

    # Print summary
    print(f"\nConfidence Report:")
    print(f"  Overall: {confidence_report['overall']:.1%}")
    print(f"  Low confidence: {confidence_report['low_confidence_count']} words")
    print(f"  Inaudible: {confidence_report['inaudible_count']} sections")

    return transcript


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio with confidence scoring"
    )
    parser.add_argument("audio_file", help="Path to audio file")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument(
        "-f",
        "--format",
        choices=["markdown", "srt", "vtt", "json"],
        default="markdown",
        help="Output format",
    )
    parser.add_argument(
        "--api", action="store_true", help="Use OpenAI API instead of local model"
    )
    parser.add_argument(
        "-l", "--language", default="auto", help="Language code or 'auto'"
    )
    parser.add_argument("--model", help="Override transcription model")

    args = parser.parse_args()

    transcript = transcribe(
        args.audio_file,
        output_path=args.output,
        output_format=args.format,
        use_api=args.api,
        language=args.language,
        model=args.model,
    )

    # Print the transcript
    print("\n" + "=" * 60)
    print(to_markdown(transcript))


if __name__ == "__main__":
    main()
