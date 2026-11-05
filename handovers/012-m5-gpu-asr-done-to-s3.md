# Handover 012 — Latency fixed with Whisper on the MX550 GPU (D29, D30) → M5 S3 — 2026-11-05

**Start the new chat with:** `DECISIONS.md` + `TEST.md` + this file.

## Goal
M5 (second device) then M6 (diarizer), plan S1–S7 in **D27**. The turn-taking test had to pass (every line ≤ 5 s) before S3. It now passes, with ASR on the GPU. Time is not the constraint for M5/M6 (Zaven, 2026-11-04).

## Current state
- Git: HEAD `342ccf5` ("D30 L5: remove .venv-gpu measuring env (one env again)") on `main`. **Not committed yet:** `README.md` (L6 edits 1–8), `TEST.md` (two rows: T1.2 32-test run + app-path turn test), this handover. Commands under "Pending commits".
- One environment again: `.venv` (+ `.venv-convert` for the one-time model conversion). `.venv-gpu`, `requirements-gpu.in/.txt` removed.
- Default suite: **32 passed** in 9.77 s (`command_outputs/m5_g4_pytest.txt`), in `.venv`, no `LD_LIBRARY_PATH`.
- **Done in this chat:**
  - Handover 011 pending items: two TEST rows (T1.2 31 passed; CPU turn re-run not passed, max 5.9 s; Zoom tab open). Zaven chose **Option 2: Whisper on the GPU** → **D29** (steps G0–G4; no time-box; three-strikes rule).
  - **G0** GPU check: ctranslate2 4.8.4 sees 1 CUDA device; `int8_float16` / `float16` supported; VRAM 5 / 2048 MiB in use.
  - **G1** measuring env `.venv-gpu`: cuBLAS 12.9.3.13, cuDNN 9.28.0.42, nvrtc 12.9.86. One strike: the faster-whisper docs' `python -c` way of finding the lib folders fails (the NVIDIA wheels have no `__init__.py`, `__file__` is None) → paths given directly.
  - **G2** `diag_asr.py` J1–J6 (`--device`, `--compute-type`, memory + VRAM, encoder timing on cuda): GPU `int8_float16` total ASR 22.8 s / max 1.0 s per segment vs CPU `int8` 113.2 s / 4.7 s; same loops (3/31), CER within ~2 points; VRAM 420 MB. `float16` rejected (slower, more loops, worse CER).
  - **G3** `diag_two_devices.py` K8–K12 (`--asr-device`, `--asr-compute-type`, VRAM): turn test **passed**, max 1.5 s, 0/28 > 5 s.
  - **D30 (G4a–G4f):** app ASR always on cuda `int8_float16`, no CLI option, no GPU → `AsrError`, never a CPU fallback; NVIDIA packages in `requirements.in`; CUDA libraries loaded in-process by `asr.load_cuda_libraries()` (ctypes, RTLD_GLOBAL; preload trick checked in `m5_g4_preload.txt`); MT and VAD stay on the CPU; T1.2 gets a GPU test; D7 addition, R18 resolved, R1 updated.
  - **L1–L6** done: `requirements.in/.txt` (L1), `asr.py` + `test_asr.py` + TEST.md T1.2 (L2, L3), diag scripts run in `.venv` and default to the app setting / load the libraries the app's way (L4), cleanup (L5), README GPU edits (L6).
  - **App-path turn test** (`command_outputs/m5_g4_turns_app.txt`, `diag_two_devices.py` with no device flags, Zoom tab open): 28 lines, median 1.3 s, p95 1.7 s, **max 1.8 s, 0 > 5 s**, 1/28 cut, peak RSS 878 MB, swap flat, VRAM 420 MB. Load average 1.69 at start.
- `app.py` still refuses `--system` (E4) until S6.

## Pending (proposed, NOT answered by Zaven yet)
1. **Section 3 status update** in DECISIONS.md (write only after approval):
   - add: "- **Latency fix on GPU done (2026-11-05):** D29 / D30: ASR on the MX550 (cuda `int8_float16`); turn test max 1.8 s on the app path (`command_outputs/m5_g4_turns_app.txt`); 32 tests pass."
   - "Next step" line → "- **Next step:** M5 S3 (`app.py` + `audio_capture.py`: two devices, E1–E3; `--system` still refused). T3 / T4 later (Zaven, 2026-11-01)."

## Exact next step
Get Zaven's answer to Pending 1. Then propose **S3** details (D27): in `audio_capture.py` and `app.py`, one SileroVad + Segmenter + capture thread per device (`capture-mic`, `capture-system`), shared id counter; **E1** shared session start time + per-Segmenter offset (first chunk arrival − 32 ms − start); **E2** session ends when every input has ended and every line is printed; **E3** one device lost → drain, exit 1. `--system` / `--system-wav` still refused (E4) until S6. List the exact code changes and the tests (T1.1 / T6 additions) for approval before writing anything.

## Notes for later (not decisions)
- **Peak RSS 878 MB** on the app path vs 729 MB in G3 (`.venv-gpu` with `LD_LIBRARY_PATH`). Likely cause: `load_cuda_libraries()` loads all 16 NVIDIA libraries, incl. ones CTranslate2 may never use (`libnvblas`, the `.alt` nvrtc libs, all cuDNN engine libs). Same as the CPU app (881 MB), swap flat, so only noted. If RAM gets tight (M6 embedding model, T4), measure a narrower preload list.
- **D28 (N = 1) and L12 (overlap case) were measured on the CPU.** With ASR ~5× faster, the `mic_01` + `sys_01` overlap case might now keep up; a re-measure (`diag_two_devices.py` with default clips) is cheap if Zaven wants it. Not planned.
- `diag_asr.py` default is still CPU `int8` (a CPU baseline, docstring says so); `diag_two_devices.py` defaults to the app setting.

## Still open from earlier
- L11 note (handover 010, proposed 2026-11-01, not answered): token cap can stop mid-letter → `�` before ` ...`.
- Client's real setup (DECISIONS section 7).
- T3 / T4 postponed.
- README: "Status at a glance" (dated 2026-11-01) and "Default test suite: 23 passed" are out of date; plus the README sections listed in handover 010 → README pass at the end of M5 / in S7.

## Watch out for
- **Stale writes:** always write each new version under a **fresh folder name**, copy, re-stage from the laptop and `cmp` byte for byte (done for every write in this chat; no stale write happened).
- Claude has no shell on the laptop; Zaven runs every command and every git command.
- Tests and the app now **need the GPU** (D30); without it they fail loudly (D22), never skip.
- No silent fallbacks (GPU ↔ CPU included); system lines never mislabelled (E4).
- TEST.md results log: append only.

## Rules reminder
- Claude proposes; Zaven decides and runs every command.
- Command outputs go to `command_outputs/<name>.txt`, never committed.
- Nothing into DECISIONS.md / TEST.md until Zaven approves it.

## Pending commits
```
git add README.md TEST.md
git commit -m "D30 L6: README GPU requirement + results; TEST rows: T1.2 (32 passed) + app-path turn test (max 1.8 s)"
git add handovers/012-m5-gpu-asr-done-to-s3.md
git commit -m "handover 012: latency fixed on GPU (D29, D30) -> M5 S3"
```
