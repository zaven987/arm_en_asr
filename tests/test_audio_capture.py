"""T1.1 - audio_capture + VAD on file input (TEST.md; D8, V1-V7).

WAVs are fed with realtime=False (V6): this tests segmentation, not latency (T2 does that).
A missing fixture or model makes the test fail, never skip (D22).

M5 S3 (D27 E1-E3, F1-F2, 2026-11-05): session offset, shared ids and the Capture class, tested with a
scripted stub VAD and stub sources (no model, no audio files).
"""
from __future__ import annotations

import threading
from pathlib import Path

import numpy as np
import pytest

from arm_en_asr.audio_capture import (
    CAP_S, SR, WINDOW, Capture, CaptureError, ParecSource, Segmenter, SileroVad, WavSource,
    new_id_counter, run_capture,
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


# ---------------------------------------------------------------- M5 S3: E1-E3, F1-F2

WAIT_S = 5.0                                  # generous timeout for thread events
ONE_SEGMENT = [0.0] * 5 + [1.0] * 20 + [0.0] * 30   # 0.64 s of speech, then > 0.6 s silence
SILENT_CHUNK = np.zeros(WINDOW, dtype=np.int16)


class ScriptedVad:
    """Stub VAD: speech probability per chunk from a list (then 0.0); no model."""

    def __init__(self, probs):
        self._probs = iter(probs)

    def prob(self, chunk) -> float:
        return next(self._probs, 0.0)


class StubSource:
    """`n` chunks (arrival = end time of the chunk), then: raise `fail`, or wait until `hold` is set
    (by the test, or by stop()), or end at once. `fed_all` is set after the last chunk was consumed."""

    def __init__(self, n: int, fail: BaseException | None = None, hold: bool = False):
        self.n, self.fail = n, fail
        self.hold = threading.Event()
        if not hold:
            self.hold.set()
        self.fed_all = threading.Event()

    def stop(self) -> None:
        self.hold.set()

    def chunks(self):
        for i in range(self.n):
            yield SILENT_CHUNK, (i + 1) * WINDOW / SR
        self.fed_all.set()
        if self.fail is not None:
            raise self.fail
        self.hold.wait()


def push_all(segmenter: Segmenter, n: int, first_arrival: float) -> list:
    out = []
    for i in range(n):
        out += segmenter.push(SILENT_CHUNK, first_arrival + i * WINDOW / SR)
    return out + segmenter.flush()


def test_session_offset_is_added_to_start_and_end():
    """E1 / F1: offset = first chunk arrival - 32 ms - session_start; end_wall unchanged."""
    session_start = 100.0
    first_arrival = session_start + 0.5 + WINDOW / SR      # first sample recorded 0.5 s after start
    seg = Segmenter("mic", ScriptedVad(ONE_SEGMENT), new_id_counter(), session_start=session_start)
    segs = push_all(seg, len(ONE_SEGMENT), first_arrival)
    assert len(segs) == 1
    s = segs[0]
    assert s.start == pytest.approx(5 * WINDOW / SR + 0.5)    # speech starts at chunk 5
    assert s.end == pytest.approx(25 * WINDOW / SR + 0.5)     # last speech chunk is 24
    assert s.end_wall == pytest.approx(first_arrival + 24 * WINDOW / SR)


def test_no_session_start_means_no_offset():
    """F1: without session_start the clock starts at this Segmenter's first sample."""
    seg = Segmenter("mic", ScriptedVad(ONE_SEGMENT), new_id_counter())
    segs = push_all(seg, len(ONE_SEGMENT), 100.0)
    assert len(segs) == 1
    assert segs[0].start == pytest.approx(5 * WINDOW / SR)
    assert segs[0].end == pytest.approx(25 * WINDOW / SR)


def test_shared_id_counter_across_devices():
    ids = new_id_counter()
    mic = Segmenter("mic", ScriptedVad(ONE_SEGMENT * 2), ids)
    system = Segmenter("system", ScriptedVad(ONE_SEGMENT), ids)
    got = []
    for segmenter, n in ((mic, len(ONE_SEGMENT)), (system, len(ONE_SEGMENT)), (mic, len(ONE_SEGMENT))):
        got += [(s.id, s.device) for s in push_all(segmenter, n, 0.0)]
    assert got == [(1, "mic"), (2, "system"), (3, "mic")]


def make_capture(sources: dict[str, StubSource], probs: dict[str, list[float]]):
    emitted: list = []
    wake = threading.Event()
    ids = new_id_counter()
    capture = Capture([(sources[d], Segmenter(d, ScriptedVad(probs[d]), ids)) for d in sources],
                      emitted.append, wake)
    return capture, emitted, wake


def test_capture_ends_when_every_input_has_ended():
    """E2: the shorter input ends first; wake is set only when the other one has ended too."""
    sources = {"mic": StubSource(len(ONE_SEGMENT)), "system": StubSource(len(ONE_SEGMENT), hold=True)}
    capture, emitted, wake = make_capture(sources, {"mic": ONE_SEGMENT, "system": ONE_SEGMENT})
    capture.start()
    mic_thread, _ = capture.threads
    mic_thread.join(WAIT_S)
    assert not mic_thread.is_alive(), "mic input did not end"
    assert sources["system"].fed_all.wait(WAIT_S)
    assert not wake.is_set(), "session ended while the system input was still running"
    sources["system"].hold.set()                      # the longer file ends
    assert wake.wait(WAIT_S), "wake not set after every input ended"
    capture.stop()
    assert capture.errors == []
    assert sorted(s.device for s in emitted) == ["mic", "system"]


def test_capture_lost_device_wakes_at_once_and_drains_the_other():
    """E3: one input fails -> wake at once, error kept; stop() ends the other, its open segment
    is still emitted."""
    lost = CaptureError("device lost: 'stub mic'")
    sources = {"mic": StubSource(len(ONE_SEGMENT), fail=lost),
               "system": StubSource(20, hold=True)}        # speech still open when stopped
    capture, emitted, wake = make_capture(sources, {"mic": ONE_SEGMENT, "system": [1.0] * 20})
    capture.start()
    assert wake.wait(WAIT_S), "wake not set after the mic input failed"
    assert capture.errors == [lost]
    assert sources["system"].fed_all.wait(WAIT_S)
    capture.stop()
    assert not any(t.is_alive() for t in capture.threads)
    assert sorted(s.device for s in emitted) == ["mic", "system"]


def test_capture_thread_names_and_one_input_per_device():
    """F2: threads capture-<device>; the same device twice is refused (D11)."""
    def segmenter(device):
        return Segmenter(device, ScriptedVad([]), new_id_counter())

    capture = Capture([(StubSource(0), segmenter("mic")), (StubSource(0), segmenter("system"))],
                      lambda s: None, threading.Event())
    assert [t.name for t in capture.threads] == ["capture-mic", "capture-system"]
    with pytest.raises(CaptureError, match="mic"):
        Capture([(StubSource(0), segmenter("mic")), (StubSource(0), segmenter("mic"))],
                lambda s: None, threading.Event())


def test_parec_source_stopped_before_start_starts_no_parec():
    """F8: stop() before the capture thread reaches parec -> parec never starts, nothing is read
    (no device needed: parec must not be started at all)."""
    src = ParecSource("no_such_source_t1_1")
    src.stop()
    assert list(src.chunks()) == []
    assert src._proc is None
