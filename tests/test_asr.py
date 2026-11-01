"""T1.2 - asr on the speech fixture (TEST.md; D3, A1-A6, D26).

Sanity check, not a quality bar: non-empty text, >= 50 % Armenian-script letters (D20).
Also: Asr pointed at an empty folder fails with a clear "model missing" error (A6).
Also: token_cap follows D26 (no model needed).
A missing fixture or model makes the test fail, never skip (D22).
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pytest

from arm_en_asr.asr import Asr, AsrError, token_cap

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
WHISPER = ROOT / "models" / "faster-whisper-small"


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


def test_speech_fixture_gives_armenian_text():
    text = Asr(WHISPER).transcribe(load_fixture("speech_short.wav"))
    print(f"ASR text: {text}")  # visible with -s / in the saved output on failure
    assert text, "ASR returned empty text"
    share = armenian_share(text)
    assert share >= 0.5, f"only {100 * share:.0f} % Armenian letters: {text!r}"


def test_missing_model_fails_loudly(tmp_path):
    """A6: empty folder -> clear 'model missing' error, no download attempt."""
    with pytest.raises(AsrError, match="model missing"):
        Asr(tmp_path)


def test_token_cap_follows_d26():
    """D26: ceil(15.8 tok/s x seconds x 1.5), at most 220 (values as in diag_asr.py)."""
    assert token_cap(1.65) == 40
    assert token_cap(4.5) == 107
    assert token_cap(7.0) == 166
    assert token_cap(20.0) == 220
