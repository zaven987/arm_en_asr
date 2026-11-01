"""Pipeline: Segments -> ASR -> MT -> joined Record -> output (DECISIONS D1, D12, D13; M3 S7 decisions P1-P9, 2026-11-01).

Threads (D1, P2):
    submit() ──► segment_queue ──► ASR workers (N, one shared model) ──► mt_queue ──► MT thread ──┐
                                        └── empty ASR text: skipped (P4) ──────────────────────────┤
                                                                                                    ▼
                                                    out_queue ──► output thread (join, order, latency, print)

Order (D13, P3): each segment gets a sequence number when it is submitted, i.e. when its end was
detected. The output thread prints results in that order; a finished result waits until every
earlier segment has been printed or skipped (L5).
Errors (P7): any exception in a worker thread is stored, the pipeline stops working, and
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
_STOP = None         # queue sentinel


class PipelineError(Exception):
    """Pipeline problem the user must see (worker error, bad setup)."""


class Pipeline:
    def __init__(self, asr, mt, n_workers: int = 1,
                 printer: Callable[[Record], None] = print_line,
                 clock: Callable[[], float] = time.monotonic):
        """P1. `asr` has .transcribe(audio) -> str and .num_workers; `mt` has .translate(text) -> str."""
        if n_workers < 1:
            raise PipelineError(f"n_workers must be >= 1, got {n_workers}")
        # P9 / D3: faster-whisper num_workers must equal the number of ASR worker threads.
        asr_workers = getattr(asr, "num_workers", None)
        if asr_workers != n_workers:
            raise PipelineError(
                f"ASR num_workers ({asr_workers}) must equal pipeline n_workers ({n_workers}) (D3)")
        self._asr, self._mt = asr, mt
        self._printer, self._clock = printer, clock
        self._seg_q: queue.Queue = queue.Queue()   # unbounded: nothing is dropped (P2, D1)
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
        self._mt_thread = threading.Thread(target=self._mt_worker, name="mt", daemon=True)
        self._out_thread = threading.Thread(target=self._output_worker, name="output", daemon=True)
        for t in (*self._asr_threads, self._mt_thread, self._out_thread):
            t.start()

    # ------------------------------------------------------------ public

    def submit(self, segment: Segment) -> None:
        """Called from a capture thread for each finished Segment, in the order their ends are detected."""
        self.check()
        if segment.device != "mic":
            # P5: system audio needs the diarizer (M5/M6); refuse it loudly, never mislabel it.
            raise PipelineError(
                f"segment {segment.id}: device {segment.device!r} is not supported until M5/M6")
        with self._lock:
            if self._closed:
                raise PipelineError(f"segment {segment.id} submitted after close()")
            seq = self._next_seq
            self._next_seq += 1
        self._seg_q.put((seq, segment))

    def check(self) -> None:
        """Raise the stored worker error, if any (P7). The app can call this while running."""
        if self._error is not None:
            raise self._error

    def close(self) -> None:
        """P8: no more input. Drain everything submitted (print or skip), stop all threads, raise any error."""
        with self._lock:
            self._closed = True
        for _ in self._asr_threads:
            self._seg_q.put(_STOP)
        for t in self._asr_threads:
            t.join()
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
                self._out_q.put((seq, None))  # P4: skipped, but its place in the order is released
            else:
                self._mt_q.put((seq, seg, armenian))

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
            self._out_q.put((seq, (seg, armenian, english)))

    def _output_worker(self) -> None:
        pending: dict[int, tuple | None] = {}
        next_seq = 0
        while (item := self._out_q.get()) is not _STOP:
            if self._failed.is_set():
                continue
            seq, result = item
            pending[seq] = result
            while next_seq in pending:  # P3: print in submit order
                result = pending.pop(next_seq)
                next_seq += 1
                if result is None:
                    continue  # P4: empty ASR text, no line
                seg, armenian, english = result
                try:
                    record = Record(
                        segment_id=seg.id,
                        speaker=MIC_SPEAKER,
                        start=seg.start,
                        armenian=armenian,
                        english=english,
                        latency=self._clock() - seg.end_wall,  # P6 / D12: measured just before printing
                    )
                    self._printer(record)
                except Exception as e:
                    self._fail("output", seg.id, e)
                    break
