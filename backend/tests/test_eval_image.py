"""scripts/eval_image.py: end-to-end image metrics, the not-run record and the T2 freeze gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import eval_image as ei  # noqa: E402
from ml.evaluation.stats import wilson_interval  # noqa: E402


def _record(i: int, label: int, generator: str, verdict: str, p: float, condition: str = "original") -> dict:
    return {"image_id": f"i{i}", "label": label, "generator": generator, "source": "test", "condition": condition,
            "group": f"i{i}", "fused": p, "detectors": {"a": p, "b": 1 - p if label else p},
            "end_to_end": {"verdict": verdict, "final_probability": p}}


def _records() -> list[dict]:
    real = [_record(i, 0, "real", "AUTHENTIC", 0.1) for i in range(8)]
    real += [_record(8, 0, "real", "INCONCLUSIVE", 0.5), _record(9, 0, "real", "MANIPULATED", 0.7)]
    ai = [_record(10 + i, 1, "sdxl_1.0", "MANIPULATED", 0.9) for i in range(6)]
    ai += [_record(16, 1, "flux1_dev", "MANIPULATED", 0.8), _record(17, 1, "flux1_dev", "AUTHENTIC", 0.2),
           _record(18, 1, "flux1_dev", "INCONCLUSIVE", 0.55), _record(19, 1, "flux1_dev", "MANIPULATED", 0.95)]
    # A transformed copy is not an original and must not be counted.
    return real + ai + [_record(99, 0, "real", "MANIPULATED", 0.99, condition="jpeg50")]


def test_metrics_on_originals_only():
    metrics = ei.image_eval_metrics(_records(), n_resamples=50)
    assert (metrics["n_images"], metrics["n_real"], metrics["n_ai"]) == (20, 10, 10)
    fpr = metrics["false_positive_rate_real"]
    assert (fpr["k"], fpr["n"]) == (1, 10) and fpr["ci95"] == list(wilson_interval(1, 10))
    assert metrics["inconclusive_rate_real"]["k"] == 1
    assert metrics["recall_per_generator"]["sdxl_1.0"]["rate"] == 1.0
    assert metrics["recall_per_generator"]["flux1_dev"]["k"] == 2
    assert metrics["confusion_matrix"]["counts"] == [[8, 1, 1], [1, 1, 8]]
    assert 0.5 < metrics["auc_final_probability"]["auc"] <= 1.0
    assert "fused" in metrics["scene_detectors"]["columns"]


def test_summarise_without_scores_reports_not_run(tmp_path):
    payload = ei.summarise(tmp_path / "missing.jsonl", results_file=tmp_path / "image_eval.json",
                           roc_path=tmp_path / "roc.png", confusion_path=tmp_path / "cm.png")
    assert payload["status"] == "not_run" and "H560" in payload["reason"]
    assert "auc_final_probability" not in payload
    assert not (tmp_path / "roc.png").exists()


def test_summarise_with_scores_writes_metrics_and_figures(tmp_path):
    scores = tmp_path / "scores.jsonl"
    scores.write_text("".join(json.dumps(r) + "\n" for r in _records()), encoding="utf-8")
    payload = ei.summarise(scores, results_file=tmp_path / "image_eval.json", roc_path=tmp_path / "roc.png",
                           confusion_path=tmp_path / "cm.png")
    assert payload["status"] == "done" and payload["scores_sha256"]
    assert (tmp_path / "roc.png").stat().st_size > 0 and (tmp_path / "cm.png").stat().st_size > 0


def test_t2_needs_the_frozen_image_config():
    assert "frozen_image_config.json" in ei.t2_gate(Path("paper/manifests/t2.csv"), frozen_tracked=False)
    assert ei.t2_gate(Path("paper/manifests/t2.csv"), frozen_tracked=True) is None
    assert ei.t2_gate(Path("paper/manifests/h560.csv"), frozen_tracked=False) is None


def test_scoring_refuses_a_missing_manifest(tmp_path):
    with pytest.raises(SystemExit, match="H560"):
        ei.main(["score", "--manifest", str(tmp_path / "h560.csv"), "--image-root", str(tmp_path)])
