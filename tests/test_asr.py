"""T1.2 - asr on the speech fixture (TEST.md; D34, before it D3, A1-A6, D26, D30).

Sanity check, not a quality bar: non-empty text, >= 50 % Armenian-script letters (D20).
Also: Asr pointed at an empty folder fails with a clear "model missing" error (A6).
Also: Asr.warm_up() runs without error (D26 addition, W4, 2026-11-04).
D34 (N8): Asr loads FastConformer CTC on the GPU (provider cuda, this process's GPU memory rose,
N3); num_workers other than 1 is refused (N2); the D33 guard: in a fresh process that imports
onnxruntime first, Asr refuses with AsrError instead of crashing. The D26 token_cap test is gone
(CTC cannot loop). The first CUDA recognizer of the pytest process is made by conftest.py (D33).
These tests need the GPU. A missing fixture, model or GPU makes the test fail, never skip (D22).
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
import wave
from pathlib import Path

import numpy as np
import pytest

from arm_en_asr import asr as asr_module
from arm_en_asr.asr import Asr, AsrError

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
FASTCONFORMER = ROOT / "models" / "fastconformer-hy-ctc"


def armenian_share(text: str) -> float:
    """Same definition as scripts/smoke_m1.py: Armenian block + Armenian ligatures."""
    letters = [c for c in text if c.isalpha()]
    arm = [c for c in letters if "԰" <= c <= "֏" or "ﬓ" <= c <= "ﬗ"]
    return len(arm) / len(letters) if letters else 0.0


def load_fixture(name: str) -> np.ndarray:
    with wave.open(str(FIXTURES / name), "rb") as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)
        pcm = w.readframes(w.getnframes())
    return np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0


@pytest.fixture(scope="module")
def asr() -> Asr:
    """One recognizer for the tests below, so the GPU never holds several at once."""
    return Asr(FASTCONFORMER)


def test_speech_fixture_gives_armenian_text(asr):
    text = asr.transcribe(load_fixture("speech_short.wav"))
    print(f"ASR text: {text}")  # visible with -s / in the saved output on failure
    assert text, "ASR returned empty text"
    share = armenian_share(text)
    assert share >= 0.5, f"only {100 * share:.0f} % Armenian letters: {text!r}"


def test_missing_model_fails_loudly(tmp_path):
    """A6: empty folder -> clear 'model missing' error, no download attempt."""
    with pytest.raises(AsrError, match="model missing"):
        Asr(tmp_path)


def test_warm_up_runs(asr):
    """W4: warm_up() decodes silence once and returns nothing."""
    assert asr.warm_up() is None


def test_asr_loads_on_gpu(asr):
    """D34 N1 / N3: provider cuda, and creating the recognizer raised this process's GPU memory."""
    assert asr_module.PROVIDER == "cuda"
    assert asr.vram_added_mb > 0, f"GPU memory did not rise: {asr.vram_added_mb} MB"


def test_num_workers_other_than_one_refused():
    """D34 N2 / D28: one recognizer, one worker."""
    with pytest.raises(AsrError, match="num_workers"):
        Asr(FASTCONFORMER, num_workers=2)


def test_d33_guard_in_a_fresh_process():
    """D33: onnxruntime imported before the first CUDA recognizer -> AsrError naming D33, not a
    segmentation fault. Runs in a subprocess, because this pytest process already has its first
    recognizer (conftest.py)."""
    code = textwrap.dedent(f"""
        import sys
        sys.path.insert(0, {str(ROOT / "src")!r})
        import onnxruntime
        from arm_en_asr.asr import Asr, AsrError
        try:
            Asr({str(FASTCONFORMER)!r})
        except AsrError as e:
            print("ASRERROR:", e)
            sys.exit(0)
        print("NO ERROR")
        sys.exit(3)
    """)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, f"exit {r.returncode}\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}"
    assert "ASRERROR:" in r.stdout and "D33" in r.stdout, r.stdout
