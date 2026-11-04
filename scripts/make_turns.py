"""M5: realistic turn-taking clips for two devices (DECISIONS D27 addition, 2026-11-04; L12).

Builds two WAVs of equal length from the eval clips, so that only one side talks at a time, as in a
call: a turn of mic_01 on the mic track, then a turn of sys_01 on the system track, and so on. The
track that is not talking is silent (zeros). Output is gitignored like all of eval/clips/.

    python scripts/make_turns.py > command_outputs/m5_make_turns.txt 2>&1

Rules:
- Turns of about 12 s: each turn ends at the quietest 100 ms window between 10 and 15 s into it
  (lowest RMS); if 15 s or less of the source is left, the turn takes all of it.
- 1.0 s of silence on both tracks at the start and between turns.
- Turns alternate system, mic, system, ...; when one source has run out, the other's remaining turns
  follow one after another (still one side at a time).
- Inputs must be 16 kHz mono 16-bit PCM WAV, or the script stops with a clear error (working rule 2).
Prints one row per turn: track, source span, output span.
"""
from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CLIPS = ROOT / "eval" / "clips"
INPUTS = {"mic": CLIPS / "mic_01.wav", "system": CLIPS / "sys_01.wav"}
OUTPUTS = {"mic": CLIPS / "turns_mic.wav", "system": CLIPS / "turns_sys.wav"}
ORDER = ("system", "mic")     # first turn: system (sys_01 opens with speech)

SR = 16000
TURN_MIN_S, TURN_MAX_S = 10.0, 15.0
QUIET_WIN_S = 0.1
GAP_S = 1.0


def read_wav(path: Path) -> np.ndarray:
    if not path.is_file():
        sys.exit(f"ERROR: missing clip {path}")
    with wave.open(str(path), "rb") as w:
        if w.getframerate() != SR or w.getnchannels() != 1 or w.getsampwidth() != 2:
            sys.exit(f"ERROR: {path} must be 16 kHz mono 16-bit PCM WAV, got {w.getframerate()} Hz, "
                     f"{w.getnchannels()} ch, {8 * w.getsampwidth()}-bit")
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def write_wav(path: Path, pcm: np.ndarray) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.astype(np.int16).tobytes())


def turn_ends(pcm: np.ndarray) -> list[int]:
    """Sample index where each turn ends (quietest window between TURN_MIN_S and TURN_MAX_S)."""
    win = int(QUIET_WIN_S * SR)
    ends, pos = [], 0
    while pos < len(pcm):
        if len(pcm) - pos <= int(TURN_MAX_S * SR):
            ends.append(len(pcm))
            break
        lo, hi = pos + int(TURN_MIN_S * SR), pos + int(TURN_MAX_S * SR)
        x = pcm[lo:hi].astype(np.float64)
        n = len(x) // win
        rms = np.sqrt((x[:n * win].reshape(n, win) ** 2).mean(axis=1))
        best = int(np.argmin(rms))
        cut = lo + best * win + win // 2       # middle of the quietest window
        ends.append(cut)
        pos = cut
    return ends


def main() -> None:
    pcm = {dev: read_wav(p) for dev, p in INPUTS.items()}
    turns = {}
    for dev in pcm:
        starts = [0] + turn_ends(pcm[dev])[:-1]
        turns[dev] = list(zip(starts, turn_ends(pcm[dev])))

    gap = np.zeros(int(GAP_S * SR), dtype=np.int16)
    tracks = {dev: [gap] for dev in pcm}
    out_pos = len(gap)
    rows = []
    idx = {dev: 0 for dev in pcm}
    k = 0
    while any(idx[d] < len(turns[d]) for d in pcm):
        dev = ORDER[k % 2]
        k += 1
        if idx[dev] >= len(turns[dev]):
            continue                            # this source has run out: the other continues
        a, b = turns[dev][idx[dev]]
        idx[dev] += 1
        piece = pcm[dev][a:b]
        for d in pcm:
            tracks[d].append(piece if d == dev else np.zeros(len(piece), dtype=np.int16))
            tracks[d].append(gap)
        rows.append((dev, a / SR, b / SR, out_pos / SR, (out_pos + len(piece)) / SR))
        out_pos += len(piece) + len(gap)

    out = {d: np.concatenate(tracks[d]) for d in pcm}
    assert len(out["mic"]) == len(out["system"])
    for d, path in OUTPUTS.items():
        write_wav(path, out[d])

    print(f"inputs: mic = {INPUTS['mic'].relative_to(ROOT)} ({len(pcm['mic']) / SR:.2f} s), "
          f"system = {INPUTS['system'].relative_to(ROOT)} ({len(pcm['system']) / SR:.2f} s)")
    print(f"turns {TURN_MIN_S:.0f}-{TURN_MAX_S:.0f} s cut at the quietest {QUIET_WIN_S * 1000:.0f} ms, "
          f"gap {GAP_S:.1f} s, first turn: {ORDER[0]}")
    print("turn\ttrack\tsource_start\tsource_end\tout_start\tout_end\tlength")
    for i, (dev, a, b, oa, ob) in enumerate(rows, 1):
        print(f"{i}\t{dev}\t{a:.2f}\t{b:.2f}\t{oa:.2f}\t{ob:.2f}\t{b - a:.2f}")
    print(f"wrote {OUTPUTS['mic'].relative_to(ROOT)} and {OUTPUTS['system'].relative_to(ROOT)}: "
          f"{len(out['mic']) / SR:.2f} s each, {len(rows)} turns "
          f"(mic {sum(r[0] == 'mic' for r in rows)}, system {sum(r[0] == 'system' for r in rows)})")


if __name__ == "__main__":
    main()
