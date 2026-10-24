#!/usr/bin/env python3
"""Dev diagnostic behind plan amendment v2: does resampling alone change the served model's verdict?

The first 150 bona fide utterances of the balanced dev subsample
(``paper_results/audio_heuristics_dev/subsample.csv``), scored by the served
checkpoint (CPU, float32) under its calibration and frozen rule, in five paths:

* ``original``: the FLAC file as distributed (16 kHz);
* ``up48_soxr_down``: 16 kHz -> 48 kHz (soxr, written as 16-bit PCM) -> 16 kHz with soxr;
* ``up48_ffmpeg_down``: the same 48 kHz file -> 16 kHz with ffmpeg's resampler;
* ``opus_libsndfile_soxr``: Opus 32 kbit/s, decoded at 48 kHz by libsndfile, -> 16 kHz with soxr;
* ``opus_ffmpeg``: the same Opus file decoded straight to 16 kHz by ffmpeg.

Writes ``paper_results/audio_codec_dev/resampling_diagnostic.json``. Dev data only.

Usage (PowerShell)::

    $env:DEEPSENTINEL_DATA = "C:\\deepsentinel_data"
    python ml/evaluation/audio_resampling_diagnostic.py
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.common import REPO_ROOT  # noqa: E402

SUBSAMPLE = REPO_ROOT / "paper_results/audio_heuristics_dev/subsample.csv"
OUTPUT = REPO_ROOT / "paper_results/audio_codec_dev/resampling_diagnostic.json"
PATHS = ("original", "up48_soxr_down", "up48_ffmpeg_down", "opus_libsndfile_soxr", "opus_ffmpeg")
N_UTTERANCES = 150


def main() -> int:
    import librosa
    import soundfile as sf
    import torch
    from app.ml.asvspoof_frontend import utterance_lfcc

    from ml.evaluation.eval_asvspoof import load_model
    from ml.preprocessing.audio_codecs import ffmpeg_exe
    from ml.preprocessing.build_asvspoof2019_la import default_la_root
    from ml.provenance import collect_provenance, sha256_file

    calibration = json.loads((REPO_ROOT / "paper/config/audio_calibration.json").read_text(encoding="utf-8"))
    frozen = json.loads((REPO_ROOT / "paper/config/frozen_audio_config.json").read_text(encoding="utf-8"))
    checkpoint = REPO_ROOT / "checkpoints" / Path(calibration["checkpoint"]).name
    if sha256_file(checkpoint) != calibration["checkpoint_sha256"]:
        raise SystemExit(f"{checkpoint.name} is not the served checkpoint.")
    root = default_la_root()
    if root is None:
        raise SystemExit("Set DEEPSENTINEL_DATA.")
    model, _ = load_model(checkpoint, torch.device("cpu"))
    exe = ffmpeg_exe()

    def probability(wave: np.ndarray) -> float:
        with torch.no_grad():
            logits = model(torch.from_numpy(utterance_lfcc(wave.astype(np.float32))).unsqueeze(1)).squeeze(1).numpy()
        return float(1 / (1 + np.exp(-(calibration["a"] * float(np.mean(logits)) + calibration["b"]))))

    with open(SUBSAMPLE, newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle) if r["label"] == "0"][:N_UTTERANCES]
    probs: dict[str, list[float]] = {p: [] for p in PATHS}
    for row in rows:
        source = root / "ASVspoof2019_LA_dev/flac" / f"{row['utt_id']}.flac"
        wave, _ = sf.read(str(source), dtype="float32")
        probs["original"].append(probability(wave))
        with tempfile.TemporaryDirectory(prefix="ds-resample-diag-") as tmp:
            tmp = Path(tmp)
            sf.write(tmp / "up.wav", librosa.resample(wave, orig_sr=16000, target_sr=48000, res_type="soxr_hq"),
                     48000, subtype="PCM_16")
            up, _ = sf.read(tmp / "up.wav", dtype="float32")
            probs["up48_soxr_down"].append(probability(librosa.resample(up, orig_sr=48000, target_sr=16000,
                                                                        res_type="soxr_hq")))
            run = [exe, "-v", "error", "-y", "-i"]
            subprocess.run([*run, str(tmp / "up.wav"), "-ar", "16000", "-ac", "1", str(tmp / "down.wav")], check=True)
            probs["up48_ffmpeg_down"].append(probability(sf.read(tmp / "down.wav", dtype="float32")[0]))
            subprocess.run([*run, str(source), "-c:a", "libopus", "-b:a", "32k", str(tmp / "x.ogg")], check=True)
            opus, rate = sf.read(tmp / "x.ogg", dtype="float32")
            probs["opus_libsndfile_soxr"].append(probability(librosa.resample(opus, orig_sr=rate, target_sr=16000,
                                                                              res_type="soxr_hq")))
            subprocess.run([*run, str(tmp / "x.ogg"), "-ar", "16000", "-ac", "1", str(tmp / "o.wav")], check=True)
            probs["opus_ffmpeg"].append(probability(sf.read(tmp / "o.wav", dtype="float32")[0]))

    flag = float(frozen["flagged_at_or_above"])
    result = {
        "purpose": "Dev diagnostic for audio_codec_plan.json amendment v2: resampling and decoding paths",
        "utterances": {"file": "paper_results/audio_heuristics_dev/subsample.csv",
                       "selection": f"first {N_UTTERANCES} bona fide rows", "n": len(rows)},
        "checkpoint": calibration["checkpoint"], "checkpoint_sha256": calibration["checkpoint_sha256"],
        "rule": {"flagged_at_or_above": flag},
        "paths": {p: {"bonafide_flagged_rate": float(np.mean(np.array(v) >= flag)),
                      "median_probability": float(np.median(v))} for p, v in probs.items()},
        "provenance": collect_provenance(SUBSAMPLE),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    for p, entry in result["paths"].items():
        print(f"{p:22s} bona fide flagged {entry['bonafide_flagged_rate'] * 100:5.1f}%  "
              f"median p {entry['median_probability']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
