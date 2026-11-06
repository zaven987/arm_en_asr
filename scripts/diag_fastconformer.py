"""D31 F5: FastConformer CTC (sherpa-onnx CUDA build) on the eval clips, compared with the Whisper beam sweep.

Runs in .venv-fc, in demo conditions (Zoom tab open, laptop plugged in):

    .venv-fc/bin/python scripts/diag_fastconformer.py eval/clips/mic_0{1,2,3}.wav eval/clips/sys_01.wav > command_outputs/m7_f5_diag_fc.txt 2>&1

P1  order rule D33: the CUDA libraries are loaded the app's way plus cudart / cuFFT / cuRAND
    (check_fc_gpu.py C1), then the fp32 and int8 recognizers are created (provider "cuda",
    num_threads 1) BEFORE anything imports onnxruntime; if onnxruntime is already imported, the
    script stops with ERROR. Each recognizer's creation must raise this process's VRAM (C5).
P2  only after P1: segments, CER and memory helpers are imported from diag_asr.py (which imports
    audio_capture, and so onnxruntime / Silero), so the segments (real Silero + Segmenter, 7 s cap)
    and the CER clean-up (G5) are the same code as in command_outputs/m7_beam_sweep.txt.
P3  per model (--models fp32,int8, default both): one warm-up decode (first segment, not counted),
    then every segment decoded on its own, one call each, as the app would.
P4  per segment: clip, id, length, ASR time, output characters, first 60 characters of the text.
P5  per clip: CER of the joined text; per model one summary line: total / median / max ASR time
    per segment, CER per clip and mean, empty outputs, RSS / peak RSS / swap / VRAM.
P6  a missing clip, model or reference CSV stops the script with ERROR (working rule 2); an empty
    output on one segment is counted, not a failure.
P7  no "loops" column: CTC cannot loop (D25).
S1 (D34 N9 / F6a, 2026-11-06): --seg-cap 7,10,12 repeats the run with other VAD segment caps (D8,
    D26), the same mechanism as diag_asr.py H2: it sets audio_capture.CAP for this script only
    (Segmenter reads it at run time); audio_capture.py is not changed. Allowed 1-15 s (diag_asr.py
    allowed only up to 7 s, because the cap could then only be shortened). The clips are cut again
    for each cap; every summary line starts with its cap.
    .venv-fc/bin/python scripts/diag_fastconformer.py eval/clips/mic_0{1,2,3}.wav eval/clips/sys_01.wav --models fp32 --seg-cap 7,10,12 > command_outputs/m7_f6a_segcap.txt 2>&1
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

import check_fc_gpu as fc   # P1 helpers; imports nothing that loads onnxruntime

ROOT = fc.ROOT
FC_SR = fc.SR_FC
NUM_THREADS = 1   # Zaven, 2026-11-06: as the app would run it


def fail(msg: str) -> None:
    fc.fail(msg)


def create_recognizers(names: list[str]) -> dict:
    """P1: D33 order rule + C5 (VRAM must rise with each recognizer)."""
    fc.load_libs(fc.EXTRA_CUDA_PACKAGES[:1])                 # cudart first
    from arm_en_asr.asr import AsrError, load_cuda_libraries
    try:
        load_cuda_libraries()                                # the app's way (D30 G4c)
    except AsrError as e:
        fail(f"P1: {e}")
    fc.load_libs(fc.EXTRA_CUDA_PACKAGES[1:])
    import sherpa_onnx
    print(f"# sherpa-onnx {sherpa_onnx.__version__}; provider cuda, num_threads {NUM_THREADS}",
          flush=True)
    if "onnxruntime" in sys.modules:
        fail("D33: onnxruntime (Silero) was imported before the first sherpa-onnx CUDA recognizer; "
             "this crashes with a segmentation fault")
    recognizers = {}
    vram_prev = fc.vram_mb()
    for name in names:
        path = fc.MODELS[name]
        t0 = time.monotonic()
        recognizers[name] = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
            model=str(path), tokens=str(fc.TOKENS), num_threads=NUM_THREADS, sample_rate=FC_SR,
            feature_dim=80, decoding_method="greedy_search", debug=False, provider="cuda")
        load_s = time.monotonic() - t0
        v = fc.vram_mb()
        print(f"# {name}: {path.name} loaded in {load_s:.1f} s, VRAM {v:.0f} MB (+{v - vram_prev:.0f})",
              flush=True)
        if v <= vram_prev:
            fail(f"C5: {name}: creating the recognizer did not raise this process's GPU memory "
                 f"({vram_prev:.0f} -> {v:.0f} MB): sherpa-onnx may run it on the CPU "
                 "(no silent fallback, working rule 2)")
        vram_prev = v
    return recognizers


def decode(rec, audio) -> tuple[str, float]:
    stream = rec.create_stream()
    stream.accept_waveform(FC_SR, audio)
    t = time.monotonic()
    rec.decode_stream(stream)
    return stream.result.text.strip(), time.monotonic() - t


def run_model(name: str, rec, clips, diag, seg_cap: float) -> str:
    """P3-P5: one model on all clips at one segment cap; returns the summary line."""
    first = clips[0][2][0]
    decode(rec, first.audio)                                 # P3 warm-up, not counted
    print(f"\n=== segment cap {seg_cap:g} s, FastConformer CTC {name}, cuda, num_threads {NUM_THREADS}")
    print(f"{'clip':7} {'seg':>3} {'len_s':>6} {'asr_s':>6} {'chars':>5}  text (first 60 chars)")
    times, empties, cers = [], 0, []
    for wav, ref_text, segs in clips:
        hyps = []
        for s in segs:
            text, asr_s = decode(rec, s.audio)
            times.append(asr_s)
            empties += not text
            hyps.append(text)
            print(f"{wav.stem:7} {s.id:>3} {len(s.audio) / FC_SR:6.2f} {asr_s:6.3f} {len(text):>5}  "
                  f"{text[:60]}", flush=True)
        c = diag.cer(" ".join(hyps), ref_text)
        cers.append((wav.stem, c))
        print(f"{wav.stem}: CER {100 * c:.1f} %", flush=True)
    mean_cer = statistics.mean(v for _, v in cers)
    line = (f"cap {seg_cap:4g} s  FastConformer CTC {name:4} cuda  total ASR {sum(times):6.2f} s  "
            f"median {statistics.median(times):.3f} s  max {max(times):.3f} s  "
            f"segments {len(times)}  empty {empties}  CER "
            + ", ".join(f"{k} {100 * v:.1f} %" for k, v in cers)
            + f"  mean {100 * mean_cer:.1f} %  | {diag.mem_text('cuda')}")
    print(line, flush=True)
    return line


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("clips", nargs="+", type=Path, help="16 kHz mono 16-bit WAVs in eval/clips/")
    ap.add_argument("--models", default="fp32,int8", help="comma-separated: fp32, int8 (default both)")
    ap.add_argument("--seg-cap", default="7",
                    help="S1: comma-separated VAD segment caps in seconds, 1-15 (default 7, the app's)")
    args = ap.parse_args()

    try:
        seg_caps = [float(x) for x in args.seg_cap.split(",")]
    except ValueError:
        fail(f"--seg-cap must be numbers in seconds, got {args.seg_cap!r}")
    for c in seg_caps:
        if not 1.0 <= c <= 15.0:
            fail(f"--seg-cap {c:g} s is outside 1-15 s")

    names = [n.strip() for n in args.models.split(",") if n.strip()]
    if not names or any(n not in fc.MODELS for n in names) or len(set(names)) != len(names):
        fail(f"--models must be a comma-separated subset of {', '.join(fc.MODELS)}: {args.models!r}")
    for p in [fc.TOKENS, fc.VAD_PATH, *(fc.MODELS[n] for n in names)]:
        if not p.is_file():
            fail(f"missing: {p} (models: scripts/download_models.py, D31 F3)")
    for wav in args.clips:
        if not wav.is_file():
            fail(f"clip not found: {wav}")

    recognizers = create_recognizers(names)                  # P1, before onnxruntime

    import diag_asr as diag                                  # P2: now Silero / onnxruntime may load
    import onnxruntime
    print(f"# onnxruntime {onnxruntime.__version__} (Silero); app segment cap "
          f"{diag.audio_capture.CAP_S:g} s; caps run here: " + ", ".join(f"{c:g} s" for c in seg_caps),
          flush=True)

    summary = []
    for seg_cap in seg_caps:
        diag.audio_capture.CAP = int(seg_cap * diag.SR)      # S1: this script only (as diag_asr H2)
        print(f"\n##### segment cap {seg_cap:g} s", flush=True)
        clips = diag.load_clips(args.clips)
        n_segs = sum(len(segs) for _, _, segs in clips)
        longest = max(len(s.audio) for _, _, segs in clips for s in segs) / FC_SR
        print(f"# {n_segs} segments in {len(clips)} clips, longest {longest:.2f} s | "
              f"{diag.mem_text('cuda')}", flush=True)
        summary += [run_model(name, recognizers[name], clips, diag, seg_cap) for name in names]
    print("\n=== summary")
    for line in summary:
        print(line)


if __name__ == "__main__":
    main()
