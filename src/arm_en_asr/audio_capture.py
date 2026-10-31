"""Audio capture + VAD segmentation (DECISIONS D8, D10, D21; M3 S3 decisions V1-V7, 2026-10-31).

Flow per device:  source (parec or WAV) -> 512-sample chunks -> Silero VAD -> Segmenter -> Segment
Each device gets its own SileroVad (the model keeps state between windows) and its own Segmenter.
"""
from __future__ import annotations

import itertools
import subprocess
import time
import wave
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime as ort

SR = 16000
WINDOW = 512              # samples per Silero step at 16 kHz (32 ms)
CONTEXT = 64              # previous samples prepended (Silero v5/v6 ONNX interface)
THRESHOLD = 0.5           # V1: window is speech if p > 0.5
END_SILENCE_S = 0.6       # D8: this much non-speech ends a segment
MIN_SPEECH_S = 0.3        # D8: shorter speech is dropped
CAP_S = 12.0              # D8 / V2: hard cap on segment audio length
PAD_S = 0.2               # V3: audio kept before first and after last speech window

END_SILENCE = int(END_SILENCE_S * SR)
MIN_SPEECH = int(MIN_SPEECH_S * SR)
CAP = int(CAP_S * SR)
PAD = int(PAD_S * SR)


class CaptureError(Exception):
    """Capture problem the user must see (bad file, missing model, device lost)."""


@dataclass
class Segment:
    """Shared unit of work (DECISIONS section 8, V4)."""
    id: int
    device: str               # "mic" | "system"
    start: float              # first speech sample, seconds from session start
    end: float                # last speech sample, seconds from session start
    audio: np.ndarray         # float32, mono, 16 kHz, includes V3 padding
    end_wall: float           # time.monotonic() when the chunk with the last speech sample arrived


# ---------------------------------------------------------------- sources
# A source yields (chunk, arrival) pairs: chunk = WINDOW int16 samples, arrival = time.monotonic().

class WavSource:
    """File mode (D11). realtime=True feeds at recording speed (D21); False only for unit tests (V6)."""

    def __init__(self, path: Path | str, realtime: bool):
        self.path = Path(path)
        self.realtime = realtime
        self._stopping = False
        if not self.path.is_file():
            raise CaptureError(f"WAV not found: {self.path}")
        try:
            with wave.open(str(self.path), "rb") as w:
                if w.getframerate() != SR or w.getnchannels() != 1 or w.getsampwidth() != 2:
                    raise CaptureError(
                        f"{self.path} must be 16 kHz mono 16-bit PCM WAV, got "
                        f"{w.getframerate()} Hz, {w.getnchannels()} ch, {8 * w.getsampwidth()}-bit")
                self._pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        except wave.Error as e:
            raise CaptureError(f"{self.path} is not a PCM WAV: {e}") from None

    def stop(self) -> None:
        self._stopping = True

    def chunks(self) -> Iterator[tuple[np.ndarray, float]]:
        t0 = time.monotonic()
        for i, pos in enumerate(range(0, len(self._pcm), WINDOW)):
            if self._stopping:
                return
            chunk = self._pcm[pos:pos + WINDOW]
            if len(chunk) < WINDOW:  # last partial chunk: pad with zeros (< 32 ms)
                chunk = np.concatenate([chunk, np.zeros(WINDOW - len(chunk), dtype=np.int16)])
            if self.realtime:
                # The chunk "arrives" when its last sample would have been recorded.
                delay = t0 + (i + 1) * WINDOW / SR - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
            yield chunk, time.monotonic()


class ParecSource:
    """Live mode: one parec subprocess per device (D10, V5). parec ending mid-session = device lost."""

    def __init__(self, device_name: str):
        self.device_name = device_name
        self._stopping = False
        self._proc: subprocess.Popen | None = None

    def stop(self) -> None:
        self._stopping = True
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()

    def chunks(self) -> Iterator[tuple[np.ndarray, float]]:
        cmd = ["parec", f"--device={self.device_name}", "--format=s16le",
               "--rate=16000", "--channels=1", "--raw"]
        try:
            self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except FileNotFoundError:
            raise CaptureError("`parec` not found. Install pulseaudio-utils.") from None
        try:
            nbytes = WINDOW * 2
            while True:
                data = self._proc.stdout.read(nbytes)
                if len(data) < nbytes:  # EOF: parec ended
                    if self._stopping:
                        return
                    self._proc.wait(timeout=2)
                    err = self._proc.stderr.read().decode(errors="replace").strip()
                    raise CaptureError(
                        f"device lost: {self.device_name!r} (parec exit {self._proc.returncode}"
                        + (f": {err}" if err else "") + ")")
                yield np.frombuffer(data, dtype=np.int16), time.monotonic()
        finally:
            if self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                    self._proc.wait()


# ---------------------------------------------------------------- VAD

class SileroVad:
    """Silero VAD v6.2.1 ONNX (D8, D24). One instance per device: it keeps state between windows."""

    def __init__(self, model_path: Path | str):
        model_path = Path(model_path)
        if not model_path.is_file():
            raise CaptureError(f"model missing: Silero VAD {model_path} (run scripts/download_models.py)")
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        self._sess = ort.InferenceSession(str(model_path), sess_options=opts,
                                          providers=["CPUExecutionProvider"])
        names = sorted(i.name for i in self._sess.get_inputs())
        if names != ["input", "sr", "state"]:
            raise CaptureError(f"unexpected Silero ONNX inputs {names}; expected input, sr, state")
        self._sr = np.array(SR, dtype=np.int64)
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros(CONTEXT, dtype=np.float32)

    def prob(self, chunk: np.ndarray) -> float:
        """Speech probability of one WINDOW-sample float32 chunk."""
        x = np.concatenate([self._context, chunk])[None, :]
        out, self._state = self._sess.run(None, {"input": x, "state": self._state, "sr": self._sr})
        self._context = x[0, -CONTEXT:]
        return float(out[0][0])


# ---------------------------------------------------------------- segmenter

class Segmenter:
    """Turns VAD-labelled chunks into Segments (D8, V1-V4). All positions are sample indices."""

    def __init__(self, device: str, vad: SileroVad, ids: Iterator[int]):
        self.device = device
        self.vad = vad
        self.ids = ids                      # shared counter, so ids are unique across devices
        self._pos = 0                       # samples seen so far
        self._history = np.zeros(0, dtype=np.float32)  # last PAD samples before a segment (pre-roll)
        self._in_speech = False
        self._audio: list[np.ndarray] = []  # current segment audio
        self._seg_start = 0                 # sample index of the segment's first audio sample
        self._seg_len = 0
        self._first_speech = 0              # sample index where speech starts
        self._last_speech_end = 0           # sample index just after the last speech window
        self._last_speech_wall = 0.0

    def push(self, chunk_i16: np.ndarray, arrival: float) -> list[Segment]:
        chunk = chunk_i16.astype(np.float32) / 32768.0
        is_speech = self.vad.prob(chunk) > THRESHOLD
        c_start, c_end = self._pos, self._pos + len(chunk)
        self._pos = c_end
        out: list[Segment] = []

        if not self._in_speech:
            if is_speech:
                self._open(self._history, c_start - len(self._history), c_start, arrival)
                self._extend(chunk, c_start, c_end, True, arrival, out)
            else:
                self._history = np.concatenate([self._history, chunk])[-PAD:]
            return out

        self._extend(chunk, c_start, c_end, is_speech, arrival, out)
        if self._in_speech and not is_speech and self._pos - self._last_speech_end >= END_SILENCE:
            self._close_after_silence(out)
        return out

    def flush(self) -> list[Segment]:
        """End of stream: close any open segment (V5)."""
        out: list[Segment] = []
        if self._in_speech:
            self._close_after_silence(out)
        return out

    # -- internals

    def _open(self, pre: np.ndarray, seg_start: int, first_speech: int, arrival: float) -> None:
        self._in_speech = True
        self._audio = [pre] if len(pre) else []
        self._seg_start = seg_start
        self._seg_len = len(pre)
        self._first_speech = first_speech
        self._last_speech_end = first_speech
        self._last_speech_wall = arrival

    def _extend(self, chunk: np.ndarray, c_start: int, c_end: int, is_speech: bool,
                arrival: float, out: list[Segment]) -> None:
        room = CAP - self._seg_len
        if len(chunk) <= room:
            self._audio.append(chunk)
            self._seg_len += len(chunk)
            if is_speech:
                self._last_speech_end, self._last_speech_wall = c_end, arrival
            return
        # V2: cap reached inside this chunk. Fill to exactly CAP, emit, start the next
        # segment with the rest of the chunk. No audio is lost.
        head, tail = chunk[:room], chunk[room:]
        cut = c_start + room
        self._audio.append(head)
        self._seg_len += len(head)
        if is_speech:
            self._last_speech_end, self._last_speech_wall = cut, arrival
        self._emit(self._seg_len, out)
        self._open(np.zeros(0, dtype=np.float32), cut, cut, arrival)
        self._audio = [tail]
        self._seg_len = len(tail)
        if is_speech:
            self._last_speech_end = c_end

    def _close_after_silence(self, out: list[Segment]) -> None:
        keep = min(self._last_speech_end + PAD - self._seg_start, self._seg_len)  # V3 trailing pad
        audio_all = np.concatenate(self._audio)
        self._emit(keep, out)
        # Audio after the trailing pad becomes pre-roll history for the next segment.
        self._history = audio_all[keep:][-PAD:]
        self._in_speech = False
        self._audio, self._seg_len = [], 0

    def _emit(self, keep: int, out: list[Segment]) -> None:
        if self._last_speech_end - self._first_speech < MIN_SPEECH:
            return  # D8: too short, dropped
        audio = np.concatenate(self._audio)[:keep]
        out.append(Segment(
            id=next(self.ids),
            device=self.device,
            start=self._first_speech / SR,
            end=self._last_speech_end / SR,
            audio=audio,
            end_wall=self._last_speech_wall,
        ))


# ---------------------------------------------------------------- loop

def run_capture(source, segmenter: Segmenter, emit: Callable[[Segment], None]) -> None:
    """Read the source until it ends (or is stopped), emitting each finished Segment.
    Raises CaptureError on device loss. Runs in the device's capture thread (D1)."""
    for chunk, arrival in source.chunks():
        for seg in segmenter.push(chunk, arrival):
            emit(seg)
    for seg in segmenter.flush():
        emit(seg)


def new_id_counter() -> Iterator[int]:
    """Segment ids shared by all devices, starting at 1."""
    return itertools.count(1)
