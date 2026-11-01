"""T6 - CLI fail-loudly checks (TEST.md).

M3 step S1 covers: unknown device name, missing model.
Step S8 adds (Q8): unknown stdin command, `quit` + Enter. These start the app live on a real
PulseAudio source; no person is needed (not marked `hardware`).
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
import threading
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


# ---------------------------------------------------------------- S8: stdin commands (Q8)

START_TIMEOUT = 60  # seconds: model loading + parec start
STOP_TIMEOUT = 60   # seconds: drain + shutdown


class LiveApp:
    """The app running live on a real source, with stdin / stdout / stderr pipes."""

    def __init__(self, source: str):
        self.source = source
        self.proc = subprocess.Popen(
            [sys.executable, str(APP), "--mic", source],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=ROOT,
        )
        self.stderr_lines: list[str] = []
        self._ready = threading.Event()
        self._reader = threading.Thread(target=self._read_stderr, daemon=True)
        self._reader.start()
        started = self._ready.wait(START_TIMEOUT) and self.proc.poll() is None
        if not started:
            self.proc.kill()
            pytest.fail(f"app did not reach 'listening on' within {START_TIMEOUT} s:\n{self.stderr}")

    def _read_stderr(self) -> None:
        for line in self.proc.stderr:
            self.stderr_lines.append(line)
            if line.startswith("listening on"):
                self._ready.set()
        self._ready.set()  # stderr closed: unblock the wait

    @property
    def stderr(self) -> str:
        return "".join(self.stderr_lines)

    def send_and_wait(self, text: str) -> int:
        self.proc.stdin.write(text)
        self.proc.stdin.flush()
        try:
            code = self.proc.wait(timeout=STOP_TIMEOUT)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            pytest.fail(f"app did not stop within {STOP_TIMEOUT} s:\n{self.stderr}")
        self._reader.join(5)
        return code


def parec_running(source: str) -> bool:
    r = subprocess.run(["pgrep", "-f", f"parec --device={re.escape(source)}"],
                       capture_output=True, text=True)
    return r.returncode == 0


def wait_for_parec(source: str, timeout: float = 5.0) -> bool:
    """'listening on' is printed as the capture thread starts; parec may need a moment."""
    stop = threading.Event()
    for _ in range(int(timeout / 0.1)):
        if parec_running(source):
            return True
        stop.wait(0.1)
    return False


def test_unknown_stdin_command_keeps_running():
    app = LiveApp(real_source_name())
    code = app.send_and_wait("hello\nquit\n")
    assert "unknown command: 'hello'" in app.stderr
    assert code == 0, f"exit {code}; stderr:\n{app.stderr}"  # still running until quit


def test_quit_shuts_down_cleanly():
    source = real_source_name()
    app = LiveApp(source)
    assert wait_for_parec(source), "parec did not start"
    code = app.send_and_wait("quit\n")
    assert code == 0, f"exit {code}; stderr:\n{app.stderr}"
    assert app.stderr_lines[-1].strip() == "stopped"
    assert not parec_running(source), "parec still running after quit"
