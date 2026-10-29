"""One-time model download and conversion (D15, D23, D24).

Run once from the repo root, with .venv active and internet on:
    python download_models.py

Everything goes into models/ (gitignored). The app never downloads at runtime.
Already-present models are skipped. Any failure stops with "ERROR:" and exit code 1.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parent
MODELS = ROOT / "models"

# faster-whisper small, CTranslate2 format (D3)
WHISPER_REPO = "Systran/faster-whisper-small"
WHISPER_REV = "536b0662742c02347bc0e980a01041f333bce120"
WHISPER_DIR = MODELS / "faster-whisper-small"

# opus-mt-hy-en original checkpoint, input for the conversion (D5, D23)
OPUS_REPO = "Helsinki-NLP/opus-mt-hy-en"
OPUS_REV = "79b0a5051bdb77155f96bb5f091c054ff575b04b"
OPUS_SRC_DIR = MODELS / "src" / "opus-mt-hy-en"
OPUS_FILES = [
    "config.json",
    "pytorch_model.bin",
    "source.spm",
    "target.spm",
    "vocab.json",
    "tokenizer_config.json",
]

# opus-mt-hy-en converted to CTranslate2 int8, using the converter in .venv-convert (D23)
OPUS_CT2_DIR = MODELS / "opus-mt-hy-en-ct2-int8"
CONVERTER = ROOT / ".venv-convert" / "bin" / "ct2-transformers-converter"

# Silero VAD ONNX from the official repo at a pinned tag (D24)
SILERO_TAG = "v6.2.1"
SILERO_URL = (
    "https://raw.githubusercontent.com/snakers4/silero-vad/"
    f"{SILERO_TAG}/src/silero_vad/data/silero_vad.onnx"
)
SILERO_PATH = MODELS / "silero_vad.onnx"


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def dir_size_mb(path: Path) -> float:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1e6


def download_whisper() -> None:
    if (WHISPER_DIR / "model.bin").exists():
        print(f"[whisper] already present, skipping: {WHISPER_DIR}")
        return
    print(f"[whisper] downloading {WHISPER_REPO}@{WHISPER_REV[:8]} ...")
    snapshot_download(WHISPER_REPO, revision=WHISPER_REV, local_dir=WHISPER_DIR)
    if not (WHISPER_DIR / "model.bin").exists():
        fail(f"[whisper] model.bin missing after download in {WHISPER_DIR}")
    print(f"[whisper] done ({dir_size_mb(WHISPER_DIR):.0f} MB)")


def download_opus_source() -> None:
    if all((OPUS_SRC_DIR / f).exists() for f in OPUS_FILES):
        print(f"[opus-src] already present, skipping: {OPUS_SRC_DIR}")
        return
    print(f"[opus-src] downloading {OPUS_REPO}@{OPUS_REV[:8]} ...")
    snapshot_download(
        OPUS_REPO, revision=OPUS_REV, local_dir=OPUS_SRC_DIR, allow_patterns=OPUS_FILES
    )
    missing = [f for f in OPUS_FILES if not (OPUS_SRC_DIR / f).exists()]
    if missing:
        fail(f"[opus-src] files missing after download: {', '.join(missing)}")
    print(f"[opus-src] done ({dir_size_mb(OPUS_SRC_DIR):.0f} MB)")


def convert_opus() -> None:
    if (OPUS_CT2_DIR / "model.bin").exists():
        print(f"[opus-ct2] already present, skipping: {OPUS_CT2_DIR}")
        return
    if OPUS_CT2_DIR.exists():
        fail(f"[opus-ct2] {OPUS_CT2_DIR} exists but has no model.bin; delete it and rerun")
    if not CONVERTER.exists():
        fail(f"[opus-ct2] converter not found: {CONVERTER} (create .venv-convert first, D23)")
    tmp_dir = OPUS_CT2_DIR.with_name(OPUS_CT2_DIR.name + ".part")
    cmd = [
        str(CONVERTER),
        "--model", str(OPUS_SRC_DIR),
        "--output_dir", str(tmp_dir),
        "--quantization", "int8",
        "--copy_files", "source.spm", "target.spm",
        "--force",  # only ever overwrites our own .part dir from an earlier failed run
    ]
    print("[opus-ct2] converting to CTranslate2 int8 ...")
    env = dict(os.environ, HF_HUB_OFFLINE="1")  # the converter must not download anything
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        fail(f"[opus-ct2] converter exited with code {result.returncode}")
    for f in ("model.bin", "source.spm", "target.spm"):
        if not (tmp_dir / f).exists():
            fail(f"[opus-ct2] {f} missing in converter output {tmp_dir}")
    tmp_dir.rename(OPUS_CT2_DIR)
    print(f"[opus-ct2] done ({dir_size_mb(OPUS_CT2_DIR):.0f} MB)")


def download_silero() -> None:
    if SILERO_PATH.exists():
        print(f"[silero] already present, skipping: {SILERO_PATH}")
    else:
        print(f"[silero] downloading {SILERO_TAG} from {SILERO_URL} ...")
        tmp_path = SILERO_PATH.with_name(SILERO_PATH.name + ".part")
        try:
            with urllib.request.urlopen(SILERO_URL, timeout=60) as resp, open(tmp_path, "wb") as out:
                shutil.copyfileobj(resp, out)
        except Exception as e:  # noqa: BLE001 - any network error must stop the script
            fail(f"[silero] download failed: {e}")
        tmp_path.rename(SILERO_PATH)
    data = SILERO_PATH.read_bytes()
    print(f"[silero] {len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()}")


def main() -> None:
    MODELS.mkdir(exist_ok=True)
    download_whisper()
    download_opus_source()
    convert_opus()
    download_silero()
    print("All models ready in", MODELS)


if __name__ == "__main__":
    main()
