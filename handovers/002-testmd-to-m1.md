# Handover 002 — TEST.md → M1 (environment) — 2026-10-29

**Start the new chat with:** `DECISIONS.md` + `TEST.md` + this file.

## Goal
Start milestone **M1 — Environment** (1.5 h budget). M1 covers:
- the uv environment
- a pinned `requirements.txt`
- `download_models.py`
- a smoke run of each model on one Armenian clip
- a RAM check

## Current state
- **M0 (Planning) is done.** DECISIONS.md (rules, decisions D1–D22, milestones, risks, limitations) and TEST.md were agreed and committed by Zaven.
- Repo: `PLAN.md`, `DECISIONS.md`, `TEST.md`, `command_outputs/laptop_specs.txt`, `handovers/001…`, `handovers/002…`, `chats/`. **No code yet.**
- TEST.md: tests T1.1–T1.6, T2, T3, T4, T5 and T6 are defined, all with status "not run". T5 details are to be agreed at M9.

## Decisions made in the previous chat (already in DECISIONS.md)
- **D2 addition:** the load-test grid is N = 1, 2, 3 × K = 1, 2, 4, 6.
  - A combination passes if max latency ≤ 5 s and swap grows by ≤ 100 MB.
  - Tie-breaker: (1) highest segments per minute, (2) highest N, (3) lowest max latency.
- **D20 addition:**
  - T6 CLI fail-loudly checks: unknown device, missing model, unknown stdin command, `quit`.
  - Sanity limits: ≥ 50 % Armenian script (T1.2), RMS > −50 dBFS (T3), ≤ 100 MB swap growth (T4), 100 % same label on a solo clip (T1.6).
- **D21:** file mode (`--mic-wav` / `--system-wav`) feeds the WAV at real-time speed.
- **D22:**
  - Small fixtures are committed in `tests/fixtures/` (FLEURS hy_am snippet, CC-BY 4.0 with attribution; generated silence; ≥ 12 s continuous speech).
  - A missing model or fixture makes a test fail, never skip.
  - pytest markers `hardware` and `slow` are excluded from a plain run.

## Relevant M1 facts (from DECISIONS.md)
- **Laptop RAM:** ~2.4 GiB free, which is the tightest constraint.
- **Python:** 3.10.12, managed with uv. Setup: `uv venv --python 3.10` → `uv pip install -r requirements.txt`. All versions pinned (D14).
- **Skeleton models, all CPU (D7):**
  - faster-whisper small int8, language `hy` (D3)
  - Helsinki-NLP/opus-mt-hy-en via CTranslate2 int8 (D5)
  - Silero VAD ONNX (D8)
- **Downloads:** models are downloaded once by `download_models.py`. The app sets `HF_HUB_OFFLINE=1` and errors if a model is missing (D15).
- **Repo layout:** see D16 (`src/arm_en_asr/…`, `tests/`, `tests/fixtures/`, `eval/…`).
- **M1 also checks** that Armenian script renders in the terminal (R15).

## Rules reminder
- Claude proposes; Zaven decides and runs every command, including every git command.
- Command outputs go to `command_outputs/<name>.txt`.
- Small steps; no silent fallbacks; three-strikes rule.

## Exact next step
Claude proposes a **pinned `requirements.txt`** for the skeleton models plus pytest, with the reason for each package, and the exact uv commands to create `.venv` and install. Zaven approves; then Claude writes the file and proposes the commit.

After that: `download_models.py` → model smoke runs + RAM check (saved to `command_outputs/`).

## Open questions
- None blocking. The client's real setup (DECISIONS.md section 7) is to be confirmed after the walking skeleton.
