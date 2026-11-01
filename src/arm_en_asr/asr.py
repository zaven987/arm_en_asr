"""ASR: Armenian speech -> Armenian text (DECISIONS D3, D7; M3 S4 decisions A1-A6, S7 P9, 2026-11-01).

One Asr object holds one faster-whisper model. Each call transcribes one Segment's audio,
independently of every other segment.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

CPU_THREADS = 4   # A3: leave cores for capture + MT; tuned in M4 (T4)
NUM_WORKERS = 1   # A3 / D1: default N = 1; must equal the pipeline's ASR worker count (P9)
BEAM_SIZE = 5     # A2: faster-whisper default; speed tuning belongs to M4 (R1)
TEMPERATURE = 0.0  # M4 (Zaven, 2026-11-01): decode once, no temperature fallback retries;
                   # the 5 s latency rule comes before a small loss in accuracy (R1)


class AsrError(Exception):
    """ASR problem the user must see (missing model)."""


class Asr:
    def __init__(self, model_dir: Path | str, num_workers: int = NUM_WORKERS):
        self.model_dir = Path(model_dir)
        self.num_workers = num_workers  # P9: Pipeline checks it equals its n_workers (D3)
        # A6: check ourselves. A path that does not exist would be taken as a model *name*
        # and faster-whisper would try to download it (working rule 2, D15).
        if not (self.model_dir / "model.bin").is_file():
            raise AsrError(
                f"model missing: faster-whisper small at {self.model_dir} "
                "(run scripts/download_models.py)"
            )
        # A1: CPU, int8 (D3, D7).
        self._model = WhisperModel(
            str(self.model_dir),
            device="cpu",
            compute_type="int8",
            cpu_threads=CPU_THREADS,
            num_workers=self.num_workers,
        )

    def transcribe(self, audio: np.ndarray) -> str:
        """A4: float32 mono 16 kHz audio -> Armenian text; "" if Whisper returns nothing."""
        pieces, _info = self._model.transcribe(
            audio,
            language="hy",                     # A2: Eastern Armenian only, no detection
            task="transcribe",
            vad_filter=False,                  # Silero already segments (D8)
            condition_on_previous_text=False,  # explicit; no effect on <= 12 s segments
            beam_size=BEAM_SIZE,
            temperature=TEMPERATURE,           # single value: no fallback re-decoding
        )
        # `pieces` is a generator: decoding happens while it is consumed.
        return " ".join(p.text.strip() for p in pieces).strip()
