#!/usr/bin/env python3
"""
Format conversion for transcripts.

Supports: Markdown, SRT, VTT, JSON
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.formats import (
    Transcript,
    from_json,
    export_transcript,
    to_markdown,
    to_srt,
    to_vtt,
    to_json,
)


def convert_transcript(
    input_path: str,
    output_path: str = None,
    output_format: str = "markdown",
) -> Path:
    """
    Convert transcript to specified format.

    Args:
        input_path: Path to transcript JSON file
        output_path: Output file path
        output_format: 'markdown', 'srt', 'vtt', or 'json'

    Returns:
        Path to exported file
    """
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Transcript not found: {input_path}")

    # Load transcript (must be JSON format)
    with open(input_path) as f:
        transcript = from_json(f.read())

    # Determine output path
    if output_path:
        output_path = Path(output_path)
    else:
        ext_map = {
            "markdown": ".md",
            "md": ".md",
            "srt": ".srt",
            "vtt": ".vtt",
            "json": ".json",
        }
        ext = ext_map.get(output_format, ".md")
        output_path = input_path.with_suffix(ext)

    # Export
    result_path = export_transcript(transcript, output_path, output_format)
    print(f"Exported to: {result_path}")

    return result_path


def batch_convert(
    input_dir: str,
    output_format: str = "markdown",
    output_dir: str = None,
) -> list[Path]:
    """
    Convert all transcript JSON files in a directory.

    Args:
        input_dir: Directory containing JSON transcripts
        output_format: Target format
        output_dir: Output directory (default: same as input)

    Returns:
        List of exported file paths
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir) if output_dir else input_dir

    output_dir.mkdir(parents=True, exist_ok=True)

    exported = []
    for json_file in input_dir.glob("*.json"):
        try:
            ext_map = {"markdown": ".md", "srt": ".srt", "vtt": ".vtt", "json": ".json"}
            output_path = output_dir / (json_file.stem + ext_map.get(output_format, ".md"))

            result = convert_transcript(str(json_file), str(output_path), output_format)
            exported.append(result)
        except Exception as e:
            print(f"Error converting {json_file.name}: {e}")

    print(f"\nConverted {len(exported)} file(s)")
    return exported


def main():
    parser = argparse.ArgumentParser(description="Convert transcript formats")
    parser.add_argument("input", help="Input transcript JSON file or directory")
    parser.add_argument("-o", "--output", help="Output file or directory")
    parser.add_argument(
        "-f",
        "--format",
        choices=["markdown", "md", "srt", "vtt", "json"],
        default="markdown",
        help="Output format",
    )
    parser.add_argument(
        "--batch", action="store_true", help="Process all JSON files in directory"
    )

    args = parser.parse_args()

    if args.batch:
        batch_convert(args.input, args.format, args.output)
    else:
        convert_transcript(args.input, args.output, args.format)


if __name__ == "__main__":
    main()
