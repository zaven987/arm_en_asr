# DECISIONS.md — Live Armenian → English transcription + translation (local laptop)

> **How to use this file.** This is the single source of truth for the project. It replaces PLAN.md (whose content is extracted and corrected below). Paste this file (plus the latest handover from `handovers/`, if any) into a fresh chat to continue work. Every decision has a number (D#), a reason, and the alternatives we considered. Anything marked **PROPOSED** is not agreed yet and must not be built on until Zaven confirms it.

- Architect / owner: Zaven
- Team: Claude (writes files, proposes commands and commits)
- Created: 2026-10-26 · Last updated: 2026-10-31

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

- **Current milestone:** M3 — Walking skeleton, mic only (in progress).
- **M3 started (2026-10-31):** plan S1–S8 agreed (handover 005). S1 done: `app.py` CLI, device and model checks, `pytest.ini`, T6 part 1 (3 tests pass; `command_outputs/m3_s1_pytest.txt`). sacremoses closed: not used at runtime (opus-mt runs with ctranslate2 + sentencepiece).
- **M2 done (2026-10-31):** reference CSVs written and reviewed: `eval/meta/mic_01`–`03.csv`, `eval/meta/sys_01.csv` (4 clips, D17; verbatim, D18); FLEURS subset `eval/meta/fleurs_hy_am_test100.csv` (D19).
- **Done in M2 (2026-10-30/31):** FLEURS subset built: 100 clips, 19.5 min, 4.7–30.9 s, 36 longer than 12 s (D19; `command_outputs/m2_fleurs_subset.txt`). MMS-1B-all downloaded (revision `3d33597…`) and run by `scripts/draft_mms.py` to draft references (D15, D18; peak RAM 4.8 GB); Zaven corrected the drafts, Claude added English. NVIDIA Armenian FastConformer added to the M7 bake-off (D4).
- **Done in M1 (2026-10-29):** pinned environment installed and verified (`command_outputs/m1_*.txt`); `.venv-convert` built (torch 2.14.1+cpu, transformers 4.57.6); `scripts/download_models.py` run: all models in `models/` (`command_outputs/m1_download.txt`).
- **M1 done (2026-10-30):** smoke run on FLEURS hy_am test id 2009 (14.76 s; `command_outputs/m1_smoke.txt`). All models load offline (faster-whisper works with huggingface-hub 2.3.0). VAD: 82 % of windows speech. ASR (Whisper small, int8, CPU, defaults): RTF 0.58 (8.5 s for 14.76 s), 100 % Armenian letters, CER ≈ 12 %, WER ≈ 56 % (mostly phonetic spelling errors). MT (opus-mt int8): 0.2 s per sentence; on the reference Armenian only the first half is correct. RAM: peak RSS 829 MB (VAD + ASR; the script freed Whisper before loading MT, so all models together ≈ 0.9–1.0 GB, to be measured in T4), 3.5–4.2 GB available, swap growth 0 MB. Armenian renders correctly after switching the terminal font (R15).
- **M0 done (2026-10-29):** questions asked and answered; decisions D1–D22 agreed (incl. D4 BuzzASR time-box); this file and TEST.md (tests T1.1–T1.6, T2–T6, all "not run") written and committed by Zaven; handovers 001 and 002 written.
- **Next step:** M3 — walking skeleton, mic only (see `handovers/005-m2-done-to-m3.md`).
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

---

## 7. Demo assumption (open question)

- Worst case assumed for the demo: **a web browser with a video call (Zoom/Meet) is open, laptop plugged in.** Models must keep latency ≤ 5 s under this load.
- **Open question (revisit after the walking skeleton):** the client's exact setup may differ; if so, we adjust then.

---

## 8. Architecture

Single process, threads + queues. Shared unit = **Segment** `{id, device (mic|system), start, end, audio}`; every stage attaches its result to the segment id.

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

**D2 — Load test.**
- What: feed K simultaneous segments (from eval clips) with N = 1, 2, 3 ASR workers, with a real Meet/Zoom tab open. Record: peak RSS, swap use, per-segment latency (median / p95 / max), throughput (segments per minute).
- Result: the largest N and K that keep RAM within limits and max latency ≤ 5 s → becomes our concurrency setting.
- Pass (agreed 2026-10-29, TEST.md T4): grid N = 1, 2, 3 × K = 1, 2, 4, 6; a combination passes if max latency ≤ 5 s and swap grows ≤ 100 MB during the run.
- Tie-breaker if several combinations pass (agreed 2026-10-29): (1) highest segments processed per minute, (2) highest N, (3) lowest max latency.
- Why: Zaven asked to know how many segments the laptop can process in parallel before hitting RAM limits or degrading latency.

**D3 — Skeleton ASR: `faster-whisper` "small", int8, CPU, language fixed to `hy`.**
- Why: ~0.5 GB RAM, most likely to work for sure (PLAN: "not much advanced on first choices"). Accuracy on Armenian is expected to be weak; that is acceptable for the skeleton.

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

**D6 — Separate ASR + MT. Merged speech→English model rejected.**
- Why: we must show Armenian text anyway, so a single speech→English model is not enough; SeamlessM4T (main merged option) is too large for this laptop.

**D7 — Skeleton runs on CPU.**
- Why: GPU needs CUDA/cuDNN setup (time risk). GPU stays a bake-off option. Device is explicit; requesting GPU when unavailable is an error, never a silent fallback.

**D8 — VAD: Silero VAD (ONNX, MIT).**
- Settings: end of phrase = 0.6 s silence; ignore speech < 0.3 s; **hard cap 12 s per segment**.
- Known trade-off: the 12 s cap may cut mid-word / mid-sentence. Revisit in the quality pass (M8) if time allows.

**D9 — Diarizer: chosen at its milestone (M6).**
- Plan: small speaker-embedding model (WeSpeaker/ECAPA via sherpa-onnx or SpeechBrain, ~25–80 MB) + online clustering (assign to nearest known speaker by cosine similarity, or create a new speaker under a threshold).
- Runs on system-audio segments only. Mic is always "Me". Focus on 1–2 remote speakers first, then more if evaluated.
- Why: lightweight, matches PLAN's VAD + clustering idea; must be online because the app is live.

**D10 — Audio capture: one `parec` subprocess per device, raw s16le 16 kHz mono.**
- `--list-devices` prints `pactl list short sources` (includes `.monitor` sources).
- Why: PulseAudio resamples for us; exact PulseAudio names work directly. `parec` is already installed (pulseaudio-utils).
- Alternatives: `sounddevice`/PortAudio (rejected: does not expose monitor sources by exact name); `soundcard` library (backup).

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

**D12 — Output line shows speaker, start offset (HH:MM:SS), Armenian, English, and measured latency** (format in section 8).
- Latency = time the line is printed − time the speech segment ended.
- Lines whose latency > 5 s get a visible warning.

**D13 — Print order: by when speech ended.** (see Known limitation L5)

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

**D22 — Test fixtures and test policy.** (agreed 2026-10-29)
- What: small fixture files are committed in `tests/fixtures/`: a few seconds of FLEURS hy_am audio (CC-BY 4.0, attribution in `tests/fixtures/README.md`), generated silence, and ≥ 12 s continuous speech. A missing model or fixture makes a test **fail**, never skip. pytest markers: `hardware` (real devices + person present) and `slow` (load test), excluded from a plain `pytest` run.
- Why: tests run from a fresh clone; skipping would be a silent fallback (working rule 2).
- Alternatives: gitignored fixtures like `eval/clips/` (rejected: tests could not run from a fresh clone).
- Addition (agreed 2026-10-31): fixtures are generated by `scripts/make_fixtures.py`: `speech_short.wav` (shortest subset clip, whole), `silence_5s.wav` (zeros), `speech_long.wav` (first subset clip with an unbroken Silero speech run ≥ 13 s, whole); the script writes `tests/fixtures/README.md` (attribution, ids, SHA-256).

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

---

## 10. Milestones (20 h total)

| # | Milestone | Hours | Status |
|---|---|---|---|
| M0 | Planning: questions, DECISIONS.md, TEST.md | 1.5 | ☑ done (2026-10-29) |
| M1 | Environment (uv), `scripts/download_models.py`, smoke-run each model on one Armenian clip, RAM check | 1.5 | ☑ done (2026-10-30) |
| M2 | Eval data v0: Zaven's clips (4, D17) + CSVs; FLEURS subset | 2 | ☑ done (2026-10-31) |
| M3 | Walking skeleton, mic only: `--list-devices`, capture, VAD, ASR, MT, print, `quit`, latency measurement, file mode | 3 | ☐ not done |
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
| R1 | Latency exceeds 5 s | Build the whole flow early; measure latency on every line (D12); end-to-end latency test; load test (D2). M1 finding (2026-10-30): Whisper small default settings RTF 0.58, so a 12 s segment (D8 cap) needs ≈ 7 s for ASR alone; to be addressed in M4 (T2, T4) | accepted |
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
- **L4 Segment cap 12 s:** long speech without pauses is cut at 12 s, possibly mid-word.
- **L5 Print order by speech end:** example — Speaker 1 talks 00:10–00:25, Me says something short 00:15–00:17 → the `[00:00:15] Me` line prints *before* `[00:00:10] Speaker 1`, so timestamps appear out of order.
- **L6 Mic is always "Me":** even if another person speaks into the mic.
- **L7 Final lines only:** no partial text while someone is speaking.
- **L8 Remote speakers:** diarization is tuned and tested for 1–2 remote speakers first.
- **L9 Demo assumption:** sized for "browser video call open + laptop plugged in"; other setups not yet verified.

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
