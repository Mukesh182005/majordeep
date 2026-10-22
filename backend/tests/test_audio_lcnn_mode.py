"""Phase 3: the ASVspoof-trained LCNN in the audio verdict, behind ``audio_model_source``.

* the legacy mode reproduces the output recorded before the change
  (``fixtures/audio_legacy_reference.json``, written by running this file as a
  script on the unchanged code);
* the backend LFCC front end reproduces the cached training features;
* class-balanced Platt scaling recovers known parameters;
* in ``lcnn_asvspoof`` mode the model stage is the calibrated LCNN probability
  computed on the waveform before peak normalisation.

Regenerate the legacy reference only on purpose (it is the regression baseline)::

    python backend/tests/test_audio_lcnn_mode.py --write-reference
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "backend"))

REFERENCE = Path(__file__).parent / "fixtures" / "audio_legacy_reference.json"
SR = 16000


def write_reference_clip(path: Path) -> Path:
    """A deterministic 3 s voiced, syllable-like test signal, 16-bit PCM WAV."""
    import soundfile as sf

    rng = np.random.default_rng(0)
    t = np.arange(3 * SR) / SR
    f0 = 140 + 8 * np.sin(2 * np.pi * 4.5 * t)
    phase = 2 * np.pi * np.cumsum(f0) / SR
    voiced = sum((0.6 / k) * np.sin(k * phase) for k in range(1, 12))
    envelope = 0.5 * (1 + np.sin(2 * np.pi * 2.0 * t - np.pi / 2))
    clip = 0.3 * voiced * envelope + 0.005 * rng.standard_normal(t.size)
    sf.write(str(path), clip.astype(np.float32), SR, subtype="PCM_16")
    return path


def run_suite(path: Path, evidence_dir: Path, torch_seed: int = 0) -> dict:
    """The audio suite as analyze_audio runs it, with the untrained SincRawNet seeded."""
    import torch

    import app.ml.audio as audio
    from app.ml.preprocessing import load_audio, normalize_waveform

    waveform, rate = load_audio(path, SR)
    torch.manual_seed(torch_seed)
    audio._AUDIO_ENSEMBLE = None  # rebuild so the random SincRawNet weights follow the seed
    kwargs = {"model_waveform": waveform} if "model_waveform" in audio.run_comprehensive_audio_forensics.__code__.co_varnames else {}
    return audio.run_comprehensive_audio_forensics(path, normalize_waveform(waveform), rate, evidence_dir, "ref", **kwargs)


def legacy_summary(result: dict) -> dict:
    models, fusion = result["models_output"], result["fusion_decision"]
    return {
        "fused_ai_probability": models["fused_ai_probability"],
        "model_branch_scores": {k: v for k, v in models.get("model_branch_scores", {}).items()
                                if isinstance(v, (int, float))},
        "generative_ai_risk_score": fusion.get("generative_ai_risk_score"),
        "structural_tampering_risk_score": fusion.get("structural_tampering_risk_score"),
        "calibrated_fake_probability": fusion.get("calibrated_fake_probability"),
        "final_verdict": fusion.get("final_verdict"),
    }


def _close(a, b, tol: float = 1e-4) -> bool:
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_close(a[k], b[k], tol) for k in a)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol
    return a == b


# --------------------------------------------------------------------------- legacy mode
def test_legacy_mode_matches_reference(tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "audio_model_source", "legacy", raising=False)
    expected = json.loads(REFERENCE.read_text(encoding="utf-8"))
    result = run_suite(write_reference_clip(tmp_path / "clip.wav"), tmp_path / "evidence")
    assert _close(legacy_summary(result), expected), (legacy_summary(result), expected)
    assert result["models_output"].get("model_stage_source", "legacy") == "legacy"


# --------------------------------------------------------------------------- front end
def test_frontend_shapes_and_float16_rounding():
    from app.ml.asvspoof_frontend import utterance_lfcc

    rng = np.random.default_rng(1)
    short = utterance_lfcc(rng.standard_normal(SR).astype(np.float32) * 0.1)
    long = utterance_lfcc(rng.standard_normal(9 * SR).astype(np.float32) * 0.1)
    assert short.shape == (1, 60, 401) and long.shape == (3, 60, 401)
    assert np.array_equal(long, long.astype(np.float16).astype(np.float32))


def test_frontend_matches_training_cache():
    """Real-data check: the served features equal the cached training features exactly."""
    data = os.environ.get("DEEPSENTINEL_DATA")
    cache_dir = REPO / "data/processed/asvspoof2019_la/features"
    if not data or not (cache_dir / "lfcc" / "dev.progress.json").exists():
        pytest.skip("ASVspoof data or LFCC cache not available")
    from app.ml.asvspoof_frontend import utterance_lfcc
    from app.ml.preprocessing import load_audio
    from ml.preprocessing.build_asvspoof2019_la import read_manifest
    from ml.training.asvspoof_dataset import CachedSplit

    cache = CachedSplit(cache_dir, "lfcc", "dev")
    rows = {r["utt_id"]: r for r in read_manifest(REPO / "data/processed/asvspoof2019_la/manifest.csv", "dev")}
    for k in (0, 1000, 20000):
        utt = cache.utt_ids[k]
        cached = np.asarray(cache.array[cache.row_start[k]: cache.row_start[k] + cache.n_windows[k]], dtype=np.float32)
        waveform, _ = load_audio(Path(data) / "ASVspoof2019" / "LA" / rows[utt]["relative_path"], SR)
        assert np.array_equal(utterance_lfcc(waveform), cached), utt


# --------------------------------------------------------------------------- calibration
def test_balanced_platt_recovers_parameters_and_ignores_class_ratio():
    from ml.evaluation.calibrate_audio_lcnn import fit_balanced_platt

    rng = np.random.default_rng(0)
    a_true, b_true = 1.7, -0.4
    x = rng.normal(0, 2, 200_000)
    y = (rng.random(x.size) < 1 / (1 + np.exp(-(a_true * x + b_true)))).astype(int)
    a, b = fit_balanced_platt(x, y)
    # Balanced weights remove the class prior: b moves by -log(n1/n0); a is unchanged.
    prior_shift = np.log((y == 1).sum() / (y == 0).sum())
    assert abs(a - a_true) < 0.05 and abs(b - (b_true - prior_shift)) < 0.05
    # Duplicating one class must not change a balanced fit.
    keep = np.concatenate([np.arange(x.size), np.flatnonzero(y == 1)])
    a2, b2 = fit_balanced_platt(x[keep], y[keep])
    assert abs(a2 - a) < 1e-6 and abs(b2 - b) < 1e-6


# --------------------------------------------------------------------------- LCNN mode
@pytest.fixture()
def lcnn_setup(tmp_path, monkeypatch):
    """A random-weight LCNN checkpoint and a calibration file pointing at it."""
    import torch

    from app.config import settings
    from app.ml import registry
    from app.ml.models_arch import build_audio_model

    torch.manual_seed(3)
    ckpt_dir = tmp_path / "checkpoints"
    ckpt_dir.mkdir()
    ckpt = ckpt_dir / "audio_lcnn_test.pt"
    torch.save({"state_dict": build_audio_model().state_dict(), "frontend": "lfcc"}, ckpt)
    calibration = {
        "checkpoint": "checkpoints/audio_lcnn_test.pt",
        "checkpoint_sha256": hashlib.sha256(ckpt.read_bytes()).hexdigest(),
        "frontend": "lfcc",
        "method": "platt_balanced",
        "a": 0.8,
        "b": 0.1,
    }
    calibration_path = tmp_path / "audio_calibration.json"
    calibration_path.write_text(json.dumps(calibration), encoding="utf-8")
    monkeypatch.setattr(settings, "checkpoint_dir", ckpt_dir)
    monkeypatch.setattr(settings, "audio_lcnn_calibration_file", calibration_path, raising=False)
    monkeypatch.setattr(settings, "audio_model_source", "lcnn_asvspoof", raising=False)
    registry.reset_cache()
    yield calibration
    registry.reset_cache()


def test_lcnn_score_is_calibrated_mean_window_logit(lcnn_setup):
    import torch

    from app.ml.asvspoof_frontend import utterance_lfcc
    from app.ml.audio.lcnn_asvspoof import score_lcnn_asvspoof
    from app.ml.registry import get_audio_lcnn_asvspoof

    rng = np.random.default_rng(2)
    waveform = (0.1 * rng.standard_normal(6 * SR)).astype(np.float32)
    out = score_lcnn_asvspoof(waveform, SR)
    model = get_audio_lcnn_asvspoof()
    with torch.no_grad():
        logits = model.module(torch.from_numpy(utterance_lfcc(waveform)).unsqueeze(1).to(model.device)).float()
    mean_logit = float(logits.mean())
    assert out["n_windows"] == 2
    assert abs(out["mean_spoof_logit"] - mean_logit) < 1e-5
    assert abs(out["cm_score"] + mean_logit) < 1e-5
    assert abs(out["probability"] - 1 / (1 + np.exp(-(0.8 * mean_logit + 0.1)))) < 1e-6


def test_lcnn_mode_replaces_model_stage(lcnn_setup, tmp_path):
    from app.ml.audio.lcnn_asvspoof import score_lcnn_asvspoof
    from app.ml.preprocessing import load_audio

    clip = write_reference_clip(tmp_path / "clip.wav")
    result = run_suite(clip, tmp_path / "evidence")
    models = result["models_output"]
    raw, _ = load_audio(clip, SR)
    assert models["model_stage_source"] == "lcnn_asvspoof"
    assert abs(models["fused_ai_probability"] - score_lcnn_asvspoof(raw, SR)["probability"]) < 1e-6
    assert "legacy_fused_ai_probability" in models
    assert models["lcnn_asvspoof"]["input_peak_normalised"] is False


def test_wrong_checkpoint_hash_is_refused(lcnn_setup, monkeypatch):
    from app.config import settings
    from app.ml import registry
    from app.ml.base import DetectorUnavailableError

    path = Path(settings.audio_lcnn_calibration_file)
    calibration = json.loads(path.read_text(encoding="utf-8"))
    calibration["checkpoint_sha256"] = "0" * 64
    path.write_text(json.dumps(calibration), encoding="utf-8")
    registry.reset_cache()
    with pytest.raises(DetectorUnavailableError, match="sha256"):
        registry.get_audio_lcnn_asvspoof()


if __name__ == "__main__" and "--write-reference" in sys.argv:
    with tempfile.TemporaryDirectory() as tmp:
        summary = legacy_summary(run_suite(write_reference_clip(Path(tmp) / "clip.wav"), Path(tmp) / "evidence"))
    REFERENCE.parent.mkdir(parents=True, exist_ok=True)
    REFERENCE.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
