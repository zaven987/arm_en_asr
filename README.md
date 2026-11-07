# Live Armenian → English transcription

A Python terminal app for online calls. It listens to two inputs at the same
time, your microphone and the call's system audio. It writes down what is said
in Eastern Armenian, translates it into English, and prints both live, with who
spoke. Your microphone is always "Me"; the other people on the call are told
apart by voice and labelled "Speaker 1", "Speaker 2", … Each line shows when
the speech started (time since the session began) and how long it took to
appear. Everything runs locally on the laptop: speech recognition runs on its
NVIDIA GPU and everything else on the CPU. After a one-time model download, it
needs no internet and no cloud service.

    [00:00:03] Speaker 1:  Բարև, ինչպե՞ս ես
               → Hi, how are you?   (0.8s)

*(This shows the line format; it is not output from a real run. Real output is
in [Measured results](#measured-results).)*

The target is at most 5 s from the end of a spoken phrase to its English line,
on a ThinkPad E16 (Intel i5-1335U, 7.4 GiB RAM, GeForce MX550 with 2 GB). In
the latency test with both inputs, the slowest line took 0.9 s. Since the
switch to FastConformer, the English translation is the weakest part (see
[Known limitations](#known-limitations)).

## Status at a glance

Status on 2026-11-07. Milestone numbers (M#) and decision numbers (D#) refer to
[DECISIONS.md](DECISIONS.md); test ids (T#) refer to [TEST.md](TEST.md).

| Part | Status |
|---|---|
| Live microphone capture (`--mic`) | works |
| Live system-audio capture (`--system`, a PulseAudio `.monitor` source) | works (M5) |
| Both inputs at the same time, one shared session clock | works (M5) |
| File mode (`--mic-wav`, `--system-wav`, for tests) | works |
| Speech detection (VAD) → Armenian text (ASR) → English (MT) → terminal line with latency | works |
| ASR: NVIDIA Armenian FastConformer (CTC) on the GPU | works (M7, D34); replaced Whisper small |
| Speaker labels for system audio ("Speaker N", diarizer) | works (M6), with known limits ([L13, L14](#known-limitations)) |
| `quit`, Ctrl+C, clear errors (unknown device, missing model, lost device, no GPU) | works |
| MT bake-off (opus-mt vs NLLB-200) | not done yet (M7, next) |

| Test | What it checks | Status |
|---|---|---|
| T1.1–T1.5 | each module on its own (capture + VAD, ASR, MT, line format, pipeline) | passed |
| T1.6 | diarizer: rules on made-up vectors, one label per solo clip, the 2-speaker clip | passed (the 2-speaker clip was used for tuning, so it is not an independent check) |
| T6 | the app fails loudly on bad input; a short `--system-wav` run works | passed |
| T2 | end-to-end latency ≤ 5 s, file mode, both inputs taking turns | passed |
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
- **An NVIDIA GPU with CUDA 12 support and `nvidia-smi`.** Speech recognition
  runs on the GPU through the CUDA build of sherpa-onnx (D34). Tested on a
  GeForce MX550 (2 GB) with driver 580.
  - The CUDA libraries (cuBLAS, cuDNN 9, the CUDA runtime, cuFFT, cuRAND) come as
    pip packages in `requirements.txt`, and the app loads them itself. So there
    is no CUDA toolkit to install and no `LD_LIBRARY_PATH` to set.
  - The model uses about 0.6 GB of GPU memory at load and grew to about 1.1 GB
    while decoding our test clips.
  - Without a usable GPU the app stops with
    `GPU required (D30, D34): no CUDA device found`.
  - If the model did not actually land on the GPU, the app stops with
    `FastConformer did not load onto the GPU: …`. It checks its own GPU
    memory with `nvidia-smi` for this.
  - It never falls back to the CPU. VAD, translation and the diarizer run on
    the CPU.
- **RAM:** about 1.5 GB free. The app's peak was 1.46 GB in the latency test
  with both inputs and the diarizer (T2). The load test (T4) has not been run.
- **Disk:** about 1.5 GB for `models/`. This includes the two original
  checkpoints the script converts from: the FastConformer `.nemo` file
  (0.46 GB) and opus-mt (0.3 GB). On top of that come the three Python
  environments. The app environment holds about 2.5 GB of NVIDIA CUDA
  libraries. The two one-time environments contain a CPU-only PyTorch, and
  `.venv-nemo` also holds NeMo.
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
and never edited by hand (D14). The CUDA build of sherpa-onnx is not on PyPI.
`requirements.txt` therefore carries a `--find-links` line pointing to the
sherpa-onnx wheel page. When regenerating the file, keep that line:

```bash
uv pip compile --emit-find-links requirements.in -o requirements.txt   # without --emit-find-links the line is dropped
uv pip sync requirements.txt                                            # update an existing .venv exactly
```

### 2. Conversion environment (`.venv-convert`, needed once)

The translation model has to be converted once to the CTranslate2 format. The
converter needs PyTorch, so it gets its own environment and PyTorch never
enters the app environment (D23).

```bash
uv venv .venv-convert --python 3.10
uv pip install --python .venv-convert --torch-backend cpu -r requirements-convert.txt
```

### 3. Export environment (`.venv-nemo`, needed once)

The speech-recognition model comes as a NeMo checkpoint. We export its CTC part
to ONNX ourselves (D31). The export needs NVIDIA NeMo and PyTorch (CPU-only),
so it also gets its own environment.

```bash
uv venv .venv-nemo --python 3.10
uv pip install --python .venv-nemo --torch-backend cpu -r requirements-nemo.txt
```

The export runs once, on the CPU, and peaked at about 3.2 GB of RAM, so close
the browser while it runs. You don't need to activate either of these two
environments: the download script calls them directly.

### 4. Download the models (needs internet, once)

With `.venv` active:

```bash
python scripts/download_models.py
```

This puts everything into `models/` (gitignored), at pinned versions (D15, D24,
D27, D31):

| Model | Source | Folder |
|---|---|---|
| NVIDIA FastConformer hybrid, Armenian (original `.nemo`, SHA-256 checked) | `nvidia/stt_hy_fastconformer_hybrid_large_pc` @ `353b409` | `models/src/fastconformer-hy/` |
| FastConformer CTC head as ONNX (`model.onnx`, used by the app; `model.int8.onnx`, not used; `tokens.txt`) | made by the script with `scripts/export_fastconformer.py` in `.venv-nemo` | `models/fastconformer-hy-ctc/` |
| opus-mt-hy-en (MT), original | `Helsinki-NLP/opus-mt-hy-en` @ `79b0a50` | `models/src/opus-mt-hy-en/` |
| opus-mt-hy-en, converted to CTranslate2 int8 | made by the script, using `.venv-convert` | `models/opus-mt-hy-en-ct2-int8/` |
| WeSpeaker ResNet34 speaker embedding (diarizer, SHA-256 checked) | `csukuangfj/speaker-embedding-models` @ `0743f30` | `models/speaker-embedding/` |
| Silero VAD v6.2.1 (ONNX) | GitHub `snakers4/silero-vad`, tag `v6.2.1` | `models/silero_vad.onnx` |

Models that are already there are skipped. Any failure, including a SHA-256
mismatch, stops the script with `ERROR:` and exit code 1. The export checks
itself: the ONNX model must give exactly the same text as NeMo on a test clip.
The script prints the SHA-256 of `silero_vad.onnx`; it should be
`1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3`.

If a model is missing later, the app stops with an error naming the file. It
never downloads anything itself.

### 5. Terminal font for Armenian

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

### Find your devices

```bash
python app.py --list-devices
```

This prints `pactl list short sources`. The second column is the exact name to
use.
- Microphones are usually `alsa_input.…`.
- Names ending in `.monitor` are system audio: what the laptop plays. For a
  call, use the monitor of the output the call plays through.

Example from the development laptop (shortened):

```
7  alsa_input.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__hw_sofhdadsp__source     …
8  alsa_input.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__hw_sofhdadsp_6__source   …
6  alsa_output.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__hw_sofhdadsp__sink.monitor …
```

### Live: microphone and system audio

```bash
python app.py --mic "<exact microphone name>" --system "<exact monitor name>"
```

- Either input may be left out: `--mic` alone transcribes only you, and
  `--system` alone only the call.
- The names must match exactly; otherwise the app stops with
  `unknown device for --mic` / `--system` (D11).
- Giving the same device twice is an error.
- Loading the models takes a few seconds. Then the app prints
  `listening on mic: …, system: …` and starts.
- Transcript lines go to stdout and all other messages go to stderr.

**Use headphones.** With loudspeakers the call audio also reaches the
microphone and comes out a second time as "Me" lines (L1).

### Reading the output

```
[00:00:56] Speaker 2:  Արարի ճիշտ ձեւակերպ եմ ավելի դա, դա մոտավորապես ճիշտ տեղեկատվություն է, Հայաստանի ակտիվ։
           → I'm going to write it correctly, it's about right information, and it'll be active in Armenia.   (0.3s)
```

(a real line from the latency test, with real ASR and MT errors)

- `[00:00:56]`: when the speech started, counted from the start of the session.
- `Speaker 2`: the speaker.
  - Microphone lines are always "Me" (L6).
  - System-audio speakers are numbered in the order they first speak, and keep
    their number for the whole session. They are not remembered between
    sessions.
- First line: Armenian text (ASR). Second line: English translation (MT).
- `(0.3s)`: latency, from the end of the phrase to this line being printed.
  The 0.6 s of silence that marks the end of a phrase is counted inside it
  (D12).
- `(5.3s ⚠ >5s)`: a line slower than 5 s gets a warning. The app keeps running.
- A line appears only after the speaker pauses (0.6 s of silence) or after 7 s
  of continuous speech, whichever comes first. Long speech without pauses is
  split every 7 s, sometimes mid-word (L4).
- Lines print in the order each phrase *ended*. When both sides talk at once,
  a later start time can print before an earlier one (L5).

### Stopping

| How | Result | Exit code |
|---|---|---|
| type `quit` + Enter | lines already captured are still printed, then `stopped` | 0 |
| Ctrl+C | the same clean shutdown | 130 |
| Ctrl+C again while shutting down | stops at once | 130 |
| an error (either device lost, model or pipeline error) | lines already captured are printed, then `ERROR: …` | 1 |

Any other text typed gives `unknown command: '<text>'` and the app keeps running.

### File mode (tests only)

```bash
python app.py --mic-wav <mic.wav> --system-wav <system.wav>
```

- Either file may be left out.
- The WAVs are fed in at real-time speed, as if someone were speaking, so the
  measured latency compares with live use (D21).
- They must be 16 kHz mono 16-bit PCM; otherwise the app stops with an error.
- The app ends by itself (exit 0) once every file has ended and every line is
  printed; `quit` stops it early.

## Tests

Tests use pytest. With `.venv` active, from the repository root:

```bash
python -m pytest -v                                  # default suite
python -m pytest tests/test_asr.py -v                # one file
python -m pytest -m eval tests/test_diarizer.py -v -s   # T1.6 on the evaluation clips
```

The default suite has 63 tests (T1.1–T1.6 and T6) and runs in under 20 s.

**What it needs:**
- the models in `models/` (see [Setup](#setup));
- the NVIDIA GPU: T1.2 and T6 run the real speech-recognition model;
- PulseAudio running with at least one source. T6 starts the app on a real
  source but needs nobody speaking.

A missing model, fixture or GPU makes a test **fail** with a clear error.
Tests are never skipped silently (D22). `tests/conftest.py` creates and frees
the speech-recognition model once before any test is collected. This sets the
library load order the GPU model needs (see
[Architecture](#architecture), D33).

**What is in the repository and what is not:**

| Data | In the repo? | Used by |
|---|---|---|
| `tests/fixtures/` (two short FLEURS clips, 5 s of silence) | yes | default suite |
| `eval/meta/*.csv` (reference Armenian + English text) | yes | T1.3 uses the FLEURS CSV; T1.6 uses `sys_01.csv` |
| `eval/clips/*.wav` (our 4 evaluation clips: `mic_01`–`03`, `sys_01`; plus the turn files made from them) | **no** (gitignored) | T1.6 (`eval` marker), T2, the diagnostic scripts |
| `eval/fleurs/` (FLEURS audio) | no (gitignored); `python scripts/fetch_fleurs.py` downloads it | M7 evaluation, `scripts/make_fixtures.py` |

So a fresh clone can run the whole default suite. The `eval` tests and T2 need
the clips that are not in the repo.

**T2 (end-to-end latency)** is a manual run, not a pytest test. First build the
turn files from `mic_01` and `sys_01`: one side talks at a time, as in a call.
Then play them through the app:

```bash
python scripts/make_turns.py
python app.py --mic-wav eval/clips/turns_mic.wav --system-wav eval/clips/turns_sys.wav
```

It passes if every printed line shows latency ≤ 5 s. The result is recorded in
TEST.md.

**Markers:** `hardware` (real devices and a person present, T3), `slow` (load
test, T4) and `eval` (needs the gitignored clips) are left out of a plain run
(`pytest.ini`). The tests for `hardware` and `slow` have not been written yet,
so `python -m pytest -m hardware` and `-m slow` find nothing today.

Full test list, pass criteria and the results log: [TEST.md](TEST.md).

## Models: chosen, alternatives, why

| Stage | Model | How it runs | Why |
|---|---|---|---|
| VAD (finds speech) | Silero VAD v6.2.1 (ONNX) | onnxruntime, CPU, one per input. A phrase ends after 0.6 s of silence; speech < 0.3 s is ignored; segments are capped at 7 s (D8, D26) | small, accurate, needs no PyTorch; taken from the official repo at a pinned tag (D24) |
| ASR (Armenian speech → text) | NVIDIA `stt_hy_fastconformer_hybrid_large_pc`, CTC head, fp32 | exported to ONNX by us; sherpa-onnx (CUDA build) on the GPU, greedy CTC decoding (D31, D34) | Armenian-only, ~115 M parameters, outputs punctuation and capitals; cannot fall into repeat loops; about 0.1 s per segment. See below |
| MT (Armenian → English) | Helsinki-NLP opus-mt-hy-en (Marian) | converted to CTranslate2 int8, CPU, 2 threads, `beam_size=2`, `no_repeat_ngram_size=3` (D5) | about 0.1 GB of RAM. The weakest part today; NLLB-200 is the next candidate (M7) |
| Diarizer (who is speaking, system audio only) | WeSpeaker ResNet34 speaker embedding (trained on VoxCeleb) + our own online clustering | sherpa-onnx, CPU, 1 thread, beside ASR (D27) | best separation of the two models measured (CAM++ rejected); about 0.24 s per segment, runs in parallel with ASR. See below |

**Why we replaced Whisper small with FastConformer (D25, D31, D34).** The app
started with Whisper small. The M1 smoke run showed the pattern: Whisper heard
the speech but spelled it phonetically (CER ≈ 12 % but WER ≈ 56 % on one FLEURS
clip). Once the app was built, Whisper's repeat loops («եմ եմ եմ …») and
latency became the main problem, and its CER on our clips was 32.4 %. Keeping
it under 5 s took a token cap, a ` ...` marker on cut lines, and a move to the
GPU. FastConformer fixes all three.
- **It cannot loop.** A CTC model labels each 80 ms of audio once, so its
  output can never be longer than the audio allows.
- **Its cost depends only on the audio length.** It costs one pass over the
  audio, whatever the text.

On the same audio, word errors fell from 84.5 % to 25.5 % and character errors
from 32.8 % to 9.7 %. ASR time per segment fell from up to 1.6 s to up to
0.12 s (see [ASR accuracy](#asr-accuracy-whisper-small-vs-fastconformer)).

The model was trained partly on FLEURS, so it is measured on our own clips
only, never on FLEURS (D4, D31). The int8 export gave the same accuracy but was
slower on this GPU, so the app uses fp32 (D31 F5).

**How the diarizer labels speakers (D27).** Each system-audio segment is turned
into a voice fingerprint (a 256-number embedding). Each speaker has a
*centroid*: the average fingerprint of their longer segments.
- **A segment with at least 2 s of speech** joins the most similar speaker if
  the similarity (cosine) is at least 0.76, and updates that speaker's
  centroid. Otherwise it starts a new "Speaker N".
- **A shorter segment** is too unreliable to start a speaker. It joins the
  nearest existing speaker and never changes a centroid.
- **The threshold 0.76 was tuned** on our only 2-speaker recording, so its
  result there is not an independent check (L14).

**Why `no_repeat_ngram_size=3` for MT (D5).** opus-mt itself (not our
conversion) can fall into a loop on some inputs, e.g. «6-6-6-…-a-a-a-…». This
setting was the only tested fix that stopped the loop without slowing it down.
The price: the English for one segment can't repeat the same 3 tokens, even
when the speaker really did.

### Alternatives considered

| Alternative | Decision | Why |
|---|---|---|
| Whisper small (faster-whisper) for ASR (D3, D26, D32) | used first, **replaced** (D34) | repeat loops; needed a token cap and the GPU to stay under 5 s; WER 84.5 % vs 25.5 %, CER 32.8 % vs 9.7 % on the same segments ([ASR accuracy](#asr-accuracy-whisper-small-vs-fastconformer)) |
| FastConformer int8 on the GPU (D31 F5) | rejected | the same CER as fp32, but about 1.8× slower on this GPU |
| FastConformer with plain onnxruntime and our own audio features (D31) | rejected | the features must match NeMo's exactly; more code and a risk of silent accuracy loss; sherpa-onnx does both |
| CAM++ speaker embedding (D27 J7) | rejected | 3× faster than ResNet34, but it put the wrong speaker nearest on 4 of 31 mic segments and 5 of 16 on the 2-speaker clip |
| BuzzASR/armenian, Whisper large-v3-turbo, Meta Omnilingual ASR (D4) | not run | FastConformer met the targets first; BuzzASR is likely too big for this laptop |
| NLLB-200-distilled-600M for MT (D5) | next (M7 MT bake-off) | usually better translations, but ~0.6–0.7 GB more RAM |
| One speech → English model, e.g. SeamlessM4T (D6) | rejected | we must show the Armenian text anyway, and SeamlessM4T is too big for this laptop |
| `sounddevice` / PortAudio for capture (D10) | rejected | cannot open PulseAudio monitor sources by exact name; `parec` can |
| The `silero-vad` pip package (D24) | rejected | requires PyTorch |
| Third-party pre-converted / pre-exported models (D23, D4) | rejected | we can't verify where they came from, so we convert and export them ourselves |

## Architecture

One process, threads and queues (D1). Separate processes would each load their
own copy of the models and run out of RAM. The model libraries (sherpa-onnx,
CTranslate2, onnxruntime) release Python's GIL, so the threads really run in
parallel.

```
[parec mic] ──► VAD ──┐
                      ├──► segments ──► ASR worker ──► MT ──────┐
[parec sys] ──► VAD ──┘   (one queue)  (FastConformer, (opus-mt) ├──► output: join by segment id,
                              │         GPU)                     │    order, latency, print
                              └──► diarizer (system segments only, ResNet34, CPU) ─┘
stdin reader: "quit" → clean shutdown
```

**Segment:** the unit that moves through the pipeline:
`{id, device, start, end, audio, end_wall}`.
- `device`: `mic` or `system`.
- `start` / `end`: the first and last speech sample, in seconds from session
  start. One session clock is shared by both inputs. Each input adds its own
  start offset, because the two `parec` processes do not start at the same
  instant.
- `audio`: 16 kHz mono float32.
- `end_wall`: when the last speech audio arrived; latency is measured from it.

| Module (`src/arm_en_asr/`) | Does |
|---|---|
| `audio_capture.py` | runs `parec` (or reads a WAV at real-time speed), runs Silero VAD on 32 ms windows, cuts Segments (0.6 s silence ends one, 7 s cap); `Capture` runs one thread per input |
| `asr.py` | Segment audio → Armenian text (FastConformer CTC via sherpa-onnx on the GPU; loads the CUDA libraries; checks that the model is really on the GPU) |
| `translate.py` | Armenian text → English (opus-mt, CTranslate2) |
| `diarizer.py` | system-audio Segment → "Speaker N" (embedding + online clustering) |
| `pipeline.py` | owns the queues and threads (ASR worker → one MT thread, diarizer thread beside them → one output thread), joins results by segment id, measures latency, stops loudly on any worker error |
| `output.py` | formats and prints the terminal line |
| `app.py` | command line, device and model checks, starts and stops everything |

**Print order (D13):** each segment gets a number when its end is detected, and
lines print in that order. A finished line waits until every earlier one is
printed. A segment with no ASR text is skipped and prints no line.

**Shutdown:** `quit` or Ctrl+C stops capture first, then lets the pipeline
finish every segment already captured, so no captured speech is lost. If either
device is lost, the whole session ends the same way, with exit code 1. Queues
are unbounded and nothing is dropped: if the pipeline is too slow, lines arrive
late (with the `⚠ >5s` warning) instead of being skipped.

**Note for developers: library load order (D33).** The app runs two different
onnxruntime builds in one process: Silero uses onnxruntime 1.23.2, and the CUDA
build of sherpa-onnx brings its own 1.28.2. Creating the first GPU recognizer
*after* `onnxruntime` was imported crashed with a segmentation fault. So:
- `app.py` builds the ASR before it imports `audio_capture` (which imports
  onnxruntime for Silero).
- `tests/conftest.py` does the same for pytest.
- `Asr` refuses with a clear `D33:` error if the order is wrong, instead of
  crashing.
- Any new script that uses both must create the recognizer first. After that,
  any order works.

The full design record, with the reasons for each choice, is in
[DECISIONS.md](DECISIONS.md) (section 8 and D1–D34).

## Measured results

All measured on the development laptop ([Requirements](#requirements)). The raw
outputs stay on the development laptop and are not in the repository
(`command_outputs/`, working rule 14); the key numbers are recorded in
DECISIONS.md and TEST.md.

### Latency (T2, turn files, both inputs)

`python app.py --mic-wav eval/clips/turns_mic.wav --system-wav eval/clips/turns_sys.wav`:
164 s, the mic and the system side taking turns (13 turns), fed at real-time
speed, with the real diarizer.

| ASR | Lines | Median | p95 | Max | Lines > 5 s | Peak RSS |
|---|---|---|---|---|---|---|
| **FastConformer CTC, GPU (now, D34)** | 28 | 0.8 s | 0.9 s | 0.9 s | 0 | 1463 MB |
| Whisper small, GPU (before, M6) | 28 | 1.3 s | 1.6 s | 1.6 s | 0 | 1079 MB |

Whisper run: Zoom tab open, laptop plugged in (the demo condition, DECISIONS
section 7). Swap was already full before both runs (R17); latency was not
affected. The Whisper run had 1 of 28 lines cut by the token cap; FastConformer
has no cap.
<!-- TODO (Zaven): confirm the Zoom tab was open and the laptop plugged in for the FastConformer run (m7_f6c_t2_turns.txt). -->

Labels in the same run: every mic line was "Me" (12). The system lines were
Speaker 1 (9) and Speaker 2 (7), in the order of the two people in `sys_01`.

The case where both sides talk at once for a long time is not T2. It was
measured separately (M5), and there lines queue up well past 5 s (L12).

### ASR accuracy: Whisper small vs FastConformer

Both models on exactly the same 47 segments (our 4 clips, cut by the app's VAD
at the 7 s cap), in one run of `scripts/diag_wer.py` (2026-11-07). Whisper ran
with its last app setting: GPU `int8_float16`, beam 5, repetition penalty 1.1,
token cap (D32). FastConformer ran with the app setting: CTC fp32 on the GPU
(D34). Lower is better.

| | `mic_01` | `mic_02` | `mic_03` | `sys_01` | all (pooled) | mean of clips |
|---|---|---|---|---|---|---|
| **WER**, Whisper small | 85.5 % | 78.7 % | 84.4 % | 87.9 % | 84.5 % | 84.1 % |
| **WER**, FastConformer | **22.1 %** | **15.7 %** | **24.0 %** | **36.9 %** | **25.5 %** | **24.7 %** |
| CER, Whisper small | 36.0 % | 21.0 % | 29.4 % | 43.3 % | 32.8 % | 32.4 % |
| CER, FastConformer | **8.2 %** | **5.0 %** | **6.9 %** | **17.4 %** | **9.7 %** | **9.4 %** |

| | Whisper small | FastConformer |
|---|---|---|
| Max ASR time per segment | 1.6 s | 0.12 s |
| Total ASR time, 47 segments | 47.1 s | 3.7 s |
| Segments caught in a repeat loop | 2 of 47 | none possible (CTC) |

- **WER** (word error rate): the share of reference words that are wrong,
  missing or extra. One wrong letter makes the whole word wrong.
- **CER** (character error rate): the same, counted in letters.
- Before both, the texts are lowercased and only Armenian letters and spaces
  are kept, so punctuation does not count.
- References: 498 words, 3316 characters. They are our hand-corrected,
  verbatim transcripts (`eval/meta/`).
- Pooled = all edits divided by all reference words or letters. Mean = the
  average of the four clips.
- The timing rows come from the earlier speed runs on the same segments (D31
  F5, D32).

Whisper's WER is much higher than its CER. Most of its words were close but
misspelled, which is the pattern the M1 smoke run first showed. FastConformer
cut the word errors to about a third (84.5 % → 25.5 %) and the character
errors to under a third (32.8 % → 9.7 %). The conversational clip `sys_01` is
the hardest for both.

### Diarizer (T1.6)

| Clip | Result |
|---|---|
| `mic_01`, `mic_02`, `mic_03` (one reader each) | each clip got one speaker label on 100 % of its segments |
| `sys_01` (89 s, 2 people) | 16 of 16 segments correct, 2 speakers found, short segments 3 of 3 |

`sys_01` is our only 2-speaker recording, and the threshold was tuned on it, so
100 % there is expected by construction. It is not an independent check (L14).

### Other

- Default test suite: 63 passed (2026-11-06).
- ASR time per segment: median 0.10 s, max 0.12 s on the GPU (47 segments).
- Diarizer: about 0.24 s per segment on the CPU, in parallel with ASR.
- MT: about 0.2 s per sentence (M1 smoke run).

## Known limitations

L-numbers refer to DECISIONS.md section 12.

**Quality**
- **Weak MT** (L10). opus-mt often gives fluent English with the wrong meaning,
  even on correct Armenian; see the example in
  [Reading the output](#reading-the-output). This is the weakest part today.
  The next step is to measure it against NLLB-200 (M7).
- **ASR errors remain.** They are worse on conversational speech than on read
  speech: `sys_01` CER 17.4 %, against 5–8 % on the read mic clips.
- **Code-switching** (L3). Russian or English words inside Armenian speech are
  processed as Armenian and often come out wrong.

**Diarizer**
- **The first sound of a session** (L13). Until "Speaker 1" has a centroid
  (an average voice built from segments of at least 2 s), the first such
  segment joins Speaker 1 with no check and starts its centroid. Suppose the
  call's first sound is short and from one person (A says "yes"), and the
  first longer speech is from another person (B). Then A and B are both
  "Speaker 1", and Speaker 1 becomes B's voice.
- **Threshold fitted on one recording** (L14). The threshold 0.76 works on
  `sys_01` only between 0.72 and 0.80. On other calls and voices, two people
  may be merged into one speaker, or one person split into two. There is no
  untouched recording to check it.
- **Short turns** (D27 J8). A segment with less than 2 s of speech never starts
  a new speaker. A new person whose first turns are all short gets an existing
  label until they say something longer.
- **1–2 remote speakers** (L8). Tested with two remote speakers only.

**Segmenting and timing**
- **7 s segment cap** (L4). Long speech without pauses is cut every 7 s,
  possibly mid-word. The first letters after a cut are sometimes lost, which
  hurts both ASR and MT.
- **Both sides talking at once** (L12). If the mic and the call both carry
  speech for a long stretch, segments arrive faster than they are processed,
  and latency grows well past 5 s. Normal turn-taking is fine (T2).
- **Lines out of time order** (L5). Lines print in the order phrases *ended*,
  so with two inputs a later start time can print first.
- **Final lines only** (L7). Nothing appears while someone is speaking; a line
  comes after a 0.6 s pause or at the 7 s cap.
- **Late, not dropped.** If the pipeline falls behind, lines queue up and
  arrive late with the `⚠ >5s` warning; nothing is skipped.

**Setup and environment**
- **Mic is always "Me"** (L6), even if someone else speaks into it.
- **Echo** (L1, will not fix). With speakers instead of headphones, call audio
  leaks into the mic and shows up as extra "Me" lines. Use headphones.
- **Overlapping speech** (L2). No special handling.
- **NVIDIA GPU required.** There is no CPU mode by design (D30, D34).
- **Tested on one laptop only** (L9). Ubuntu 22.04 with PulseAudio and an
  NVIDIA MX550. Other setups and PipeWire have not been verified, and the
  capture test on real devices (T3) has not been run.
- **Out of scope by design:** no GUI, no installer, transcripts are not saved
  to a file (DECISIONS section 5).

## What we'd improve with more time

Roughly in the order we would do it.

1. **MT bake-off (M7):** opus-mt against NLLB-200-distilled-600M. We'd score
   MT alone on FLEURS reference text (chrF / BLEU plus a manual rating), and
   separately ASR + MT on our clips. MT is now the weakest measured point.
2. **An independent diarizer check:** a new 2-speaker recording that the
   threshold was not tuned on (L14), and a look at the first-sound rule (L13).
3. **Quality pass (M8):** a 10 s segment cap was slightly more accurate than
   7 s (mean CER 8.5 % vs 9.4 %). It also changes the diarizer's segments, so
   it would be tested with T1.6 and MT. Cutting at a pause instead of at a hard
   cap would help too.
4. **T3 and T4:** capture from real devices with a person present, and the load
   test to choose how many segments to process in parallel.
5. **Virtual-sink test (M9, T5):** play a clip into a PulseAudio null sink, so
   the system-audio path can be tested without a real call.
6. **Partial text** while someone is still speaking (DECISIONS section 6).

## Licences and attribution

### Models

| Model | Used for | Licence | Source |
|---|---|---|---|
| NVIDIA `stt_hy_fastconformer_hybrid_large_pc` | ASR (app); CTC head exported by us to ONNX | CC-BY-4.0 | [nvidia/stt_hy_fastconformer_hybrid_large_pc](https://huggingface.co/nvidia/stt_hy_fastconformer_hybrid_large_pc) |
| opus-mt-hy-en (Helsinki-NLP, OPUS-MT) | MT (app); converted by us to CTranslate2 int8 | Apache-2.0 | [Helsinki-NLP/opus-mt-hy-en](https://huggingface.co/Helsinki-NLP/opus-mt-hy-en) |
| WeSpeaker ResNet34 (`wespeaker_en_voxceleb_resnet34.onnx`) | diarizer (app) | CC-BY 4.0 (follows its training data, VoxCeleb) | WeSpeaker; the copy at [csukuangfj/speaker-embedding-models](https://huggingface.co/csukuangfj/speaker-embedding-models) |
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

Each package's licence is in its own metadata. The app's main ones are
sherpa-onnx, CTranslate2, onnxruntime, sentencepiece and numpy
(`requirements.in`). NVIDIA NeMo and PyTorch are used only in the one-time
export and conversion environments, never by the app.

### Chat transcripts

All chat transcripts are in [`chats/`](chats/) as `.md` files (deliverable 3).

## Project documents

| File / folder | What it is |
|---|---|
| [DECISIONS.md](DECISIONS.md) | the single source of truth: working rules, every decision (D#) with its reason and the alternatives, milestones, risks, known limitations |
| [TEST.md](TEST.md) | the agreed tests, pass criteria, statuses and the results log |
| [`handovers/`](handovers/) | short notes passed from one working session to the next |
| [`chats/`](chats/) | all chat transcripts (`.md`) |
| [`scripts/`](scripts/) | one-time and diagnostic helpers (below) |

| Script | What it does |
|---|---|
| `download_models.py` | downloads and converts / exports every app model (Setup step 4) |
| `export_fastconformer.py` | FastConformer CTC head → ONNX, runs in `.venv-nemo` (called by `download_models.py`) |
| `fetch_fleurs.py`, `make_fixtures.py` | FLEURS subset and the test fixtures |
| `download_mms.py`, `draft_mms.py` | MMS drafts of the reference texts |
| `make_turns.py` | the turn-taking files for T2 |
| `diag_fastconformer.py`, `check_fc_gpu.py` | FastConformer accuracy and speed on our clips; GPU checks |
| `diag_wer.py` | Whisper vs FastConformer WER and CER on the same segments (needs faster-whisper, see the script) |
| `diag_embed.py`, `tune_diarizer.py` | speaker-embedding measurement and the threshold sweep |
| `diag_mt.py` | the opus-mt loop diagnosis |
| `diag_asr.py`, `diag_two_devices.py`, `smoke_m1.py` | Whisper-era measurements, kept as the record; they need faster-whisper, which the app environment no longer has |

Raw command outputs (`command_outputs/`) stay on the development laptop and are
not committed (DECISIONS working rule 14).
