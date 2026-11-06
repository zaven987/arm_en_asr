"""pytest setup for the D33 order rule (DECISIONS D33, D34 N4).

pytest imports every test file while collecting, and test_audio_capture.py imports audio_capture,
which imports onnxruntime (Silero). The first sherpa-onnx CUDA recognizer of a process must be
created before that, or it crashes (D33). So at session start, before collection, one Asr
(FastConformer CTC on the GPU) is created and freed at once: after that, the rule is met for the
whole process (D33 addition, command_outputs/m7_f6_prime.txt), and no test holds an extra model.

If this fails (e.g. model missing, no GPU), nothing is hidden: the reason is printed in the
report header, and every test that builds an Asr fails loudly with its own AsrError (D22).
"""
from __future__ import annotations

import gc
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FASTCONFORMER = ROOT / "models" / "fastconformer-hy-ctc"

_prime_result = "not run"


def pytest_sessionstart(session) -> None:
    global _prime_result
    from arm_en_asr.asr import Asr, AsrError
    try:
        asr = Asr(FASTCONFORMER)
    except AsrError as e:
        _prime_result = f"FAILED: {e}"
        return
    _prime_result = f"OK (first CUDA recognizer created, +{asr.vram_added_mb:.0f} MB GPU memory, freed)"
    del asr
    gc.collect()


def pytest_report_header(config) -> str:
    return f"D33 priming (conftest.py): {_prime_result}"
