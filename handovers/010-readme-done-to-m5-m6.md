# Handover 010 — README done → M5 second device + M6 diarizer — 2026-11-04

**Start the new chat with:** `DECISIONS.md` + `TEST.md` + this file.

## Goal
Connect the second device (system-audio monitor, **M5**) and the diarizer ("Speaker N" for system audio, **M6**). Zaven decided this on 2026-11-04. Budget in DECISIONS section 10: M5 1 h, M6 2 h; Zaven tracks the time.

## Current state
- **README.md written and committed** (`496adf4`, M10 deliverable). It describes the app as it is today: mic only, `--system` refused, no diarizer. **After M5/M6 the README must be updated** (sections Status at a glance, Running, Tests, Architecture, Measured results, Known limitations, What we'd improve).
- Git: HEAD `c50aeb6` ("Added chats") on branch `main`; everything from handover 009 is committed (`aa32fda`, `b9cec1b`, `496adf4`). Checked from `.git/logs/HEAD` on 2026-11-04.
- DECISIONS.md and TEST.md unchanged since 2026-11-01. Default suite 23 passed; T1.1–T1.5, T2 (mic only), T6 `passed`; T1.6, T3, T4, T5 `not run`.
- M10 is **not finished**: the final test run and TEST.md statuses are still to do (after M5/M6).

## What already exists for M5 (read the code before proposing)
- `audio_capture.py` was built for two devices: one `SileroVad` per device (it keeps state), one `Segmenter(device, vad, ids)` per device, and a **shared id counter** (`new_id_counter()`) so segment ids are unique across devices. `Segment.device` is `"mic" | "system"`.
- `app.py` checks `--system` / `--system-wav` (device name / file exists), then refuses them (lines 159–161, D11 addition 2026-10-31). `run_session()` builds **one** source, one segmenter and one capture thread (`capture-mic`); shutdown stops that one source.
- `pipeline.py`: `submit()` refuses system segments (P5, ~line 74); the output thread labels every line `MIC_SPEAKER = "Me"`.
- D11: either input may be left out (`--mic` and/or `--system`; `--mic-wav` and/or `--system-wav`).
- D13 / L5: print order by when each segment's end was detected; with two devices, lines can print with timestamps out of order.

## Open decisions for M5 (Claude proposes, Zaven decides — none agreed yet)
1. **Session clock with two devices.** Today `start` / `end` are counted by samples from each source's own first sample (D12). Two `parec` processes do not start at the same instant, so the two devices' offsets could drift apart by the start gap. Options: one shared start time for both, or accept the gap and record it.
2. **File mode with two WAVs of different length** (`mic_01` 61 s, `sys_01` 89 s): the app ends when **both** files have ended? (D11 Q-rules say file mode ends when "the file" has ended.)
3. **Lost device:** one device lost → whole session ends with exit 1, as today (D11)? Proposed: yes.
4. **Label for system lines if M5 lands before M6:** a placeholder (e.g. "System") or keep refusing until the diarizer exists. Proposed: build M5 and M6 in one go, or use a stub diarizer, so no line is ever mislabelled (working rule 2).
5. **Latency with two devices — biggest risk (R1).** With N = 1 ASR worker, a mic segment and a system segment that end together are processed one after the other, and one ASR call already takes up to 4.7 s. T2 had only 4.8 s max with one device, so two devices will very likely break 5 s. Options: N = 2 workers (`Asr(num_workers=2)`; D3 says `num_workers` must equal N; RAM and CPU impact unmeasured, T4 postponed), or accept and record. Needs a measurement before choosing.

## Open decisions for M6 (D9)
- **Model:** D9 plan = small speaker-embedding model (WeSpeaker / ECAPA, ~25–80 MB) via sherpa-onnx or SpeechBrain + online clustering (nearest known speaker by cosine similarity, new speaker under a threshold). SpeechBrain needs PyTorch, which must not enter `.venv` (D23 spirit), so an ONNX model run with onnxruntime or sherpa-onnx is the likely path. Any new package goes into `requirements.in` → `uv pip compile` (D14); the model goes into `scripts/download_models.py` at a pinned revision with a checksum (D15, D24 pattern). Licence noted for the README.
- **Where it runs:** in parallel with ASR, on system segments only (D1, D9); the pipeline joins the label by segment id. Mic stays "Me" (L6).
- **Threshold:** tuned on what? Only `sys_01` exists (89 s, 2 speakers; D17). Tuning and testing on the same clip overfits (R13); say so in TEST.md / README.
- **Short segments:** `sys_01` has turns of 0.5–0.9 s (e.g. 55.90–56.60, 56.70–57.20); embeddings on such short audio are unstable (R11). What to do with segments too short to embed (keep the last speaker? new label?) must be decided.
- **T1.6 scoring:** VAD segments do not line up with the reference turns in `eval/meta/sys_01.csv`, so a rule is needed to give each segment its reference speaker (e.g. the speaker with most overlap). Speaker numbers are arbitrary, so % correct needs a mapping (best match of Speaker N to the reference names).
- RAM: ~2.4 GB free at the start of the project (section 2); the embedding model must fit next to Whisper, opus-mt and a browser call (R17).

## Tests touched by M5 / M6 (TEST.md, nothing changed yet)
- **T1.5** (pipeline): system segments are now accepted; the "system refused" test changes; a diarizer stub joins the label.
- **T6** (CLI): the "unknown `--system` device" test stays; nothing may still refuse `--system`.
- **T1.6** (diarizer, M6): solo mic clip → 100 % one label; `sys_01` → % correct reported, no threshold.
- **T2 re-run (M5):** `python app.py --mic-wav eval/clips/mic_01.wav --system-wav eval/clips/sys_01.wav`, every line ≤ 5 s, demo conditions.
- **T3** (capture smoke, both devices) is still postponed unless Zaven decides otherwise.

## Exact next step (proposal, Zaven to approve before anything is written)
**Claude proposes an M5 + M6 plan in small steps (like M3 S1–S8), with an answer proposal for each open decision above; Zaven agrees the plan before any code changes.** A likely first step is measuring decision 5 (two devices with N = 1 vs N = 2) because the answer can change the rest of the plan.

**Files to read before proposing:** `app.py`, `src/arm_en_asr/audio_capture.py`, `src/arm_en_asr/pipeline.py`, `src/arm_en_asr/output.py`, `tests/test_pipeline.py`, `tests/test_cli.py`, `eval/meta/sys_01.csv`, `README.md`.

## Pending (not written, waiting for Zaven)
- **DECISIONS.md section 3** still says "Next step: M5 … (see `handovers/009-latency-fix-done-to-m5.md`)"; that file no longer exists. Proposed replacement:
  - Current milestone: `- **Current milestone:** M5 — second device, then M6 diarizer (Zaven, 2026-11-04). M10: README done (2026-11-01); final test run and TEST.md statuses after M6.`
  - Next step: `- **Next step:** M5 + M6 plan (see `handovers/010-readme-done-to-m5-m6.md`).`
  - Add a status line: `- **README done (2026-11-01):** `README.md` written and committed (`496adf4`).`
- **L11 note (proposed 2026-11-01, not answered):** append to L11: *The cap counts tokens, not letters, so it can stop in the middle of an Armenian letter; the line then shows `�` just before ` ...` (seen in T2: «… եմ ե� ...»). Not fixed.* The README already describes this.
- **T2 conditions:** whether a Meet/Zoom tab was open during the 2026-11-01 T2 run is still not confirmed; the M5 re-run should state it.

## Open questions
- Client's real setup (DECISIONS section 7): still to confirm.
- Time left in the 20 h budget: Zaven tracks (cut order M9, then M8).

## Watch out for
- **Stale writes (happened again on 2026-11-01 with README.md):** the file copy tool can write an older version when the same container path is reused. Fix: write each new version under a **fresh file name/folder** in the container, copy it, read it back from the laptop and `cmp` byte for byte. Never skip the read-back.
- Claude has no shell on the laptop; staging and reading files works, running does not. Every model run, test and git command goes through Zaven (working rule 8).
- No silent fallbacks: a system line must never be labelled wrongly or dropped without a sign (working rule 2).
- TEST.md results log: rows are appended, never edited.

## Rules reminder
- Claude proposes; Zaven decides and runs every command, including every git command.
- Command outputs go to `command_outputs/<name>.txt` and are not committed.
- Nothing goes into DECISIONS.md / TEST.md until Zaven approves it.
- Small steps; no silent fallbacks; three-strikes rule.

## Pending commits
```
git add handovers/010-readme-done-to-m5-m6.md
git commit -m "handover 010: README done -> M5 second device + M6 diarizer"
```
