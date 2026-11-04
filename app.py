#!/usr/bin/env python3
"""Live Armenian -> English transcription + translation (DECISIONS.md).

Usage (D11):
    python app.py --list-devices
    python app.py [--mic "<exact source name>"] [--system "<exact monitor name>"]
    python app.py [--mic-wav a.wav] [--system-wav b.wav]    # file mode, tests only
    (at least one input; either may be left out)

Typing `quit` + Enter stops cleanly (exit 0); file mode also stops by itself when the file has
ended and every line is printed (exit 0). Ctrl+C = same clean shutdown, exit 130. Errors exit 1.
Transcript lines go to stdout; all other messages go to stderr (M3 S8, Q1-Q9).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
from pathlib import Path

# No runtime downloads (D15). Set before any Hugging Face library is imported.
os.environ["HF_HUB_OFFLINE"] = "1"

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

# Read at call time, so T6 can point it at an empty folder (agreed 2026-10-31).
MODELS_DIR = ROOT / "models"

N_ASR_WORKERS = 1        # D1: start with N = 1; Asr num_workers must equal it (D3, P9)
POLL_S = 0.2             # Q3: main thread checks for pipeline errors this often
EXIT_INTERRUPTED = 130   # Q6: Ctrl+C


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
        p.error("give --mic and/or --system (live), --mic-wav and/or --system-wav (file mode), "
                "or --list-devices")
    return args


def run(args: argparse.Namespace) -> int:
    if args.list_devices:
        print(pactl_sources_raw(), end="")
        return 0

    # 1. Inputs: device names (live) or files (file mode).
    # Either input may be left out (agreed 2026-10-31).
    if args.mic is not None or args.system is not None:
        available = source_names(pactl_sources_raw())
        if args.mic is not None:
            check_device("--mic", args.mic, available)
        if args.system is not None:
            check_device("--system", args.system, available)
    else:
        if args.mic_wav is not None:
            check_wav_exists("--mic-wav", args.mic_wav)
        if args.system_wav is not None:
            check_wav_exists("--system-wav", args.system_wav)

    # 2. Models (read MODELS_DIR now, not at import time).
    check_models(MODELS_DIR)

    # 3. System audio is processed from M5 on; until then refuse it rather than ignore it.
    if args.system is not None or args.system_wav is not None:
        raise AppError("system audio (--system / --system-wav) is not processed yet (milestone M5).")

    return run_session(args)


def info(message: str) -> None:
    """Q2: every message except transcript lines goes to stderr."""
    print(message, file=sys.stderr, flush=True)


def run_session(args: argparse.Namespace) -> int:
    """Q1-Q6: load models, start pipeline + capture + stdin reader, wait, shut down cleanly."""
    # Imported here, so --list-devices and the early checks stay fast.
    from arm_en_asr.asr import Asr, AsrError
    from arm_en_asr.audio_capture import (CaptureError, ParecSource, Segmenter, SileroVad,
                                          WavSource, new_id_counter, run_capture)
    from arm_en_asr.pipeline import Pipeline, PipelineError
    from arm_en_asr.translate import Mt, MtError
    known_errors = (AsrError, CaptureError, MtError, PipelineError)

    # Q1: models, then pipeline, then capture, then commands.
    try:
        info("loading models…")
        vad = SileroVad(MODELS_DIR / "silero_vad.onnx")
        asr = Asr(MODELS_DIR / "faster-whisper-small", num_workers=N_ASR_WORKERS)
        asr.warm_up()                    # W2 (D26 addition): first real segment is not slower
        mt = Mt(MODELS_DIR / "opus-mt-hy-en-ct2-int8")
        if args.mic is not None:
            source = ParecSource(args.mic)
            ready = f"listening on mic: {args.mic} — type quit + Enter to stop"
        else:
            source = WavSource(args.mic_wav, realtime=True)  # D21: always real-time in the app
            ready = f"playing {args.mic_wav} at real-time speed — type quit + Enter to stop early"
        segmenter = Segmenter("mic", vad, new_id_counter())
        pipeline = Pipeline(asr, mt, n_workers=N_ASR_WORKERS)
    except known_errors as e:
        raise AppError(str(e)) from None

    wake = threading.Event()             # set by: quit, end of capture (file end / error)
    capture_errors: list[BaseException] = []

    def capture() -> None:
        try:
            run_capture(source, segmenter, pipeline.submit)
        except BaseException as e:       # device lost, or submit refused: shown by the main thread
            capture_errors.append(e)
        finally:
            wake.set()                   # file mode: the file has ended

    def commands() -> None:
        for line in sys.stdin:
            cmd = line.strip()
            if not cmd:
                continue                 # Q3: blank lines are ignored
            if cmd == "quit":
                wake.set()
                return
            info(f"unknown command: {cmd!r} (type quit + Enter to stop)")
        # Q5: end of stdin: stop reading commands, keep running.

    threading.Thread(target=commands, name="stdin", daemon=True).start()
    capture_thread = threading.Thread(target=capture, name="capture-mic", daemon=True)
    capture_thread.start()
    info(ready)

    exit_code = 0
    pipeline_error: BaseException | None = None
    try:
        while not wake.wait(POLL_S):
            pipeline.check()             # Q3: a worker error ends the session at once
    except PipelineError as e:
        pipeline_error = e
    except KeyboardInterrupt:
        exit_code = EXIT_INTERRUPTED     # Q6: same clean shutdown as quit

    # Shutdown (P8, Q4): stop capture first, then drain what was already captured.
    try:
        source.stop()
        capture_thread.join()
        try:
            pipeline.close()
        except PipelineError as e:
            pipeline_error = pipeline_error or e
    except KeyboardInterrupt:            # second Ctrl+C while draining: stop now
        info("stopped (interrupted while finishing the last lines)")
        return EXIT_INTERRUPTED

    errors = [str(e) for e in (*capture_errors, pipeline_error) if e is not None]
    if errors:
        raise AppError("\n".join(dict.fromkeys(errors)))  # Q4: exit 1, each error once
    info("stopped")
    return exit_code


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
