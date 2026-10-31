#!/usr/bin/env python3
"""Live Armenian -> English transcription + translation (DECISIONS.md).

Usage (D11):
    python app.py --list-devices
    python app.py --mic "<exact source name>" [--system "<exact monitor name>"]
    python app.py --mic-wav a.wav [--system-wav b.wav]      # file mode, tests only

M3 step S1: command line, device-name check and model check only.
The pipeline is connected in step S8.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# No runtime downloads (D15). Set before any Hugging Face library is imported.
os.environ["HF_HUB_OFFLINE"] = "1"

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

# Read at call time, so T6 can point it at an empty folder (agreed 2026-10-31).
MODELS_DIR = ROOT / "models"


class AppError(Exception):
    """An error the user must see; main() prints it and exits non-zero."""


def required_model_files(models_dir: Path) -> list[tuple[str, Path]]:
    """(model name, file) pairs the app needs. Written by scripts/download_models.py."""
    whisper = models_dir / "faster-whisper-small"
    opus = models_dir / "opus-mt-hy-en-ct2-int8"
    return [
        ("Silero VAD v6.2.1", models_dir / "silero_vad.onnx"),
        ("faster-whisper small", whisper / "model.bin"),
        ("faster-whisper small", whisper / "config.json"),
        ("faster-whisper small", whisper / "tokenizer.json"),
        ("faster-whisper small", whisper / "vocabulary.txt"),
        ("opus-mt-hy-en (CTranslate2 int8)", opus / "model.bin"),
        ("opus-mt-hy-en (CTranslate2 int8)", opus / "config.json"),
        ("opus-mt-hy-en (CTranslate2 int8)", opus / "shared_vocabulary.json"),
        ("opus-mt-hy-en (CTranslate2 int8)", opus / "source.spm"),
        ("opus-mt-hy-en (CTranslate2 int8)", opus / "target.spm"),
    ]


def check_models(models_dir: Path) -> None:
    missing = [(name, path) for name, path in required_model_files(models_dir) if not path.is_file()]
    if missing:
        lines = "\n".join(f"  - {name}: {path}" for name, path in missing)
        raise AppError(
            f"model files missing:\n{lines}\n"
            "Run `python scripts/download_models.py` once (needs internet). "
            "The app never downloads models itself."
        )


def pactl_sources_raw() -> str:
    """Output of `pactl list short sources` (D10). Fails loudly if pactl does not work."""
    try:
        result = subprocess.run(
            ["pactl", "list", "short", "sources"],
            capture_output=True, text=True, timeout=10,
        )
    except FileNotFoundError:
        raise AppError("`pactl` not found. Install pulseaudio-utils.") from None
    except subprocess.TimeoutExpired:
        raise AppError("`pactl list short sources` did not answer within 10 s. Is PulseAudio running?") from None
    if result.returncode != 0:
        raise AppError(
            f"`pactl list short sources` failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout


def source_names(raw: str) -> list[str]:
    """Source names = 2nd tab-separated column of `pactl list short sources`."""
    names = []
    for line in raw.splitlines():
        cols = line.split("\t")
        if len(cols) >= 2:
            names.append(cols[1])
    return names


def check_device(option: str, name: str, available: list[str]) -> None:
    if name not in available:
        raise AppError(
            f"unknown device for {option}: {name!r}\n"
            "Use an exact name from `python app.py --list-devices`."
        )


def check_wav_exists(option: str, path: str) -> None:
    if not Path(path).is_file():
        raise AppError(f"file not found for {option}: {path}")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="app.py",
        description="Live Armenian -> English transcription + translation.",
    )
    p.add_argument("--list-devices", action="store_true",
                   help="print PulseAudio sources (incl. .monitor) and exit")
    p.add_argument("--mic", metavar="NAME", help="exact PulseAudio source name of the microphone")
    p.add_argument("--system", metavar="NAME", help="exact PulseAudio monitor name of system audio")
    p.add_argument("--mic-wav", metavar="FILE", help="file mode (tests only): WAV fed as the mic")
    p.add_argument("--system-wav", metavar="FILE", help="file mode (tests only): WAV fed as system audio")
    args = p.parse_args(argv)

    live = args.mic is not None or args.system is not None
    file_mode = args.mic_wav is not None or args.system_wav is not None
    if args.list_devices and (live or file_mode):
        p.error("--list-devices cannot be combined with other options")
    if live and file_mode:
        p.error("use either --mic/--system (live) or --mic-wav/--system-wav (file mode), not both")
    if not args.list_devices and not live and not file_mode:
        p.error("give --mic (live), --mic-wav (file mode) or --list-devices")
    if args.system is not None and args.mic is None:
        p.error("--system needs --mic")
    if args.system_wav is not None and args.mic_wav is None:
        p.error("--system-wav needs --mic-wav")
    return args


def run(args: argparse.Namespace) -> int:
    if args.list_devices:
        print(pactl_sources_raw(), end="")
        return 0

    # 1. Inputs: device names (live) or files (file mode).
    if args.mic is not None:
        available = source_names(pactl_sources_raw())
        check_device("--mic", args.mic, available)
        if args.system is not None:
            check_device("--system", args.system, available)
    else:
        check_wav_exists("--mic-wav", args.mic_wav)
        if args.system_wav is not None:
            check_wav_exists("--system-wav", args.system_wav)

    # 2. Models (read MODELS_DIR now, not at import time).
    check_models(MODELS_DIR)

    # 3. System audio is processed from M5 on; until then refuse it rather than ignore it.
    if args.system is not None or args.system_wav is not None:
        raise AppError("system audio (--system / --system-wav) is not processed yet (milestone M5).")

    raise AppError("checks passed, but the pipeline is not connected yet (M3 step S8).")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        code = run(args)
    except AppError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    sys.exit(code)


if __name__ == "__main__":
    main()
