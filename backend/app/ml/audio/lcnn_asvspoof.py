"""Model stage of the audio verdict in ``audio_model_source="lcnn_asvspoof"`` mode.

Scores an utterance with the ASVspoof 2019 LA-trained LCNN exactly as it was
evaluated (``ml/evaluation/eval_asvspoof.py``): LFCC of every 4 s window,
float32 inference, mean of the window spoof logits. The mean logit is mapped
to a probability with the class-balanced Platt scaling fitted on the dev split
(``paper/config/audio_calibration.json``). Each window's own calibrated
probability is reported for the timeline; the verdict uses the mean only.

Inference is strict float32 and deterministic (no TF32, deterministic cuDNN
algorithms), so the same file gives the same score in every process.

The model was trained on waveforms as read from the file, so callers pass the
waveform before peak normalisation; ``peak_normalised=True`` records that a
normalised waveform had to be used instead.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from app.ml.asvspoof_frontend import SAMPLE_RATE, WINDOW_SAMPLES, utterance_lfcc


def window_spans(num_samples: int, sample_rate: int = SAMPLE_RATE, window: int = WINDOW_SAMPLES) -> list[tuple[float, float]]:
    """(start, end) in seconds of each window ``utterance_windows`` cuts.

    Up to 4 s: one window over the whole clip (repeated to 4 s for the model).
    Longer: consecutive 4 s windows, then the last 4 s if a remainder is left.
    """
    duration = num_samples / sample_rate
    if num_samples <= window:
        return [(0.0, duration)]
    spans = [(i * window / sample_rate, (i + 1) * window / sample_rate) for i in range(num_samples // window)]
    if num_samples % window:
        spans.append((duration - window / sample_rate, duration))
    return spans


@lru_cache(maxsize=4)
def _verdict_config(path: str, mtime: float) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_verdict_config() -> dict[str, Any]:
    """The frozen audio verdict rule (``paper/config/frozen_audio_config.json``).

    Refused unless it was frozen for the checkpoint the calibration file names:
    thresholds fitted for one model mean nothing for another.
    """
    from app.config import settings
    from app.ml.base import DetectorUnavailableError

    path = Path(settings.audio_verdict_config_file)
    if not path.is_file():
        raise DetectorUnavailableError(f"Frozen audio verdict config not found: {path}")
    config = _verdict_config(str(path), path.stat().st_mtime)
    calibration = json.loads(Path(settings.audio_lcnn_calibration_file).read_text(encoding="utf-8"))
    if config.get("checkpoint_sha256") != calibration.get("checkpoint_sha256"):
        raise DetectorUnavailableError(
            f"{path.name} was frozen for a different checkpoint than {Path(settings.audio_lcnn_calibration_file).name}."
        )
    return config


def score_lcnn_asvspoof(waveform: np.ndarray, sample_rate: int, peak_normalised: bool = False) -> dict[str, Any]:
    import torch

    from app.ml.registry import get_audio_lcnn_asvspoof

    loaded = get_audio_lcnn_asvspoof()
    wave = np.asarray(waveform, dtype=np.float32)
    if wave.ndim > 1:
        wave = wave.mean(axis=1)
    resampled_from = None
    if sample_rate != SAMPLE_RATE:
        import librosa

        wave = librosa.resample(wave, orig_sr=sample_rate, target_sr=SAMPLE_RATE).astype(np.float32)
        resampled_from = sample_rate

    features = torch.from_numpy(utterance_lfcc(wave)).unsqueeze(1)
    previous_matmul_tf32 = torch.backends.cuda.matmul.allow_tf32
    try:
        torch.backends.cuda.matmul.allow_tf32 = False
        with torch.no_grad(), torch.backends.cudnn.flags(enabled=True, benchmark=False, deterministic=True, allow_tf32=False):
            logits = loaded.module(features.to(loaded.device, dtype=torch.float32)).float().squeeze(1).cpu().numpy()
    finally:
        torch.backends.cuda.matmul.allow_tf32 = previous_matmul_tf32
    logits = np.atleast_1d(logits)
    mean_logit = float(logits.mean())
    calibration = loaded.metadata["calibration"]
    a, b = float(calibration["a"]), float(calibration["b"])

    def calibrated(logit: float) -> float:
        return float(1.0 / (1.0 + np.exp(-(a * logit + b))))

    spans = window_spans(wave.size)
    return {
        "probability": calibrated(mean_logit),
        "mean_spoof_logit": mean_logit,
        "cm_score": -mean_logit,
        "n_windows": int(logits.size),
        "window_spoof_logits": [round(float(v), 4) for v in logits],
        "windows": [
            {"index": i, "start_s": round(start, 3), "end_s": round(end, 3),
             "spoof_logit": round(float(logit), 4), "probability": round(calibrated(float(logit)), 4)}
            for i, ((start, end), logit) in enumerate(zip(spans, logits, strict=True))
        ],
        "model_version": loaded.version,
        "checkpoint": loaded.metadata["checkpoint"],
        "checkpoint_sha256": loaded.metadata["checkpoint_sha256"],
        "calibration": {"method": calibration.get("method"), "a": a, "b": b},
        "input_peak_normalised": bool(peak_normalised),
        "resampled_from_hz": resampled_from,
        "inference": "float32, TF32 off, deterministic cuDNN",
    }
