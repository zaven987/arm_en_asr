"""T1.5 - pipeline join + order (TEST.md; D1, D12, D13, D27, L5; M3 S7 decisions P1-P10; M5 S1 G1-G7).

Stub ASR / MT / diarizer, no models. Out-of-order finishing is forced with threading.Event gates
(no sleeps), so the tests are deterministic. A stub that waits too long fails the test instead of hanging.
"""
from __future__ import annotations

import threading

import numpy as np
import pytest

from arm_en_asr.audio_capture import Segment
from arm_en_asr.pipeline import Pipeline, PipelineError

GATE_TIMEOUT = 5.0  # seconds; only reached if the pipeline is broken


def make_segment(seg_id: int, device: str = "mic", end_wall: float = 0.0) -> Segment:
    """The stub ASR reads the segment id back from the audio."""
    return Segment(id=seg_id, device=device, start=10.0 * seg_id, end=10.0 * seg_id + 2.0,
                   audio=np.full(160, seg_id, dtype=np.float32), end_wall=end_wall)


class StubAsr:
    """Returns "hy-<id>". `waits[id]` = id whose ASR must finish first; `empty` / `fail` = ids."""

    def __init__(self, num_workers: int = 1, waits=None, empty=(), fail=()):
        self.num_workers = num_workers
        self.waits = waits or {}
        self.empty, self.fail = set(empty), set(fail)
        self.done = {}            # id -> Event, set when that id's ASR has finished
        self.finish_order = []
        self._lock = threading.Lock()

    def _event(self, seg_id):
        with self._lock:
            return self.done.setdefault(seg_id, threading.Event())

    def transcribe(self, audio):
        seg_id = int(audio[0])
        if seg_id in self.waits:
            other = self.waits[seg_id]
            if not self._event(other).wait(GATE_TIMEOUT):
                raise TimeoutError(f"segment {seg_id} waited for segment {other} too long")
        if seg_id in self.fail:
            raise RuntimeError(f"stub ASR error on {seg_id}")
        with self._lock:
            self.finish_order.append(seg_id)
        self._event(seg_id).set()
        return "" if seg_id in self.empty else f"hy-{seg_id}"


class StubMt:
    def __init__(self):
        self.calls = []
        self.done = threading.Event()  # set after the first translation

    def translate(self, armenian):
        self.calls.append(armenian)
        self.done.set()
        return f"en-{armenian}"


class StubDiarizer:
    """Returns "Speaker <id>". `wait_for` = Event to wait on before labelling; `fail` / `bad` = ids."""

    def __init__(self, wait_for: threading.Event | None = None, fail=(), bad=()):
        self.wait_for = wait_for
        self.fail, self.bad = set(fail), set(bad)
        self.calls = []

    def label(self, segment):
        self.calls.append(segment.id)
        if self.wait_for is not None and not self.wait_for.wait(GATE_TIMEOUT):
            raise TimeoutError(f"diarizer waited too long on segment {segment.id}")
        if segment.id in self.fail:
            raise RuntimeError(f"stub diarizer error on {segment.id}")
        if segment.id in self.bad:
            return ""
        return f"Speaker {segment.id}"


def run(asr, ids, n_workers=1, clock=lambda: 0.0, end_wall=0.0, diarizer=None, devices=None, mt=None):
    """Submit segments `ids` (devices[i] or "mic"), close, return (printed records, pipeline)."""
    printed = []
    p = Pipeline(asr, mt or StubMt(), n_workers=n_workers, diarizer=diarizer,
                 printer=printed.append, clock=clock)
    for k, i in enumerate(ids):
        p.submit(make_segment(i, device=devices[k] if devices else "mic", end_wall=end_wall))
    p.close()
    return printed, p


def test_each_line_joins_the_right_segment():
    printed, _ = run(StubAsr(), [1, 2, 3])
    assert [r.segment_id for r in printed] == [1, 2, 3]
    for r in printed:
        assert r.armenian == f"hy-{r.segment_id}"
        assert r.english == f"en-hy-{r.segment_id}"
        assert r.start == 10.0 * r.segment_id


def test_lines_print_in_order_of_speech_end():
    """3 workers; ASR finishes 3, 2, 1 (gates); lines still print 1, 2, 3 (D13, P3)."""
    asr = StubAsr(num_workers=3, waits={1: 2, 2: 3})
    printed, _ = run(asr, [1, 2, 3], n_workers=3)
    assert asr.finish_order == [3, 2, 1]
    assert [r.segment_id for r in printed] == [1, 2, 3]


def test_mic_segments_are_always_me():
    printed, _ = run(StubAsr(), [1, 2, 3])
    assert {r.speaker for r in printed} == {"Me"}


def test_system_segment_without_diarizer_is_refused():
    """G2 / D27 E4: refused loudly, never mislabelled."""
    p = Pipeline(StubAsr(), StubMt(), printer=lambda r: None)
    with pytest.raises(PipelineError, match="system audio needs a diarizer"):
        p.submit(make_segment(1, device="system"))
    p.close()


def test_unknown_device_is_refused():
    """G2."""
    p = Pipeline(StubAsr(), StubMt(), diarizer=StubDiarizer(), printer=lambda r: None)
    with pytest.raises(PipelineError, match="unknown device 'speaker'"):
        p.submit(make_segment(1, device="speaker"))
    p.close()


def test_system_lines_get_the_diarizer_label():
    """G3: mixed devices; system lines carry the label, mic lines are "Me";
    the diarizer is called for system segments only."""
    diarizer = StubDiarizer()
    printed, _ = run(StubAsr(), [1, 2, 3, 4], diarizer=diarizer,
                     devices=["mic", "system", "mic", "system"])
    assert [(r.segment_id, r.speaker) for r in printed] == [
        (1, "Me"), (2, "Speaker 2"), (3, "Me"), (4, "Speaker 4")]
    assert diarizer.calls == [2, 4]


def test_line_waits_for_a_late_label():
    """G3: the label arrives after the text; the line still prints, in order, with its label."""
    mt = StubMt()
    diarizer = StubDiarizer(wait_for=mt.done)  # label only after a translation has finished
    printed, _ = run(StubAsr(), [1, 2], diarizer=diarizer, devices=["system", "mic"], mt=mt)
    assert [(r.segment_id, r.speaker) for r in printed] == [(1, "Speaker 1"), (2, "Me")]


def test_empty_asr_text_prints_no_line_and_later_lines_still_print():
    """P4: segment 2 has empty ASR text: no MT call, no line; 3 still prints after it."""
    asr = StubAsr(num_workers=2, empty={2}, waits={3: 2})
    printed, _ = run(asr, [1, 2, 3], n_workers=2)
    assert [r.segment_id for r in printed] == [1, 3]


def test_empty_asr_text_on_system_segment_is_labelled_but_prints_no_line():
    """G4: the diarizer still sees segment 2; no line for it; 3 still prints."""
    diarizer = StubDiarizer()
    printed, _ = run(StubAsr(empty={2}), [1, 2, 3], diarizer=diarizer,
                     devices=["system", "system", "system"])
    assert [(r.segment_id, r.speaker) for r in printed] == [(1, "Speaker 1"), (3, "Speaker 3")]
    assert diarizer.calls == [1, 2, 3]


def test_latency_is_print_time_minus_end_wall():
    printed, _ = run(StubAsr(), [1], clock=lambda: 100.0, end_wall=97.5)
    assert printed[0].latency == pytest.approx(2.5)


def test_worker_error_fails_loudly():
    printed = []
    p = Pipeline(StubAsr(fail={2}), StubMt(), printer=printed.append)
    for i in [1, 2, 3]:
        p.submit(make_segment(i))
    with pytest.raises(PipelineError, match="ASR failed on segment 2"):
        p.close()
    assert 3 not in [r.segment_id for r in printed]  # P7: the pipeline stops after the error


@pytest.mark.parametrize("kind", ["fail", "bad"])
def test_diarizer_error_fails_loudly(kind):
    """G5: an exception or an empty label stops the pipeline with a clear error."""
    printed = []
    diarizer = StubDiarizer(**{kind: {2}})
    p = Pipeline(StubAsr(), StubMt(), diarizer=diarizer, printer=printed.append)
    for i in [1, 2, 3]:
        p.submit(make_segment(i, device="system"))
    with pytest.raises(PipelineError, match="diarizer failed on segment 2"):
        p.close()
    assert 2 not in [r.segment_id for r in printed]
    assert 3 not in [r.segment_id for r in printed]


def test_worker_count_mismatch_fails_loudly():
    with pytest.raises(PipelineError, match=r"num_workers \(1\) must equal pipeline n_workers \(2\)"):
        Pipeline(StubAsr(num_workers=1), StubMt(), n_workers=2)
