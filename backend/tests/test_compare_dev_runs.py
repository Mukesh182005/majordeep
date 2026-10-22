"""ml/evaluation/compare_dev_runs.py: identical runs compare equal, any difference is caught."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.evaluation.compare_dev_runs import compare_runs, compare_weights, main  # noqa: E402

SCORES = "utt_id,label,score\nLA_D_1,0,1.5\nLA_D_2,1,-2.0\n"


def _run(folder: Path, eer: float = 0.0019, scores: str = SCORES, best_epoch: int = 20) -> Path:
    folder.mkdir(parents=True)
    metrics = {"eer": eer, "eer_threshold": -2.1, "min_tdcf": 0.004, "auc_bonafide_vs_spoof": 0.99, "n_bonafide": 1, "n_spoof": 1}
    (folder / "dev_metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    (folder / "run_config.json").write_text(json.dumps({"best_epoch": best_epoch}), encoding="utf-8")
    (folder / "dev_scores.csv").write_text(scores, encoding="utf-8")
    return folder


def test_identical_runs_compare_equal(tmp_path):
    result = compare_runs(_run(tmp_path / "a"), _run(tmp_path / "b"))
    assert result["dev_metrics_all_equal"] and result["best_epoch"]["equal"]
    assert result["dev_scores"]["byte_identical"]


def test_a_different_metric_score_or_epoch_is_caught(tmp_path):
    other = _run(tmp_path / "b", eer=0.002, scores=SCORES.replace("-2.0", "-2.1"), best_epoch=19)
    result = compare_runs(_run(tmp_path / "a"), other)
    assert not result["dev_metrics_all_equal"] and not result["dev_metrics"]["eer"]["equal"]
    assert result["dev_metrics"]["min_tdcf"]["equal"]
    assert not result["dev_scores"]["byte_identical"] and not result["best_epoch"]["equal"]


def test_weights_are_compared_tensor_by_tensor(tmp_path):
    torch = pytest.importorskip("torch")
    weights = {"conv.weight": torch.arange(6.0).reshape(2, 3), "bn.num_batches_tracked": torch.tensor(5)}
    torch.save({"state_dict": weights, "epoch": 20}, tmp_path / "a.pt")
    # Different metadata, same tensors: still bit-identical weights.
    torch.save({"state_dict": {k: v.clone() for k, v in weights.items()}, "epoch": 20, "note": "re-run"}, tmp_path / "b.pt")
    same = compare_weights(tmp_path / "a.pt", tmp_path / "b.pt")
    assert same["bit_identical"] and same["max_abs_difference"] == 0.0 and same["n_tensors"] == 2

    torch.save({"state_dict": dict(weights, **{"conv.weight": weights["conv.weight"] + 1e-6})}, tmp_path / "c.pt")
    changed = compare_weights(tmp_path / "a.pt", tmp_path / "c.pt")
    assert not changed["bit_identical"] and changed["tensors_differing"] == ["conv.weight"]
    assert 0.0 < changed["max_abs_difference"] < 1e-5


def test_main_writes_comparison_json_with_provenance(tmp_path):
    recorded, rerun = _run(tmp_path / "a"), _run(tmp_path / "b")
    main(["--recorded", str(recorded), "--rerun", str(rerun), "--no-index"])
    written = json.loads((rerun / "comparison.json").read_text(encoding="utf-8"))
    assert written["dev_metrics_all_equal"] and "weights" not in written
    assert "git_commit" in written["provenance"] and written["provenance"]["command_line"][1:3] == ["--recorded", str(recorded)]


def test_main_rewrites_only_its_own_index_section(tmp_path):
    index = tmp_path / "INDEX.md"
    index.write_text("# Index\n<!-- begin:other -->\n| kept | 1 | `f` | `k` | 2 |\n<!-- end:other -->\n", encoding="utf-8")
    recorded, rerun = _run(tmp_path / "a"), _run(tmp_path / "b", best_epoch=19)
    for _ in range(2):  # a second run replaces the section instead of appending to it
        main(["--recorded", str(recorded), "--rerun", str(rerun), "--index", str(index)])
    text = index.read_text(encoding="utf-8")
    assert "| kept | 1 |" in text and text.count("<!-- begin:audio_lcnn_repro -->") == 1
    assert "best epoch equal | no (20 / 19)" in text and "byte-identical | yes" in text
