"""Build the committed test fixtures in tests/fixtures/ (D22, agreed 2026-10-31: F1-F5).

Run once from the repo root with .venv active, after scripts/fetch_fleurs.py and
scripts/download_models.py:
    python scripts/make_fixtures.py

Writes:
    tests/fixtures/speech_short.wav    shortest FLEURS subset clip, whole (F1)
    tests/fixtures/silence_5s.wav      5 s of digital zeros (F2)
    tests/fixtures/speech_long.wav     first subset clip (CSV order) with an unbroken
                                       Silero speech run >= 13 s, whole (F3)
    tests/fixtures/README.md           attribution, FLEURS ids, SHA-256 (F4)

Running it again gives the same files. Tests never run this script.
"""
from __future__ import annotations

import csv
import hashlib
import sys
import wave
from pathlib import Path

import numpy as np
import onnxruntime as ort

ROOT = Path(__file__).resolve().parent.parent
SUBSET_CSV = ROOT / "eval" / "meta" / "fleurs_hy_am_test100.csv"
SILERO_PATH = ROOT / "models" / "silero_vad.onnx"
OUT = ROOT / "tests" / "fixtures"

FLEURS_REV = "70bb2e84b976b7e960aa89f1c648e09c59f894dd"  # same as eval/meta/README.md

SR = 16000
VAD_WINDOW = 512          # samples per Silero step at 16 kHz (32 ms)
VAD_CONTEXT = 64          # previous samples prepended (Silero v5/v6 ONNX interface)
VAD_THRESHOLD = 0.5       # speech if p > 0.5
GAP_END_S = 0.6           # a gap this long ends a run (D8)
MIN_RUN_S = 0.3           # runs shorter than this are ignored (D8)
LONG_RUN_S = 13.0         # F3: 12 s cap (D8) + 1 s margin
SILENCE_S = 5.0           # F2


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def read_pcm16(path: Path) -> bytes:
    if not path.is_file():
        fail(f"WAV missing: {path} (run scripts/fetch_fleurs.py first)")
    try:
        with wave.open(str(path), "rb") as w:
            if w.getframerate() != SR or w.getnchannels() != 1 or w.getsampwidth() != 2:
                fail(f"{path} must be 16 kHz mono 16-bit PCM (D18)")
            return w.readframes(w.getnframes())
    except wave.Error as e:
        fail(f"{path} is not a 16-bit PCM WAV (D18): {e}")


def write_pcm16(path: Path, pcm: bytes) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rows() -> list[dict]:
    if not SUBSET_CSV.is_file():
        fail(f"{SUBSET_CSV} missing (run scripts/fetch_fleurs.py first)")
    with SUBSET_CSV.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        fail(f"{SUBSET_CSV} has no rows")
    return rows


def load_vad() -> ort.InferenceSession:
    if not SILERO_PATH.is_file():
        fail(f"model missing: {SILERO_PATH} (run scripts/download_models.py)")
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 1
    sess = ort.InferenceSession(str(SILERO_PATH), sess_options=opts,
                                providers=["CPUExecutionProvider"])
    names = sorted(i.name for i in sess.get_inputs())
    if names != ["input", "sr", "state"]:
        fail(f"unexpected Silero ONNX inputs {names}; expected input, sr, state")
    return sess


def speech_probs(sess: ort.InferenceSession, pcm: bytes) -> list[float]:
    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    state = np.zeros((2, 1, 128), dtype=np.float32)
    context = np.zeros(VAD_CONTEXT, dtype=np.float32)
    sr = np.array(SR, dtype=np.int64)
    probs = []
    for start in range(0, len(audio) - VAD_WINDOW + 1, VAD_WINDOW):
        x = np.concatenate([context, audio[start:start + VAD_WINDOW]])[None, :]
        out, state = sess.run(None, {"input": x, "state": state, "sr": sr})
        probs.append(float(out[0][0]))
        context = x[0, -VAD_CONTEXT:]
    return probs


def longest_run_s(probs: list[float]) -> float:
    """Longest speech run in seconds; gaps shorter than GAP_END_S do not end a run."""
    win_s = VAD_WINDOW / SR
    gap_windows = int(np.ceil(GAP_END_S / win_s))
    best = 0.0
    run_start = last_speech = None
    for i, p in enumerate(probs):
        if p <= VAD_THRESHOLD:
            continue
        if last_speech is not None and i - last_speech - 1 >= gap_windows:
            run_start = None  # gap long enough: previous run ended
        if run_start is None:
            run_start = i
        last_speech = i
        length = (last_speech - run_start + 1) * win_s
        if length >= MIN_RUN_S:
            best = max(best, length)
    return best


def main() -> None:
    rows = load_rows()
    OUT.mkdir(parents=True, exist_ok=True)

    # F1: shortest clip, whole (first one in CSV order on a tie).
    short = min(rows, key=lambda r: float(r["end"]))
    short_pcm = read_pcm16(ROOT / short["wav"])
    write_pcm16(OUT / "speech_short.wav", short_pcm)
    print(f"[F1] speech_short.wav <- FLEURS id {short['fleurs_id']} ({float(short['end']):.2f} s)")

    # F2: zeros.
    write_pcm16(OUT / "silence_5s.wav", b"\x00\x00" * int(SR * SILENCE_S))
    print(f"[F2] silence_5s.wav <- {SILENCE_S:.0f} s of zeros")

    # F3: first clip in CSV order with an unbroken speech run >= LONG_RUN_S.
    sess = load_vad()
    long_row = long_pcm = None
    long_run = 0.0
    for r in rows:
        if float(r["end"]) < LONG_RUN_S:
            continue
        pcm = read_pcm16(ROOT / r["wav"])
        run = longest_run_s(speech_probs(sess, pcm))
        print(f"     id {r['fleurs_id']}: {float(r['end']):.2f} s, longest run {run:.2f} s")
        if run >= LONG_RUN_S:
            long_row, long_pcm, long_run = r, pcm, run
            break
    if long_row is None:
        fail(f"no subset clip has an unbroken speech run >= {LONG_RUN_S:.0f} s (F3); "
             "tell Claude, do not pick a clip by hand")
    write_pcm16(OUT / "speech_long.wav", long_pcm)
    print(f"[F3] speech_long.wav <- FLEURS id {long_row['fleurs_id']} "
          f"({float(long_row['end']):.2f} s, longest run {long_run:.2f} s)")

    # F4: README with attribution and hashes.
    files = [
        ("speech_short.wav",
         f"FLEURS hy_am test, id {short['fleurs_id']}, {float(short['end']):.2f} s, whole clip "
         "(shortest clip in `eval/meta/fleurs_hy_am_test100.csv`)"),
        ("silence_5s.wav", f"{SILENCE_S:.0f} s of digital zeros, generated (no source)"),
        ("speech_long.wav",
         f"FLEURS hy_am test, id {long_row['fleurs_id']}, {float(long_row['end']):.2f} s, whole clip "
         f"(first subset clip with an unbroken Silero speech run >= {LONG_RUN_S:.0f} s; "
         f"longest run {long_run:.2f} s)"),
    ]
    table = "\n".join(f"| `{name}` | {desc} | `{sha256(OUT / name)}` |" for name, desc in files)
    readme = f"""# tests/fixtures — committed test fixtures (D22)

Generated by `python scripts/make_fixtures.py`; do not edit by hand. All files are 16 kHz mono 16-bit PCM WAV.

| File | Content | SHA-256 |
|---|---|---|
{table}

## Attribution (FLEURS clips)

- Source: **FLEURS** (Google), `google/fleurs` on Hugging Face, revision `{FLEURS_REV}`, hy_am test split.
- Licence: **CC-BY 4.0** — https://creativecommons.org/licenses/by/4.0/
- Paper: Conneau et al., "FLEURS: Few-shot Learning Evaluation of Universal Representations of Speech", 2022, https://arxiv.org/abs/2205.12446
- Changes made by us: audio converted from 32-bit float to 16-bit PCM WAV (D18); clips copied whole, not cut.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    print(f"[F4] README.md written")
    for name, _ in files:
        print(f"     {name}: {(OUT / name).stat().st_size} bytes, sha256 {sha256(OUT / name)}")


if __name__ == "__main__":
    main()
