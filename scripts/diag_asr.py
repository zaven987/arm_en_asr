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
"""
from __future__ import annotations

import argparse
import csv
import math
import re
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from arm_en_asr.audio_capture import (  # noqa: E402
    SR, Segmenter, SileroVad, WavSource, new_id_counter, run_capture)

MODELS_DIR = ROOT / "models"
WHISPER_DIR = MODELS_DIR / "faster-whisper-small"
VAD_PATH = MODELS_DIR / "silero_vad.onnx"
META_DIR = ROOT / "eval" / "meta"
RATE_CLIPS = ["mic_01", "mic_02", "mic_03"]  # G4 c: token rate from these references

# Current setting, same as asr.py (D3 A1-A2 + temperature=0).
BASE_LOAD = dict(device="cpu", compute_type="int8", cpu_threads=4, num_workers=1)
BASE_TRANSCRIBE = dict(language="hy", task="transcribe", vad_filter=False,
                       condition_on_previous_text=False, beam_size=5, temperature=0.0)

LOOP_COMPRESSION = 2.4  # faster-whisper's own compression_ratio_threshold default
CAP_MARGIN = 1.5        # G4 c
MAX_NEW_TOKENS_LIMIT = 440  # Whisper max_length 448 minus the few prompt tokens

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


# ---------------------------------------------------------------- model

def load_model(cpu_threads: int):
    from faster_whisper import WhisperModel
    load = dict(BASE_LOAD, cpu_threads=cpu_threads)
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
          f", at most {MAX_NEW_TOKENS_LIMIT}", flush=True)
    return rate


def encoder_time(model, audio: np.ndarray) -> float:
    """G3: one encoder pass on the 30 s window, as faster-whisper pads it."""
    features = model.feature_extractor(audio)
    n_frames = model.feature_extractor.nb_max_frames
    features = features[:, :n_frames]
    if features.shape[1] < n_frames:
        features = np.pad(features, ((0, 0), (0, n_frames - features.shape[1])))
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("clips", nargs="+", type=Path, help="16 kHz mono 16-bit WAVs in eval/clips/")
    ap.add_argument("--variants", default=DEFAULT_VARIANTS,
                    help=f"comma-separated; x+y combines (default {DEFAULT_VARIANTS})")
    args = ap.parse_args()

    variants = parse_variants(args.variants)
    if not (WHISPER_DIR / "model.bin").is_file():
        fail(f"model missing: faster-whisper small at {WHISPER_DIR} (run scripts/download_models.py)")
    if not VAD_PATH.is_file():
        fail(f"model missing: Silero VAD {VAD_PATH} (run scripts/download_models.py)")

    import faster_whisper
    print(f"# faster-whisper {faster_whisper.__version__}; base transcribe {BASE_TRANSCRIBE}")
    print(f"# variants: {', '.join(v[0] for v in variants)}")

    clips = []
    for wav in args.clips:
        ref_text, _ = read_reference(wav.stem)
        segs = cut_segments(wav)
        if not segs:
            fail(f"VAD found no segments in {wav}")
        print(f"# {wav}: {len(segs)} segments: "
              + ", ".join(f"{s.id}:{s.start:.1f}-{s.end:.1f}s" for s in segs), flush=True)
        clips.append((wav, ref_text, segs))

    model, model_threads = None, None
    rate = None
    summary = []
    for name, load_kw, trans_kw in variants:
        threads = load_kw.get("cpu_threads", BASE_LOAD["cpu_threads"])
        if threads != model_threads:
            model = None  # free the old model before loading the next (RAM)
            model = load_model(threads)
            model_threads = threads
            # Warm-up call, not timed: the first call carries one-off start-up costs.
            list(model.transcribe(clips[0][2][0].audio, **BASE_TRANSCRIBE)[0])
            print("# warm-up done (not counted)", flush=True)
            print("# G3 encoder-only time per segment, cpu_threads="
                  f"{threads} (one pass on the padded 30 s window):")
            for wav, _ref, segs in clips:
                for s in segs:
                    print(f"#   {wav.stem} seg {s.id}: {len(s.audio) / SR:5.2f} s audio -> "
                          f"encoder {encoder_time(model, s.audio):.2f} s", flush=True)
        if trans_kw.get("max_new_tokens") == "cap" and rate is None:
            rate = token_rate(model)

        print(f"\n=== variant {name}: load {load_kw or '-'}, transcribe {trans_kw or '-'}")
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
                    cap = min(math.ceil(rate * seg_s * CAP_MARGIN), MAX_NEW_TOKENS_LIMIT)
                    kw["max_new_tokens"] = cap
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
        line = (f"variant {name:12} total ASR {sum(times):6.1f} s  max {max(times):5.1f} s  "
                f"loops {loops}/{len(times)}  CER " + ", ".join(f"{k} {100 * v:.1f} %" for k, v in cers))
        print(line, flush=True)
        summary.append(line)

    print("\n=== summary")
    for line in summary:
        print(line)


if __name__ == "__main__":
    main()
