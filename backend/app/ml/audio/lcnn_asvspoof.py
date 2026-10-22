"""Model stage of the audio verdict in ``audio_model_source="lcnn_asvspoof"`` mode.

Scores an utterance with the ASVspoof 2019 LA-trained LCNN exactly as it was
evaluated (``ml/evaluation/eval_asvspoof.py``): LFCC of every 4 s window,
float32 inference, mean of the window spoof logits. The mean logit is mapped
to a probability with the class-balanced Platt scaling fitted on the dev split
(``paper/config/audio_calibration.json``).

The model was trained on waveforms as read from the file, so callers pass the
waveform before peak normalisation; ``peak_normalised=True`` records that a
normalised waveform had to be used instead.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from app.ml.asvspoof_frontend import SAMPLE_RATE, utterance_lfcc


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
    with torch.no_grad():
        logits = loaded.module(features.to(loaded.device, dtype=torch.float32)).float().squeeze(1).cpu().numpy()
    mean_logit = float(logits.mean())
    calibration = loaded.metadata["calibration"]
    a, b = float(calibration["a"]), float(calibration["b"])
    probability = float(1.0 / (1.0 + np.exp(-(a * mean_logit + b))))
    return {
        "probability": probability,
        "mean_spoof_logit": mean_logit,
        "cm_score": -mean_logit,
        "n_windows": int(logits.size),
        "window_spoof_logits": [round(float(v), 4) for v in logits],
        "model_version": loaded.version,
        "checkpoint": loaded.metadata["checkpoint"],
        "checkpoint_sha256": loaded.metadata["checkpoint_sha256"],
        "calibration": {"method": calibration.get("method"), "a": a, "b": b},
        "input_peak_normalised": bool(peak_normalised),
        "resampled_from_hz": resampled_from,
    }
