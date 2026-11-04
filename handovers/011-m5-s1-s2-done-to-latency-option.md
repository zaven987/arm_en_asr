# Handover 011 — M5 S1 + S2 done, turn-taking test not yet passed → latency decision — 2026-11-05

**Start the new chat with:** `DECISIONS.md` + `TEST.md` + this file.

## Goal
M5 (second device) then M6 (diarizer), plan S1–S7 in **D27**. Before S3, a realistic two-device turn-taking test must pass (every line ≤ 5 s). Time is not the constraint for M5/M6 (Zaven, 2026-11-04).

## Current state
- Git: HEAD `c8f0eec` ("M5: repetition_penalty 1.1 + ASR warm-up (D26 additions), T1.2 warm-up test") on `main`. Everything written in the last chat is committed (checked from `.git/logs/HEAD`). This handover is not committed yet.
- Default suite: **31 passed** (`command_outputs/m5_rp_pytest.txt`).
- **Done:**
  - **S1** (`2ed8403`): `Pipeline(..., diarizer=None)`; system segments accepted only with a diarizer; diarizer thread labels system segments in submit order; G1–G7. T1.5 14/14 passed (logged).
  - **S2**: `scripts/diag_two_devices.py` (K1–K7; options `--mic`, `--system`, `--variants` added later; calls `asr.warm_up()`). Overlap case `mic_01` + `sys_01`: every variant far over 5 s (queue builds up) → **D28** N = 1, `cpu_threads` 4; **L12** (both sides talking at once). Logged as a measurement row.
  - **Turn-taking test** (D27 addition): `scripts/make_turns.py` → `eval/clips/turns_mic.wav` + `turns_sys.wav` (164 s, 13 turns, one side at a time). First run: max 6.7 s, 5/28 > 5 s, not passed (logged).
  - **Fix (D26 additions):** `repetition_penalty=1.1` (from `diag_asr.py`, `m5_diag_asr_rp.txt`: loops 13/31 → 3/31, CER 59.0/45.8/36.1 → 46.7/24.8/31.1 %) + `Asr.warm_up()` called by the app and by `diag_two_devices.py`.
  - `pytest.ini` has the `eval` marker (excluded by default; D22).
- **Turn-taking re-run with the fix** (`command_outputs/m5_turns_n1t4_rp.txt`): 28 lines, median 4.4 s, p95 5.4 s, **max 5.9 s, 3 lines > 5 s** (5.09, 5.38, 5.93 s, all mic; 2 not cut, none queued); cut 9 → 4; first line 6.75 → 4.81 s (warm-up works); swap +68 MB; load average 2.03 at start (was 0.23 in the first run). **Still not passed.** Cause: per-segment cost (0.6 s end silence + ≈ 4.3–4.7 s ASR on dense 6–7 s mic segments + MT) sits right at 5 s; no backlog.
- `app.py` still refuses `--system` (E4) until S6.

## Pending (proposed, NOT answered by Zaven yet)
1. **Two results rows** (write only after approval; Zoom status to confirm first):
   ```
   | 2026-11-05 | T1.2 | c8f0eec | plain `python -m pytest -v -s` run; repetition_penalty 1.1 + warm_up (D26 additions) | 4/4 T1.2 tests passed (Armenian text; missing model → clear error; token_cap follows D26; warm_up runs); whole default suite 31 passed in 14.57 s | passed | `command_outputs/m5_rp_pytest.txt` |
   | 2026-11-05 | — (M5 turn-taking measurement, stub diarizer; pre-check for T2) | c8f0eec | turn files (164 s), real-time feed, N = 1, 4 threads, repetition_penalty 1.1, warm-up; load average 2.03 at start; Zoom tab: <to confirm>, plugged in | 28 lines (mic 12, system 16); median 4.4 s, p95 5.4 s, max 5.9 s; 3 lines > 5 s (5.09, 5.38, 5.93 s, all mic; 2 not cut, none queued); 4/28 cut; first line 4.81 s; peak RSS 881 MB; swap 1499 → 1567 MB | not passed (≤ 5 s rule) | `command_outputs/m5_turns_n1t4_rp.txt` |
   ```
2. **Was the Zoom tab open** during the re-run? (Zaven: laptop is plugged in for all tests.)
3. **Latency decision — options proposed:**
   - **Option 1 (Claude recommends first):** shorter segments, VAD cap 6 s and/or end silence 0.5 s; saves ≈ 0.2–0.4 s per line; costs more mid-word cuts (L4) and possibly CER (D26 measured worse CER at 6 s, but before the penalty). Measure without changing the app:
     - CER/ASR: `python scripts/diag_asr.py eval/clips/mic_01.wav eval/clips/mic_02.wav eval/clips/mic_03.wav --variants g+b+c+d1 --seg-cap 6,7 > command_outputs/m5_diag_asr_cap6.txt 2>&1`
     - Latency: add `--seg-cap` and `--end-silence` options to `diag_two_devices.py` (patch `audio_capture.CAP` / `END_SILENCE` in the child process only, as `diag_asr.py` already does with `--seg-cap`), then re-run the turn test per setting.
   - **Option 2:** Whisper on the MX550 GPU (M7 work brought forward, D7, R18; needs CUDA libs in `.venv`). Biggest gain, biggest setup risk.
   - **Option 3:** accept 3/28 lines at 5.1–5.9 s; breaks the only hard rule (section 4), so Zaven's call, recorded as a limitation.
   - Note: run-to-run variation is unknown (one run each, background load differed).

## Exact next step
Get Zaven's answers to Pending 1–3. Then, if Option 1: propose the exact `diag_two_devices.py` option changes, write them after approval, and give Zaven the commands. If the turn test passes → propose S3 details (`app.py` + `audio_capture.py`: two sources, E1 clock offsets, E2/E3 end rules; `--system` still refused).

## Still open from earlier
- L11 note (handover 010, proposed 2026-11-01, not answered): token cap can stop mid-letter → `�` before ` ...`.
- Client's real setup (DECISIONS section 7).
- T3 / T4 postponed.
- README sections to update after M5/M6 (list in handover 010).

## Watch out for
- **Stale writes happened twice more** (DECISIONS.md on 2026-11-04): the copy tool wrote an older version. Always write each new version under a **fresh folder name**, copy, re-stage from the laptop and `cmp` byte for byte; re-send from a fresh folder if it differs.
- Claude has no shell on the laptop; Zaven runs every command and every git command.
- No silent fallbacks; system lines never mislabelled (E4).
- TEST.md results log: append only.

## Rules reminder
- Claude proposes; Zaven decides and runs every command.
- Command outputs go to `command_outputs/<name>.txt`, never committed.
- Nothing into DECISIONS.md / TEST.md until Zaven approves it.

## Pending commits
```
git add handovers/011-m5-s1-s2-done-to-latency-option.md
git commit -m "handover 011: M5 S1+S2 done, turn-taking test not passed -> latency decision"
```
