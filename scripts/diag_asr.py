"""Latency fix diagnosis: Whisper speed / repetition-loop variants (handover 008; G1-G8, 2026-11-01).

Read-only for the app: imports the app's capture code so the segments are exactly the ones the
app sees, and loads faster-whisper with the same arguments as src/arm_en_asr/asr.py, but never
changes asr.py. Runs in .venv.

    python scripts/diag_asr.py eval/clips/mic_01.wav > command_outputs/latency_diag_asr.txt 2>&1
    python scripts/diag_asr.py eval/clips/mic_0{1,2,3}.wav --variants a,b+c+g   # G4 f: combination

G1  segments: WavSource(realtime=False) + SileroVad + Segmenter, as in app.py.
G2  per segment and variant: length, ASR time, tokens, decode passes, compression ratio,
    avg log-probability, looped; per variant: total / max ASR time, loops, whole-clip CER.
G3  encoder-only time per segment (one pass on the padded 30 s window).
G4  variants (one change each from the current setting beam 5, temperature 0, cpu_threads 4):
      a  current setting            d1 repetition_penalty=1.1    e  cpu_threads=8
      b  beam_size=1                d2 repetition_penalty=1.3    g  without_timestamps=True
      c  max_new_tokens = ceil(rate x segment length x 1.5)
      d3 no_repeat_ngram_size=8
    "x+y" combines variants (f).
G5  CER: lowercase, Armenian letters and spaces only, spaces collapsed; edit distance / reference
    characters. Loops can push it above 100 %.
A missing model, clip or reference CSV stops the script with a clear error (working rule 2).
H2 (D26, 2026-11-01): --seg-cap 6,7,8 repeats the run with a shorter VAD segment cap (D8). It changes
audio_capture.CAP for this script only; audio_capture.py itself is not changed.
J1-J6 (D29 G2, 2026-11-05): GPU option. Runs in .venv-gpu with LD_LIBRARY_PATH set to the cuBLAS /
cuDNN / nvrtc lib folders before Python starts (D29 G1):
    python scripts/diag_asr.py eval/clips/mic_0{1,2,3}.wav --variants g+b+c+d1 --device cuda --compute-type int8_float16,float16
J1  --device cpu|cuda (default cpu).
J2  --compute-type: comma-separated; default int8 on cpu; required on cuda. Each one loads the model.
J3  cuda without a CUDA device, an unsupported compute type, or variant e on cuda -> clear error.
J4  memory after load + warm-up and after each variant: current RSS, peak RSS so far in this process
    (getrusage; it never goes down, so a later compute type also shows earlier peaks), swap used,
    and on cuda this process's VRAM from nvidia-smi.
J5  G3 encoder timing on cuda copies the encoder output to the CPU (to_cpu=True), so it includes a
    small copy; the cpu path is unchanged.
"""
from __future__ import annotations

import argparse
import csv
import gc
import math
import os
import re
import resource
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import arm_en_asr.audio_capture as audio_capture  # noqa: E402
from arm_en_asr.audio_capture import (  # noqa: E402
    SR, Segmenter, SileroVad, WavSource, new_id_counter, run_capture)

MODELS_DIR = ROOT / "models"
WHISPER_DIR = MODELS_DIR / "faster-whisper-small"
VAD_PATH = MODELS_DIR / "silero_vad.onnx"
META_DIR = ROOT / "eval" / "meta"
RATE_CLIPS = ["mic_01", "mic_02", "mic_03"]  # G4 c: token rate from these references

# Current setting, same as asr.py (D3 A1-A2 + temperature=0). device / compute_type: J1, J2.
BASE_LOAD = dict(device="cpu", compute_type="int8", cpu_threads=4, num_workers=1)
DEVICES = ("cpu", "cuda")  # J1
BASE_TRANSCRIBE = dict(language="hy", task="transcribe", vad_filter=False,
                       condition_on_previous_text=False, beam_size=5, temperature=0.0)

LOOP_COMPRESSION = 2.4  # faster-whisper's own compression_ratio_threshold default
CAP_MARGIN = 1.5        # G4 c
MAX_NEW_TOKENS_LIMIT = 440  # Whisper max_length 448 minus the few prompt tokens
# H1 (2026-11-01): faster-whisper passes max_length = prompt + max_new_tokens to CTranslate2
# unchanged (fw_transcribe.py lines 1416-1452), but CTranslate2 then generates at most
# floor(max_length / 2) new tokens. This rule fits every value measured in
# latency_diag_asr*.txt (e.g. 285 + 4 -> 144, 107 + 4 -> 55, uncapped 448 -> 224). So to allow
# `cap` new tokens we pass 2 x cap; the printed cap is the number of tokens actually allowed.
CT2_LENGTH_FACTOR = 2
EFFECTIVE_CAP_LIMIT = MAX_NEW_TOKENS_LIMIT // CT2_LENGTH_FACTOR  # 220

# name -> (load overrides, transcribe overrides). "cap" is filled per segment (variant c).
VARIANTS: dict[str, tuple[dict, dict]] = {
    "a": ({}, {}),
    "b": ({}, {"beam_size": 1}),
    "c": ({}, {"max_new_tokens": "cap"}),
    "d1": ({}, {"repetition_penalty": 1.1}),
    "d2": ({}, {"repetition_penalty": 1.3}),
    "d3": ({}, {"no_repeat_ngram_size": 8}),
    "e": ({"cpu_threads": 8}, {}),
    "g": ({}, {"without_timestamps": True}),
}
DEFAULT_VARIANTS = "a,b,c,d1,d2,d3,e,g"


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


# ---------------------------------------------------------------- CER (G5)

def is_armenian_letter(c: str) -> bool:
    return c.isalpha() and ("԰" <= c <= "֏" or "ﬓ" <= c <= "ﬗ")


def clean(text: str) -> str:
    kept = "".join(c if is_armenian_letter(c) else " " for c in text.lower())
    return re.sub(r" +", " ", kept).strip()


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(hyp: str, ref: str) -> float:
    ref_c, hyp_c = clean(ref), clean(hyp)
    if not ref_c:
        fail("reference text is empty after clean-up")
    return edit_distance(hyp_c, ref_c) / len(ref_c)


# ---------------------------------------------------------------- data

def read_reference(stem: str) -> tuple[str, float]:
    """Joined Armenian reference text and total duration (s) of eval/meta/<stem>.csv."""
    path = META_DIR / f"{stem}.csv"
    if not path.is_file():
        fail(f"reference CSV not found: {path}")
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        fail(f"reference CSV has no rows: {path}")
    text = " ".join(r["armenian"] for r in rows)
    duration = sum(float(r["end"]) - float(r["start"]) for r in rows)
    return text, duration


def cut_segments(wav: Path) -> list:
    """G1: the same segments the app produces (realtime=False only skips the waiting)."""
    segments: list = []
    source = WavSource(wav, realtime=False)
    segmenter = Segmenter("mic", SileroVad(VAD_PATH), new_id_counter())
    run_capture(source, segmenter, segments.append)
    return segments


# ---------------------------------------------------------------- memory (J4)

def rss_mb() -> float:
    import psutil
    return psutil.Process().memory_info().rss / 2**20


def peak_rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # Linux: KiB


def swap_mb() -> float:
    import psutil
    return psutil.swap_memory().used / 2**20


def vram_mb() -> float | None:
    """This process's GPU memory in MiB from nvidia-smi; None if nvidia-smi does not list it."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=False)
    except FileNotFoundError:
        fail("--device cuda: nvidia-smi not found, so VRAM cannot be measured")
    if out.returncode != 0:
        fail(f"nvidia-smi failed (exit {out.returncode}): {out.stderr.strip()}")
    for line in out.stdout.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) == 2 and parts[0] == str(os.getpid()):
            return float(parts[1])
    return None


def mem_text(device: str) -> str:
    text = f"RSS {rss_mb():.0f} MB, peak RSS {peak_rss_mb():.0f} MB, swap {swap_mb():.0f} MB"
    if device == "cuda":
        v = vram_mb()
        text += f", VRAM {v:.0f} MB" if v is not None else ", VRAM n/a (process not listed by nvidia-smi)"
    return text


# ---------------------------------------------------------------- model

def load_model(cpu_threads: int, device: str, compute_type: str):
    from faster_whisper import WhisperModel
    load = dict(BASE_LOAD, cpu_threads=cpu_threads, device=device, compute_type=compute_type)
    t0 = time.monotonic()
    model = WhisperModel(str(WHISPER_DIR), **load)
    print(f"# loaded faster-whisper small {load} in {time.monotonic() - t0:.1f} s", flush=True)
    return model


def token_rate(model) -> float:
    """G4 c: Whisper tokens per second of speech in the mic reference texts."""
    total_tokens, total_s = 0, 0.0
    for stem in RATE_CLIPS:
        text, duration = read_reference(stem)
        n = len(model.hf_tokenizer.encode(text, add_special_tokens=False).ids)
        print(f"# token rate: {stem}: {n} tokens / {duration:.1f} s = {n / duration:.2f} tok/s")
        total_tokens += n
        total_s += duration
    rate = total_tokens / total_s
    print(f"# token rate: all: {rate:.2f} tok/s; cap = ceil({rate:.2f} x segment s x {CAP_MARGIN})"
          f" tokens allowed, at most {EFFECTIVE_CAP_LIMIT}; passed to faster-whisper as "
          f"max_new_tokens = {CT2_LENGTH_FACTOR} x cap (H1)", flush=True)
    return rate


def encoder_time(model, audio: np.ndarray, device: str) -> float:
    """G3: one encoder pass on the 30 s window, as faster-whisper pads it.
    J5: on cuda the output is copied to the CPU, which also waits for the GPU to finish."""
    features = model.feature_extractor(audio)
    n_frames = model.feature_extractor.nb_max_frames
    features = features[:, :n_frames]
    if features.shape[1] < n_frames:
        features = np.pad(features, ((0, 0), (0, n_frames - features.shape[1])))
    if device == "cuda":
        # WhisperModel.encode has no to_cpu argument (faster-whisper 1.2.1), so call the
        # CTranslate2 encoder the same way it does, but with to_cpu=True.
        from faster_whisper.transcribe import get_ctranslate2_storage
        storage = get_ctranslate2_storage(np.expand_dims(features, 0))
        t0 = time.monotonic()
        model.model.encode(storage, to_cpu=True)
        return time.monotonic() - t0
    t0 = time.monotonic()
    out = model.encode(features)
    np.asarray(out)  # make sure the result is materialised before stopping the clock
    return time.monotonic() - t0


def run_variant(model, audio: np.ndarray, transcribe_kw: dict) -> dict:
    t0 = time.monotonic()
    pieces, _info = model.transcribe(audio, **transcribe_kw)
    pieces = list(pieces)  # decoding happens while the generator is consumed
    elapsed = time.monotonic() - t0
    tokens = sum(len(p.tokens) for p in pieces)
    return dict(
        time=elapsed,
        text=" ".join(p.text.strip() for p in pieces).strip(),
        tokens=tokens,
        passes=len({p.seek for p in pieces}),
        compression=max((p.compression_ratio for p in pieces), default=0.0),
        logprob=min((p.avg_logprob for p in pieces), default=0.0),
    )


# ---------------------------------------------------------------- main

def parse_variants(spec: str) -> list[tuple[str, dict, dict]]:
    out = []
    for name in spec.split(","):
        name = name.strip()
        load, trans = {}, {}
        for part in name.split("+"):
            if part not in VARIANTS:
                fail(f"unknown variant {part!r}; known: {', '.join(VARIANTS)}")
            pl, pt = VARIANTS[part]
            for d, add in ((load, pl), (trans, pt)):
                clash = set(d) & set(add)
                if clash:
                    fail(f"variant {name!r} sets {', '.join(clash)} twice")
                d.update(add)
        out.append((name, load, trans))
    return out


def load_clips(paths: list[Path]) -> list:
    clips = []
    for wav in paths:
        ref_text, _ = read_reference(wav.stem)
        segs = cut_segments(wav)
        if not segs:
            fail(f"VAD found no segments in {wav}")
        print(f"# {wav}: {len(segs)} segments: "
              + ", ".join(f"{s.id}:{s.start:.1f}-{s.end:.1f}s" for s in segs), flush=True)
        clips.append((wav, ref_text, segs))
    return clips


def run_one(model, rate, clips, seg_cap: float, name: str, load_kw: dict, trans_kw: dict,
            device: str, compute_type: str) -> str:
    """One variant on all clips at one segment cap; returns the summary line."""
    print(f"\n=== segment cap {seg_cap:g} s, {device} {compute_type}, variant {name}: "
          f"load {load_kw or '-'}, transcribe {trans_kw or '-'}")
    print(f"{'clip':7} {'seg':>3} {'len_s':>6} {'asr_s':>6} {'tokens':>6} {'cap':>4} "
          f"{'passes':>6} {'compr':>6} {'logprob':>7} {'loop':>4}  text (first 60 chars)")
    times, loops, cers = [], 0, []
    for wav, ref_text, segs in clips:
        hyps = []
        for s in segs:
            seg_s = len(s.audio) / SR
            kw = dict(BASE_TRANSCRIBE, **trans_kw)
            cap = None
            if kw.get("max_new_tokens") == "cap":
                cap = min(math.ceil(rate * seg_s * CAP_MARGIN), EFFECTIVE_CAP_LIMIT)
                kw["max_new_tokens"] = CT2_LENGTH_FACTOR * cap  # H1: CTranslate2 allows half
            r = run_variant(model, s.audio, kw)
            looped = r["compression"] > LOOP_COMPRESSION or (cap is not None and r["tokens"] >= cap)
            loops += looped
            times.append(r["time"])
            hyps.append(r["text"])
            print(f"{wav.stem:7} {s.id:>3} {seg_s:6.2f} {r['time']:6.2f} {r['tokens']:>6} "
                  f"{cap if cap is not None else '-':>4} {r['passes']:>6} {r['compression']:6.2f} "
                  f"{r['logprob']:7.2f} {'YES' if looped else 'no':>4}  {r['text'][:60]}",
                  flush=True)
        c = cer(" ".join(hyps), ref_text)
        cers.append((wav.stem, c))
        print(f"{wav.stem}: CER {100 * c:.1f} %", flush=True)
    line = (f"cap {seg_cap:4g} s  {device} {compute_type:12} variant {name:12} "
            f"total ASR {sum(times):6.1f} s  max {max(times):5.1f} s  loops {loops}/{len(times)}  CER "
            + ", ".join(f"{k} {100 * v:.1f} %" for k, v in cers)
            + f"  | {mem_text(device)}")  # J4
    print(line, flush=True)
    return line


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("clips", nargs="+", type=Path, help="16 kHz mono 16-bit WAVs in eval/clips/")
    ap.add_argument("--variants", default=DEFAULT_VARIANTS,
                    help=f"comma-separated; x+y combines (default {DEFAULT_VARIANTS})")
    ap.add_argument("--seg-cap", default=f"{audio_capture.CAP_S:g}",
                    help="comma-separated VAD segment caps in seconds, 1-12 (default: the app's D8 cap)")
    ap.add_argument("--device", default="cpu", choices=DEVICES, help="J1: default cpu")
    ap.add_argument("--compute-type", default=None,
                    help="J2: comma-separated CTranslate2 compute types; default int8 on cpu, "
                         "required on cuda")
    args = ap.parse_args()

    variants = parse_variants(args.variants)
    device = args.device
    # J2: never pick a GPU compute type silently.
    if args.compute_type is None:
        if device == "cuda":
            fail("--device cuda needs --compute-type (e.g. int8_float16,float16)")
        compute_types = [BASE_LOAD["compute_type"]]
    else:
        compute_types = [c.strip() for c in args.compute_type.split(",") if c.strip()]
        if not compute_types:
            fail(f"--compute-type is empty: {args.compute_type!r}")
    # J3: fail loudly before loading anything.
    import ctranslate2
    if device == "cuda":
        if ctranslate2.get_cuda_device_count() == 0:
            fail("--device cuda: ctranslate2 sees no CUDA device")
        for name, load_kw, _trans in variants:
            if "cpu_threads" in load_kw:
                fail(f"variant {name!r} changes cpu_threads, which has no meaning on cuda")
    supported = ctranslate2.get_supported_compute_types(device)
    for ct in compute_types:
        if ct not in supported:
            fail(f"compute type {ct!r} not supported on {device}; supported: "
                 + ", ".join(sorted(supported)))
    try:
        seg_caps = [float(x) for x in args.seg_cap.split(",")]
    except ValueError:
        fail(f"--seg-cap must be numbers in seconds, got {args.seg_cap!r}")
    for c in seg_caps:
        if not 1.0 <= c <= audio_capture.CAP_S:
            fail(f"--seg-cap {c:g} s is outside 1-{audio_capture.CAP_S:g} s")
    if not (WHISPER_DIR / "model.bin").is_file():
        fail(f"model missing: faster-whisper small at {WHISPER_DIR} (run scripts/download_models.py)")
    if not VAD_PATH.is_file():
        fail(f"model missing: Silero VAD {VAD_PATH} (run scripts/download_models.py)")

    import faster_whisper
    print(f"# faster-whisper {faster_whisper.__version__}; base transcribe {BASE_TRANSCRIBE}")
    print(f"# variants: {', '.join(v[0] for v in variants)}; segment caps: "
          + ", ".join(f"{c:g} s" for c in seg_caps), flush=True)
    print(f"# device {device}; compute types: {', '.join(compute_types)}; ctranslate2 "
          f"{ctranslate2.__version__}; LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH', '')}")
    swap_start = swap_mb()
    print(f"# memory at start: {mem_text(device)}", flush=True)

    model, model_key = None, None
    rate = None
    summary = []
    for seg_cap in seg_caps:
        audio_capture.CAP = int(seg_cap * SR)  # H2: this script only; Segmenter reads it at run time
        print(f"\n##### segment cap {seg_cap:g} s", flush=True)
        clips = load_clips(args.clips)
        for compute_type in compute_types:
            for name, load_kw, trans_kw in variants:
                threads = load_kw.get("cpu_threads", BASE_LOAD["cpu_threads"])
                if (threads, compute_type) != model_key:
                    model = None  # free the old model before loading the next (RAM, VRAM)
                    gc.collect()
                    model = load_model(threads, device, compute_type)
                    model_key = (threads, compute_type)
                    # Warm-up call, not timed: the first call carries one-off start-up costs.
                    list(model.transcribe(clips[0][2][0].audio, **BASE_TRANSCRIBE)[0])
                    print("# warm-up done (not counted)", flush=True)
                    print(f"# memory after load + warm-up: {mem_text(device)}", flush=True)  # J4
                    print(f"# G3 encoder-only time per segment, {device} {compute_type}, "
                          f"cpu_threads={threads} (one pass on the padded 30 s window):")
                    for wav, _ref, segs in clips:
                        for s in segs:
                            print(f"#   {wav.stem} seg {s.id}: {len(s.audio) / SR:5.2f} s audio -> "
                                  f"encoder {encoder_time(model, s.audio, device):.2f} s", flush=True)
                if trans_kw.get("max_new_tokens") == "cap" and rate is None:
                    rate = token_rate(model)
                summary.append(run_one(model, rate, clips, seg_cap, name, load_kw, trans_kw,
                                       device, compute_type))

    print("\n=== summary")
    for line in summary:
        print(line)
    print(f"swap used: start {swap_start:.0f} MB -> end {swap_mb():.0f} MB "
          f"({swap_mb() - swap_start:+.0f} MB)")


if __name__ == "__main__":
    main()
