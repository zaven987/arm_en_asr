# Handover 013 — M5 S3 done (two-device capture, F1–F8) → M6 S4 — 2026-11-05

**Start the new chat with:** `DECISIONS.md` + `TEST.md` + this file.

## Goal
M5 (second device) then M6 (diarizer), plan S1–S7 in **D27**. S1, S2, the GPU latency fix (D29, D30) and now **S3** are done. Next: **S4**, the speaker-embedding model choice (first M6 step). Time is not the constraint for M5 / M6 (Zaven, 2026-11-04).

## Current state
- Git: S3 code committed as `fa4588a` on `main` (app.py, audio_capture.py, both test files, incl. F8). **Not committed yet** (as far as Claude knows): `DECISIONS.md` (F7 / F8 bullets, section 3 "S3 done" + next step), `TEST.md` (T1.1 / T6 wording + 3 result rows), this handover. Commands under "Pending commits".
- Default suite: **41 passed** in 10.01 s (`command_outputs/m5_s3b_pytest.txt`), `.venv`, ASR on the GPU (D30).
- `app.py` still refuses `--system` / `--system-wav` (E4, F5) until S6 connects the real diarizer.
- **Done in this chat:**
  - Handover 012 Pending 1 (section 3 GPU line + next step) approved and written.
  - Three conflicts resolved and written: D27 S7 now notes that T2 uses the turn files; TEST.md "Last updated" bumped; the double "G" prefix noted, S3 uses **F**.
  - **S3 = D27 addition F1–F8:**
    - F1 `Segmenter(…, session_start=None)`: offset = first chunk arrival − 32 ms − `session_start`; none → offset 0 (T1.1 file tests, diag scripts).
    - F2 new `Capture` class (`audio_capture.py`): one thread per input `capture-<device>`; wake when every input ended (E2) or at once on an error (E3); `stop()` stops and joins all; same device twice → `CaptureError`.
    - F3 `app.py` builds inputs mic, system; one `SileroVad` per input; shared ids; `session_start` just before capture starts; shutdown = `capture.stop()` then `pipeline.close()`.
    - F4 one ready line (`listening on mic: …, system: …` / `playing mic: …`). F5 refusal message "refused until the diarizer is connected (D27 E4, step S6)". F6 docstrings.
    - F7 (Zaven): a lost device's own open segment is dropped, not flushed; the other device's open segment is drained.
    - F8 `ParecSource` lock between `stop()` and starting `parec`. Found because T6 `test_unknown_stdin_command_keeps_running` hung in the first run (`m5_s3_pytest.txt`, 39 passed / 1 failed): `quit` came before `parec` started. After F8: 5/5 on its own (`m5_s3_f8_stdin_x5.txt`), 41 passed in the full suite.
  - Tests added: T1.1 +7 (stub VAD / stub sources: offset, no offset, shared ids, E2, E3, thread names / duplicate, F8); T6 +2 (`--system-wav` still refused; file mode mic only exits 0).

## Pending (proposed, NOT answered by Zaven yet)
- None.

## Exact next step
Propose **S4** details (D27 "M6 model") for Zaven's approval before anything is installed or written:
- First candidate `sherpa-onnx` + a small WeSpeaker / 3D-Speaker speaker-embedding model (~25–40 MB). Check first (web) that a wheel exists for Python 3.10 / x86-64 Linux and that it does not pull in torch; pick the exact version and model, with licence (for the README).
- Package via `requirements.in` → `uv pip compile` (D14); model via `scripts/download_models.py` at a pinned URL + SHA-256 (D15, D24).
- **30-minute time-box on installation**; if `sherpa-onnx` fails to install, stop and choose the fallback `kaldi-native-fbank` + our onnxruntime (a decision, never a runtime fallback).
- Device: propose CPU for the embedding model (ASR keeps the GPU) unless measured otherwise; record RSS, because peak RSS is already ~880 MB (see notes).
- Smoke script (new `scripts/…`, name to be proposed): embed every segment of `mic_01`–`03` and `sys_01` (real Segmenter, 7 s cap) and print time per embedding, RSS, and cosine similarity for same-speaker vs different-speaker pairs; the short-segment length (~1 s, R11) is set in S4 from these numbers. Threshold tuning on `mic_01`–`03` only, never `sys_01` (R13).
- List exact files, commands and the output file name (`command_outputs/m6_s4_….txt`) for approval.

## Notes for later (not decisions)
- **Peak RSS 878 MB** on the app path (handover 012): `load_cuda_libraries()` loads all 16 NVIDIA libraries; if RAM gets tight with the embedding model, measure a narrower preload list.
- D28 (N = 1) and L12 (overlap case) were measured on the CPU; a GPU re-measure of `mic_01` + `sys_01` is cheap if Zaven wants it. Not planned.
- `diag_asr.py` default is still CPU `int8` (baseline); `diag_two_devices.py` defaults to the app setting and uses `Segmenter` without `session_start` (F1 offset 0, fine for its latency numbers).
- When S6 removes the `--system` refusal, T6's `test_system_wav_still_refused` is replaced (D27 S6: a short `--system-wav` run is accepted and exits 0).

## Still open from earlier
- L11 note (handover 010, not answered): token cap can stop mid-letter → `�` before ` ...`.
- Client's real setup (DECISIONS section 7).
- T3 / T4 postponed.
- README: "Status at a glance" and "Default test suite: 23 passed" out of date; README pass in S7.

## Watch out for
- **Stale writes:** write each new version under a **fresh folder name**, copy, re-stage from the laptop and `cmp` byte for byte (done for every write in this chat; no stale write).
- Claude has no shell on the laptop; Zaven runs every command and every git command.
- Tests and the app **need the GPU** (D30); without it they fail loudly, never skip.
- No silent fallbacks; system lines never mislabelled (E4).
- Live-app tests: anything that starts `parec` can race with an early `quit` (F8 fixed `ParecSource`); keep that in mind for new live tests.
- TEST.md results log: append only.

## Rules reminder
- Claude proposes; Zaven decides and runs every command.
- Command outputs go to `command_outputs/<name>.txt`, never committed.
- Nothing into DECISIONS.md / TEST.md until Zaven approves it.

## Pending commits
```
git add DECISIONS.md TEST.md
git commit -m "M5 S3 records: D27 F7/F8, status S3 done -> next M6 S4; TEST T1.1/T6 S3 checks + result rows (41 passed)"
git add handovers/013-m5-s3-done-to-m6-s4.md
git commit -m "handover 013: M5 S3 done (two-device capture, F1-F8) -> M6 S4"
```
(If the F7 / F8 DECISIONS commit was already made, the first commit just carries the section 3 update.)
