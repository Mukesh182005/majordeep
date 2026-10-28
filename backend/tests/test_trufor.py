"""TruFor wiring: safe checkpoint loading, pinned weights, and how its result reaches the image verdict.

No downloads: the real model is replaced by a stub; the loader is tested on small files.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

torch = pytest.importorskip("torch")

from app.config import settings  # noqa: E402
from app.models import Verdict  # noqa: E402


def test_loader_accepts_numpy_scalars_but_not_arbitrary_objects(tmp_path):
    from app.ml import trufor

    good = tmp_path / "good.pth.tar"
    torch.save({"state_dict": {"w": torch.zeros(2)}, "best": np.float64(0.9)}, good)
    assert set(trufor._load_state_dict(good)) == {"w"}

    bad = tmp_path / "bad.pth.tar"
    torch.save({"state_dict": {"w": torch.zeros(2)}, "obj": Image.new("RGB", (1, 1))}, bad)
    with pytest.raises(Exception):
        trufor._load_state_dict(bad)


def test_weights_with_the_wrong_hash_are_refused(tmp_path, monkeypatch):
    from app.ml import trufor

    fake = tmp_path / "trufor.pth.tar"
    torch.save({"state_dict": {}}, fake)
    monkeypatch.setattr(trufor, "_MODEL", None)
    monkeypatch.setattr(trufor, "_FAILED", False)
    monkeypatch.setattr(settings, "trufor_enabled", True)
    monkeypatch.setattr(settings, "trufor_weights", str(fake))
    assert trufor.get_trufor() is None


def _stub(score: float):
    def analyze(image, heatmap_path=None, loaded=None):
        if heatmap_path is not None:
            Image.new("RGB", (8, 8)).save(heatmap_path)
        return {"score": score, "manipulated_area_fraction": 0.12, "mean_localisation": 0.1, "mean_confidence": 0.8,
                "analysed_size": [256, 256], "downscaled": False, "model": "TruFor (CVPR 2023)", "citation": "test",
                "heatmap_file": None if heatmap_path is None else heatmap_path.name, "region_box": [10, 10, 50, 50]}
    return analyze


def _run(tmp_path, monkeypatch, score: float, in_verdict: bool):
    import app.ml.image_pipeline as ip
    from app.ml import trufor

    monkeypatch.setattr(settings, "trufor_enabled", True)
    monkeypatch.setattr(settings, "trufor_in_verdict", in_verdict)
    monkeypatch.setattr(trufor, "analyze", _stub(score))
    monkeypatch.setattr(ip, "score_scene", lambda image: {"scene_ai_prob": 0.001, "model_scores": {"test/model": 0.001}})
    source = tmp_path / "photo.png"
    Image.new("RGB", (256, 256), (40, 90, 140)).save(source)
    return ip.analyze_image(source, tmp_path / "evidence", "trufor-job")


def test_flagged_region_is_shown_but_does_not_change_the_verdict_by_default(tmp_path, monkeypatch):
    result = _run(tmp_path, monkeypatch, score=0.9, in_verdict=False)
    ev = result.evidence
    assert result.verdict is Verdict.AUTHENTIC
    assert ev["trufor"]["flagged"] and not ev["trufor"]["in_verdict"]
    assert ev["trufor_file"] == "trufor-job_trufor.png" and (tmp_path / "evidence" / ev["trufor_file"]).is_file()
    stage5 = next(m for m in ev["pipeline_modules"] if m["stage"] == 5)
    assert stage5["status"] == "SUSPICIOUS" and "unvalidated, not in verdict" in stage5["summary"]


def test_in_verdict_a_flagged_region_raises_the_probability(tmp_path, monkeypatch):
    result = _run(tmp_path, monkeypatch, score=0.9, in_verdict=True)
    assert result.verdict is Verdict.MANIPULATED
    assert result.evidence["threat_code"] == "SPLICING_TAMPERING"


def test_low_score_is_not_flagged(tmp_path, monkeypatch):
    result = _run(tmp_path, monkeypatch, score=0.2, in_verdict=True)
    assert not result.evidence["trufor"]["flagged"]
    assert result.verdict is Verdict.AUTHENTIC
