# TEST.md — Live Armenian → English transcription + translation

> **How to use this file.** Every test entry, every pass criterion and every status change is agreed with Zaven **before** it is written here (working rule 10). Zaven runs all tests on his laptop; when Claude needs the output, Zaven saves it to `command_outputs/<name>.txt` and sends the path (rules 8–9). Decisions referenced as D# are in `DECISIONS.md`.

- Created: 2026-10-29 · Last updated: 2026-11-01

---

## 1. Conventions

- **IDs:** `T<group>.<n>` (e.g. `T1.3`). IDs are never reused, even if a test is removed.
- **Status values:** `not run` · `passed` · `not passed`. A status changes only after Zaven agrees.
- **How to run:** with `.venv` activated, from the repo root:
  - default suite: `python -m pytest -v`
  - one file: `python -m pytest tests/test_asr.py -v`
  - hardware tests: `python -m pytest -m hardware -v`
  - load test: `python -m pytest -m slow -v`
- **Markers:**
  - `hardware`: needs real PulseAudio devices and a person present.
  - `slow`: the load test.
  - A plain `pytest` run excludes both (configured in pytest settings).
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
| T2 | End-to-end latency, file mode | M4 (re-run M5) | not run |
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
- **Linked:** D3, D26, R5.
- **Input:** speech fixture.
- **Run:** `python -m pytest tests/test_asr.py -v`
- **Pass:**
  - Speech fixture → non-empty text, and at least 50 % of its letters are Armenian script.
  - `Asr` pointed at an empty folder → fails with a clear "model missing" error; no download attempted (A6, D15).
  - `token_cap` follows D26: 1.65 s → 40, 4.5 s → 107, 7 s → 166, 20 s → 220 tokens.
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
- **Linked:** D1, D13, L5.
- **Input:** stub ASR / MT (diarizer stub added in M6) that return results out of order.
- **Run:** `python -m pytest tests/test_pipeline.py -v`
- **Pass:**
  - Each line joins the right segment id.
  - Lines print in order of speech end.
  - Mic segments are always "Me".
  - A segment with empty ASR text prints no line, and later lines still print.
  - Latency = print time − `end_wall`.
  - A worker error or a worker-count mismatch makes the pipeline fail loudly.
- **Status:** passed (2026-11-01, see results log)

#### T1.6 — `diarizer` (M6)
- **Purpose:** speaker labels stay stable.
- **Linked:** D9, D17, R11.
- **Input:** a solo mic clip; a 2-speaker system clip (eval data).
- **Run:** `python -m pytest tests/test_diarizer.py -v`
- **Pass:**
  - Solo mic clip fed through the diarizer → 100 % of segments get the same speaker number.
  - 2-speaker system clip → % correct is reported, with no threshold.
- **Status:** not run

### T2 — End-to-end latency, file mode
- **Purpose:** prove that end of phrase → English line takes ≤ 5 s.
- **Linked:** D11, D12, D21, R1.
- **Milestone:** M4 (mic only); re-run in M5 with `--system-wav`.
- **Conditions:** demo conditions.
- **Run:** `python app.py --mic-wav <eval clip>` (M5: add `--system-wav <eval clip>`). WAVs are fed at real-time speed.
- **Pass:** every printed line has latency ≤ 5 s. Record median, p95 and max in the results log.
- **Status:** not run

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
