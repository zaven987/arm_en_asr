# Handover 005 — M2 done → M3 walking skeleton — 2026-10-31

**Start the new chat with:** `DECISIONS.md` + `TEST.md` + this file.

## Goal
Start milestone **M3 — Walking skeleton, mic only** (3 h budget): `--list-devices`, capture, VAD, ASR, MT, print, `quit`, latency measurement, file mode (D10–D13, D21). Tests that belong to M3 in TEST.md: T1.1–T1.5 and T6.

## Current state
- **M2 is done** (DECISIONS.md section 3).
- Eval data (all metadata committed in `eval/meta/`, audio gitignored):
  - `fleurs_hy_am_test100.csv`: FLEURS subset, first 100 matched sentence ids, 19.5 min, 4.7–30.9 s, 36 clips longer than 12 s (D19). WAVs in `eval/fleurs/hy_am/test/*.pcm16.wav`. Attribution in `eval/meta/README.md`.
  - `mic_01.csv` (folk tale), `mic_02.csv` (news reading), `mic_03.csv` (speech): about 1 min each, one speaker, `Me` (D17).
  - `sys_01.csv`: 89 s, 2 speakers (`Speaker 1`, `Speaker 2`), used for T1.6 (D17).
  - References are verbatim (D18). English added by Claude, reviewed by Zaven.
  - WAVs in `eval/clips/` are 16 kHz mono 16-bit (`command_outputs/m2_clips_check.txt`).
- Helper scripts added: `scripts/download_mms.py`, `scripts/draft_mms.py` (MMS-1B-all in `models/mms-1b-all/`, run in `.venv-convert`, reference drafting only, not an app model). `scripts/fetch_fleurs.py` extended for the subset.
- **Still no app code** (`src/`, `app.py`, `tests/` don't exist).
- Git: one commit made in this chat (FLEURS subset + MMS scripts + DECISIONS). The M2 reference-CSV commit was proposed at the end of this chat. **Zaven: confirm in the new chat whether it has been made.**

## Decisions made in this chat (already in DECISIONS.md)
- **D4:** NVIDIA `stt_hy_fastconformer_hybrid_large_pc` added to the M7 bake-off; we export it to ONNX ourselves (D23 pattern). Mic clips are not from Grqaser.
- **D15:** `download_models.py` stays for app models only; helper-only models get their own download helper (`download_mms.py`).
- **D16:** layout adds `download_mms.py`, `draft_mms.py`, `eval/meta/README.md`.
- **D17:** 4 clips (3 mic + `sys_01` with 2 speakers); the 3-speaker clip was dropped.
- **D18:** FLEURS subset in one CSV (+ `fleurs_id`, `wav`); references drafted by MMS-1B-all and corrected by Zaven; verbatim spelling; labels `Me` / `Speaker N`.
- **D19:** subset rule = first 100 hy_am test sentence ids with an en_us match, one recording each.

## Correction to handover 004
It said en_us `test.tsv` has 350 rows. It has **647 recordings of 350 sentences**; hy_am has 932 recordings of 350 sentences. The script label is fixed.

## Next step
Agree with Zaven how M3 starts. Claude proposes M3 as a short list of small, separately committable steps (for example: package skeleton + `app.py` CLI + T6; then capture/VAD in file mode + T1.1; then ASR, MT, output, pipeline with their tests), including the pytest config that excludes the `hardware` and `slow` markers (carried over from handover 004). Zaven approves before anything is written.

## Watch out for
- **R1 latency:** Whisper small RTF 0.58 means a 12 s segment needs about 7 s of ASR. Still to be addressed in M4 (T2, T4).
- **M7 notes, not decided yet:**
  - FLEURS clips: fed to ASR whole, or through VAD (D8 cap), decided in M7 (D19).
  - Text clean-up before WER/CER must treat «։» and «:» as the same, and «և» and «եւ»; remove ՞ ՛ ՜, which sit inside words; ignore case and punctuation.
  - Verbatim references (D18) score models that write standard spelling (e.g. «ճիշտ է» for «ճիշտա») as wrong; clean-up cannot fix this.
  - FastConformer ONNX export probably needs NeMo in `.venv-convert`; agree the exact steps in M7.
- **Clips end mid-word** (`mic_01` «սրբ», `mic_02` «170»): the references mirror the audio; that is intended.
- **Editing CSVs:** a plain text editor saved the drafts without quotes, so commas inside sentences broke the CSV. The files in `eval/meta/` are proper CSV; if they need edits, tell Claude, or keep quotes intact.
- **Files Claude sends** don't need downloading into the repo: Claude writes directly to the folder. Downloads created duplicates (`scripts/fetch_fleurs-1.py`, `Claude outputs/`), both deleted.
- **MMS warning** "lm_head … newly initialized" is expected: the Armenian adapter replaces that layer.
- Carried over from 004: "Recommended: pip install sacremoses" (check at M3/M7); the HF_TOKEN warning is harmless.

## Open questions
- The client's real setup (DECISIONS.md section 7) is still to be confirmed after the walking skeleton.

## Rules reminder
- Claude proposes; Zaven decides and runs every command, including every git command.
- Command outputs go to `command_outputs/<name>.txt` and are not committed.
- Small steps; no silent fallbacks; three-strikes rule.
