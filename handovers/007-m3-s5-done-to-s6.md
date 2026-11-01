# Handover 007 — M3 S4–S5 done → S6 (`output.py`) — 2026-11-01

**Start the new chat with:** `DECISIONS.md` + `TEST.md` + this file.

## Goal
Continue milestone **M3 — Walking skeleton, mic only** (3 h budget; Zaven monitors time). Plan S1–S8, each step committed separately. S1–S5 are done in code; next is **(1) record T1.3 as passed**, then **S6 `output.py` + T1.4**.

| Step | Content | Tests | Status |
|---|---|---|---|
| S1 | `pytest.ini`, `__init__.py`, `app.py` CLI (D11), device + model checks | T6 part 1 | done |
| S2 | `scripts/make_fixtures.py` + `tests/fixtures/` | — | done |
| S3 | `audio_capture.py` | T1.1 | done, passed |
| S4 | `asr.py` (D3, A1–A6) | T1.2 | done, passed (`6720d83`) |
| S5 | `translate.py` (D5, B1–B6, C1–C3) | T1.3 | done in code (`ff6cef1`), all checks pass; **TEST.md status not yet recorded** |
| S6 | `output.py`: line format + latency warning (D12) | T1.4 | **next** |
| S7 | `pipeline.py`: threads/queues, join by id, order by speech end, latency (D1, D13) | T1.5 | — |
| S8 | connect everything in `app.py`: live mic + file mode, stdin `quit`; first manual runs | T6 part 2 | — |

## Current state
- Code: `app.py`, `src/arm_en_asr/{__init__,audio_capture,asr,translate}.py`, `tests/{test_cli,test_audio_capture,test_asr,test_translate}.py`, `scripts/{…,make_fixtures,diag_mt}.py`.
- Default suite: **9 passed in 6.07 s** (`command_outputs/m3_s5b_pytest.txt`): T6 part 1 (3), T1.1 (3), T1.2 (2), T1.3 (1).
- `asr.py`: `Asr(model_dir).transcribe(audio) -> str`; faster-whisper small, CPU int8, `cpu_threads=4`, `num_workers=1`, `language="hy"`, `beam_size=5`, `vad_filter=False`, `condition_on_previous_text=False`; own "model missing" check.
- `translate.py`: `Mt(model_dir).translate(armenian) -> str`; opus-mt-hy-en CT2 int8, `inter_threads=1`, `intra_threads=2`, `beam_size=2`, **`no_repeat_ngram_size=3`**; empty input → `""`; own "model missing" check (no test, B5).
- MT finding (D5, L10): opus-mt-hy-en **itself** loops on FLEURS sentence 2 («6-6-6-…-a-a-a-…»), also the original PyTorch model, any beam, float32. Only `no_repeat_ngram_size=3` stops it (`command_outputs/m3_s5_diag_mt.txt`). Meaning errors remain (e.g. "solar system", "six or six") → M7 bake-off vs NLLB. T1.3 now also checks English ≤ 2× Armenian length in characters (normal 0.72–1.64×, loop 2.32–2.47×; narrow margin, re-check if inputs change).
- TEST.md: T1.1, T1.2 `passed` with results rows; T1.3 entry has the 2-bullet pass criteria but status still `not run`; T6 `not run` until S8.
- DECISIONS.md: status line for S5 still says "T1.3 to be re-run" and Next step says "re-run T1.3 … then S6" — both to be updated by step 1 below.
- Git: last commit `ff6cef1` (S5, all files incl. DECISIONS/TEST at their current state). Pending commit: this handover (see below).

## Decisions made in this chat (already in DECISIONS.md)
- **D3 addition (A1–A6):** load/transcribe settings above; `num_workers` must equal N when M4 uses N > 1 workers; M1's RTF 0.58 was with default threads, so T4 measures the 4-thread setting.
- **D5 additions (B1–B6, C1–C3):** settings above; diagnosis + 30-min time-box; C1 `no_repeat_ngram_size=3` with its trade-off (one segment's English can never contain the same 3-token sequence twice); C2 length check in T1.3; C3 output-length cap **rejected**.
- **D16:** `scripts/diag_mt.py` (committed; runs in `.venv-convert`). Its off-by-one in the loop flag for variant e is known and **will not be fixed** (Zaven, 2026-11-01).
- **L10:** weak MT (opus-mt-hy-en): wrong meaning on clean input; repetition loops on numbers / hyphenated words (loop guarded, meaning → M7).
- Status line fix: "Next step" now points at the latest handover.

## Exact next step

### Step 1 — record S5 (proposal, Zaven to approve before Claude writes)
- **TEST.md** catalogue: `| T1.3 | Unit: \`translate\` | M3 | passed |`; T1.3 entry `- **Status:** passed (2026-11-01, see results log)`; results-log row appended below the T1.2 row:
  ```
  | 2026-11-01 | T1.3 | ff6cef1 | plain `python -m pytest -v -s` run; `no_repeat_ngram_size=3` (D5 C1) | 1/1 T1.3 test passed (3 FLEURS sentences: non-empty English, no Armenian letters, length ≤ 2× Armenian); whole default suite 9 passed in 6.07 s | passed | `command_outputs/m3_s5b_pytest.txt`; first run without the fix looped on sentence 2 (`m3_s5_pytest.txt`, `m3_s5_diag_mt.txt`) |
  ```
- **DECISIONS.md** section 3: replace the "S5 in progress" line with
  `- **S5 done (2026-11-01):** \`translate.py\` + T1.3 (passed; \`command_outputs/m3_s5b_pytest.txt\`). opus-mt repetition loop found and fixed with \`no_repeat_ngram_size=3\` (D5, L10; \`scripts/diag_mt.py\`, \`command_outputs/m3_s5_diag_mt.txt\`).`
  and Next step with
  `- **Next step:** M3 S6 — \`output.py\` + T1.4 (see \`handovers/007-m3-s5-done-to-s6.md\`).`
- Proposed commit: `git add TEST.md DECISIONS.md` · `git commit -m "TEST: T1.3 passed + results row; DECISIONS: S5 done, next step S6"`

### Step 2 — S6 `output.py` + T1.4: questions for Zaven (approve or change before Claude writes)
- **O1. Interface:** a `Record` dataclass in `output.py` = `{segment_id, speaker, start, armenian, english, latency}` (`start` in seconds from session start, `latency` in seconds, D12). Pure `format_line(record) -> str` (tested by T1.4) plus `print_line(record)` that writes it to stdout with `flush=True` (so lines appear at once; latency is measured when printed, D12 — S7 measures it just before calling `print_line`).
- **O2. Offset:** `[HH:MM:SS]` from `start`, **truncated** (floor), not rounded: 83.9 s → `[00:01:23]` (T1.4: 83 s → `[00:01:23]`).
- **O3. Layout, exactly as DECISIONS section 8:**
  - line 1: `[HH:MM:SS] <speaker>:  <armenian>` (two spaces after the colon);
  - line 2: 11 spaces (width of `[HH:MM:SS] `), then `→ <english>   (<latency>s)` (three spaces before the bracket), latency with 1 decimal.
  - Spacing checked against section 8 (2026-11-01): 2 spaces after the colon, 11-space indent, 3 spaces before `(`.
- **O4. Latency warning:** text `(5.3s ⚠ >5s)` (previewed in handover 006; section 8 does not specify it). Warn when the **raw** latency is > 5.0 s (strictly). Edge case to confirm: 5.04 s would show `(5.0s ⚠ >5s)` — accept, or show 2 decimals when warning? T1.4: 5.1 s → warning, 4.9 s → none.
- **O5. Empty text:** `output` formats whatever it is given (empty Armenian / English included); whether empty segments are printed or skipped is decided in S7 (A4).
- **O6. Plain text only:** no colours, no extra dependency; `⚠` and `→` need a UTF-8 terminal (locale en_US.UTF-8, R15 font note).
- **O7. T1.4 tests (`tests/test_output.py`)** as TEST.md: fixed record → exact two-line string; 83 s → `[00:01:23]`; 5.1 s → warning; 4.9 s → no warning.

### Previewed for later steps (asked again at each step)
- **S7:** what to do with segments whose ASR text is empty (skip or print); `num_workers` = N reminder (D3); print order by speech end (D13, L5).
- **S8:** in file mode the app exits 0 by itself once the file has ended and all lines are printed (needed for T2); live mode exits only on `quit`. T6 part 2 (`quit`, unknown command) is written then.

## Open questions
- Client's real setup (DECISIONS.md section 7) — still to confirm after the walking skeleton.

## Watch out for
- **Claude's file writes (stale content):** in this chat a write landed with old content twice (DECISIONS.md and TEST.md: new mtime, old size). What worked: write from a **fresh copy at a new path** in Claude's workspace, then read the file back from the laptop and compare **byte for byte** (`cmp`), not only the size. Do this after every write.
- Claude's cloud workspace cannot reach PyPI, so it cannot run the models itself; all runs go through Zaven (working rule 8).
- **R1 latency:** Whisper small RTF 0.58 → 12 s segment ≈ 7 s ASR; MT is fast (≈ 0.1–0.3 s per sentence with the loop fixed). Addressed in M4 (T2, T4).
- TEST.md results log: the "—" placeholder row stays; rows are appended, never edited.
- M7 notes from handover 005 still apply (WER/CER text clean-up, verbatim references, FastConformer ONNX export); add: MT bake-off should include the FLEURS sentences from T1.3 and inputs with numbers / hyphens (L10).

## Rules reminder
- Claude proposes; Zaven decides and runs every command, including every git command.
- Command outputs go to `command_outputs/<name>.txt` and are not committed.
- Nothing goes into DECISIONS.md / TEST.md until Zaven approves it.
- Small steps; no silent fallbacks; three-strikes rule.

## Pending commit (this handover)
```
git add handovers/007-m3-s5-done-to-s6.md
git commit -m "handover 007: M3 S4-S5 done -> S6"
```
