"""T6 - CLI fail-loudly checks (TEST.md).

M3 step S1 covers: unknown device name, missing model.
Step S8 adds: unknown stdin command, `quit` + Enter.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"


def load_app():
    """Import app.py from the repo root (it is not on the import path)."""
    spec = importlib.util.spec_from_file_location("app_under_test", APP)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_app(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(APP), *args],
        capture_output=True, text=True, timeout=30, cwd=ROOT,
    )


def real_source_name() -> str:
    """Any existing PulseAudio source. Fails (never skips) if pactl does not work."""
    out = subprocess.run(
        ["pactl", "list", "short", "sources"], capture_output=True, text=True, timeout=10, check=True,
    ).stdout
    names = [line.split("\t")[1] for line in out.splitlines() if "\t" in line]
    assert names, "pactl lists no sources; PulseAudio must be running for T6"
    return names[0]


def write_silent_wav(path: Path, seconds: float = 0.5) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * int(16000 * seconds))


def test_unknown_mic_device():
    bad = "no_such_source_t6_mic"
    r = run_app("--mic", bad)
    assert r.returncode != 0
    assert "unknown device for --mic" in r.stderr
    assert bad in r.stderr


def test_unknown_system_device():
    bad = "no_such_source_t6_system.monitor"
    r = run_app("--mic", real_source_name(), "--system", bad)
    assert r.returncode != 0
    assert "unknown device for --system" in r.stderr
    assert bad in r.stderr


def test_missing_model(tmp_path, monkeypatch, capsys):
    app = load_app()
    empty = tmp_path / "models_empty"
    empty.mkdir()
    monkeypatch.setattr(app, "MODELS_DIR", empty)
    wav = tmp_path / "input.wav"
    write_silent_wav(wav)

    with pytest.raises(SystemExit) as exc:
        app.main(["--mic-wav", str(wav)])

    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "model files missing" in err
    for name in ("Silero VAD", "faster-whisper small", "opus-mt-hy-en"):
        assert name in err, f"error does not name {name}"
    assert str(empty) in err
    # No download attempted: the app forces offline mode and creates nothing.
    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert list(empty.iterdir()) == []
