"""T1.1 - audio_capture + VAD on file input (TEST.md; D8, V1-V7).

WAVs are fed with realtime=False (V6): this tests segmentation, not latency (T2 does that).
A missing fixture or model makes the test fail, never skip (D22).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from arm_en_asr.audio_capture import (
    CAP_S, SR, Segmenter, SileroVad, WavSource, new_id_counter, run_capture,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
SILERO = ROOT / "models" / "silero_vad.onnx"


def segments_of(fixture: str):
    segmenter = Segmenter("mic", SileroVad(SILERO), new_id_counter())
    out = []
    run_capture(WavSource(FIXTURES / fixture, realtime=False), segmenter, out.append)
    return out


def assert_16k_mono(seg):
    assert seg.audio.dtype == np.float32
    assert seg.audio.ndim == 1  # mono; samples are at SR = 16 kHz by construction


def test_speech_fixture_gives_segments():
    segs = segments_of("speech_short.wav")
    assert len(segs) >= 1
    for s in segs:
        assert_16k_mono(s)
        assert 0.3 <= len(s.audio) / SR <= CAP_S, f"segment {s.id}: {len(s.audio) / SR:.2f} s"


def test_silence_fixture_gives_no_segments():
    assert segments_of("silence_5s.wav") == []


def test_continuous_speech_is_cut_at_cap():
    """D8 / D26: the cap is CAP_S (7 s); speech_long.wav has >= 13 s of unbroken speech."""
    segs = segments_of("speech_long.wav")
    lengths = [len(s.audio) / SR for s in segs]
    assert all(n <= CAP_S for n in lengths), lengths
    assert any(len(s.audio) == int(CAP_S * SR) for s in segs), (
        f"no segment of exactly {CAP_S:g} s: {lengths}")
    for s in segs:
        assert_16k_mono(s)
