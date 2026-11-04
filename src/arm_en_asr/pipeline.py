"""Pipeline: Segments -> ASR -> MT (+ diarizer) -> joined Record -> output
(DECISIONS D1, D12, D13, D27; M3 S7 decisions P1-P9, 2026-11-01; M5 S1 decisions G1-G7, 2026-11-04).

Threads (D1, P2, G3):
    submit() ──► segment_queue ──► ASR workers (N, one shared model) ──► mt_queue ──► MT thread ──┐
         │                              └── empty ASR text: skipped (P4) ──────────────────────────┤
         └── system segments only ──► diarizer_queue ──► diarizer thread ("Speaker N") ────────────┤
                                                                                                    ▼
                                                    out_queue ──► output thread (join, order, latency, print)

Order (D13, P3): each segment gets a sequence number when it is submitted, i.e. when its end was
detected. The output thread prints results in that order; a finished result waits until every
earlier segment has been printed or skipped (L5).
Join (G3, G4): a mic segment is complete when its text result has arrived ("Me", L6); a system
segment also needs its diarizer label. A system segment with empty ASR text is still labelled (so
clustering sees all speech), then skipped like any empty segment.
Errors (P7, G5): any exception in a worker thread is stored, the pipeline stops working, and
check() / submit() / close() raise PipelineError naming the stage and segment id.
"""
from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from arm_en_asr.output import Record, print_line

if TYPE_CHECKING:
    from arm_en_asr.audio_capture import Segment

MIC_SPEAKER = "Me"   # L6: everything from the mic is "Me"
DEVICES = ("mic", "system")
_STOP = None         # queue sentinel
_TEXT, _LABEL = "text", "label"   # kinds of out_queue messages (G3)


class PipelineError(Exception):
    """Pipeline problem the user must see (worker error, bad setup)."""


class Pipeline:
    def __init__(self, asr, mt, n_workers: int = 1, diarizer=None,
                 printer: Callable[[Record], None] = print_line,
                 clock: Callable[[], float] = time.monotonic):
        """P1, G1. `asr` has .transcribe(audio) -> str and .num_workers; `mt` has .translate(text) -> str;
        `diarizer` (optional) has .label(segment) -> str, e.g. "Speaker 1"."""
        if n_workers < 1:
            raise PipelineError(f"n_workers must be >= 1, got {n_workers}")
        # P9 / D3: faster-whisper num_workers must equal the number of ASR worker threads.
        asr_workers = getattr(asr, "num_workers", None)
        if asr_workers != n_workers:
            raise PipelineError(
                f"ASR num_workers ({asr_workers}) must equal pipeline n_workers ({n_workers}) (D3)")
        self._asr, self._mt, self._diarizer = asr, mt, diarizer
        self._printer, self._clock = printer, clock
        self._seg_q: queue.Queue = queue.Queue()   # unbounded: nothing is dropped (P2, D1)
        self._diar_q: queue.Queue = queue.Queue()
        self._mt_q: queue.Queue = queue.Queue()
        self._out_q: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._next_seq = 0
        self._closed = False
        self._error: PipelineError | None = None
        self._failed = threading.Event()

        self._asr_threads = [
            threading.Thread(target=self._asr_worker, name=f"asr-{i + 1}", daemon=True)
            for i in range(n_workers)
        ]
        # G3: the diarizer thread exists only when a diarizer is given.
        self._diar_thread = (
            threading.Thread(target=self._diar_worker, name="diarizer", daemon=True)
            if diarizer is not None else None
        )
        self._mt_thread = threading.Thread(target=self._mt_worker, name="mt", daemon=True)
        self._out_thread = threading.Thread(target=self._output_worker, name="output", daemon=True)
        for t in (*self._asr_threads, self._diar_thread, self._mt_thread, self._out_thread):
            if t is not None:
                t.start()

    # ------------------------------------------------------------ public

    def submit(self, segment: Segment) -> None:
        """Called from a capture thread for each finished Segment, in the order their ends are detected."""
        self.check()
        # G2: refuse loudly, never mislabel (working rule 2, D27 E4).
        if segment.device not in DEVICES:
            raise PipelineError(f"segment {segment.id}: unknown device {segment.device!r}")
        if segment.device == "system" and self._diarizer is None:
            raise PipelineError(f"segment {segment.id}: system audio needs a diarizer (none given)")
        with self._lock:
            if self._closed:
                raise PipelineError(f"segment {segment.id} submitted after close()")
            seq = self._next_seq
            self._next_seq += 1
        if segment.device == "system":
            self._diar_q.put((seq, segment))
        self._seg_q.put((seq, segment))

    def check(self) -> None:
        """Raise the stored worker error, if any (P7). The app can call this while running."""
        if self._error is not None:
            raise self._error

    def close(self) -> None:
        """P8, G6: no more input. Drain everything submitted (print or skip), stop all threads,
        raise any error. Order: ASR workers and diarizer, then MT, then output."""
        with self._lock:
            self._closed = True
        for _ in self._asr_threads:
            self._seg_q.put(_STOP)
        if self._diar_thread is not None:
            self._diar_q.put(_STOP)
        for t in self._asr_threads:
            t.join()
        if self._diar_thread is not None:
            self._diar_thread.join()
        self._mt_q.put(_STOP)
        self._mt_thread.join()
        self._out_q.put(_STOP)
        self._out_thread.join()
        self.check()

    # ------------------------------------------------------------ workers

    def _fail(self, stage: str, segment_id: int | None, exc: BaseException) -> None:
        where = f" on segment {segment_id}" if segment_id is not None else ""
        with self._lock:
            if self._error is None:  # keep the first error
                err = PipelineError(f"{stage} failed{where}: {exc!r}")
                err.__cause__ = exc
                self._error = err
        self._failed.set()

    def _asr_worker(self) -> None:
        while (item := self._seg_q.get()) is not _STOP:
            if self._failed.is_set():
                continue  # P7: stop working, but keep draining so close() never hangs
            seq, seg = item
            try:
                armenian = self._asr.transcribe(seg.audio).strip()
            except Exception as e:
                self._fail("ASR", seg.id, e)
                continue
            if not armenian:
                self._out_q.put((_TEXT, seq, seg, None))  # P4: skipped, but its place in the order is released
            else:
                self._mt_q.put((seq, seg, armenian))

    def _diar_worker(self) -> None:
        """G3: label system segments one by one, in submit order (clustering depends on order)."""
        while (item := self._diar_q.get()) is not _STOP:
            if self._failed.is_set():
                continue
            seq, seg = item
            try:
                label = self._diarizer.label(seg)
                if not isinstance(label, str) or not label.strip():
                    # G5: a missing label is an error, never a blank speaker on the line.
                    raise ValueError(f"diarizer returned {label!r}, expected a non-empty str")
            except Exception as e:
                self._fail("diarizer", seg.id, e)
                continue
            self._out_q.put((_LABEL, seq, seg, label))

    def _mt_worker(self) -> None:
        while (item := self._mt_q.get()) is not _STOP:
            if self._failed.is_set():
                continue
            seq, seg, armenian = item
            try:
                english = self._mt.translate(armenian)
            except Exception as e:
                self._fail("MT", seg.id, e)
                continue
            self._out_q.put((_TEXT, seq, seg, (armenian, english)))

    def _output_worker(self) -> None:
        texts: dict[int, tuple[Segment, tuple[str, str] | None]] = {}
        labels: dict[int, str] = {}
        next_seq = 0
        while (item := self._out_q.get()) is not _STOP:
            if self._failed.is_set():
                continue
            kind, seq, seg, value = item
            if kind == _TEXT:
                texts[seq] = (seg, value)
            else:
                labels[seq] = value
            while next_seq in texts:  # P3: print in submit order
                seg, result = texts[next_seq]
                if seg.device == "system" and next_seq not in labels:
                    break  # G3: wait for the diarizer label
                del texts[next_seq]
                speaker = labels.pop(next_seq, MIC_SPEAKER)
                next_seq += 1
                if result is None:
                    continue  # P4 / G4: empty ASR text, no line
                armenian, english = result
                try:
                    record = Record(
                        segment_id=seg.id,
                        speaker=speaker,
                        start=seg.start,
                        armenian=armenian,
                        english=english,
                        latency=self._clock() - seg.end_wall,  # P6 / D12: measured just before printing
                    )
                    self._printer(record)
                except Exception as e:
                    self._fail("output", seg.id, e)
                    break
