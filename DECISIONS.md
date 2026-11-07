# DECISIONS.md — Live Armenian → English transcription + translation (local laptop)

> **How to use this file.** This is the single source of truth for the project. It replaces PLAN.md (whose content is extracted and corrected below). Paste this file (plus the latest handover from `handovers/`, if any) into a fresh chat to continue work. Every decision has a number (D#), a reason, and the alternatives we considered. Anything marked **PROPOSED** is not agreed yet and must not be built on until Zaven confirms it.

- Architect / owner: Zaven
- Team: Claude (writes files, proposes commands and commits)
- Created: 2026-10-26 · Last updated: 2026-11-07 (M7 WER, Whisper vs FastConformer)

---

## 1. Working rules (stable — never change without Zaven)

1. **Scope:** do not add features outside the plan's scope (sections 4–5). New ideas go to "Future ideas" (section 6), not into code.
2. **No silent fallbacks. Fail loudly and clearly.** (e.g. GPU requested but missing → exit with error, never quietly use CPU; missing model → error, never auto-download at runtime.)
3. **Small steps.** Each step should be small enough to review and commit on its own.
4. **Git:** Claude only *proposes* commits (message + files). Claude never runs git commands. Zaven runs `git init` and every git command himself.
5. **Record everything here:** every decision and its reason, in short human-readable steps, plus the current project status / milestone (section 3).
6. **Three-strikes rule:** if Claude fails three times on the same problem, stop, go back to the last working state, and narrow the problem down together with Zaven.
7. **Focused chats:** when a chat gets long, Claude writes a short handover (goal, current state, decisions, next step) to `handovers/NNN-topic.md`; a new chat starts with DECISIONS.md + that handover.
8. **Who runs what:** Zaven runs all terminal commands (app, tests, installs) on his laptop. Claude has no shell on the laptop; Claude proposes the exact commands to run and Zaven sends back the exact output/errors.
9. **Command outputs:** when Claude needs a command's output, Claude asks Zaven to save it into `command_outputs/<name>.txt`, and Zaven sends back that file path.
10. **TEST.md:** every part of TEST.md (what is written, each test's status passed / not passed) is agreed with Zaven *before* it is written.
11. **Risk mitigations:** any new mitigation must be agreed with Zaven before it is written here.
12. **Time:** Zaven monitors the 20-hour budget and is the one who decides whether a milestone is overrunning and must be cut. Cut order: M9 first, then M8.
13. **Chats folder:** Zaven exports all chat transcripts as `.md` into `chats/`.
14. **Command outputs are not committed:** files in `command_outputs/` stay local on Zaven's laptop and are never committed to git; enforced by `.gitignore`. (added 2026-10-29)

---

## 2. Quick facts

| Item | Value |
|---|---|
| Laptop | ThinkPad E16 Gen 1, Ubuntu 22.04.5 LTS, kernel 6.8 |
| CPU | Intel i5-1335U (2 P-cores + 8 E-cores, 12 threads, 15 W) |
| RAM | 7.4 GiB total, **~2.4 GiB available** at measurement, swap 2 GiB (1.4 GiB already used) → **RAM is the tightest constraint** |
| GPU | NVIDIA GeForce MX550, 2 GiB VRAM, driver 580, CUDA 13.0 |
| Disk | ~309 GB free |
| Audio | **Real PulseAudio 15.99.1** (not PipeWire). Default mic: `alsa_input.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__hw_sofhdadsp_6__source`; monitors end in `.monitor` |
| Python | 3.10.12, env managed with **uv** |
| Locale | en_US.UTF-8 |
| Raw specs | `command_outputs/laptop_specs.txt` |
| Total time budget | **20 hours** |

---

## 3. Current status

- **Current milestone:** M7 — ASR/MT bake-off. First step: a `beam_size` sweep on Whisper small, to see which beam sizes keep latency roughly under 5 s (Zaven, 2026-11-05); done. FastConformer was brought in (D31), stopped the same day and resumed on 2026-11-06 from F1; until F6 the app ASR stays Whisper small with beam 5 (D32). M6 S7c (README sections) postponed (Zaven, 2026-11-05); M10 (README, final test run, TEST.md statuses) afterwards. M5 and M6 done (2026-11-05). M4 tests T3 and T4 postponed (Zaven, 2026-11-01).
- **M5 + M6 plan agreed (2026-11-04):** steps S1–S7 and their rules in D27.
- **README done (2026-11-01):** `README.md` written and committed (`496adf4`).
- **Latency fix done (2026-11-01):** D26 (Whisper greedy, no timestamps, token cap with ` ...`, VAD cap 7 s); T2 on mic_01 passed: max 4.8 s (`command_outputs/d26_t2_mic01.txt`).
- **M3 started (2026-10-31):** plan S1–S8 agreed (handover 005). S1 done: `app.py` CLI, device and model checks, `pytest.ini`, T6 part 1 (3 tests pass; `command_outputs/m3_s1_pytest.txt`). sacremoses closed: not used at runtime (opus-mt runs with ctranslate2 + sentencepiece).
- **S2 done:** fixtures committed (ids 1817, 1699). **S3 done:** audio_capture + T1.1 (passed; `command_outputs/m3_s3_pytest.txt`).
- **S4 done (2026-11-01):** `asr.py` + T1.2 (passed, 2 tests; `command_outputs/m3_s4_pytest.txt`, `m3_s4b_pytest.txt`).
- **S5 done (2026-11-01):** `translate.py` + T1.3 (passed; `command_outputs/m3_s5b_pytest.txt`). opus-mt repetition loop found and fixed with `no_repeat_ngram_size=3` (D5, L10; `scripts/diag_mt.py`, `command_outputs/m3_s5_diag_mt.txt`).
- **S6 done (2026-11-01):** `output.py` + T1.4 (passed, 4 tests; `command_outputs/m3_s6_pytest.txt`). Line format and latency warning as D12 (O1–O6).
- **S7 done (2026-11-01):** `pipeline.py` + T1.5 (passed, 7 tests; `command_outputs/m3_s7_pytest.txt`); `Asr` takes `num_workers` (D1, D3, D13 additions; L5 note).
- **S8 done, M3 done (2026-11-01):** app connected (live mic + file mode, quit, Ctrl+C) + T6 (passed; `command_outputs/m3_s8_pytest.txt`). First manual runs: live short phrases 2.9–3.1 s; file mode `mic_01` 3.2 s → 111.1 s, a backlog (`command_outputs/m3_s8_file_mic01.txt`, `m3_s8_live.txt`; R1).
- **M2 done (2026-10-31):** reference CSVs written and reviewed: `eval/meta/mic_01`–`03.csv`, `eval/meta/sys_01.csv` (4 clips, D17; verbatim, D18); FLEURS subset `eval/meta/fleurs_hy_am_test100.csv` (D19).
- **Done in M2 (2026-10-30/31):** FLEURS subset built: 100 clips, 19.5 min, 4.7–30.9 s, 36 longer than 12 s (D19; `command_outputs/m2_fleurs_subset.txt`). MMS-1B-all downloaded (revision `3d33597…`) and run by `scripts/draft_mms.py` to draft references (D15, D18; peak RAM 4.8 GB); Zaven corrected the drafts, Claude added English. NVIDIA Armenian FastConformer added to the M7 bake-off (D4).
- **Done in M1 (2026-10-29):** pinned environment installed and verified (`command_outputs/m1_*.txt`); `.venv-convert` built (torch 2.14.1+cpu, transformers 4.57.6); `scripts/download_models.py` run: all models in `models/` (`command_outputs/m1_download.txt`).
- **M1 done (2026-10-30):** smoke run on FLEURS hy_am test id 2009 (14.76 s; `command_outputs/m1_smoke.txt`). All models load offline (faster-whisper works with huggingface-hub 2.3.0). VAD: 82 % of windows speech. ASR (Whisper small, int8, CPU, defaults): RTF 0.58 (8.5 s for 14.76 s), 100 % Armenian letters, CER ≈ 12 %, WER ≈ 56 % (mostly phonetic spelling errors). MT (opus-mt int8): 0.2 s per sentence; on the reference Armenian only the first half is correct. RAM: peak RSS 829 MB (VAD + ASR; the script freed Whisper before loading MT, so all models together ≈ 0.9–1.0 GB, to be measured in T4), 3.5–4.2 GB available, swap growth 0 MB. Armenian renders correctly after switching the terminal font (R15).
- **M0 done (2026-10-29):** questions asked and answered; decisions D1–D22 agreed (incl. D4 BuzzASR time-box); this file and TEST.md (tests T1.1–T1.6, T2–T6, all "not run") written and committed by Zaven; handovers 001 and 002 written.
- **M5 S1 done (2026-11-04):** pipeline accepts system segments with a diarizer; T1.5 passed (14 tests). **S2 done:** overlap measured, N = 1 kept (D28), L12 added.
- **Turn-taking measurement (2026-11-04): not passed** (max 6.7 s, 5/28 lines > 5 s, mostly token-cap loops). Fix agreed: `repetition_penalty=1.1` + ASR warm-up (D26 additions).
- **Latency fix on GPU done (2026-11-05):** D29 / D30: ASR on the MX550 (cuda `int8_float16`); turn test max 1.8 s on the app path (`command_outputs/m5_g4_turns_app.txt`); 32 tests pass.
- **M5 S3 done (2026-11-05):** two-device capture (`Capture`, E1 session offset, E2 / E3, F1–F8); `--system` still refused (E4); `ParecSource` stop/start race fixed (F8); 41 tests pass (`command_outputs/m5_s3b_pytest.txt`).
- **M6 S4 done (2026-11-05):** speaker-embedding model chosen: `sherpa-onnx` 1.13.8 + WeSpeaker ResNet34 on the CPU; CAM++ rejected; short-segment length 2.0 s (D27 J1–J9; `command_outputs/m6_s4_embed_resnet34.txt`, `m6_s4_embed_campplus.txt`).
- **M6 S5 done (2026-11-05):** `diarizer.py` (`SpeakerClusters`, `Embedder`, `Diarizer`; K3 a option B; `THRESHOLD` 0.76, tuned on `mic_01`–`03` + `sys_01`) + `tests/test_diarizer.py`; 60 tests pass; T1.6 passed: each solo mic clip 1 speaker, `sys_01` 16/16 with 2 speakers (tuned on it, so not an independent check; L14) (D27 S5; `command_outputs/m6_s5b_pytest.txt`, `m6_s5b_t16.txt`).
- **M6 S6 done (2026-11-05):** the app builds the real diarizer when a system input is given; `--system` / `--system-wav` accepted; the speaker-embedding model is checked always; no diarizer warm-up; 61 tests pass, T6 passed (8/8). `sys_01` through the app: labels as T1.6 (16/16), max latency 5.2 s (2/16 lines > 5 s, not T2), peak RSS 1070 MB (D27 S6; `command_outputs/m6_s6_pytest.txt`, `m6_s6_sys01.txt`).
- **M6 S7a done (2026-11-05):** T2 passed on the turn files with the real diarizer (Zoom tab open, plugged in): 28 lines, median 1.3 s, p95 1.6 s, max 1.6 s, 0 > 5 s; peak RSS 1079 MB; swap full (R17) (D27 S7; `command_outputs/m6_s7_t2_turns.txt`). **M5 and M6 done.**
- **M7 beam sweep done (2026-11-05):** Whisper small, cuda `int8_float16`, beams 1 / 2 / 3 / 5 on `mic_01`–`03` + `sys_01` (47 segments; `command_outputs/m7_beam_sweep.txt`, `diag_asr.py` variants b2 / b3): ASR max per segment 1.0 / 1.3 / 1.4 / 1.6 s, loops 7 / 3 / 2 / 2 of 47, mean CER 41.5 / 36.1 / 31.9 / 32.4 %. Stage B (turn test) not run; replaced by the D32 check (pytest + T2 on the turn files).
- **M7 D31 F4 done (2026-11-06):** `.venv-fc`; FastConformer CTC on the GPU via sherpa-onnx CUDA: fp32 0.023 s / int8 0.131 s for 4.68 s, both CER 0 % on the fixture; order rule D33; T1.6 unchanged (`command_outputs/m7_f4e_check.txt`).
- **M7 D31 F5 done (2026-11-06):** FastConformer fp32 mean CER 9.4 % vs Whisper beam 5 32.4 %, max ASR 0.118 s vs 1.6 s (`command_outputs/m7_f5_diag_fc.txt`).
- **M7 D31 F6 decided (2026-11-06): D34:** the app ASR becomes FastConformer CTC fp32 on the GPU; faster-whisper removed; the D32 check is not run (replaced by F6c).
- **D34 F6a done (2026-11-06):** VAD cap stays 7 s; 10 s (mean CER 8.5 % vs 9.4 %) goes to M8 (`command_outputs/m7_f6a_segcap.txt`).
- **Next step:** D34 F6b code (`asr.py`, `app.py`, `conftest.py`, tests, requirements). M6 S7c README sections (handover 010 list) postponed. T3 / T4 later (Zaven, 2026-11-01).
- **Open / pending:** client's real setup (section 7) to be confirmed after the walking skeleton.

---

## 4. Goal and scope (from PLAN.md, corrected)

Build a Python terminal app, run as `python app.py`, that during a live session (an online call):

1. **Captures audio** at the same time from exactly two input devices chosen by the user: one microphone (the user, "Me") and one system-audio output monitor (the other call participants).
2. **Transcribes** the speech (Eastern Armenian only) to Armenian text (ASR).
3. **Translates** the Armenian text to English (MT).
4. **Labels the speaker:** everything from the microphone is always **"Me"** (even if the voice changes); system-audio speech is labelled **"Speaker N"**, stable for the whole session. Speakers are not remembered between sessions.
5. **Prints live in the terminal:** Armenian text, English translation, speaker label, and the **start time of the speech as offset from session start**, plus the measured latency.

Corrections to PLAN.md:
- Goal step 3 said "translate Armenian *translations*" → it means *transcriptions*.
- The module list in PLAN.md was an unordered set, not the flow. The flow is in section 8.
- `output` takes a combined record (Armenian, English, speaker, time, latency), not only Armenian text.
- "Datetime" = offset from session start (HH:MM:SS), start of the speech.

**Constraints**
- End-to-end latency (end of spoken Armenian phrase → its English line in terminal) **≤ 5 s**. This is the only hard quality threshold for now. The VAD silence that detects "end of phrase" counts inside the 5 s.
- Everything runs on Zaven's laptop. No cloud speech/translation APIs. Internet only for the one-time model download; fully offline at runtime.
- Python; any libraries/models allowed if they run locally. Non-commercial project → non-commercial model licences are OK.

**Deliverables** (git repo)
1. Source code.
2. README: setup + run (incl. audio device setup); chosen models, alternatives considered and why; short architecture; known limitations and what we'd improve with more time.
3. `chats/` with all chat transcripts as `.md`.

---

## 5. Out of scope

- Any GUI (terminal only).
- Installers or packaged apps.
- Saving transcripts to a file.
- Echo handling.
- Overlapping-speech handling (best effort only).
- More than one mic or more than one system monitor.

## 6. Future ideas (not to be built unless Zaven moves them into scope)

- Partial / streaming text while a person is still speaking (now: final lines only).
- NVIDIA Armenian FastConformer CTC as the ASR model (D25): cannot loop, and its cost does not grow with the number of tokens. Set aside for time on 2026-11-01; brought into scope and stopped on 2026-11-05 (D31); in scope again since 2026-11-06 (D31 resumed), so no longer a Future idea.

---

## 7. Demo assumption (open question)

- Worst case assumed for the demo: **a web browser with a video call (Zoom/Meet) is open, laptop plugged in.** Models must keep latency ≤ 5 s under this load.
- **Open question (revisit after the walking skeleton):** the client's exact setup may differ; if so, we adjust then.

---

## 8. Architecture

Single process, threads + queues. Shared unit = **Segment** `{id, device (mic|system), start, end, audio, end_wall}` (`end_wall` added 2026-11-01, see D12); every stage attaches its result to the segment id.

```
[mic parec] ──► VAD ──┐
                      ├──► segment_queue ──► ASR workers (N, one shared model) ──► MT ──┐
[sys parec] ──► VAD ──┘            │                                                ├──► pipeline (join by segment id) ──► output (print)
                                   └──► diarizer (system segments only) ─────────────┘
stdin reader: "quit" → clean shutdown
```

Modules (`src/arm_en_asr/`):
| Module | Input | Output |
|---|---|---|
| `audio_capture` | two exact PulseAudio source names | VAD-segmented `Segment`s (16 kHz mono) |
| `asr` | Segment audio | Armenian text |
| `translate` | Armenian text | English text |
| `diarizer` | system-audio Segments | "Speaker N" (mic segments are always "Me") |
| `pipeline` (new) | all of the above | owns queues/threads, joins results by segment id, measures latency |
| `output` | joined record | terminal line |

Terminal line format:
```
[00:01:23] Speaker 1:  Բարև, ինչպե՞ս ես
           → Hi, how are you?   (2.8s)
```

---

## 9. Decision log

Format: **what** · *why* · alternatives considered. All agreed 2026-10-28 unless marked otherwise.

**D1 — Concurrency: one process, threads + queues.**
- What: one capture+VAD thread per device → shared segment queue → N ASR worker threads sharing one model → MT → pipeline join → output thread. Diarizer runs in parallel with ASR, not after it. Start with N = 1.
- Why: separate processes would each load their own model copy and break the RAM limit; CTranslate2 / onnxruntime release the Python GIL, so threads run truly in parallel.
- Backlog: any line over 5 s gets a visible warning; app keeps running.
- Alternatives: multiprocessing (rejected: RAM); strictly sequential flow (rejected: latency).
- Addition (agreed 2026-11-01, M3 S7, P1, P2, P5, P7–P9): `pipeline.py` has `Pipeline(asr, mt, n_workers=1, printer=print_line, clock=time.monotonic)`. `submit(segment)` is called from the capture thread; `check()` raises a stored worker error; `close()` drains everything submitted (printed or skipped), stops all threads and raises any error. Threads: N ASR workers → one MT thread → one output thread (join, order, latency, print); queues are unbounded, nothing is dropped. A worker exception stops the pipeline and is raised as `PipelineError` naming the stage and segment id. One shutdown path: `close()`; for `quit`, capture stops first, then `close()`, so segments already captured still print. `Asr(model_dir, num_workers=1)`; the pipeline refuses `asr.num_workers` ≠ `n_workers` (D3). Mic segments are always "Me"; until M5/M6 a system segment is refused with a clear error.

**D2 — Load test.**
- What: feed K simultaneous segments (from eval clips) with N = 1, 2, 3 ASR workers, with a real Meet/Zoom tab open. Record: peak RSS, swap use, per-segment latency (median / p95 / max), throughput (segments per minute).
- Result: the largest N and K that keep RAM within limits and max latency ≤ 5 s → becomes our concurrency setting.
- Pass (agreed 2026-10-29, TEST.md T4): grid N = 1, 2, 3 × K = 1, 2, 4, 6; a combination passes if max latency ≤ 5 s and swap grows ≤ 100 MB during the run.
- Tie-breaker if several combinations pass (agreed 2026-10-29): (1) highest segments processed per minute, (2) highest N, (3) lowest max latency.
- Why: Zaven asked to know how many segments the laptop can process in parallel before hitting RAM limits or degrading latency.

**D3 — Skeleton ASR: `faster-whisper` "small", int8, CPU, language fixed to `hy`.**
- Why: ~0.5 GB RAM, most likely to work for sure (PLAN: "not much advanced on first choices"). Accuracy on Armenian is expected to be weak; that is acceptable for the skeleton.
- Addition (agreed 2026-11-01, M3 S4, A1–A6):
  - Load: `WhisperModel(models/faster-whisper-small, device="cpu", compute_type="int8", cpu_threads=4, num_workers=1)`. 4 threads leave cores for capture and MT. M1's RTF 0.58 was measured with the default (`cpu_threads=0`), so T4 measures this setting. With N > 1 workers sharing the model, `num_workers` must equal N (M4).
  - Transcribe: `language="hy"`, `task="transcribe"`, `vad_filter=False` (Silero segments, D8), `condition_on_previous_text=False` (explicit; has no effect on segments ≤ 12 s, since each segment is its own call), `beam_size=5`. Speed tuning belongs to M4 / R1.
  - Interface: `Asr(model_dir).transcribe(audio) -> str`; audio is the Segment's float32 mono 16 kHz array; pieces joined with spaces and stripped; `""` if Whisper returns nothing (what to do with empty lines: S7).
  - `Asr` itself checks `model_dir/model.bin` exists and raises a clear "model missing" error; otherwise faster-whisper would treat the path as a model name and try a download (working rule 2, D15).
- Addition (Zaven, 2026-11-01, M4): `temperature=0.0` in `transcribe`, so faster-whisper decodes each segment once and never re-decodes at higher temperatures. Reason: the S8 file-mode run on `mic_01` reached 111 s latency, and fallback retries on low-confidence Armenian were the leading suspect. The 5 s latency rule comes before a small loss in ASR accuracy. Result: `command_outputs/m4_file_mic01_temp0.txt`: max latency 111.1 s → 29.6 s, no swap growth, but 4 of 7 segments now print Whisper repetition loops.
- Addition (Zaven, 2026-11-01, D26): `transcribe` now uses `beam_size=1` (replacing A2's 5; back to 5 by D32, 2026-11-05), `without_timestamps=True`, and the D26 token cap (`max_new_tokens` = 2 × `token_cap(segment seconds)`). When the cap is hit, the text ends with ` ...` (L11).

**D4 — ASR bake-off after the skeleton (in M7), on our eval data + FLEURS.**
- Candidates:
  - Whisper small (skeleton baseline) — CPU.
  - Whisper large-v3-turbo int8 on MX550 GPU — ~0.8 GB VRAM, speed unknown.
  - Meta Omnilingual ASR CTC 300M — 1.3 GB fp32 (less in fp16 on GPU); strong average multilingual CER; no punctuation; needs fairseq2; Armenian score unknown.
  - **BuzzASR/armenian, quantized** (Whisper large-v3 fine-tune, best Armenian accuracy found: FLEURS WER ≈ 11.9 %, CER ≈ 3.7 %). Added on Zaven's question. Full fp16 (~3 GB) does not fit; int8 (~1.6–1.8 GB) or whisper.cpp q5 (~1.1 GB) might fit RAM, but the full 32-layer decoder likely breaks 5 s on the 15 W CPU, and int8 conversion itself needs loading ~3 GB fp16 weights.
  - BuzzASR quantized is a conditional candidate with a **30-minute time-box** (agreed 2026-10-28); if it does not load and run within that, we record it as "rejected: hardware" and move on.
  - **NVIDIA `stt_hy_fastconformer_hybrid_large_pc`** (added 2026-10-30, on Zaven's question). FastConformer hybrid Transducer + CTC, ~115M parameters, Armenian only, outputs punctuation and capitals, CC-BY-4.0. Model card: FLEURS test WER 12.3 % (Transducer) / 13.2 % (CTC). Trained on Common Voice 17 (48 h), FLEURS (12 h), Grqaser audiobooks (22 h) and two proprietary sets (~214 h). Not Whisper in architecture or data, small enough to be fast on CPU.
    - Conversion: we export it to ONNX ourselves in `.venv-convert` and run it with onnxruntime (D23 pattern). The third-party ONNX export (OpenVoiceOS) is rejected for the same reason as in D23 (we can't verify where it came from). Exact export steps are agreed in M7.
    - Caveat: it was trained on Grqaser audiobooks, so eval clips taken from Grqaser could inflate its score. Zaven's mic clips are not from Grqaser (confirmed 2026-10-31).
- Why: Armenian is low-resource; ASR quality is our biggest risk, so we choose the final model by measurement.

**D5 — Skeleton MT: `Helsinki-NLP/opus-mt-hy-en` (Marian), via CTranslate2 int8.**
- Why: ~0.1 GB. Whisper (0.5 GB) + NLLB (0.7 GB) + diarizer + Zoom (~1 GB) would push us to the ~2.4 GB limit.
- Bake-off candidate (M7): NLLB-200-distilled-600M (int8, ~0.6–0.7 GB, CC-BY-NC — OK for us), usually better quality.
- Addition (agreed 2026-11-01, M3 S5, B1–B6):
  - Load: `ctranslate2.Translator(models/opus-mt-hy-en-ct2-int8, device="cpu", compute_type="int8", inter_threads=1, intra_threads=2)`; 2 threads so ASR keeps its 4 (D3); T4 tunes it.
  - Tokenisation as in the M1 smoke run: `source.spm` encode + `</s>`; decode with `target.spm`, dropping `</s>`.
  - One call per segment, no sentence splitting (M1 weakness on long input revisited in M7/M8); `beam_size=2` (CTranslate2 default, set explicitly).
  - Interface: `Mt(model_dir).translate(armenian) -> str` (class named `Mt`, not `Translator`, to avoid confusion with `ctranslate2.Translator`); empty input → `""` without calling the model.
  - `Mt` checks `model.bin`, `source.spm`, `target.spm` exist and raises a clear "model missing" error naming the file (working rule 2, D15). No separate test for it.
  - T1.3 input: `armenian` text of the first 3 rows of `eval/meta/fleurs_hy_am_test100.csv`.
- Addition (agreed 2026-11-01, M3 S5): the first T1.3 run showed a repetition loop on FLEURS sentence 2 («6-6-6-…-a-a-a-…» up to CTranslate2's 256-token limit; L10). Diagnosis: `scripts/diag_mt.py` (committed) compares beam 2 / 3 / 6, int8 vs float32, the original PyTorch model, `no_repeat_ngram_size=3`, `repetition_penalty=1.2` and ":" → "։". **Time-box 30 minutes**; if no clean fix is found in that time, `no_repeat_ngram_size=3` is added. Any change to B3 is agreed before `translate.py` changes.
- Addition (agreed 2026-11-01, M3 S5, C1–C3): result of `diag_mt.py` (`command_outputs/m3_s5_diag_mt.txt`).
  - Finding: the loop is in the **model itself**. The original PyTorch model loops on sentence 2 too (beam 2 and 6, up to its 512-token limit), so conversion, int8 and tokenisation are not the cause. Beam 3 and beam 6, float32, `repetition_penalty=1.2` and ":" → "։" all still loop; a wider beam is only slower (beam 6 ≈ 2×), float32 ≈ 3–4× slower with no better output.
  - **C1 fix:** `no_repeat_ngram_size=3`, with int8 and `beam_size=2` kept (B1, B3 unchanged). It was the only variant that stopped the loop (sentence 2: 28 tokens, 0.14 s instead of 256 tokens, 1.5 s), and it left sentences 1 and 3 almost unchanged at no extra time.
  - **Trade-off:** the English output of one segment can never contain the same 3-token sequence twice, even when the speaker really repeats it (e.g. a phrase said twice, or a score like «6-6-6»). Such repeats are rare inside one segment of ≤ 12 s; when they occur, the English may drop or reword the repeat. The fix stops the loop but does not fix meaning: sentence 2 still translates «6-6» as "six or six" (L10, M7).
  - **C2:** T1.3 also checks that each English output is at most 2× its Armenian input in characters, so a loop now fails the test. In `diag_mt.py`, normal outputs were 0.72–1.64× and the CTranslate2 loop (stopped at 256 tokens) 2.32–2.47×; the margin is narrow, so if T1.3 inputs change, the 2× limit is re-checked.
  - **C3 rejected:** no output-length cap (`max_decoding_length` tied to input length); C1 already fixes the measured loop.

**D6 — Separate ASR + MT. Merged speech→English model rejected.**
- Why: we must show Armenian text anyway, so a single speech→English model is not enough; SeamlessM4T (main merged option) is too large for this laptop.

**D7 — Skeleton runs on CPU.**
- Why: GPU needs CUDA/cuDNN setup (time risk). GPU stays a bake-off option. Device is explicit; requesting GPU when unavailable is an error, never a silent fallback.
- Addition (Zaven, 2026-11-05, D29 / D30): ASR now runs on the MX550 GPU (`cuda`, `int8_float16`); MT and VAD stay on the CPU. The explicit-device rule stays: no GPU → error, never a CPU fallback.

**D8 — VAD: Silero VAD (ONNX, MIT).**
- Settings: end of phrase = 0.6 s silence; ignore speech < 0.3 s; **hard cap 12 s per segment**.
- Known trade-off: the 12 s cap may cut mid-word / mid-sentence. Revisit in the quality pass (M8) if time allows.
- Addition (Zaven, 2026-11-01, D26): the hard cap is now **7 s** (was 12 s), for latency; see D26 for the measurements.
- Addition (agreed 2026-10-31, M3 S3): Silero runs on 512-sample windows; a window is speech if p > 0.5 (the two-threshold variant 0.5 / 0.35 waits for M8 if the VAD turns out choppy). At the 12 s cap the segment closes at exactly 12 s and the next one starts with the remaining audio (nothing lost). 0.2 s of audio is kept before the first and after the last speech window, counted inside the cap. At end of stream (end of file or `quit`) an open segment is closed and emitted.

**D9 — Diarizer: chosen at its milestone (M6).**
- Plan: small speaker-embedding model (WeSpeaker/ECAPA via sherpa-onnx or SpeechBrain, ~25–80 MB) + online clustering (assign to nearest known speaker by cosine similarity, or create a new speaker under a threshold).
- Runs on system-audio segments only. Mic is always "Me". Focus on 1–2 remote speakers first, then more if evaluated.
- Why: lightweight, matches PLAN's VAD + clustering idea; must be online because the app is live.

**D10 — Audio capture: one `parec` subprocess per device, raw s16le 16 kHz mono.**
- `--list-devices` prints `pactl list short sources` (includes `.monitor` sources).
- Why: PulseAudio resamples for us; exact PulseAudio names work directly. `parec` is already installed (pulseaudio-utils).
- Alternatives: `sounddevice`/PortAudio (rejected: does not expose monitor sources by exact name); `soundcard` library (backup).
- Addition (agreed 2026-10-31): command `parec --device=<name> --format=s16le --rate=16000 --channels=1 --raw`; parec ending mid-session = device lost → loud error.

**D11 — CLI.**
```
python app.py --list-devices
python app.py --mic "<exact source name>" --system "<exact monitor name>"
python app.py --mic-wav a.wav [--system-wav b.wav]     # file mode, tests only
```
- `--mic` is the microphone, `--system` the system-audio monitor; names must match `--list-devices` output exactly.
- Typing `quit` + Enter → clean shutdown. Any other text → "unknown command".
- In the mic-only skeleton (M3) `--system` is optional; from M5 on both are required.
- Fail loudly (exit with clear error): unknown device name, missing model, device lost mid-session.
- Addition (agreed 2026-10-31): T6 tests "missing model" by calling `app.main()` in-process with `MODELS_DIR` pointed at an empty folder; no new CLI option. The "unknown device" tests need PulseAudio running but no person, so they are not marked `hardware`.
- Addition (agreed 2026-10-31): until M5, `--system` / `--system-wav` are checked (device name / file exists) and then refused with a clear error, never silently ignored (working rule 2).
- Addition (agreed 2026-10-31), replacing "from M5 on both are required" above: at least one of `--mic` / `--system` is given; either may be left out. The same applies to `--mic-wav` / `--system-wav`.
- Addition (agreed 2026-11-01, M3 S8, Q1–Q9): startup order: checks → models → pipeline → capture → stdin reader; the session clock starts at the first captured sample. Transcript lines go to stdout, all other messages to stderr (`loading models…`, `listening on …` / `playing …`, `stopped`). `quit` → exit 0; any other non-blank text → `unknown command: '<text>'`, keeps running; blank lines are ignored; end of stdin stops command reading only. File mode ends by itself with exit 0 once every line is printed. A lost device or a pipeline error drains what was captured, then exits 1 with `ERROR: …`. Ctrl+C = the same clean shutdown, exit 130 (a second Ctrl+C stops at once). `parec` runs in its own session, so Ctrl+C reaches only the app, which stops `parec` itself.
- Addition (Zaven, 2026-11-04, D27 E1–E3): with two devices, the session clock starts just before the capture threads start (replacing "at the first captured sample" above), file mode ends when every input has ended, and losing either device ends the whole session with exit 1.

**D12 — Output line shows speaker, start offset (HH:MM:SS), Armenian, English, and measured latency** (format in section 8).
- Latency = time the line is printed − time the speech segment ended.
- Lines whose latency > 5 s get a visible warning.
- Addition (agreed 2026-10-31): `Segment` = `{id, device, start, end, audio, end_wall}`. `start` / `end` = first / last speech sample in seconds from session start, counted by samples. `end_wall` = `time.monotonic()` arrival of the chunk holding the last speech sample; latency is measured from it, so the 0.6 s end silence counts inside the 5 s.
- Addition (agreed 2026-11-01, M3 S6, O1–O6): `output.py` has a `Record` `{segment_id, speaker, start, armenian, english, latency}`, a pure `format_line(record) -> str` (T1.4) and `print_line(record)`, which prints with `flush=True`; S7 measures latency just before calling it. The offset `[HH:MM:SS]` is truncated, not rounded (83.9 s → `[00:01:23]`). The layout is exactly section 8: 2 spaces after the colon, an 11-space indent, 3 spaces before `(`, latency to 1 decimal. A warning `(5.3s ⚠ >5s)` is shown when the raw latency is > 5.0 s, so 5.04 s shows `(5.0s ⚠ >5s)`. Empty text is formatted as given; whether to skip it is decided in S7. Plain text only, no colours, no new dependency.
- Addition (Zaven, 2026-11-01, D26): the Armenian text can end with ` ...` when the ASR token cap stopped it (L11). The marker is part of the ASR text, so `output.py` and the line format do not change.

**D13 — Print order: by when speech ended.** (see Known limitation L5)
- Addition (agreed 2026-11-01, M3 S7, P3, P4): each segment gets a sequence number when it is submitted, i.e. when its end was detected; the output thread prints in that order, and a finished result waits until every earlier one is printed or skipped (cross-device case: L5). A segment whose ASR text is empty after stripping is skipped: no MT call, no line, and its place in the order is released. Empty English for non-empty Armenian is still printed.

**D14 — Environment: uv + Python 3.10.12.**
- `uv venv --python 3.10` creates `.venv`; install with `uv pip install -r requirements.txt`; all versions pinned in `requirements.txt`.
- Addition (agreed 2026-10-29): stay on Python 3.10.12 even though it reaches end-of-life in Oct 2026. The pins that depend on 3.10 are onnxruntime 1.23.2 and numpy 2.2.6, the last versions with 3.10 support. Direct dependencies live in `requirements.in`; `requirements.txt` is generated from it by `uv pip compile` and never edited by hand.
- Alternative: a uv-managed Python 3.12 (rejected for now; revisit at M7 if a bake-off candidate needs 3.11+).

**D15 — Models downloaded once by `scripts/download_models.py`.**
- The app sets `HF_HUB_OFFLINE=1` and exits with a clear error if a model is missing. No runtime downloads.
- Addition (agreed 2026-10-29): models live in `models/` at the repo root (gitignored). Revisions are pinned: faster-whisper-small `536b066…`, opus-mt-hy-en `79b0a50…`. `download_models.py` calls the converter in `.venv-convert`.
- Addition (agreed 2026-10-30): `download_models.py` moved from the repo root to `scripts/` (run as `python scripts/download_models.py`), so all helper scripts live together.
- Addition (agreed 2026-10-30): `download_models.py` stays for **app models only**. A model used only by a helper script gets its own one-time download helper. First case: MMS-1B-all for reference drafting (D18), fetched by `scripts/download_mms.py` into `models/mms-1b-all/` (gitignored) at a pinned revision, base files + Armenian adapter (`adapter.hye.*`) only, not the full repo.

**D16 — Repo layout.**
```
app.py
src/arm_en_asr/{audio_capture,asr,translate,diarizer,pipeline,output}.py
tests/
tests/fixtures/           # small committed fixtures (D22)
eval/meta/*.csv           # committed
eval/clips/*.wav          # gitignored
chats/  handovers/  command_outputs/
models/                   # gitignored (D15)
scripts/                  # helper scripts, committed (added 2026-10-29):
                          #   download_models.py (D15; moved here 2026-10-30), fetch_fleurs.py (D19), smoke_m1.py (M1),
                          #   download_mms.py + draft_mms.py (D15, D18; added 2026-10-30)
                          #   make_fixtures.py (D22; added 2026-10-31)
                          #   diag_mt.py (D5 MT loop diagnosis, runs in .venv-convert; added 2026-11-01)
                          #   diag_asr.py (latency fix: Whisper speed / loop variants, runs in .venv; added 2026-11-01)
                          #   diag_two_devices.py (M5 S2: two devices at once, N / threads variants; added 2026-11-04)
                          #   make_turns.py (M5: turn-taking WAVs turns_mic / turns_sys from mic_01 + sys_01; added 2026-11-04)
                          #   diag_embed.py (M6 S4: speaker-embedding measurement on mic_01-03 + sys_01; added 2026-11-05)
                          #   tune_diarizer.py (M6 S5: diarizer threshold sweep on mic_01-03, --sys01 adds sys_01; added 2026-11-05)
                          #   export_fastconformer.py (D31 F3: FastConformer CTC head -> ONNX for sherpa-onnx, runs in .venv-nemo; added 2026-11-06)
                          #   check_fc_gpu.py (D31 F4: FastConformer CTC on the GPU via sherpa-onnx CUDA, runs in .venv-fc; added 2026-11-06)
                          #   diag_fastconformer.py (D31 F5: FastConformer CTC fp32 / int8 on the eval clips, same segments + CER as diag_asr.py, D33 order; runs in .venv-fc; added 2026-11-06)
                          #   diag_wer.py (M7: Whisper vs FastConformer WER + CER on the same segments; runs in .venv-fc; added 2026-11-07)
eval/fleurs/              # raw FLEURS files, gitignored (D19; added 2026-10-29)
eval/meta/README.md       # data sources + licences (FLEURS CC-BY 4.0), committed (added 2026-10-30)
DECISIONS.md  TEST.md  README.md  requirements.txt  .gitignore
pytest.ini                # added 2026-10-31: pythonpath = src, markers hardware / slow excluded by default via addopts;
                          #   app.py adds src/ to sys.path itself (no packaging, no pyproject.toml)
requirements.in  requirements-convert.in  requirements-convert.txt     # added 2026-10-29 (D14, D23)
requirements-nemo.in  requirements-nemo.txt     # added 2026-11-06 (D31 F1): one-time FastConformer export env .venv-nemo
requirements-fc.in  requirements-fc.txt         # added 2026-11-06 (D31 F4): measuring env .venv-fc (sherpa-onnx CUDA build)
```

**D17 — Evaluation clips: each clip has one device role.**
- Mic clips: single speaker ("Me"). System clips: 1–3 speakers (podcasts, interviews).
- Tests needing both devices pair a mic clip with a system clip via `--mic-wav` + `--system-wav`.
- Extra use (testing only): mic clips are also fed through the diarizer to check it keeps the **same speaker number for one speaker through a whole solo clip**.
- Source: existing public/scripted audio (no one recorded). 5–10 clips, 1–3 min each, at least 2 speakers overall.
- Addition (agreed 2026-10-30): 5 clips. **3 mic clips**, 1 min each, from audiobooks (single reader). **2 system clips**, 1.5 min each, from podcasts chosen by Zaven: one with **2 speakers** (used for T1.6, the 1–2 remote speaker case of D9/M6) and one with **3 speakers**. Files: `eval/clips/mic_01…03.wav`, `sys_01…02.wav`, converted with ffmpeg to 16 kHz mono 16-bit PCM.
- Addition (agreed 2026-10-31): cut to **4 clips** for time, replacing the 5-clip plan above. `mic_01`–`03`: about 1 min each, one speaker each (folk tale, news reading, speech). `sys_01`: 89 s, 2 speakers, used for T1.6. The 3-speaker clip was dropped, so diarization is measured only on the 2-speaker case (D9, L8). This is deliberately below D17's original 5–10 clips.

**D18 — Clip metadata: one CSV per clip, audio 16 kHz mono WAV.**
- Columns: `start,end,device,speaker,armenian,english`. Times in seconds from clip start (e.g. `12.40`).
- Zaven writes Armenian text, times, speakers → Claude adds English and formats → Zaven reviews.
- Audio gitignored; only metadata committed.
- Addition (agreed 2026-10-29): eval clips are stored as 16 kHz mono 16-bit PCM WAV. FLEURS ships 32-bit float WAV, so `scripts/fetch_fleurs.py` keeps the original and writes a `.pcm16.wav` copy next to it.
- Addition (agreed 2026-10-30): the FLEURS subset is described by one file, `eval/meta/fleurs_hy_am_test100.csv`: the D18 columns plus `fleurs_id` and `wav`; `start=0.00`, `end` = clip length, `device=mic`, `speaker=Me`. Generated by `scripts/fetch_fleurs.py`, never edited by hand. Attribution (CC-BY 4.0) in `eval/meta/README.md`.
- Addition (agreed 2026-10-30): reference text for Zaven's clips is drafted by **Meta MMS-1B-all** (`hye` adapter, run once in `.venv-convert`) and then corrected by hand by Zaven. The draft model is non-Whisper, so references don't lean towards a bake-off candidate. MMS is not a bake-off candidate itself, because it was trained on FLEURS.
  - `scripts/draft_mms.py eval/clips/<name>.wav` checks the file is 16 kHz mono 16-bit (fails loudly otherwise), cuts it into ~15 s windows at the quietest point between 12 and 18 s (one long pass would need several GB of RAM), and writes `eval/clips/<name>.draft.csv` (gitignored) in the D18 columns: `armenian` = draft, `speaker` and `english` blank. The draft has no capitals and no punctuation.
  - Zaven corrects the text, adds punctuation, splits it into speaker turns with times and saves `eval/meta/<name>.csv`; then Claude adds English and Zaven reviews (as above).
  - Runs in fp32 (~4 GB RAM); Zaven closes browser tabs while it runs.
- Addition (agreed 2026-10-31): references are **verbatim**: spoken forms are kept as pronounced (e.g. «նցոր», «ճիշտա», «կարաս»), not changed to standard spelling. Speaker labels in CSVs: `Me` for mic, `Speaker N` for system, the same as the terminal. The MMS draft run worked (peak RAM 4.8 GB; `command_outputs/m2_mms_draft.txt`).

**D19 — Public data: FLEURS hy_am only** (~100 test sentences; FLEURS has parallel English text → free MT references).
- Common Voice dropped to save time (needs manual login download).
- Addition (agreed 2026-10-30): FLEURS hy_am test has 350 sentences in 932 recordings, all with an en_us match. Subset = the **first 100 hy_am test sentence ids in TSV order** that have an en_us match, one recording per id (the first row for that id). Result: 19.5 min, 4.7–30.9 s per clip, 36 clips longer than 12 s. Whether clips are fed to ASR whole or through VAD (D8 cap) is decided in M7.
  - Rejected: all 350 (~69 min, about 40 min of ASR per candidate in M7); only clips ≤ 12 s (biases towards short sentences).

**D20 — Metrics (v0, baseline only, no quality thresholds yet).**
- ASR: WER and CER. MT: chrF / BLEU + Zaven's manual 1–5 rating. Latency: median / p95 / max. Diarization: % of segments with correct label.
- Only hard pass/fail: latency ≤ 5 s.
- Tests: pytest. Initial tests: (1) each module alone on fixture audio, (2) end-to-end latency in file mode, (3) capture smoke test (open both devices 3 s, check audio is not silent), plus the D2 load test. Virtual-sink capture test after the skeleton (M9). (4) CLI fail-loudly checks (T6, added 2026-10-29). Full list and pass criteria: TEST.md.
- Sanity limits (agreed 2026-10-29; not quality thresholds): ASR output ≥ 50 % Armenian-script letters (T1.2); capture "not silent" = RMS > −50 dBFS (T3); load test swap growth ≤ 100 MB (T4); diarizer keeps one label on 100 % of a solo clip's segments (T1.6).

**D21 — File mode feeds WAVs at real-time speed.** (agreed 2026-10-29)
- What: `--mic-wav` / `--system-wav` stream the file at the speed it was recorded, not as fast as possible.
- Why: otherwise the whole file arrives instantly and the measured latency (D12) means nothing compared with live use.
- Alternatives: feed as fast as possible (rejected: latency not comparable to live).
- Addition (agreed 2026-10-31): the WAV source takes an explicit `realtime` flag. The app always uses `True`; the T1.1 unit tests use `False` (they test segmentation only; latency is T2). WAV input must be 16 kHz mono 16-bit PCM or it fails loudly.

**D22 — Test fixtures and test policy.** (agreed 2026-10-29)
- What: small fixture files are committed in `tests/fixtures/`: a few seconds of FLEURS hy_am audio (CC-BY 4.0, attribution in `tests/fixtures/README.md`), generated silence, and ≥ 12 s continuous speech. A missing model or fixture makes a test **fail**, never skip. pytest markers: `hardware` (real devices + person present) and `slow` (load test), excluded from a plain `pytest` run.
- Why: tests run from a fresh clone; skipping would be a silent fallback (working rule 2).
- Alternatives: gitignored fixtures like `eval/clips/` (rejected: tests could not run from a fresh clone).
- Addition (agreed 2026-10-31): fixtures are generated by `scripts/make_fixtures.py`: `speech_short.wav` (shortest subset clip, whole), `silence_5s.wav` (zeros), `speech_long.wav` (first subset clip with an unbroken Silero speech run ≥ 13 s, whole); the script writes `tests/fixtures/README.md` (attribution, ids, SHA-256).
- Addition (Zaven, 2026-11-04): new pytest marker **`eval`** for tests that need the gitignored eval clips in `eval/clips/` (first case: T1.6). Excluded from a plain `pytest` run, like `hardware` and `slow`. A missing clip makes the test **fail** with a clear error, never skip. Why: those clips cannot be in a fresh clone, so the default suite stays runnable from one.

**D23 — Model conversion happens in a separate, one-time environment.** (agreed 2026-10-29)
- What: opus-mt-hy-en is converted to CTranslate2 int8 in `.venv-convert` from a pinned `requirements-convert.txt` (CPU-only torch + transformers).
- Why: torch never enters the app environment.
- Addition (agreed 2026-10-29): direct dependencies go in `requirements-convert.in`; `requirements-convert.txt` is generated with `uv pip compile --torch-backend cpu`. Pins: ctranslate2 4.8.4, transformers 4.57.6 (last v4; chosen over v5 because the Marian converter is long proven on v4), torch 2.14.x CPU, sentencepiece 0.2.2.
- Alternatives: torch in the main environment (rejected: about 1 GB more, and a risk of pulling the CUDA build); someone else's pre-converted model (rejected: we can't verify where it came from).

**D24 — Silero VAD file comes from the official snakers4/silero-vad GitHub repo at a pinned release tag.** (agreed 2026-10-29)
- What: `scripts/download_models.py` fetches `silero_vad.onnx`; the app runs it with onnxruntime.
- Addition (agreed 2026-10-29): tag v6.2.1 (6.2.2 / 6.2.3 judged minor).
- Addition (agreed 2026-10-29): SHA-256 of `silero_vad.onnx` v6.2.1 (2 327 524 bytes): `1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3`.
- Alternatives: the `silero-vad` pip package (rejected: requires torch); the copy bundled in faster-whisper (rejected: ties VAD to the ASR library).

**D25 — Latency fix: bring NVIDIA Armenian FastConformer (CTC) forward from M7 as the ASR model.** (Zaven, 2026-11-01) (superseded by D26, 2026-11-01)
- What: `stt_hy_fastconformer_hybrid_large_pc` (D4) is brought forward from the M7 bake-off to now, to fix latency (R1). We use its **CTC head with greedy decoding**, not its Transducer head. Export to ONNX in `.venv-convert`, run with onnxruntime (D4, D23 pattern); the exact export steps are agreed before any work starts. Until it is measured and agreed, the app keeps Whisper small as it is (D3, `temperature=0`); there is no runtime fallback between the two models (working rule 2).
- Why: settings alone cannot bring Whisper small under 5 s without losing text. Measured with `scripts/diag_asr.py` (`command_outputs/latency_diag_asr.txt`, `latency_diag_asr_f.txt`; 3 mic clips, 21 segments):
  - Whisper's encoder costs ≈ 1.9 s per segment whatever its length (it always processes a 30 s window), and each output token costs another ≈ 17 ms (greedy) to ≈ 37 ms (beam 5). Armenian speech needs ≈ 15.8 Whisper tokens per second, so a full 12 s segment is ≈ 190 tokens ≈ 5.5 s of ASR alone, even with greedy decoding.
  - Best accuracy (`without_timestamps=True`, "g"): CER 19.5–34.5 %, but max ASR 9.3 s. Fastest (g + greedy + token cap, "g+b+c"): max ASR 4.3 s, but CER 45–51 %, because the cap cut the end of normal speech: the effective cap was half the value set (e.g. 285 → 144 tokens on every 12 s segment; reason not yet known), so most of its speed came from dropping text without any sign.
- **Why FastConformer CTC cannot loop:** Whisper's decoder is autoregressive: each token is predicted from the tokens it has already written, so once it writes a repeat, that repeat makes the next one more likely, and it can repeat until its token limit (the «ԱՐՈՈՈՈ…» lines). CTC has no such feedback. The encoder outputs one label distribution per audio frame (80 ms after 8× subsampling, so a 12 s segment has ≈ 150 frames); greedy decoding takes the best label in each frame, merges repeated labels and removes blanks. The model never sees its own output, and the output can never be longer than the number of frames, which is fixed by the audio length. Bad audio can still give wrong text, but not an endless loop.
- **Why its cost does not grow with the number of tokens:** all the work is one encoder pass over the actual audio (no padding to 30 s), so the cost depends on the audio length only. Turning the frames into text is one arg-max per frame, which is almost free. Whisper instead runs its decoder once per output token, and Armenian needs many tokens.
- Note: this holds for the **CTC head only**. The model's Transducer head (FLEURS WER 12.3 % vs CTC 13.2 %) predicts each label from the previous ones, so its cost does grow with the output; it is not used.
- Not yet known (measured after the export): speed on this CPU, RAM, and accuracy on our clips (CER on `mic_01`–`03`, same clean-up as `diag_asr.py`). The model outputs punctuation and capitals; the reference CSVs have them too (D18).
- Alternatives (from the `latency_diag_asr_f.txt` results): (A) keep Whisper with g+b+c (rejected: drops roughly the last quarter of long segments without any sign, CER ≈ 49 %); (B) Whisper g+b with a shorter VAD cap, e.g. 7 s (not chosen: more mid-word cuts, L4, and the 1.9 s encoder floor stays); (D) Whisper g alone (rejected: max ASR 9.3 s breaks 5 s).
- Addition (Zaven, 2026-11-01): superseded before any work started: not enough time left in the budget. Option B chosen instead (D26). FastConformer CTC moved to Future ideas (section 6); the reasons above stay as the record for that idea.
- Addition (Zaven, 2026-11-05): brought back into scope by D31, on the GPU instead of the CPU; the reasons above (CTC cannot loop, cost grows with audio length only) still apply; stopped the same day (D31); resumed on 2026-11-06 (D31).

**D26 — Latency fix: Whisper small, faster settings + shorter segments (option B).** (Zaven, 2026-11-01)
- What: transcribe with `without_timestamps=True`, `beam_size=1`, `temperature=0`, and a token cap that only stops loops (it must never cut normal speech); the VAD segment cap (D8) is shortened from 12 s. The exact cap values are chosen from one more `diag_asr.py` run and agreed before `asr.py` / `audio_capture.py` change.
- Why: `latency_diag_asr_f.txt`: a full 12 s segment needs ≈ 5.5 s of ASR even with greedy decoding (≈ 1.9 s encoder + ≈ 190 tokens × 17 ms); shorter segments mean fewer tokens per call.
- Trade-offs: more segments cut mid-word (L4; this was M8 work, now pulled forward); greedy decoding has a worse CER than beam 5 (g+b vs g); the 1.9 s encoder cost per segment stays.
- Alternatives: see D25.
- Addition (Zaven, 2026-11-01): values chosen from `command_outputs/latency_diag_asr_segcap.txt` (g+b+c on mic_01–03, segment caps 6 / 7 / 8 s): **VAD segment cap 7 s** (D8). At 7 s: max ASR 4.7 s per segment (6 s: 4.4 s; 8 s: 5.1 s), CER 59.0 / 45.8 / 36.1 % (6 s: 68.5 / 45.6 / 53.5 %; 8 s: 68.4 / 52.2 / 62.9 %). Token cap: allowed tokens = ceil(15.8 tok/s × segment length × 1.5), at most 220, passed as `max_new_tokens` = 2 × that, because CTranslate2 generates at most half of `max_length` (prompt + `max_new_tokens`); this rule fits every measured value (`diag_asr.py` H1). Known cost: 13 of 31 segments hit the cap at 7 s (mostly greedy over-generation such as «եմ եմ եմ …»); their text stops at the cap and what came before is printed. CER is worse than Whisper beam 5 at 12 s (32.5 / 19.5 / 34.5 %), which broke 5 s.
- Addition (Zaven, 2026-11-01): a segment whose text was stopped by the token cap is shown with ` ...` at the end of its Armenian text, so the cut is visible, never silent (working rule 2, L11). Code: `asr.py` (`token_cap`, `CUT_MARKER`); T1.2 tests `token_cap`.
- Addition (Zaven, 2026-11-04, M5): `transcribe` also uses `repetition_penalty=1.1` (variant d1). Measured with `diag_asr.py` on `mic_01`–`03`, 7 s cap (`command_outputs/m5_diag_asr_rp.txt`): loops 13/31 → 3/31, CER 59.0 / 45.8 / 36.1 % → 46.7 / 24.8 / 31.1 %, total ASR 115.4 → 111.3 s, max ASR 4.7 s (unchanged). Rejected: 1.3 (d2): loops 1/31, but it returned empty text on 2 segments and garbage on others; CER 59.3 / 53.9 / 50.0 %. Reason: the turn-taking test failed because looping segments run to the token cap (≈ 4.7 s of ASR each). The token cap and ` ...` stay as a safety net (3/31 still loop).
- Addition (Zaven, 2026-11-04, M5, W2–W4): `Asr.warm_up()` transcribes 1 s of silence once and discards the result; the app calls it while "loading models…" (before "listening on"), and `diag_two_devices.py` does the same. Reason: the first line of the turn-taking run took 6.75 s, and the app (unlike `diag_asr.py`) had no warm-up. T1.2 checks that `warm_up()` runs.

**D27 — M5 + M6 plan: second device, then diarizer.** (Zaven, 2026-11-04)
- Steps (each reviewed and committed on its own):
  - **S1** `pipeline.py`: optional `diarizer`; system segments accepted only when there is one; T1.5 updated.
  - **S2** `scripts/diag_two_devices.py`: `mic_01` + `sys_01` at the same time, real time, real Segmenters / Pipeline / ASR / MT, stub diarizer. Variants: N = 1 / `cpu_threads` 4, N = 2 / 4, N = 2 / 2. Records latency (median / p95 / max, lines > 5 s), peak RSS, swap. Demo conditions, Meet/Zoom tab confirmed. Output `command_outputs/m5_s2_two_devices.txt`. Zaven then chooses N and threads (new D#).
  - **S3** `app.py` + `audio_capture.py`: one VAD, one Segmenter and one capture thread per device (`capture-mic`, `capture-system`), shared id counter; rules E1–E3 below. `--system` still refused (E4).
  - **S4** embedding model choice (see M6 below).
  - **S5** `diarizer.py` + T1.6 (`eval` marker, D22).
  - **S6** app passes the real diarizer; the `--system` refusal is removed; T6 still passes, plus one test that a short `--system-wav` run is accepted and exits 0.
  - **S7** T2 re-run `app.py --mic-wav eval/clips/mic_01.wav --system-wav eval/clips/sys_01.wav` (replaced by the turn files `turns_mic.wav` + `turns_sys.wav`, see the addition after S2 below; Zaven, 2026-11-05), demo conditions; then statuses, DECISIONS / TEST updates and the README sections listed in handover 010.
- **E1 Session clock with two devices** (changes D11 Q1 "the session clock starts at the first captured sample"): one shared start time is taken just before the capture threads start. Each Segmenter adds its own offset = arrival of its first chunk − one window (32 ms) − start time; `start` / `end` stay counted by samples (D12) plus that offset. Why: two `parec` processes (or two WAV threads) do not start at the same instant. Caveat: `parec` buffering enters the offset, so it is approximate (tens of ms); the display truncates to whole seconds.
- **E2 File mode with WAVs of different length:** the session ends when **every** input has ended and every line is printed (exit 0); the shorter file's capture thread just finishes first.
- **E3 Lost device:** one device lost → the whole session ends: what was captured is drained, then exit 1 with `ERROR: …` (as D11).
- **E4 No mislabelled lines** (working rule 2): `Pipeline` takes an optional `diarizer`; a system segment submitted without one is refused loudly (`PipelineError`). The app keeps refusing `--system` / `--system-wav` until S6 connects the real diarizer, so before that system lines appear only in test stubs and in the S2 output file.
- **E5 Latency with two devices:** measured in S2 before choosing N. `mic_01` + `sys_01` overlap almost all the time, a worst case that real calls (turns and pauses) do not reach. If this worst case breaks 5 s but realistic conversational audio passes, that is accepted and recorded as a known limitation (Zaven).
- **M6 model (S4):** first candidate `sherpa-onnx` (feature extraction + ONNX inference in one package) with a small WeSpeaker / 3D-Speaker embedding model (~25–40 MB). Package via `requirements.in` → `uv pip compile` (D14); model via `scripts/download_models.py` at a pinned URL with SHA-256 (D15, D24); licence recorded for the README. **30-minute time-box on installation:** if `sherpa-onnx` causes install problems on Python 3.10, stop and use the fallback `kaldi-native-fbank` + our onnxruntime. Choosing the fallback is a decision, never a runtime fallback. Sanity check: a smoke script embeds every segment of `mic_01`–`03` and `sys_01` and prints time per embedding, RSS, and cosine similarity for same-speaker vs different-speaker pairs.
- **M6 clustering (S5):** online; each speaker has a centroid = mean of its normalised embeddings. A segment joins the nearest speaker by cosine similarity; if the best score is below the threshold, it becomes a new "Speaker N". The diarizer runs in its own thread beside ASR (D1), on system segments only, in submit order (clustering depends on order).
  - **Threshold** tuned on `mic_01`–`03` only (three different readers give same- and different-speaker pairs); `sys_01` is used for testing only, so it is not tuned on (R13).
  - **Short segments** (below a speech length set in S4, about 1 s; R11): assigned to the nearest *existing* speaker; they never create a new speaker and never update a centroid. If no speaker exists yet, the segment becomes Speaker 1.
  - **T1.6 scoring:** each segment gets the reference speaker (`eval/meta/sys_01.csv`) it overlaps most in time; segments with no overlap are counted and left out. Speaker numbers are matched to reference names by the best one-to-one mapping. Reported: % correct, number of speakers found, short segments separately.
- Time: Zaven, 2026-11-04: time is not the constraint for M5 / M6.
- Addition (Zaven, 2026-11-04, after S2): S2 result (`command_outputs/m5_s2_two_devices.txt`; Zoom tab open, plugged in): with `mic_01` + `sys_01` talking at the same time, every variant breaks 5 s (max 23.0 / 23.2 / 18.2 s for n1t4 / n2t4 / n2t2) because segments arrive faster (≈ one per 3.3 s) than the pipeline finishes them (≈ one per 3.8 s), so a queue builds up. This overlap case is recorded as a measurement and known limitation L12, **not** as T2. A realistic **turn-taking** test is added before S3: `scripts/make_turns.py` builds `eval/clips/turns_mic.wav` + `turns_sys.wav` (gitignored): turns of about 10–15 s cut at the quietest 100 ms, alternating `sys_01` / `mic_01`, 1 s silence between turns, the other track silent. It is measured now with `diag_two_devices.py --mic … --system … --variants n1t4` (new options); pass = every line ≤ 5 s. **Pass → go straight to S3. Fail → stop and decide together on reducing the token-cap loops.** S7's T2 re-run uses the turn files instead of `mic_01` + `sys_01`.
- Addition (Zaven, 2026-11-05, S3, F1–F6):
  - **F1** (E1) `Segmenter` takes an optional `session_start`. On its first chunk it sets offset = arrival − one window (32 ms) − `session_start`; `start` / `end` = sample index / 16 000 + offset; `end_wall` unchanged. Without `session_start` the offset is 0 (the clock starts at that Segmenter's first sample, as before); the T1.1 file tests and the diagnostic scripts keep using that. Alternative: required argument (rejected: changes the diag scripts for no gain).
  - **F2** (E2, E3) new `Capture` class in `audio_capture.py`: one thread per input, named `capture-<device>`, each running `run_capture`. A thread that ends normally sets the wake event only when every thread has ended (E2); an error is stored and sets it at once (E3). `stop()` stops every source and joins every thread. The same device given twice → `CaptureError` (D11). Why: the two-device paths are tested with stubs now, while the app still refuses `--system` (E4). Alternative: the loop inside `app.py` (rejected: E2 / E3 untested until S6).
  - **F3** `app.py`: inputs in the order mic, system; one `SileroVad` per input and one shared id counter; `session_start` is taken just before the Segmenters are made and `Capture.start()`; shutdown = `capture.stop()`, then `pipeline.close()`. Exit codes unchanged.
  - **F4** one ready line: `listening on mic: <name>, system: <name> — …` / `playing mic: <file>, system: <file> at real-time speed — …`.
  - **F5** E4 unchanged; the refusal message now says the system input is refused until the diarizer is connected (step S6).
  - **F6** docstrings: file mode ends when every file has ended.
  - **F7** (E3): when a device is lost, its own unfinished segment is dropped (not flushed); the other device's open segment is still drained. (Zaven, 2026-11-05)
  - **F8** `ParecSource.stop()` and the start of `parec` share a lock; a stop that comes before `parec` has started means `parec` never starts. Why: T6 `test_unknown_stdin_command_keeps_running` hung (`command_outputs/m5_s3_pytest.txt`): `quit` came before `parec` had started, so `parec` started afterwards and was read forever. The race was already there before S3; it was hit now, probably because the app process is larger since D30 and starting `parec` takes longer. T1.1 adds a test for it.
  - Tests: T1.1 gets stub-based checks for F1 (offset, no offset), the shared id counter, E2, E3 and F2's thread names / duplicate device; T6 gets "`--system-wav` still refused" (replaced in S6) and "file mode, mic only, ends by itself with exit 0". TEST.md wording is agreed after the run.
- Addition (Zaven, 2026-11-05, S4, J1–J9): speaker-embedding model.
  - **J1** `sherpa-onnx==1.13.8` in `requirements.in` (pulls in `sherpa-onnx-core==1.13.8`; no torch; CPU wheels). Last 1.x with Python 3.10 wheels; 2.0.x not used (new major version; no 3.10 Linux wheel seen for 2.0.1). Installed without problems; onnxruntime 1.23.2 (Silero) and sherpa-onnx load in one process (`command_outputs/m6_s4_compile.txt`, `m6_s4_install.txt`, `m6_s4_import.txt`).
  - **J2** model from Hugging Face `csukuangfj/speaker-embedding-models` (the sherpa-onnx maintainer's copy of the release files) at revision `0743f301363dec56491a490f6d6cbc9d67f9a3bf`, fetched by `scripts/download_models.py` into `models/speaker-embedding/` and checked against its SHA-256 (fails loudly on a mismatch). Licence: WeSpeaker pretrained models follow their dataset's licence; VoxCeleb = **CC-BY 4.0** (for the README).
  - **J3** CPU, 1 thread (ASR keeps the GPU).
  - **J4** stop rules (no build from source, no torch or other heavy package, install and import must work); the 30-minute time-box was dropped (Zaven). None was hit.
  - **J5** `scripts/diag_embed.py --model <file>`: real Silero + Segmenter (7 s cap) on `mic_01`–`03` and `sys_01`; prints time per embedding, RSS, pair similarities, a centroid check per speech-length bucket and a threshold table (mic only).
  - **J7 Model: WeSpeaker ResNet34** (`wespeaker_en_voxceleb_resnet34.onnx`, 26 534 365 bytes, SHA-256 `5ef208a9da1453335308a6b6f4e6dfbd7e183a38b604de0a57664f45d257fe94`, embedding size 256). Results (`command_outputs/m6_s4_embed_resnet34.txt`): 47/47 segments embedded; 235 ms median, 241 ms max per embedding (1 thread); model +74 MB RSS (script peak 218 MB). mic: nearest centroid wrong 0/31; segments ≥ 2 s: same-speaker pairs min 0.729, different-speaker pairs max 0.758; at threshold 0.75: 30/31 join their own speaker, 31/31 stay out of the other. sys_01 (report only, R13): wrong 0/16, smallest margin on a long segment 0.018.
    - **CAM++ rejected** (`wespeaker_en_voxceleb_CAM++.onnx`, `command_outputs/m6_s4_embed_campplus.txt`): about 3× faster (82 ms median) and +50 MB, but nearest centroid wrong 4/31 on mic and 5/16 on sys_01; same- and different-speaker similarities overlap almost completely (segments ≥ 2 s: same min 0.422, different max 0.916). Removed from `download_models.py`.
    - Note for S5: on sys_01 (one recording, two speakers) different-speaker similarity is much higher (centroid "other" 0.57–0.85) than between the three separate mic recordings (0.38–0.73), so a threshold tuned on the mic clips may sit close to the different-speaker range of a real call. T1.6 shows the effect; sys_01 is still not tuned on (R13).
  - **J8 Short-segment length: 2.0 s of speech** (end − start; replaces "about 1 s" in "M6 clustering (S5)" above), for the S5 rule above (a short segment joins the nearest existing speaker, never creates a speaker, never updates a centroid). Why: every mic segment ≥ 2 s scored ≥ 0.846 against its own speaker's centroid; below 2 s the scores were 0.53–0.87 (4 segments), close to the threshold range. Stability is preferred over catching a new speaker's very short turns (Zaven). Cost: a new speaker whose first turns are all < 2 s is put into an existing speaker until they say something longer. Alternative: 1.0 s (rejected: more segments allowed to create a speaker, near the threshold).
  - **J9** records: this addition, D16, section 3, TEST.md results row.
- Addition (Zaven, 2026-11-05, S5, K1–K8 and changes): diarizer.
  - **K1** `src/arm_en_asr/diarizer.py` in three parts: `SpeakerClusters(threshold, short_s=2.0)` = the clustering rules only (plain numpy, no model; tested on made-up vectors); `Embedder(model_path, num_threads=1)` = sherpa-onnx extractor on the CPU, `embed(audio)` → unit vector or `None` ("not ready"); `Diarizer(model_path, threshold=THRESHOLD)` = both, `label(segment)` → "Speaker N" (pipeline G3). A missing model → `DiarizerError("model missing: …")`, no download (D15). No lock: only the pipeline's diarizer thread calls `label()`.
  - **K2** rules (D27 "M6 clustering", J8): embeddings L2-normalised, score = cosine with a speaker's centroid (normalised mean of its long-segment embeddings); speech length = `end − start`. Long (≥ 2.0 s): best score ≥ threshold → joins and updates that centroid, else a new "Speaker N" (numbered in order of appearance). Short (< 2.0 s): joins the nearest centroid, no threshold; never creates a speaker (except Speaker 1 when none exists), never updates a centroid.
  - **K3 (a) option B** (Zaven; replaces his first K3 a rule): Speaker 1 created by short or not-ready segments has no centroid; until it has one, short segments join it and the first long segment joins it **with no check** and starts its centroid. The first rule (compare the first long segment with the average of the short ones; plus a no-reference fallback) made `mic_01` (first segment 1.25 s) split into 2 speakers for every threshold above 0.71 (`command_outputs/m6_s5_tune_sys01.txt`), so no threshold suited both the mic clips and `sys_01`. Known limitation L13.
  - **K3 (b)** (Zaven): a segment sherpa-onnx cannot embed ("not ready") gets the last assigned speaker, or Speaker 1 if there is none; counted. 0 such segments on the eval clips.
  - **K4** `scripts/tune_diarizer.py`: embeds every segment once (real Silero + Segmenter, 7 s cap), then replays `SpeakerClusters` for thresholds 0.50–0.90 (step 0.01) on each mic clip alone (expect 1 speaker), `mic_01` → `02` → `03` in a row and taking turns one segment each (expect 3). Choice rule fixed before the run: middle of the widest unbroken passing range. Result (first K3 a rule): 0.60–0.71 → **0.655** (`command_outputs/m6_s5_tune.txt`).
  - **T1.6 with 0.655:** solo mic clips passed; `sys_01` was merged into 1 speaker, 9/16 correct (56 %) (`command_outputs/m6_s5_pytest.txt`, `m6_s5_t16.txt`). Cause (as noted after S4): two people on one recording score much closer (Speaker 2's first segment: 0.729 against Speaker 1) than three readers on separate recordings.
  - **Change (Zaven): the threshold is tuned on `sys_01` too.** This replaces "Threshold tuned on `mic_01`–`03` only … `sys_01` is used for testing only" in "M6 clustering (S5)" above. `tune_diarizer.py --sys01` prints `sys_01`'s speakers found and % correct per threshold, and the range where the mic rules pass **and** `sys_01` finds 2 speakers (printing only; the threshold is chosen together). With option B: that range is **0.72–0.80** (`sys_01` 100 % correct there; mic rules pass 0.60–0.83) → **`THRESHOLD` = 0.76** (Zaven) (`command_outputs/m6_s5_tune_sys01_b.txt`). The mic-only rule with option B would give 0.715, which still merges `sys_01`.
  - **Consequences:** `sys_01` is no longer an independent check (its T1.6 result is 100 % by construction); the margin is 0.04 on each side; taking turns on the mic clips is 96.8 % correct (one segment: the option B case, L13). **No second 2-speaker clip will be made** (Zaven), so the diarizer has no untouched check (R13, L14).
  - **K5–K8:** `THRESHOLD` set from the tuning run; `tests/test_diarizer.py` (default suite: rules on made-up vectors, constants, missing model, real `Embedder` / `Diarizer` on `speech_short.wav`; `eval`: T1.6); files and order as proposed. Results with 0.76: 60 tests pass (`command_outputs/m6_s5b_pytest.txt`); T1.6: `mic_01`–`03` 1 speaker each, `sys_01` 16/16, 2 speakers, short segments 3/3 (`command_outputs/m6_s5b_t16.txt`).
- Addition (Zaven, 2026-11-05, S6, H1–H7): the app connects the real diarizer.
  - **H1** `app.py` builds `Diarizer(MODELS_DIR / SPEAKER_MODEL)` (default `THRESHOLD` 0.76) only when a system input is given and passes it to `Pipeline(…, diarizer=…)`; a mic-only run has no diarizer (no RAM, no thread). `DiarizerError` → `ERROR: …`, exit 1.
  - **H2** the `--system` / `--system-wav` refusal (E4 / F5 in `app.py`) is removed. E4 stays in `Pipeline`: a system segment without a diarizer is refused.
  - **H3** `check_models()` checks the speaker-embedding model **always**, also without a system input (Zaven), so every run needs the same complete install. The path is a constant in `app.py` (`SPEAKER_MODEL`), so the early checks and `--list-devices` do not import sherpa-onnx; a T6 test checks it equals `diarizer.MODEL_FILE`. Alternative: only with a system input (rejected).
  - **H4** no diarizer warm-up: in S4 the model's very first call took 37.5 ms for 1 s of audio, the same rate as later calls (~35 ms per second of audio; `command_outputs/m6_s4_embed_resnet34.txt`), and the diarizer runs beside ASR. A warm-up, if ever added, must call `embed()` only, never `label()` (that would create Speaker 1 from silence).
  - **H5** T6: `test_system_wav_still_refused` replaced by `test_system_wav_run_accepted` (0.5 s silent mic WAV + committed fixture `speech_short.wav` as system → exit 0, a `Speaker 1:` line, no `Me:` line, last message `stopped`; no eval data, D22); `test_missing_model` also checks the speaker model is named; new `test_speaker_model_path_matches_diarizer`.
  - **H6** files: `app.py`, `tests/test_cli.py`.
  - **H7** results: 61 tests pass, T6 8/8 (`command_outputs/m6_s6_pytest.txt`). `python app.py --system-wav eval/clips/sys_01.wav` under `/usr/bin/time -v` (`command_outputs/m6_s6_sys01.txt`; Zoom tab not confirmed): 16 lines, labels the same as T1.6 (16/16, 2 speakers); latency median ≈ 1.4 s, max 5.2 s, 2 lines > 5 s (`[00:01:10]`, cut by the token cap, and `[00:01:17]`, which most likely waited behind it, D13), `[00:00:42]` (also cut) 4.8 s; 4/16 cut; peak RSS 1070 MB (not comparable with the earlier 878 MB, which `diag_two_devices.py` measured on the turn files). Not T2 (`sys_01` is non-stop speech). Where the time went on the cut lines is not known; no diagnostic now: S7's T2 on the turn files is the check, and only if it fails do we look into it (Zaven, option A). Also seen: the L11 `�` before ` ...` (`[00:00:14]`).
- Addition (Zaven, 2026-11-05, S7a): T2 on the turn files with the real diarizer: `/usr/bin/time -v python app.py --mic-wav eval/clips/turns_mic.wav --system-wav eval/clips/turns_sys.wav`, `free -m` before and after (`command_outputs/m6_s7_t2_turns.txt`; Zoom tab open, plugged in). **Passed:** 28 lines (Me 12, Speaker 1 9, Speaker 2 7), latency median 1.3 s, p95 1.6 s, max 1.6 s, 0 > 5 s; 1/28 cut by the token cap; mic lines only "Me", system lines Speaker 1 / 2 in the order of the `sys_01` parts (report only, L14); peak RSS 1079 MB; RAM available 3270 → 2764 MB; swap 2034 → 2047 of 2047 MB (full; R17). The earlier app-path run without the diarizer (D30) had max 1.8 s. The L11 `�` note stays out of L11 (Zaven).

**D28 — ASR concurrency: N = 1 worker, `cpu_threads` 4 (unchanged).** (Zaven, 2026-11-04)
- What: the app keeps `N_ASR_WORKERS = 1` and `CPU_THREADS = 4` (D1, D3 A1).
- Why (M5 S2, `command_outputs/m5_s2_two_devices.txt`): N = 2 finishes the same work in about the same time (run 101 s / 94 s vs 106 s with N = 1), because both workers share the same CPU; it costs about 180–210 MB more RAM (peak RSS 1059 / 1087 MB vs 877 MB) and swap grew by 183 MB (n2t4) and 78 MB (n2t2), against 0 MB with N = 1 (T4 allows ≤ 100 MB).
- Alternatives: N = 2 with 4 threads (rejected: no gain, swap growth over the T4 limit); N = 2 with 2 threads (rejected: max 18.2 s instead of 23.0 s on the overlap case, still far over 5 s, more RAM and swap growth).
- The full T4 load test (D2) is still postponed; D28 is based on the S2 measurement only.

**D29 — Latency fix for M5: Whisper small on the MX550 GPU (Option 2, M7 GPU work brought forward).** (Zaven, 2026-11-05)
- Why: the turn-taking re-run with repetition_penalty 1.1 + warm-up still had 3/28 lines at 5.1–5.9 s, all dense mic segments, no backlog (`command_outputs/m5_turns_n1t4_rp.txt`).
- Steps, measuring before any app change:
  - **G0** check `ctranslate2` sees the GPU.
  - **G1** separate measuring env `.venv-gpu` from `requirements-gpu.in` (= `requirements.txt` + `nvidia-cublas-cu12` + `nvidia-cudnn-cu12==9.*`), `LD_LIBRARY_PATH` set before Python starts; `.venv` unchanged.
  - **G2** `diag_asr.py --device / --compute-type` (default CPU int8), app settings g+b+c+d1, 7 s cap, mic_01–03, `int8_float16` and `float16`: ASR time, CER, loops, RSS, VRAM.
  - **G3** `diag_two_devices.py --asr-device`, turn test in demo conditions, pass = every line ≤ 5 s and swap growth ≤ 100 MB.
  - **G4** new D# on device choice and library loading, then M5 S3.
- No runtime fallback between GPU and CPU (D7, working rule 2).
- No time-box (Zaven, 2026-11-05); the three-strikes rule applies.
- Alternatives: Option 1, shorter segments (more mid-word cuts, L4, and possibly worse CER); Option 3, accept the misses (breaks the only hard rule).
- Addition (Zaven, 2026-11-05): G0 done: ctranslate2 4.8.4 sees 1 CUDA device; supported `int8_float16`, `float16`, `int8`, `int8_float32`, `float32`; VRAM 5 / 2048 MiB in use (`command_outputs/m5_gpu_check.txt`).
- Addition (Zaven, 2026-11-05): G2 result (`command_outputs/m5_g2_diag_asr_gpu.txt`, `m5_g2_diag_asr_cpu.txt`; same session, `.venv-gpu`, mic_01–03, 7 s cap, g+b+c+d1). GPU `int8_float16`: total ASR 22.8 s, max 1.0 s per segment, encoder 0.35 s, loops 3/31, CER 45.0 / 26.7 / 31.9 %, RSS 715 MB, VRAM 420 MB. GPU `float16`: 61.4 s, max 2.6 s, encoder 0.98 s, loops 5/31, CER 49.7 / 38.1 / 34.9 %, VRAM 708 MB. CPU `int8`: 113.2 s, max 4.7 s, encoder 2.0–2.3 s, loops 3/31, CER 46.7 / 24.8 / 31.1 %, RSS 652 MB. Swap +0 MB in all three. **`int8_float16` is used for G3**; `float16` rejected (slower, more loops, worse CER, more VRAM).
- Addition (Zaven, 2026-11-05): G3 passed (`command_outputs/m5_g3_turns_gpu.txt`; Zoom tab open, plugged in): turn files, N = 1, ASR cuda `int8_float16`: 28 lines, median 1.2 s, p95 1.5 s, max 1.5 s, 0 > 5 s (CPU: max 5.9 s, 3 > 5 s), 1/28 cut (CPU 4/28), peak RSS 729 MB (CPU 881 MB), swap +0 MB, VRAM 420 MB.

**D30 — App ASR on the MX550 GPU; one environment; CUDA libraries loaded in-process (D29 G4).** (Zaven, 2026-11-05)
- Why: D29 G2 / G3: on the GPU (`int8_float16`) ASR is about 5× faster with the same loops and CER; the turn test max latency fell from 5.9 s (CPU) to 1.5 s.
- **G4a** ASR always runs on the GPU: `asr.py` `DEVICE = "cuda"`, `COMPUTE_TYPE = "int8_float16"` (was `"cpu"` / `"int8"`); no app CLI option. No GPU → `AsrError` ("GPU required (D30): ctranslate2 sees no CUDA device"); never a CPU fallback (D7, working rule 2). The diagnostic scripts keep `--device` / `--asr-device` for measuring. Alternative: app option `--asr-device cpu|cuda` (rejected: a second setup that is known to break 5 s).
- **G4b** One environment again: `nvidia-cublas-cu12==12.9.3.13` and `nvidia-cudnn-cu12==9.28.0.42` (the versions G1 resolved) move into `requirements.in`; `requirements.txt` is regenerated; `.venv` gets the libraries; `requirements-gpu.in/.txt` and `.venv-gpu` are removed. App, tests and diagnostic scripts all run in `.venv`.
- **G4c** CUDA libraries load in-process: before Whisper loads, `asr.py` loads the cuBLAS / cuDNN / nvrtc libraries from the installed NVIDIA packages with `ctypes` (`RTLD_GLOBAL`), so neither `python app.py` nor pytest needs `LD_LIBRARY_PATH` (an export must be set before Python starts, and the tests call `app.main()` inside pytest). A missing library → `AsrError` naming it. Alternative: Zaven exports `LD_LIBRARY_PATH` (README note): the fallback *decision* if G4c fails, never a runtime fallback.
  - Checked (2026-11-05, `command_outputs/m5_g4_preload.txt`): with `LD_LIBRARY_PATH` unset, all 16 libraries loaded and Whisper transcribed 5 s of mic_01 on cuda `int8_float16` ("PRELOAD OK").
- **G4d** MT (opus-mt) and VAD (Silero) stay on the CPU.
- **G4e** Tests: T1.2 adds "`Asr` loads on cuda `int8_float16`"; T1.2 and T6 then need the GPU and fail loudly without it (D22). Exact TEST.md wording comes with the code.
- **G4f** Records: D7 addition, R18 resolved, R1 mitigation with the G3 numbers.

**D31 — ASR model: NVIDIA Armenian FastConformer, CTC head, greedy decoding, on the MX550 GPU (brought into scope from section 6).** (Zaven, 2026-11-05)
- What: replace Whisper small with `nvidia/stt_hy_fastconformer_hybrid_large_pc` (D4), CTC head, greedy decoding. We export it to ONNX ourselves in a separate one-time env `.venv-nemo`; third-party ONNX exports stay rejected (D4, D23). It runs with **sherpa-onnx**'s NeMo CTC recognizer (feature extraction + greedy CTC decoding in the package) on the **GPU** (`provider="cuda"`), CUDA build `1.13.8+cuda12.cudnn9` (wheel `sherpa_onnx-1.13.8+cuda12.cudnn9.onnxruntime1.28.2-cp310-cp310-linux_x86_64.whl` from the sherpa-onnx wheel page, not PyPI). fp32 and int8 are both measured. Measured on our clips only (`mic_01`–`03`, `sys_01`), not FLEURS: the model was trained on FLEURS (D4 caveat). The app keeps Whisper small until FastConformer is measured and the switch is agreed; no runtime fallback between models or between GPU and CPU (D7, working rule 2).
- Why: Whisper's decoder loops (L11; 2–7 of 47 segments in `command_outputs/m7_beam_sweep.txt`); CTC cannot loop and its cost grows with audio length only (D25).
- Model (model card): ~115M parameters, CC-BY-4.0, 16 kHz mono, SentencePiece 1024 tokens, FLEURS WER 13.2 % (CTC), NeMo 2.0.0.
- Beam sweep: stage B (turn test) is not run; `m7_beam_sweep.txt` stays as the Whisper record for the bake-off.
- Alternatives: Whisper small beam 3 (loops 2/47, mean CER 31.9 %, max ASR 1.4 s; not chosen: still loops); runtime plain onnxruntime + own mel features (rejected: must match NeMo's preprocessor exactly, more code, risk of silent accuracy loss); CPU (not chosen, Zaven); export inside `.venv-convert` (rejected: NeMo and its dependencies could break the proven opus-mt env, D23).
- Steps (each reviewed and committed on its own):
  - **F0** records: this D#, section 3, section 6, D25 addition.
  - **F1** `.venv-nemo` from `requirements-nemo.in`: `nemo_toolkit[asr]` 2.x + CPU-only torch; export runs on the CPU, once. Stop rules as D27 J4 (no build from source, no install / import problems).
  - **F2** `scripts/download_models.py` fetches the `.nemo` at a pinned revision with SHA-256 and calls the export script (D15 pattern); output in `models/fastconformer-hy-ctc/`.
  - **F3** `scripts/export_fastconformer.py` (in `.venv-nemo`): CTC head → `model.onnx`, `tokens.txt` (`<blk>` last), sherpa-onnx metadata, plus `model.int8.onnx`.
  - **F4** GPU check in a separate measuring env `.venv-fc` (= `requirements.txt` with sherpa-onnx swapped for the CUDA build; `.venv` unchanged until F6, as D29 G1): sherpa-onnx loads with `provider="cuda"`; Silero's onnxruntime 1.23.2 and sherpa's bundled 1.28.2 load in one process; the diarizer on the CPU gives the same T1.6 result. Open risk: onnxruntime CUDA may need more NVIDIA libraries than the three loaded today (D30 G4c).
  - **F5** `scripts/diag_fastconformer.py` in `.venv-fc`, demo conditions (Zoom tab open, plugged in): same segments (7 s cap) and CER clean-up as `diag_asr.py`, on `mic_01`–`03` + `sys_01`; fp32 and int8: ASR time per segment (median / max), CER per clip, RSS, VRAM, swap. Expected: int8 on the GPU may be slower than fp32 (limited CUDA int8 kernels).
  - **F6** Zaven decides; a new D# covers the `asr.py` change, merging the CUDA sherpa-onnx into `requirements.in` (`--find-links`), and what happens to the token cap and ` ...` marker (L11), which CTC does not need.
- Addition (Zaven, 2026-11-05): **stopped** before F1; nothing was installed or built. FastConformer goes back to Future ideas (section 6). ASR stays Whisper small, now with beam 5 (D32).
- Addition (Zaven, 2026-11-06): **resumed** from F1, steps F1–F6 unchanged. Whisper small with beam 5 (D32) stays the app ASR until F6. F1 files agreed: `requirements-nemo.in` (`nemo_toolkit[asr]>=2.0,<3`, `torch>=2.14,<2.15` CPU, `onnx`, `onnxruntime`) → `requirements-nemo.txt` by `uv pip compile --torch-backend cpu`; `.venv-nemo/` gitignored. If no NeMo 2.x fits Python 3.10 + torch 2.14, that is a stop rule (J4) and Zaven decides.
- Addition (Zaven, 2026-11-06): **F1 done:** `.venv-nemo`, 190 packages: nemo-toolkit 2.7.3, torch 2.14.1+cpu, onnx 1.22.0, onnxruntime 1.23.2; import OK, no CUDA (`command_outputs/m7_f1_compile.txt`, `m7_f1_install.txt`, `m7_f1_import.txt`). 4 pure-Python source archives built (antlr4-python3-runtime, kaldi-python-io, wget, sox); accepted under J4 (Zaven). `cuda-bindings` 13.4.4 came in as a NeMo dependency; unused (CPU torch).
- Addition (Zaven, 2026-11-06): **F2 / F3 split** (changes F2 above): F2 only downloads and checks the `.nemo` (`nvidia/stt_hy_fastconformer_hybrid_large_pc` at revision `353b40909f02cf5b74a577294822d8c73fbb1ca1`, `stt_hy_fastconformer_hybrid_large_pc.nemo`, 459 243 520 bytes, SHA-256 `30fac7407cbdff02f77564c11139dd861e933364850d8c60a27c2843d119fdf7`) into `models/src/fastconformer-hy/`; F3 adds the export call to `download_models.py` together with `export_fastconformer.py`, so each step runs on its own.
- Addition (Zaven, 2026-11-06): **F2 done:** `.nemo` downloaded and checked, 459 243 520 bytes, SHA-256 OK (`command_outputs/m7_f2_download.txt`).
- Addition (Zaven, 2026-11-06): **F3 agreed (E1–E9):** `scripts/export_fastconformer.py` (runs in `.venv-nemo`): E1 writes `<out>.part`, renamed at the end; refuses an existing `<out>`; offline. E2 `ASRModel.restore_from` on the CPU; must be the hybrid RNNT+CTC BPE class. E3 reads sample rate (must be 16 000), features, `normalize`, subsampling factor from the model config. E4 exports the CTC head only (`set_export_config({"decoder_type": "ctc"})`); ONNX output size = vocabulary + 1. E5 `tokens.txt`, `<blk>` last. E6 metadata `vocab_size`, `normalize_type`, `subsampling_factor` (from E3) + `model_type`, `version`, `url`, `comment`. E7 `model.int8.onnx` by `quantize_dynamic` (QUInt8). E8 self-check on `speech_short.wav`: fp32 ONNX text must equal NeMo's own CTC output (else fail); int8 text + CER vs fp32 reported. E9 sizes, SHA-256, time, peak RSS. `download_models.py` `export_fastconformer()` runs it (`convert_opus` pattern) into `models/fastconformer-hy-ctc/`.
- Addition (Zaven, 2026-11-06): **F3 done:** `models/fastconformer-hy-ctc/`: `model.onnx` 458 161 306 bytes (SHA-256 `00df8494b96b15536018254a90af1e1173b5bad9c6de4a152467cbc610036dfb`), `model.int8.onnx` 131 652 696 bytes (`8be35ea8859604738ac2c4f9dcfc84a7b648acae085984c6a784dec45ac4c65a`), `tokens.txt` 1025 lines (`221b1dd978a2d8f4fe8a8e185e400c09f98d71c887de9099cb2f1154d321416b`). Metadata: vocab_size 1025, normalize_type per_feature, subsampling_factor 8. E8: NeMo = ONNX fp32 = ONNX int8 text on `speech_short.wav` (int8 vs fp32 CER 0.0 %); CPU 0.14 s (fp32) / 0.07 s (int8) for 4.7 s. Peak RSS 3186 MB, 17 s. The int8 step's "unsupported type to quantize" warnings are int64 shape tensors, skipped on purpose (`command_outputs/m7_f3_export.txt`).
- Addition (Zaven, 2026-11-06): **F4 files agreed:** `requirements-fc.in` (= `requirements.in` with `sherpa-onnx==1.13.8+cuda12.cudnn9.onnxruntime1.28.2` via `--find-links`, plus `nvidia-cuda-runtime-cu12`, `nvidia-cufft-cu12`, `nvidia-curand-cu12`, which onnxruntime's CUDA provider needs); `.venv-fc/` gitignored; `scripts/check_fc_gpu.py` C1–C6: C1 CUDA libraries the app's way + cudart / cuFFT / cuRAND; C2 `ldd` on the CUDA provider library, no "not found"; C3 Silero (onnxruntime 1.23.2) + sherpa-onnx (1.28.2) in one process; C4 `from_nemo_ctc(provider="cuda")` fp32 + int8 on `speech_short.wav`: text, CER vs E8 (reported), first call + median of 5; C5 no silent CPU fallback: this process's VRAM must be > 0; C6 RSS, VRAM. Then T1.6 (default + `eval`) in `.venv-fc`: same result expected.
- Addition (Zaven, 2026-11-06): **F4 done.** `.venv-fc` from `requirements-fc.txt` (43 packages; sherpa-onnx `1.13.8+cuda12.cudnn9.onnxruntime1.28.2` from `--find-links`, no `sherpa-onnx-core`; added nvidia-cuda-runtime-cu12 12.9.79, -cufft-cu12 11.4.1.4, -curand-cu12 10.3.10.19, and -nvjitlink-cu12 12.9.86 via cuFFT).
  - `requirements-fc.txt` is compiled with **`--emit-find-links`**. Without it, `uv pip compile` leaves out the `--find-links` line, so the install cannot find the CUDA wheel (`command_outputs/m7_f4_install.txt`). The same applies to `requirements.txt` in F6.
  - **The first `check_fc_gpu.py` run crashed** with a segmentation fault in `from_nemo_ctc(provider="cuda")` after Silero had run (onnxruntime 1.23.2). Without onnxruntime 1.23.2 in the process, the CUDA recognizer worked. With the CUDA recognizer created first, Silero and a second CUDA recognizer worked too. Result: order rule D33 (`m7_f4c_check.txt`, `m7_f4c_sherpa_cuda.txt`, `m7_f4d_order.txt`). `check_fc_gpu.py` gets step R: both recognizers are created before Silero, with the D33 guard. C5 is stricter: each recognizer's creation must raise the process's VRAM.
  - **Result** (`m7_f4e_check.txt`, `CHECK OK`): C1–C3 OK (CUDA provider: 0 libraries not found). fp32: load 1.2 s, +580 MB VRAM, median 0.023 s for the 4.68 s fixture. int8: load 0.8 s, +76 MB VRAM, median 0.131 s. Both give exactly the E8 text (CER 0.0 %). End: VRAM 742 MB, RSS 1236 MB.
  - **Note:** int8 on the GPU is slower than fp32 and than int8 on the CPU (F3: 0.07 s), and adds little VRAM. Its quantized operations most likely run on the CPU inside onnxruntime (placement is per operation; C5 cannot see it). F5 measures both.
  - **T1.6 in `.venv-fc`:** the same as before: 19 default diarizer tests pass; `mic_01`–`03` 1 speaker each; `sys_01` 16/16, 2 speakers, short segments 3/3 (`m7_f4b_diarizer.txt`, `m7_f4b_t16.txt`).
- Addition (Zaven, 2026-11-06): **F5 done** (`command_outputs/m7_f5_diag_fc.txt`; `diag_fastconformer.py`, cuda, num_threads 1, Zoom tab open, plugged in). Same 47 segments as `m7_beam_sweep.txt` (7 s cap), same CER clean-up.
  - **fp32:** total ASR 3.65 s, median 0.100 s, max 0.118 s per segment; CER `mic_01` 8.2 %, `mic_02` 5.0 %, `mic_03` 6.9 %, `sys_01` 17.4 %, mean 9.4 %; 0 empty.
  - **int8:** total 6.77 s, median 0.180 s, max 0.186 s; CER 8.3 / 4.9 / 6.9 / 17.2 %, mean 9.3 %; 0 empty.
  - **Compared with Whisper small beam 5** (the app setting, D32): mean CER 32.4 % → 9.4 %, max ASR 1.6 s → 0.118 s, total 47.1 s → 3.65 s, no loops possible (D25).
  - **Memory:** VRAM +582 MB (fp32) and +74 MB (int8) at load; the process ended at 1178 MB after the fp32 runs and 1382 MB after int8 (onnxruntime's GPU memory pool grows during decoding; both models were loaded). RSS 1238–1290 MB; swap full from the start (R17).
  - **int8 rejected for the GPU:** the same CER, about 1.8× slower, and more VRAM. Its quantized operations run on the CPU (F4 note).
  - **Seen:** some segment starts lose their first letters where the 7 s cap cut the word (L4).
  - ASR time only; end-to-end latency (T2) is measured after F6.

**D32 — Whisper small decodes with `beam_size=5` (replaces D26's `beam_size=1`).** (Zaven, 2026-11-05)
- What: `asr.py` `BEAM_SIZE = 5`. Unchanged: `without_timestamps=True`, `temperature=0`, `repetition_penalty` 1.1, the D26 token cap with ` ...`, the 7 s VAD cap, cuda `int8_float16`.
- Why (`command_outputs/m7_beam_sweep.txt`, 47 segments of `mic_01`–`03` + `sys_01`, GPU): mean CER 41.5 % → 32.4 %, loops 7/47 → 2/47; max ASR per segment 1.0 s → 1.6 s, median 0.74 s → 1.09 s.
- Trade-off: beam search sometimes ends early and drops the rest of a segment, with no ` ...` marker because the cap was not hit (beam 5: `mic_01` seg 9, `mic_03` seg 3, about half the usual tokens).
- Alternatives: beam 3 (mean CER 31.9 %, max 1.4 s, loops 2/47; almost the same; not chosen: Zaven chose 5); beam 2 (36.1 %) and beam 1 (41.5 %) rejected: less accurate.
- Check (replaces the sweep's stage B): plain pytest suite (T1.2, T6), then T2 on the turn files in demo conditions; pass = every line ≤ 5 s. TEST.md rows are agreed after the run.
- Notes: no test and nothing in `app.py` refers to the beam size; README line 270 (`beam_size=1`) goes on the postponed S7c list.

**D33 — Two onnxruntime builds in one process: the first sherpa-onnx CUDA recognizer is created before onnxruntime 1.23.2 is imported.** (Zaven, 2026-11-06)
- What: any process that runs Silero (onnxruntime 1.23.2, D8 / D24) and FastConformer on the GPU (the sherpa-onnx CUDA build with its own onnxruntime 1.28.2, D31) creates its **first** CUDA recognizer before `onnxruntime` is imported. After that, Silero and more CUDA recognizers work in any order.
  - Guard (working rule 2): if `"onnxruntime"` is already in `sys.modules` when the first CUDA recognizer is created, stop with an error naming D33. Never a segfault, never a CPU fallback.
  - The rule says "imported" rather than "used". That is stricter than the evidence requires, but it is simple to check.
- Applies to:
  - `scripts/check_fc_gpu.py` (done, F4)
  - `scripts/diag_fastconformer.py` (F5)
  - the app after F6: the FastConformer `Asr` is built, with the guard, before `audio_capture` / Silero is imported. F6 says how `app.py`'s imports and startup order (D11 Q1) change for this.
- Why (F4 diagnosis, `command_outputs/m7_f4c_check.txt`, `m7_f4c_sherpa_cuda.txt`, `m7_f4d_order.txt`):
  - with Silero run first, `from_nemo_ctc(provider="cuda")` crashed (exit 139)
  - without onnxruntime 1.23.2 in the process, it worked
  - with the recognizer first, Silero and a second recognizer (int8) worked

  The most likely cause is that both onnxruntime builds use a provider library with the same file name, and whichever loads first is reused. This is not proven; the rule rests on what was seen.
- Alternatives:
  - Silero through sherpa-onnx's own VAD (not chosen: a VAD rewrite; its segmentation differs from D8, and T1.1 would change)
  - one model in a separate process (rejected: breaks D1)
  - onnxruntime 1.28 for Silero (not possible: 1.23.2 is the last version for Python 3.10, D14)
  - a uv-managed Python 3.11+ (not chosen: a new environment and re-pinning everything)
- Risk: the rule depends on import order. A later change that imports onnxruntime earlier stops loudly at the guard.
- Addition (Zaven, 2026-11-06): the rule holds after the first recognizer is freed: create, free (VRAM 580 → 60 MB), then Silero, then a new recognizer worked, with the E8 text (`command_outputs/m7_f6_prime.txt`). So one created and freed recognizer is enough to set the order (used by `tests/conftest.py`, D34 N4).

**D34 — App ASR: NVIDIA FastConformer CTC, fp32, on the MX550 GPU via sherpa-onnx (D31 F6; replaces Whisper small, D3 / D26 / D32).** (Zaven, 2026-11-06)
- Why (D31 F5, `command_outputs/m7_f5_diag_fc.txt`, same 47 segments): mean CER 32.4 % (Whisper beam 5) → 9.4 %, max ASR per segment 1.6 s → 0.118 s, and CTC cannot loop (D25).
- **N1 Model:** `models/fastconformer-hy-ctc/model.onnx` + `tokens.txt` (F3), fp32, `provider="cuda"`, `num_threads=1`, greedy CTC. int8 is not used (F5).
- **N2 `asr.py`:** same interface: `Asr(model_dir, num_workers=1)`, `transcribe(audio) -> str` (stripped), `warm_up()` (1 s of silence; the first CUDA call takes 0.2 s against 0.02 s later, F4).
  - A missing `model.onnx` / `tokens.txt` → `AsrError("model missing: …")`.
  - `num_workers` other than 1 → `AsrError` (D28: one recognizer, one worker).
  - `load_cuda_libraries()` also loads cudart, cuFFT and cuRAND (as F4 C1).
- **N3 No silent CPU fallback:** after creating the recognizer, this process's VRAM (nvidia-smi) must have risen, else `AsrError`. No GPU or no nvidia-smi → `AsrError`.
- **N4 D33 in the app:** the guard sits in `Asr` (first CUDA recognizer in the process). `app.py` `run_session` imports `asr`, builds and warms up `Asr` first, and only then imports `audio_capture` and builds the Silero VADs, MT and the diarizer. The D11 Q1 order (checks → models → pipeline → capture) holds; only the order among the models changes. pytest: `tests/conftest.py` creates one `Asr` at session start (before the test files are collected) and frees it at once (D33 addition), so the tests never hold two models on the GPU.
- **N5 Removed** (CTC cannot loop, D25): the token cap, `CUT_MARKER` ` ...`, the beam / temperature / repetition-penalty / compute-type / CPU-thread settings. L11 and the D12 / D26 ` ...` additions are marked as history.
- **N6 Requirements:**
  - `requirements.in` swaps `sherpa-onnx==1.13.8` for the CUDA build via `--find-links`, and adds nvidia-cuda-runtime / cufft / curand-cu12.
  - `requirements.txt` is compiled with `--emit-find-links`.
  - `.venv` is updated with `uv pip sync requirements.txt`, so the CPU `sherpa-onnx-core` is removed rather than left alongside.
  - The diarizer uses the same package on the CPU (T1.6 passed in `.venv-fc`).
  - Afterwards, `requirements-fc.in/.txt` and `.venv-fc` are removed (as D30 G4b).
- **N7 faster-whisper removed** (Zaven): out of `requirements.in`, `app.py`'s model checks and `scripts/download_models.py`. `ctranslate2` stays for MT (D5). `scripts/diag_asr.py` stays as the record of the Whisper measurements, with a docstring note that it now needs faster-whisper 1.2.1 installed by hand. `diag_fastconformer.py` still works: the helpers it imports from `diag_asr.py` do not need faster-whisper. Alternative: keep it installed so `diag_asr.py` runs from the pinned environment (not chosen).
- **N8 Tests:**
  - T1.2: Armenian text on the fixture, model missing, `warm_up`, loads on CUDA with VRAM above 0, and the D33 guard. The guard test runs in a subprocess that imports onnxruntime first and expects `AsrError`.
  - The `token_cap` test is removed.
  - T6: "missing model" names the FastConformer model.
- **N9 VAD cap (D26 7 s):** measured first. `diag_fastconformer.py --seg-cap 7,10,12`, fp32 only, the same mechanism as `diag_asr.py` H2: CER, max ASR, VRAM. Zaven chooses the cap, and T1.1's cap test follows it.
- **N10 Steps:**
  - **F6a** cap measurement
  - **F6b** code (`asr.py`, `app.py`, `conftest.py`, tests, requirements)
  - **F6c** pytest plus T2 on the turn files in demo conditions (pass = every line ≤ 5 s)
  - **F6d** records (L11, D12, D26, TEST.md wording); the README later (S7c)
- **N11 D32 check:** not run. Whisper is no longer the app ASR, so F6c's pytest and T2 replace it.
- Addition (Zaven, 2026-11-06): **F6a done** (`command_outputs/m7_f6a_segcap.txt`; fp32, demo conditions). Caps 7 / 10 / 12 s: 47 / 36 / 32 segments; mean CER 9.4 / 8.5 / 8.7 % (mic_01 8.2 / 7.5 / 6.5, mic_02 5.0 / 5.0 / 5.2, mic_03 6.9 / 6.2 / 6.6, sys_01 17.4 / 15.3 / 16.5 %); max ASR 0.124 / 0.134 / 0.201 s; VRAM 1102 MB for all; the 7 s run repeats F5. **The cap stays 7 s** (D26) for F6: the gain is about 1 point on four clips (R13), and a longer cap would also change the diarizer's segments (`THRESHOLD` fitted at 7 s, L14), MT on longer input (D5, M1) and how often lines appear. The cap goes to M8, where 10 s is the candidate, to be tested with T1.6 and MT. T1.1 is unchanged.
- Addition (Zaven, 2026-11-07): **WER, Whisper vs FastConformer** (`scripts/diag_wer.py`, `.venv-fc`, `command_outputs/m7_wer_whisper_fc.txt`). Same 47 segments (7 s cap), clean-up as G5, words = cleaned text split on spaces; references 498 words / 3316 characters.
  - **Whisper small**, D32 setting (cuda `int8_float16`, beam 5, `repetition_penalty` 1.1, token cap; loops 2/47): WER `mic_01` 85.5 %, `mic_02` 78.7 %, `mic_03` 84.4 %, `sys_01` 87.9 %, pooled 84.5 %, mean 84.1 %; CER 36.0 / 21.0 / 29.4 / 43.3 %, pooled 32.8 %, mean 32.4 %.
  - **FastConformer CTC fp32**: WER 22.1 / 15.7 / 24.0 / 36.9 %, pooled 25.5 %, mean 24.7 %; CER 8.2 / 5.0 / 6.9 / 17.4 %, pooled 9.7 %, mean 9.4 %.
  - The CERs repeat `m7_beam_sweep.txt` and F5. The FastConformer WER repeats `m7_fc_wer.txt` (2026-11-06, inline command).

---

## 10. Milestones (20 h total)

| # | Milestone | Hours | Status |
|---|---|---|---|
| M0 | Planning: questions, DECISIONS.md, TEST.md | 1.5 | ☑ done (2026-10-29) |
| M1 | Environment (uv), `scripts/download_models.py`, smoke-run each model on one Armenian clip, RAM check | 1.5 | ☑ done (2026-10-30) |
| M2 | Eval data v0: Zaven's clips (4, D17) + CSVs; FLEURS subset | 2 | ☑ done (2026-10-31) |
| M3 | Walking skeleton, mic only: `--list-devices`, capture, VAD, ASR, MT, print, `quit`, latency measurement, file mode | 3 | ☑ done (2026-11-01) |
| M4 | Initial tests: unit, end-to-end latency, capture smoke, load test (D2) | 2 | ☐ not done |
| M5 | Second device (system monitor), both devices at once | 1 | ☑ done (2026-11-05) |
| M6 | Diarization (1–2 remote speakers) | 2 | ☑ done (2026-11-05) |
| M7 | Baseline evaluation + ASR/MT bake-off → final model choice | 2 | ☐ not done |
| M8 | Improvement pass on the weakest measured point (incl. segment cap) | 1.5 | ☐ not done |
| M9 | Virtual-sink capture test | 1 | ☐ not done |
| M10 | README, final test run, TEST.md statuses | 1.5 | ☐ not done |
| — | Buffer | 1 | — |

Zaven decides when a milestone overruns. Cut order: M9, then M8.

---

## 11. Risks

| # | Risk | Mitigation | Status |
|---|---|---|---|
| R1 | Latency exceeds 5 s | Build the whole flow early; measure latency on every line (D12); end-to-end latency test; load test (D2). M1 finding (2026-10-30): Whisper small default settings RTF 0.58, so a 12 s segment (D8 cap) needs ≈ 7 s for ASR alone; to be addressed in M4 (T2, T4). M3 S8 finding (2026-11-01): fixed cost ≈ 2.4 s per segment; on mic_01 latency grew to 111 s, so ASR took far longer than RTF 0.58 on several segments; diagnosed first in M4. Latency-fix finding (2026-11-01): with `temperature=0` (D3) max latency on mic_01 fell from 111.1 s to 29.6 s; no swap growth, so not RAM; Whisper repetition loops are the main cause (`command_outputs/m4_file_mic01_temp0.txt`). diag_asr finding (2026-11-01): Whisper small cannot transcribe a full 12 s Armenian segment in ≤ 5 s on this CPU without losing text; FastConformer CTC brought forward (D25). D26 result (2026-11-01): T2 on mic_01 max latency 4.8 s, median 4.1 s; headroom is small (worst lines are cap-cut segments). GPU finding (2026-11-05, D29 / D30): with ASR on the MX550 (cuda `int8_float16`) the turn test had max latency 1.5 s, median 1.2 s, 0/28 lines > 5 s (CPU: max 5.9 s, 3/28) (`command_outputs/m5_g3_turns_gpu.txt`). M6 S7 T2 (2026-11-05, real diarizer, turn files, Zoom tab open, plugged in): max 1.6 s, median 1.3 s, 0/28 lines > 5 s (`command_outputs/m6_s7_t2_turns.txt`). | accepted |
| R2 | Re-deciding the same thing many times | Stable rules and decisions recorded here | accepted |
| R3 | Wrong or big commits | Small commits, proposed by Claude, run only by Zaven | accepted |
| R4 | App does not work on this laptop | Laptop specs collected early (section 2); models sized to RAM | accepted |
| R5 | Poor Armenian ASR quality (low-resource) — highest risk | Measure on eval data before building on top; bake-off (D4) | accepted |
| R6 | ASR errors carry into MT | Measure ASR and MT separately (MT also on FLEURS reference text) | accepted |
| R7 | Whisper hallucinations on silence/noise | VAD gating; filter known hallucination phrases only if measured | accepted |
| R8 | CPU/RAM contention (ASR + MT + diarizer + Zoom) | Load test (D2); small models first | accepted |
| R9 | PulseAudio/PipeWire mismatch | Checked: real PulseAudio 15.99.1; capture via `parec` (D10) | accepted |
| R10 | Speaker bleed / echo into mic → false "Me" lines | **Will not fix** — echo handling is out of scope; headphones are up to the user | will not fix |
| R11 | Live diarization harder than offline; short segments → unstable embeddings | Online clustering; test with solo mic clips (D17). Online clustering + 2.0 s short-segment rule (D27 J8, K2); T1.6 passed (2026-11-05) | accepted |
| R12 | VAD cuts mid-word or waits too long | Tuned parameters (D8); revisit in M8 | accepted |
| R13 | Eval set too small to tell real improvements from noise | Add FLEURS subset (D19); treat small differences carefully. Diarizer threshold tuned on `sys_01`, the only 2-speaker clip (D27 S5); no second clip will be made (Zaven, 2026-11-05), so the diarizer has no untouched check (L14) | accepted |
| R14 | Model download size / disk | 309 GB free; models downloaded once (D15) | accepted |
| R15 | Armenian script renders badly in terminal | Checked in M1: text is correct UTF-8; overlap came from Ubuntu Mono lacking Armenian letters. Fix: terminal font DejaVu Sans Mono (setup note in README, M10) | accepted |
| R16 | Scope creep | Working rule 1; Future ideas section | accepted |
| R17 | RAM: only ~2.4 GB free, swap already used → swapping breaks 5 s | Load test (D2); RAM check in M1; close unneeded apps before demo; light MT first (D5). M6 S7 T2 (2026-11-05): swap was full (2034 → 2047 of 2047 MB) during the run; latency unaffected (max 1.6 s); app peak RSS 1079 MB | accepted |
| R18 | MX550 GPU path costs time (CUDA/cuDNN setup) | CPU first (D7); GPU only in M7, time-boxed to 1 h. GPU work brought forward to M5 (D29); the 1 h time-box is lifted (Zaven, 2026-11-05). Resolved by D29 / D30 (2026-11-05): CUDA libraries from pip, loaded in-process; one wrong library path cost one strike | resolved |
| R19 | 20 h budget overrun | Hours per milestone; Zaven decides cuts; cut order M9 → M8 | accepted |

---

## 12. Known limitations

- **L1 Echo:** with speakers instead of headphones, call audio leaks into the mic and appears as duplicate "Me" lines (out of scope, will not fix).
- **L2 Overlapping speech:** no special handling; text or speaker label may be wrong when people talk at the same time.
- **L3 Code-switching:** Russian/English words inside Armenian speech are processed as-is; models may get them wrong.
- **L4 Segment cap 7 s** (12 s until 2026-11-01, D26): long speech without pauses is cut at 7 s, possibly mid-word.
- **L5 Print order by speech end:** example — Speaker 1 talks 00:10–00:25, Me says something short 00:15–00:17 → the `[00:00:15] Me` line prints *before* `[00:00:10] Speaker 1`, so timestamps appear out of order. Also (agreed 2026-11-01, M3 S7, P3): lines print in the order segments were submitted, i.e. when each segment's end was detected. A segment cut at the 12 s cap is submitted at once, one that ends in silence 0.6 s later, so with two devices (M5 on) two segments that end within 0.6 s of each other can print swapped.
- **L6 Mic is always "Me":** even if another person speaks into the mic.
- **L7 Final lines only:** no partial text while someone is speaking.
- **L8 Remote speakers:** diarization is tuned and tested for 1–2 remote speakers first.
- **L9 Demo assumption:** sized for "browser video call open + laptop plugged in"; other setups not yet verified.
- **L10 Weak MT (opus-mt-hy-en):** the skeleton MT model is a weak point. Even on clean reference Armenian it often gives fluent English with the wrong meaning (e.g. FLEURS «Մարզընկեր ըմբիշները … Լունային» → "I think they're also paying a debt of respect"), and on some inputs (numbers like «6-6», hyphenated words) it can fall into a repetition loop («6-6-6-…-a-a-a-…»). Loop: diagnosed and guarded in M3 S5 (D5). Meaning errors: measured and compared with NLLB in the M7 bake-off.
- **L11 Cut-off lines (` ...`):** with greedy decoding Whisper sometimes keeps repeating (e.g. «եմ եմ եմ …»). The D26 token cap stops it in time, and the Armenian line then ends with ` ...` to show the text was cut; the repeated words before the cut are still printed. On `mic_01`–`03` this happened on 13 of 31 segments. The marker also goes into MT, so the English line may or may not show it.
- **L12 Both sides talking at once** (added 2026-11-04, D27, D28): when the mic and the call audio both carry speech for a long stretch, segments arrive faster than ASR can finish them, lines queue up and latency grows well past 5 s. Measured in M5 S2 on `mic_01` + `sys_01` played together (89 s): max 23.0 s with N = 1. A second ASR worker does not help (D28). Normal conversation, where people take turns, is the case the app is built for.
- **L13 Diarizer: first sound of a session** (added 2026-11-05, D27 S5 K3 a option B): until Speaker 1 has a centroid, its first long segment (≥ 2 s) joins it with no check. If the session's first system sound is short and from a different person than the first long speech (e.g. person A says "yes", then person B talks), A's short sound and B's speech both get Speaker 1, and Speaker 1 becomes B's voice. Seen once on the mic clips (taking-turns order, 1 of 31 segments).
- **L14 Diarizer threshold fitted on one recording** (added 2026-11-05, D27 S5): `THRESHOLD` 0.76 was chosen so that `sys_01`, the only 2-speaker clip, is labelled correctly; it works there only between 0.72 and 0.80. Other calls and voices may get two people merged into one speaker or one person split into two. There is no untouched clip to check it (R13).

---

## 13. Handover template (`handovers/NNN-topic.md`)

```
# Handover NNN — <topic> — <date>
Goal: <what this chat was trying to do>
Current state: <what works, what does not; current milestone>
Decisions made in this chat: <D# list, already copied into DECISIONS.md>
Next step: <the single next concrete action>
Open questions: <if any>
```
