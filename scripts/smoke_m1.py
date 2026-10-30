"""M1 smoke run: each model once on the FLEURS smoke clip, plus a RAM check (M1, R15, R17).

Run from the repo root with .venv active, after scripts/fetch_fleurs.py:
    python scripts/smoke_m1.py 2>&1 | tee command_outputs/m1_smoke.txt

Offline only: models are loaded from models/; nothing is downloaded.
Information only: no pass/fail thresholds (those live in TEST.md).
"""
import os

os.environ["HF_HUB_OFFLINE"] = "1"  # set before any Hugging Face import (D15)

import json  # noqa: E402
import resource  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import wave  # noqa: E402
from pathlib import Path  # noqa: E402

import ctranslate2  # noqa: E402
import numpy as np  # noqa: E402
import onnxruntime as ort  # noqa: E402
import psutil  # noqa: E402
import sentencepiece as spm  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
SMOKE_JSON = ROOT / "eval" / "fleurs" / "smoke_clip.json"
WHISPER_DIR = MODELS / "faster-whisper-small"
OPUS_DIR = MODELS / "opus-mt-hy-en-ct2-int8"
SILERO_PATH = MODELS / "silero_vad.onnx"

SR = 16000
VAD_WINDOW = 512   # samples per Silero step at 16 kHz
VAD_CONTEXT = 64   # samples of previous window prepended (Silero v5/v6 ONNX interface)
PROC = psutil.Process()
MB = 1024 * 1024


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def mem(label: str) -> None:
    vm, sw = psutil.virtual_memory(), psutil.swap_memory()
    print(f"[ram] {label:<16} rss {PROC.memory_info().rss / MB:7.0f} MB | "
          f"available {vm.available / MB:6.0f} MB | swap used {sw.used / MB:6.0f} MB")


def armenian_share(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    arm = [c for c in letters if "԰" <= c <= "֏" or "ﬓ" <= c <= "ﬗ"]
    return len(arm) / len(letters) if letters else 0.0


def load_clip() -> tuple[dict, np.ndarray]:
    if not SMOKE_JSON.exists():
        fail(f"{SMOKE_JSON} missing; run scripts/fetch_fleurs.py first")
    clip = json.loads(SMOKE_JSON.read_text(encoding="utf-8"))
    wav_path = ROOT / clip["wav"]
    if not wav_path.exists():
        fail(f"clip WAV missing: {wav_path}")
    try:
        with wave.open(str(wav_path), "rb") as w:
            if w.getframerate() != SR or w.getnchannels() != 1 or w.getsampwidth() != 2:
                fail(f"{wav_path} must be 16 kHz mono 16-bit PCM (D18)")
            pcm = w.readframes(w.getnframes())
    except wave.Error as e:
        fail(f"{wav_path} is not a 16-bit PCM WAV (D18): {e}")
    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    return clip, audio


def run_vad(audio: np.ndarray) -> None:
    if not SILERO_PATH.exists():
        fail(f"model missing: {SILERO_PATH} (run scripts/download_models.py)")
    t0 = time.perf_counter()
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 1
    sess = ort.InferenceSession(str(SILERO_PATH), sess_options=opts,
                                providers=["CPUExecutionProvider"])
    names = sorted(i.name for i in sess.get_inputs())
    if names != ["input", "sr", "state"]:
        fail(f"unexpected Silero ONNX inputs {names}; expected input, sr, state")
    print(f"[vad] loaded in {time.perf_counter() - t0:.2f} s")
    mem("after VAD load")

    state = np.zeros((2, 1, 128), dtype=np.float32)
    context = np.zeros(VAD_CONTEXT, dtype=np.float32)
    sr = np.array(SR, dtype=np.int64)
    probs = []
    t0 = time.perf_counter()
    for start in range(0, len(audio) - VAD_WINDOW + 1, VAD_WINDOW):
        x = np.concatenate([context, audio[start:start + VAD_WINDOW]])[None, :]
        out, state = sess.run(None, {"input": x, "state": state, "sr": sr})
        probs.append(float(out[0][0]))
        context = x[0, -VAD_CONTEXT:]
    dt = time.perf_counter() - t0
    speech = sum(p > 0.5 for p in probs)
    print(f"[vad] {len(probs)} windows in {dt:.2f} s; speech (p > 0.5) in {speech} "
          f"({100 * speech / max(len(probs), 1):.0f} %)")


def run_asr(audio: np.ndarray) -> str:
    if not (WHISPER_DIR / "model.bin").exists():
        fail(f"model missing: {WHISPER_DIR} (run scripts/download_models.py)")
    t0 = time.perf_counter()
    model = WhisperModel(str(WHISPER_DIR), device="cpu", compute_type="int8")
    print(f"[asr] faster-whisper small int8 CPU loaded in {time.perf_counter() - t0:.2f} s")
    mem("after ASR load")

    t0 = time.perf_counter()
    segments, info = model.transcribe(audio, language="hy")
    text = " ".join(s.text.strip() for s in segments)  # generator: decoding happens here
    dt = time.perf_counter() - t0
    secs = len(audio) / SR
    print(f"[asr] {secs:.2f} s audio transcribed in {dt:.2f} s (RTF {dt / secs:.2f})")
    print(f"[asr] text: {text}")
    print(f"[asr] Armenian-letter share: {100 * armenian_share(text):.0f} %")
    mem("after ASR run")
    return text


def run_mt(sentences: dict[str, str], english_ref: str) -> None:
    for f in ("model.bin", "source.spm", "target.spm"):
        if not (OPUS_DIR / f).exists():
            fail(f"model file missing: {OPUS_DIR / f} (run scripts/download_models.py)")
    t0 = time.perf_counter()
    translator = ctranslate2.Translator(str(OPUS_DIR), device="cpu", compute_type="int8")
    sp_src = spm.SentencePieceProcessor(model_file=str(OPUS_DIR / "source.spm"))
    sp_tgt = spm.SentencePieceProcessor(model_file=str(OPUS_DIR / "target.spm"))
    print(f"[mt] opus-mt-hy-en int8 CPU loaded in {time.perf_counter() - t0:.2f} s")
    mem("after MT load")

    print(f"[mt] English reference: {english_ref}")
    for label, text in sentences.items():
        if not text.strip():
            print(f"[mt] {label}: (empty input, skipped)")
            continue
        tokens = sp_src.encode(text, out_type=str) + ["</s>"]
        t0 = time.perf_counter()
        hyp = translator.translate_batch([tokens])[0].hypotheses[0]
        dt = time.perf_counter() - t0
        english = sp_tgt.decode([t for t in hyp if t != "</s>"])
        print(f"[mt] {label} ({dt:.2f} s): {english}")
    mem("after MT run")


def main() -> None:
    print(f"[env] python {sys.version.split()[0]}, cpus {os.cpu_count()}, "
          f"ctranslate2 {ctranslate2.__version__}, onnxruntime {ort.__version__}")
    swap_start = psutil.swap_memory().used
    mem("start")

    clip, audio = load_clip()
    print(f"[clip] FLEURS id {clip['id']} ({clip['wav']}, {len(audio) / SR:.2f} s)")
    print(f"[clip] Armenian reference: {clip['armenian']}")  # R15: check this renders correctly

    run_vad(audio)
    asr_text = run_asr(audio)
    run_mt({"from ASR text": asr_text, "from reference Armenian": clip["armenian"]},
           clip["english"])

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # KiB -> MiB on Linux
    swap_delta = (psutil.swap_memory().used - swap_start) / MB
    print(f"[ram] peak rss {peak:.0f} MB | swap growth during run {swap_delta:+.0f} MB")
    print("[done] smoke run finished")


if __name__ == "__main__":
    main()
