"""M7 WER: Whisper small (the last app setting, D32) vs FastConformer CTC fp32 (D34) on the same segments.

Zaven, 2026-11-07: the FastConformer WER (command_outputs/m7_fc_wer.txt) had no Whisper WER to compare
with, because the beam sweep (m7_beam_sweep.txt) printed only CER and the first 60 characters of each
segment. This script scores both models in one run, with the same segments and the same clean-up.

Runs in .venv-fc, the only environment that still has faster-whisper 1.2.1 (D34 N7 removed it from
.venv), with models/faster-whisper-small/ still on disk. Accuracy only, so demo conditions are not needed:

    .venv-fc/bin/python scripts/diag_wer.py eval/clips/mic_0{1,2,3}.wav eval/clips/sys_01.wav > command_outputs/m7_wer_whisper_fc.txt 2>&1

W1  order rule D33: the FastConformer fp32 recognizer is created first, by
    diag_fastconformer.create_recognizers() (CUDA libraries, D33 guard, C5 VRAM check); only then
    diag_asr.py is imported (Silero / onnxruntime).
W2  segments: diag_asr.load_clips(), the app's Silero + Segmenter at the app cap of 7 s, the same 47
    segments as m7_beam_sweep.txt, m7_f5_diag_fc.txt and m7_fc_wer.txt.
W3  FastConformer fp32, cuda, num_threads 1: one warm-up decode (not counted), then each segment on its
    own (as in diag_fastconformer.py). The recognizer is then freed before Whisper is loaded.
W4  Whisper small, cuda int8_float16, cpu_threads 4, variant g+c+d1 = the D32 app setting: beam 5,
    temperature 0, without_timestamps, repetition_penalty 1.1, D26 token cap (diag_asr.py M1). One
    warm-up transcribe (not counted). Loop = compression ratio > 2.4 or the cap was hit (diag_asr.py G2).
W5  clean-up: diag_asr.clean() (G5: lowercase, Armenian letters and spaces only, spaces collapsed), for
    both CER and WER. Words = the cleaned text split on spaces. WER = word edit distance / reference
    words; CER = character edit distance / reference characters (spaces included, as diag_asr.cer).
    Per clip: the segments' texts joined with spaces against the clip's joined reference (eval/meta).
W6  reported per model: per segment the FULL text (not cut at 60 characters); per clip WER and CER;
    "all" = pooled (summed edits / summed reference size, as m7_fc_wer.txt); "mean" = mean of the four
    clips (as the CER numbers in DECISIONS D31 F5 / D32). Check: the CER lines should repeat
    m7_beam_sweep.txt (Whisper g+c+d1: 36.0 / 21.0 / 29.4 / 43.3 %) and m7_f5_diag_fc.txt (FastConformer
    fp32: 8.2 / 5.0 / 6.9 / 17.4 %); the reference sizes should repeat m7_fc_wer.txt (498 words, 3316
    characters).
W7  a missing model, clip or reference CSV stops with ERROR (working rule 2).
"""
from __future__ import annotations

import argparse
import gc
import math
from pathlib import Path

import diag_fastconformer as dfc   # imports nothing that loads onnxruntime (W1)

WHISPER_LOAD = dict(cpu_threads=4, device="cuda", compute_type="int8_float16")
WHISPER_VARIANT = "g+c+d1"   # D32: beam 5 (the base), without_timestamps, cap, repetition_penalty 1.1


def fail(msg: str) -> None:
    dfc.fail(msg)


def score(hyp: str, ref: str, diag) -> dict:
    """W5: word and character edits on the cleaned texts."""
    h, r = diag.clean(hyp), diag.clean(ref)
    if not r:
        fail("reference text is empty after clean-up")
    hw, rw = h.split(), r.split()
    return dict(w_err=diag.edit_distance(hw, rw), w_ref=len(rw),
                c_err=diag.edit_distance(h, r), c_ref=len(r))


def report(name: str, results: list[tuple[str, dict]]) -> str:
    """W6: per-clip table plus pooled and mean; returns the summary line."""
    print(f"\n{name}")
    print(f"{'clip':7} {'ref words':>9} {'WER':>7} {'ref chars':>9} {'CER':>7}")
    for stem, s in results:
        print(f"{stem:7} {s['w_ref']:>9} {100 * s['w_err'] / s['w_ref']:6.1f}% "
              f"{s['c_ref']:>9} {100 * s['c_err'] / s['c_ref']:6.1f}%")
    tw = sum(s["w_err"] for _, s in results); rw = sum(s["w_ref"] for _, s in results)
    tc = sum(s["c_err"] for _, s in results); rc = sum(s["c_ref"] for _, s in results)
    mean_w = sum(s["w_err"] / s["w_ref"] for _, s in results) / len(results)
    mean_c = sum(s["c_err"] / s["c_ref"] for _, s in results) / len(results)
    print(f"{'all':7} {rw:>9} {100 * tw / rw:6.1f}% {rc:>9} {100 * tc / rc:6.1f}%   (pooled)")
    print(f"{'mean':7} {'':>9} {100 * mean_w:6.1f}% {'':>9} {100 * mean_c:6.1f}%   (mean of clips)")
    return (f"{name:40}  WER " + ", ".join(f"{k} {100 * s['w_err'] / s['w_ref']:.1f} %" for k, s in results)
            + f"  pooled {100 * tw / rw:.1f} %  mean {100 * mean_w:.1f} %  |  CER "
            + ", ".join(f"{k} {100 * s['c_err'] / s['c_ref']:.1f} %" for k, s in results)
            + f"  pooled {100 * tc / rc:.1f} %  mean {100 * mean_c:.1f} %")


def run_fastconformer(rec, clips, diag) -> list[tuple[str, dict]]:
    """W3."""
    dfc.decode(rec, clips[0][2][0].audio)                    # warm-up, not counted
    print("\n=== FastConformer CTC fp32, cuda, num_threads 1 (full text per segment)")
    results = []
    for wav, ref_text, segs in clips:
        hyps = []
        for s in segs:
            text, asr_s = dfc.decode(rec, s.audio)
            hyps.append(text)
            print(f"{wav.stem:7} {s.id:>3} {len(s.audio) / dfc.FC_SR:6.2f} s {asr_s:6.3f} s  {text}",
                  flush=True)
        results.append((wav.stem, score(" ".join(hyps), ref_text, diag)))
    return results


def run_whisper(clips, diag) -> tuple[list[tuple[str, dict]], int, int]:
    """W4."""
    if not (diag.WHISPER_DIR / "model.bin").is_file():
        fail(f"missing: {diag.WHISPER_DIR / 'model.bin'} (faster-whisper small, D15 revision 536b066)")
    model = diag.load_model(**WHISPER_LOAD)
    rate = diag.token_rate(model)
    (_, _, trans_kw), = diag.parse_variants(WHISPER_VARIANT)
    first = clips[0][2][0]
    list(model.transcribe(first.audio, **diag.BASE_TRANSCRIBE)[0])   # warm-up, not counted
    print(f"\n=== Whisper small, cuda int8_float16, variant {WHISPER_VARIANT} (D32 app setting; "
          f"full text per segment)")
    results, loops, n = [], 0, 0
    for wav, ref_text, segs in clips:
        hyps = []
        for s in segs:
            seg_s = len(s.audio) / diag.SR
            kw = dict(diag.BASE_TRANSCRIBE, **trans_kw)
            cap = min(math.ceil(rate * seg_s * diag.CAP_MARGIN), diag.EFFECTIVE_CAP_LIMIT)
            kw["max_new_tokens"] = diag.CT2_LENGTH_FACTOR * cap      # as diag_asr.run_one (H1)
            r = diag.run_variant(model, s.audio, kw)
            looped = r["compression"] > diag.LOOP_COMPRESSION or r["tokens"] >= cap
            loops += looped
            n += 1
            hyps.append(r["text"])
            print(f"{wav.stem:7} {s.id:>3} {seg_s:6.2f} s {r['time']:6.2f} s  "
                  f"{'LOOP ' if looped else ''}{r['text']}", flush=True)
        results.append((wav.stem, score(" ".join(hyps), ref_text, diag)))
    return results, loops, n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("clips", nargs="+", type=Path, help="16 kHz mono 16-bit WAVs in eval/clips/")
    args = ap.parse_args()
    for p in [dfc.fc.TOKENS, dfc.fc.VAD_PATH, dfc.fc.MODELS["fp32"]]:
        if not p.is_file():
            fail(f"missing: {p} (models: scripts/download_models.py)")
    for wav in args.clips:
        if not wav.is_file():
            fail(f"clip not found: {wav}")

    rec = dfc.create_recognizers(["fp32"])["fp32"]           # W1: before onnxruntime

    import diag_asr as diag                                  # W1: Silero / onnxruntime may load now
    clips = diag.load_clips(args.clips)                      # W2
    print(f"# {sum(len(s) for _, _, s in clips)} segments | {diag.mem_text('cuda')}", flush=True)

    fc_results = run_fastconformer(rec, clips, diag)
    del rec
    gc.collect()
    print(f"# FastConformer freed | {diag.mem_text('cuda')}", flush=True)

    wh_results, loops, n = run_whisper(clips, diag)
    print(f"# Whisper done | {diag.mem_text('cuda')}", flush=True)

    print("\n=== WER / CER (W5, W6)")
    lines = [report(f"Whisper small {WHISPER_VARIANT} (D32), loops {loops}/{n}", wh_results),
             report("FastConformer CTC fp32 (D34)", fc_results)]
    print("\n=== summary")
    for line in lines:
        print(line)


if __name__ == "__main__":
    main()
