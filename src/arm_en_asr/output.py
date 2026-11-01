"""Output: one joined record -> two terminal lines (DECISIONS D12, section 8; M3 S6 decisions O1-O6, 2026-11-01).

Format (section 8):
    [00:01:23] Speaker 1:  Բարև, ինչպե՞ս ես
               → Hi, how are you?   (2.8s)

`format_line` is pure and tested by T1.4; `print_line` writes it to stdout at once.
Plain text only, no colours (O6); "→" and "⚠" need a UTF-8 terminal (R15).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

LATENCY_LIMIT = 5.0          # D12 / section 4: warn when the raw latency is strictly above this (O4)
INDENT = " " * len("[00:00:00] ")  # O3: 11 spaces, the width of the time stamp


@dataclass(frozen=True)
class Record:
    """O1: one segment's joined result."""
    segment_id: int
    speaker: str      # "Me" or "Speaker N"
    start: float      # seconds from session start (Segment.start, D12)
    armenian: str
    english: str
    latency: float    # seconds, measured just before print_line (D12, S7)


def format_offset(seconds: float) -> str:
    """O2: [HH:MM:SS], truncated (floor), not rounded: 83.9 s -> [00:01:23]."""
    total = math.floor(seconds)
    h, rest = divmod(total, 3600)
    m, s = divmod(rest, 60)
    return f"[{h:02d}:{m:02d}:{s:02d}]"


def format_latency(latency: float) -> str:
    """O4: 1 decimal; warning decided on the raw value, so 5.04 s shows (5.0s ⚠ >5s)."""
    if latency > LATENCY_LIMIT:
        return f"({latency:.1f}s ⚠ >5s)"
    return f"({latency:.1f}s)"


def format_line(record: Record) -> str:
    """O3: two lines, no trailing newline. O5: empty texts are formatted as given."""
    line1 = f"{format_offset(record.start)} {record.speaker}:  {record.armenian}"
    line2 = f"{INDENT}→ {record.english}   {format_latency(record.latency)}"
    return f"{line1}\n{line2}"


def print_line(record: Record) -> None:
    """O1: print at once (flush), so latency measured just before is what the user sees."""
    print(format_line(record), flush=True)
