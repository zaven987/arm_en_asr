"""D31 F4: GPU check for FastConformer CTC with the CUDA build of sherpa-onnx. Runs in .venv-fc.

    .venv-fc/bin/python scripts/check_fc_gpu.py > command_outputs/m7_f4_check.txt 2>&1

.venv-fc = requirements-fc.in (requirements.in with sherpa-onnx 1.13.8+cuda12.cudnn9 and cudart /
cuFFT / cuRAND added); .venv is not touched until F6.

Order rule (F4 diagnosis, command_outputs/m7_f4c_check.txt, m7_f4c_sherpa_cuda.txt, m7_f4d_order.txt):
the FIRST sherpa-onnx CUDA recognizer in a process must be created before onnxruntime 1.23.2
(Silero) is imported. The other way round, from_nemo_ctc(provider="cuda") crashes with a
segmentation fault. After that, Silero and more CUDA recognizers work in any order.
Guard: if onnxruntime is already imported when the first recognizer is made, the script stops
with ERROR instead of crashing.

C1  load the CUDA libraries the app's way (asr.load_cuda_libraries: nvrtc, cuBLAS, cuDNN) plus
    cudart, cuFFT, cuRAND (this script only), with RTLD_GLOBAL; a missing one is named.
C2  ldd on sherpa-onnx's onnxruntime CUDA provider library, with LD_LIBRARY_PATH set to the NVIDIA
    package lib folders for the ldd call only; any "not found" fails and is named.
R   (order rule) OfflineRecognizer.from_nemo_ctc(provider="cuda") for model.onnx and
    model.int8.onnx, before onnxruntime is imported (guarded); load time and VRAM per model.
C3  Silero VAD (onnxruntime 1.23.2) segments speech_short.wav in the same process, after R.
C4  both recognizers on speech_short.wav: text, CER against the F3 E8 text (reported only:
    sherpa-onnx computes its own features), first-call time and the median of 5 more calls.
    Empty text fails.
C5  no silent CPU fallback: each recognizer's creation must raise this process's VRAM
    (nvidia-smi), i.e. VRAM after fp32 > before, and after int8 > after fp32.
C6  RSS and VRAM printed.
Any problem stops the script with "ERROR:" and exit code 1 (working rule 2).
"""
from __future__ import annotations

import ctypes
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

FIXTURE = ROOT / "tests" / "fixtures" / "speech_short.wav"
VAD_PATH = ROOT / "models" / "silero_vad.onnx"
FC_DIR = ROOT / "models" / "fastconformer-hy-ctc"
MODELS = {"fp32": FC_DIR / "model.onnx", "int8": FC_DIR / "model.int8.onnx"}
TOKENS = FC_DIR / "tokens.txt"
EXTRA_CUDA_PACKAGES = ("cuda_runtime", "cufft", "curand")   # C1: needed by onnxruntime CUDA
APP_CUDA_PACKAGES = ("cuda_nvrtc", "cublas", "cudnn")       # what asr.load_cuda_libraries loads
# F3 E8 output (NeMo = ONNX fp32 = ONNX int8, command_outputs/m7_f3_export.txt)
E8_TEXT = "Սակայն այս առումով Շենգենգոտին աշխատում է ինչպես մեկ պետություն։"
REPEATS = 5
SR_FC = 16000   # FastConformer sample rate (F3 E3); audio_capture.SR is not imported before R,
                # because audio_capture imports onnxruntime (order rule)


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def log(msg: str) -> None:
    print(msg, flush=True)


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def nvidia_lib_dirs(packages) -> list[Path]:
    try:
        import nvidia
    except ImportError:
        fail("C1: no nvidia packages installed in this environment (requirements-fc.in)")
    roots = [Path(p) for p in nvidia.__path__]
    dirs = []
    for package in packages:
        found = [r / package / "lib" for r in roots if (r / package / "lib").is_dir()]
        if not found:
            fail(f"C1: nvidia/{package}/lib not found in " + ", ".join(map(str, roots))
                 + " (requirements-fc.in)")
        dirs.extend(found)
    return dirs


def load_libs(packages) -> int:
    n = 0
    for d in nvidia_lib_dirs(packages):
        libs = sorted(d.glob("lib*.so*"))
        if not libs:
            fail(f"C1: no lib*.so* in {d}")
        for so in libs:
            try:
                ctypes.CDLL(str(so), mode=ctypes.RTLD_GLOBAL)
            except OSError as e:
                fail(f"C1: {so.name} cannot be loaded: {e}")
            n += 1
    return n


def rss_mb() -> float:
    import psutil
    return psutil.Process().memory_info().rss / 2**20


def vram_mb() -> float:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=False)
    except FileNotFoundError:
        fail("C5: nvidia-smi not found, so GPU use cannot be checked")
    if out.returncode != 0:
        fail(f"C5: nvidia-smi failed (exit {out.returncode}): {out.stderr.strip()}")
    for line in out.stdout.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) == 2 and parts[0] == str(os.getpid()):
            return float(parts[1])
    return 0.0


def main() -> None:
    for p in [FIXTURE, VAD_PATH, TOKENS, *MODELS.values()]:
        if not p.is_file():
            fail(f"missing: {p} (fixtures: D22; models: scripts/download_models.py, D31 F3)")

    # ---------------------------------------------------------------- C1
    n_extra = load_libs(EXTRA_CUDA_PACKAGES[:1])          # cudart first
    from arm_en_asr.asr import AsrError, load_cuda_libraries
    try:
        load_cuda_libraries()                             # the app's way (D30 G4c)
    except AsrError as e:
        fail(f"C1: {e}")
    n_extra += load_libs(EXTRA_CUDA_PACKAGES[1:])
    log(f"# C1: app CUDA libraries loaded; extra cudart / cuFFT / cuRAND: {n_extra} files")

    # ---------------------------------------------------------------- C2
    import sherpa_onnx
    log(f"# sherpa-onnx {sherpa_onnx.__version__} from {Path(sherpa_onnx.__file__).parent}")
    search = [Path(sherpa_onnx.__file__).parent, Path(sherpa_onnx.__file__).parent.parent]
    providers = sorted({p for s in search for p in s.rglob("libonnxruntime_providers_cuda.so*")})
    if not providers:
        fail("C2: no libonnxruntime_providers_cuda.so in the sherpa-onnx install: not the CUDA build")
    lib_path = ":".join(str(d) for d in nvidia_lib_dirs(APP_CUDA_PACKAGES + EXTRA_CUDA_PACKAGES))
    for prov in providers:
        out = subprocess.run(["ldd", str(prov)], capture_output=True, text=True,
                             env=dict(os.environ, LD_LIBRARY_PATH=lib_path))
        missing = [line.strip() for line in out.stdout.splitlines() if "not found" in line]
        log(f"# C2: {prov}: {len(out.stdout.splitlines())} libraries, {len(missing)} not found")
        if missing:
            fail("C2: missing libraries for the CUDA provider: " + "; ".join(missing))

    # ---------------------------------------------------------------- R (order rule) + C5
    if "onnxruntime" in sys.modules:
        fail("order rule: onnxruntime (Silero) was imported before the first sherpa-onnx CUDA "
             "recognizer; this crashes with a segmentation fault (F4 diagnosis)")
    recognizers = {}
    vram_prev = vram_mb()
    log(f"# R: VRAM before any recognizer: {vram_prev:.0f} MB")
    for name, path in MODELS.items():
        t0 = time.monotonic()
        recognizers[name] = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
            model=str(path), tokens=str(TOKENS), num_threads=1, sample_rate=SR_FC, feature_dim=80,
            decoding_method="greedy_search", debug=False, provider="cuda")
        load_s = time.monotonic() - t0
        v = vram_mb()
        log(f"# R: {name} recognizer created (provider cuda): load {load_s:.1f} s, "
            f"VRAM {v:.0f} MB (+{v - vram_prev:.0f}), RSS {rss_mb():.0f} MB")
        if v <= vram_prev:
            fail(f"C5: {name}: creating the recognizer did not raise this process's GPU memory "
                 f"({vram_prev:.0f} -> {v:.0f} MB): sherpa-onnx may run it on the CPU "
                 "(no silent fallback, working rule 2)")
        vram_prev = v

    # ---------------------------------------------------------------- C3
    import onnxruntime
    from arm_en_asr.audio_capture import SR, Segmenter, SileroVad, WavSource, new_id_counter, run_capture
    segments: list = []
    run_capture(WavSource(FIXTURE, realtime=False),
                Segmenter("mic", SileroVad(VAD_PATH), new_id_counter()), segments.append)
    if not segments:
        fail("C3: Silero found no segment in the speech fixture")
    log(f"# C3: onnxruntime {onnxruntime.__version__} (Silero) + sherpa-onnx in one process: "
        f"{len(segments)} segment(s): " + ", ".join(f"{s.start:.2f}-{s.end:.2f}s" for s in segments))

    # ---------------------------------------------------------------- C4
    import numpy as np
    import wave
    with wave.open(str(FIXTURE), "rb") as w:
        if w.getframerate() != SR or w.getnchannels() != 1 or w.getsampwidth() != 2:
            fail(f"C4: {FIXTURE} must be 16 kHz mono 16-bit")
        audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    log(f"# C4: fixture {FIXTURE.name}: {len(audio) / SR:.2f} s")
    for name, rec in recognizers.items():
        def run() -> tuple[str, float]:
            stream = rec.create_stream()
            stream.accept_waveform(SR, audio)
            t = time.monotonic()
            rec.decode_stream(stream)
            return stream.result.text, time.monotonic() - t

        text, first_s = run()
        times = [run()[1] for _ in range(REPEATS)]
        if not text.strip():
            fail(f"C4: {name}: empty text on the speech fixture")
        c = edit_distance(text, E8_TEXT) / len(E8_TEXT)
        log(f"# C4: {name}: first call {first_s:.3f} s, median of {REPEATS} "
            f"{statistics.median(times):.3f} s (max {max(times):.3f} s); CER vs E8 {100 * c:.1f} %")
        log(f"# C4: {name} text: {text}")
    # ---------------------------------------------------------------- C6
    log(f"# C6: end: VRAM {vram_mb():.0f} MB, RSS {rss_mb():.0f} MB (both recognizers + Silero loaded)")
    log("CHECK OK")


if __name__ == "__main__":
    main()
