"""T1.6 - diarizer (TEST.md; D9, D17, D22, D27, R11, R13; M6 S4 J1-J8, S5 K1-K8, 2026-11-05).

Default suite (no eval clips):
  - SpeakerClusters rules on made-up 3-d vectors (K2, K3 a/b, J8), with a fixed test threshold
    of 0.7 so the rules are tested apart from the tuned value.
  - The tuned constants (THRESHOLD 0.76, SHORT_S 2.0).
  - Embedder / Diarizer on speech_short.wav with the real model: a 256-d unit vector, a label.
  - A missing model gives a clear "model missing" error, no download (D15).
eval marker (T1.6 proper; gitignored clips in eval/clips/, D22):
  - each of mic_01-03 alone -> one speaker on 100 % of its segments;
  - sys_01 -> % correct, speakers found, short segments: printed (run with -s), no threshold;
    scoring as agreed in TEST.md T1.6. THRESHOLD was tuned with sys_01 (Zaven, 2026-11-05,
    changes R13), so this report is no longer an independent check.
A missing fixture, model or clip fails, never skips (D22).
"""
from __future__ import annotations

import csv
import itertools
import wave
from pathlib import Path

import numpy as np
import pytest

from arm_en_asr.audio_capture import (
    Segment, Segmenter, SileroVad, WavSource, new_id_counter, run_capture)
from arm_en_asr.diarizer import (
    MODEL_FILE, SHORT_S, THRESHOLD, Diarizer, DiarizerError, Embedder, SpeakerClusters)

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
MODELS = ROOT / "models"
MODEL = MODELS / MODEL_FILE
VAD = MODELS / "silero_vad.onnx"
CLIPS = ROOT / "eval" / "clips"
META = ROOT / "eval" / "meta"

T = 0.7                     # rule tests only
LONG, SHORT = 3.0, 1.0      # speech seconds


def vec(*xs) -> np.ndarray:
    return np.asarray(xs, dtype=np.float32)


def at_cos(c: float) -> np.ndarray:
    """Unit vector with cosine c to (1, 0, 0), in the x-z plane."""
    return vec(c, 0.0, float(np.sqrt(1.0 - c * c)))


A, B, C = vec(1, 0, 0), vec(0, 1, 0), vec(0, 0, 1)


def load_fixture(name: str) -> np.ndarray:
    with wave.open(str(FIXTURES / name), "rb") as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)
        pcm = w.readframes(w.getnframes())
    return np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0


# ---------------------------------------------------------------- rules (made-up vectors)

def test_long_segment_joins_above_threshold_and_starts_new_speaker_below():
    c = SpeakerClusters(T)
    assert c.assign(A, LONG) == "Speaker 1"
    assert c.assign(at_cos(0.75), LONG) == "Speaker 1"   # >= 0.7: joins
    c = SpeakerClusters(T)
    c.assign(A, LONG)
    assert c.assign(at_cos(0.65), LONG) == "Speaker 2"   # < 0.7: new speaker


def test_speakers_are_numbered_in_order_of_appearance():
    c = SpeakerClusters(T)
    assert [c.assign(v, LONG) for v in (A, B, C, A, C)] == [
        "Speaker 1", "Speaker 2", "Speaker 3", "Speaker 1", "Speaker 3"]
    assert c.labels == ["Speaker 1", "Speaker 2", "Speaker 3"]


def test_short_segment_never_creates_a_speaker():
    """J8: a short segment far from every speaker still joins the nearest one."""
    c = SpeakerClusters(T)
    c.assign(A, LONG)
    assert c.assign(B, SHORT) == "Speaker 1"
    assert c.labels == ["Speaker 1"]


def test_short_segment_joins_the_nearest_speaker():
    c = SpeakerClusters(T)
    c.assign(A, LONG)
    c.assign(B, LONG)
    assert c.assign(vec(0.3, 0.6, 0.0), SHORT) == "Speaker 2"


def test_short_segment_never_updates_a_centroid():
    """After 5 short B segments, Speaker 1's centroid is still A: a long segment at cos 0.72 to A
    still joins (it would not if the centroid had moved toward B)."""
    c = SpeakerClusters(T)
    c.assign(A, LONG)
    for _ in range(5):
        assert c.assign(B, SHORT) == "Speaker 1"
    assert c.assign(at_cos(0.72), LONG) == "Speaker 1"


def test_boundary_speech_length_counts_as_long():
    """J8: speech >= 2.0 s is long (can create a speaker)."""
    c = SpeakerClusters(T)
    c.assign(A, LONG)
    assert c.assign(B, SHORT_S) == "Speaker 2"


def test_k3a_first_long_segment_joins_a_short_started_speaker_1_without_check():
    """K3 (a) option B: shorts A, C, then a long B (orthogonal to both) still joins Speaker 1."""
    c = SpeakerClusters(T)
    assert c.assign(A, SHORT) == "Speaker 1"
    assert c.assign(C, SHORT) == "Speaker 1"
    assert c.assign(B, LONG) == "Speaker 1"
    assert c.labels == ["Speaker 1"]


def test_k3a_centroid_comes_from_the_long_segment_only():
    """Short B, then long A starts Speaker 1's centroid = A (the short is not in it): a long at cos 0.75
    to A joins at 0.7 (against the mean of A and B it would score 0.53 and start Speaker 2)."""
    c = SpeakerClusters(T)
    c.assign(B, SHORT)
    assert c.assign(A, LONG) == "Speaker 1"
    assert c.assign(at_cos(0.75), LONG) == "Speaker 1"
    assert c.assign(B, LONG) == "Speaker 2"


def test_k3b_not_ready_gets_the_last_speaker_or_speaker_1():
    c = SpeakerClusters(T)
    assert c.assign(None, SHORT) == "Speaker 1"       # nobody yet
    c.assign(A, LONG)
    c.assign(B, LONG)                                 # last = Speaker 2
    assert c.assign(None, LONG) == "Speaker 2"
    assert c.not_ready == 2
    assert c.labels == ["Speaker 1", "Speaker 2"]


def test_speaker_with_no_reference_takes_the_next_embedding():
    """K3 (a) B: only not-ready segments so far -> the next long segment joins Speaker 1."""
    c = SpeakerClusters(T)
    c.assign(None, SHORT)
    assert c.assign(B, LONG) == "Speaker 1"
    assert c.assign(A, LONG) == "Speaker 2"


@pytest.mark.parametrize("bad", [vec(0, 0, 0), vec(np.nan, 1, 0), vec()])
def test_bad_embedding_fails_loudly(bad):
    with pytest.raises(DiarizerError, match="bad embedding"):
        SpeakerClusters(T).assign(bad, LONG)


@pytest.mark.parametrize("threshold", [1.5, -1.5])
def test_bad_threshold_fails_loudly(threshold):
    with pytest.raises(DiarizerError, match="threshold"):
        SpeakerClusters(threshold)


def test_tuned_constants():
    """Threshold (Zaven, 2026-11-05, tune_diarizer.py --sys01) and J8 short-segment length (D27)."""
    assert THRESHOLD == 0.76
    assert SHORT_S == 2.0


# ---------------------------------------------------------------- model (default suite)

def test_missing_model_fails_loudly(tmp_path):
    """D15: clear 'model missing' error, no download attempt."""
    with pytest.raises(DiarizerError, match="model missing"):
        Embedder(tmp_path / "none.onnx")
    with pytest.raises(DiarizerError, match="model missing"):
        Diarizer(tmp_path / "none.onnx")


def test_embedder_gives_a_256_d_unit_vector():
    embedder = Embedder(MODEL)
    e = embedder.embed(load_fixture("speech_short.wav"))
    assert embedder.dim == 256
    assert e is not None and e.shape == (256,)
    assert abs(float(np.linalg.norm(e)) - 1.0) < 1e-4
    assert embedder.embed(np.zeros(0, dtype=np.float32)) is None


def test_diarizer_labels_a_segment():
    audio = load_fixture("speech_short.wav")
    seg = Segment(id=1, device="system", start=0.0, end=len(audio) / 16000, audio=audio, end_wall=0.0)
    d = Diarizer(MODEL)
    assert d.clusters.threshold == THRESHOLD
    assert d.label(seg) == "Speaker 1"


# ---------------------------------------------------------------- T1.6 on eval clips

def segments(stem: str) -> list[Segment]:
    path = CLIPS / f"{stem}.wav"
    assert path.is_file(), f"eval clip not found: {path} (D22)"
    out: list[Segment] = []
    segmenter = Segmenter("system", SileroVad(VAD), new_id_counter())
    run_capture(WavSource(path, realtime=False), segmenter, out.append)
    assert out, f"no segments from {stem}"
    return out


@pytest.mark.eval
@pytest.mark.parametrize("stem", ["mic_01", "mic_02", "mic_03"])
def test_solo_clip_gets_one_speaker(stem):
    d = Diarizer(MODEL)
    segs = segments(stem)
    labels = [d.label(s) for s in segs]
    print(f"\n{stem}: " + ", ".join(f"{s.id}:{s.end - s.start:.2f}s={lab}"
                                    for s, lab in zip(segs, labels)))
    assert len(set(labels)) == 1, f"{stem}: {len(set(labels))} speakers: {sorted(set(labels))}"


@pytest.mark.eval
def test_sys_01_report():
    """2 speakers, % correct reported with no threshold (TEST.md T1.6 scoring)."""
    ref_path = META / "sys_01.csv"
    assert ref_path.is_file(), f"reference CSV not found: {ref_path} (D22)"
    with open(ref_path, newline="", encoding="utf-8") as f:
        ref = [(float(r["start"]), float(r["end"]), r["speaker"].strip()) for r in csv.DictReader(f)]

    def truth(seg: Segment) -> str | None:
        best, best_overlap = None, 0.0
        for rs, re_, speaker in ref:
            overlap = min(seg.end, re_) - max(seg.start, rs)
            if overlap > best_overlap:
                best, best_overlap = speaker, overlap
        return best

    d = Diarizer(MODEL)
    segs = segments("sys_01")
    rows = [(s, d.label(s), truth(s)) for s in segs]    # every segment is labelled, in order
    scored = [r for r in rows if r[2] is not None]
    no_overlap = len(rows) - len(scored)

    readers = sorted({t for _, _, t in scored})
    found = sorted({lab for _, lab, _ in rows})
    k = min(len(readers), len(found))
    best_map: dict[str, str] = {}
    best_ok = -1
    for rs in itertools.permutations(readers, k):
        for ls in itertools.permutations(found, k):
            m = dict(zip(ls, rs))
            ok = sum(m.get(lab) == t for _, lab, t in scored)
            if ok > best_ok:
                best_ok, best_map = ok, m

    print(f"\nsys_01: {len(rows)} segments, {no_overlap} with no reference overlap (left out)")
    for s, lab, t in rows:
        mark = "" if t is None else ("ok" if best_map.get(lab) == t else "WRONG")
        kind = "short" if s.end - s.start < SHORT_S else "long"
        print(f"  {s.id:>3} {s.start:7.2f} {s.end - s.start:5.2f}s {kind:5} {lab:10} ref {t}  {mark}")
    short = [r for r in scored if r[0].end - r[0].start < SHORT_S]
    short_ok = sum(best_map.get(lab) == t for _, lab, t in short)
    n = len(scored)
    print(f"sys_01 RESULT: {best_ok}/{n} correct ({100 * best_ok / n:.1f} %); speakers found "
          f"{len(found)} (reference {len(readers)}); short segments {short_ok}/{len(short)} correct; "
          f"not ready {d.clusters.not_ready}; mapping {best_map}")
    assert rows   # reported only: no pass threshold (TEST.md T1.6)
