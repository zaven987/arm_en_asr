# TEST.md — Live Armenian → English transcription + translation

> **How to use this file.** Every test entry, every pass criterion and every status change is agreed with Zaven **before** it is written here (working rule 10). Zaven runs all tests on his laptop; when Claude needs the output, Zaven saves it to `command_outputs/<name>.txt` and sends the path (rules 8–9). Decisions referenced as D# are in `DECISIONS.md`.

- Created: 2026-10-29 · Last updated: 2026-11-04

---

## 1. Conventions

- **IDs:** `T<group>.<n>` (e.g. `T1.3`). IDs are never reused, even if a test is removed.
- **Status values:** `not run` · `passed` · `not passed`. A status changes only after Zaven agrees.
- **How to run:** with `.venv` activated, from the repo root:
  - default suite: `python -m pytest -v`
  - one file: `python -m pytest tests/test_asr.py -v`
  - hardware tests: `python -m pytest -m hardware -v`
  - load test: `python -m pytest -m slow -v`
  - eval-clip tests: `python -m pytest -m eval -v`
- **Markers:**
  - `hardware`: needs real PulseAudio devices and a person present.
  - `slow`: the load test.
  - `eval` (added 2026-11-04, D22): needs the gitignored eval clips in `eval/clips/`; a missing clip makes the test fail, never skip.
  - A plain `pytest` run excludes all three (configured in pytest settings).
- **Fail loudly in tests too:** a missing model or fixture makes the test **fail** with a clear error. Tests are never silently skipped (working rule 2, D22).
- **Fixtures** (D22): small committed files in `tests/fixtures/`:
  - a few seconds of FLEURS hy_am audio (CC-BY 4.0, attribution in `tests/fixtures/README.md`)
  - generated silence
  - ≥ 12 s continuous-speech audio
- **File mode** (D21): `--mic-wav` / `--system-wav` feed the WAV at **real-time speed**, so measured latency matches live use.
- **Demo conditions** (DECISIONS section 7): browser with a Meet/Zoom call tab open, laptop plugged in.

---

## 2. Test catalogue

| ID | Name | Milestone | Status |
|---|---|---|---|
| T1.1 | Unit: `audio_capture` + VAD (file input) | M3 | passed |
| T1.2 | Unit: `asr` | M3 | passed |
| T1.3 | Unit: `translate` | M3 | passed |
| T1.4 | Unit: `output` line format | M3 | passed |
| T1.5 | Unit: `pipeline` join + order | M3 | passed |
| T1.6 | Unit: `diarizer` | M6 | not run |
| T2 | End-to-end latency, file mode | M4 (re-run M5) | passed |
| T3 | Capture smoke test (`hardware`) | M4 (mic), M5 (both) | not run |
| T4 | Load test, D2 (`slow`) | M4 | not run |
| T5 | Virtual-sink capture test | M9 | not run |
| T6 | CLI fail-loudly checks | M3 | passed |

---

## 3. Test entries

### T1 — Unit tests per module on fixture audio

#### T1.1 — `audio_capture` + VAD (file input)
- **Purpose:** VAD produces correct segments from a file input.
- **Linked:** D8, D10, D26, R7, R12.
- **Input:** speech fixture; silence fixture; ≥ 12 s continuous-speech fixture.
- **Run:** `python -m pytest tests/test_audio_capture.py -v`
- **Pass:**
  - Speech fixture → at least 1 segment, each 0.3–7 s long, 16 kHz mono.
  - Silence fixture → 0 segments.
  - Continuous-speech fixture → cut at the 7 s cap (D8, D26; was 12 s until 2026-11-01).
- **Status:** passed (2026-10-31, see results log)

#### T1.2 — `asr`
- **Purpose:** ASR runs and returns Armenian text. This is a sanity check, not a quality bar.
- **Linked:** D3, D26, D30, R5.
- **Input:** speech fixture.
- **Run:** `python -m pytest tests/test_asr.py -v`
- **Needs:** the MX550 GPU (D30 G4e); without it the tests fail loudly, never skip (D22).
- **Pass:**
  - Speech fixture → non-empty text, and at least 50 % of its letters are Armenian script.
  - `Asr` pointed at an empty folder → fails with a clear "model missing" error; no download attempted (A6, D15).
  - `Asr.warm_up()` runs without error (D26 addition, 2026-11-04).
  - `token_cap` follows D26: 1.65 s → 40, 4.5 s → 107, 7 s → 166, 20 s → 220 tokens.
  - `Asr` loads Whisper on cuda `int8_float16` (D30).
- **Status:** passed (2026-11-01, see results log)

#### T1.3 — `translate`
- **Purpose:** MT runs and returns English.
- **Linked:** D5, R6.
- **Input:** 3 FLEURS hy_am sentences (reference text).
- **Run:** `python -m pytest tests/test_translate.py -v`
- **Pass:**
  - Non-empty English for each sentence, with no Armenian characters.
  - Each English output is at most 2× the length of its Armenian input, in characters (catches repetition loops; D5, L10).
- **Status:** passed (2026-11-01, see results log)

#### T1.4 — `output` line format
- **Purpose:** the terminal line matches the agreed format.
- **Linked:** D12, DECISIONS section 8.
- **Input:** fixed in-test records.
- **Run:** `python -m pytest tests/test_output.py -v`
- **Pass:**
  - A fixed record gives exactly the line format in DECISIONS section 8.
  - Offset 83 s → `[00:01:23]`.
  - Latency 5.1 s → warning shown; 4.9 s → no warning.
- **Status:** passed (2026-11-01, see results log)

#### T1.5 — `pipeline` join + order
- **Purpose:** results are joined by segment id and printed in the right order.
- **Linked:** D1, D13, D27, L5.
- **Input:** stub ASR / MT that return results out of order (diarizer stub added in M5 S1).
- **Run:** `python -m pytest tests/test_pipeline.py -v`
- **Pass:**
  - Each line joins the right segment id.
  - Lines print in order of speech end.
  - Mic segments are always "Me".
  - System segments carry the diarizer's label; the diarizer is called for system segments only; a system segment without a diarizer is refused loudly (D27 E4); a diarizer error fails loudly.
  - A segment with empty ASR text prints no line, and later lines still print.
  - Latency = print time − `end_wall`.
  - A worker error or a worker-count mismatch makes the pipeline fail loudly.
- **Status:** passed (2026-11-01, see results log)

#### T1.6 — `diarizer` (M6)
- **Purpose:** speaker labels stay stable.
- **Linked:** D9, D17, R11.
- **Input:** a solo mic clip; a 2-speaker system clip (eval data).
- **Run:** `python -m pytest -m eval tests/test_diarizer.py -v` (marker `eval`, added 2026-11-04)
- **Pass:**
  - Solo mic clip fed through the diarizer → 100 % of segments get the same speaker number.
  - 2-speaker system clip → % correct is reported, with no threshold.
- **Scoring** (agreed 2026-11-04, D27): each segment gets the reference speaker in `eval/meta/sys_01.csv` it overlaps most in time; segments with no overlap are counted and left out. Speaker numbers are matched to reference names by the best one-to-one mapping. Reported: % correct, number of speakers found, short segments separately. The threshold is tuned on `mic_01`–`03` only, never on `sys_01` (R13).
- **Status:** not run

### T2 — End-to-end latency, file mode
- **Purpose:** prove that end of phrase → English line takes ≤ 5 s.
- **Linked:** D11, D12, D21, D27, D28, R1, L12.
- **Milestone:** M4 (mic only); re-run in M5 (S7) with both devices on the turn-taking files.
- **Conditions:** demo conditions.
- **Run:** `python app.py --mic-wav <eval clip>`. WAVs are fed at real-time speed.
  - M5 (changed 2026-11-04, D27): `python app.py --mic-wav eval/clips/turns_mic.wav --system-wav eval/clips/turns_sys.wav`. The turn files are made by `python scripts/make_turns.py` from `mic_01` + `sys_01` (one side talks at a time, as in a call).
  - The overlap case (`mic_01` + `sys_01` played together) is **not** T2: it is a recorded measurement and known limitation L12.
- **Pass:** every printed line has latency ≤ 5 s. Record median, p95 and max in the results log.
- **Status:** passed (2026-11-01, mic only, see results log; re-run in M5 S7 on the turn files)

### T3 — Capture smoke test (`hardware`)
- **Purpose:** real devices deliver real audio.
- **Linked:** D10, R9.
- **Milestone:** M4 (mic); M5 (mic + system monitor).
- **Setup:** Zaven speaks into the mic and plays a video so the monitor source has sound. Each device is opened with `parec` for 3 s.
- **Run:** `python -m pytest -m hardware tests/test_capture_smoke.py -v`
- **Pass, per device:**
  - at least 2.5 s of samples received
  - RMS above −50 dBFS (not silent)
- **Status:** not run

### T4 — Load test (D2, `slow`)
- **Purpose:** find how many segments the laptop can process in parallel before RAM or latency breaks.
- **Linked:** D1, D2, R1, R8, R17.
- **Milestone:** M4.
- **Conditions:** demo conditions (Meet/Zoom tab open, plugged in).
- **Grid:** N = 1, 2, 3 ASR workers × K = 1, 2, 4, 6 segments submitted at once (segments from eval clips).
- **Recorded per (N, K):** peak RSS, swap use (start / end), median / p95 / max latency, segments processed per minute.
- **Run:** `python -m pytest -m slow tests/test_load.py -v`
- **Pass:** at least one (N, K) combination where:
  - max latency ≤ 5 s, and
  - swap use grows by no more than 100 MB during the run.
- **Tie-breaker:** if several combinations pass, choose by this order:
  1. Highest segments processed per minute.
  2. Highest N (number of workers).
  3. Lowest max latency.
- **Result:** the chosen (N, K) is recorded as a new D# in DECISIONS.md.
- **Status:** not run

### T5 — Virtual-sink capture test (M9)
- **Purpose:** play a clip into a PulseAudio null sink and capture its `.monitor` via `--system`, so the system path is tested without a real call.
- **Linked:** D10, D20.
- **Milestone:** M9. Cut first if time runs short (working rule 12).
- **Run / Pass:** to be agreed with Zaven when we reach M9.
- **Status:** not run

### T6 — CLI fail-loudly checks
- **Purpose:** errors are clear and the app never silently falls back.
- **Linked:** working rule 2, D11, D15.
- **Milestone:** M3.
- **Run:** `python -m pytest tests/test_cli.py -v`
- **Pass, in all cases:**
  - **Unknown device name** passed to `--mic` / `--system` → the app exits with a non-zero code and a clear error naming the device.
  - **Missing model** → the app exits with a non-zero code and a clear error naming the model. No download is attempted.
  - **Unknown stdin command** (any text other than `quit`) → prints "unknown command" and keeps running.
  - **`quit` + Enter** → clean shutdown with exit code 0. All `parec` subprocesses and worker threads are stopped.
- **Status:** passed (2026-11-01, see results log)

---

## 4. Results log

Rows are only ever appended, never edited. One row per run.

| Date | Test ID | Commit | Conditions | Key numbers | Status | Notes |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |
| 2026-10-31 | T1.1 | 83c9def | file input fed with `realtime=False` (V6); plain `python -m pytest -v` run | 3/3 T1.1 tests passed (speech, silence, 12 s cut); whole default suite 6 passed in 0.34 s | passed | `command_outputs/m3_s3_pytest.txt` |
| 2026-11-01 | T1.2 | 6720d83 | plain `python -m pytest -v -s` run | 2/2 T1.2 tests passed (Armenian text 100 % Armenian letters; missing model → clear error); whole default suite 8 passed in 5.19 s | passed | `command_outputs/m3_s4_pytest.txt`, `command_outputs/m3_s4b_pytest.txt` |
| 2026-11-01 | T1.3 | ff6cef1 | plain `python -m pytest -v -s` run; `no_repeat_ngram_size=3` (D5 C1) | 1/1 T1.3 test passed (3 FLEURS sentences: non-empty English, no Armenian letters, length ≤ 2× Armenian); whole default suite 9 passed in 6.07 s | passed | `command_outputs/m3_s5b_pytest.txt`; first run without the fix looped on sentence 2 (`m3_s5_pytest.txt`, `m3_s5_diag_mt.txt`) |
| 2026-11-01 | T1.4 | 6cf8810 | plain `python -m pytest -v -s` run | 4/4 T1.4 tests passed (exact section 8 format; 83 s → `[00:01:23]`, 83.9 s truncated; 5.1 s → warning; 4.9 s → none); whole default suite 13 passed in 6.09 s | passed | `command_outputs/m3_s6_pytest.txt` |
| 2026-11-01 | T1.5 | 8a7b9a7 | plain `python -m pytest -v -s` run; stub ASR / MT, out-of-order finishing forced with Event gates (3 workers) | 7/7 T1.5 tests passed (join by id; ASR finished 3,2,1 → printed 1,2,3; mic = "Me", system refused; empty ASR text → no line, later lines print; latency = clock − end_wall; worker error and worker-count mismatch fail loudly); whole default suite 20 passed in 6.21 s | passed | `command_outputs/m3_s7_pytest.txt` |
| 2026-11-01 | T6 | fb25231 | plain `python -m pytest -v -s` run; live on a real PulseAudio source, no person | 5/5 T6 tests passed (unknown --mic / --system device; missing model; unknown stdin command keeps running; quit → exit 0, "stopped", no parec left); whole default suite 22 passed in 8.40 s | passed | `command_outputs/m3_s8_pytest.txt` |
| 2026-11-01 | T1.1 | ad8b730 | plain `python -m pytest -v -s` run; VAD cap 7 s (D26) | 3/3 T1.1 tests passed (speech, silence, cut at 7 s); whole default suite 23 passed in 6.82 s | passed | `command_outputs/d26_pytest.txt` |
| 2026-11-01 | T1.2 | ad8b730 | same run; D26 ASR settings (greedy, no timestamps, token cap) | 3/3 T1.2 tests passed (Armenian text; missing model → clear error; token_cap follows D26) | passed | `command_outputs/d26_pytest.txt` |
| 2026-11-01 | T2 | ad8b730 | file mode `mic_01` (61 s, real-time feed), mic only, N = 1, D26 settings; Meet/Zoom tab open: not confirmed | 11 lines; latency median 4.1 s, p95 4.8 s, max 4.8 s; 0 lines > 5 s; swap 1051 → 1051 MB; 5/11 lines end with ` ...` (L11) | passed | `command_outputs/d26_t2_mic01.txt` |
| 2026-11-04 | T1.5 | 2ed8403 | plain `python -m pytest -v -s` run; stub ASR / MT / diarizer, out-of-order finishing forced with Event gates | 14/14 T1.5 tests passed (the earlier checks, plus: system lines carry the diarizer label; diarizer called for system segments only; late label still prints in order; empty ASR text on a system segment → labelled, no line; system segment without a diarizer refused; unknown device refused; diarizer error or empty label fails loudly); whole default suite 30 passed in 7.32 s | passed | `command_outputs/m5_s1_pytest.txt` |
| 2026-11-04 | — (M5 S2 measurement, not T2) | 2ed8403 + `diag_two_devices.py` | `mic_01` + `sys_01` played together (overlap, 89 s), real-time feed, stub diarizer; Zoom tab open, plugged in | 27 lines each; n1t4 (N 1, 4 threads): median 14.1 s, p95 21.0 s, max 23.0 s, 26 > 5 s, peak RSS 877 MB, swap +0 MB; n2t4: max 23.2 s, 26 > 5 s, 1059 MB, swap +183 MB; n2t2: max 18.2 s, 25 > 5 s, 1087 MB, swap +78 MB; 13/27 lines cut by the token cap | measurement | `command_outputs/m5_s2_two_devices.txt`; result: D28 (N = 1), L12 |
| 2026-11-04 | — (M5 turn-taking measurement, stub diarizer; pre-check for T2) | a040565 | `turns_mic.wav` + `turns_sys.wav` (164 s, 13 turns, one side at a time; `make_turns.py`), real-time feed, N = 1, 4 threads; Zoom tab open, plugged in | 28 lines (mic 12, system 16); median 4.1 s, p95 6.0 s, max 6.7 s; 5 lines > 5 s (4 cut by the token cap, 1 queued behind one); 9/28 cut; peak RSS 886 MB; swap 1593 → 1592 MB | not passed (≤ 5 s rule) | `command_outputs/m5_turns_n1t4.txt`, `m5_make_turns.txt` |
| 2026-11-05 | T1.2 | c8f0eec | plain `python -m pytest -v -s` run; repetition_penalty 1.1 + warm_up (D26 additions) | 4/4 T1.2 tests passed (Armenian text; missing model → clear error; token_cap follows D26; warm_up runs); whole default suite 31 passed in 14.57 s | passed | `command_outputs/m5_rp_pytest.txt` |
| 2026-11-05 | — (M5 turn-taking measurement, stub diarizer; pre-check for T2) | c8f0eec | turn files (164 s), real-time feed, N = 1, 4 threads, repetition_penalty 1.1, warm-up; load average 2.03 at start; Zoom tab open, plugged in | 28 lines (mic 12, system 16); median 4.4 s, p95 5.4 s, max 5.9 s; 3 lines > 5 s (5.09, 5.38, 5.93 s, all mic; 2 not cut, none queued); 4/28 cut; first line 4.81 s; peak RSS 881 MB; swap 1499 → 1567 MB | not passed (≤ 5 s rule) | `command_outputs/m5_turns_n1t4_rp.txt` |
| 2026-11-05 | — (M5 turn-taking measurement on GPU, D29 G3; pre-check for T2) | 7647ae5 (same code, committed after the run) | turn files (164 s), real-time feed, N = 1, ASR on MX550 cuda int8_float16 (.venv-gpu), MT / VAD on CPU, repetition_penalty 1.1, warm-up; load average 0.37 at start; Zoom tab open, plugged in | 28 lines (mic 12, system 16); median 1.2 s, p95 1.5 s, max 1.5 s; 0 lines > 5 s; 1/28 cut; peak RSS 729 MB; swap 1641 → 1641 MB; VRAM 420 MB | passed (≤ 5 s rule) | `command_outputs/m5_g3_turns_gpu.txt` |
