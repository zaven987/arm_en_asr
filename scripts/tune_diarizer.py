"""M6 S5 K4: choose the diarizer threshold on mic_01-03 only (R13; D27 S5, K1-K8, 2026-11-05).

Read-only for the app. Runs in .venv:
    python scripts/tune_diarizer.py > command_outputs/m6_s5_tune.txt 2>&1

1. Segments: WavSource(realtime=False) + SileroVad + Segmenter (7 s cap), as in app.py, on
   mic_01, mic_02, mic_03 (one reader per clip, D17). sys_01 is never used here (R13).
2. Every segment is embedded once with diarizer.Embedder (ResNet34, CPU, 1 thread).
3. For each threshold 0.50 ... 0.90 (step 0.01) the real diarizer.SpeakerClusters is replayed on:
   - solo:        each clip on its own                       -> expected 1 speaker per clip
   - in a row:    mic_01 -> mic_02 -> mic_03                 -> expected 3 speakers
   - taking turns: one segment from each clip in rotation    -> expected 3 speakers
   % correct = best one-to-one matching of "Speaker N" to readers (T1.6 scoring); labels left
   without a reader count as wrong.
Choice rule (K4, fixed before the run): the widest unbroken range of thresholds where every solo
clip gives 1 speaker and both mixed orders give exactly 3; the threshold is the middle of that
range. No passing threshold, or two ranges equally wide -> printed, and we decide together.
--sys01 (Zaven, 2026-11-05, after T1.6 found 1 speaker on sys_01; changes R13, to be recorded):
    python scripts/tune_diarizer.py --sys01 > command_outputs/m6_s5_tune_sys01.txt 2>&1
   also replays sys_01 (2 speakers, one recording) for each threshold and prints its speakers
   found and % correct (T1.6 scoring: reference speaker = most time overlap in eval/meta/sys_01.csv;
   segments with no overlap are clustered but not scored), plus the ranges where the mic rules pass
   AND sys_01 finds exactly 2 speakers. It prints only; the threshold is chosen together.
A missing model or clip stops with a clear error (working rule 2).
"""
from __future__ import annotations

import argparse
import csv
import itertools
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from arm_en_asr.audio_capture import (  # noqa: E402
    CAP_S, Segmenter, SileroVad, WavSource, new_id_counter, run_capture)
from arm_en_asr.diarizer import MODEL_FILE, SHORT_S, Embedder, SpeakerClusters  # noqa: E402

MODELS_DIR = ROOT / "models"
VAD_PATH = MODELS_DIR / "silero_vad.onnx"
CLIPS_DIR = ROOT / "eval" / "clips"
CLIPS = ["mic_01", "mic_02", "mic_03"]
SYS_CLIP = "sys_01"
META_DIR = ROOT / "eval" / "meta"
THRESHOLDS = [round(0.50 + 0.01 * i, 2) for i in range(41)]   # 0.50 ... 0.90


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def segment_clip(stem: str) -> list:
    out: list = []
    segmenter = Segmenter("system", SileroVad(VAD_PATH), new_id_counter())
    run_capture(WavSource(CLIPS_DIR / f"{stem}.wav", realtime=False), segmenter, out.append)
    return out


def replay(items: list[tuple[str, float, object]], threshold: float) -> list[str]:
    clusters = SpeakerClusters(threshold, SHORT_S)
    return [clusters.assign(emb, speech_s) for _, speech_s, emb in items]


def score(items: list[tuple[str, float, object]], labels: list[str]) -> tuple[int, int, int]:
    """(speakers found, correct, total) with the best one-to-one reader -> label matching."""
    readers = sorted({clip for clip, _, _ in items})
    found = sorted(set(labels))
    counts = {(r, lab): 0 for r in readers for lab in found}
    for (clip, _, _), lab in zip(items, labels):
        counts[(clip, lab)] += 1
    best = 0
    k = min(len(readers), len(found))
    for chosen_readers in itertools.permutations(readers, k):
        for chosen_labels in itertools.permutations(found, k):
            best = max(best, sum(counts[(r, lab)] for r, lab in zip(chosen_readers, chosen_labels)))
    return len(found), best, len(items)


def read_sys_reference() -> list[tuple[float, float, str]]:
    path = META_DIR / f"{SYS_CLIP}.csv"
    with open(path, newline="", encoding="utf-8") as f:
        rows = [(float(r["start"]), float(r["end"]), r["speaker"].strip()) for r in csv.DictReader(f)]
    if not rows:
        fail(f"{path} has no rows")
    return rows


def sys_truth(start: float, end: float, ref: list[tuple[float, float, str]]) -> str | None:
    best, best_overlap = None, 0.0
    for rs, re_, speaker in ref:
        overlap = min(end, re_) - max(start, rs)
        if overlap > best_overlap:
            best, best_overlap = speaker, overlap
    return best


def ranges_of(flags: list[bool]) -> list[tuple[int, int]]:
    ranges, start = [], None
    for i, ok in enumerate(flags + [False]):
        if ok and start is None:
            start = i
        elif not ok and start is not None:
            ranges.append((start, i - 1))
            start = None
    return ranges


def digits(labels: list[str]) -> str:
    out = []
    for lab in labels:
        n = int(lab.split()[-1])
        out.append(str(n) if n < 10 else "+")
    return "".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sys01", action="store_true",
                    help="also report sys_01 per threshold (Zaven, 2026-11-05; changes R13)")
    args = ap.parse_args()

    model = MODELS_DIR / MODEL_FILE
    if not model.is_file():
        fail(f"model missing: {model} (run scripts/download_models.py)")
    if not VAD_PATH.is_file():
        fail(f"model missing: Silero VAD {VAD_PATH} (run scripts/download_models.py)")
    for stem in CLIPS + ([SYS_CLIP] if args.sys01 else []):
        if not (CLIPS_DIR / f"{stem}.wav").is_file():
            fail(f"eval clip not found: {CLIPS_DIR / (stem + '.wav')}")
    if args.sys01 and not (META_DIR / f"{SYS_CLIP}.csv").is_file():
        fail(f"reference CSV not found: {META_DIR / (SYS_CLIP + '.csv')}")

    print(f"model {model.name}; VAD cap {CAP_S} s; short segments < {SHORT_S} s; clips {', '.join(CLIPS)}")
    embedder = Embedder(model, num_threads=1)
    per_clip: dict[str, list[tuple[str, float, object]]] = {}
    t0 = time.perf_counter()
    for stem in CLIPS:
        items = []
        for seg in segment_clip(stem):
            items.append((stem, seg.end - seg.start, embedder.embed(seg.audio)))
        per_clip[stem] = items
        n_short = sum(sp < SHORT_S for _, sp, _ in items)
        n_nr = sum(e is None for _, _, e in items)
        print(f"{stem}: {len(items)} segments, {n_short} short (< {SHORT_S} s), {n_nr} not ready; "
              "speech s: " + " ".join(f"{sp:.2f}" for _, sp, _ in items))
    sys_items: list[tuple[str | None, float, object]] = []
    if args.sys01:
        ref = read_sys_reference()
        for seg in segment_clip(SYS_CLIP):
            sys_items.append((sys_truth(seg.start, seg.end, ref), seg.end - seg.start,
                              embedder.embed(seg.audio)))
        print(f"{SYS_CLIP}: {len(sys_items)} segments, "
              f"{sum(sp < SHORT_S for _, sp, _ in sys_items)} short, "
              f"{sum(e is None for _, _, e in sys_items)} not ready, "
              f"{sum(t is None for t, _, _ in sys_items)} with no reference overlap (not scored); "
              "reference: " + "".join(t[-1] if t else "?" for t, _, _ in sys_items))
    print(f"segmentation + embedding: {time.perf_counter() - t0:.1f} s")

    in_a_row = [it for stem in CLIPS for it in per_clip[stem]]
    turns = [it for group in itertools.zip_longest(*(per_clip[s] for s in CLIPS))
             for it in group if it is not None]
    print("taking turns order: " + " ".join(clip[-2:] for clip, _, _ in turns))

    sys_head = f" | {'sys spk':>7} {'correct':>8}  labels" if args.sys01 else ""
    print(f"\n{'t':>5} | {'solo speakers 01/02/03':>22} {'outside main':>13} | "
          f"{'in a row':>8} {'correct':>8} | {'turns':>5} {'correct':>8} | pass{sys_head}")
    passing: list[bool] = []
    sys_two: list[bool] = []
    for t in THRESHOLDS:
        solo_spk, solo_out = [], 0
        for stem in CLIPS:
            n_found, correct, total = score(per_clip[stem], replay(per_clip[stem], t))
            solo_spk.append(n_found)
            solo_out += total - correct
        row_spk, row_ok, row_n = score(in_a_row, replay(in_a_row, t))
        trn_spk, trn_ok, trn_n = score(turns, replay(turns, t))
        ok = all(n == 1 for n in solo_spk) and row_spk == 3 and trn_spk == 3
        passing.append(ok)
        sys_col = ""
        if args.sys01:
            labels = replay(sys_items, t)            # every segment is clustered, in order
            scored = [(it, lab) for it, lab in zip(sys_items, labels) if it[0] is not None]
            s_spk = len(set(labels))
            _, s_ok, s_n = score([it for it, _ in scored], [lab for _, lab in scored])
            sys_two.append(s_spk == 2)
            sys_col = f" | {s_spk:>7} {100 * s_ok / s_n:7.1f}%  {digits(labels)}"
        print(f"{t:5.2f} | {'/'.join(map(str, solo_spk)):>22} {solo_out:>13} | "
              f"{row_spk:>8} {100 * row_ok / row_n:7.1f}% | {trn_spk:>5} {100 * trn_ok / trn_n:7.1f}% | "
              f"{'PASS' if ok else '-':4}{sys_col}")

    print()
    if args.sys01:
        both = ranges_of([p and s for p, s in zip(passing, sys_two)])
        if both:
            for lo, hi in both:
                print(f"mic rules pass AND {SYS_CLIP} finds 2 speakers: "
                      f"{THRESHOLDS[lo]:.2f} - {THRESHOLDS[hi]:.2f} ({hi - lo + 1} thresholds)")
        else:
            print(f"no threshold where the mic rules pass AND {SYS_CLIP} finds 2 speakers")
        for lo, hi in ranges_of(sys_two):
            print(f"{SYS_CLIP} finds 2 speakers (mic rules ignored): "
                  f"{THRESHOLDS[lo]:.2f} - {THRESHOLDS[hi]:.2f}")
        print("(--sys01 prints only; the threshold is chosen together)\n")

    # K4 choice rule (mic only): widest unbroken passing range, middle of it.
    ranges = ranges_of(passing)
    if not ranges:
        print("RESULT: no threshold passes (K4) -> stop and decide together")
        print("\nDONE")
        return
    for lo, hi in ranges:
        print(f"passing range: {THRESHOLDS[lo]:.2f} - {THRESHOLDS[hi]:.2f} ({hi - lo + 1} thresholds)")
    widest = max(hi - lo for lo, hi in ranges)
    best = [(lo, hi) for lo, hi in ranges if hi - lo == widest]
    if len(best) > 1:
        print("RESULT: two or more passing ranges are equally wide (K4) -> stop and decide together")
    else:
        lo, hi = best[0]
        mid = (THRESHOLDS[lo] + THRESHOLDS[hi]) / 2
        print(f"RESULT: widest range {THRESHOLDS[lo]:.2f} - {THRESHOLDS[hi]:.2f}; "
              f"middle = {mid:.3f} (K4 choice)")
    print("\nDONE")


if __name__ == "__main__":
    main()
