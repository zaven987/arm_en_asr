"""Fetch FLEURS hy_am test (D19) at a pinned revision, pick the M1 smoke clip and build the eval subset.

Run from the repo root with .venv active and internet on:
    python scripts/fetch_fleurs.py

Downloads into eval/fleurs/ (gitignored). FLEURS stores 32-bit float WAV: each extracted clip is kept
untouched and gets a 16 kHz mono 16-bit PCM copy next to it (D18).

Smoke clip rule (agreed 2026-10-29): first hy_am test row whose sentence id is also in en_us test.
  -> writes eval/fleurs/smoke_clip.json for scripts/smoke_m1.py.
Subset rule (agreed 2026-10-30): first 100 hy_am test sentence ids in TSV order that are also in
en_us test, one recording per id (the first hy_am row for that id).
  -> writes eval/meta/fleurs_hy_am_test100.csv (committed): D18 columns + fleurs_id, wav.
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
SUBSET_N = 100
SUBSET_CSV = ROOT / "eval" / "meta" / "fleurs_hy_am_test100.csv"
SUBSET_COLUMNS = ["start", "end", "device", "speaker", "armenian", "english", "fleurs_id", "wav"]

# FLEURS TSV columns (no header row)
COL_ID, COL_FILE, COL_RAW_TEXT, COL_NUM_SAMPLES = 0, 1, 2, 5
EXPECTED_COLS = 7


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def read_tsv(path: Path) -> list[list[str]]:
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
    if not rows:
        fail(f"{path} is empty")
    bad = [i + 1 for i, r in enumerate(rows) if len(r) != EXPECTED_COLS]
    if bad:
        fail(f"{path}: rows {bad[:5]} do not have {EXPECTED_COLS} columns")
    return rows


def text_by_id(rows: list[list[str]], label: str) -> dict[str, str]:
    """Sentence id -> raw text. Fails if one id has two different texts (one id has several recordings)."""
    texts: dict[str, str] = {}
    for r in rows:
        sid, text = r[COL_ID], r[COL_RAW_TEXT]
        if sid in texts and texts[sid] != text:
            fail(f"{label}: sentence id {sid} has two different texts")
        texts.setdefault(sid, text)
    return texts


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


def extract_clips(tar_path: Path, file_names: list[str]) -> None:
    """Extract the named WAVs into CLIP_DIR in one pass over the archive. Already present files are skipped."""
    CLIP_DIR.mkdir(parents=True, exist_ok=True)
    wanted = {n for n in file_names if not (CLIP_DIR / n).exists()}
    print(f"[fleurs] {len(file_names) - len(wanted)} of {len(file_names)} clips already extracted")
    if not wanted:
        return
    print(f"[fleurs] extracting {len(wanted)} clips from {tar_path.name} (one pass) ...")
    found: set[str] = set()
    with tarfile.open(tar_path, "r:gz") as tar:
        for member in tar:
            name = Path(member.name).name
            if not member.isfile() or name not in wanted:
                continue
            if name in found:
                fail(f"{name} appears twice in {tar_path.name}")
            wav_path = CLIP_DIR / name
            tmp = wav_path.with_name(name + ".part")
            tmp.write_bytes(tar.extractfile(member).read())  # written under our own name, never the archive path
            tmp.rename(wav_path)
            found.add(name)
            if found == wanted:
                break
    missing = sorted(wanted - found)
    if missing:
        fail(f"{len(missing)} clips not found in {tar_path.name}, e.g. {missing[:3]}")


def make_pcm16_copy(wav_path: Path, expected_frames: int) -> tuple[Path, float]:
    """Check one extracted clip and write its PCM copy (D18). Returns PCM path and length in seconds."""
    rate, channels, audio = read_float_wav(wav_path)
    if rate != 16000 or channels != 1:
        fail(f"{wav_path} is {rate} Hz / {channels} ch; expected 16000 Hz mono")
    frames = len(audio)
    if frames != expected_frames:
        fail(f"{wav_path} has {frames} samples; FLEURS TSV says {expected_frames}")
    peak = float(np.max(np.abs(audio))) if frames else 0.0
    if peak > 1.0:
        print(f"[fleurs] note: {wav_path.name} float peak {peak:.3f} > 1.0, clipped in the PCM copy")
    pcm_path = wav_path.with_name(wav_path.stem + ".pcm16.wav")
    if not pcm_path.exists():
        write_pcm16_wav(pcm_path, audio, rate)
    return pcm_path, frames / rate


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
    tar_path = paths["data/hy_am/audio/test.tar.gz"]

    hy_rows = read_tsv(paths["data/hy_am/test.tsv"])
    en_rows = read_tsv(paths["data/en_us/test.tsv"])
    hy_by_id = text_by_id(hy_rows, "hy_am")
    en_by_id = text_by_id(en_rows, "en_us")
    print(f"[fleurs] hy_am test: {len(hy_rows)} recordings of {len(hy_by_id)} sentences; "
          f"en_us test: {len(en_rows)} recordings of {len(en_by_id)} sentences")

    # One recording per sentence id: the first hy_am row for that id, in TSV order.
    first_rec: dict[str, list[str]] = {}
    for r in hy_rows:
        if r[COL_ID] in en_by_id:
            first_rec.setdefault(r[COL_ID], r)
    if not first_rec:
        fail("no hy_am test row has a matching en_us sentence id")
    if len(first_rec) < SUBSET_N:
        fail(f"only {len(first_rec)} matched sentences; subset needs {SUBSET_N}")
    subset = list(first_rec.values())[:SUBSET_N]
    smoke = subset[0]  # smoke rule == first matched row

    extract_clips(tar_path, [r[COL_FILE] for r in subset])

    # --- smoke clip (M1), unchanged output ---
    smoke_wav = CLIP_DIR / smoke[COL_FILE]
    smoke_pcm, smoke_sec = make_pcm16_copy(smoke_wav, int(smoke[COL_NUM_SAMPLES]))
    SMOKE_JSON.write_text(json.dumps({
        "fleurs_revision": REVISION,
        "id": smoke[COL_ID],
        "wav": str(smoke_pcm.relative_to(ROOT)),
        "original_wav": str(smoke_wav.relative_to(ROOT)),
        "seconds": round(smoke_sec, 2),
        "armenian": smoke[COL_RAW_TEXT],
        "english": en_by_id[smoke[COL_ID]],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[fleurs] smoke clip: id {smoke[COL_ID]}, {smoke[COL_FILE]}, {smoke_sec:.2f} s "
          f"-> {SMOKE_JSON.relative_to(ROOT)}")

    # --- eval subset (M2) ---
    out_rows = []
    total = 0.0
    for r in subset:
        pcm_path, sec = make_pcm16_copy(CLIP_DIR / r[COL_FILE], int(r[COL_NUM_SAMPLES]))
        total += sec
        out_rows.append({
            "start": "0.00",
            "end": f"{sec:.2f}",
            "device": "mic",
            "speaker": "Me",
            "armenian": r[COL_RAW_TEXT],
            "english": en_by_id[r[COL_ID]],
            "fleurs_id": r[COL_ID],
            "wav": str(pcm_path.relative_to(ROOT)),
        })
    SUBSET_CSV.parent.mkdir(parents=True, exist_ok=True)
    tmp = SUBSET_CSV.with_name(SUBSET_CSV.name + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SUBSET_COLUMNS)
        w.writeheader()
        w.writerows(out_rows)
    tmp.rename(SUBSET_CSV)
    lengths = sorted(float(o["end"]) for o in out_rows)
    print(f"[fleurs] subset: {len(out_rows)} clips, {total / 60:.1f} min, "
          f"{lengths[0]:.1f}-{lengths[-1]:.1f} s, {sum(x > 12 for x in lengths)} longer than 12 s")
    print(f"[fleurs] wrote {SUBSET_CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
