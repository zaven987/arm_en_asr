"""M5 S2: two devices at once, latency and RAM per ASR setting (DECISIONS D27 S2, E5; K1-K7, 2026-11-04).

Feeds eval/clips/mic_01.wav (as "mic") and eval/clips/sys_01.wav (as "system") at the same time, at
real-time speed, through the app's real capture code, Pipeline, ASR and MT. Read-only for the app:
nothing in src/ or app.py changes. Runs in .venv, under demo conditions (Meet/Zoom tab open, plugged in).

    python scripts/diag_two_devices.py > command_outputs/m5_s2_two_devices.txt 2>&1
    # turn-taking files (D27 addition, 2026-11-04), current app setting only:
    python scripts/diag_two_devices.py --mic eval/clips/turns_mic.wav --system eval/clips/turns_sys.wav \
        --variants n1t4 > command_outputs/m5_turns_n1t4.txt 2>&1

Options (added 2026-11-04): --mic / --system choose the WAVs (paths from the repo root or absolute;
defaults mic_01 / sys_01), --variants a comma list of variant names (default: all three).

K1  three variants, one after another, each in its own child process (clean RAM figures):
      n1t4 = N 1, cpu_threads 4 (current app setting)   n2t4 = N 2, cpu_threads 4   n2t2 = N 2, cpu_threads 2
K2  one WavSource (realtime=True) + SileroVad + Segmenter per device, shared id counter, one capture
    thread per device; a run ends when both files have ended and every line is printed (~89 s).
K3  cpu_threads is set through asr.CPU_THREADS for this script only; asr.py is not changed.
K4  system lines get the stub label "Speaker ?" (never a real label; this script only, D27 E4).
K5  each line is printed in the normal format, plus a tab-separated row:
      ROW <variant> <segment id> <device> <start s> <latency s> <cut yes/no>
K6  summary per variant: lines, lines > 5 s, latency median / p95 / max (all, mic, system), peak RSS
    (sampled every 0.2 s), swap at start / end, model load time, lines cut by the token cap;
    at the end a table comparing the variants.
K7  header: start time, CPU count, load average. Conditions (browser tabs, power) are told by Zaven.
A missing clip or model, a capture error or a pipeline error stops the script with a clear error
(working rule 2).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

MODELS_DIR = ROOT / "models"
CLIPS = {"mic": ROOT / "eval" / "clips" / "mic_01.wav",
         "system": ROOT / "eval" / "clips" / "sys_01.wav"}
VARIANTS = {"n1t4": (1, 4), "n2t4": (2, 4), "n2t2": (2, 2)}   # name -> (N workers, cpu_threads)
STUB_LABEL = "Speaker ?"      # K4
RSS_SAMPLE_S = 0.2            # K6
POLL_S = 0.2
LATENCY_LIMIT = 5.0           # D12
SUMMARY_TAG = "SUMMARY_JSON\t"


class DiagError(Exception):
    pass


def p95(values: list[float]) -> float:
    """Nearest-rank 95th percentile."""
    s = sorted(values)
    return s[max(0, math.ceil(0.95 * len(s)) - 1)]


def lat_stats(values: list[float]) -> dict:
    if not values:
        return {"n": 0, "median": None, "p95": None, "max": None}
    return {"n": len(values), "median": statistics.median(values), "p95": p95(values), "max": max(values)}


def fmt(x: float | None, unit: str = "s") -> str:
    return "-" if x is None else f"{x:.1f}{unit}"


class StubDiarizer:
    """K4: fixed placeholder label, so no real speaker is ever claimed."""

    def label(self, segment) -> str:
        return STUB_LABEL


# ---------------------------------------------------------------- child: one variant

def run_variant(name: str, clips: dict[str, Path]) -> int:
    import psutil

    import arm_en_asr.asr as asr_module
    from arm_en_asr.audio_capture import Segmenter, SileroVad, WavSource, new_id_counter, run_capture
    from arm_en_asr.output import format_line
    from arm_en_asr.pipeline import Pipeline
    from arm_en_asr.translate import Mt

    n_workers, cpu_threads = VARIANTS[name]
    proc = psutil.Process()
    swap_start = psutil.swap_memory().used

    # K6: peak RSS sampler (also covers model loading).
    peak = {"rss": proc.memory_info().rss}
    sampling = threading.Event()

    def sample_rss() -> None:
        while not sampling.wait(RSS_SAMPLE_S):
            peak["rss"] = max(peak["rss"], proc.memory_info().rss)

    sampler = threading.Thread(target=sample_rss, name="rss", daemon=True)
    sampler.start()

    print(f"=== variant {name}: N = {n_workers}, cpu_threads = {cpu_threads} ===", flush=True)
    t_load = time.monotonic()
    asr_module.CPU_THREADS = cpu_threads           # K3: this process only
    asr = asr_module.Asr(MODELS_DIR / "faster-whisper-small", num_workers=n_workers)
    asr.warm_up()                                  # W3: same startup as the app (W2)
    mt = Mt(MODELS_DIR / "opus-mt-hy-en-ct2-int8")
    ids = new_id_counter()
    sources, segmenters = {}, {}
    for device, path in clips.items():
        sources[device] = WavSource(path, realtime=True)
        segmenters[device] = Segmenter(device, SileroVad(MODELS_DIR / "silero_vad.onnx"), ids)
    load_s = time.monotonic() - t_load
    print(f"models loaded in {load_s:.1f} s", flush=True)

    devices: dict[int, str] = {}   # segment id -> device, filled before submit
    rows: list[dict] = []

    def printer(record) -> None:   # K5
        device = devices[record.segment_id]
        cut = record.armenian.endswith(asr_module.CUT_MARKER)
        print(format_line(record), flush=True)
        print(f"ROW\t{name}\t{record.segment_id}\t{device}\t{record.start:.2f}\t{record.latency:.2f}\t"
              f"{'yes' if cut else 'no'}", flush=True)
        rows.append({"device": device, "latency": record.latency, "cut": cut})

    pipeline = Pipeline(asr, mt, n_workers=n_workers, diarizer=StubDiarizer(), printer=printer)

    def submit(segment) -> None:
        devices[segment.id] = segment.device
        pipeline.submit(segment)

    errors: list[BaseException] = []

    def capture(device: str) -> None:
        try:
            run_capture(sources[device], segmenters[device], submit)
        except BaseException as e:
            errors.append(e)

    threads = [threading.Thread(target=capture, args=(d,), name=f"capture-{d}", daemon=True)
               for d in clips]
    t_run = time.monotonic()
    for t in threads:
        t.start()
    while any(t.is_alive() for t in threads):   # K2: until both files have ended
        if errors:
            break
        pipeline.check()
        time.sleep(POLL_S)
    for s in sources.values():
        s.stop()
    for t in threads:
        t.join()
    pipeline.close()                            # drain: every line printed
    run_s = time.monotonic() - t_run
    sampling.set()
    sampler.join()
    peak["rss"] = max(peak["rss"], proc.memory_info().rss)
    swap_end = psutil.swap_memory().used
    if errors:
        raise DiagError(f"capture failed: {errors[0]!r}")

    lat_all = [r["latency"] for r in rows]
    summary = {
        "variant": name, "n_workers": n_workers, "cpu_threads": cpu_threads,
        "lines": len(rows),
        "over_5s": sum(1 for x in lat_all if x > LATENCY_LIMIT),
        "cut": sum(1 for r in rows if r["cut"]),
        "all": lat_stats(lat_all),
        "mic": lat_stats([r["latency"] for r in rows if r["device"] == "mic"]),
        "system": lat_stats([r["latency"] for r in rows if r["device"] == "system"]),
        "peak_rss_mb": peak["rss"] / 2**20,
        "swap_start_mb": swap_start / 2**20, "swap_end_mb": swap_end / 2**20,
        "load_s": load_s, "run_s": run_s,
    }
    print(f"--- summary {name} ---")
    print(f"lines {summary['lines']} (mic {summary['mic']['n']}, system {summary['system']['n']}), "
          f"> 5 s: {summary['over_5s']}, cut by token cap: {summary['cut']}")
    for part in ("all", "mic", "system"):
        st = summary[part]
        print(f"latency {part:6s}: median {fmt(st['median'])}, p95 {fmt(st['p95'])}, max {fmt(st['max'])}")
    print(f"peak RSS {summary['peak_rss_mb']:.0f} MB; swap {summary['swap_start_mb']:.0f} -> "
          f"{summary['swap_end_mb']:.0f} MB; load {load_s:.1f} s; run {run_s:.1f} s")
    print(SUMMARY_TAG + json.dumps(summary), flush=True)
    return 0


# ---------------------------------------------------------------- parent: all variants

def check_inputs(clips: dict[str, Path]) -> None:
    missing = [str(p) for p in clips.values() if not p.is_file()]
    for p in (MODELS_DIR / "silero_vad.onnx", MODELS_DIR / "faster-whisper-small" / "model.bin",
              MODELS_DIR / "opus-mt-hy-en-ct2-int8" / "model.bin"):
        if not p.is_file():
            missing.append(str(p))
    if missing:
        raise DiagError("missing files:\n" + "\n".join(f"  - {m}" for m in missing))


def run_all(clips: dict[str, Path], variants: list[str]) -> int:
    check_inputs(clips)
    load1, load5, load15 = os.getloadavg()
    print(f"diag_two_devices.py  start {datetime.now().isoformat(timespec='seconds')}  "
          f"CPUs {os.cpu_count()}  load average {load1:.2f} {load5:.2f} {load15:.2f}")
    print(f"mic = {clips['mic']}, system = {clips['system']}, variants = {','.join(variants)}, "
          f"real-time feed; system label = {STUB_LABEL!r} (stub, K4)")
    print("conditions (Meet/Zoom tab, power): reported by Zaven, not detected\n", flush=True)

    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    summaries = []
    for name in variants:
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--variant", name,
                                  "--mic", str(clips["mic"]), "--system", str(clips["system"])],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, encoding="utf-8", env=env, cwd=ROOT)
        summary = None
        for line in child.stdout:
            if line.startswith(SUMMARY_TAG):
                summary = json.loads(line[len(SUMMARY_TAG):])
            else:
                print(line, end="", flush=True)
        code = child.wait()
        if code != 0 or summary is None:
            raise DiagError(f"variant {name} failed (exit {code}); see its output above")
        summaries.append(summary)
        print(flush=True)

    print("=== comparison (K6) ===")
    print("variant  N  thr  lines  >5s  cut  med(all)  p95(all)  max(all)  max(mic)  max(sys)  "
          "peakRSS  swap start->end")
    for s in summaries:
        print(f"{s['variant']:7s}  {s['n_workers']}  {s['cpu_threads']:3d}  {s['lines']:5d}  "
              f"{s['over_5s']:3d}  {s['cut']:3d}  {fmt(s['all']['median']):>8s}  {fmt(s['all']['p95']):>8s}  "
              f"{fmt(s['all']['max']):>8s}  {fmt(s['mic']['max']):>8s}  {fmt(s['system']['max']):>8s}  "
              f"{s['peak_rss_mb']:5.0f} MB  {s['swap_start_mb']:.0f} -> {s['swap_end_mb']:.0f} MB")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--variant", choices=list(VARIANTS), help="internal: run one variant (child process)")
    p.add_argument("--mic", default=str(CLIPS["mic"]), help="WAV fed as the mic (default mic_01)")
    p.add_argument("--system", default=str(CLIPS["system"]), help="WAV fed as system audio (default sys_01)")
    p.add_argument("--variants", default=",".join(VARIANTS),
                   help=f"comma list from {','.join(VARIANTS)} (default: all)")
    args = p.parse_args()
    clips = {"mic": (ROOT / args.mic).resolve(), "system": (ROOT / args.system).resolve()}
    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    unknown = [v for v in variants if v not in VARIANTS]
    if unknown or not variants:
        p.error(f"unknown or empty --variants {unknown or args.variants!r}; choose from {','.join(VARIANTS)}")
    try:
        code = run_variant(args.variant, clips) if args.variant else run_all(clips, variants)
    except DiagError as e:
        print(f"ERROR: {e}", file=sys.stderr, flush=True)
        code = 1
    sys.exit(code)


if __name__ == "__main__":
    main()
