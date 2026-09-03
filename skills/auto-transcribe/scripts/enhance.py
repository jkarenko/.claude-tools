#!/usr/bin/env python3
"""
Audio preprocessing pipeline for improved transcription quality.

Features:
- Format conversion to 16kHz mono WAV
- Loudness normalization (EBU R128)
- Noise reduction (noisereduce or deepfilternet)
- Voice isolation (optional, via demucs)
"""

import argparse
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from utils.audio import load_audio, save_audio, calculate_snr, get_audio_info
from utils.config import load_settings


def normalize_loudness(input_path: Path, output_path: Path) -> Path:
    """
    Apply EBU R128 loudness normalization using ffmpeg.
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"Normalization failed: {result.stderr.decode()}")

    return output_path


def reduce_noise_noisereduce(audio: np.ndarray, sr: int = 16000) -> np.ndarray:
    """
    Apply noise reduction using noisereduce library.

    Uses stationary noise reduction - estimates noise from the quietest parts.
    """
    import noisereduce as nr

    # Reduce noise with conservative settings
    reduced = nr.reduce_noise(
        y=audio,
        sr=sr,
        stationary=True,
        prop_decrease=0.75,  # How much to reduce noise (0-1)
        n_std_thresh_stationary=1.5,  # Threshold for noise detection
    )

    return reduced


def reduce_noise_deepfilter(input_path: Path, output_path: Path) -> Path:
    """
    Apply noise reduction using DeepFilterNet (higher quality, slower).
    """
    cmd = ["deepFilter", str(input_path), "-o", str(output_path)]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        # Check if deepfilter is installed
        raise RuntimeError(
            f"DeepFilterNet failed. Is it installed? "
            f"Error: {result.stderr.decode()}"
        )

    return output_path


def isolate_voice(input_path: Path, output_path: Path) -> Path:
    """
    Isolate voice using demucs (removes music/background).

    This is resource-intensive - only use when necessary.
    """
    cmd = [
        "python",
        "-m",
        "demucs",
        "--two-stems",
        "vocals",
        "-o",
        str(output_path.parent),
        str(input_path),
    ]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"Voice isolation failed: {result.stderr.decode()}")

    # Demucs outputs to a subdirectory
    vocals_path = output_path.parent / "htdemucs" / input_path.stem / "vocals.wav"
    if vocals_path.exists():
        vocals_path.rename(output_path)
        return output_path

    raise FileNotFoundError("Demucs output not found")


def enhance(
    audio_path: str,
    output_path: Optional[str] = None,
    normalize: bool = True,
    noise_reduction: str = "noisereduce",
    voice_isolation: bool = False,
    force: bool = False,
) -> dict:
    """
    Run audio enhancement pipeline.

    Args:
        audio_path: Input audio file
        output_path: Output file (default: {name}_enhanced.wav)
        normalize: Apply loudness normalization
        noise_reduction: 'noisereduce', 'deepfilternet', or 'none'
        voice_isolation: Apply voice isolation (slow)
        force: Apply enhancement even if SNR is already good

    Returns:
        Dict with paths and quality metrics
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if output_path:
        output_path = Path(output_path)
    else:
        output_path = audio_path.parent / f"{audio_path.stem}_enhanced.wav"

    print(f"Enhancing: {audio_path.name}")

    # Load original for SNR calculation
    audio_original, sr = load_audio(audio_path, sr=16000, mono=True)
    snr_before = calculate_snr(audio_original, sr)
    print(f"Original SNR: {snr_before:.1f} dB")

    # Skip if SNR is already excellent and not forcing
    if snr_before > 30 and not force:
        print("Audio quality is already excellent, skipping enhancement.")
        # Still convert to standard format
        save_audio(audio_original, output_path, sr)
        return {
            "input": str(audio_path),
            "output": str(output_path),
            "snr_before": snr_before,
            "snr_after": snr_before,
            "improvement": 0,
            "skipped": True,
        }

    # Working with temp files for pipeline
    current_audio = audio_original
    current_path = audio_path

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Step 1: Voice isolation (if requested, do first)
        if voice_isolation:
            print("Isolating voice...")
            try:
                isolated_path = tmpdir / "isolated.wav"
                save_audio(current_audio, tmpdir / "input.wav", sr)
                isolate_voice(tmpdir / "input.wav", isolated_path)
                current_audio, _ = load_audio(isolated_path, sr=16000, mono=True)
                current_path = isolated_path
                print("  Voice isolation complete")
            except Exception as e:
                print(f"  Voice isolation skipped: {e}")

        # Step 2: Noise reduction
        if noise_reduction != "none":
            print(f"Reducing noise ({noise_reduction})...")
            try:
                if noise_reduction == "deepfilternet":
                    # DeepFilterNet works on files
                    input_for_df = tmpdir / "pre_denoise.wav"
                    save_audio(current_audio, input_for_df, sr)
                    denoised_path = tmpdir / "denoised.wav"
                    reduce_noise_deepfilter(input_for_df, denoised_path)
                    current_audio, _ = load_audio(denoised_path, sr=16000, mono=True)
                else:
                    # noisereduce works in memory
                    current_audio = reduce_noise_noisereduce(current_audio, sr)
                print("  Noise reduction complete")
            except Exception as e:
                print(f"  Noise reduction skipped: {e}")

        # Step 3: Loudness normalization
        if normalize:
            print("Normalizing loudness...")
            try:
                pre_norm = tmpdir / "pre_norm.wav"
                save_audio(current_audio, pre_norm, sr)
                normalized_path = tmpdir / "normalized.wav"
                normalize_loudness(pre_norm, normalized_path)
                current_audio, _ = load_audio(normalized_path, sr=16000, mono=True)
                print("  Normalization complete")
            except Exception as e:
                print(f"  Normalization skipped: {e}")

    # Save final output
    save_audio(current_audio, output_path, sr)

    # Calculate improvement
    snr_after = calculate_snr(current_audio, sr)
    improvement = snr_after - snr_before

    print(f"\nEnhanced SNR: {snr_after:.1f} dB (improvement: {improvement:+.1f} dB)")
    print(f"Output saved to: {output_path}")

    return {
        "input": str(audio_path),
        "output": str(output_path),
        "snr_before": snr_before,
        "snr_after": snr_after,
        "improvement": improvement,
        "skipped": False,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Enhance audio for better transcription quality"
    )
    parser.add_argument("audio_file", help="Path to audio file")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument(
        "--no-normalize", action="store_true", help="Skip loudness normalization"
    )
    parser.add_argument(
        "--noise-reduction",
        choices=["noisereduce", "deepfilternet", "none"],
        default="noisereduce",
        help="Noise reduction method",
    )
    parser.add_argument(
        "--voice-isolation",
        action="store_true",
        help="Isolate voice from background (slow)",
    )
    parser.add_argument(
        "--force", action="store_true", help="Enhance even if quality is good"
    )

    args = parser.parse_args()

    result = enhance(
        args.audio_file,
        output_path=args.output,
        normalize=not args.no_normalize,
        noise_reduction=args.noise_reduction,
        voice_isolation=args.voice_isolation,
        force=args.force,
    )

    print(f"\nResult: {result}")


if __name__ == "__main__":
    main()
