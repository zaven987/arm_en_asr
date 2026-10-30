"""Draft Armenian reference text for an eval clip with Meta MMS-1B-all (D18). Helper only, not the app.

Run from the repo root with .venv-convert active (offline is fine), after scripts/download_mms.py:
    python scripts/draft_mms.py eval/clips/mic_01.wav [eval/clips/sys_01.wav ...]

For each clip (16 kHz mono 16-bit PCM WAV named mic_NN.wav or sys_NN.wav, D17) it:
  - cuts the audio into ~15 s windows, each cut at the quietest 0.1 s frame between 12 and 18 s
    (one long pass over 60-90 s would need several GB of RAM),
  - transcribes each window with MMS-1B-all + the Armenian adapter (hye),
  - writes eval/clips/<name>.draft.csv (gitignored) in the D18 columns:
    start,end = window times; armenian = draft; device from the file name;
    speaker = "Me" for mic clips, blank for system clips; english blank.
The draft has no capitals and no punctuation. Zaven corrects it, adds punctuation, splits it into
speaker turns with times and saves eval/meta/<name>.csv (D18).
An existing draft is never overwritten. Any failure stops with "ERROR:" and exit code 1.
"""
import csv
import os
import resource
import sys
import time
import wave
from pathlib import Path

import numpy as np

os.environ["HF_HUB_OFFLINE"] = "1"  # never download here; scripts/download_mms.py does that
os.environ["TRANSFORMERS_OFFLINE"] = "1"

ROOT = Path(__file__).resolve().parent.parent
MMS_DIR = ROOT / "models" / "mms-1b-all"
MMS_REQUIRED = ["config.json", "preprocessor_config.json", "tokenizer_config.json", "vocab.json",
                "model.safetensors", "adapter.hye.safetensors"]
LANG = "hye"
RATE = 16000
WIN_MIN_S, WIN_MAX_S = 12.0, 18.0  # cut window, target ~15 s
FRAME_S = 0.1                      # energy frame used to find the quietest cut point
DEVICE_BY_PREFIX = {"mic_": "mic", "sys_": "system"}
COLUMNS = ["start", "end", "device", "speaker", "armenian", "english"]


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def device_for(path: Path) -> str:
    for prefix, device in DEVICE_BY_PREFIX.items():
        if path.name.startswith(prefix):
            return device
    fail(f"{path.name}: name must start with mic_ or sys_ (D17) so the device role is known")


def read_pcm16_wav(path: Path) -> np.ndarray:
    if not path.is_file():
        fail(f"{path} not found")
    with wave.open(str(path), "rb") as w:
        ch, width, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        if (ch, width, rate) != (1, 2, RATE):
            fail(f"{path} is {rate} Hz / {ch} ch / {8 * width} bit; expected 16000 Hz mono 16-bit (D18)")
        data = w.readframes(n)
    audio = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0
    if len(audio) == 0:
        fail(f"{path} has no audio")
    return audio


def cut_points(audio: np.ndarray) -> list[tuple[int, int]]:
    """Windows (start, end) in samples, each cut at the quietest frame between 12 and 18 s."""
    frame = int(FRAME_S * RATE)
    lo, hi = int(WIN_MIN_S * RATE), int(WIN_MAX_S * RATE)
    windows, pos, n = [], 0, len(audio)
    while n - pos > hi:
        starts = np.arange(pos + lo, pos + hi - frame + 1, frame)
        rms = [float(np.sqrt(np.mean(audio[s:s + frame] ** 2))) for s in starts]
        cut = int(starts[int(np.argmin(rms))]) + frame // 2
        windows.append((pos, cut))
        pos = cut
    windows.append((pos, n))
    return windows


def load_model():
    missing = [f for f in MMS_REQUIRED if not (MMS_DIR / f).is_file()]
    if missing:
        fail(f"MMS model files missing in {MMS_DIR}: {', '.join(missing)} "
             "(run python scripts/download_mms.py first)")
    import torch  # imported here: only needed once the inputs are known to be valid
    from transformers import AutoProcessor, Wav2Vec2ForCTC

    print(f"[mms] loading {MMS_DIR.relative_to(ROOT)} with adapter '{LANG}' (fp32, ~4 GB RAM) ...")
    t0 = time.time()
    processor = AutoProcessor.from_pretrained(str(MMS_DIR), target_lang=LANG)
    model = Wav2Vec2ForCTC.from_pretrained(str(MMS_DIR), target_lang=LANG, ignore_mismatched_sizes=True)
    model.eval()
    print(f"[mms] loaded in {time.time() - t0:.1f} s")
    return torch, processor, model


def transcribe(torch, processor, model, chunk: np.ndarray) -> str:
    inputs = processor(chunk, sampling_rate=RATE, return_tensors="pt")
    with torch.inference_mode():
        logits = model(**inputs).logits
    ids = torch.argmax(logits, dim=-1)[0]
    return processor.decode(ids).strip()


def draft_clip(path: Path, torch, processor, model) -> None:
    out_path = path.with_name(path.stem + ".draft.csv")
    device = device_for(path)
    audio = read_pcm16_wav(path)
    windows = cut_points(audio)
    print(f"[mms] {path.name}: {len(audio) / RATE:.1f} s, {len(windows)} windows, device {device}")
    rows = []
    for s, e in windows:
        t0 = time.time()
        text = transcribe(torch, processor, model, audio[s:e])
        print(f"[mms]   {s / RATE:6.2f}-{e / RATE:6.2f} s ({time.time() - t0:.1f} s): {text}")
        rows.append({"start": f"{s / RATE:.2f}", "end": f"{e / RATE:.2f}", "device": device,
                     "speaker": "Me" if device == "mic" else "", "armenian": text, "english": ""})
    tmp = out_path.with_name(out_path.name + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    tmp.rename(out_path)
    print(f"[mms] wrote {out_path.relative_to(ROOT)}")


def main() -> None:
    if len(sys.argv) < 2:
        fail("usage: python scripts/draft_mms.py eval/clips/<name>.wav [...]")
    paths = [Path(a).resolve() for a in sys.argv[1:]]
    for p in paths:  # check everything before loading the 4 GB model
        device_for(p)
        read_pcm16_wav(p)
        out = p.with_name(p.stem + ".draft.csv")
        if out.exists():
            fail(f"{out} already exists; delete or rename it first (never overwritten)")
    torch, processor, model = load_model()
    for p in paths:
        draft_clip(p, torch, processor, model)
    peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # Linux: KiB
    print(f"[mms] done: {len(paths)} clip(s), peak RSS {peak_mb:.0f} MB")


if __name__ == "__main__":
    main()
