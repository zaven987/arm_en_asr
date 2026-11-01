# Handover 009 — latency fix done → README.md (M10) — 2026-11-01

**Start the new chat with:** `DECISIONS.md` + `TEST.md` + this file.

## Goal
This chat fixed the latency problem from handover 008. The 5 s rule now holds on `mic_01` in file mode. **Next work: write `README.md`** (M10 deliverable, DECISIONS section 4). Zaven decided this on 2026-11-01. M5 (second device), M6 (diarizer) and the M4 tests T3 / T4 are **postponed**, not cut, unless Zaven decides otherwise. Zaven tracks the time budget.

## Current state
- **Latency fix done (D26).** Whisper small now runs with `beam_size=1`, `without_timestamps=True`, `temperature=0` and a token cap. If the cap stops the text, the Armenian line ends with ` ...` (L11). The VAD segment cap is **7 s** (was 12 s).
- **T2 passed** on `mic_01`, mic only (`command_outputs/d26_t2_mic01.txt`): 11 lines, median 4.1 s, max 4.8 s, no swap growth. Headroom is small: the worst lines are segments cut at the 7 s cap. 5 of 11 lines end with ` ...` (repeats; ASR quality on them is poor, R5).
- Default suite: **23 passed** (`command_outputs/d26_pytest.txt`). TEST.md: T1.1–T1.5, T2 and T6 `passed`; T1.6, T3, T4 and T5 `not run`.
- **What the app does today:** mic only, live (`--mic`) or file mode (`--mic-wav`). `--system` / `--system-wav` are checked and then refused with a clear error ("not processed yet (milestone M5)", `app.py` lines 159–161). There is no diarizer, so every line is "Me".
- **`README.md` does not exist yet** (repo root checked 2026-11-01).
- Git: last known HEAD `ad8b730` (D26 code + T1.1/T1.2 updates + L11). After that, Claude wrote DECISIONS.md section 3 / R1, TEST.md T2 status + 3 results rows, and this handover (see Pending commits).

## Decisions made in this chat (all already in DECISIONS.md)
- D3 additions: `temperature=0`; then the D26 settings (beam 1, no timestamps, token cap, ` ...`).
- D8 addition: segment cap 7 s. D12 addition: the Armenian text may end with ` ...` (the line format is unchanged). D16: `diag_asr.py`.
- **D25** (FastConformer CTC brought forward): **superseded by D26** for time. FastConformer is in Future ideas (section 6) **and stays in the M7 bake-off (D4 unchanged)**.
- **D26** (option B) + additions: measurements, the token-cap rule and the ` ...` marker.
- L4 (cap 7 s), new **L11** (cut-off lines), R1 notes, section 3 status.
- Finding: CTranslate2 generates at most floor((prompt + `max_new_tokens`) / 2) new tokens. It is not faster-whisper (`command_outputs/fw_transcribe.py` passes the value unchanged); the rule fits every measured value. So `asr.py` passes 2 × the cap.

## Exact next step (proposal, Zaven to approve before anything is written)
**Propose a README outline (headings + one line on what goes under each) and agree it before drafting.** Then draft it section by section, each reviewed by Zaven.

What the README must contain (DECISIONS section 4, Deliverables 2):
1. **Setup + run, including audio device setup.**
   - uv + Python 3.10.12, `.venv` from `requirements.txt` (D14).
   - `.venv-convert` for the one-time model conversion (D23).
   - `python scripts/download_models.py` (D15: models in `models/`, pinned revisions, no runtime downloads).
   - `python app.py --list-devices`, then `--mic "<exact name>"` (D10, D11; PulseAudio, `parec`).
   - File mode `--mic-wav` (tests only, D21).
   - `quit` / Ctrl+C (D11).
   - Terminal font DejaVu Sans Mono for Armenian letters (R15).
   - How to run the tests (TEST.md section 1).
2. **Chosen models, alternatives considered and why.**
   - ASR: faster-whisper small, int8, CPU, with the D26 settings (D3, D7, D26).
   - MT: opus-mt-hy-en via CTranslate2 int8 with `no_repeat_ngram_size=3` (D5).
   - VAD: Silero v6.2.1 ONNX (D8, D24).
   - Alternatives: D4 (bake-off candidates, incl. BuzzASR and FastConformer), D5 (NLLB), D6 (no merged speech→English model), D10 (`sounddevice` rejected), D23, D24, D25 (FastConformer, set aside for time).
3. **Short architecture.** Section 8 (threads + queues, Segment, modules) and D1 / D13 (print order).
4. **Known limitations and what we'd improve with more time.**
   - Section 12 L1–L11; R5 / R1 (small latency headroom).
   - **Not built yet: system audio (M5) and the diarizer (M6)**, so the app is mic only today.
   - Improvements: FastConformer CTC (D25, section 6), NLLB (D5), M5 / M6, T3 / T4, the M8 quality pass, partial text (section 6).
5. **Licences / attribution:**
   - FLEURS CC-BY 4.0 (`eval/meta/README.md`, `tests/fixtures/README.md`).
   - Model licences from the model cards.
   - `chats/` holds the chat transcripts (Deliverables 3).

**Open points to agree for the README:**
- Language and length.
- Whether it reports measured numbers (T2: max 4.8 s; diag CER).
- How to present M5 / M6 as postponed.
- What the README says about `eval/clips/` (gitignored, D16), so a fresh clone can still run the tests (fixtures committed, D22).

**Files to read before drafting:** `app.py` (CLI text), `scripts/download_models.py`, `requirements.in`, `requirements-convert.in`, `.gitignore`, `pytest.ini`, `eval/meta/README.md`, `tests/fixtures/README.md`.

## Pending (not written, waiting for Zaven)
- **DECISIONS.md section 3 still points to M5** and to `handovers/009-latency-fix-done-to-m5.md`. Proposed replacement texts:
  - Current milestone: `- **Current milestone:** M10 — README (Zaven, 2026-11-01). M5, M6 and the M4 tests T3 / T4 postponed.`
  - Next step: `- **Next step:** README.md outline, then draft (see `handovers/009-latency-fix-done-to-readme.md`).`
- **Old handover file:** `handovers/009-latency-fix-done-to-m5.md` is replaced by this file. It is not committed yet, so Zaven deletes it: `rm handovers/009-latency-fix-done-to-m5.md`.
- **`�` fix in `asr.py`.** The token cap can stop in the middle of an Armenian letter's bytes, which leaves `�` (U+FFFD) before ` ...` (seen in T2: «… եմ ե� ...»). Proposal: strip trailing `�` before adding the marker. One line, no new test.
- **T2 conditions:** whether a Meet/Zoom tab was open during the T2 run is not confirmed. The results row says so. Zaven decides whether a re-run with the tab open is needed.

## Open questions
- Client's real setup (DECISIONS.md section 7): still to confirm.
- Time: how much of the remaining 20 h budget is left (Zaven tracks; M10 is 1.5 h; cut order M9, then M8).

## Watch out for
- **Stale writes:** in this chat the file copy tool once wrote an *older* version of a file. It seemed to reuse an earlier upload from the same container path; the file got a new timestamp but the old content. Fix that worked: write each new version under a **fresh file name** in the container, commit it, then read the file back from the laptop and `cmp` it byte for byte. Never skip the read-back.
- The README must describe the code as it is (mic only, D26 settings, 7 s cap). It must not describe M5 / M6 features as working.
- Claude's cloud workspace has no models and no internet for pip; every model run goes through Zaven (working rule 8).
- TEST.md results log: rows are appended, never edited.

## Rules reminder
- Claude proposes; Zaven decides and runs every command, including every git command.
- Command outputs go to `command_outputs/<name>.txt` and are not committed.
- Nothing goes into DECISIONS.md / TEST.md until Zaven approves it.
- Small steps; no silent fallbacks; three-strikes rule.

## Pending commits
```
rm handovers/009-latency-fix-done-to-m5.md
git add DECISIONS.md TEST.md handovers/009-latency-fix-done-to-readme.md
git commit -m "DECISIONS: latency fix done, R1 D26 result; TEST: T1.1/T1.2/T2 results, T2 passed; handover 009 (-> README)"
```
