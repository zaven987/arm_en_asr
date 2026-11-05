# Handover 015 — M5 + M6 done (S6, S7a) → M7 bake-off, first a beam_size sweep — 2026-11-05

**Start the new chat with:** `DECISIONS.md` + `TEST.md` + this file.

## Goal
M5 (second device) and M6 (diarizer) are **done**. Zaven's direction (2026-11-05, end of this chat): **start the M7 bake-off now. The first step is a `beam_size` sweep to see which beam sizes keep the model approximately under 5 s. The README pass (D27 S7c) is postponed.** These directions are **not yet in DECISIONS.md** (see "Pending").

## Current state
- **S6 done** (D27 addition "S6, H1–H7"): `app.py` builds `Diarizer(MODELS_DIR / SPEAKER_MODEL)` only with a system input and passes it to `Pipeline`; `--system` / `--system-wav` are accepted; `check_models()` always checks the speaker-embedding model; no diarizer warm-up. `tests/test_cli.py`: refusal test replaced by `test_system_wav_run_accepted`, `test_speaker_model_path_matches_diarizer` added. **61 tests pass**, T6 8/8 (`command_outputs/m6_s6_pytest.txt`).
  - `sys_01` through the app (not T2, `m6_s6_sys01.txt`): labels 16/16 as T1.6; max 5.2 s, 2/16 lines > 5 s (a token-cap line and one waiting behind it); peak RSS 1070 MB. Zaven chose option A: no diagnostic, T2 is the check.
- **S7a done** (D27 addition "S7a"): **T2 passed** on the turn files with the real diarizer, Zoom tab open, plugged in: 28 lines, median 1.3 s, p95 1.6 s, max 1.6 s, 0 > 5 s, 1/28 cut, peak RSS 1079 MB, **swap full** (2034 → 2047 of 2047 MB; R17) (`command_outputs/m6_s7_t2_turns.txt`).
- Records written and checked byte for byte on the laptop: DECISIONS section 3 (current milestone M10, M6 S7a done, next step S7c), milestone table M5 / M6 ☑ done, R1 / R11 / R17 updated, TEST.md T2 status + results rows. **L11 `�` note: Zaven said no** (not added).
- TEST.md statuses: T1.1–T1.6, T2, T6 passed; T3, T4, T5 not run.
- ASR today (D3, D26, D29, D30): Whisper small, cuda `int8_float16`, `beam_size=1`, `temperature=0`, `without_timestamps=True`, `repetition_penalty=1.1`, token cap with ` ...`, VAD cap 7 s. MT opus-mt int8 CPU (`beam_size=2`); diarizer CPU 1 thread.

## Pending (Zaven's direction, NOT yet in DECISIONS.md — propose the text first)
- **Section 3:** current milestone becomes M7 (bake-off); "Next step" = beam_size sweep (replaces "M6 S7c: README sections"); S7c README postponed (Zaven, 2026-11-05). M10 (README, final test run) still to do afterwards.

## Exact next step
Propose the **beam_size sweep** in detail for Zaven's approval before anything is written or run:
- **Read first:** `scripts/diag_asr.py` (it already has `--device` / `--compute-type`, variants g / b / c / d1, token cap, 7 s cap, CER on `mic_01`–`03`); check whether it can take a beam size, or what small option to add. `command_outputs/m5_g2_diag_asr_gpu.txt` is the GPU baseline at beam 1 (`int8_float16`: max 1.0 s ASR per segment, total 22.8 s, loops 3/31, CER 45.0 / 26.7 / 31.9 %).
- **Questions to settle with Zaven:**
  - Which model(s): Whisper small only (current app model), or also bake-off candidates from D4 (Whisper large-v3-turbo on the MX550, ~0.8 GB VRAM; VRAM 2 GB total, Whisper small uses 420 MB; BuzzASR quantized; Omnilingual). FastConformer is in Future ideas (D25).
  - Which beam sizes (e.g. 1, 2, 3, 5).
  - Device / compute type: cuda `int8_float16` (app setting, D30).
  - What "approximately under 5 s" is measured on: ASR time per segment (`diag_asr.py`, fast, no MT / queue) vs end-to-end latency (turn test via `diag_two_devices.py` or app T2-style run). ASR time alone must leave room for VAD end silence (0.6 s), MT and print.
  - Keep `repetition_penalty=1.1`, token cap and 7 s cap fixed? (Beam search may change the loop count; the token cap rule D26 was fitted for greedy.)
  - Record per beam: ASR time median / max per segment, CER per clip, loops (cap hits), VRAM, RSS.
  - Demo conditions (Zoom tab open, plugged in) for timing runs.
  - Output names: `command_outputs/m7_beam_….txt`.
- Then: Zaven chooses; a new D# records it before `asr.py` changes.

## Notes for later (not decisions)
- On the CPU, beam 5 cost ≈ 37 ms per token vs ≈ 17 ms greedy (D25); on the GPU the encoder is 0.35 s and ASR is ≈ 5× faster (D29 G2), so beam > 1 may now fit.
- The `sys_01` S6 run had 2 lines at 5.2 s on token-cap segments; where that time went is unknown (S6 H7). Beam search could make cap-hit segments slower — watch the max.
- Swap was full during T2 (R17); a bigger ASR model adds RAM / VRAM.
- `diag_embed.py` / `tune_diarizer.py` use `Segmenter` without `session_start` (fine for them).
- sherpa-onnx stays on 1.13.8 (no Python 3.10 Linux wheel seen for 2.x).

## Still open from earlier
- **S7c README** (postponed): sections from handover 010 (Status at a glance, Running incl. two devices + live command, Tests 61 + `eval`, Architecture with diarizer, Measured results, Known limitations L12–L14, What we'd improve) + WeSpeaker ResNet34 / VoxCeleb CC-BY 4.0 licence line.
- M10: final test run and TEST.md statuses.
- Client's real setup (DECISIONS section 7).
- T3 / T4 postponed.

## Live run command (given to Zaven this chat)
```
python app.py --list-devices
python app.py --mic "alsa_input.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__hw_sofhdadsp_6__source" --system "$(pactl get-default-sink).monitor"
```
Headphones (L1); `quit` + Enter to stop; add ` 2>&1 | tee command_outputs/<name>.txt` to keep a copy.

## Watch out for
- **Stale writes:** after `device_commit_files`, re-stage and `cmp`; write each new version from a **new folder**. No stale write happened in this chat with that rule.
- Claude has no shell on the laptop; Zaven runs every command and every git command.
- Tests and the app need the GPU (D30) and the speaker-embedding model; missing → fail loudly, never skip.
- No silent fallbacks; system lines never mislabelled (E4).
- TEST.md results log: append only.
- Don't claim a commit happened unless Zaven confirmed it (the T2 row's commit column says "S6 code + S6 records" for that reason).

## Rules reminder
- Claude proposes; Zaven decides and runs every command.
- Command outputs go to `command_outputs/<name>.txt`, never committed.
- Nothing into DECISIONS.md / TEST.md until Zaven approves it.

## Pending commits (run any not yet done, in this order)
```
git add app.py tests/test_cli.py
git commit -m "M6 S6: app connects the real diarizer; --system/--system-wav accepted; speaker model checked always"
git add DECISIONS.md TEST.md
git commit -m "M6 S6 + S7a records: D27 S6 H1-H7, S7a T2 passed (max 1.6 s); M5 + M6 done"
git add handovers/015-m6-done-to-m7-beam-sweep.md
git commit -m "handover 015: M5 + M6 done -> M7 bake-off, beam_size sweep first"
```
(If the S6 records were already committed separately, the second commit just carries the S7a records.)
