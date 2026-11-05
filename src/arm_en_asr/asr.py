"""ASR: Armenian speech -> Armenian text (DECISIONS D3, D7, D26, D30; M3 S4 decisions A1-A6, S7 P9).

One Asr object holds one faster-whisper model. Each call transcribes one Segment's audio,
independently of every other segment. D30: Whisper runs on the MX550 GPU (cuda, int8_float16);
no GPU is an error, never a CPU fallback. The CUDA libraries come from the pip NVIDIA packages and
are loaded here, so no LD_LIBRARY_PATH is needed.
"""
from __future__ import annotations

import ctypes
import math
from pathlib import Path

import ctranslate2
import numpy as np
from faster_whisper import WhisperModel

SR = 16000
DEVICE = "cuda"               # D30 G4a: Whisper on the MX550 GPU (was "cpu", D7)
COMPUTE_TYPE = "int8_float16"  # D30 G4a / D29 G2: ~5x faster than CPU int8, same loops and CER
CUDA_LIB_PACKAGES = ("cuda_nvrtc", "cublas", "cudnn")  # D30 G4c: lib folders under nvidia/
CPU_THREADS = 4   # A3: leave cores for capture + MT; tuned in M4 (T4). No effect on cuda (D30)
NUM_WORKERS = 1   # A3 / D1: default N = 1; must equal the pipeline's ASR worker count (P9)
BEAM_SIZE = 1     # D26: greedy decoding, about half the decoding time of beam 5 (latency fix)
TEMPERATURE = 0.0  # D3 (Zaven, 2026-11-01): decode once, no temperature fallback retries;
                   # the 5 s latency rule comes before a small loss in accuracy (R1)

# D26 token cap: stops a repetition loop without cutting normal speech.
TOKEN_RATE = 15.8      # Whisper tokens per second in the mic_01-03 references (diag_asr.py)
TOKEN_MARGIN = 1.5     # room above the average rate for dense speech
TOKEN_CAP_MAX = 220    # Whisper's 448-token limit, halved by CTranslate2 (below), minus the prompt
CT2_LENGTH_FACTOR = 2  # CTranslate2 generates at most half of max_length = prompt + max_new_tokens
                       # (measured in diag_asr.py H1), so we pass 2 x the tokens we want to allow
CUT_MARKER = " ..."    # D26 / L11: shown when the cap stopped the text
REPETITION_PENALTY = 1.1  # D26 addition (Zaven, 2026-11-04, W1): loops 13/31 -> 3/31 and better CER
                          # on mic_01-03 (m5_diag_asr_rp.txt); the token cap above stays as a safety net
WARM_UP_S = 1.0        # W2: seconds of silence transcribed once at startup


class AsrError(Exception):
    """ASR problem the user must see (missing model, no GPU, missing CUDA library)."""


_cuda_libraries_loaded = False


def load_cuda_libraries() -> None:
    """D30 G4c: load cuBLAS / cuDNN / nvrtc from the installed NVIDIA pip packages with RTLD_GLOBAL,
    so CTranslate2 finds them later without LD_LIBRARY_PATH (checked: m5_g4_preload.txt).
    Runs once per process; anything missing raises AsrError naming it."""
    global _cuda_libraries_loaded
    if _cuda_libraries_loaded:
        return
    try:
        import nvidia
    except ImportError:
        raise AsrError("CUDA libraries missing: the nvidia-cublas-cu12 / nvidia-cudnn-cu12 packages "
                       "are not installed in this environment (D30; see requirements.txt)") from None
    roots = [Path(p) for p in nvidia.__path__]
    for package in CUDA_LIB_PACKAGES:
        lib_dirs = [r / package / "lib" for r in roots if (r / package / "lib").is_dir()]
        libs = sorted(so for d in lib_dirs for so in d.glob("lib*.so*"))
        if not libs:
            raise AsrError(f"CUDA libraries missing: no lib*.so* for nvidia/{package} in "
                           + ", ".join(str(r) for r in roots) + " (D30)")
        for so in libs:
            try:
                ctypes.CDLL(str(so), mode=ctypes.RTLD_GLOBAL)
            except OSError as e:
                raise AsrError(f"CUDA library {so.name} cannot be loaded: {e} (D30)") from e
    _cuda_libraries_loaded = True


def token_cap(seconds: float) -> int:
    """D26: number of new tokens allowed for a segment of this length."""
    return min(math.ceil(TOKEN_RATE * seconds * TOKEN_MARGIN), TOKEN_CAP_MAX)


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
        # D30 G4a: GPU required; never a CPU fallback (D7, working rule 2).
        if ctranslate2.get_cuda_device_count() == 0:
            raise AsrError("GPU required (D30): ctranslate2 sees no CUDA device")
        load_cuda_libraries()  # D30 G4c
        self._model = WhisperModel(
            str(self.model_dir),
            device=DEVICE,
            compute_type=COMPUTE_TYPE,
            cpu_threads=CPU_THREADS,
            num_workers=self.num_workers,
        )

    def warm_up(self) -> None:
        """W2: transcribe WARM_UP_S of silence once and discard the result, so the first real
        segment of a session does not pay the first-call cost. Called while models load."""
        self.transcribe(np.zeros(int(WARM_UP_S * SR), dtype=np.float32))

    def transcribe(self, audio: np.ndarray) -> str:
        """A4: float32 mono 16 kHz audio -> Armenian text; "" if Whisper returns nothing.
        D26: if the token cap stopped the text, it ends with CUT_MARKER (L11)."""
        cap = token_cap(len(audio) / SR)
        pieces, _info = self._model.transcribe(
            audio,
            language="hy",                     # A2: Eastern Armenian only, no detection
            task="transcribe",
            vad_filter=False,                  # Silero already segments (D8)
            condition_on_previous_text=False,  # explicit; no effect on single-segment calls
            beam_size=BEAM_SIZE,
            temperature=TEMPERATURE,           # single value: no fallback re-decoding
            without_timestamps=True,           # D26: one decoding pass, far fewer loops
            max_new_tokens=CT2_LENGTH_FACTOR * cap,
            repetition_penalty=REPETITION_PENALTY,  # W1: fewer repetition loops
        )
        # `pieces` is a generator: decoding happens while it is consumed.
        pieces = list(pieces)
        text = " ".join(p.text.strip() for p in pieces).strip()
        if text and sum(len(p.tokens) for p in pieces) >= cap:
            text += CUT_MARKER
        return text
