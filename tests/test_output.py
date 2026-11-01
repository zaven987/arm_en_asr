"""T1.4 - output line format (TEST.md; D12, DECISIONS section 8, O1-O7).

Pass: a fixed record gives exactly the section 8 format; offset 83 s -> [00:01:23];
latency 5.1 s -> warning shown, 4.9 s -> no warning.
"""
from __future__ import annotations

from arm_en_asr.output import Record, format_line


def make_record(start: float = 83.0, latency: float = 2.8) -> Record:
    return Record(
        segment_id=1,
        speaker="Speaker 1",
        start=start,
        armenian="Բարև, ինչպե՞ս ես",
        english="Hi, how are you?",
        latency=latency,
    )


def test_fixed_record_gives_section_8_format():
    expected = (
        "[00:01:23] Speaker 1:  Բարև, ինչպե՞ս ես\n"
        "           → Hi, how are you?   (2.8s)"
    )
    assert format_line(make_record()) == expected


def test_offset_83s():
    """83 s -> [00:01:23]; also truncated, not rounded (O2): 83.9 s -> [00:01:23]."""
    assert format_line(make_record(start=83.0)).startswith("[00:01:23] ")
    assert format_line(make_record(start=83.9)).startswith("[00:01:23] ")


def test_latency_over_5s_shows_warning():
    assert format_line(make_record(latency=5.1)).endswith("(5.1s ⚠ >5s)")


def test_latency_under_5s_shows_no_warning():
    line = format_line(make_record(latency=4.9))
    assert line.endswith("(4.9s)")
    assert "⚠" not in line
