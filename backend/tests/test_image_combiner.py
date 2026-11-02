"""The learned image-detector combination (app/ml/image_combiner.py)."""

import json
import math

from app.config import settings
from app.ml import image_combiner


def _write(tmp_path, monkeypatch, models, coef, intercept):
    monkeypatch.setattr(settings, "checkpoint_dir", tmp_path)
    (tmp_path / "image_combiner.json").write_text(
        json.dumps({"models": models, "coef": coef, "intercept": intercept}), encoding="utf-8")


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
