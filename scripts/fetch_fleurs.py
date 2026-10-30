"""Fetch FLEURS hy_am test (D19) at a pinned revision and pick the M1 smoke clip.

Run from the repo root with .venv active and internet on:
    python scripts/fetch_fleurs.py

Downloads into eval/fleurs/ (gitignored). Extracts only the smoke clip WAV (FLEURS stores
32-bit float WAV), keeps it untouched, writes a 16 kHz mono 16-bit PCM copy next to it (D18),
and writes eval/fleurs/smoke_clip.json for scripts/smoke_m1.py.
Smoke clip rule (agreed 2026-10-29): first hy_am test row whose sentence id is also in en_us test.
"""
import csv
import json
import struct
import sys
import tarfile
import wave
from pathlib import Path

import numpy as np
from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parent.parent
FLEURS_DIR = ROOT / "eval" / "fleurs"
REPO = "google/fleurs"
REVISION = "70bb2e84b976b7e960aa89f1c648e09c59f894dd"
FILES = ["data/hy_am/test.tsv", "data/en_us/test.tsv", "data/hy_am/audio/test.tar.gz"]
CLIP_DIR = FLEURS_DIR / "hy_am" / "test"
SMOKE_JSON = FLEURS_DIR / "smoke_clip.json"

# FLEURS TSV columns (no header row)
COL_ID, COL_FILE, COL_RAW_TEXT = 0, 1, 2


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def read_tsv(path: Path) -> list[list[str]]:
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
    if not rows:
        fail(f"{path} is empty")
    return rows


WAVE_FORMAT_IEEE_FLOAT = 3
WAVE_FORMAT_EXTENSIBLE = 0xFFFE


def read_float_wav(path: Path) -> tuple[int, int, np.ndarray]:
    """Read a 32-bit float WAV (stdlib `wave` only reads integer PCM). Returns rate, channels, samples."""
    data = path.read_bytes()
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        fail(f"{path} is not a RIFF/WAVE file")
    fmt = None
    samples = None
    pos = 12
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack("<I", data[pos + 4:pos + 8])[0]
        body = data[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            tag, channels, rate, _, _, bits = struct.unpack("<HHIIHH", body[:16])
            if tag == WAVE_FORMAT_EXTENSIBLE and len(body) >= 26:
                tag = struct.unpack("<H", body[24:26])[0]  # first 2 bytes of SubFormat GUID
            fmt = (tag, channels, rate, bits)
        elif cid == b"data":
            samples = body
        pos += 8 + size + (size & 1)  # chunks are padded to an even size
    if fmt is None or samples is None:
        fail(f"{path} has no fmt or data chunk")
    tag, channels, rate, bits = fmt
    if tag != WAVE_FORMAT_IEEE_FLOAT or bits != 32:
        fail(f"{path} is format {tag} / {bits} bit; expected 32-bit float (format 3)")
    return rate, channels, np.frombuffer(samples[: len(samples) // 4 * 4], dtype="<f4")


def write_pcm16_wav(path: Path, audio: np.ndarray, rate: int) -> None:
    pcm = np.round(np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")
    tmp = path.with_name(path.name + ".part")
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    tmp.rename(path)


def main() -> None:
    paths = {}
    for name in FILES:
        print(f"[fleurs] {name} @ {REVISION[:8]} ...")
        local = Path(hf_hub_download(REPO, name, repo_type="dataset", revision=REVISION,
                                     local_dir=FLEURS_DIR))
        if not local.exists():
            fail(f"{name} missing after download")
        print(f"[fleurs]   -> {local} ({local.stat().st_size / 1e6:.1f} MB)")
        paths[name] = local

    hy_rows = read_tsv(paths["data/hy_am/test.tsv"])
    en_by_id = {r[COL_ID]: r[COL_RAW_TEXT] for r in read_tsv(paths["data/en_us/test.tsv"])}
    print(f"[fleurs] hy_am test rows: {len(hy_rows)}, en_us test rows: {len(en_by_id)}")

    pick = next((r for r in hy_rows if r[COL_ID] in en_by_id), None)
    if pick is None:
        fail("no hy_am test row has a matching en_us sentence id")
    sent_id, file_name, hy_text = pick[COL_ID], pick[COL_FILE], pick[COL_RAW_TEXT]
    en_text = en_by_id[sent_id]

    CLIP_DIR.mkdir(parents=True, exist_ok=True)
    wav_path = CLIP_DIR / file_name
    if wav_path.exists():
        print(f"[fleurs] clip already extracted, skipping: {wav_path}")
    else:
        print(f"[fleurs] extracting {file_name} from test.tar.gz ...")
        with tarfile.open(paths["data/hy_am/audio/test.tar.gz"], "r:gz") as tar:
            member = next((m for m in tar if m.isfile() and Path(m.name).name == file_name), None)
            if member is None:
                fail(f"{file_name} not found in test.tar.gz")
            src = tar.extractfile(member)
            tmp = wav_path.with_name(wav_path.name + ".part")
            tmp.write_bytes(src.read())  # written under our own name, never the archive path
            tmp.rename(wav_path)

    rate, channels, audio = read_float_wav(wav_path)
    if rate != 16000 or channels != 1:
        fail(f"{wav_path} is {rate} Hz / {channels} ch; expected 16000 Hz mono")
    frames = len(audio)
    peak = float(np.max(np.abs(audio))) if frames else 0.0
    if peak > 1.0:
        print(f"[fleurs] note: float peak {peak:.3f} > 1.0, clipped in the PCM copy")

    pcm_path = wav_path.with_name(wav_path.stem + ".pcm16.wav")
    if pcm_path.exists():
        print(f"[fleurs] PCM copy already present, skipping: {pcm_path.relative_to(ROOT)}")
    else:
        write_pcm16_wav(pcm_path, audio, rate)
        print(f"[fleurs] wrote 16 kHz mono 16-bit PCM copy: {pcm_path.relative_to(ROOT)}")

    SMOKE_JSON.write_text(json.dumps({
        "fleurs_revision": REVISION,
        "id": sent_id,
        "wav": str(pcm_path.relative_to(ROOT)),
        "original_wav": str(wav_path.relative_to(ROOT)),
        "seconds": round(frames / rate, 2),
        "armenian": hy_text,
        "english": en_text,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[fleurs] smoke clip: id {sent_id}, {file_name}, {frames / rate:.2f} s")
    print(f"[fleurs] Armenian: {hy_text}")
    print(f"[fleurs] English:  {en_text}")
    print(f"[fleurs] wrote {SMOKE_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
