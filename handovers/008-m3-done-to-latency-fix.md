# Handover 008 — M3 done → fix the latency problem (before M4) — 2026-11-01

**Start the new chat with:** `DECISIONS.md` + `TEST.md` + this file.

## Goal
M3 (walking skeleton, mic only) is done. The first file-mode runs break the 5 s latency rule badly. **The next work is fixing that latency problem**, before M4 proper (T2, T3, T4). Zaven decided this on 2026-11-01. Zaven tracks the time budget and decides how much time goes to it.

## Current state
- **M3 done**: S1–S8, all committed. App runs live (`--mic`) and in file mode (`--mic-wav`), with `quit` / unknown command / Ctrl+C (exit 130), errors exit 1. Default suite **22 passed** (`command_outputs/m3_s8_pytest.txt`, `m4_temp0_pytest.txt`). TEST.md: T1.1–T1.5 and T6 `passed`; T1.6, T2–T5 `not run`.
- Code: `app.py` (`run_session`), `src/arm_en_asr/{audio_capture,asr,translate,output,pipeline}.py`, tests `tests/test_{cli,audio_capture,asr,translate,output,pipeline}.py`.
- **`asr.py` now has `temperature=0.0`** (Zaven's decision, 2026-11-01: latency before a small accuracy loss). Written and tests pass. **Not yet confirmed committed** (see Pending), and **not yet recorded in DECISIONS.md** (proposed D3 addition below).
- Git: last known HEAD `8329363` (TEST.md: T6 passed; DECISIONS: D11 S8 additions, M3 done, R1 S8 finding).

## The problem: measurements so far
File mode on `eval/clips/mic_01.wav` (61 s, real-time feed, N = 1 ASR worker). Latency per line:

| Line start | Default fallback (`m3_s8_file_mic01.txt`) | `temperature=0` (`m4_file_mic01_temp0.txt`) | ASR text with temperature=0 |
|---|---|---|---|
| 00:00:01 | 3.2 s | 3.2 s | normal |
| 00:00:03 | 9.7 s | 9.7 s | normal (12 s segment) |
| 00:00:15 | 32.6 s | 13.2 s | **loop** «ԵբՈՈՈՈ…» |
| 00:00:20 | 82.0 s | 29.6 s | **loop** «այս, այս, այս, …» |
| 00:00:31 | 87.1 s | 27.3 s | **loop** «ԱՐՈՈՈՈ…» |
| 00:00:44 | 82.2 s | 21.5 s | normal (waits behind the loop) |
| 00:00:56 | 111.1 s | 25.8 s | **loop** «ԱՐՈՈՈՈ…» |

Live mic, short phrases (`m3_s8_live.txt`): 2.9–3.1 s on every line.

What this shows:
1. **Not RAM.** No swap growth during the temperature=0 run (swap 1197 → 1197 MB, 3.7–4.1 GB available; `free -m` in `m4_file_mic01_temp0.txt`).
2. **Whisper repetition loops are the main cause.** With fallback on, faster-whisper re-decoded these segments up to 6 times (temperatures 0.0–1.0), which explains the 111 s. With `temperature=0` it decodes once, but on 4 of 7 segments it still loops until the token limit (~448 tokens). That costs many seconds, and the loop text is now **printed** (the fallback used to hide it by retrying). This is more than the "slight accuracy drop" expected. The MT output for those lines is garbage too ("KOCHOCOTOSITOTS …").
3. **Backlog.** With N = 1, one slow segment delays every later one (line 00:00:44 is normal text but waits 21.5 s).
4. **Floor.** About 3 s even for a one-word phrase: 0.6 s VAD end silence + ≈ 2.4 s ASR + MT. Whisper's encoder always processes a 30 s window, so short segments cost about the same.
5. A full 12 s segment of normal speech still takes ≈ 9.7 s (line 00:00:03), so even without loops 12 s segments break 5 s.

## Exact next step (proposal, Zaven to approve before anything is written)
**Measure before changing more settings.** Write `scripts/diag_asr.py` (runs in `.venv`, read-only for the app), time-boxed like D5 (proposed: 45 min):
- Cut `mic_01.wav` into the same VAD segments the app uses (`WavSource(realtime=False)` + `Segmenter`).
- For each segment and each variant, print: segment length, ASR time, tokens generated, compression ratio, average log-probability, and whether it looped. Also per variant: CER of the whole clip's text against `eval/meta/mic_01.csv` (concatenated, same clean-up as T1.2), so the speed gain is weighed against accuracy.
- Variants (each a single change from the current setting `beam_size=5, temperature=0`):
  - a. current setting (baseline)
  - b. `beam_size=1` (greedy): faster decoding
  - c. a token cap per segment (`max_new_tokens` tied to segment length; the cap value is chosen from the reference texts' tokens per second): cuts a loop short
  - d. `repetition_penalty` (e.g. 1.1–1.3) and/or `no_repeat_ngram_size`: prevent loops (risk: Armenian is split into many small byte-level tokens, so `no_repeat_ngram_size` may damage normal text; CER shows it)
  - e. `cpu_threads` 4 vs 8
  - f. best combination of the above
- Output to `command_outputs/latency_diag_asr.txt`. Then Zaven picks the settings; `asr.py` changes only after that.

## Further options if settings alone are not enough (for Zaven to decide later)
- **N = 2 ASR workers** (D1, D2): removes the backlog behind one slow segment; RAM looks fine (no swap). CPU has only 2 P-cores, so measure.
- **Shorter segment cap** than 12 s (D8, L4; was planned for M8): less audio per call; but it does not reduce the ≈ 2.4 s fixed cost.
- **Drop looped output** (compression ratio > 2.4) instead of printing it: fixes the garbage lines but not the time.
- **Faster / non-looping ASR model**, pulled forward from M7: NVIDIA Armenian FastConformer CTC (D4) is non-autoregressive, so it cannot loop and should be much faster; needs the ONNX export (M7 plan). Whisper base/tiny: faster but even weaker Armenian.
- **GPU (MX550)**, D7/R18: time-boxed 1 h.

## Proposals still waiting for Zaven (not written)
- **D3 addition:** `- Addition (Zaven, 2026-11-01, M4): \`temperature=0.0\` in \`transcribe\`, so faster-whisper decodes each segment once and never re-decodes at higher temperatures. Reason: the S8 file-mode run on \`mic_01\` reached 111 s latency, and fallback retries on low-confidence Armenian were the leading suspect. The 5 s latency rule comes before a small loss in ASR accuracy. Result: \`command_outputs/m4_file_mic01_temp0.txt\`: max latency 111.1 s → 29.6 s, no swap growth, but 4 of 7 segments now print Whisper repetition loops.`
- **Section 3:** "Current milestone" still says M3 in progress. Proposed: `- **Current milestone:** latency fix (after M3, before M4; Zaven 2026-11-01).` Next step: `- **Next step:** latency fix: \`scripts/diag_asr.py\` measurements (see \`handovers/008-m3-done-to-latency-fix.md\`).`
- **R1:** append the temperature=0 result (max 29.6 s, loops are the main cause, not RAM).
- **D16:** add `diag_asr.py` to the scripts list once approved.

## Open questions
- Client's real setup (DECISIONS.md section 7): still to confirm.
- Time: how much of the remaining budget goes to the latency fix (Zaven decides; M4 is 2 h, buffer 1 h).

## Watch out for
- **Stale writes:** after every write, Claude reads the file back from the laptop and compares it byte for byte (`cmp`). This worked every time in this chat.
- Claude's cloud workspace has no models; every model run goes through Zaven (working rule 8).
- `asr.py` still says `temperature=0.0`; any further setting change is agreed first.
- TEST.md results log: rows are appended, never edited.
- M7 notes from handovers 005 / 007 still apply.

## Rules reminder
- Claude proposes; Zaven decides and runs every command, including every git command.
- Command outputs go to `command_outputs/<name>.txt` and are not committed.
- Nothing goes into DECISIONS.md / TEST.md until Zaven approves it.
- Small steps; no silent fallbacks; three-strikes rule.

## Pending commits
```
git add src/arm_en_asr/asr.py          # only if not committed yet
git commit -m "ASR temperature=0: no fallback re-decoding (latency over accuracy, R1)"

git add handovers/008-m3-done-to-latency-fix.md
git commit -m "handover 008: M3 done -> latency fix"
```
