#!/usr/bin/env python3
"""Environment check for the auto-transcribe skill.

Stdlib only — runs with the system python3, no venv or third-party packages
required, so it works on a machine where nothing is set up yet. Prints one line
per requirement and, at the end, the exact commands to install whatever is
missing. Exit code 0 = ready to transcribe, 1 = something required is missing.

Usage: python3 scripts/doctor.py
"""

import platform
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
VENV_PY = SKILL_DIR / ".venv" / "bin" / "python"
MODELS_DIR = Path.home() / ".auto-transcribe" / "models"
SETTINGS = Path.home() / ".auto-transcribe" / "config" / "settings.yaml"
HF_WHISPER_CACHE = Path.home() / ".cache" / "huggingface" / "hub"
# the imports meeting.py needs at runtime (torch comes in via speechbrain)
CORE_IMPORTS = "mlx_whisper, speechbrain, sklearn, soundfile, numpy, yaml"

UV_INSTALL = "curl -LsSf https://astral.sh/uv/install.sh | sh"
BREW_INSTALL = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'

OK, BAD, NOTE = "✓", "✗", "•"


def main() -> int:
    print(f"auto-transcribe doctor — skill at {SKILL_DIR}\n")
    fixes = []  # commands to run, in order
    ready = True

    def check(ok, label, detail="", fix=None, required=True):
        nonlocal ready
        mark = OK if ok else (BAD if required else NOTE)
        print(f" {mark} {label}" + (f" — {detail}" if detail else ""))
        if not ok:
            if fix and fix not in fixes:
                fixes.append(fix)
            if required:
                ready = False

    # 1. platform: mlx-whisper needs an Apple Silicon Mac
    is_mac = platform.system() == "Darwin"
    is_arm = platform.machine() == "arm64"
    if is_mac and not is_arm:
        check(False, "Apple Silicon",
              "python3 reports x86_64 — an Intel Mac (or python3 running under "
              "Rosetta) cannot run mlx-whisper")
    else:
        check(is_mac and is_arm, "Apple Silicon Mac",
              "" if is_mac and is_arm else
              f"{platform.system()}/{platform.machine()} — local transcription "
              "(mlx-whisper) requires macOS on Apple Silicon")

    # 2. uv (installs and manages the skill's venv)
    has_uv = shutil.which("uv") is not None
    check(has_uv, "uv", "" if has_uv else "package manager used to set up the venv",
          fix=UV_INSTALL)

    # 3. ffmpeg + ffprobe (system binaries, used for channel split / probing)
    has_ffmpeg = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
    has_brew = shutil.which("brew") is not None
    if not has_ffmpeg and not has_brew:
        check(False, "Homebrew", "needed here to install ffmpeg", fix=BREW_INSTALL)
    check(has_ffmpeg, "ffmpeg + ffprobe",
          "" if has_ffmpeg else "audio probing and channel splitting",
          fix="brew install ffmpeg")

    # 4. skill venv with the Python dependencies
    if not VENV_PY.exists():
        check(False, "skill venv", f"{VENV_PY.parent} missing",
              fix=f'cd "{SKILL_DIR}" && uv sync')
    else:
        try:
            r = subprocess.run([str(VENV_PY), "-c", f"import {CORE_IMPORTS}"],
                               capture_output=True, text=True, timeout=180)
            ok = r.returncode == 0
            detail = "" if ok else (r.stderr.strip().splitlines() or ["import failed"])[-1]
        except (subprocess.TimeoutExpired, OSError) as e:
            ok, detail = False, str(e)
        check(ok, "Python dependencies", detail, fix=f'cd "{SKILL_DIR}" && uv sync')

    # 5. models (auto-downloaded on first run; informational only)
    have_whisper = any(HF_WHISPER_CACHE.glob("models--*whisper*")) if HF_WHISPER_CACHE.exists() else False
    have_ecapa = (MODELS_DIR / "ecapa").exists()
    check(have_whisper and have_ecapa, "models",
          "" if have_whisper and have_ecapa else
          "Whisper (~3 GB) and the ECAPA voice model download automatically on "
          "first run — no action needed, just internet and time",
          required=False)

    # 6. personal settings (created/learned on first use; informational only)
    check(SETTINGS.exists(), "settings",
          "" if SETTINGS.exists() else
          f"{SETTINGS} not created yet — first use will ask for your name, "
          "channel layout, and recordings folder and save them",
          required=False)

    print()
    if fixes:
        print("To fix, run in order:")
        for i, cmd in enumerate(fixes, 1):
            print(f"  {i}. {cmd}")
        print("\nThen run this doctor again.")
    elif ready:
        print("Ready to transcribe.")
    else:
        print("This machine cannot run local transcription (see above).")
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
