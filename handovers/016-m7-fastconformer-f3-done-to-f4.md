# Handover 016 — M7: beam sweep done, Whisper beam 5 (D32), FastConformer CTC F1–F3 done → F4 GPU check — 2026-11-06

**Start the new chat with:** `DECISIONS.md` + `TEST.md` + this file.

## Goal
M7 bake-off. Zaven's direction: replace Whisper small with NVIDIA's Armenian FastConformer, CTC head, greedy decoding, on the MX550 GPU through sherpa-onnx (D31), because Whisper loops (L11). Until F6, the app keeps Whisper small with **beam 5** (D32).

## Current state
- **Beam sweep done** (`command_outputs/m7_beam_sweep.txt`; `diag_asr.py` variants `b2` / `b3`, committed): Whisper small, cuda `int8_float16`, 47 segments of `mic_01`–`03` + `sys_01`. Beams 1 / 2 / 3 / 5: max ASR 1.0 / 1.3 / 1.4 / 1.6 s, loops 7 / 3 / 2 / 2, mean CER 41.5 / 36.1 / 31.9 / 32.4 %. Stage B (turn test) was not run.
- **D32:** `asr.py` `BEAM_SIZE = 5` (written; commit not confirmed). **The D32 check has not been reported yet:** the plain pytest suite and T2 on the turn files at beam 5 (`command_outputs/m7_d32_pytest.txt`, `m7_d32_t2_turns.txt`; commands below). Zaven: "the beam size should stay 5".
- **D31 history:** brought in 2026-11-05, stopped the same day (D32 instead), **resumed 2026-11-06** from F1. All recorded in D31 / D25 / sections 3 and 6.
- **F1 done:** `.venv-nemo` (nemo-toolkit 2.7.3, torch 2.14.1+cpu, onnx 1.22.0, onnxruntime 1.23.2); 4 pure-Python source builds accepted under J4.
- **F2 done:** `.nemo` at revision `353b4090…`, 459 243 520 bytes, SHA-256 OK (`download_models.py` `download_fastconformer_source()`). F2 / F3 split recorded.
- **F3 done:** `scripts/export_fastconformer.py` (E1–E9) run by `download_models.py` `export_fastconformer()` → `models/fastconformer-hy-ctc/` (`model.onnx` 458 MB, `model.int8.onnx` 132 MB, `tokens.txt` 1025 lines). Self-check: NeMo = ONNX fp32 = ONNX int8 text on `speech_short.wav`; CPU 0.14 / 0.07 s for 4.7 s; peak RSS 3.2 GB (`command_outputs/m7_f3_export.txt`).
- **F4 files written (agreed), not run yet:** `requirements-fc.in`, `.gitignore` (`.venv-fc/`), `scripts/check_fc_gpu.py` (C1–C6). Recorded in D31 ("F4 files agreed") and D16.
- **Diarizer:** `THRESHOLD` back to **0.76** (D27 S5). In between, Zaven had tried 0.65 (written by Claude, no records, at his request) and 0.97 (set by Zaven on the laptop). Both are gone now.
- TEST.md: no changes in this chat. Statuses: T1.1–T1.6, T2, T6 passed; T3, T4, T5 not run.

## Exact next step
Zaven runs F4 and sends the outputs:
```
uv venv .venv-fc --python 3.10
uv pip compile requirements-fc.in --python-version 3.10 -o requirements-fc.txt > command_outputs/m7_f4_compile.txt 2>&1
uv pip install --python .venv-fc -r requirements-fc.txt > command_outputs/m7_f4_install.txt 2>&1
.venv-fc/bin/python scripts/check_fc_gpu.py > command_outputs/m7_f4_check.txt 2>&1
.venv-fc/bin/python -m pytest -v tests/test_diarizer.py > command_outputs/m7_f4_diarizer.txt 2>&1
.venv-fc/bin/python -m pytest -m eval tests/test_diarizer.py -v -s > command_outputs/m7_f4_t16.txt 2>&1
```
Claude reads them:
- **Compile:** does the CUDA wheel resolve from `--find-links`, and does it need `sherpa-onnx-core`?
- **check_fc_gpu.py** must end with `CHECK OK`. In particular, C5 VRAM must be > 0, otherwise sherpa-onnx silently ran on the CPU. Also look at the C4 CER against the E8 text, and the timings.
- **T1.6** must give the same result as before: the default diarizer tests pass (20); `mic_01`–`03` 1 speaker each; `sys_01` 16/16, 2 speakers.
- Then Claude proposes the F4 record (results) and the F5 plan.

## F5 / F6 (agreed in D31, details still to propose)
- **F5:** `scripts/diag_fastconformer.py` in `.venv-fc`, demo conditions (Zoom tab open, plugged in). It uses the same segments (real Silero + Segmenter, 7 s cap) and the same CER clean-up as `diag_asr.py`, on `mic_01`–`03` + `sys_01`, for fp32 and int8. It records ASR time per segment (median / max), CER per clip, RSS, VRAM and swap, compared with the four rows of `m7_beam_sweep.txt` (beam 5 = the current app setting). FLEURS is not used (the model was trained on it).
  - Note: the reference CSVs have punctuation and capitals, and the CER clean-up lowercases and drops them, so the comparison with Whisper is fair.
- **F6:** Zaven decides. A new D# covers:
  - the `asr.py` change, keeping the `Asr.transcribe()` interface
  - merging the CUDA sherpa-onnx and the extra NVIDIA packages into `requirements.in` (`--find-links`)
  - the token cap and ` ...` (L11), which CTC doesn't need
  - the T1.2 test changes
  - README later
  - whether the 7 s VAD cap (D26, set for Whisper's latency) is kept

## Notes for later (not decisions)
- **Live mic-as-`--system` test (Zaven, 2026-11-05):** every line got the same speaker. Possible causes (not diagnosed):
  - short segments < 2 s never create a speaker (J8)
  - K3 a option B, the first long segment joins Speaker 1 unchecked (L13)
  - a threshold fitted on `sys_01` (L14)

  If Zaven wants it diagnosed: record the mic with `parec … --file-format=wav eval/clips/live_diar.wav` during a live test, replay it with `--system-wav`, then a small diagnostic of per-segment length / similarity (new code, propose first). Raising the threshold (≈ 0.80–0.85), not lowering it, splits voices more.
- **README** (postponed S7c) still says `beam_size=1` (line 270); it also needs the FastConformer outcome.
- **D32 trade-off:** beam search sometimes ends early and drops the rest of a segment, with no ` ...` marker.
- **The int8 export's "unsupported type to quantize" warnings** are harmless (int64 shape tensors).
- **On the GPU, int8 may be slower than fp32** (limited CUDA int8 kernels); F5 measures it.
- **`cuda-bindings` 13.4.4** sits unused in `.venv-nemo`.
- **Swap was full on 2026-11-05 (R17);** the F3 export peaked at 3.2 GB RSS.

## Watch out for
- **Stale writes:** stage the laptop file fresh before editing, write each new version from a new output folder, then re-stage and `cmp`. In this chat the laptop's `diarizer.py` had been changed by Zaven (0.97) between writes; the fresh-stage rule caught it.
- **`device_commit_files`** only accepts files under `/mnt/user-data/outputs/`.
- **No shell on the laptop:** Zaven runs every command and every git command. Claude doesn't claim a commit happened unless Zaven confirms it.
- **GitHub / PyPI pages** may not be fetchable from Claude's side (allowlist); NeMo API details were written from documentation and confirmed by the F3 run.
- **No silent fallbacks:** GPU → CPU in sherpa-onnx is exactly the risk C5 checks.

## Rules reminder
- Claude proposes; Zaven decides and runs every command.
- Command outputs go to `command_outputs/<name>.txt` and are never committed.
- Nothing goes into DECISIONS.md / TEST.md until Zaven approves it. TEST.md results log: append only.

## Pending commits (run any not yet done, in this order; Zaven confirmed only the M1 / section 3 commits from 2026-11-05)
```
git add src/arm_en_asr/asr.py DECISIONS.md
git commit -m "M7 D32: Whisper beam_size 5 (was 1); D31 FastConformer stopped, back to Future ideas"
git add src/arm_en_asr/diarizer.py
git commit -m "diarizer THRESHOLD back to 0.76 (D27 S5)"        # only if 0.65 / 0.97 had been committed; else git diff shows nothing
git add DECISIONS.md requirements-nemo.in .gitignore
git commit -m "M7 D31 resumed: F1 requirements-nemo.in, .venv-nemo gitignored"
git add requirements-nemo.txt
git commit -m "M7 D31 F1: requirements-nemo.txt (nemo-toolkit 2.7.3, torch 2.14.1+cpu)"
git add scripts/download_models.py DECISIONS.md
git commit -m "M7 D31 F1 record + F2: download_models.py fetches the FastConformer .nemo (pinned, SHA-256)"
git add scripts/export_fastconformer.py scripts/download_models.py DECISIONS.md
git commit -m "M7 D31 F2 record + F3: export_fastconformer.py (CTC head -> ONNX, int8, self-check); download_models.py runs it"
git add DECISIONS.md requirements-fc.in .gitignore scripts/check_fc_gpu.py
git commit -m "M7 D31 F3 record + F4 files: requirements-fc.in, check_fc_gpu.py, .venv-fc gitignored"
git add handovers/016-m7-fastconformer-f3-done-to-f4.md
git commit -m "handover 016: M7 FastConformer F3 done -> F4 GPU check"
```
Commits whose files were already committed together will just carry fewer files. `requirements-fc.txt` is committed after F4 has been reviewed.

## D32 check commands (still to run)
```
python -m pytest -v > command_outputs/m7_d32_pytest.txt 2>&1
{ free -m; /usr/bin/time -v python app.py --mic-wav eval/clips/turns_mic.wav --system-wav eval/clips/turns_sys.wav; free -m; } > command_outputs/m7_d32_t2_turns.txt 2>&1
```
Run T2 with the Zoom tab open and the laptop plugged in; pass = every line ≤ 5 s.
