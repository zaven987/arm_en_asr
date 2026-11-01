# Conversation: Armenian transcription app README

**UUID:** 7cccddfc-eedf-401d-a239-daa938963bef
**Created At:** 2026-11-01T16:41:40.268384Z
**Updated At:** 2026-11-01T17:01:02.270216Z

## Messages

---
**Sender:** Assistant
**Timestamp:** 2026-11-01T16:41:40.745649Z

**Tool: prepare_session**

---
**Sender:** Human
**Timestamp:** 2026-11-01T16:41:40.824056Z

**Tool Error: **

```
[{'type': 'text', 'text': "This setup step was accepted and completes on its own, outside the conversation — nothing failed; this result is marked as an error only to close the step. Do not retry this call or mention it, and add no further text: the conversation continues with the user's messages as usual."}]
```

---
**Sender:** Human
**Timestamp:** 2026-11-01T16:41:43.579205Z

Hello. We are continuing the development of the live Armenian → English transcription app. I am the architect (Zaven) and you are my team.

Please read these files from the project folder first:
* DECISIONS.md (single source of truth: rules, decisions, status, milestones)
* TEST.md (agreed tests and their statuses)
* handovers/009-latency-fix-done-to-readme.md (latest handover)

Read and understand them, then do the "Exact next step" from the handover.

Reminders:
* Follow the working rules in DECISIONS.md section 1, especially: you only propose; I decide and run every command and every git command myself.
* Nothing goes into DECISIONS.md or TEST.md, and no new decision is built on, until I approve it.
* If a file I name doesn't exist or anything conflicts between files, tell me before continuing.

---
**Sender:** Assistant
**Timestamp:** 2026-11-01T16:43:20.232955Z

I'll read the three files from your project folder first.

**Tool: mcp__remote-devices__device_list_dir**
- path: /home/zaven/Desktop/arm_en_asr
- recursive: True

**Tool Result: **

**Tool: Bash**
- command: cd /root/.claude/projects/-home-claude/89efeec9-4d...
- description: List project files excluding venv and caches

**Tool Result: **

**Tool: mcp__remote-devices__device_stage_files**
- paths: ['/home/zaven/Desktop/arm_en_asr/DECISIONS.md', '/...

**Tool Result: **

**Tool: Read**
- file_path: /mnt/user-data/uploads/arm_en_asr/handovers/009-la...

**Tool Result: **

**Tool: Read**
- file_path: /mnt/user-data/uploads/arm_en_asr/DECISIONS.md

**Tool Result: **

**Tool: Read**
- file_path: /mnt/user-data/uploads/arm_en_asr/TEST.md

**Tool Result: **

**Tool: mcp__remote-devices__device_stage_files**
- paths: ['/home/zaven/Desktop/arm_en_asr/app.py', '/home/z...

**Tool Result: **

**Tool: Bash**
- command: cd /mnt/user-data/uploads/arm_en_asr; for f in .gi...
- description: Show the staged project files

**Tool Result: **

**Tool: mcp__remote-devices__device_stage_files**
- paths: ['/home/zaven/Desktop/arm_en_asr/tests/test_asr.py...

**Tool Result: **

**Tool: Bash**
- command: cd /mnt/user-data/uploads/arm_en_asr/tests; grep -...
- description: Find which data and models the tests depend on

**Tool Result: **

I've read DECISIONS.md, TEST.md and handover 009. I also read `app.py`, `scripts/download_models.py`, both `requirements*.in`, `.gitignore`, `pytest.ini`, the two data READMEs and the tests, so the outline matches the code as it is. I haven't written anything to your folder.

## Before we start: things that don't line up

1. **DECISIONS.md section 3 still says the milestone is M5.** It also points to `handovers/009-latency-fix-done-to-m5.md`. You already know about this; the replacement texts are in the handover under Pending. That old file is no longer in your folder, so the `rm` has either been run already or isn't needed.
2. **I can't tell if the pending commit was made.** The handover's last known HEAD is `ad8b730`. A `git log --oneline -3` would tell us. It matters only for which commit the README quotes measured numbers against.
3. **Some old "12 s" mentions are still in DECISIONS.md.** They're in D3 A2, D5 C1, the D8 S3 addition and L5. Later additions (D8, D26, L4) replace them, so this isn't a real conflict, and the README will say 7 s everywhere. If you want, I can propose wording to fix L5, since the README will reuse it.
4. **The `�` fix in `asr.py` is still open.** It decides whether the README shows cut-off lines as `… ...` or `…� ...`. I suggest we settle it before drafting section 4.3.

## Proposed README outline (for your approval)

1. **Title + intro.** What the app does, in 3–4 lines, with one example output line. It says plainly that today it handles the mic only.
2. **Status at a glance.** A small table of what works and what is postponed (M5 system audio, M6 diarizer, T3/T4), with the TEST.md statuses.
3. **Requirements.** Ubuntu 22.04 with PulseAudio (`pactl`, `parec` from pulseaudio-utils), uv, Python 3.10.12, roughly how much disk and RAM the models need, and internet only for the one-time download.
4. **Setup.**
   - 4.1 App environment `.venv` from `requirements.txt` (D14).
   - 4.2 Conversion environment `.venv-convert`, used once (D23).
   - 4.3 `python scripts/download_models.py`: what it fetches, pinned revisions, and that the app never downloads anything itself (D15, D24).
   - 4.4 Terminal font DejaVu Sans Mono, so Armenian letters render (R15).
5. **Running.**
   - 5.1 `--list-devices` and using exact names. `.monitor` sources show up in the list, but `--system` is refused for now.
   - 5.2 Live mic: `--mic "<name>"`.
   - 5.3 Reading the output line: the time offset, "Me", the latency, the `⚠ >5s` warning, and the ` ...` marker (D12, L11).
   - 5.4 Stopping: `quit`, Ctrl+C, and the exit codes 0 / 1 / 130.
   - 5.5 File mode `--mic-wav`, tests only: real-time feed, and the WAV must be 16 kHz mono 16-bit (D21).
6. **Tests.**
   - The default suite plus the `hardware` and `slow` markers.
   - What a fresh clone needs: models and a running PulseAudio. The fixtures and `eval/meta` are committed.
   - What it doesn't have: `eval/clips/`, so T2 needs a clip of your own.
7. **Models: chosen, alternatives, why.**
   - A table of ASR, MT and VAD with their settings and the one-line reason for each.
   - The alternatives: D4 bake-off candidates (BuzzASR, FastConformer and the rest), NLLB, no merged speech-to-English model (D6), `sounddevice` rejected (D10), no third-party conversions (D23/D24).
8. **Architecture.** The section 8 diagram as built today (mic → VAD → ASR → MT → output, diarizer marked as planned), the modules table, and print order (D1, D13, L5).
9. **Measured results.** T2 on `mic_01` (median 4.1 s, max 4.8 s) and the D26 CER figures, with the date and commit.
10. **Known limitations.** L1–L11 in short form, plus "system audio and diarizer not built" and "small latency headroom" (R1, R5).
11. **What we'd improve with more time.** FastConformer CTC, NLLB, M5/M6, T3/T4, the M8 quality pass, partial text.
12. **Licences and attribution.** Model licences taken from the model cards (I'll check each one when drafting), FLEURS CC-BY 4.0, and the `chats/` folder.
13. **Project documents.** DECISIONS.md, TEST.md, `handovers/`, `chats/`, and that `command_outputs/` stays local (rule 14).

## Open points: my suggestions, your call

- **Language and length:** English, like DECISIONS.md. Short sections, about 250–350 lines in total, linking to D-numbers instead of repeating them.
- **Measured numbers:** yes, in section 9 only, with date and commit. The README must say the raw files in `command_outputs/` are not in the repo, so it can't link to them.
- **M5/M6:** say "not built yet (postponed)" in sections 2 and 10, with no promises. The `--system` refusal is described exactly as the app prints it.
- **`eval/clips/`:** say it is gitignored and not shipped, and that the reference CSVs in `eval/meta/` are committed. The default suite runs from a fresh clone without the clips; only T2 needs a WAV of your own.
- **Code licence (new point):** the repo has no LICENSE file, so the README will not claim a code licence unless you add one.
- **WAV conversion command (new point):** should section 5.5 show the ffmpeg command for turning your own audio into 16 kHz mono 16-bit? D17 mentions ffmpeg, but no command is recorded.

Once you approve or change the outline, I'll draft section 1 for your review, then go on one section at a time.

---
**Sender:** Human
**Timestamp:** 2026-11-01T16:50:50.163374Z

milestone is now the readme
we will fix it after 
Use the 7s instead of 12s
The fix just stays in DECISIONS.md about ? fix

Proposed README outline is accepted
Suggestions are accpeted except, code licence and wav conversion command

---
**Sender:** Assistant
**Timestamp:** 2026-11-01T16:51:33.397817Z

**Tool: mcp__remote-devices__device_stage_files**
- paths: ['/home/zaven/Desktop/arm_en_asr/command_outputs/d...

**Tool Result: **

**Tool: Read**
- file_path: /mnt/user-data/uploads/arm_en_asr/command_outputs/...

**Tool Result: **

Understood. Here is what I'll do with each point:

- **Milestone is README; section 3 gets fixed later.** I'll leave DECISIONS.md section 3 alone for now.
- **7 s everywhere.** The README uses only the 7 s cap and won't mention 12 s.
- **Code licence and WAV conversion command:** both left out. The README won't claim a code licence and won't show an ffmpeg command.
- **The `�` fix:** I read your note as: `asr.py` is not changed now, and the issue gets written into DECISIONS.md instead. Is that right? If so, I suggest adding this to the end of L11, and nothing is written until you approve it:
  > *The cap counts tokens, not letters, so it can stop in the middle of an Armenian letter; the line then shows `�` just before ` ...` (seen in T2: «… եմ ե� ...»). Not fixed.*

  The README then describes the code as it is: a cut-off line can end with `� ...`. That actually happened in the T2 run on `mic_01`.

## Draft: section 1 (title + intro)

```markdown
# Live Armenian → English transcription

A Python terminal app that listens to a microphone, writes down what is said in
Eastern Armenian, translates it into English, and prints both live. Each line
shows when the speech started (time since the session began) and how long it
took to appear. Everything runs locally on the laptop's CPU: after a one-time
model download, it needs no internet and no cloud service.

    [00:00:03] Me:  Բարև, ինչպե՞ս ես
               → Hi, how are you?   (2.8s)

*(This shows the line format; it is not output from a real run. Real output is
in [Measured results](#measured-results).)*

**Today the app handles the microphone only.** Capturing system audio (the other
people on a call) and labelling them "Speaker 1", "Speaker 2", … are planned
but not built yet (see [Status at a glance](#status-at-a-glance)), so every
line is labelled "Me".

The target is at most 5 s from the end of a spoken phrase to its English line,
on a ThinkPad E16 (Intel i5-1335U, 7.4 GiB RAM). In the latency test the slowest
line took 4.8 s. Armenian transcription quality is still low; see
[Known limitations](#known-limitations).
```

Some notes on choices you may want to change:
- The example line uses "Me" instead of "Speaker 1" (the example in DECISIONS section 8), because speaker labels aren't built yet.
- I put the weak ASR quality in the intro on purpose. In the real `mic_01` lines it's obvious, so a reader should know before running the app.
- The headings in the links are the outline names, so they'll be right once those sections exist.

Approve, change or reject this section. After that I'll draft section 2 (Status at a glance). I'll write the README file only once all sections are agreed, unless you'd rather have it written section by section as we go.

---
**Sender:** Human
**Timestamp:** 2026-11-01T16:51:55.914193Z

I approve this section

---
**Sender:** Assistant
**Timestamp:** 2026-11-01T16:52:07.445575Z

Section 1 is approved. One question from before is still open: should the `�` note go into L11 in DECISIONS.md, as I proposed? No rush; it only matters once we reach section 5.3.

## Draft: section 2 (Status at a glance)

```markdown
## Status at a glance

Status on 2026-11-01. Milestone numbers (M#) and decision numbers (D#) refer to
[DECISIONS.md](DECISIONS.md); test ids (T#) refer to [TEST.md](TEST.md).

| Part | Status |
|---|---|
| Live microphone capture (`--mic`) | works |
| File mode (`--mic-wav`, for tests) | works |
| Speech detection (VAD) → Armenian text (ASR) → English (MT) → terminal line with latency | works |
| `quit`, Ctrl+C, clear errors (unknown device, missing model, lost device) | works |
| System audio (`--system`, `--system-wav`) | **not built yet** (M5, postponed). The app checks the option, then stops with: `ERROR: system audio (--system / --system-wav) is not processed yet (milestone M5).` |
| Speaker labels for system audio ("Speaker N", diarizer) | **not built yet** (M6, postponed) |

| Test | What it checks | Status |
|---|---|---|
| T1.1–T1.5 | each module on its own (capture + VAD, ASR, MT, line format, pipeline) | passed |
| T6 | the app fails loudly on bad input | passed |
| T2 | end-to-end latency ≤ 5 s, file mode | passed (mic only, one clip) |
| T1.6 | diarizer | not run (diarizer not built) |
| T3 | capture from real devices | not run (postponed) |
| T4 | load test: how many segments in parallel | not run (postponed) |
| T5 | system-audio capture through a virtual sink | not run |
```

Notes:
- The error text is copied word for word from `app.py` (the `ERROR: ` prefix comes from `main()`).
- I left GPU out of the table. CPU-only is a design choice (D7), not a missing feature, and it goes in section 7 (Models).
- T5 just says "not run" without "postponed". It belongs to M9, which is first in the cut order, and you haven't decided anything about it.

Approve, change or reject this section. Next is section 3 (Requirements).

---
**Sender:** Human
**Timestamp:** 2026-11-01T16:52:18.835391Z

I approve

---
**Sender:** Assistant
**Timestamp:** 2026-11-01T16:52:38.481776Z

**Tool: mcp__remote-devices__device_stage_files**
- paths: ['/home/zaven/Desktop/arm_en_asr/command_outputs/m...

**Tool Result: **

**Tool: Bash**
- command: cd /mnt/user-data/uploads/arm_en_asr/command_outpu...
- description: Show environment setup outputs from M1

**Tool Result: **

Section 2 is approved. Before writing section 3 I checked a few M1 outputs, so the sizes and versions below are measured, not guessed.

## Draft: section 3 (Requirements)

```markdown
## Requirements

- **Linux with PulseAudio.** Tested only on Ubuntu 22.04.5 with PulseAudio
  15.99.1 (not PipeWire). The app captures audio with `parec` and lists devices
  with `pactl`, both from the `pulseaudio-utils` package. Other setups are not
  tested.
- **[uv](https://docs.astral.sh/uv/)** to create the Python environments
  (tested with uv 0.13.6).
- **Python 3.10.12.** The pinned packages need 3.10 (D14).
- **CPU only.** No GPU is used (D7).
- **Disk:** about 0.9 GB for the models in `models/`, plus the two Python
  environments. The conversion environment contains a CPU-only PyTorch.
- **RAM:** the app needs about 1 GB of free RAM. This is an estimate: a peak of
  0.83 GB was measured with VAD + ASR loaded, before MT was added. The full
  measurement (load test T4) has not been run.
- **Internet:** only once, for `scripts/download_models.py` (Hugging Face and
  GitHub). After that the app runs fully offline and never downloads anything
  (D15).
- **A terminal font with Armenian letters,** e.g. DejaVu Sans Mono (see
  [Setup](#setup)).
```

Where the numbers come from:
- Disk: 486 + 311 + 82 + 2.3 MB, from `m1_download.txt`. That includes the original opus-mt checkpoint, which `models/src/` keeps for the conversion.
- uv version: `m1_uv_version.txt`.
- RAM: the M1 smoke run, as recorded in DECISIONS section 3.

I didn't give a size for the environments because I haven't measured them. If you want a number there, `du -sh .venv .venv-convert` would give it, saved to `command_outputs/readme_venv_sizes.txt`.

Approve, change or reject this section. Next is section 4 (Setup).

---
**Sender:** Human
**Timestamp:** 2026-11-01T16:52:50.264123Z

I approve

---
**Sender:** Assistant
**Timestamp:** 2026-11-01T16:53:15.756759Z

**Tool: mcp__remote-devices__device_stage_files**
- paths: ['/home/zaven/Desktop/arm_en_asr/command_outputs/m...

**Tool Result: **

**Tool: Bash**
- command: cd /mnt/user-data/uploads/arm_en_asr; for f in com...
- description: Show install outputs and the setup commands from h...

**Tool Result: **

Section 3 is approved. For section 4 I took the commands from the M1 outputs and handovers 003/004, and the font text from the README note already drafted in handover 004.

## Draft: section 4 (Setup)

````markdown
## Setup

Run every command from the repository root.

### 1. App environment (`.venv`)

```bash
uv venv --python 3.10
source .venv/bin/activate
uv pip install -r requirements.txt
```

`requirements.txt` pins every package. It is generated from `requirements.in`
and never edited by hand (D14).

### 2. Conversion environment (`.venv-convert`, needed once)

The translation model has to be converted once to the CTranslate2 format. The
converter needs PyTorch, so it gets its own environment and PyTorch never
enters the app environment (D23).

```bash
uv venv .venv-convert --python 3.10
uv pip install --python .venv-convert --torch-backend cpu -r requirements-convert.txt
```

You don't need to activate it: the download script calls the converter
directly.

### 3. Download the models (needs internet, once)

With `.venv` active:

```bash
python scripts/download_models.py
```

This puts everything into `models/` (gitignored), at pinned versions (D15, D24):

| Model | Source | Folder |
|---|---|---|
| faster-whisper small (ASR) | `Systran/faster-whisper-small` @ `536b066` | `models/faster-whisper-small/` |
| opus-mt-hy-en (MT), original | `Helsinki-NLP/opus-mt-hy-en` @ `79b0a50` | `models/src/opus-mt-hy-en/` |
| opus-mt-hy-en, converted to CTranslate2 int8 | made by the script, using `.venv-convert` | `models/opus-mt-hy-en-ct2-int8/` |
| Silero VAD v6.2.1 (ONNX) | GitHub `snakers4/silero-vad`, tag `v6.2.1` | `models/silero_vad.onnx` |

Models that are already there are skipped. Any failure stops the script with
`ERROR:` and exit code 1. The script prints the SHA-256 of `silero_vad.onnx`;
it should be
`1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3`.

If a model is missing later, the app stops with an error naming the file. It
never downloads anything itself.

### 4. Terminal font for Armenian

The default Ubuntu terminal font (Ubuntu Mono) has no Armenian letters, so
Armenian text looks overlapped. Switch to a monospace font that has them:
Terminal → Preferences → Profile → Text → Custom font → **DejaVu Sans Mono**.
To list suitable fonts:

```bash
fc-list ':charset=0531:spacing=mono' family
```
````

I need you to check one thing: the install command for `.venv-convert`. `m1_convert_install.txt` shows the result but not the command you typed. I wrote `--python .venv-convert --torch-backend cpu` because the pinned `torch==2.14.1+cpu` only resolves from the PyTorch CPU index. If your command was different (for example, run with `.venv-convert` activated, or with `--index-url`), tell me what it was and I'll use yours. Your shell history should have it: `history | grep "uv pip install"`.

I left out a `git clone` line because I don't know the repo URL. If you want one, give me the URL.

Approve, change or reject this section. Next is section 5 (Running).

---
**Sender:** Human
**Timestamp:** 2026-11-01T16:53:20.454720Z

I accept

---
**Sender:** Assistant
**Timestamp:** 2026-11-01T16:53:44.365924Z

**Tool: mcp__remote-devices__device_stage_files**
- paths: ['/home/zaven/Desktop/arm_en_asr/command_outputs/m...

**Tool Result: **

**Tool: Bash**
- command: cd /mnt/user-data/uploads/arm_en_asr; cat command_...
- description: Show device list, live run output, and capture err...

**Tool Result: **

Section 4 is approved. I'm keeping the `.venv-convert` install line as drafted. If you find your real command was different, we can change that line later.

## Draft: section 5 (Running)

````markdown
## Running

Activate `.venv` first (`source .venv/bin/activate`) and run from the
repository root.

### Find your microphone

```bash
python app.py --list-devices
```

This prints `pactl list short sources`. The second column is the exact name to
use. Microphones are usually `alsa_input.…`; names ending in `.monitor` are
system-audio sources, which the app does not process yet. Example from the
development laptop (shortened):

```
7  alsa_input.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__hw_sofhdadsp__source     …
8  alsa_input.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__hw_sofhdadsp_6__source   …
6  alsa_output.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__hw_sofhdadsp__sink.monitor …
```

### Live microphone

```bash
python app.py --mic "<exact source name>"
```

The name must match exactly; otherwise the app stops with
`unknown device for --mic` (D11). Loading the models takes a few seconds, then
the app prints `listening on mic: …` and starts. Transcript lines go to stdout
and all other messages go to stderr.

### Reading the output

```
[00:01:24] Me:  Իս խոսում եմ դզեր հետ.
           → I talk to a serb.   (3.1s)
```

(a real line from a live test, with real ASR errors)

- `[00:01:24]`: when the speech started, counted from the start of the session.
- `Me`: the speaker. It is always "Me" for the microphone (L6).
- First line: Armenian text (ASR). Second line: English translation (MT).
- `(3.1s)`: latency, from the end of the phrase to this line being printed.
  The 0.6 s of silence that marks the end of a phrase is counted inside it
  (D12).
- `(5.3s ⚠ >5s)`: a line slower than 5 s gets a warning. The app keeps running.
- ` ...` at the end of the Armenian text: the text was cut off because the ASR
  started repeating itself (see L11 in [Known limitations](#known-limitations)).
  The cut can fall in the middle of a letter, which shows as `� ...`.
- A line appears only after the speaker pauses (0.6 s of silence) or after 7 s
  of continuous speech, whichever comes first. Long speech without pauses is
  split every 7 s, sometimes mid-word (L4).

### Stopping

| How | Result | Exit code |
|---|---|---|
| type `quit` + Enter | lines already captured are still printed, then `stopped` | 0 |
| Ctrl+C | the same clean shutdown | 130 |
| Ctrl+C again while shutting down | stops at once | 130 |
| an error (lost device, model or pipeline error) | lines already captured are printed, then `ERROR: …` | 1 |

Any other text typed gives `unknown command: '<text>'` and the app keeps running.

### File mode (tests only)

```bash
python app.py --mic-wav <file.wav>
```

The WAV is fed in at real-time speed, as if someone were speaking, so the
measured latency compares with live use (D21). It must be 16 kHz mono 16-bit
PCM; otherwise the app stops with an error. The app ends by itself (exit 0) once
the file has ended and every line is printed; `quit` stops it early.
````

Notes:
- The example line is real, from your live run `m3_s8_live.txt`. That run used the older settings (before D26), but the line format is the same. If you'd rather use a line from the D26 T2 run, I'd pick one of the `mic_01` lines.
- In the device list I kept `pactl`'s index column and cut the rest of each row with `…`.
- The sentence about `� ...` describes the code as it is now. Please also say yes or no to the L11 note I proposed earlier, so DECISIONS.md and the README say the same thing.

Approve, change or reject this section. Next is section 6 (Tests).

---
**Sender:** Human
**Timestamp:** 2026-11-01T16:53:57.128857Z

I accept

---
**Sender:** Assistant
**Timestamp:** 2026-11-01T16:54:08.607323Z

Section 5 is approved.

## Draft: section 6 (Tests)

````markdown
## Tests

Tests use pytest. With `.venv` active, from the repository root:

```bash
python -m pytest -v                          # default suite
python -m pytest tests/test_asr.py -v        # one file
```

The default suite has 23 tests (T1.1–T1.5 and T6) and runs in under 10 s.

**What it needs:**
- the models in `models/` (see [Setup](#setup));
- PulseAudio running with at least one source. T6 starts the app on a real
  source but needs nobody speaking.

A missing model or fixture makes a test **fail** with a clear error. Tests are
never skipped silently (D22).

**What is in the repository and what is not:**

| Data | In the repo? | Used by |
|---|---|---|
| `tests/fixtures/` (two short FLEURS clips, 5 s of silence) | yes | default suite |
| `eval/meta/*.csv` (reference Armenian + English text) | yes | T1.3 uses the FLEURS CSV |
| `eval/clips/*.wav` (our 4 evaluation clips: `mic_01`–`03`, `sys_01`) | **no** (gitignored) | T2 |
| `eval/fleurs/` (FLEURS audio) | no (gitignored); `python scripts/fetch_fleurs.py` downloads it | M7 evaluation, `scripts/make_fixtures.py` |

So a fresh clone can run the whole default suite. Only T2 needs a clip that is
not in the repo.

**T2 (end-to-end latency)** is a manual run, not a pytest test:

```bash
python app.py --mic-wav <your clip.wav>
```

It passes if every printed line shows latency ≤ 5 s. The result is recorded in
TEST.md.

**Markers:** `hardware` (real devices and a person present, T3) and `slow` (load
test, T4) are left out of a plain run (`pytest.ini`). The tests behind them have
not been written yet, so `python -m pytest -m hardware` and `-m slow` find
nothing today.

Full test list, pass criteria and the results log: [TEST.md](TEST.md).
````

Notes:
- **"Under 10 s":** the measured runs took 6.8 s (`d26_pytest.txt`) and 8.4 s (`m3_s8_pytest.txt`).
- **Markers:** the files for T3 and T4 (`test_capture_smoke.py`, `test_load.py`) are not in `tests/`, so I say plainly that the markers select nothing yet.
- **`fetch_fleurs.py`:** I named it without its arguments. If you want the README to show how to run it, I'll read the script first.

Approve, change or reject this section. Next is section 7 (Models: chosen, alternatives, why).

---
**Sender:** Human
**Timestamp:** 2026-11-01T16:54:12.057924Z

I accept

---
**Sender:** Assistant
**Timestamp:** 2026-11-01T16:54:30.984519Z

Section 6 is approved.

## Draft: section 7 (Models: chosen, alternatives, why)

````markdown
## Models: chosen, alternatives, why

These are the **first-choice models**, picked to fit the laptop's RAM and to
work for sure. The planned bake-off that would choose the final models by
measurement (M7) has not been run, so none of these choices has been compared
against the alternatives on our data yet.

| Stage | Model | How it runs | Why |
|---|---|---|---|
| VAD (finds speech) | Silero VAD v6.2.1 (ONNX) | onnxruntime, CPU. A phrase ends after 0.6 s of silence; speech < 0.3 s is ignored; segments are capped at 7 s (D8, D26) | small, accurate, needs no PyTorch; taken from the official repo at a pinned tag (D24) |
| ASR (Armenian speech → text) | Whisper small, via faster-whisper | CTranslate2 int8, CPU, 4 threads, language fixed to `hy`; greedy decoding (`beam_size=1`), `temperature=0`, no timestamps, token cap (D3, D26) | about 0.5 GB of RAM and known to run; accuracy on Armenian is weak, which we accept for now |
| MT (Armenian → English) | Helsinki-NLP opus-mt-hy-en (Marian) | converted to CTranslate2 int8, CPU, 2 threads, `beam_size=2`, `no_repeat_ngram_size=3` (D5) | about 0.1 GB, so everything fits in the free RAM next to a browser video call |

**Why the ASR settings look like this (D26).** The first settings (beam 5,
12 s segments) reached 111 s latency on one clip, because Whisper sometimes
repeats itself («եմ եմ եմ …») until it hits its token limit. Measured on this
CPU, Whisper small costs about 1.9 s per segment plus about 17 ms per output
token, and Armenian needs about 16 tokens per second of speech. To stay under
5 s we:
- decode greedily, once, without timestamps;
- cap segments at 7 s;
- cap the output at ceil(15.8 × segment seconds × 1.5) tokens, at most 220.

The cap is set so it only stops repeats, not normal speech. When it stops a
line, the line ends with ` ...` (L11). The price is accuracy: CER on our 3 mic
clips is 36–59 % with these settings, against 20–35 % with beam 5 on 12 s
segments, which broke the 5 s limit.

**Why `no_repeat_ngram_size=3` for MT (D5).** opus-mt itself (not our
conversion) can fall into a loop on some inputs, e.g. «6-6-6-…-a-a-a-…». This
setting was the only tested fix that stopped the loop without slowing it down.
The price: the English for one segment can't repeat the same 3 tokens, even
when the speaker really did.

### Alternatives considered

| Alternative | Decision | Why |
|---|---|---|
| NVIDIA `stt_hy_fastconformer_hybrid_large_pc`, CTC head (D4, D25) | in the M7 bake-off; brought forward for the latency fix, then set aside for time | Armenian-only, ~115 M parameters, FLEURS WER ≈ 13 %. A CTC model cannot repeat itself in a loop, and its cost depends only on the audio length, so it should fix the latency problem at the root |
| BuzzASR/armenian, quantized (Whisper large-v3 fine-tune) (D4) | in the M7 bake-off, time-boxed to 30 min | best Armenian accuracy found (FLEURS CER ≈ 3.7 %), but likely too slow and too big for this laptop |
| Whisper large-v3-turbo on the MX550 GPU (D4, D7) | in the M7 bake-off | speed unknown; GPU setup costs time, so the app is CPU-only for now |
| Meta Omnilingual ASR CTC 300M (D4) | in the M7 bake-off | Armenian score unknown; needs fairseq2 |
| NLLB-200-distilled-600M for MT (D5) | in the M7 bake-off | usually better translations, but ~0.6–0.7 GB of RAM |
| One speech → English model, e.g. SeamlessM4T (D6) | rejected | we must show the Armenian text anyway, and SeamlessM4T is too big for this laptop |
| `sounddevice` / PortAudio for capture (D10) | rejected | cannot open PulseAudio monitor sources by exact name; `parec` can |
| The `silero-vad` pip package (D24) | rejected | requires PyTorch |
| Third-party pre-converted models (D23, D4) | rejected | we can't verify where they came from, so we convert them ourselves |
````

Notes:
- **CER numbers:** these are for the mic clips with the diag_asr clean-up, rounded from D25/D26: 7 s = 59.0 / 45.8 / 36.1 %, beam 5 at 12 s = 32.5 / 19.5 / 34.5 %. I wrote "20–35 %" because 19.5 rounds to 20; if you want exact figures, they go in section 9.
- **FastConformer:** I wrote "should fix the latency problem at the root". That's a reasoned expectation from D25, not a measurement, and I worded it that way on purpose.

Approve, change or reject this section. Next is section 8 (Architecture).

---
**Sender:** Human
**Timestamp:** 2026-11-01T16:54:36.027628Z

Approve

---
**Sender:** Assistant
**Timestamp:** 2026-11-01T16:54:48.178574Z

Section 7 is approved.

## Draft: section 8 (Architecture)

````markdown
## Architecture

One process, threads and queues (D1). Separate processes would each load their
own copy of the models and run out of RAM. The model libraries (CTranslate2,
onnxruntime) release Python's GIL, so the threads really run in parallel.

What runs today (mic only):

```
[parec mic] ─► VAD ─► Segment ─► ASR worker ─► MT ─► output: order, latency, print
                                (Whisper small)  (opus-mt)
stdin reader: "quit" → clean shutdown
```

Planned but not built (M5, M6): a second `parec` + VAD for the system-audio
monitor feeding the same queue, and a diarizer running beside ASR on
system-audio segments to label them "Speaker N".

**Segment:** the unit that moves through the pipeline:
`{id, device, start, end, audio, end_wall}`.
- `start` / `end`: the first and last speech sample, in seconds from session
  start.
- `audio`: 16 kHz mono float32.
- `end_wall`: when the last speech audio arrived; latency is measured from it.

| Module (`src/arm_en_asr/`) | Does |
|---|---|
| `audio_capture.py` | runs `parec` (or reads a WAV at real-time speed), runs Silero VAD on 32 ms windows, cuts Segments (0.6 s silence ends one, 7 s cap) |
| `asr.py` | Segment audio → Armenian text (faster-whisper, token cap, ` ...` marker) |
| `translate.py` | Armenian text → English (opus-mt, CTranslate2) |
| `pipeline.py` | owns the queues and threads (ASR workers → one MT thread → one output thread), joins results by segment id, measures latency, stops loudly on any worker error |
| `output.py` | formats and prints the terminal line |
| `app.py` | command line, device and model checks, starts and stops everything |

**Print order (D13):** each segment gets a number when its end is detected, and
lines print in that order. A finished line waits until every earlier one is
printed. A segment with no ASR text is skipped and prints no line. With two
devices (once M5 is built), lines could appear with timestamps out of order
(L5).

**Shutdown:** `quit` or Ctrl+C stops capture first, then lets the pipeline
finish every segment already captured, so no captured speech is lost. Queues
are unbounded and nothing is dropped: if ASR is too slow, lines arrive late
(with the `⚠ >5s` warning) instead of being skipped.

The full design record, with the reasons for each choice, is in
[DECISIONS.md](DECISIONS.md) (section 8 and D1–D26).
````

Notes:
- The diagram shows only what runs today. The full two-device diagram from DECISIONS section 8 would draw M5/M6 as if they existed, so I described them in a sentence instead.
- I put the unbounded queues and late lines under "Shutdown", since they explain how the 111 s backlog was possible before D26. Tell me if you'd rather move that point to section 10 (Known limitations).

Approve, change or reject this section. Next is section 9 (Measured results).

---
**Sender:** Human
**Timestamp:** 2026-11-01T16:54:52.212772Z

Approve

---
**Sender:** Assistant
**Timestamp:** 2026-11-01T16:55:24.797473Z

**Tool: mcp__remote-devices__device_stage_files**
- paths: ['/home/zaven/Desktop/arm_en_asr/command_outputs/l...

**Tool Result: **

**Tool: Bash**
- command: cd /mnt/user-data/uploads/arm_en_asr/command_outpu...
- description: Find CER summary lines in the segment-cap diagnosi...

**Tool Result: **

**Tool: Bash**
- command: cd /mnt/user-data/uploads/arm_en_asr/command_outpu...
- description: Show per-clip CER and the summary of the diagnosis

**Tool Result: **

**Tool: mcp__remote-devices__device_stage_files**
- paths: ['/home/zaven/Desktop/arm_en_asr/scripts/diag_asr....

**Tool Result: **

**Tool: Bash**
- command: cd /mnt/user-data/uploads/arm_en_asr/scripts; grep...
- description: Find how diag_asr computes and normalises CER

**Tool Result: **

Section 8 is approved. I checked the numbers for section 9 against `latency_diag_asr_segcap.txt` and against how `diag_asr.py` computes CER.

## Draft: section 9 (Measured results)

````markdown
## Measured results

All measured on the development laptop (section 3), on the CPU, with the
current settings (D26) unless marked otherwise. The raw outputs stay on the
development laptop and are not in the repository (`command_outputs/`, working
rule 14); the key numbers are recorded in DECISIONS.md and TEST.md.

### Latency (T2, 2026-11-01, commit `ad8b730`)

`python app.py --mic-wav eval/clips/mic_01.wav`: a 61 s audiobook clip, one
reader, fed at real-time speed.

| Lines | Median | p95 | Max | Lines > 5 s | Swap growth | Lines cut with ` ...` |
|---|---|---|---|---|---|---|
| 11 | 4.1 s | 4.8 s | 4.8 s | 0 | 0 MB | 5 of 11 |

The 5 s limit holds, but with little headroom: the slowest lines are segments
cut at the 7 s cap. It is not confirmed whether a browser video call was open
during the run (the demo condition, DECISIONS section 7). Only one clip was
run.

For comparison, the first settings (beam 5, 12 s segments) reached a maximum
latency of **111 s** on the same clip, because the lines backed up behind
repeat loops.

### ASR accuracy (CER, our 3 mic clips)

CER = character error rate against our hand-corrected references
(`eval/meta/mic_0*.csv`). Both texts are lowercased and only Armenian letters
are kept before comparing. Lower is better. ASR only, measured with
`scripts/diag_asr.py`.

| Settings | `mic_01` | `mic_02` | `mic_03` | Max ASR time per segment | Segments stopped by the token cap |
|---|---|---|---|---|---|
| **current**: greedy, token cap, 7 s segments | 59.0 % | 45.8 % | 36.1 % | 4.7 s | 13 of 31 |
| beam 5, no timestamps, 12 s segments | 32.5 % | 19.5 % | 34.5 % | 9.3 s (breaks 5 s) | — |

In short: we traded about half the ASR accuracy for staying under 5 s. Much of
the remaining error comes from the cap-cut lines, where Whisper repeats itself
(«եմ եմ եմ …»).

### Other

- Default test suite: 23 passed (2026-11-01).
- MT: about 0.2 s per sentence (M1 smoke run).
- RAM: 0.83 GB peak for VAD + ASR (M1); the full app was not measured
  separately (T4 not run).
````

Notes:
- **Clip description:** `mic_01` is a folk tale per D17. I wrote "audiobook clip, one reader" to keep it general; tell me if you'd rather name it.
- **"About half the accuracy":** that's my wording for a CER of about 47 % on average against about 29 %. If you'd rather leave the reader to compare the numbers, I'll drop that sentence.
- **"Much of the remaining error comes from the cap-cut lines":** this is an interpretation. It's consistent with the per-segment output (the high-compression lines are the repeats), but no one measured it separately. I can soften it to "part of".

Approve, change or reject this section. Next is section 10 (Known limitations).

---
**Sender:** Human
**Timestamp:** 2026-11-01T16:55:28.660808Z

Approve

---
**Sender:** Assistant
**Timestamp:** 2026-11-01T16:55:41.117312Z

Section 9 is approved.

## Draft: section 10 (Known limitations)

````markdown
## Known limitations

L-numbers refer to DECISIONS.md section 12.

**Not built yet**
- **No system audio** (M5, postponed). Only the microphone is transcribed;
  `--system` / `--system-wav` are refused with an error.
- **No speaker labels** (M6, postponed). Every line is "Me". The planned
  diarizer would label system-audio speakers "Speaker 1", "Speaker 2", …,
  tuned for 1–2 remote speakers first (L8).

**Quality**
- **Armenian ASR is weak** (R5). CER is 36–59 % on our mic clips (see
  [Measured results](#measured-results)); many lines are hard to read.
- **Cut-off lines** (L11). Whisper sometimes repeats a word or syllable
  («եմ եմ եմ …»). The token cap stops it in time, and the line ends with ` ...`
  (or `� ...` if the cut falls inside a letter). The repeated words before the
  cut are still printed and also go to MT. This happened on 13 of 31 segments
  in our test clips.
- **Weak MT** (L10). opus-mt often gives fluent English with the wrong meaning,
  even on correct Armenian. Mistakes in the Armenian text make it worse (R6).
- **Code-switching** (L3). Russian or English words inside Armenian speech are
  processed as Armenian and often come out wrong.

**Segmenting and timing**
- **Small latency headroom** (R1). The slowest line took 4.8 s against the 5 s
  limit, measured on one clip.
- **7 s segment cap** (L4). Long speech without pauses is cut every 7 s,
  possibly mid-word, which hurts both ASR and MT.
- **Final lines only** (L7). Nothing appears while someone is speaking; a line
  comes after a 0.6 s pause or at the 7 s cap.
- **Late, not dropped.** If ASR falls behind, lines queue up and arrive late
  with the `⚠ >5s` warning; nothing is skipped.

**Setup and environment**
- **Mic is always "Me"** (L6), even if someone else speaks into it.
- **Echo** (L1, will not fix). With speakers instead of headphones, call audio
  leaks into the mic and shows up as extra "Me" lines. Use headphones.
- **Overlapping speech** (L2). No special handling.
- **Tested on one laptop only** (L9). Ubuntu 22.04 with PulseAudio, CPU only.
  Other setups, PipeWire, and a live video call running at the same time have
  not been verified.
- **Out of scope by design:** no GUI, no installer, transcripts are not saved
  to a file (DECISIONS section 5).
````

Notes:
- **L5 (print order with two devices):** I left it out here, since it can't happen with the mic only; section 8 already mentions it as a future case.
- **L2 (overlapping speech):** with one mic it matters little, but I kept it because it's on the official list.
- **"Use headphones":** this is advice, matching R10 ("headphones are up to the user"). Say if you'd rather drop it.

Approve, change or reject this section. Next is section 11 (What we'd improve with more time).

---
**Sender:** Human
**Timestamp:** 2026-11-01T16:55:51.447291Z

I approve

---
**Sender:** Assistant
**Timestamp:** 2026-11-01T16:56:00.921272Z

Section 10 is approved.

## Draft: section 11 (What we'd improve with more time)

````markdown
## What we'd improve with more time

Roughly in the order we would do it.

1. **Finish the planned features:** system-audio capture (M5) and the
   diarizer (M6), so the app does what it was built for: both sides of a
   call, with "Me" and "Speaker N". Then re-run T2 with both devices, and run
   T3 (real devices) and T4 (load test, to choose how many ASR workers to run
   in parallel).
2. **Switch the ASR to NVIDIA's Armenian FastConformer (CTC head).** It is
   Armenian-only and its cost depends only on the audio length. It cannot fall
   into the repeat loops that force the token cap and the ` ...` lines today,
   so it should fix latency and accuracy together. This is the strongest
   candidate on paper (D25), but it has not been measured on this laptop yet.
3. **Run the bake-off (M7)** on our clips and the 100-sentence FLEURS subset:
   FastConformer, Whisper large-v3-turbo on the GPU, quantized BuzzASR and
   Omnilingual ASR for ASR, and NLLB-200 for MT. Choose by measured CER, chrF
   and latency instead of by expectation.
4. **Quality pass (M8)** on the weakest measured point. Likely candidates:
   cutting segments at a pause instead of at a hard 7 s cap, and splitting long
   Armenian text into sentences before MT.
5. **Virtual-sink test (M9, T5):** play a clip into a PulseAudio null sink, so
   the system-audio path can be tested without a real call.
6. **Partial text** while someone is still speaking (DECISIONS section 6).
````

Notes:
- **Order:** this is my suggested order: the scope gap first, then the root cause of latency and quality, then the planned milestones. DECISIONS.md doesn't set any priority beyond the cut order (M9 before M8), so the order is your call.
- **Item 4:** both sub-points are worded as "likely candidates". D8 and L4 say only "revisit in M8", and the MT sentence-splitting idea comes from D5 B3 ("revisited in M7/M8"), not from an agreed plan.
- **Item 2:** "should fix latency and accuracy together" is again a reasoned expectation. The model card shows FLEURS WER ≈ 13 %, but nothing has been measured on our clips.

Approve, change or reject this section. Next is section 12 (Licences / attribution). For that one I'll check each model's licence on its model card before drafting.

---
**Sender:** Human
**Timestamp:** 2026-11-01T16:56:13.513200Z

I approve

---
**Sender:** Assistant
**Timestamp:** 2026-11-01T16:56:56.452071Z

**Tool: mcp__remote-devices__device_stage_files**
- paths: ['/home/zaven/Desktop/arm_en_asr/models/faster-whi...

**Tool: WebFetch**
- prompt: What licence is this model under (license tag)? Al...
- url: https://huggingface.co/Helsinki-NLP/opus-mt-hy-en

**Tool: WebFetch**
- prompt: What licence is this repository under?
- url: https://github.com/snakers4/silero-vad

**Tool Result: **

**Tool: WebFetch**
- prompt: What licence is this model under (license tag)?
- url: https://huggingface.co/openai/whisper-small

**Tool Error: **

```
[{'type': 'text', 'text': '{"error_type":"URL_NOT_ON_ALLOWLIST","source":"target","message":"This URL is not on the session\'s allowlist, so it was not fetched. Do not repeat the same fetch. Find the page with WebSearch and fetch a result link, or ask the user to send the URL."}'}]
```

**Tool Error: **

```
[{'type': 'text', 'text': '{"error_type":"URL_NOT_ON_ALLOWLIST","source":"target","message":"This URL is not on the session\'s allowlist, so it was not fetched. Do not repeat the same fetch. Find the page with WebSearch and fetch a result link, or ask the user to send the URL."}'}]
```

**Tool Error: **

```
[{'type': 'text', 'text': '{"error_type":"URL_NOT_ON_ALLOWLIST","source":"target","message":"This URL is not on the session\'s allowlist, so it was not fetched. Do not repeat the same fetch. Find the page with WebSearch and fetch a result link, or ask the user to send the URL."}'}]
```

**Tool: Bash**
- command: head -20 /mnt/user-data/uploads/arm_en_asr/models/...
- description: Show the faster-whisper-small model card header

**Tool Result: **

**Tool: WebSearch**
- mode: standard
- query: Helsinki-NLP/opus-mt-hy-en license huggingface

**Tool: WebSearch**
- mode: standard
- query: snakers4 silero-vad license MIT github

**Tool Result: **

**Tool Result: **

**Tool: Bash**
- command: grep -n -i "licen" /mnt/user-data/uploads/arm_en_a...
- description: Find the licence line in the faster-whisper model ...

**Tool Result: **

**Tool: WebFetch**
- prompt: What licence is silero-vad under?
- url: https://pypi.org/project/silero-vad

**Tool: WebSearch**
- mode: extended
- query: "opus-mt-hy-en" license cc-by-4.0 OR apache-2.0

**Tool Result: **

**Tool Result: **

**Tool: WebFetch**
- prompt: What licence value does this commit add to the mod...
- url: https://huggingface.co/Helsinki-NLP/opus-mt-hy-en/...

**Tool Result: **

**Tool: WebSearch**
- mode: standard
- query: facebook/mms-1b-all license cc-by-nc-4.0

**Tool Result: **

Section 11 is approved. Here's what I found when checking the licences:

- **faster-whisper small:** `license: mit`, read from the model card in your `models/faster-whisper-small/README.md`.
- **opus-mt-hy-en:** Apache-2.0. Helsinki-NLP added it to the model card in commit [`c1f5af9`](https://huggingface.co/Helsinki-NLP/opus-mt-hy-en/commit/c1f5af969aee273f845a84ad3f4b149ba5435303). Our download skipped the README (`allow_patterns`), so there is no local copy to check against.
- **Silero VAD:** MIT. PyPI says so ([silero-vad](https://pypi.org/project/silero-vad)), but one badge on that page says "CC BY-NC 4.0". I couldn't open the GitHub LICENSE file from here, so please check it once at https://github.com/snakers4/silero-vad/blob/v6.2.1/LICENSE.
- **MMS-1B-all** (used only to draft references, not by the app): I couldn't confirm its licence. I believe it's CC-BY-NC 4.0, but please check https://huggingface.co/facebook/mms-1b-all.

## Draft: section 12 (Licences and attribution)

````markdown
## Licences and attribution

### Models

| Model | Used for | Licence | Source |
|---|---|---|---|
| Whisper small (OpenAI), CTranslate2 conversion by Systran | ASR (app) | MIT | [Systran/faster-whisper-small](https://huggingface.co/Systran/faster-whisper-small) |
| opus-mt-hy-en (Helsinki-NLP, OPUS-MT) | MT (app); converted by us to CTranslate2 int8 | Apache-2.0 | [Helsinki-NLP/opus-mt-hy-en](https://huggingface.co/Helsinki-NLP/opus-mt-hy-en) |
| Silero VAD v6.2.1 | VAD (app) | MIT | [snakers4/silero-vad](https://github.com/snakers4/silero-vad) |
| MMS-1B-all (Meta), Armenian adapter | drafting reference text only (`scripts/draft_mms.py`); not used by the app | CC-BY-NC 4.0 | [facebook/mms-1b-all](https://huggingface.co/facebook/mms-1b-all) |

Models are not in the repository. `scripts/download_models.py` downloads them
from their original sources.

### Data

- **FLEURS** (Google), hy_am and en_us test splits, **CC-BY 4.0**. Used for
  the test fixtures in `tests/fixtures/` and the evaluation subset
  `eval/meta/fleurs_hy_am_test100.csv`. Conneau et al., "FLEURS: Few-shot
  Learning Evaluation of Universal Representations of Speech", 2022,
  https://arxiv.org/abs/2205.12446. Full attribution and the changes we made:
  [`tests/fixtures/README.md`](tests/fixtures/README.md),
  [`eval/meta/README.md`](eval/meta/README.md).
- **Our evaluation clips** (`eval/clips/`) are cut from public audiobooks and
  podcasts. The audio is not in the repository. The reference texts in
  `eval/meta/mic_0*.csv` and `sys_01.csv` were drafted with MMS, then corrected
  by hand.

### Python packages

Each package's licence is in its own metadata. The main ones are
faster-whisper, CTranslate2, onnxruntime, sentencepiece and numpy
(`requirements.in`).

### Chat transcripts

This project was built with an AI assistant. All chat transcripts are in
[`chats/`](chats/) as `.md` files (deliverable 3).
````

Things I need you to decide:
1. **The two licences above:** please confirm Silero's MIT and MMS's CC-BY-NC 4.0, or tell me what you find.
2. **The eval clip sources:** DECISIONS.md says only "audiobooks / podcasts chosen by Zaven" and doesn't name them. Do you want the README to name the sources, or keep it general as drafted?
3. **"Built with an AI assistant":** that's my wording for why `chats/` exists. Change it or drop it as you like.

Sources:
- [opus-mt-hy-en licence commit](https://huggingface.co/Helsinki-NLP/opus-mt-hy-en/commit/c1f5af969aee273f845a84ad3f4b149ba5435303)
- [silero-vad on PyPI](https://pypi.org/project/silero-vad)

---
**Sender:** Human
**Timestamp:** 2026-11-01T16:57:44.435547Z

No licence confirmation is needed we ended README,yes?

---
**Sender:** Assistant
**Timestamp:** 2026-11-01T16:57:54.502694Z

Nearly. Section 12 is drafted, and I'm taking your answer as approval with the licences as written. Section 13, the last one in the outline, is below. Once you approve it, I'll put the README together and write it to your folder.

## Draft: section 13 (Project documents)

```markdown
## Project documents

| File / folder | What it is |
|---|---|
| [DECISIONS.md](DECISIONS.md) | the single source of truth: working rules, every decision (D#) with its reason and the alternatives, milestones, risks, known limitations |
| [TEST.md](TEST.md) | the agreed tests, pass criteria, statuses and the results log |
| [`handovers/`](handovers/) | short notes passed from one working session to the next |
| [`chats/`](chats/) | all chat transcripts (`.md`) |
| [`scripts/`](scripts/) | one-time and diagnostic helpers: model download, FLEURS fetch, fixtures, reference drafting, ASR / MT diagnosis |

Raw command outputs (`command_outputs/`) stay on the development laptop and are
not committed (DECISIONS working rule 14).
```

**Still open, and needed before I write the file:**
1. **Section 12, eval clip sources:** keep the general wording ("public audiobooks and podcasts"), or name them?
2. **Section 12, the `chats/` sentence:** keep "built with an AI assistant", or drop it?

**Not blocking the README, but open from earlier:**
3. **The `�` note for L11 in DECISIONS.md:** yes or no?
4. **DECISIONS.md section 3** (milestone = README): you said we'd fix it later.

Once you answer 1 and 2 and approve section 13, I'll do the following:
- write `README.md` under a fresh file name here, copy it to your folder, read it back and compare byte for byte (the handover's stale-write warning);
- propose the commit for you to run:

```
git add README.md
git commit -m "README: setup, run, models, architecture, results, limitations, licences (M10)"
```

---
**Sender:** Human
**Timestamp:** 2026-11-01T16:59:06.768402Z

1. public audiobooks and podcasts
2. drop it

---
**Sender:** Assistant
**Timestamp:** 2026-11-01T17:01:02.337041Z

**Tool: Bash**
- command: mkdir -p /mnt/user-data/outputs/readme_m10_a && ca...
- description: Assemble the approved README sections into one fil...

**Tool Result: **

**Tool: Bash**
- command: cd /mnt/user-data/outputs/readme_m10_a; sed -i 's/...
- description: Replace a section-number reference with a link

**Tool Result: **

**Tool: mcp__remote-devices__device_commit_files**
- files: [{'devicePath': '/home/zaven/Desktop/arm_en_asr/RE...

**Tool Result: **

Now reading it back from your laptop to check it byte for byte.

**Tool: mcp__remote-devices__device_stage_files**
- paths: ['/home/zaven/Desktop/arm_en_asr/README.md']

**Tool Result: **

**Tool: Bash**
- command: cd /mnt/user-data; sha256sum uploads/arm_en_asr/RE...
- description: Compare read-back with local copy; make a fresh co...

**Tool Result: **

The read-back caught the stale-write bug the handover warned about. Your laptop got the version from before my last one-line edit. I'm writing it again from a fresh file name.

**Tool: mcp__remote-devices__device_commit_files**
- files: [{'devicePath': '/home/zaven/Desktop/arm_en_asr/RE...

**Tool Result: **

**Tool: mcp__remote-devices__device_stage_files**
- paths: ['/home/zaven/Desktop/arm_en_asr/README.md']

**Tool Result: **

**Tool: Bash**
- command: cd /mnt/user-data; cmp uploads/arm_en_asr/README.m...
- description: Compare read-back README with the intended file by...

**Tool Result: **

Yes, the README is finished. `README.md` is now in your project folder: 523 lines, all 13 sections as you approved them.

- **Changes beyond what you approved:** I put in your two answers (general wording for the clip sources, and the AI-assistant sentence dropped). I also made one small edit: in Measured results, "(section 3)" is now a link to the Requirements section, because the README headings have no numbers. I took your answers as approval of section 13 as drafted.
- **Write check:** the first copy to your laptop hit the stale-write bug from the handover and landed without that last edit. I wrote it again from a fresh file name and read it back. It now matches byte for byte. To check it yourself: `sha256sum README.md` should print `8bb2c8af0642d50c306ed6b889551fcd4394aaf591c668018421b44ffc05515f`.

**Proposed commit (for you to run):**
```
git add README.md
git commit -m "README: setup, run, models, architecture, results, limitations, licences (M10)"
```
If the earlier handover commit (DECISIONS.md, TEST.md, handover 009) hasn't been run yet, it's still pending as well.

**Still open for later:**
1. **DECISIONS.md section 3:** set the milestone to M10, README done. I'll propose the text when you're ready.
2. **L11 note about `�`:** I'd suggest a yes, since the README already describes it.
3. **The rest of M10:** a final test run and the TEST.md statuses.
