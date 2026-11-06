"""ASR: Armenian speech -> Armenian text (DECISIONS D34; before it D3, D26, D30, D32 for Whisper).

D34: NVIDIA FastConformer CTC (stt_hy_fastconformer_hybrid_large_pc, CTC head, exported by
scripts/export_fastconformer.py, D31 F3), fp32, greedy decoding, run by sherpa-onnx (CUDA build)
on the MX550 GPU. One Asr object holds one recognizer; each call transcribes one Segment's audio,
independently of every other segment. CTC cannot loop (D25), so there is no token cap and no
" ..." marker any more (L11 is history).

No silent fallbacks (working rule 2):
- no GPU, or a CUDA library missing -> AsrError; never a CPU fallback (D7, D30)
- N3: sherpa-onnx can fall back to the CPU by itself when the CUDA provider fails, so after the
  recognizer is created this process's GPU memory (nvidia-smi) must have risen, else AsrError
- D33: the first sherpa-onnx CUDA recognizer in a process must be created before onnxruntime
  (Silero, audio_capture) is imported; otherwise it crashes with a segmentation fault. The guard
  raises AsrError instead. After the first one, Asr objects can be created in any order.
The CUDA libraries come from the pip NVIDIA packages and are loaded here, so no LD_LIBRARY_PATH
is needed (D30 G4c).
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path

import ctranslate2
import numpy as np

SR = 16000
MODEL_FILE = "model.onnx"      # N1: fp32 (int8 rejected for the GPU, D31 F5)
TOKENS_FILE = "tokens.txt"
PROVIDER = "cuda"              # N1: MX550 GPU (D7, D30)
NUM_THREADS = 1                # N1: CPU threads sherpa-onnx may use (D31 F5)
FEATURE_DIM = 80               # NeMo preprocessor features (F3 E3)
NUM_WORKERS = 1                # D28 / N2: one recognizer, one ASR worker
# D30 G4c + D34 N2: lib folders under nvidia/, loaded in this order (as check_fc_gpu.py C1):
# cudart first; nvrtc / cuBLAS / cuDNN; cuFFT / cuRAND for onnxruntime's CUDA provider.
CUDA_LIB_PACKAGES = ("cuda_runtime", "cuda_nvrtc", "cublas", "cudnn", "cufft", "curand")
WARM_UP_S = 1.0                # W2: seconds of silence decoded once at startup (first CUDA call
                               # 0.2 s vs 0.02 s later, D31 F4)


class AsrError(Exception):
    """ASR problem the user must see (missing model, no GPU, missing CUDA library, D33)."""


_cuda_libraries_loaded = False
_cuda_recognizer_created = False   # D33: set once the first CUDA recognizer exists in this process


def load_cuda_libraries() -> None:
    """D30 G4c: load the CUDA libraries from the installed NVIDIA pip packages with RTLD_GLOBAL,
    so CTranslate2 and onnxruntime find them without LD_LIBRARY_PATH.
    Runs once per process; anything missing raises AsrError naming it."""
    global _cuda_libraries_loaded
    if _cuda_libraries_loaded:
        return
    try:
        import nvidia
    except ImportError:
        raise AsrError("CUDA libraries missing: the nvidia-*-cu12 packages are not installed in "
                       "this environment (D30, D34; see requirements.txt)") from None
    roots = [Path(p) for p in nvidia.__path__]
    for package in CUDA_LIB_PACKAGES:
        lib_dirs = [r / package / "lib" for r in roots if (r / package / "lib").is_dir()]
        libs = sorted(so for d in lib_dirs for so in d.glob("lib*.so*"))
        if not libs:
            raise AsrError(f"CUDA libraries missing: no lib*.so* for nvidia/{package} in "
                           + ", ".join(str(r) for r in roots) + " (D30, D34)")
        for so in libs:
            try:
                ctypes.CDLL(str(so), mode=ctypes.RTLD_GLOBAL)
            except OSError as e:
                raise AsrError(f"CUDA library {so.name} cannot be loaded: {e} (D30)") from e
    _cuda_libraries_loaded = True


def process_vram_mb() -> float:
    """N3: this process's GPU memory in MiB from nvidia-smi (0 if it is not listed)."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, check=False)
    except FileNotFoundError:
        raise AsrError("nvidia-smi not found, so GPU use cannot be checked (D34 N3)") from None
    except subprocess.TimeoutExpired:
        raise AsrError("nvidia-smi did not answer within 10 s (D34 N3)") from None
    if out.returncode != 0:
        raise AsrError(f"nvidia-smi failed (exit {out.returncode}): {out.stderr.strip()} (D34 N3)")
    for line in out.stdout.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) == 2 and parts[0] == str(os.getpid()):
            return float(parts[1])
    return 0.0


class Asr:
    def __init__(self, model_dir: Path | str, num_workers: int = NUM_WORKERS):
        global _cuda_recognizer_created
        self.model_dir = Path(model_dir)
        self.num_workers = num_workers  # P9: Pipeline checks it equals its n_workers (D3)
        if num_workers != NUM_WORKERS:
            raise AsrError(f"num_workers must be {NUM_WORKERS} (D28, D34 N2: one recognizer, "
                           f"one worker), got {num_workers}")
        # A6: check ourselves, so a missing file gives a clear error (D15).
        for name in (MODEL_FILE, TOKENS_FILE):
            if not (self.model_dir / name).is_file():
                raise AsrError(f"model missing: FastConformer CTC {name} at {self.model_dir} "
                               "(run scripts/download_models.py)")
        # D30 G4a: GPU required; never a CPU fallback (D7, working rule 2).
        if ctranslate2.get_cuda_device_count() == 0:
            raise AsrError("GPU required (D30, D34): no CUDA device found")
        load_cuda_libraries()  # D30 G4c
        if not _cuda_recognizer_created and "onnxruntime" in sys.modules:
            raise AsrError("D33: onnxruntime (Silero) was imported before the first FastConformer "
                           "CUDA recognizer in this process; build Asr before importing "
                           "audio_capture (otherwise sherpa-onnx crashes)")
        import sherpa_onnx
        vram_before = process_vram_mb()
        self._recognizer = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
            model=str(self.model_dir / MODEL_FILE),
            tokens=str(self.model_dir / TOKENS_FILE),
            num_threads=NUM_THREADS,
            sample_rate=SR,
            feature_dim=FEATURE_DIM,
            decoding_method="greedy_search",
            debug=False,
            provider=PROVIDER,
        )
        _cuda_recognizer_created = True
        self.vram_added_mb = process_vram_mb() - vram_before
        if self.vram_added_mb <= 0:
            raise AsrError(f"FastConformer did not load onto the GPU: this process's GPU memory "
                           f"did not rise ({vram_before:.0f} MB before, {vram_before + self.vram_added_mb:.0f} "
                           "MB after); sherpa-onnx may have fallen back to the CPU (D34 N3)")

    def warm_up(self) -> None:
        """W2: decode WARM_UP_S of silence once and discard the result, so the first real
        segment of a session does not pay the first-call cost. Called while models load."""
        self.transcribe(np.zeros(int(WARM_UP_S * SR), dtype=np.float32))

    def transcribe(self, audio: np.ndarray) -> str:
        """A4: float32 mono 16 kHz audio -> Armenian text (stripped); "" if nothing is recognised."""
        stream = self._recognizer.create_stream()
        stream.accept_waveform(SR, audio)
        self._recognizer.decode_stream(stream)
        return stream.result.text.strip()
