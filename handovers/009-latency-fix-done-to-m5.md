# Handover 009 — latency fix done → M5 second device (then M6 diarizer) — 2026-11-01

**Start the new chat with:** `DECISIONS.md` + `TEST.md` + this file.

## Goal
This chat fixed the latency problem from handover 008. The 5 s rule now holds on `mic_01` in file mode. **Next work: M5 (second device, system monitor), then M6 (diarizer).** Zaven decided on 2026-11-01 to move on now and **postpone the M4 tests T3 (capture smoke) and T4 (load test)**. Zaven tracks the time budget.

## Current state
- **Latency fix done (D26).** Whisper small now runs with `beam_size=1`, `without_timestamps=True`, `temperature=0` and a token cap. If the cap stops the text, the Armenian line ends with ` ...` (L11). The VAD segment cap is **7 s** (was 12 s).
- **T2 passed** on `mic_01`, mic only (`command_outputs/d26_t2_mic01.txt`): 11 lines, median 4.1 s, max 4.8 s, no swap growth. Headroom is small: the worst lines are segments cut at the 7 s cap. 5 of 11 lines end with ` ...` (repeats; ASR quality on them is poor, R5).
- Default suite: **23 passed** (`command_outputs/d26_pytest.txt`). TEST.md: T1.1–T1.5, T2 and T6 `passed`; T1.6, T3, T4 and T5 `not run`.
- Git: last known HEAD `ad8b730` (D26 code + T1.1/T1.2 updates + L11). After that, Claude wrote DECISIONS.md section 3 / R1, TEST.md T2 status + 3 results rows, and this handover (see Pending commits).
- Code: `app.py`, `src/arm_en_asr/{audio_capture,asr,translate,output,pipeline}.py`. Tests: `tests/test_{cli,audio_capture,asr,translate,output,pipeline}.py`. Helper: `scripts/diag_asr.py` (has `--variants` and `--seg-cap`).

## Decisions made in this chat (all already in DECISIONS.md)
- D3 additions: `temperature=0`; then the D26 settings (beam 1, no timestamps, token cap, ` ...`).
- D8 addition: segment cap 7 s. D12 addition: the Armenian text may end with ` ...` (the line format is unchanged). D16: `diag_asr.py`.
- **D25** (FastConformer CTC brought forward): **superseded by D26** for time. FastConformer is in Future ideas (section 6) **and stays in the M7 bake-off (D4 unchanged)**.
- **D26** (option B) + additions: measurements, the token-cap rule and the ` ...` marker.
- L4 (cap 7 s), new **L11** (cut-off lines), R1 notes, section 3 status.
- Finding: CTranslate2 generates at most floor((prompt + `max_new_tokens`) / 2) new tokens. It is not faster-whisper (`command_outputs/fw_transcribe.py` passes the value unchanged); the rule fits every measured value. So `asr.py` passes 2 × the cap.

## Exact next step (proposal, Zaven to approve before anything is written)
**Propose an M5 plan as small steps (like M3's S1–S8) and agree it before writing code.** What exists and what has to be decided:
- **What blocks system audio today:** `app.py` lines 159–161 refuse `--system` / `--system-wav` ("not processed yet (milestone M5)"). `pipeline.py` lines 74–76 refuse system segments (P5: "never mislabel"). Both are lifted in M5.
- **Capture:** one thread per device, each with its own `SileroVad` + `Segmenter` and a shared id counter. This is already designed in `audio_capture.py` (D1, D10). The session clock starts at the first captured sample (D11 Q-decisions). To decide: does it start at the first sample of *either* device?
- **To decide: the label of system segments before M6.** M6 adds the diarizer. Options: do M5 + M6 as one step, or use a clear interim label (e.g. "Speaker ?") that is never presented as a real speaker (working rule 2, P5).
- **Load risk:** two devices mean more segments with N = 1 ASR worker, and T2 has only ≈ 0.2 s headroom. T4 (D2) is postponed, so the **T2 re-run with `--system-wav`** (TEST.md T2, M5) is the main check. Pair a mic clip with `eval/clips/sys_01.wav` (89 s, 2 speakers, D17).
- **File mode with two WAVs:** both start together and have different lengths; the session ends when both are done and every line is printed (D11, D21).
- **Print order across devices:** L5 (by speech end; cap-cut vs silence-ended segments can swap within 0.6 s).

**M6 (after M5):** D9's plan is a small speaker-embedding model (WeSpeaker / ECAPA, ~25–80 MB) plus online cosine clustering. It runs on system segments only, in parallel with ASR (D1). Open points for M6:
- the runtime: sherpa-onnx (a new pip dependency) or onnxruntime with an ONNX model. SpeechBrain needs torch, which D23 keeps out of the app env.
- the download path (D15) and RAM.
- the T1.6 details (solo mic clip → 100 % one label; `sys_01` → % correct reported).

## Pending (not written, waiting for Zaven)
- **`�` fix in `asr.py`.** The token cap can stop in the middle of an Armenian letter's bytes, which leaves `�` (U+FFFD) before ` ...` (seen in T2: «… եմ ե� ...»). Proposal: strip trailing `�` before adding the marker. One line, no new test.
- **T2 conditions:** whether a Meet/Zoom tab was open during the T2 run is not confirmed. The results row says so. Zaven decides whether a re-run with the tab open is needed.
- **M4 leftovers:** T3 (mic) and T4 (load test) postponed; T2 re-run in M5.

## Open questions
- Client's real setup (DECISIONS.md section 7): still to confirm.
- Time: how much of the remaining 20 h budget is left (Zaven tracks; M5 1 h, M6 2 h; cut order M9, then M8).

## Watch out for
- **Stale writes:** in this chat the file copy tool once wrote an *older* version of a file. It seemed to reuse an earlier upload from the same container path; the file got a new timestamp but the old content. Fix that worked: write each new version under a **fresh file name** in the container, commit it, then read the file back from the laptop and `cmp` it byte for byte. Never skip the read-back.
- The installed `faster_whisper/transcribe.py` is hardlinked by uv, so it cannot be read through the bridge. `command_outputs/fw_transcribe.py` is a copy (faster-whisper 1.2.1).
- Claude's cloud workspace has no models and no internet for pip; every model run goes through Zaven (working rule 8).
- `diag_asr.py` changes `audio_capture.CAP` for its own run only; the app uses `CAP_S = 7.0`.
- TEST.md results log: rows are appended, never edited.

## Rules reminder
- Claude proposes; Zaven decides and runs every command, including every git command.
- Command outputs go to `command_outputs/<name>.txt` and are not committed.
- Nothing goes into DECISIONS.md / TEST.md until Zaven approves it.
- Small steps; no silent fallbacks; three-strikes rule.

## Pending commits
```
git add DECISIONS.md TEST.md handovers/009-latency-fix-done-to-m5.md
git commit -m "DECISIONS: latency fix done, M5 next, R1 D26 result; TEST: T1.1/T1.2/T2 results, T2 passed; handover 009"
```
