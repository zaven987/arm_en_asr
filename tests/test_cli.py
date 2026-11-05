"""T6 - CLI fail-loudly checks (TEST.md).

M3 step S1 covers: unknown device name, missing model.
Step S8 adds (Q8): unknown stdin command, `quit` + Enter. These start the app live on a real
PulseAudio source; no person is needed (not marked `hardware`).
M5 S3 adds (D27 E2, E4, F5): `--system-wav` still refused (replaced in S6); file mode with the mic
only ends by itself with exit 0 (loads the models, needs the GPU, D30).
M6 S6 (D27 S6, H3, H5): the refusal test is replaced by "a short --system-wav run is accepted and
exits 0" (real diarizer on the committed fixture speech_short.wav, no eval data, D22); the missing-
model error also names the speaker-embedding model; app.SPEAKER_MODEL equals diarizer.MODEL_FILE.
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
SPEECH_SHORT = ROOT / "tests" / "fixtures" / "speech_short.wav"   # D22, FLEURS CC-BY 4.0


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
    for name in ("Silero VAD", "faster-whisper small", "opus-mt-hy-en",
                 "WeSpeaker ResNet34 speaker embedding"):   # H3: checked always
        assert name in err, f"error does not name {name}"
    assert str(empty) in err
    # No download attempted: the app forces offline mode and creates nothing.
    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert list(empty.iterdir()) == []


def test_speaker_model_path_matches_diarizer():
    """H3: app.py writes the path itself (no sherpa-onnx import in the early checks); it must not drift."""
    from arm_en_asr.diarizer import MODEL_FILE
    assert load_app().SPEAKER_MODEL == MODEL_FILE


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


# ---------------------------------------------------------------- M5 S3 (D27 E2), M6 S6 (H5)

FILE_RUN_TIMEOUT = 120  # seconds: model loading on the GPU + warm-up + a short file


def test_system_wav_run_accepted(tmp_path):
    """D27 S6 (replaces the S3 refusal test): a short --system-wav run is accepted, the real
    diarizer labels its line "Speaker 1", the session ends by itself (E2) with exit 0."""
    assert SPEECH_SHORT.is_file(), f"fixture missing: {SPEECH_SHORT} (run scripts/make_fixtures.py)"
    silence = tmp_path / "silence.wav"
    write_silent_wav(silence)
    r = subprocess.run(
        [sys.executable, str(APP), "--mic-wav", str(silence), "--system-wav", str(SPEECH_SHORT)],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=FILE_RUN_TIMEOUT, cwd=ROOT,
    )
    assert r.returncode == 0, f"exit {r.returncode}; stderr:\n{r.stderr}"
    assert f"system: {SPEECH_SHORT}" in r.stderr
    assert "Speaker 1:" in r.stdout, f"no Speaker 1 line; stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
    assert "Me:" not in r.stdout, f"silent mic printed a line; stdout:\n{r.stdout}"
    assert r.stderr.strip().splitlines()[-1] == "stopped"


def test_file_mode_mic_only_ends_by_itself(tmp_path):
    """E2 with one input: the file ends, every line is printed, exit 0."""
    wav = tmp_path / "silence.wav"
    write_silent_wav(wav)
    r = subprocess.run(
        [sys.executable, str(APP), "--mic-wav", str(wav)],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=FILE_RUN_TIMEOUT, cwd=ROOT,
    )
    assert r.returncode == 0, f"exit {r.returncode}; stderr:\n{r.stderr}"
    assert f"playing mic: {wav}" in r.stderr
    assert r.stderr.strip().splitlines()[-1] == "stopped"
