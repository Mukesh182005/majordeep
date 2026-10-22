"""Rule-based model stage of the audio suite (``audio_model_source="legacy"``).

What used to run here, and was removed because none of it was a trained model:

* a sinc-filter waveform network built with random weights and never loaded
  from a checkpoint, so the same clip scored differently in every process;
* two probabilities labelled with the names of self-supervised speech models
  (layer 18 and layer 4 "probing") that were a high-frequency
  spectral-smoothness formula (the second was 0.92 x the first + 0.04);
  neither model was ever loaded;
* a typology breakdown and a generator-family attribution derived from those
  two numbers.

What remains is the hand-set tabular rule score (glottal anomaly, jitter/HNR,
high-order LFCC energy, trailing container bytes) and a rule-based audio-domain
label. Both are heuristics that have not been validated: on the balanced
ASVspoof 2019 LA dev subsample the tabular score's AUC was 0.552
(paper_results/audio_heuristics_dev/signal_auc.json, signals.model_tabular).
The trained detector is the ASVspoof 2019 LA LCNN (app/ml/audio/lcnn_asvspoof.py).
"""

from __future__ import annotations

from typing import Any

import numpy as np

HEURISTIC_LABEL = "heuristic (unvalidated)"


def score_audio_heuristics(
    signal_intel: dict[str, Any],
    glottal_physics: dict[str, Any],
    file_dna: dict[str, Any],
) -> dict[str, Any]:
    """Model-stage output when no trained audio model is in use."""
    tabular_prob = score_tabular_features(signal_intel, glottal_physics, file_dna)
    return {
        "fused_ai_probability": round(tabular_prob, 4),
        "model_stage_source": "legacy",
        "model_stage_label": HEURISTIC_LABEL,
        "heuristic_scores": {"tabular_rules_prob": round(tabular_prob, 4)},
        "audio_domain": classify_domain(signal_intel),
        "audio_domain_label": HEURISTIC_LABEL,
    }


def score_tabular_features(intel: dict[str, Any], physics: dict[str, Any], dna: dict[str, Any]) -> float:
    """Hand-set rules over the deterministic signal descriptors (not trained)."""
    score = 0.10
    # Glottal flow anomaly
    glottal_score = physics.get("composite_physiological_anomaly_score", 0.0)
    score += 0.35 * glottal_score

    # Voice quality: synthetic speech is assumed to show very low jitter with high HNR
    vq = intel.get("voice_quality", {})
    jitter = vq.get("jitter_local_percent", 0.0)
    hnr = vq.get("harmonics_to_noise_ratio_db", 20.0)
    if 0 < jitter < 0.12 and hnr > 28.0:
        score += 0.25

    # High-order LFCC energy
    cep = intel.get("cepstral_analysis", {})
    lfcc = cep.get("lfcc_coefficients_1_20", [])
    if len(lfcc) >= 15:
        high_lfcc_energy = np.mean(np.abs(lfcc[10:]))
        if high_lfcc_energy < 0.25:
            score += 0.15

    # Bytes appended after the end of the audio stream
    if dna.get("trailing_data_detected", False):
        score += 0.10

    return float(min(0.98, max(0.02, score)))


def classify_domain(intel: dict[str, Any]) -> str:
    """Rule-based guess at speech / singing / ambient / other from spectral descriptors."""
    freq = intel.get("frequency_domain", {})
    centroid = freq.get("spectral_centroid_hz", 2000.0)
    flatness = freq.get("spectral_flatness", 0.05)
    vq = intel.get("voice_quality", {})
    voiced = vq.get("voiced_to_unvoiced_ratio", 0.5)

    if voiced > 0.40 and 200 <= centroid <= 3800:
        return "CONVERSATIONAL_SPEECH"
    elif voiced > 0.55 and centroid > 3800:
        return "SINGING_VOICE"
    elif flatness > 0.15:
        return "AMBIENT_OR_ENVIRONMENTAL"
    else:
        return "GENERAL_AUDIO_OR_MUSIC"
