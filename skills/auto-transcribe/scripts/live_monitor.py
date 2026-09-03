#!/usr/bin/env python3
"""
Live monitoring for transcripts and audio files.

Features:
- Monitor timestamped transcript output files
- Monitor growing audio files
- Continuous template filling
- Intermediary file for clean diffing
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from utils.config import load_settings
from utils.formats import Segment, Transcript, export_transcript


def parse_timestamped_line(line: str) -> Optional[dict]:
    """
    Parse a timestamped transcript line.

    Format: [00:00:00.02] Dia: text...
    """
    pattern = r"\[(\d{2}):(\d{2}):(\d{2})\.(\d{2})\]\s+(\w+):\s*(.+)"
    match = re.match(pattern, line.strip())

    if match:
        hours, minutes, seconds, centis, speaker, text = match.groups()
        timestamp = (
            int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(centis) / 100
        )
        return {
            "timestamp": timestamp,
            "speaker": speaker,
            "text": text,
        }
    return None


def parse_plain_transcript_line(line: str) -> Optional[dict]:
    """
    Parse plain transcript format.

    Format: [HH:MM:SS] text... or just text
    """
    # Try timestamped format
    pattern = r"\[(\d{2}):(\d{2}):(\d{2})\]\s*(.+)"
    match = re.match(pattern, line.strip())

    if match:
        hours, minutes, seconds, text = match.groups()
        timestamp = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
        return {"timestamp": timestamp, "speaker": None, "text": text}

    # Plain text
    text = line.strip()
    if text:
        return {"timestamp": None, "speaker": None, "text": text}

    return None


class LiveTranscriptMonitor:
    """Monitor a live transcript file and process updates."""

    def __init__(
        self,
        source_path: str,
        output_path: Optional[str] = None,
        template_path: Optional[str] = None,
        source_format: str = "timestamped",
        poll_interval: int = 20,
    ):
        self.source_path = Path(source_path)
        self.source_format = source_format
        self.poll_interval = poll_interval

        # Output paths
        if output_path:
            self.output_path = Path(output_path)
        else:
            self.output_path = self.source_path.with_stem(
                f"{self.source_path.stem}_processed"
            )

        self.template_path = Path(template_path) if template_path else None

        # State tracking
        self.last_byte_position = 0
        self.segments: list[Segment] = []
        self.running = False

    def parse_line(self, line: str) -> Optional[dict]:
        """Parse a line based on configured format."""
        if self.source_format in ("timestamped", "audio_hijack"):  # legacy value accepted
            return parse_timestamped_line(line)
        else:
            return parse_plain_transcript_line(line)

    def read_new_content(self) -> list[dict]:
        """Read new content from source file since last check."""
        if not self.source_path.exists():
            return []

        with open(self.source_path, "rb") as f:
            f.seek(self.last_byte_position)
            new_bytes = f.read()
            self.last_byte_position = f.tell()

        if not new_bytes:
            return []

        # Decode and parse lines
        try:
            new_text = new_bytes.decode("utf-8")
        except UnicodeDecodeError:
            new_text = new_bytes.decode("utf-8", errors="ignore")

        parsed = []
        for line in new_text.split("\n"):
            if line.strip():
                result = self.parse_line(line)
                if result:
                    parsed.append(result)

        return parsed

    def update_segments(self, new_content: list[dict]) -> None:
        """Add new content to segments."""
        for item in new_content:
            # Try to merge with last segment if same speaker
            if (
                self.segments
                and item.get("speaker") == self.segments[-1].speaker
                and item.get("timestamp")
            ):
                # Extend existing segment
                self.segments[-1].text += " " + item["text"]
                self.segments[-1].end = item.get("timestamp", self.segments[-1].end)
            else:
                # New segment
                timestamp = item.get("timestamp", 0)
                self.segments.append(
                    Segment(
                        start=timestamp,
                        end=timestamp + 1,  # Will be updated
                        text=item["text"],
                        speaker=item.get("speaker"),
                    )
                )

    def build_transcript(self) -> Transcript:
        """Build transcript from current segments."""
        return Transcript(
            segments=self.segments.copy(),
            source_file=str(self.source_path),
            duration=self.segments[-1].end if self.segments else 0,
        )

    def save_output(self) -> None:
        """Save current transcript to output file."""
        if not self.segments:
            return

        transcript = self.build_transcript()
        export_transcript(transcript, self.output_path, "json")

        # Also save markdown for easy reading
        md_path = self.output_path.with_suffix(".md")
        export_transcript(transcript, md_path, "markdown")

    def update_template(self) -> None:
        """Update template with current transcript content."""
        if not self.template_path or not self.segments:
            return

        try:
            from template_fill import fill_from_transcript

            # Save current transcript first
            self.save_output()

            # Fill template
            filled_path = self.template_path.with_stem(
                f"{self.template_path.stem}_live"
            )
            fill_from_transcript(
                str(self.output_path),
                str(self.template_path),
                output_path=str(filled_path),
            )
            print(f"  Template updated: {filled_path}")
        except Exception as e:
            print(f"  Template update failed: {e}")

    def run(self) -> None:
        """Run the monitoring loop."""
        print(f"Monitoring: {self.source_path}")
        print(f"Output: {self.output_path}")
        print(f"Poll interval: {self.poll_interval}s")
        if self.template_path:
            print(f"Template: {self.template_path}")
        print("\nPress Ctrl+C to stop.\n")

        self.running = True
        last_template_update = 0
        template_update_interval = max(60, self.poll_interval * 3)  # Update template less frequently

        try:
            while self.running:
                # Check for new content
                new_content = self.read_new_content()

                if new_content:
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] "
                        f"New content: {len(new_content)} line(s)"
                    )
                    self.update_segments(new_content)
                    self.save_output()

                    # Update template periodically
                    if (
                        self.template_path
                        and time.time() - last_template_update > template_update_interval
                    ):
                        self.update_template()
                        last_template_update = time.time()

                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            print("\n\nStopping monitor...")
            self.running = False

        # Final save
        self.save_output()
        if self.template_path:
            self.update_template()

        print(f"Final transcript saved to: {self.output_path}")


class LiveAudioMonitor:
    """Monitor a growing audio file and transcribe incrementally."""

    def __init__(
        self,
        audio_path: str,
        output_path: Optional[str] = None,
        poll_interval: int = 20,
        buffer_lag: int = 10,
    ):
        self.audio_path = Path(audio_path)
        self.poll_interval = poll_interval
        self.buffer_lag = buffer_lag

        if output_path:
            self.output_path = Path(output_path)
        else:
            self.output_path = self.audio_path.with_suffix(".json")

        # State
        self.last_processed_time = 0.0
        self.segments: list[Segment] = []
        self.running = False

    def get_safe_duration(self) -> float:
        """Get duration of audio that's safe to process (with lag buffer)."""
        try:
            from utils.audio import get_audio_info

            info = get_audio_info(self.audio_path)
            return max(0, info["duration"] - self.buffer_lag)
        except Exception:
            return 0

    def transcribe_chunk(self, start: float, end: float) -> list[Segment]:
        """Transcribe a chunk of audio."""
        import tempfile
        import subprocess

        from transcribe import transcribe
        from utils.audio import load_audio, save_audio

        # Extract chunk
        audio, sr = load_audio(self.audio_path, sr=16000, mono=True)
        start_sample = int(start * sr)
        end_sample = int(end * sr)
        chunk = audio[start_sample:end_sample]

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        save_audio(chunk, tmp_path, sr)

        try:
            # Transcribe
            transcript = transcribe(tmp_path, output_format="json")

            # Adjust timestamps
            for seg in transcript.segments:
                seg.start += start
                seg.end += start

            return transcript.segments
        finally:
            Path(tmp_path).unlink()

    def run(self) -> None:
        """Run the audio monitoring loop."""
        print(f"Monitoring audio: {self.audio_path}")
        print(f"Output: {self.output_path}")
        print(f"Poll interval: {self.poll_interval}s, Buffer lag: {self.buffer_lag}s")
        print("\nPress Ctrl+C to stop.\n")

        self.running = True

        try:
            while self.running:
                safe_duration = self.get_safe_duration()

                if safe_duration > self.last_processed_time + 5:  # At least 5s of new audio
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] "
                        f"Processing: {self.last_processed_time:.1f}s - {safe_duration:.1f}s"
                    )

                    new_segments = self.transcribe_chunk(
                        self.last_processed_time, safe_duration
                    )

                    if new_segments:
                        self.segments.extend(new_segments)
                        self.last_processed_time = safe_duration

                        # Save
                        transcript = Transcript(
                            segments=self.segments,
                            source_file=str(self.audio_path),
                            duration=safe_duration,
                        )
                        export_transcript(transcript, self.output_path, "json")
                        print(f"  Saved {len(self.segments)} segments")

                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            print("\n\nStopping audio monitor...")
            self.running = False

        print(f"Final transcript saved to: {self.output_path}")


def monitor_live(
    source_path: str,
    output_path: Optional[str] = None,
    template_path: Optional[str] = None,
    mode: str = "text",
    poll_interval: Optional[int] = None,
    buffer_lag: Optional[int] = None,
) -> None:
    """
    Main live monitoring function.

    Args:
        source_path: Path to transcript text file or audio file
        output_path: Output path for processed transcript
        template_path: Optional template to fill
        mode: 'text' for transcript files, 'audio' for audio files
        poll_interval: Seconds between checks
        buffer_lag: Seconds behind write head (audio mode)
    """
    settings = load_settings()
    live_settings = settings.get("live_monitoring", {})

    poll_interval = poll_interval or live_settings.get("poll_interval", 20)
    buffer_lag = buffer_lag or live_settings.get("buffer_lag", 10)

    if mode == "audio":
        monitor = LiveAudioMonitor(
            source_path,
            output_path=output_path,
            poll_interval=poll_interval,
            buffer_lag=buffer_lag,
        )
    else:
        source_format = live_settings.get("source_format", "timestamped")
        monitor = LiveTranscriptMonitor(
            source_path,
            output_path=output_path,
            template_path=template_path,
            source_format=source_format,
            poll_interval=poll_interval,
        )

    monitor.run()


def main():
    parser = argparse.ArgumentParser(description="Live transcript/audio monitoring")
    parser.add_argument("source", help="Path to transcript text file or audio file")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("-t", "--template", help="Template file to fill")
    parser.add_argument(
        "-m",
        "--mode",
        choices=["text", "audio"],
        default="text",
        help="Monitoring mode",
    )
    parser.add_argument(
        "-i", "--interval", type=int, help="Poll interval in seconds"
    )
    parser.add_argument(
        "--buffer-lag", type=int, help="Buffer lag in seconds (audio mode)"
    )

    args = parser.parse_args()

    monitor_live(
        args.source,
        output_path=args.output,
        template_path=args.template,
        mode=args.mode,
        poll_interval=args.interval,
        buffer_lag=args.buffer_lag,
    )


if __name__ == "__main__":
    main()
