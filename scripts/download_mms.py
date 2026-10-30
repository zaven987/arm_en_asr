"""One-time download of Meta MMS-1B-all for reference drafting only (D15, D18). Not an app model.

Run once from the repo root, with .venv-convert active and internet on:
    python scripts/download_mms.py

Downloads only the base model files and the Armenian adapter (adapter.hye.*) at a pinned revision
into models/mms-1b-all/ (gitignored), about 3.9 GB. Already-present files are skipped.
Any failure stops with "ERROR:" and exit code 1.
"""
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parent.parent  # repo root (script lives in scripts/)
MMS_REPO = "facebook/mms-1b-all"
MMS_REV = "3d33597edbdaaba14a8e858e2c8caa76e3cec0cd"  # command_outputs/m2_mms_info.txt
MMS_DIR = ROOT / "models" / "mms-1b-all"

# file -> size in bytes at MMS_REV (from command_outputs/m2_mms_info.txt)
MMS_FILES = {
    "config.json": 2040,
    "preprocessor_config.json": 254,
    "special_tokens_map.json": 96,
    "tokenizer_config.json": 397,
    "vocab.json": 1340148,
    "model.safetensors": 3859521128,
    "adapter.hye.safetensors": 9167492,
}


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def wrong_files() -> list[str]:
    """Files that are missing or have an unexpected size."""
    bad = []
    for name, size in MMS_FILES.items():
        path = MMS_DIR / name
        if not path.is_file():
            bad.append(f"{name} (missing)")
        elif path.stat().st_size != size:
            bad.append(f"{name} ({path.stat().st_size} bytes, expected {size})")
    return bad


def main() -> None:
    if not wrong_files():
        print(f"[mms] already present, skipping: {MMS_DIR}")
        return
    print(f"[mms] downloading {MMS_REPO}@{MMS_REV[:8]} (base + hye adapter, ~3.9 GB) ...")
    MMS_DIR.parent.mkdir(exist_ok=True)
    snapshot_download(MMS_REPO, revision=MMS_REV, local_dir=MMS_DIR, allow_patterns=list(MMS_FILES))
    bad = wrong_files()
    if bad:
        fail(f"[mms] after download: {', '.join(bad)}")
    total = sum(MMS_FILES.values()) / 1e9
    print(f"[mms] done: {len(MMS_FILES)} files, {total:.2f} GB in {MMS_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
