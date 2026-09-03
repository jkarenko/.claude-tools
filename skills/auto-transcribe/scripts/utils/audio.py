"""Audio loading, conversion, and channel splitting utilities."""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import librosa
import numpy as np
import soundfile as sf


def load_audio(
    path: str | Path, sr: int = 16000, mono: bool = True
) -> tuple[np.ndarray, int]:
    """
    Load audio file and convert to target sample rate.

    Args:
        path: Path to audio file
        sr: Target sample rate (default 16kHz for Whisper)
        mono: Whether to convert to mono

    Returns:
        Tuple of (audio_array, sample_rate)
    """
    path = Path(path)

    # Handle various formats via librosa (uses ffmpeg as backend)
    try:
        audio, sample_rate = librosa.load(str(path), sr=sr, mono=mono)
        return audio, sample_rate
    except Exception as e:
        # Try ffmpeg directly for problematic formats
        return _load_via_ffmpeg(path, sr, mono)


def _load_via_ffmpeg(path: Path, sr: int, mono: bool) -> tuple[np.ndarray, int]:
    """Load audio using ffmpeg directly."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    channels = "1" if mono else "2"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(path),
        "-ar",
        str(sr),
        "-ac",
        channels,
        "-f",
        "wav",
        tmp_path,
    ]

    subprocess.run(cmd, capture_output=True, check=True)
    audio, sample_rate = sf.read(tmp_path)
    Path(tmp_path).unlink()

    return audio.astype(np.float32), sample_rate


def save_audio(audio: np.ndarray, path: str | Path, sr: int = 16000) -> None:
    """Save audio array to file."""
    path = Path(path)
    sf.write(str(path), audio, sr)


def split_stereo_channels(
    path: str | Path, sr: int = 16000
) -> tuple[np.ndarray, np.ndarray]:
    """
    Split stereo audio into left and right channels.

    Returns:
        Tuple of (left_channel, right_channel) as numpy arrays
    """
    audio, _ = librosa.load(str(path), sr=sr, mono=False)

    if audio.ndim == 1:
        # Already mono - return same for both
        return audio, audio

    left = audio[0]
    right = audio[1]
    return left, right


def get_audio_info(path: str | Path) -> dict:
    """Get information about an audio file."""
    path = Path(path)
    info = sf.info(str(path))
    return {
        "duration": info.duration,
        "sample_rate": info.samplerate,
        "channels": info.channels,
        "format": info.format,
        "subtype": info.subtype,
    }


def convert_to_wav(
    input_path: str | Path, output_path: Optional[str | Path] = None, sr: int = 16000
) -> Path:
    """
    Convert audio file to WAV format suitable for transcription.

    Args:
        input_path: Source audio file
        output_path: Destination path (default: same name with .wav)
        sr: Target sample rate

    Returns:
        Path to converted file
    """
    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path.with_suffix(".wav")
    else:
        output_path = Path(output_path)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ar",
        str(sr),
        "-ac",
        "1",  # mono
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]

    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def calculate_snr(audio: np.ndarray, sr: int = 16000) -> float:
    """
    Estimate Signal-to-Noise Ratio of audio.

    Uses a simple energy-based estimation assuming noise is in quiet sections.
    """
    # Frame the audio
    frame_length = int(0.025 * sr)  # 25ms frames
    hop_length = int(0.010 * sr)  # 10ms hop

    # Calculate energy per frame
    frames = librosa.util.frame(audio, frame_length=frame_length, hop_length=hop_length)
    energy = np.sum(frames**2, axis=0)

    # Estimate noise from lowest energy frames (bottom 10%)
    threshold_idx = int(len(energy) * 0.1)
    sorted_energy = np.sort(energy)
    noise_energy = np.mean(sorted_energy[:threshold_idx]) + 1e-10

    # Signal energy from top 50%
    signal_energy = np.mean(sorted_energy[len(energy) // 2 :])

    snr = 10 * np.log10(signal_energy / noise_energy)
    return float(snr)
