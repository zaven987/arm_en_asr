# Handover 014 — M6 S4 + S5 done (embedding model, diarizer, threshold 0.76) → M6 S6 — 2026-11-05

**Start the new chat with:** `DECISIONS.md` + `TEST.md` + this file.

## Goal
M5 (second device) then M6 (diarizer), plan S1–S7 in **D27**. S1–S3 (M5) and now **S4** (speaker-embedding model) and **S5** (`diarizer.py` + T1.6) are done. Next: **S6**, connect the real diarizer to the app. Time is not the constraint for M5 / M6 (Zaven, 2026-11-04).

## Current state
- Git (Zaven confirmed all commits): S4 code + records, S5 code (`diarizer.py`, `tune_diarizer.py`, `test_diarizer.py`) and S5 records are committed on `main`. Only this handover is still to commit (see "Pending commits").
- Default suite: **60 passed** (`command_outputs/m6_s5b_pytest.txt`), `.venv`, ASR on the GPU (D30). T1.6 (`-m eval`): **passed** (`m6_s5b_t16.txt`).
- `app.py` still refuses `--system` / `--system-wav` (E4, F5) until S6.
- **S4 (D27 addition J1–J9):**
  - `sherpa-onnx==1.13.8` (+ `sherpa-onnx-core==1.13.8`, CPU wheels, no torch) in `requirements.in` / `.txt`. Both onnxruntimes (Silero's 1.23.2 and sherpa's) load in one process.
  - Model **WeSpeaker ResNet34** `models/speaker-embedding/wespeaker_en_voxceleb_resnet34.onnx` (Hugging Face `csukuangfj/speaker-embedding-models` @ `0743f301…`, SHA-256 checked by `download_models.py`; licence CC-BY 4.0 via VoxCeleb, for the README). CPU, 1 thread, 235 ms median per 7 s segment, +74 MB RSS. CAM++ measured and rejected.
  - Short-segment length **2.0 s** of speech (J8). The 30-minute time-box was dropped; the stop rules were kept (none hit).
- **S5 (D27 addition "S5, K1–K8 and changes"):**
  - `src/arm_en_asr/diarizer.py`: `SpeakerClusters` (rules, plain numpy), `Embedder` (sherpa-onnx), `Diarizer(model_path, threshold=THRESHOLD)` with `label(segment)` → "Speaker N". `MODEL_FILE` (path under `models/`), `SHORT_S` = 2.0, **`THRESHOLD` = 0.76**, `DiarizerError("model missing: …")`.
  - K3 (a) **option B**: until Speaker 1 has a centroid, shorts join it and the first long segment joins it with no check (Zaven's first rule, a short-vs-long check, created a phantom speaker in `mic_01`). K3 (b): "not ready" → last speaker, or Speaker 1.
  - Threshold history: mic-only K4 gave 0.655 → T1.6 merged `sys_01` (9/16, 1 speaker). **Zaven changed the rule: tune on `sys_01` too** (`tune_diarizer.py --sys01`); with option B the range where everything passes is 0.72–0.80 → 0.76. `sys_01` is therefore **not an independent check**, and **no second 2-speaker clip will be made** (Zaven) → R13 updated, **L13** (first sound of a session), **L14** (threshold fitted on one recording, margin 0.04).

## Pending (proposed, NOT answered by Zaven yet)
- None.

## Exact next step
Propose **S6** details (D27 S6) for Zaven's approval before anything is written:
- `app.py`: build `Diarizer(MODELS_DIR / MODEL_FILE)` when a system input is used and pass it to `Pipeline(asr, mt, n_workers=…, diarizer=…)`; remove the `--system` / `--system-wav` refusal (E4 / F5 message at the "D27 E4 / F5" check).
- `check_models()` should also check the speaker-embedding model (clear "model missing" error before anything starts) — propose whether always or only with a system input.
- Decide whether the diarizer needs a warm-up like ASR (W4): in S4 the first embedding call was measured separately as a warm-up (see `m6_s4_embed_resnet34.txt`); measure before adding.
- Tests (T6, D27 S6): replace `tests/test_cli.py::test_system_wav_still_refused` with "a short `--system-wav` run is accepted and exits 0"; T6 must still pass. Possibly a short WAV is needed (e.g. a fixture or a cut of `sys_01`, which is gitignored eval data → D22 rules); propose.
- List exact files, commands and output names (`command_outputs/m6_s6_….txt`) for approval.
- Then S7: T2 re-run on `turns_mic.wav` + `turns_sys.wav` (demo conditions), statuses, DECISIONS / TEST updates, README sections (handover 010) incl. the WeSpeaker / VoxCeleb CC-BY 4.0 licence line and L13 / L14.

## Notes for later (not decisions)
- RAM: app peak was 878 MB before the diarizer; the model adds ~75–125 MB. Measure in S6 / S7.
- The diarizer runs on the CPU (1 thread) beside MT (2 threads); 235 ms per 7 s segment, so it should not add latency, but S7's T2 run will show it.
- `diag_embed.py` and `tune_diarizer.py` use `Segmenter` without `session_start` (offset 0; fine for them).
- sherpa-onnx 2.x may have no Python 3.10 Linux wheel; stay on 1.13.8 unless Zaven decides otherwise.
- The S4 "note for S5" (same-recording speakers score much closer) is what made 0.655 fail; real calls may differ again (L14).

## Still open from earlier
- L11 note (handover 010, not answered): token cap can stop mid-letter → `�` before ` ...`.
- Client's real setup (DECISIONS section 7).
- T3 / T4 postponed.
- README: "Status at a glance" and test counts out of date (now 60); README pass in S7.

## Watch out for
- **Stale writes happened 4 times in this chat:** the laptop received the version from just before Claude's last edit. Rule that worked: after `device_commit_files`, re-stage and `cmp`; if it differs, copy the final file into a **new folder** and commit again, then `cmp` again.
- Claude has no shell on the laptop; Zaven runs every command and every git command (a `device_bash` tool appeared briefly in this chat and was not used).
- Tests and the app **need the GPU** (D30) and now the speaker-embedding model; missing → fail loudly, never skip.
- No silent fallbacks; system lines never mislabelled (E4).
- Live-app tests: anything that starts `parec` can race with an early `quit` (F8).
- TEST.md results log: append only.
- R13 means "eval set too small" (a risk row), not "never tune on `sys_01`"; the tuning rule lives in D27 and was changed in S5.

## Rules reminder
- Claude proposes; Zaven decides and runs every command.
- Command outputs go to `command_outputs/<name>.txt`, never committed.
- Nothing into DECISIONS.md / TEST.md until Zaven approves it.

## Pending commits
```
git add handovers/014-m6-s5-done-to-s6.md
git commit -m "handover 014: M6 S4 + S5 done (ResNet34, diarizer, threshold 0.76) -> M6 S6"
```
