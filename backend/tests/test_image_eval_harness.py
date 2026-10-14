"""Image evaluation harness: manifest validation, resume, error handling, metrics."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.evaluation.eval_image_detectors import (  # noqa: E402
    MANIFEST_COLUMNS,
    group_split_problems,
    read_image_manifest,
    run,
)

HEADER = ",".join(MANIFEST_COLUMNS)


def _manifest(tmp_path: Path, lines: list[str]) -> Path:
    path = tmp_path / "manifest.csv"
    path.write_text("\n".join([HEADER, *lines]) + "\n", encoding="utf-8")
    return path


class TestManifest:
    def test_valid_manifest_and_default_group(self, tmp_path):
        rows = read_image_manifest(_manifest(tmp_path, [
            "r1,real/a.jpg,0,real,coco,original,",
            "f1,ai/b.png,1,sdxl,synthbuster,original,f1",
            "f1_j75,ai/b_j75.jpg,1,sdxl,synthbuster,jpeg75,f1",
        ]))
        assert [r["label"] for r in rows] == [0, 1, 1]
        assert rows[0]["group"] == "r1"  # an original is its own group

    @pytest.mark.parametrize("line", [
        "r1,real/a.jpg,0,sdxl,coco,original,r1",  # real image with a generator
        "f1,ai/b.png,1,real,x,original,f1",  # AI image without one
        "f1,ai/b.png,2,sdxl,x,original,f1",  # bad label
        "f1,/abs/b.png,1,sdxl,x,original,f1",  # absolute path
        "f1,../b.png,1,sdxl,x,original,f1",  # escapes the root
    ])
    def test_rejects_bad_rows(self, tmp_path, line):
        with pytest.raises(ValueError):
            read_image_manifest(_manifest(tmp_path, [line]))

    def test_rejects_duplicate_ids(self, tmp_path):
        with pytest.raises(ValueError):
            read_image_manifest(_manifest(tmp_path, ["a,x.jpg,0,real,s,original,a", "a,y.jpg,0,real,s,original,a"]))

    def test_group_split_check(self):
        rows = [{"group": "g1", "split": "train"}, {"group": "g1", "split": "test"}, {"group": "g2", "split": "test"}]
        assert group_split_problems(rows) == ["group g1 in splits ['test', 'train']"]


def _images(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "images"
    (root / "real").mkdir(parents=True)
    (root / "ai").mkdir()
    rng = np.random.default_rng(0)
    for name in ("real/a.png", "real/b.png", "ai/c.png", "ai/d.png"):
        Image.fromarray(rng.integers(0, 255, (64, 64, 3), dtype=np.uint8)).save(root / name)
    framed = np.zeros((200, 200, 3), dtype=np.uint8)  # black viewer bars around a noisy picture
    framed[30:170, 20:180] = rng.integers(40, 255, (140, 160, 3), dtype=np.uint8)
    Image.fromarray(framed).save(root / "ai/framed.png")
    manifest = _manifest(tmp_path, [
        "a,real/a.png,0,real,cam,original,a",
        "b,real/b.png,0,real,cam,original,b",
        "c,ai/c.png,1,sdxl,bench,original,c",
        "d,ai/d.png,1,flux,bench,original,d",
        "e,ai/framed.png,1,flux,bench,screenshot,d",
        "missing,ai/none.png,1,flux,bench,original,missing",
    ])
    return root, manifest


def _fake_scene(image):
    value = float(np.asarray(image, dtype=np.float64).mean() / 255.0)
    return {"scene_ai_prob": value, "model_scores": {"detA": value, "detB": 1 - value}}


def test_run_scores_resumes_and_logs_errors(tmp_path):
    root, manifest = _images(tmp_path)
    rows = read_image_manifest(manifest)
    out = tmp_path / "scores.jsonl"
    counts = run(rows, root, out, _fake_scene, {"const": lambda path: 0.25})
    assert counts == {"already_done": 0, "scored": 5, "failed": 1}
    records = [json.loads(line) for line in out.read_text().splitlines()]
    framed = next(r for r in records if r["image_id"] == "e")
    assert framed["border_cropped"] and "fused_uncropped" in framed
    assert records[0]["extra"]["const"] == 0.25 and len(records[0]["sha256"]) == 64
    errors = (tmp_path / "scores.errors.jsonl").read_text().splitlines()
    assert json.loads(errors[0])["image_id"] == "missing"

    again = run(rows, root, out, _fake_scene)
    assert again == {"already_done": 5, "scored": 0, "failed": 1}  # only the bad file is retried
    assert len(out.read_text().splitlines()) == 5


def test_metrics_from_scores():
    from paper.analysis import image_metrics

    rng = np.random.default_rng(5)
    records = []
    for i in range(120):
        label = int(i >= 60)
        fused = float(np.clip(rng.normal(0.25 + 0.5 * label, 0.15), 0, 1))
        records.append({
            "image_id": f"i{i}", "label": label, "generator": "real" if label == 0 else ("sdxl" if i % 2 else "flux"),
            "condition": "original", "fused": fused,
            "detectors": {"A": fused, "B": float(rng.uniform())},
            "end_to_end": {"verdict": "MANIPULATED" if fused >= 0.58 else ("AUTHENTIC" if fused <= 0.42 else "INCONCLUSIVE"),
                           "verdict_basis": "detector_score"},
        })
    metrics = image_metrics.condition_metrics(records, n_resamples=200)
    assert metrics["n_real"] == 60 and metrics["n_ai"] == 60
    assert set(metrics["columns"]) == {"fused", "detector:A", "detector:B"}
    assert metrics["delong_vs_ours"]["detector:A"]["p_value"] == 1.0  # same scores as ours
    assert metrics["delong_vs_ours"]["detector:B"]["p_value"] < 0.001
    assert set(metrics["per_generator"]) == {"sdxl", "flux"}
    verdicts = metrics["end_to_end_verdicts"]["real"]
    assert sum(verdicts[v]["k"] for v in ("AUTHENTIC", "INCONCLUSIVE", "MANIPULATED")) == 60


def test_index_section_is_replaced_not_duplicated(tmp_path):
    from paper.analysis.index_tools import update_index_section

    index = tmp_path / "INDEX.md"
    index.write_text("# Index\n\n| Paper item | Value | File | Key | Phase |\n|---|---|---|---|---|\n", encoding="utf-8")
    update_index_section("demo", [("AUC", "0.900", "f.json", "k", "4")], index)
    update_index_section("demo", [("AUC", "0.910", "f.json", "k", "4")], index)
    text = index.read_text(encoding="utf-8")
    assert text.count("begin:demo") == 1 and "0.910" in text and "0.900" not in text
