"""D31 F3: export the CTC head of NVIDIA's Armenian FastConformer hybrid to ONNX for sherpa-onnx.

Runs in .venv-nemo (D31 F1), once. Normally called by scripts/download_models.py:
    .venv-nemo/bin/python scripts/export_fastconformer.py \
        --nemo models/src/fastconformer-hy/stt_hy_fastconformer_hybrid_large_pc.nemo \
        --out models/fastconformer-hy-ctc

E1  writes into <out>.part and renames it to <out> only at the end; refuses if <out> exists;
    HF_HUB_OFFLINE=1, nothing is downloaded.
E2  ASRModel.restore_from(..., map_location="cpu"); the model must be the hybrid RNNT+CTC BPE class.
E3  reads sample rate (must be 16000), feature count, normalize and subsampling factor from the
    model config and prints them.
E4  exports the CTC head only: set_export_config({"decoder_type": "ctc"}) + export("model.onnx");
    the ONNX output size must equal vocabulary + 1 (blank).
E5  tokens.txt from the CTC decoder vocabulary, "<token> <id>", <blk> last.
E6  metadata in the ONNX files: vocab_size, normalize_type, subsampling_factor (from E3), plus
    model_type, version, url, comment.
E7  model.int8.onnx with onnxruntime quantize_dynamic (QUInt8); E6 metadata is added to both files.
E8  self-check on tests/fixtures/speech_short.wav: NeMo's own CTC output (torch forward of the
    model: preprocessor -> encoder -> CTC decoder, greedy) is the reference; model.onnx in
    onnxruntime on the same NeMo features must give exactly the same text (else fail);
    model.int8.onnx text and its CER against fp32 are printed, no limit.
E9  prints file sizes, SHA-256, time taken and peak RSS.
Any problem stops the script with "ERROR:" and exit code 1 (working rule 2).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import resource
import shutil
import sys
import time
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"  # E1: never download (D15)

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "speech_short.wav"
SOURCE_URL = ("https://huggingface.co/nvidia/stt_hy_fastconformer_hybrid_large_pc"
              "@353b40909f02cf5b74a577294822d8c73fbb1ca1")
HYBRID_CLASS = "EncDecHybridRNNTCTCBPEModel"
SAMPLE_RATE = 16000


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def log(msg: str) -> None:
    print(msg, flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def peak_rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # Linux: KiB


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def greedy_ids(logprobs, blank: int) -> list[int]:
    """Greedy CTC: best label per frame, merge repeats, drop blanks. logprobs: [frames, classes]."""
    best = logprobs.argmax(axis=-1).tolist()
    out, last = [], None
    for t in best:
        if t != last and t != blank:
            out.append(t)
        last = t
    return out


def add_metadata(path: Path, meta: dict) -> None:
    import onnx
    model = onnx.load(str(path))
    existing = {p.key for p in model.metadata_props}
    for key, value in meta.items():
        if key in existing:
            fail(f"E6: {path.name} already has metadata key {key!r}")
        prop = model.metadata_props.add()
        prop.key, prop.value = key, str(value)
    onnx.save(model, str(path))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--nemo", type=Path, required=True, help="the .nemo checkpoint (D31 F2)")
    ap.add_argument("--out", type=Path, required=True, help="output folder, must not exist")
    args = ap.parse_args()
    t_start = time.monotonic()

    # ---------------------------------------------------------------- E1
    nemo_path, out_dir = args.nemo.resolve(), args.out.resolve()
    if not nemo_path.is_file():
        fail(f"E1: .nemo file not found: {nemo_path} (run scripts/download_models.py, D31 F2)")
    if out_dir.exists():
        fail(f"E1: output folder already exists: {out_dir}; delete it to export again")
    if not FIXTURE.is_file():
        fail(f"E8: fixture missing: {FIXTURE} (D22)")
    part_dir = out_dir.with_name(out_dir.name + ".part")
    if part_dir.exists():
        log(f"# E1: removing our own unfinished {part_dir} from an earlier run")
        shutil.rmtree(part_dir)
    part_dir.mkdir(parents=True)

    import numpy as np
    import onnx
    import onnxruntime as ort
    import soundfile as sf
    import torch
    import nemo
    import nemo.collections.asr as nemo_asr
    from onnxruntime.quantization import QuantType, quantize_dynamic
    log(f"# nemo {nemo.__version__}, torch {torch.__version__}, onnx {onnx.__version__}, "
        f"onnxruntime {ort.__version__}")

    # ---------------------------------------------------------------- E2
    log(f"# E2: loading {nemo_path} on the CPU ...")
    t0 = time.monotonic()
    m = nemo_asr.models.ASRModel.restore_from(restore_path=str(nemo_path), map_location="cpu")
    m.eval()
    cls = type(m).__name__
    log(f"# E2: loaded {cls} in {time.monotonic() - t0:.1f} s; peak RSS {peak_rss_mb():.0f} MB")
    if cls != HYBRID_CLASS:
        fail(f"E2: expected {HYBRID_CLASS}, got {cls}")

    # ---------------------------------------------------------------- E3
    pre = m.cfg.preprocessor
    sample_rate = int(pre.sample_rate)
    features = int(pre.features)
    normalize = pre.get("normalize", None)
    normalize_type = "" if normalize in (None, "NA", "None") else str(normalize)
    subsampling = int(m.cfg.encoder.subsampling_factor)
    log(f"# E3: sample_rate {sample_rate}, features {features}, normalize {normalize!r} "
        f"-> normalize_type {normalize_type!r}, subsampling_factor {subsampling}")
    if sample_rate != SAMPLE_RATE:
        fail(f"E3: sample rate {sample_rate}, expected {SAMPLE_RATE}")
    if features != 80 or subsampling != 8 or normalize_type != "per_feature":
        log("# E3: NOTE: differs from the values seen in other sherpa-onnx FastConformer exports "
            "(80 / 8 / per_feature); the values read here are the ones written (E6)")

    # ---------------------------------------------------------------- E4
    vocab = list(m.ctc_decoder.vocabulary)
    n_classes = int(m.ctc_decoder.num_classes_with_blank)
    blank = len(vocab)
    if n_classes != len(vocab) + 1:
        fail(f"E4: CTC decoder has {n_classes} classes, vocabulary {len(vocab)} + blank expected")
    onnx_path = part_dir / "model.onnx"
    log(f"# E4: exporting the CTC head (vocabulary {len(vocab)} + blank) ...")
    t0 = time.monotonic()
    m.set_export_config({"decoder_type": "ctc"})
    m.export(str(onnx_path))
    log(f"# E4: exported in {time.monotonic() - t0:.1f} s; peak RSS {peak_rss_mb():.0f} MB")
    if not onnx_path.is_file():
        fail(f"E4: export wrote no {onnx_path}")
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    ins = [(i.name, i.shape) for i in sess.get_inputs()]
    outs = [(o.name, o.shape) for o in sess.get_outputs()]
    log(f"# E4: ONNX inputs {ins}, outputs {outs}")
    if len(ins) != 2 or len(outs) < 1:
        fail(f"E4: expected 2 inputs (audio features, length) and a log-prob output")
    if outs[0][1][-1] != n_classes:
        fail(f"E4: ONNX output size {outs[0][1][-1]}, expected {n_classes} (vocabulary + blank)")
    del sess

    # ---------------------------------------------------------------- E5
    tokens_path = part_dir / "tokens.txt"
    with open(tokens_path, "w", encoding="utf-8") as f:
        for i, tok in enumerate(vocab):
            if not tok or any(c.isspace() for c in tok):
                fail(f"E5: token {i} {tok!r} is empty or contains whitespace")
            f.write(f"{tok} {i}\n")
        f.write(f"<blk> {blank}\n")
    log(f"# E5: tokens.txt: {len(vocab) + 1} lines, <blk> = {blank}")

    # ---------------------------------------------------------------- E7 (before E6, see docstring)
    int8_path = part_dir / "model.int8.onnx"
    log("# E7: quantizing to int8 (dynamic, QUInt8) ...")
    t0 = time.monotonic()
    quantize_dynamic(str(onnx_path), str(int8_path), weight_type=QuantType.QUInt8)
    log(f"# E7: done in {time.monotonic() - t0:.1f} s")

    # ---------------------------------------------------------------- E6
    meta = {
        "vocab_size": n_classes,
        "normalize_type": normalize_type,
        "subsampling_factor": subsampling,
        "model_type": "EncDecCTCModelBPE",
        "version": "1",
        "url": SOURCE_URL,
        "comment": "CTC head of stt_hy_fastconformer_hybrid_large_pc, exported for sherpa-onnx (D31 F3)",
    }
    for p in (onnx_path, int8_path):
        add_metadata(p, meta)
    log(f"# E6: metadata added to model.onnx and model.int8.onnx: {meta}")

    # ---------------------------------------------------------------- E8
    audio, sr = sf.read(str(FIXTURE), dtype="float32")
    if sr != SAMPLE_RATE or audio.ndim != 1:
        fail(f"E8: {FIXTURE} must be 16 kHz mono, got {sr} Hz, shape {audio.shape}")
    with torch.no_grad():
        signal = torch.from_numpy(audio).unsqueeze(0)
        length = torch.tensor([len(audio)], dtype=torch.int64)
        feats, feat_len = m.preprocessor(input_signal=signal, length=length)
        encoded, enc_len = m.encoder(audio_signal=feats, length=feat_len)
        ref_logp = m.ctc_decoder(encoder_output=encoded)[0, : int(enc_len[0])].numpy()
    ref_text = m.tokenizer.ids_to_text(greedy_ids(ref_logp, blank))
    log(f"# E8: fixture {FIXTURE.name}: {len(audio) / SAMPLE_RATE:.2f} s, {int(enc_len[0])} frames")
    log(f"# E8: NeMo (torch) CTC : {ref_text}")
    if not ref_text.strip():
        fail("E8: NeMo's own CTC output is empty on the speech fixture")

    feed_names = [i[0] for i in ins]
    texts = {}
    for name, p in (("fp32", onnx_path), ("int8", int8_path)):
        s = ort.InferenceSession(str(p), providers=["CPUExecutionProvider"])
        t0 = time.monotonic()
        out = s.run(None, {feed_names[0]: feats.numpy(),
                           feed_names[1]: feat_len.numpy().astype(np.int64)})
        dt = time.monotonic() - t0
        texts[name] = m.tokenizer.ids_to_text(greedy_ids(out[0][0], blank))
        log(f"# E8: ONNX {name} CTC ({dt:.2f} s on the CPU): {texts[name]}")
    if texts["fp32"] != ref_text:
        fail("E8: model.onnx (fp32) text differs from NeMo's own CTC output; the export is not trusted")
    log("# E8: fp32 ONNX text == NeMo text: OK")
    c = edit_distance(texts["int8"], texts["fp32"]) / max(len(texts["fp32"]), 1)
    log(f"# E8: int8 vs fp32 CER {100 * c:.1f} % (reported only, no limit)")

    # ---------------------------------------------------------------- E1 + E9
    part_dir.rename(out_dir)
    log(f"# E9: results in {out_dir}:")
    for p in sorted(out_dir.iterdir()):
        log(f"#   {p.name}: {p.stat().st_size} bytes, sha256 {sha256_file(p)}")
    log(f"# E9: total {time.monotonic() - t_start:.1f} s; peak RSS {peak_rss_mb():.0f} MB")
    log("EXPORT OK")


if __name__ == "__main__":
    main()
