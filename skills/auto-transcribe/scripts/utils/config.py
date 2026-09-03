"""Configuration and vocabulary loading utilities."""

import os
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path.home() / ".auto-transcribe" / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.yaml"
VOCABULARY_FILE = CONFIG_DIR / "vocabulary.yaml"
SPEAKERS_DIR = CONFIG_DIR / "speakers"
MODELS_DIR = Path.home() / ".auto-transcribe" / "models"
TRANSCRIPTS_DIR = Path.home() / ".auto-transcribe" / "transcripts"


def ensure_dirs() -> None:
    """Ensure all required directories exist."""
    for dir_path in [CONFIG_DIR, SPEAKERS_DIR, MODELS_DIR, TRANSCRIPTS_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict[str, Any]:
    """Load settings from YAML file, with defaults."""
    defaults = {
        "transcription": {
            "model": "mlx-community/whisper-large-v3-mlx",
            "fallback_api": "openai",
            "confidence_thresholds": {"high": 0.7, "low": 0.4},
            "language": "auto",
        },
        "enhancement": {
            "enabled": True,
            "normalize": True,
            "noise_reduction": "noisereduce",
            "voice_isolation": False,
        },
        "diarization": {
            "default_mode": "stereo",
            # which physical channel carries the user's own mic: "left", "right",
            # or None = no dedicated user channel (mono / plain stereo mix)
            "user_channel": None,
            "user_name": None,  # user-channel label; unset -> placeholder "You"
            "similarity_threshold": 0.75,
        },
        "filename": {
            "org_marker": None,  # employer name to strip from filename context, e.g. "Acme"
        },
        # where meeting recordings land (the recording app's output folder);
        # used to resolve bare filenames — unset until the user configures it
        "recordings_dir": None,
        "live_monitoring": {
            "poll_interval": 20,
            "buffer_lag": 10,
            "source_format": "timestamped",  # "[hh:mm:ss.cc] Speaker: text" lines
        },
        "output": {
            "default_format": "markdown",
            "timestamp_format": "hh:mm:ss",
            "include_confidence_report": True,
            "archive_transcripts": True,
        },
    }

    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE) as f:
            user_settings = yaml.safe_load(f) or {}
        # Deep merge
        for key, value in user_settings.items():
            if key in defaults and isinstance(defaults[key], dict):
                defaults[key].update(value)
            else:
                defaults[key] = value

    return defaults


def load_vocabulary() -> list[str]:
    """Load domain vocabulary for transcription improvement."""
    vocab = []
    if VOCABULARY_FILE.exists():
        with open(VOCABULARY_FILE) as f:
            data = yaml.safe_load(f) or {}
        for category in data.values():
            if isinstance(category, list):
                vocab.extend(category)
    return vocab


def save_settings(settings: dict[str, Any]) -> None:
    """Save settings to YAML file."""
    ensure_dirs()
    with open(SETTINGS_FILE, "w") as f:
        yaml.dump(settings, f, default_flow_style=False)


def update_setting(section: str, key: str, value: Any) -> None:
    """Set one key in the user's settings.yaml, touching nothing else.

    Edits the raw user file (not the merged defaults) so only explicitly
    configured values are persisted."""
    ensure_dirs()
    data = {}
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE) as f:
            data = yaml.safe_load(f) or {}
    data.setdefault(section, {})[key] = value
    with open(SETTINGS_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def add_vocabulary(terms: list[str], category: str = "custom") -> None:
    """Add terms to vocabulary file."""
    ensure_dirs()
    data = {}
    if VOCABULARY_FILE.exists():
        with open(VOCABULARY_FILE) as f:
            data = yaml.safe_load(f) or {}

    if category not in data:
        data[category] = []

    # Add unique terms
    existing = set(data[category])
    for term in terms:
        if term not in existing:
            data[category].append(term)

    with open(VOCABULARY_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
