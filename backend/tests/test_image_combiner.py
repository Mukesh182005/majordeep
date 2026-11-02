"""The learned image-detector combination (app/ml/image_combiner.py)."""

import json
import math

from app.config import settings
from app.ml import image_combiner


def _logit(p):
    return math.log(p / (1 - p))


def _write(tmp_path, monkeypatch, models, coef, intercept, z_authentic=None, z_manipulated=None):
    """Cut-offs default to the band itself, so the combination is not rescaled."""
    monkeypatch.setattr(settings, "checkpoint_dir", tmp_path)
    monkeypatch.setattr(settings, "fake_threshold", 0.5)
    monkeypatch.setattr(settings, "uncertain_band", 0.08)
    (tmp_path / "image_combiner.json").write_text(json.dumps({
        "models": models, "coef": coef, "intercept": intercept,
        "z_authentic": _logit(0.42) if z_authentic is None else z_authentic,
        "z_manipulated": _logit(0.58) if z_manipulated is None else z_manipulated}), encoding="utf-8")


def test_no_file_means_no_combination(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "checkpoint_dir", tmp_path)
    assert image_combiner.combine({"a": 0.9}) is None


def test_combines_log_odds_with_the_stored_coefficients(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, ["a", "b"], [1.0, 2.0], -0.5)
    p = image_combiner.combine({"a": 0.8, "b": 0.3})
    z = -0.5 + math.log(0.8 / 0.2) + 2 * math.log(0.3 / 0.7)
    assert abs(p - 1 / (1 + math.exp(-z))) < 1e-9


def test_a_local_checkpoint_matches_by_the_end_of_its_path(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, ["commfor_ft_v3/model.safetensors"], [1.0], 0.0)
    p = image_combiner.combine({r"C:\any\checkpoints\commfor_ft_v3/model.safetensors": 0.9})
    assert abs(p - 0.9) < 1e-6


def test_a_missing_detector_falls_back(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, ["a", "b"], [1.0, 1.0], 0.0)
    assert image_combiner.combine({"a": 0.9}) is None


def test_switched_off_by_setting(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, ["a"], [1.0], 0.0)
    monkeypatch.setattr(settings, "image_combiner_enabled", False)
    assert image_combiner.combine({"a": 0.9}) is None


def test_the_measured_cut_offs_land_on_any_configured_band(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, ["a"], [1.0], 0.0, z_authentic=-3.0, z_manipulated=1.0)
    monkeypatch.setattr(settings, "uncertain_band", 0.15)  # band 0.35 / 0.65
    at_low = image_combiner.combine({"a": 1 / (1 + math.exp(3.0))})
    at_high = image_combiner.combine({"a": 1 / (1 + math.exp(-1.0))})
    assert abs(at_low - 0.35) < 1e-3 and abs(at_high - 0.65) < 1e-3
