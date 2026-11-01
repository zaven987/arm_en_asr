"""T1.3 - translate on FLEURS reference Armenian (TEST.md; D5, B1-B6).

Input: the `armenian` text of the first 3 rows of eval/meta/fleurs_hy_am_test100.csv (B6).
Pass: non-empty English for each sentence, with no Armenian characters, and at most
2x the Armenian length in characters (C2: catches repetition loops, L10).
A missing model or CSV makes the test fail, never skip (D22).
"""
from __future__ import annotations

import csv
from pathlib import Path

from arm_en_asr.translate import Mt

ROOT = Path(__file__).resolve().parent.parent
OPUS = ROOT / "models" / "opus-mt-hy-en-ct2-int8"
FLEURS_CSV = ROOT / "eval" / "meta" / "fleurs_hy_am_test100.csv"
MAX_LENGTH_RATIO = 2  # C2: in diag_mt.py normal output was 0.72-1.64x the Armenian length,
                      # the CT2 loop (stopped at 256 tokens) 2.32-2.47x


def has_armenian(text: str) -> bool:
    """Armenian block + Armenian ligatures (same ranges as tests/test_asr.py)."""
    return any("԰" <= c <= "֏" or "ﬓ" <= c <= "ﬗ" for c in text)


def first_sentences(n: int) -> list[str]:
    with FLEURS_CSV.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))[:n]
    assert len(rows) == n, f"{FLEURS_CSV} has fewer than {n} rows"
    return [r["armenian"] for r in rows]


def test_fleurs_sentences_give_english():
    mt = Mt(OPUS)
    for armenian in first_sentences(3):
        english = mt.translate(armenian)
        print(f"HY: {armenian}\nEN: {english}")  # visible with -s
        assert english, f"empty translation for: {armenian!r}"
        assert not has_armenian(english), f"Armenian characters in output: {english!r}"
        assert len(english) <= MAX_LENGTH_RATIO * len(armenian), (
            f"English {len(english)} chars > {MAX_LENGTH_RATIO}x Armenian {len(armenian)} chars "
            f"(repetition loop?): {english!r}"
        )
