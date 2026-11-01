"""M3 S5 diagnosis: why does opus-mt-hy-en loop on FLEURS sentence 2? (D5; time-box 30 min)

Translates the T1.3 sentences (first 3 rows of eval/meta/fleurs_hy_am_test100.csv) under
several variants and prints each English output with its token count and time.
Information only: no pass/fail. Does not change the app.

Run ONCE in .venv-convert (it has ctranslate2 + transformers + torch), from the repo root:
    .venv-convert/bin/python scripts/diag_mt.py 2>&1 | tee command_outputs/m3_s5_diag_mt.txt

Variants:
  a  CT2 int8, beam 2                    current setting (B3); should reproduce the loop
  b  CT2 int8, beam 3                    does a slightly wider beam already help?
  c  CT2 int8, beam 6                    beam of the original model config (num_beams: 6)
  d  CT2 int8 file loaded as float32, beam 2 and 6   int8 compute (partly; rounding is in the file)
  e  original PyTorch model (transformers), beam 2 and 6   does the model itself loop?
  f  CT2 int8, beam 2, no_repeat_ngram_size=3          candidate guard
  g  CT2 int8, beam 2, repetition_penalty=1.2          candidate guard
  h  CT2 int8, beam 2, ASCII ":" -> Armenian full stop "։" (U+0589)   input punctuation
"""
import os

os.environ["HF_HUB_OFFLINE"] = "1"  # set before any Hugging Face import (D15)

import csv  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import ctranslate2  # noqa: E402
import sentencepiece as spm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CT2_DIR = ROOT / "models" / "opus-mt-hy-en-ct2-int8"
HF_DIR = ROOT / "models" / "src" / "opus-mt-hy-en"
FLEURS_CSV = ROOT / "eval" / "meta" / "fleurs_hy_am_test100.csv"
N_SENTENCES = 3
THREADS = 2          # same as B1 intra_threads
CT2_LIMIT = 256      # CTranslate2 default max_decoding_length
EOS = "</s>"


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def load_sentences() -> list[str]:
    if not FLEURS_CSV.is_file():
        fail(f"missing {FLEURS_CSV}")
    with FLEURS_CSV.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))[:N_SENTENCES]
    if len(rows) != N_SENTENCES:
        fail(f"{FLEURS_CSV} has fewer than {N_SENTENCES} rows")
    return [r["armenian"] for r in rows]


def check_files() -> None:
    for p in (CT2_DIR / "model.bin", CT2_DIR / "source.spm", CT2_DIR / "target.spm",
              HF_DIR / "pytorch_model.bin", HF_DIR / "config.json"):
        if not p.is_file():
            fail(f"model file missing: {p} (run scripts/download_models.py)")


def report(variant: str, i: int, english: str, n_tokens: int, dt: float, limit: int) -> None:
    flag = "  <-- HIT LENGTH LIMIT (loop)" if n_tokens >= limit else ""
    print(f"[{variant}] s{i + 1} | {n_tokens:3d} tokens | {dt:5.2f} s{flag}")
    print(f"    EN: {english}")


class Ct2:
    def __init__(self, compute_type: str):
        self.tr = ctranslate2.Translator(str(CT2_DIR), device="cpu", compute_type=compute_type,
                                         inter_threads=1, intra_threads=THREADS)
        self.sp_src = spm.SentencePieceProcessor(model_file=str(CT2_DIR / "source.spm"))
        self.sp_tgt = spm.SentencePieceProcessor(model_file=str(CT2_DIR / "target.spm"))

    def run(self, variant: str, sentences: list[str], **opts) -> None:
        for i, text in enumerate(sentences):
            tokens = self.sp_src.encode(text.strip(), out_type=str) + [EOS]
            t0 = time.perf_counter()
            hyp = self.tr.translate_batch([tokens], **opts)[0].hypotheses[0]
            dt = time.perf_counter() - t0
            out = [t for t in hyp if t != EOS]
            report(variant, i, self.sp_tgt.decode(out), len(out), dt, CT2_LIMIT)


def run_hf(sentences: list[str]) -> None:
    import torch
    from transformers import MarianMTModel, MarianTokenizer

    torch.set_num_threads(THREADS)
    tok = MarianTokenizer.from_pretrained(str(HF_DIR))
    model = MarianMTModel.from_pretrained(str(HF_DIR)).eval()
    max_len = model.config.max_length  # 512 in the original config
    for beam in (2, 6):
        variant = f"e beam{beam}"
        for i, text in enumerate(sentences):
            inputs = tok([text.strip()], return_tensors="pt")
            t0 = time.perf_counter()
            with torch.no_grad():
                ids = model.generate(**inputs, num_beams=beam, max_length=max_len)[0]
            dt = time.perf_counter() - t0
            english = tok.decode(ids, skip_special_tokens=True)
            n = int((ids != tok.pad_token_id).sum()) - 1  # minus final </s>
            report(variant, i, english, n, dt, max_len - 1)


def main() -> None:
    print(f"[env] python {sys.version.split()[0]}, ctranslate2 {ctranslate2.__version__}")
    check_files()
    sentences = load_sentences()
    for i, s in enumerate(sentences):
        print(f"HY s{i + 1}: {s}")
    print()

    int8 = Ct2("int8")
    int8.run("a int8 beam2", sentences, beam_size=2)
    int8.run("b int8 beam3", sentences, beam_size=3)
    int8.run("c int8 beam6", sentences, beam_size=6)
    int8.run("f int8 beam2 no_repeat_ngram=3", sentences, beam_size=2, no_repeat_ngram_size=3)
    int8.run("g int8 beam2 rep_penalty=1.2", sentences, beam_size=2, repetition_penalty=1.2)
    int8.run("h int8 beam2 ':'->'։'", [s.replace(":", "։") for s in sentences], beam_size=2)
    del int8

    f32 = Ct2("float32")
    f32.run("d float32 beam2", sentences, beam_size=2)
    f32.run("d float32 beam6", sentences, beam_size=6)
    del f32

    run_hf(sentences)
    print("[done] diag_mt finished")


if __name__ == "__main__":
    main()
