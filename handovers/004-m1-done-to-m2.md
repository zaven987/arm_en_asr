# Handover 004 — M1 done → M2 eval data — 2026-10-30

**Start the new chat with:** `DECISIONS.md` + `TEST.md` + this file.

## Goal
Start milestone **M2 — Eval data v0** (2 h budget): Zaven's 5–10 clips + CSVs (D17, D18) and the FLEURS hy_am subset (D19).

## Current state
- **M1 is done** (DECISIONS.md section 3 has the numbers).
- `.venv` (app) and `.venv-convert` (one-time conversion; torch 2.14.1+cpu, transformers 4.57.6) are both built from pinned files.
- `scripts/download_models.py` has been run (moved from the repo root to `scripts/` on 2026-10-30). `models/` holds:
  - faster-whisper-small
  - opus-mt-hy-en (source checkpoint, kept)
  - opus-mt-hy-en-ct2-int8
  - silero_vad.onnx (SHA-256 in D24)
- `scripts/fetch_fleurs.py` has been run. FLEURS revision `70bb2e8…` is in `eval/fleurs/` (gitignored):
  - hy_am test.tsv (932 rows) and en_us test.tsv (350 rows)
  - hy_am `test.tar.gz` (518 MB, the full test split)
  - the smoke clip (id 2009), as the float original plus a `.pcm16.wav` copy (D18)
- `scripts/smoke_m1.py` ran successfully (`command_outputs/m1_smoke.txt`).
- **No app code yet** (`src/`, `app.py`, `tests/` don't exist).
- Git: the M1 smoke/fetch commit was proposed in this chat. **Zaven: confirm in the new chat whether it has been made.**

## Decisions made in this chat (already in DECISIONS.md)
- **D15:** models live in `models/`; revisions are pinned; `scripts/download_models.py` calls the converter in `.venv-convert`.
- **D16:** layout adds `models/`, `scripts/` (committed; holds `download_models.py`, `fetch_fleurs.py`, `smoke_m1.py`), `eval/fleurs/` (gitignored) and `requirements-convert.in`.
- **D18:** eval clips are 16 kHz mono **16-bit PCM** WAV. FLEURS float WAVs get a `.pcm16.wav` copy.
- **D23:** `requirements-convert.in` is the source file; transformers v4 (4.57.6) chosen over v5.
- **D24:** silero tag v6.2.1 and its SHA-256.
- **Rule 14:** enforced by `.gitignore` (`command_outputs/`, plus `eval/clips/`).
- **R1:** M1 finding: Whisper small RTF 0.58, so a 12 s segment needs ≈ 7 s for ASR alone. To be addressed in M4.
- **R15:** solved by switching the terminal font to DejaVu Sans Mono.

## Next step
Agree with Zaven how M2 starts:
1. **Zaven's clips (D17):** which public/scripted sources, and their device roles (mic clips are single-speaker; system clips have 1–3 speakers).
2. **FLEURS subset (D19, "~100 test sentences"):** Claude proposes the selection rule, for example the first 100 hy_am test rows with an en_us match, one recording per sentence id. Claude then proposes how to extend `scripts/fetch_fleurs.py` to extract them as `.pcm16.wav` plus a metadata CSV in the D18 columns.

Zaven approves before anything is written.

## README setup note (agreed 2026-10-30, to go into README in M10)
> **Armenian in the terminal.** The default Ubuntu terminal font (Ubuntu Mono) has no Armenian letters, so Armenian text looks overlapped. Switch the terminal font to a monospace font that has Armenian: Terminal → Preferences → Profile → Text → Custom font → **DejaVu Sans Mono**. To list suitable fonts: `fc-list ':charset=0531:spacing=mono' family`.

## Watch out for
- **MT quality:** on the *reference* Armenian, opus-mt got only the first half right ("flowers" for legumes, "solar system" for primates). That supports keeping NLLB in the M7 bake-off (D5).
- **"Recommended: pip install sacremoses":** a warning from the Marian tokenizer during conversion. The app uses sentencepiece only. Check at M3/M7 whether skipping it matters; it has not been added.
- **The smoke script frees Whisper before loading MT**, so its peak RSS (829 MB) is not the all-models figure. T4 measures that properly.
- **pytest config:** D16 still has no pytest config file, but TEST.md needs one to exclude the `hardware` and `slow` markers. Propose it with the first tests.
- **HF_TOKEN warning** on downloads: only a rate-limit notice; nothing to do.

## Open questions
- The client's real setup (DECISIONS.md section 7) is still to be confirmed after the walking skeleton.

## Rules reminder
- Claude proposes; Zaven decides and runs every command, including every git command.
- Command outputs go to `command_outputs/<name>.txt` and are not committed.
- Small steps; no silent fallbacks; three-strikes rule.
