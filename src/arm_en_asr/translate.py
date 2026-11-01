"""MT: Armenian text -> English text (DECISIONS D5, D23; M3 S5 decisions B1-B6, C1, 2026-11-01).

One Mt object holds one opus-mt-hy-en model (CTranslate2 int8). Each call translates one
segment's text in one go, with no sentence splitting (B3).
"""
from __future__ import annotations

from pathlib import Path

import ctranslate2
import sentencepiece as spm

INTRA_THREADS = 2   # B1: ASR keeps its 4 threads (D3); tuned in M4 (T4)
INTER_THREADS = 1   # B1
BEAM_SIZE = 2       # B3: CTranslate2 default, as in the M1 smoke run; set explicitly
NO_REPEAT_NGRAM = 3 # C1: stops the model's repetition loops (L10); measured by scripts/diag_mt.py
EOS = "</s>"
REQUIRED = ("model.bin", "source.spm", "target.spm")


class MtError(Exception):
    """MT problem the user must see (missing model)."""


class Mt:
    def __init__(self, model_dir: Path | str):
        self.model_dir = Path(model_dir)
        # B5: name the missing file ourselves (working rule 2, D15).
        for name in REQUIRED:
            if not (self.model_dir / name).is_file():
                raise MtError(
                    f"model missing: opus-mt-hy-en file {self.model_dir / name} "
                    "(run scripts/download_models.py)"
                )
        # B1: CPU, int8 (D5).
        self._translator = ctranslate2.Translator(
            str(self.model_dir),
            device="cpu",
            compute_type="int8",
            inter_threads=INTER_THREADS,
            intra_threads=INTRA_THREADS,
        )
        # B2: SentencePiece in and out, as in the M1 smoke run.
        self._sp_src = spm.SentencePieceProcessor(model_file=str(self.model_dir / "source.spm"))
        self._sp_tgt = spm.SentencePieceProcessor(model_file=str(self.model_dir / "target.spm"))

    def translate(self, armenian: str) -> str:
        """B4: Armenian text -> English text; "" for empty input (model not called)."""
        text = armenian.strip()
        if not text:
            return ""
        tokens = self._sp_src.encode(text, out_type=str) + [EOS]
        result = self._translator.translate_batch(
            [tokens], beam_size=BEAM_SIZE, no_repeat_ngram_size=NO_REPEAT_NGRAM
        )
        hyp = result[0].hypotheses[0]
        return self._sp_tgt.decode([t for t in hyp if t != EOS]).strip()
