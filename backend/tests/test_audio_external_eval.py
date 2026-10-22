"""P2: In-the-Wild manifest and scoring, and the results/audio_eval.json summary.

Runs on a fake corpus and random-weight LCNNs: these check the plumbing
(labels, guards, resume, metric consistency), not any model's accuracy.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
SR = 16000


@pytest.fixture(autouse=True)
def _restore_tf32_flags():
    """eval_in_the_wild switches TF32 off process-wide; leave other tests as they were."""
    import torch

    saved = (torch.backends.cudnn.allow_tf32, torch.backends.cuda.matmul.allow_tf32)
    yield
    torch.backends.cudnn.allow_tf32, torch.backends.cuda.matmul.allow_tf32 = saved


def _write_wav(path: Path, seconds: float, seed: int) -> None:
    import soundfile as sf

    rng = np.random.default_rng(seed)
    sf.write(str(path), (0.05 * rng.standard_normal(int(seconds * SR))).astype(np.float32), SR, subtype="PCM_16")


@pytest.fixture()
def fake_itw(tmp_path):
    root = tmp_path / "release_in_the_wild"
    root.mkdir()
    rows = [("0.wav", "Speaker A", "spoof"), ("1.wav", "Speaker A", "bona-fide"), ("2.wav", "Speaker B", "spoof"),
            ("3.wav", "Speaker B", "bona-fide"), ("4.wav", "Speaker C", "bona-fide"), ("5.wav", "Speaker C", "spoof")]
    with open(root / "meta.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["file", "speaker", "label"])
        writer.writerows(rows)
    for i, (name, _, _) in enumerate(rows):
        _write_wav(root / name, 1.5 + 2.0 * (i % 3), seed=i)  # 1.5 s to 5.5 s: one and two windows
    return root


def test_manifest_labels_speakers_and_refusals(fake_itw, tmp_path):
    from ml.preprocessing.build_in_the_wild import build, parse_meta

    summary = build(fake_itw, tmp_path / "manifest.csv", tmp_path / "summary.json")
    assert (summary["n_bonafide"], summary["n_spoof"], summary["n_speakers"]) == (3, 3, 3)
    assert summary["n_speakers_with_both_classes"] == 3
    with open(tmp_path / "manifest.csv", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert {r["utt_id"]: int(r["label"]) for r in rows}["1"] == 0
    assert "Speaker" not in (tmp_path / "summary.json").read_text(encoding="utf-8"), "names stay out of the summary"

    bad = tmp_path / "bad.csv"
    bad.write_text("file,speaker,label\n0.wav,A,fake\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown label"):
        parse_meta(bad)
    (fake_itw / "3.wav").unlink()
    with pytest.raises(SystemExit, match="missing"):
        build(fake_itw, tmp_path / "m2.csv", tmp_path / "s2.json")


def test_builder_needs_the_licence_confirmed(monkeypatch):
    from ml.preprocessing import build_in_the_wild

    monkeypatch.setattr(sys, "argv", ["build_in_the_wild.py"])
    with pytest.raises(SystemExit, match="licence"):
        build_in_the_wild.main()


@pytest.fixture()
def frozen_random_lcnns(tmp_path):
    """Two random-weight LFCC LCNN checkpoints and a selection file freezing them."""
    import torch
    from app.ml.models_arch import build_audio_model

    entries = []
    for seed in (0, 1):
        torch.manual_seed(seed)
        path = tmp_path / f"lcnn_test_seed{seed}.pt"
        torch.save({"state_dict": build_audio_model().state_dict(), "frontend": "lfcc"}, path)
        entries.append({"checkpoint": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "seed": seed})
    selection = tmp_path / "selection.json"
    selection.write_text(json.dumps({"selected_checkpoints": entries}), encoding="utf-8")
    return selection, entries


def _run_itw(fake_itw, tmp_path, selection, *extra):
    from ml.evaluation.eval_in_the_wild import main
    from ml.preprocessing.build_in_the_wild import build

    manifest = tmp_path / "manifest.csv"
    if not manifest.is_file():
        build(fake_itw, manifest, tmp_path / "summary.json")
    return main(["--root", str(fake_itw), "--manifest", str(manifest), "--output-dir", str(tmp_path / "out"),
                 "--selection", str(selection), "--device", "cpu", "--log-every", "2", *extra])


def test_itw_scoring_metrics_resume_and_guards(fake_itw, tmp_path, frozen_random_lcnns):
    import torch
    from app.ml.asvspoof_frontend import utterance_lfcc
    from app.ml.models_arch import build_audio_model
    from app.ml.preprocessing import load_audio

    selection, entries = frozen_random_lcnns
    with pytest.raises(SystemExit, match="confirm-final-eval"):
        _run_itw(fake_itw, tmp_path, selection)

    metrics = _run_itw(fake_itw, tmp_path, selection, "--confirm-final-eval")
    assert set(metrics["per_checkpoint"]) == {"lcnn_test_seed0", "lcnn_test_seed1"}
    for entry in metrics["per_checkpoint"].values():
        assert (entry["n_bonafide"], entry["n_spoof"]) == (3, 3)
        assert 0.0 <= entry["eer"] <= 1.0 and 0.0 <= entry["auc_bonafide_vs_spoof"] <= 1.0
    assert metrics["summary"]["eer_percent"]["n"] == 2

    # The stored score is the serving feature path through the frozen weights.
    out = tmp_path / "out" / "lcnn_test_seed0_scores.csv"
    with open(out, newline="", encoding="utf-8") as handle:
        first = next(csv.DictReader(handle))
    model = build_audio_model()
    model.load_state_dict(torch.load(entries[0]["checkpoint"], weights_only=True)["state_dict"])
    waveform, _ = load_audio(fake_itw / f"{first['utt_id']}.wav", SR)
    with torch.no_grad():
        expected = -float(model.float().eval()(torch.from_numpy(utterance_lfcc(waveform)).unsqueeze(1)).mean())
    assert abs(float(first["score"]) - expected) < 1e-5

    # Resume: a second run scores nothing new and duplicates nothing.
    _run_itw(fake_itw, tmp_path, selection, "--confirm-final-eval")
    with open(out, newline="", encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == 6
    with open(tmp_path / "out" / "eval_log.csv", newline="", encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == 2


def test_itw_refuses_checkpoints_that_are_not_frozen(fake_itw, tmp_path, frozen_random_lcnns):
    selection, entries = frozen_random_lcnns
    data = json.loads(selection.read_text(encoding="utf-8"))
    data["selected_checkpoints"][0]["sha256"] = "0" * 64
    selection.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SystemExit, match="not the frozen checkpoint"):
        _run_itw(fake_itw, tmp_path, selection, "--confirm-final-eval")


def test_itw_smoke_runs_stay_out_of_paper_results(fake_itw, tmp_path, frozen_random_lcnns):
    from ml.evaluation.eval_in_the_wild import main

    selection, _ = frozen_random_lcnns
    with pytest.raises(SystemExit, match="outside paper_results"):
        main(["--root", str(fake_itw), "--selection", str(selection), "--confirm-final-eval", "--limit", "2",
              "--output-dir", str(REPO / "paper_results" / "audio_in_the_wild")])


def test_audio_eval_summary_refuses_inconsistent_files(tmp_path):
    from ml.evaluation.eval_audio import la_eval, score_metrics

    eval_dir = tmp_path / "eval"
    eval_dir.mkdir()
    rng = np.random.default_rng(0)
    labels = np.array([0] * 20 + [1] * 40)
    scores = np.where(labels == 0, 2.0, -2.0) + rng.standard_normal(labels.size)
    with open(eval_dir / "m_eval_scores.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["utt_id", "attack_id", "label", "score"])
        writer.writerows([f"u{i}", "A07" if y else "-", int(y), f"{s:.6f}"] for i, (y, s) in enumerate(zip(labels, scores, strict=False)))
    stored = {**score_metrics(labels, np.round(scores, 6)), "min_tdcf": 0.1, "per_attack": {}}
    (eval_dir / "m_eval_metrics.json").write_text(json.dumps(stored), encoding="utf-8")

    with pytest.MonkeyPatch.context() as mp:
        import ml.evaluation.eval_audio as module

        mp.setattr(module, "REPO_ROOT", tmp_path)
        result = la_eval("m", tmp_path)
        assert result["eer"] == stored["eer"] and result["min_tdcf"] == 0.1
        stored["eer"] += 0.01
        (eval_dir / "m_eval_metrics.json").write_text(json.dumps(stored), encoding="utf-8")
        with pytest.raises(SystemExit, match="differs"):
            la_eval("m", tmp_path)


def test_committed_audio_eval_matches_the_saved_eval_scores():
    """results/audio_eval.json was generated from the committed score files, not typed in."""
    report_path = REPO / "results" / "audio_eval.json"
    if not report_path.is_file():
        pytest.skip("results/audio_eval.json not generated")
    from ml.evaluation.eval_audio import read_scores, score_metrics

    report = json.loads(report_path.read_text(encoding="utf-8"))["asvspoof2019_la_eval"]
    scores_file = REPO / report["sources"]["scores"]["file"]
    assert hashlib.sha256(scores_file.read_bytes()).hexdigest() == report["sources"]["scores"]["sha256"]
    recomputed = score_metrics(*read_scores(scores_file))
    assert abs(recomputed["eer"] - report["eer"]) < 1e-12
    assert abs(recomputed["auc_bonafide_vs_spoof"] - report["auc_bonafide_vs_spoof"]) < 1e-12
