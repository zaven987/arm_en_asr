# Live Armenian → English transcription

A Python terminal app that listens to a microphone, writes down what is said in
Eastern Armenian, translates it into English, and prints both live. Each line
shows when the speech started (time since the session began) and how long it
took to appear. Everything runs locally on the laptop (speech recognition on its NVIDIA GPU, the rest on the CPU): after a one-time
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

## Requirements

- **Linux with PulseAudio.** Tested only on Ubuntu 22.04.5 with PulseAudio
  15.99.1 (not PipeWire). The app captures audio with `parec` and lists devices
  with `pactl`, both from the `pulseaudio-utils` package. Other setups are not
  tested.
- **[uv](https://docs.astral.sh/uv/)** to create the Python environments
  (tested with uv 0.13.6).
- **Python 3.10.12.** The pinned packages need 3.10 (D14).
- **An NVIDIA GPU with CUDA 12 support.** Speech recognition (Whisper) runs on the GPU (D30); tested on a GeForce MX550 (2 GB) with driver 580. The CUDA libraries (cuBLAS, cuDNN 9) come as pip packages in `requirements.txt` and the app loads them itself, so no CUDA toolkit install and no `LD_LIBRARY_PATH` are needed. Without a usable GPU the app stops with `GPU required (D30): ctranslate2 sees no CUDA device`; it never falls back to the CPU. VAD and translation run on the CPU.
- **Disk:** about 0.9 GB for the models in `models/`, plus the two Python
  environments (the app environment holds about 2.5 GB of NVIDIA CUDA libraries). The conversion environment contains a CPU-only PyTorch.
- **RAM:** the app needs about 1 GB of free RAM. This is an estimate: a peak of
  0.83 GB was measured with VAD + ASR loaded, before MT was added. The full
  measurement (load test T4) has not been run.
- **Internet:** only once, for `scripts/download_models.py` (Hugging Face and
  GitHub). After that the app runs fully offline and never downloads anything
  (D15).
- **A terminal font with Armenian letters,** e.g. DejaVu Sans Mono (see
  [Setup](#setup)).

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

## Models: chosen, alternatives, why

These are the **first-choice models**, picked to fit the laptop's RAM and to
work for sure. The planned bake-off that would choose the final models by
measurement (M7) has not been run, so none of these choices has been compared
against the alternatives on our data yet.

| Stage | Model | How it runs | Why |
|---|---|---|---|
| VAD (finds speech) | Silero VAD v6.2.1 (ONNX) | onnxruntime, CPU. A phrase ends after 0.6 s of silence; speech < 0.3 s is ignored; segments are capped at 7 s (D8, D26) | small, accurate, needs no PyTorch; taken from the official repo at a pinned tag (D24) |
| ASR (Armenian speech → text) | Whisper small, via faster-whisper | CTranslate2 `int8_float16` on the GPU (D30), language fixed to `hy`; greedy decoding (`beam_size=1`), `temperature=0`, no timestamps, token cap (D3, D26) | about 0.4 GB of GPU memory; about 5× faster than on the CPU (D29); accuracy on Armenian is weak, which we accept for now |
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
segments, which broke the 5 s limit. These settings were tuned on the CPU. Since D30 the same settings run on the GPU, where the slowest segment takes about 1 s instead of 4.7 s.

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
| Whisper large-v3-turbo on the MX550 GPU (D4, D7) | in the M7 bake-off | speed unknown on this GPU; Whisper small runs on it since D30 |
| Meta Omnilingual ASR CTC 300M (D4) | in the M7 bake-off | Armenian score unknown; needs fairseq2 |
| NLLB-200-distilled-600M for MT (D5) | in the M7 bake-off | usually better translations, but ~0.6–0.7 GB of RAM |
| One speech → English model, e.g. SeamlessM4T (D6) | rejected | we must show the Armenian text anyway, and SeamlessM4T is too big for this laptop |
| `sounddevice` / PortAudio for capture (D10) | rejected | cannot open PulseAudio monitor sources by exact name; `parec` can |
| The `silero-vad` pip package (D24) | rejected | requires PyTorch |
| Third-party pre-converted models (D23, D4) | rejected | we can't verify where they came from, so we convert them ourselves |

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

## Measured results

All measured on the development laptop ([Requirements](#requirements)), on the CPU, with the
current settings (D26) unless marked otherwise. The raw outputs stay on the
development laptop and are not in the repository (`command_outputs/`, working
rule 14); the key numbers are recorded in DECISIONS.md and TEST.md.

**Since D30 (2026-11-05) ASR runs on the GPU.** The turn-taking test (two devices, 164 s, 28 lines) gave median 1.3 s, max 1.8 s and 0 lines over 5 s, against max 5.9 s on the CPU (D29, D30). The CPU tables below are kept for comparison.

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
- **Tested on one laptop only** (L9). Ubuntu 22.04 with PulseAudio and an NVIDIA MX550.
  Other setups, PipeWire, and a live video call running at the same time have
  not been verified.
- **Out of scope by design:** no GUI, no installer, transcripts are not saved
  to a file (DECISIONS section 5).

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

All chat transcripts are in [`chats/`](chats/) as `.md` files (deliverable 3).

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
