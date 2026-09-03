#!/usr/bin/env python3
"""
Speaker diarization for transcripts.

Features:
- Stereo channel splitting (left = user, right = remote)
- Multi-speaker detection in mono using voice embeddings
- Speaker profile matching and learning
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from utils.audio import load_audio, split_stereo_channels, get_audio_info
from utils.config import load_settings
from utils.speakers import (
    save_speaker_profile,
    load_speaker_profile,
    match_speaker,
    list_speaker_profiles,
)
from utils.formats import Segment, Transcript, from_json, to_json, export_transcript


def get_voice_encoder():
    """Load the Resemblyzer voice encoder."""
    from resemblyzer import VoiceEncoder

    encoder = VoiceEncoder()
    return encoder


def compute_embedding(audio: np.ndarray, sr: int = 16000) -> np.ndarray:
    """Compute voice embedding for audio segment."""
    from resemblyzer import preprocess_wav

    encoder = get_voice_encoder()

    # Preprocess for Resemblyzer (expects specific format)
    wav = preprocess_wav(audio, source_sr=sr)
    embedding = encoder.embed_utterance(wav)

    return embedding


def segment_by_voice_activity(
    audio: np.ndarray, sr: int = 16000, min_segment_length: float = 0.5
) -> list[dict]:
    """
    Segment audio by voice activity detection.

    Returns list of segments with start/end times.
    """
    import librosa

    # Use librosa's RMS energy for simple VAD
    frame_length = int(0.025 * sr)  # 25ms
    hop_length = int(0.010 * sr)  # 10ms

    rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[
        0
    ]

    # Threshold at 20% of max energy
    threshold = 0.2 * np.max(rms)
    is_speech = rms > threshold

    # Find contiguous speech regions
    segments = []
    in_speech = False
    start_frame = 0

    for i, speech in enumerate(is_speech):
        if speech and not in_speech:
            start_frame = i
            in_speech = True
        elif not speech and in_speech:
            # End of segment
            start_time = start_frame * hop_length / sr
            end_time = i * hop_length / sr
            if end_time - start_time >= min_segment_length:
                segments.append({"start": start_time, "end": end_time})
            in_speech = False

    # Handle segment at end
    if in_speech:
        start_time = start_frame * hop_length / sr
        end_time = len(audio) / sr
        if end_time - start_time >= min_segment_length:
            segments.append({"start": start_time, "end": end_time})

    return segments


def diarize_stereo(
    audio_path: str,
    left_speaker: str = "User",
    right_speaker: str = "Remote",
) -> list[dict]:
    """
    Diarize stereo audio by channel.

    Left channel = user's microphone
    Right channel = remote participants
    """
    left, right = split_stereo_channels(audio_path)

    # Detect voice activity in each channel
    left_segments = segment_by_voice_activity(left)
    right_segments = segment_by_voice_activity(right)

    # Tag with speakers
    all_segments = []
    for seg in left_segments:
        seg["speaker"] = left_speaker
        seg["channel"] = "left"
        all_segments.append(seg)

    for seg in right_segments:
        seg["speaker"] = right_speaker
        seg["channel"] = "right"
        all_segments.append(seg)

    # Sort by start time
    all_segments.sort(key=lambda x: x["start"])

    return all_segments


def diarize_mono(
    audio_path: str,
    num_speakers: Optional[int] = None,
    speaker_profiles: Optional[list[str]] = None,
) -> list[dict]:
    """
    Diarize mono audio using speaker embeddings and clustering.

    Args:
        audio_path: Path to audio file
        num_speakers: Known number of speakers (optional)
        speaker_profiles: Names of known speaker profiles to match

    Returns:
        List of segments with speaker labels
    """
    from sklearn.cluster import AgglomerativeClustering

    audio, sr = load_audio(audio_path, sr=16000, mono=True)
    settings = load_settings()
    similarity_threshold = settings["diarization"]["similarity_threshold"]

    # Get voice segments
    segments = segment_by_voice_activity(audio, sr)

    if not segments:
        return []

    # Compute embeddings for each segment
    embeddings = []
    for seg in segments:
        start_sample = int(seg["start"] * sr)
        end_sample = int(seg["end"] * sr)
        segment_audio = audio[start_sample:end_sample]

        if len(segment_audio) < sr * 0.3:  # Skip very short segments
            embeddings.append(None)
            continue

        try:
            emb = compute_embedding(segment_audio, sr)
            embeddings.append(emb)
        except Exception:
            embeddings.append(None)

    # Filter out segments without valid embeddings
    valid_indices = [i for i, e in enumerate(embeddings) if e is not None]
    valid_embeddings = np.array([embeddings[i] for i in valid_indices])

    if len(valid_embeddings) == 0:
        return segments  # Return without speaker labels

    # Cluster embeddings
    if num_speakers:
        n_clusters = num_speakers
    else:
        # Estimate number of speakers (between 2 and 10)
        n_clusters = min(max(2, len(valid_embeddings) // 5), 10)

    clustering = AgglomerativeClustering(
        n_clusters=n_clusters, metric="cosine", linkage="average"
    )
    labels = clustering.fit_predict(valid_embeddings)

    # Assign labels to segments
    label_map = {}
    for i, idx in enumerate(valid_indices):
        cluster_id = labels[i]

        if cluster_id not in label_map:
            # Try to match to known profile
            emb = valid_embeddings[i]
            match = match_speaker(emb, similarity_threshold)
            if match:
                label_map[cluster_id] = match[0]
            else:
                label_map[cluster_id] = f"Speaker {cluster_id + 1}"

        segments[idx]["speaker"] = label_map[cluster_id]

    # Fill in missing speakers
    for seg in segments:
        if "speaker" not in seg:
            seg["speaker"] = "Unknown"

    return segments


def apply_diarization_to_transcript(
    transcript: Transcript, diarization: list[dict]
) -> Transcript:
    """
    Apply speaker labels from diarization to transcript segments.
    """
    for seg in transcript.segments:
        # Find overlapping diarization segment
        seg_mid = (seg.start + seg.end) / 2

        for diar_seg in diarization:
            if diar_seg["start"] <= seg_mid <= diar_seg["end"]:
                seg.speaker = diar_seg.get("speaker")
                break

    return transcript


def learn_speaker(audio_path: str, name: str, metadata: dict = None) -> str:
    """
    Learn a speaker's voice from an audio sample.

    Args:
        audio_path: Audio file with speaker's voice
        name: Name to save the profile as
        metadata: Optional metadata (notes, source, etc.)

    Returns:
        Path to saved profile
    """
    audio, sr = load_audio(audio_path, sr=16000, mono=True)

    # Compute average embedding over the file
    segments = segment_by_voice_activity(audio, sr)

    embeddings = []
    for seg in segments:
        start_sample = int(seg["start"] * sr)
        end_sample = int(seg["end"] * sr)
        segment_audio = audio[start_sample:end_sample]

        if len(segment_audio) >= sr * 0.3:
            try:
                emb = compute_embedding(segment_audio, sr)
                embeddings.append(emb)
            except Exception:
                continue

    if not embeddings:
        raise ValueError("Could not extract voice features from audio")

    # Average embedding
    avg_embedding = np.mean(embeddings, axis=0)

    # Normalize
    avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)

    profile_path = save_speaker_profile(name, avg_embedding, metadata)
    print(f"Saved speaker profile for '{name}' to {profile_path}")

    return str(profile_path)


def diarize(
    audio_path: str,
    transcript_path: Optional[str] = None,
    output_path: Optional[str] = None,
    mode: str = "auto",
    left_speaker: str = "User",
    right_speaker: str = "Remote",
    num_speakers: Optional[int] = None,
) -> dict:
    """
    Main diarization function.

    Args:
        audio_path: Path to audio file
        transcript_path: Optional existing transcript to enhance
        output_path: Output path for diarized transcript
        mode: 'stereo', 'mono', or 'auto'
        left_speaker: Name for left channel speaker
        right_speaker: Name for right channel speaker
        num_speakers: Number of speakers (for mono mode)

    Returns:
        Dict with results and paths
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    info = get_audio_info(audio_path)
    print(f"Diarizing: {audio_path.name}")
    print(f"Channels: {info['channels']}, Duration: {info['duration']:.1f}s")

    # Determine mode
    if mode == "auto":
        mode = "stereo" if info["channels"] == 2 else "mono"
    print(f"Using {mode} mode")

    # Run diarization
    if mode == "stereo":
        diarization = diarize_stereo(str(audio_path), left_speaker, right_speaker)
    else:
        diarization = diarize_mono(str(audio_path), num_speakers)

    # Count speakers
    speakers = set(seg.get("speaker", "Unknown") for seg in diarization)
    print(f"Detected {len(speakers)} speaker(s): {', '.join(speakers)}")

    # Apply to transcript if provided
    if transcript_path:
        transcript_path = Path(transcript_path)
        with open(transcript_path) as f:
            if transcript_path.suffix == ".json":
                transcript = from_json(f.read())
            else:
                # Can't easily parse markdown back, need JSON
                raise ValueError("Please provide transcript in JSON format for diarization")

        transcript = apply_diarization_to_transcript(transcript, diarization)

        if output_path:
            output_path = Path(output_path)
        else:
            output_path = transcript_path.with_stem(f"{transcript_path.stem}_diarized")

        export_transcript(transcript, output_path, "json")
        print(f"Diarized transcript saved to: {output_path}")

        return {
            "audio": str(audio_path),
            "transcript": str(output_path),
            "speakers": list(speakers),
            "segments": len(diarization),
        }

    # Just output diarization data
    if output_path:
        output_path = Path(output_path)
    else:
        output_path = audio_path.with_suffix(".diarization.json")

    with open(output_path, "w") as f:
        json.dump(diarization, f, indent=2)
    print(f"Diarization saved to: {output_path}")

    return {
        "audio": str(audio_path),
        "diarization": str(output_path),
        "speakers": list(speakers),
        "segments": len(diarization),
    }


def main():
    parser = argparse.ArgumentParser(description="Speaker diarization for audio")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Diarize command
    diar_parser = subparsers.add_parser("diarize", help="Diarize audio file")
    diar_parser.add_argument("audio_file", help="Path to audio file")
    diar_parser.add_argument("-t", "--transcript", help="Transcript JSON to enhance")
    diar_parser.add_argument("-o", "--output", help="Output file path")
    diar_parser.add_argument(
        "-m",
        "--mode",
        choices=["stereo", "mono", "auto"],
        default="auto",
        help="Diarization mode",
    )
    diar_parser.add_argument(
        "--left-speaker", default="User", help="Name for left channel"
    )
    diar_parser.add_argument(
        "--right-speaker", default="Remote", help="Name for right channel"
    )
    diar_parser.add_argument(
        "-n", "--num-speakers", type=int, help="Number of speakers (mono mode)"
    )

    # Learn speaker command
    learn_parser = subparsers.add_parser("learn", help="Learn a speaker's voice")
    learn_parser.add_argument("audio_file", help="Audio file with speaker's voice")
    learn_parser.add_argument("name", help="Speaker name")

    # List speakers command
    list_parser = subparsers.add_parser("list", help="List known speakers")

    args = parser.parse_args()

    if args.command == "diarize" or args.command is None:
        if not hasattr(args, "audio_file") or not args.audio_file:
            parser.print_help()
            return

        result = diarize(
            args.audio_file,
            transcript_path=getattr(args, "transcript", None),
            output_path=getattr(args, "output", None),
            mode=getattr(args, "mode", "auto"),
            left_speaker=getattr(args, "left_speaker", "User"),
            right_speaker=getattr(args, "right_speaker", "Remote"),
            num_speakers=getattr(args, "num_speakers", None),
        )
        print(f"\nResult: {result}")

    elif args.command == "learn":
        learn_speaker(args.audio_file, args.name)

    elif args.command == "list":
        profiles = list_speaker_profiles()
        if profiles:
            print("Known speakers:")
            for p in profiles:
                print(f"  - {p['name']}")
        else:
            print("No speaker profiles found.")


if __name__ == "__main__":
    main()
