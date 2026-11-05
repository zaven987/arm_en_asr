"""Diarizer: online speaker clustering for system audio (DECISIONS D9, D27; M6 S4 J1-J8,
M6 S5 K1-K8, 2026-11-05).

Parts (K1):
  SpeakerClusters - the clustering rules only: plain numpy, no model (tested on made-up vectors).
  Embedder        - the speaker-embedding model: sherpa-onnx 1.13.8, WeSpeaker ResNet34, CPU,
                    1 thread (J1-J3, J7). embed(audio) -> unit vector, or None if not ready.
  Diarizer        - Embedder + SpeakerClusters; label(segment) -> "Speaker N" (pipeline G3).

Rules (D27 "M6 clustering", J8, K2, K3). Embeddings are L2-normalised; score = cosine similarity
with a speaker's centroid; speech length = segment.end - segment.start.
  - Long segment (speech >= SHORT_S = 2.0 s): best score >= threshold -> joins that speaker and
    updates its centroid; otherwise a new "Speaker N" (numbered in order of appearance) whose
    centroid starts with this embedding.
  - Short segment (< 2.0 s): joins the speaker with the nearest centroid, with no threshold;
    never creates a speaker (except Speaker 1 when none exists) and never updates a centroid.
  - Centroid = normalised mean of the speaker's long-segment embeddings.
  - K3 (a), option B (Zaven, 2026-11-05, replaces the short-vs-long check): Speaker 1 created by
    short or not-ready segments has no centroid; until it has one, short segments simply join it,
    and the first long segment joins it with no check and starts its centroid. Known limitation:
    if a different person made the first short sound, they are merged with the first real speaker.
  - K3 (b) (Zaven): a segment sherpa-onnx cannot embed ("not ready", e.g. a click) gets the last
    assigned speaker, or Speaker 1 if there is none yet; counted in .not_ready.
THRESHOLD = 0.76 (Zaven, 2026-11-05): the middle of 0.72-0.80, the range where the mic rules pass
AND sys_01 finds its 2 speakers (tune_diarizer.py --sys01, command_outputs/m6_s5_tune_sys01_b.txt).
History: K5 first gave 0.655 (mic_01-03 only), which merged sys_01's two speakers in T1.6; tuning
on sys_01 changes R13, so sys_01 is no longer an independent check (a new 2-speaker clip is needed).
Only the pipeline's diarizer thread calls label() (G3), so there is no lock.
Errors fail loudly (working rule 2): a missing model, a bad config, a bad embedding.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import sherpa_onnx

from arm_en_asr.audio_capture import SR

if TYPE_CHECKING:
    from arm_en_asr.audio_capture import Segment

SHORT_S = 2.0      # J8: below this much speech a segment never creates a speaker or updates a centroid
THRESHOLD = 0.76   # cosine score a long segment needs to join a speaker (tune_diarizer.py --sys01)
MODEL_FILE = Path("speaker-embedding") / "wespeaker_en_voxceleb_resnet34.onnx"  # J7, under models/


class DiarizerError(Exception):
    """Diarizer problem the user must see (missing model, bad config, bad embedding)."""


def _unit(v) -> np.ndarray:
    v = np.asarray(v, dtype=np.float32).ravel()
    norm = float(np.linalg.norm(v))
    if v.size == 0 or not np.isfinite(norm) or norm == 0.0:
        raise DiarizerError(f"bad embedding (size {v.size}, norm {norm})")
    return v / norm


# ---------------------------------------------------------------- clustering (no model)

@dataclass
class _Speaker:
    label: str
    long_sum: np.ndarray | None = None    # sum of unit embeddings of long segments (the centroid)
    n_long: int = 0

    def centroid(self) -> np.ndarray | None:
        return _unit(self.long_sum) if self.n_long else None

    def add_long(self, e: np.ndarray) -> None:
        self.long_sum = e.copy() if self.long_sum is None else self.long_sum + e
        self.n_long += 1


class SpeakerClusters:
    """Online clustering. assign(embedding or None, speech_s) -> "Speaker N"."""

    def __init__(self, threshold: float, short_s: float = SHORT_S):
        if not -1.0 <= threshold <= 1.0:
            raise DiarizerError(f"threshold must be in [-1, 1], got {threshold}")
        if short_s < 0:
            raise DiarizerError(f"short_s must be >= 0, got {short_s}")
        self.threshold = float(threshold)
        self.short_s = float(short_s)
        self._speakers: list[_Speaker] = []
        self._last: _Speaker | None = None
        self.not_ready = 0

    @property
    def labels(self) -> list[str]:
        return [s.label for s in self._speakers]

    def assign(self, embedding, speech_s: float) -> str:
        if embedding is None:                      # K3 (b)
            self.not_ready += 1
            speaker = self._last if self._last is not None else self._new()
        else:
            e = _unit(embedding)
            if speech_s >= self.short_s:
                speaker = self._assign_long(e)
            else:
                speaker = self._assign_short(e)
        self._last = speaker
        return speaker.label

    # ------------------------------------------------------------ internals

    def _new(self) -> _Speaker:
        speaker = _Speaker(f"Speaker {len(self._speakers) + 1}")
        self._speakers.append(speaker)
        return speaker

    def _scored(self, e: np.ndarray) -> list[tuple[_Speaker, float]]:
        return [(s, float(np.dot(e, c))) for s in self._speakers
                if (c := s.centroid()) is not None]

    def _assign_long(self, e: np.ndarray) -> _Speaker:
        scored = self._scored(e)
        if scored:
            best, score = max(scored, key=lambda x: x[1])
            speaker = best if score >= self.threshold else self._new()
        elif self._speakers:
            speaker = self._speakers[0]   # K3 (a) B: Speaker 1 has no centroid yet -> joins, no check
        else:
            speaker = self._new()
        speaker.add_long(e)
        return speaker

    def _assign_short(self, e: np.ndarray) -> _Speaker:
        scored = self._scored(e)
        if scored:
            return max(scored, key=lambda x: x[1])[0]   # nearest centroid, no threshold
        if self._speakers:
            return self._speakers[0]      # only Speaker 1 exists, without a centroid
        return self._new()                # first segment of the session: Speaker 1


# ---------------------------------------------------------------- model

class Embedder:
    """sherpa-onnx speaker-embedding extractor (J1-J3). Never downloads anything (D15)."""

    def __init__(self, model_path: Path, num_threads: int = 1):
        model_path = Path(model_path)
        if not model_path.is_file():
            raise DiarizerError(f"model missing: {model_path} (run scripts/download_models.py)")
        if num_threads < 1:
            raise DiarizerError(f"num_threads must be >= 1, got {num_threads}")
        config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=str(model_path), num_threads=num_threads, debug=False, provider="cpu")
        if not config.validate():
            raise DiarizerError(f"sherpa-onnx rejected the extractor config for {model_path}")
        self._extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)
        self.dim = self._extractor.dim

    def embed(self, audio: np.ndarray) -> np.ndarray | None:
        """Unit-length embedding of 16 kHz float32 mono audio, or None if sherpa-onnx is not ready."""
        audio = np.asarray(audio, dtype=np.float32).ravel()
        if audio.size == 0:
            return None
        stream = self._extractor.create_stream()
        stream.accept_waveform(sample_rate=SR, waveform=audio)
        stream.input_finished()
        if not self._extractor.is_ready(stream):
            return None
        return _unit(self._extractor.compute(stream))


class Diarizer:
    """label(segment) -> "Speaker N" for system segments, called in submit order (pipeline G3)."""

    def __init__(self, model_path: Path, threshold: float = THRESHOLD, num_threads: int = 1,
                 short_s: float = SHORT_S):
        self.clusters = SpeakerClusters(threshold, short_s)   # checks the numbers before loading
        self.embedder = Embedder(model_path, num_threads)

    def label(self, segment: Segment) -> str:
        return self.clusters.assign(self.embedder.embed(segment.audio),
                                    segment.end - segment.start)
