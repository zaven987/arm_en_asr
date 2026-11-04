# DECISIONS.md — Live Armenian → English transcription + translation (local laptop)

> **How to use this file.** This is the single source of truth for the project. It replaces PLAN.md (whose content is extracted and corrected below). Paste this file (plus the latest handover from `handovers/`, if any) into a fresh chat to continue work. Every decision has a number (D#), a reason, and the alternatives we considered. Anything marked **PROPOSED** is not agreed yet and must not be built on until Zaven confirms it.

- Architect / owner: Zaven
- Team: Claude (writes files, proposes commands and commits)
- Created: 2026-10-26 · Last updated: 2026-11-04

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

- **Current milestone:** M5 — second device, then M6 diarizer (Zaven, 2026-11-04). M10: README done (2026-11-01); final test run and TEST.md statuses after M6. M4 tests T3 and T4 postponed (Zaven, 2026-11-01).
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
- **Next step:** turn-taking measurement (`make_turns.py` + `diag_two_devices.py`, D27 addition); pass → M5 S3, fail → decide on the token-cap loops. T3 / T4 later (Zaven, 2026-11-01).
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
- NVIDIA Armenian FastConformer CTC as the ASR model (D25): cannot loop, and its cost does not grow with the number of tokens. Set aside for time on 2026-11-01.

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
- Addition (Zaven, 2026-11-01, D26): `transcribe` now uses `beam_size=1` (replacing A2's 5), `without_timestamps=True`, and the D26 token cap (`max_new_tokens` = 2 × `token_cap(segment seconds)`). When the cap is hit, the text ends with ` ...` (L11).

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
eval/fleurs/              # raw FLEURS files, gitignored (D19; added 2026-10-29)
eval/meta/README.md       # data sources + licences (FLEURS CC-BY 4.0), committed (added 2026-10-30)
DECISIONS.md  TEST.md  README.md  requirements.txt  .gitignore
pytest.ini                # added 2026-10-31: pythonpath = src, markers hardware / slow excluded by default via addopts;
                          #   app.py adds src/ to sys.path itself (no packaging, no pyproject.toml)
requirements.in  requirements-convert.in  requirements-convert.txt     # added 2026-10-29 (D14, D23)
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

**D26 — Latency fix: Whisper small, faster settings + shorter segments (option B).** (Zaven, 2026-11-01)
- What: transcribe with `without_timestamps=True`, `beam_size=1`, `temperature=0`, and a token cap that only stops loops (it must never cut normal speech); the VAD segment cap (D8) is shortened from 12 s. The exact cap values are chosen from one more `diag_asr.py` run and agreed before `asr.py` / `audio_capture.py` change.
- Why: `latency_diag_asr_f.txt`: a full 12 s segment needs ≈ 5.5 s of ASR even with greedy decoding (≈ 1.9 s encoder + ≈ 190 tokens × 17 ms); shorter segments mean fewer tokens per call.
- Trade-offs: more segments cut mid-word (L4; this was M8 work, now pulled forward); greedy decoding has a worse CER than beam 5 (g+b vs g); the 1.9 s encoder cost per segment stays.
- Alternatives: see D25.
- Addition (Zaven, 2026-11-01): values chosen from `command_outputs/latency_diag_asr_segcap.txt` (g+b+c on mic_01–03, segment caps 6 / 7 / 8 s): **VAD segment cap 7 s** (D8). At 7 s: max ASR 4.7 s per segment (6 s: 4.4 s; 8 s: 5.1 s), CER 59.0 / 45.8 / 36.1 % (6 s: 68.5 / 45.6 / 53.5 %; 8 s: 68.4 / 52.2 / 62.9 %). Token cap: allowed tokens = ceil(15.8 tok/s × segment length × 1.5), at most 220, passed as `max_new_tokens` = 2 × that, because CTranslate2 generates at most half of `max_length` (prompt + `max_new_tokens`); this rule fits every measured value (`diag_asr.py` H1). Known cost: 13 of 31 segments hit the cap at 7 s (mostly greedy over-generation such as «եմ եմ եմ …»); their text stops at the cap and what came before is printed. CER is worse than Whisper beam 5 at 12 s (32.5 / 19.5 / 34.5 %), which broke 5 s.
- Addition (Zaven, 2026-11-01): a segment whose text was stopped by the token cap is shown with ` ...` at the end of its Armenian text, so the cut is visible, never silent (working rule 2, L11). Code: `asr.py` (`token_cap`, `CUT_MARKER`); T1.2 tests `token_cap`.

**D27 — M5 + M6 plan: second device, then diarizer.** (Zaven, 2026-11-04)
- Steps (each reviewed and committed on its own):
  - **S1** `pipeline.py`: optional `diarizer`; system segments accepted only when there is one; T1.5 updated.
  - **S2** `scripts/diag_two_devices.py`: `mic_01` + `sys_01` at the same time, real time, real Segmenters / Pipeline / ASR / MT, stub diarizer. Variants: N = 1 / `cpu_threads` 4, N = 2 / 4, N = 2 / 2. Records latency (median / p95 / max, lines > 5 s), peak RSS, swap. Demo conditions, Meet/Zoom tab confirmed. Output `command_outputs/m5_s2_two_devices.txt`. Zaven then chooses N and threads (new D#).
  - **S3** `app.py` + `audio_capture.py`: one VAD, one Segmenter and one capture thread per device (`capture-mic`, `capture-system`), shared id counter; rules E1–E3 below. `--system` still refused (E4).
  - **S4** embedding model choice (see M6 below).
  - **S5** `diarizer.py` + T1.6 (`eval` marker, D22).
  - **S6** app passes the real diarizer; the `--system` refusal is removed; T6 still passes, plus one test that a short `--system-wav` run is accepted and exits 0.
  - **S7** T2 re-run `app.py --mic-wav eval/clips/mic_01.wav --system-wav eval/clips/sys_01.wav`, demo conditions; then statuses, DECISIONS / TEST updates and the README sections listed in handover 010.
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

**D28 — ASR concurrency: N = 1 worker, `cpu_threads` 4 (unchanged).** (Zaven, 2026-11-04)
- What: the app keeps `N_ASR_WORKERS = 1` and `CPU_THREADS = 4` (D1, D3 A1).
- Why (M5 S2, `command_outputs/m5_s2_two_devices.txt`): N = 2 finishes the same work in about the same time (run 101 s / 94 s vs 106 s with N = 1), because both workers share the same CPU; it costs about 180–210 MB more RAM (peak RSS 1059 / 1087 MB vs 877 MB) and swap grew by 183 MB (n2t4) and 78 MB (n2t2), against 0 MB with N = 1 (T4 allows ≤ 100 MB).
- Alternatives: N = 2 with 4 threads (rejected: no gain, swap growth over the T4 limit); N = 2 with 2 threads (rejected: max 18.2 s instead of 23.0 s on the overlap case, still far over 5 s, more RAM and swap growth).
- The full T4 load test (D2) is still postponed; D28 is based on the S2 measurement only.

---

## 10. Milestones (20 h total)

| # | Milestone | Hours | Status |
|---|---|---|---|
| M0 | Planning: questions, DECISIONS.md, TEST.md | 1.5 | ☑ done (2026-10-29) |
| M1 | Environment (uv), `scripts/download_models.py`, smoke-run each model on one Armenian clip, RAM check | 1.5 | ☑ done (2026-10-30) |
| M2 | Eval data v0: Zaven's clips (4, D17) + CSVs; FLEURS subset | 2 | ☑ done (2026-10-31) |
| M3 | Walking skeleton, mic only: `--list-devices`, capture, VAD, ASR, MT, print, `quit`, latency measurement, file mode | 3 | ☑ done (2026-11-01) |
| M4 | Initial tests: unit, end-to-end latency, capture smoke, load test (D2) | 2 | ☐ not done |
| M5 | Second device (system monitor), both devices at once | 1 | ☐ not done |
| M6 | Diarization (1–2 remote speakers) | 2 | ☐ not done |
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
| R1 | Latency exceeds 5 s | Build the whole flow early; measure latency on every line (D12); end-to-end latency test; load test (D2). M1 finding (2026-10-30): Whisper small default settings RTF 0.58, so a 12 s segment (D8 cap) needs ≈ 7 s for ASR alone; to be addressed in M4 (T2, T4). M3 S8 finding (2026-11-01): fixed cost ≈ 2.4 s per segment; on mic_01 latency grew to 111 s, so ASR took far longer than RTF 0.58 on several segments; diagnosed first in M4. Latency-fix finding (2026-11-01): with `temperature=0` (D3) max latency on mic_01 fell from 111.1 s to 29.6 s; no swap growth, so not RAM; Whisper repetition loops are the main cause (`command_outputs/m4_file_mic01_temp0.txt`). diag_asr finding (2026-11-01): Whisper small cannot transcribe a full 12 s Armenian segment in ≤ 5 s on this CPU without losing text; FastConformer CTC brought forward (D25). D26 result (2026-11-01): T2 on mic_01 max latency 4.8 s, median 4.1 s; headroom is small (worst lines are cap-cut segments). | accepted |
| R2 | Re-deciding the same thing many times | Stable rules and decisions recorded here | accepted |
| R3 | Wrong or big commits | Small commits, proposed by Claude, run only by Zaven | accepted |
| R4 | App does not work on this laptop | Laptop specs collected early (section 2); models sized to RAM | accepted |
| R5 | Poor Armenian ASR quality (low-resource) — highest risk | Measure on eval data before building on top; bake-off (D4) | accepted |
| R6 | ASR errors carry into MT | Measure ASR and MT separately (MT also on FLEURS reference text) | accepted |
| R7 | Whisper hallucinations on silence/noise | VAD gating; filter known hallucination phrases only if measured | accepted |
| R8 | CPU/RAM contention (ASR + MT + diarizer + Zoom) | Load test (D2); small models first | accepted |
| R9 | PulseAudio/PipeWire mismatch | Checked: real PulseAudio 15.99.1; capture via `parec` (D10) | accepted |
| R10 | Speaker bleed / echo into mic → false "Me" lines | **Will not fix** — echo handling is out of scope; headphones are up to the user | will not fix |
| R11 | Live diarization harder than offline; short segments → unstable embeddings | Online clustering; test with solo mic clips (D17) | accepted |
| R12 | VAD cuts mid-word or waits too long | Tuned parameters (D8); revisit in M8 | accepted |
| R13 | Eval set too small to tell real improvements from noise | Add FLEURS subset (D19); treat small differences carefully | accepted |
| R14 | Model download size / disk | 309 GB free; models downloaded once (D15) | accepted |
| R15 | Armenian script renders badly in terminal | Checked in M1: text is correct UTF-8; overlap came from Ubuntu Mono lacking Armenian letters. Fix: terminal font DejaVu Sans Mono (setup note in README, M10) | accepted |
| R16 | Scope creep | Working rule 1; Future ideas section | accepted |
| R17 | RAM: only ~2.4 GB free, swap already used → swapping breaks 5 s | Load test (D2); RAM check in M1; close unneeded apps before demo; light MT first (D5) | accepted |
| R18 | MX550 GPU path costs time (CUDA/cuDNN setup) | CPU first (D7); GPU only in M7, time-boxed to 1 h | accepted |
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
