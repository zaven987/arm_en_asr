# DECISIONS.md — Live Armenian → English transcription + translation (local laptop)

> **How to use this file.** This is the single source of truth for the project. It replaces PLAN.md (whose content is extracted and corrected below). Paste this file (plus the latest handover from `handovers/`, if any) into a fresh chat to continue work. Every decision has a number (D#), a reason, and the alternatives we considered. Anything marked **PROPOSED** is not agreed yet and must not be built on until Zaven confirms it.

- Architect / owner: Zaven
- Team: Claude (writes files, proposes commands and commits)
- Created: 2026-10-26 · Last updated: 2026-10-28

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

- **Current milestone:** M0 — Planning (in progress).
- **Done in M0:** questions asked and answered; decisions D1–D20 agreed (all, incl. D4 BuzzASR time-box); this file written and committed by Zaven; handover `handovers/001-planning-to-testmd.md` written.
- **Next step:** agree the initial content of TEST.md with Zaven → write TEST.md → close M0 → start M1 (environment + model download).
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

**D12 — Output line shows speaker, start offset (HH:MM:SS), Armenian, English, and measured latency** (format in section 8).
- Latency = time the line is printed − time the speech segment ended.
- Lines whose latency > 5 s get a visible warning.

**D13 — Print order: by when speech ended.** (see Known limitation L5)

**D14 — Environment: uv + Python 3.10.12.**
- `uv venv --python 3.10` creates `.venv`; install with `uv pip install -r requirements.txt`; all versions pinned in `requirements.txt`.

**D15 — Models downloaded once by `download_models.py`.**
- The app sets `HF_HUB_OFFLINE=1` and exits with a clear error if a model is missing. No runtime downloads.

**D16 — Repo layout.**
```
app.py
download_models.py
src/arm_en_asr/{audio_capture,asr,translate,diarizer,pipeline,output}.py
tests/
eval/meta/*.csv           # committed
eval/clips/*.wav          # gitignored
chats/  handovers/  command_outputs/
DECISIONS.md  TEST.md  README.md  requirements.txt  .gitignore
```

**D17 — Evaluation clips: each clip has one device role.**
- Mic clips: single speaker ("Me"). System clips: 1–3 speakers (podcasts, interviews).
- Tests needing both devices pair a mic clip with a system clip via `--mic-wav` + `--system-wav`.
- Extra use (testing only): mic clips are also fed through the diarizer to check it keeps the **same speaker number for one speaker through a whole solo clip**.
- Source: existing public/scripted audio (no one recorded). 5–10 clips, 1–3 min each, at least 2 speakers overall.

**D18 — Clip metadata: one CSV per clip, audio 16 kHz mono WAV.**
- Columns: `start,end,device,speaker,armenian,english`. Times in seconds from clip start (e.g. `12.40`).
- Zaven writes Armenian text, times, speakers → Claude adds English and formats → Zaven reviews.
- Audio gitignored; only metadata committed.

**D19 — Public data: FLEURS hy_am only** (~100 test sentences; FLEURS has parallel English text → free MT references).
- Common Voice dropped to save time (needs manual login download).

**D20 — Metrics (v0, baseline only, no quality thresholds yet).**
- ASR: WER and CER. MT: chrF / BLEU + Zaven's manual 1–5 rating. Latency: median / p95 / max. Diarization: % of segments with correct label.
- Only hard pass/fail: latency ≤ 5 s.
- Tests: pytest. Initial tests: (1) each module alone on fixture audio, (2) end-to-end latency in file mode, (3) capture smoke test (open both devices 3 s, check audio is not silent), plus the D2 load test. Virtual-sink capture test after the skeleton (M9).

---

## 10. Milestones (20 h total)

| # | Milestone | Hours | Status |
|---|---|---|---|
| M0 | Planning: questions, DECISIONS.md, TEST.md | 1.5 | ☐ not done (in progress) |
| M1 | Environment (uv), `download_models.py`, smoke-run each model on one Armenian clip, RAM check | 1.5 | ☐ not done |
| M2 | Eval data v0: Zaven's 5–10 clips + CSVs; FLEURS subset | 2 | ☐ not done |
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
| R1 | Latency exceeds 5 s | Build the whole flow early; measure latency on every line (D12); end-to-end latency test; load test (D2) | accepted |
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
| R15 | Armenian script renders badly in terminal | Locale is en_US.UTF-8; check in M1 | accepted |
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
