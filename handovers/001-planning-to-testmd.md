# Handover 001 — Planning → TEST.md — 2026-10-28

**Start the new chat with:** `DECISIONS.md` + this file.

## Goal
Finish milestone **M0 (Planning)** by agreeing on and writing **TEST.md**. Then start M1.

## Current state
- `DECISIONS.md` is written and committed by Zaven. It holds the rules, laptop facts, scope, architecture, decisions D1–D20 (all agreed), milestones M0–M10 (20 h), risks R1–R19, and known limitations L1–L9.
- Repo so far: `PLAN.md`, `DECISIONS.md`, `command_outputs/laptop_specs.txt`, `handovers/001-planning-to-testmd.md`. No code yet.
- Current milestone: **M0, in progress** (about 1.5 h budgeted).

## Key decisions (details in DECISIONS.md)
- One process with threads and queues. A shared `Segment` unit, joined by segment id in a new `pipeline` module (D1). Load test with N = 1–3 ASR workers while a Zoom/Meet tab is open (D2).
- Skeleton models run on CPU (D7):
  - ASR: faster-whisper small, int8, language `hy` (D3).
  - MT: opus-mt-hy-en, int8 (D5).
  - VAD: Silero, 0.6 s silence, 12 s segment cap (D8).
- Bake-off in M7 (D4, D5):
  - ASR: Whisper large-v3-turbo on the GPU, Omnilingual CTC 300M, quantized BuzzASR (30-min time box).
  - MT: NLLB-600M.
- Capture uses one `parec` per device (D10). CLI: `--list-devices`, `--mic`, `--system`, `--mic-wav`/`--system-wav` for file mode, and `quit` to stop (D11).
- Each line shows speaker, start offset, Armenian, English and latency, with a warning above 5 s. Lines print in order of when speech ended (D12, D13).
- Setup: uv, Python 3.10, pinned `requirements.txt` (D14). Offline at runtime, `download_models.py` for the one-time download (D15).
- Eval data: one device role per clip, plus one CSV per clip (`start,end,device,speaker,armenian,english`), audio gitignored (D17, D18). FLEURS hy_am only (D19).
- Metrics: WER/CER, chrF/BLEU plus manual rating, latency median/p95/max, diarization % correct. The only hard threshold is latency ≤ 5 s. Tests use pytest (D20).

## Rules reminder
- Claude proposes; Zaven decides, runs every command and every git command.
- Every part of TEST.md must be agreed before it is written.
- No silent fallbacks. Small steps. Three-strikes rule. Command outputs go to `command_outputs/`.

## Exact next step
Claude proposes the **structure and first entries of TEST.md** for Zaven to approve:
1. Unit tests per module on fixture audio.
2. End-to-end latency test in file mode (≤ 5 s).
3. Capture smoke test: open both devices for 3 s and check the audio is not silent.
4. Load test (D2).
5. Virtual-sink capture test (M9, later).

Each entry gets an ID, its purpose, how to run it, the pass criterion, and status "not run", plus a results log section. After Zaven approves, Claude writes TEST.md and proposes a commit. M0 is then marked done and M1 starts.

## Open questions
- None blocking. The client's real setup (DECISIONS.md section 7) is to be confirmed after the walking skeleton.
