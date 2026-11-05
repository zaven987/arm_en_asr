"""M6 S4: speaker-embedding measurement for the diarizer model choice (D27 S4, J1-J6, 2026-11-05).

Read-only for the app. Runs in .venv, once per candidate model:
    python scripts/diag_embed.py --model models/speaker-embedding/wespeaker_en_voxceleb_resnet34.onnx > command_outputs/m6_s4_embed_resnet34.txt 2>&1
    python scripts/diag_embed.py --model "models/speaker-embedding/wespeaker_en_voxceleb_CAM++.onnx" > command_outputs/m6_s4_embed_campplus.txt 2>&1

Segments: WavSource(realtime=False) + SileroVad + Segmenter (7 s cap, no session_start), as in
app.py, on mic_01-03 and sys_01. Silero (our onnxruntime) and sherpa-onnx run in one process.
Speaker per segment: a mic clip = its own speaker (one reader per clip, D17); a sys_01 segment = the
reference speaker in eval/meta/sys_01.csv it overlaps most in time (T1.6 rule); no overlap ->
counted and left out.
Embeddings: sherpa_onnx.SpeakerEmbeddingExtractor on the CPU, --threads (default 1, J3); each
embedding is L2-normalised, so cosine similarity = dot product. A segment that sherpa-onnx reports
as not ready (too short) is counted and left out.
Printed:
  - per segment: clip, id, speech length (end - start), audio length (with padding), speaker,
    time to embed;
  - versions, model SHA-256, embedding size, load time, RSS before / after load / at the end, peak
    RSS, time per embedding (median / p95 / max; a warm-up call on 1 s of silence is left out);
  - per clip group: cosine similarity of same- vs different-speaker pairs;
  - centroid check (R11): each segment vs its own speaker's centroid (normalised mean of that
    speaker's OTHER segments with speech >= 2 s) and vs the best other speaker's centroid, by
    speech-length bucket, with how often the nearest centroid is the wrong speaker;
  - threshold table 0.30-0.80, mic clips only: how many segments would join their own speaker
    (own >= t) and how many would stay out of the wrong one (best other < t);
  - sys_01: the same numbers, reported only, never used for tuning (R13).
A missing model, clip or reference CSV stops with a clear error (working rule 2).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import resource
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime
import psutil
import sherpa_onnx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from arm_en_asr.audio_capture import (  # noqa: E402
    CAP_S, SR, Segmenter, SileroVad, WavSource, new_id_counter, run_capture)

MODELS_DIR = ROOT / "models"
VAD_PATH = MODELS_DIR / "silero_vad.onnx"
CLIPS_DIR = ROOT / "eval" / "clips"
META_DIR = ROOT / "eval" / "meta"
MIC_CLIPS = ["mic_01", "mic_02", "mic_03"]
SYS_CLIP = "sys_01"

LONG_S = 2.0                     # centroids are built from segments with at least this much speech
BUCKETS = [(0.0, 0.7), (0.7, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, float("inf"))]
THRESHOLDS = [round(0.30 + 0.05 * i, 2) for i in range(11)]  # 0.30 ... 0.80
TABLE_MIN_S = 1.0                # second threshold table: segments with speech >= 1 s only


@dataclass
class Item:
    clip: str
    id: int
    start: float
    end: float
    audio_s: float
    speaker: str | None
    audio: np.ndarray
    emb: np.ndarray | None = None
    ms: float | None = None

    @property
    def speech_s(self) -> float:
        return self.end - self.start


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def rss_mb() -> float:
    return psutil.Process().memory_info().rss / 1e6


def peak_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 / 1e6  # ru_maxrss is in KiB


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def dist(vals: list[float]) -> str:
    if not vals:
        return "n=0"
    a = np.asarray(vals)
    return (f"n={len(a)}  min {a.min():.3f}  p5 {np.percentile(a, 5):.3f}  "
            f"median {np.median(a):.3f}  p95 {np.percentile(a, 95):.3f}  max {a.max():.3f}")


# ---------------------------------------------------------------- data

def check_inputs(model: Path) -> None:
    if not model.is_file():
        fail(f"model not found: {model} (run scripts/download_models.py)")
    if not VAD_PATH.is_file():
        fail(f"model missing: Silero VAD {VAD_PATH} (run scripts/download_models.py)")
    for stem in MIC_CLIPS + [SYS_CLIP]:
        if not (CLIPS_DIR / f"{stem}.wav").is_file():
            fail(f"eval clip not found: {CLIPS_DIR / (stem + '.wav')}")
    if not (META_DIR / f"{SYS_CLIP}.csv").is_file():
        fail(f"reference CSV not found: {META_DIR / (SYS_CLIP + '.csv')}")


def read_sys_reference() -> list[tuple[float, float, str]]:
    rows = []
    with open(META_DIR / f"{SYS_CLIP}.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append((float(r["start"]), float(r["end"]), r["speaker"].strip()))
    if not rows:
        fail(f"{SYS_CLIP}.csv has no rows")
    return rows


def sys_label(start: float, end: float, ref: list[tuple[float, float, str]]) -> str | None:
    best, best_overlap = None, 0.0
    for rs, re_, speaker in ref:
        overlap = min(end, re_) - max(start, rs)
        if overlap > best_overlap:
            best, best_overlap = speaker, overlap
    return best


def segment_clip(stem: str, device: str) -> list:
    out: list = []
    segmenter = Segmenter(device, SileroVad(VAD_PATH), new_id_counter())
    run_capture(WavSource(CLIPS_DIR / f"{stem}.wav", realtime=False), segmenter, out.append)
    return out


# ---------------------------------------------------------------- embeddings

def load_extractor(model: Path, threads: int):
    config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
        model=str(model), num_threads=threads, debug=False, provider="cpu")
    if not config.validate():
        fail(f"sherpa-onnx rejected the extractor config for {model}")
    return sherpa_onnx.SpeakerEmbeddingExtractor(config)


def embed(extractor, audio: np.ndarray) -> np.ndarray | None:
    stream = extractor.create_stream()
    stream.accept_waveform(sample_rate=SR, waveform=audio)
    stream.input_finished()
    if not extractor.is_ready(stream):
        return None
    v = np.asarray(extractor.compute(stream), dtype=np.float32)
    norm = float(np.linalg.norm(v))
    if not np.isfinite(norm) or norm == 0.0:
        fail(f"embedding has norm {norm}")
    return v / norm


# ---------------------------------------------------------------- analysis

def centroid(items: list[Item]) -> np.ndarray | None:
    if not items:
        return None
    c = np.mean([it.emb for it in items], axis=0)
    return c / np.linalg.norm(c)


def analyse(title: str, items: list[Item], show_table: bool) -> None:
    print(f"\n==== {title} ====")
    ready = [it for it in items if it.emb is not None and it.speaker is not None]
    speakers = sorted({it.speaker for it in ready})
    print(f"segments used: {len(ready)}; speakers: "
          + ", ".join(f"{s} ({sum(it.speaker == s for it in ready)})" for s in speakers))

    # pairs
    same, diff, same_long, diff_long = [], [], [], []
    for i, a in enumerate(ready):
        for b in ready[i + 1:]:
            cos = float(np.dot(a.emb, b.emb))
            both_long = a.speech_s >= LONG_S and b.speech_s >= LONG_S
            (same if a.speaker == b.speaker else diff).append(cos)
            if both_long:
                (same_long if a.speaker == b.speaker else diff_long).append(cos)
    print("\npair cosine similarity")
    print(f"  same speaker, all     : {dist(same)}")
    print(f"  diff speaker, all     : {dist(diff)}")
    print(f"  same speaker, both>={LONG_S:.0f}s: {dist(same_long)}")
    print(f"  diff speaker, both>={LONG_S:.0f}s: {dist(diff_long)}")

    # centroid check (leave-one-out for the segment's own speaker)
    long_by_spk = {s: [it for it in ready if it.speaker == s and it.speech_s >= LONG_S]
                   for s in speakers}
    rows = []  # (item, own, best_other, best_other_speaker)
    skipped = 0
    for it in ready:
        own_c = centroid([x for x in long_by_spk[it.speaker] if x is not it])
        others = [(s, centroid(long_by_spk[s])) for s in speakers if s != it.speaker]
        others = [(s, c) for s, c in others if c is not None]
        if own_c is None or not others:
            skipped += 1
            continue
        own = float(np.dot(it.emb, own_c))
        o_spk, o_cos = max(((s, float(np.dot(it.emb, c))) for s, c in others), key=lambda x: x[1])
        rows.append((it, own, o_cos, o_spk))

    print(f"\ncentroid check (centroids from segments with speech >= {LONG_S:.0f} s, "
          f"own speaker without the segment itself); skipped (no centroid): {skipped}")
    print(f"  {'clip':7} {'id':>3} {'speech':>6} {'speaker':10} {'own':>6} {'other':>6}  nearest")
    for it, own, o_cos, o_spk in rows:
        ok = "ok" if own > o_cos else f"WRONG ({o_spk})"
        print(f"  {it.clip:7} {it.id:>3} {it.speech_s:6.2f} {it.speaker:10} {own:6.3f} {o_cos:6.3f}  {ok}")

    print("\n  by speech length:")
    print(f"  {'bucket':>11} {'n':>3} {'own med':>8} {'other med':>9} "
          f"{'margin min':>10} {'margin med':>10} {'wrong':>5}")
    for lo, hi in BUCKETS:
        b = [r for r in rows if lo <= r[0].speech_s < hi]
        label = f"{lo:.1f}-{hi:.1f}s" if hi != float("inf") else f">={lo:.1f}s"
        if not b:
            print(f"  {label:>11} {0:>3}")
            continue
        margins = [own - o for _, own, o, _ in b]
        print(f"  {label:>11} {len(b):>3} {np.median([r[1] for r in b]):8.3f} "
              f"{np.median([r[2] for r in b]):9.3f} {min(margins):10.3f} "
              f"{np.median(margins):10.3f} {sum(m <= 0 for m in margins):>5}")

    if not show_table:
        return
    for min_s in (0.0, TABLE_MIN_S):
        group = [r for r in rows if r[0].speech_s >= min_s]
        n = len(group)
        print(f"\n  threshold table, segments with speech >= {min_s:.1f} s (n={n}):")
        print(f"  {'t':>5} {'joins own (own>=t)':>20} {'stays out of other (other<t)':>30}")
        for t in THRESHOLDS:
            a = sum(own >= t for _, own, _, _ in group)
            r = sum(o < t for _, _, o, _ in group)
            pa = 100 * a / n if n else 0.0
            pr = 100 * r / n if n else 0.0
            print(f"  {t:5.2f} {a:>8}/{n} ({pa:5.1f} %) {r:>17}/{n} ({pr:5.1f} %)")


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", required=True, type=Path, help="speaker-embedding ONNX file")
    ap.add_argument("--threads", type=int, default=1, help="sherpa-onnx num_threads (J3: 1)")
    args = ap.parse_args()
    if args.threads < 1:
        fail("--threads must be >= 1")
    model = args.model if args.model.is_absolute() else (Path.cwd() / args.model)
    check_inputs(model)

    print(f"sherpa-onnx {getattr(sherpa_onnx, '__version__', '(no __version__)')}, "
          f"onnxruntime {onnxruntime.__version__}, numpy {np.__version__}")
    print(f"model {model.name}: {model.stat().st_size} bytes, sha256 {sha256_file(model)}")
    print(f"provider cpu, threads {args.threads}, VAD cap {CAP_S} s")
    print(f"RSS at start: {rss_mb():.0f} MB")

    # segments (Silero only)
    ref = read_sys_reference()
    items: list[Item] = []
    no_overlap = 0
    for stem in MIC_CLIPS + [SYS_CLIP]:
        device = "system" if stem == SYS_CLIP else "mic"
        for seg in segment_clip(stem, device):
            if stem == SYS_CLIP:
                speaker = sys_label(seg.start, seg.end, ref)
                no_overlap += speaker is None
            else:
                speaker = stem
            items.append(Item(stem, seg.id, seg.start, seg.end, len(seg.audio) / SR, speaker,
                              seg.audio))
    print(f"segments: " + ", ".join(
        f"{s} {sum(it.clip == s for it in items)}" for s in MIC_CLIPS + [SYS_CLIP])
          + f"; {SYS_CLIP} segments with no reference overlap: {no_overlap}")
    print(f"RSS after VAD segmentation: {rss_mb():.0f} MB")

    # model
    before = rss_mb()
    t0 = time.perf_counter()
    extractor = load_extractor(model, args.threads)
    load_s = time.perf_counter() - t0
    after_load = rss_mb()
    print(f"load {load_s:.2f} s; embedding size {extractor.dim}; "
          f"RSS {before:.0f} -> {after_load:.0f} MB (+{after_load - before:.0f} MB)")

    t0 = time.perf_counter()
    warm = embed(extractor, np.zeros(SR, dtype=np.float32))
    print(f"warm-up (1 s silence): {(time.perf_counter() - t0) * 1000:.1f} ms, "
          f"{'ready' if warm is not None else 'not ready'}")

    # embeddings
    print(f"\n{'clip':7} {'id':>3} {'start':>6} {'speech':>6} {'audio':>6} {'speaker':10} {'ms':>7}")
    not_ready = 0
    for it in items:
        t0 = time.perf_counter()
        it.emb = embed(extractor, it.audio)
        it.ms = (time.perf_counter() - t0) * 1000
        not_ready += it.emb is None
        flag = "" if it.emb is not None else "  NOT READY (left out)"
        print(f"{it.clip:7} {it.id:>3} {it.start:6.2f} {it.speech_s:6.2f} {it.audio_s:6.2f} "
              f"{str(it.speaker):10} {it.ms:7.1f}{flag}")

    times = [it.ms for it in items if it.emb is not None]
    print(f"\nembedded {len(times)} / {len(items)} segments; not ready: {not_ready}")
    if times:
        print(f"time per embedding: median {np.median(times):.1f} ms, "
              f"p95 {np.percentile(times, 95):.1f} ms, max {max(times):.1f} ms")
    print(f"RSS after embeddings: {rss_mb():.0f} MB; peak RSS (process): {peak_mb():.0f} MB")

    analyse("mic_01-03 (tuning set: threshold and short-segment length come from here)",
            [it for it in items if it.clip in MIC_CLIPS], show_table=True)
    analyse(f"{SYS_CLIP} (report only, never used for tuning, R13)",
            [it for it in items if it.clip == SYS_CLIP], show_table=False)
    print("\nDONE")


if __name__ == "__main__":
    main()
