"""scripts/eval_pipeline.py: the stratified sample, the eval gate, resumable scoring and the summary."""

from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import eval_pipeline as ep  # noqa: E402
from ml.evaluation.stats import wilson_interval  # noqa: E402


def _manifest() -> list[dict]:
    rows = []
    for split, attacks in (("eval", ("A07", "A08", "A09")), ("dev", ("A01",))):
        prefix = "E" if split == "eval" else "D"
        rows += [{"utt_id": f"{prefix}_b{i:03d}", "split": split, "label": 0, "attack_id": "-",
                  "relative_path": f"{split}/b{i:03d}.flac"} for i in range(40)]
        for attack in attacks:
            rows += [{"utt_id": f"{prefix}_{attack}_{i:03d}", "split": split, "label": 1, "attack_id": attack,
                      "relative_path": f"{split}/{attack}_{i:03d}.flac"} for i in range(15)]
    return rows


def test_sample_is_stratified_seeded_and_independent_of_row_order():
    rows = _manifest()
    sample = ep.stratified_sample(rows, "eval", n_bonafide=10, n_per_attack=4, seed=0)
    assert len(sample) == 10 + 3 * 4
    assert all(r["split"] == "eval" for r in sample)
    assert sum(r["label"] == 0 for r in sample) == 10
    assert {a: sum(r["attack_id"] == a for r in sample) for a in ("A07", "A08", "A09")} == {"A07": 4, "A08": 4, "A09": 4}
    assert len({r["utt_id"] for r in sample}) == len(sample)

    shuffled = rows[:]
    random.Random(1).shuffle(shuffled)
    again = ep.stratified_sample(shuffled, "eval", 10, 4, seed=0)
    assert [r["utt_id"] for r in again] == [r["utt_id"] for r in sample]
    other = ep.stratified_sample(rows, "eval", 10, 4, seed=1)
    assert [r["utt_id"] for r in other] != [r["utt_id"] for r in sample]


def test_sample_refuses_more_than_exists():
    with pytest.raises(ValueError, match="A07"):
        ep.stratified_sample(_manifest(), "eval", n_bonafide=10, n_per_attack=16, seed=0)
    with pytest.raises(ValueError, match="bona fide"):
        ep.stratified_sample(_manifest(), "eval", n_bonafide=41, n_per_attack=1, seed=0)


def test_eval_gate():
    ok = dict(git_status="", frozen_diff="", frozen_tracked=True)
    assert ep.gate_problems("eval", confirm=True, official=True, **ok) == []
    assert any("--confirm-final-eval" in p for p in ep.gate_problems("eval", False, True, **ok))
    assert any("not clean" in p for p in ep.gate_problems("eval", True, True, **{**ok, "git_status": "?? x.py"}))
    assert any("differs" in p for p in ep.gate_problems("eval", True, True, **{**ok, "frozen_diff": "@@"}))
    assert any("not committed" in p for p in ep.gate_problems("eval", True, True, **{**ok, "frozen_tracked": False}))
    # A timing run on dev into a scratch folder needs neither.
    assert ep.gate_problems("dev", False, False, git_status="?? x.py", frozen_diff="", frozen_tracked=True) == []


def _fake_scorer(task):
    utt_id, _ = task
    if utt_id.endswith("_bad"):
        return {"utt_id": utt_id, "seconds": 0.0, "error": "RuntimeError: decode failed"}
    spoof = "_A" in utt_id
    return {"utt_id": utt_id, "verdict": "flagged" if spoof else "authentic",
            "fake_probability": 0.9 if spoof else 0.1, "lcnn_probability": 0.9 if spoof else 0.1,
            "mean_spoof_logit": 1.0, "n_windows": 1, "weights_status": "trained", "model_version": "t",
            "checkpoint_sha256": "abc", "seconds": 0.01, "error": ""}


def test_scoring_appends_and_resumes_without_duplicates(tmp_path):
    sample = ep.stratified_sample(_manifest(), "eval", 4, 2, seed=0)
    scores = tmp_path / "scores.csv"
    assert ep.run_scoring(sample[:5], tmp_path, scores, workers=0, threads=1, scorer=_fake_scorer) == 5
    todo = [r for r in sample if r["utt_id"] not in ep.done_ids(scores)]
    assert len(todo) == len(sample) - 5
    ep.run_scoring(todo, tmp_path, scores, workers=0, threads=1, scorer=_fake_scorer)
    rows = ep.read_csv(scores)
    assert sorted(r["utt_id"] for r in rows) == sorted(r["utt_id"] for r in sample)
    assert list(rows[0]) == ep.COLUMNS
    assert {r["label"] for r in rows} == {"0", "1"}


def test_verdict_rates_use_wilson_and_count_errors_apart():
    rows = ([{"utt_id": f"b{i}", "label": 0, "attack_id": "-", "verdict": "authentic", "fake_probability": 0.1,
              "error": ""} for i in range(18)]
            + [{"utt_id": "b18", "label": 0, "attack_id": "-", "verdict": "inconclusive", "fake_probability": 0.5,
                "error": ""},
               {"utt_id": "b19", "label": 0, "attack_id": "-", "verdict": "", "fake_probability": "",
                "error": "RuntimeError"}]
            + [{"utt_id": f"s{i}", "label": 1, "attack_id": "A07" if i < 5 else "A08",
                "verdict": "flagged" if i != 9 else "authentic", "fake_probability": 0.9 if i != 9 else 0.2,
                "error": ""} for i in range(10)])
    summary = ep.verdict_rates(rows, n_resamples=50)
    bona = summary["classes"]["bonafide"]
    assert (bona["n"], bona["errors"]) == (20, 1)
    assert (bona["authentic"]["k"], bona["authentic"]["n"]) == (18, 19)
    assert bona["authentic"]["ci95"] == list(wilson_interval(18, 19))
    assert summary["per_attack"]["A08"]["authentic"]["k"] == 1
    assert summary["per_attack"]["A07"]["flagged"]["rate"] == 1.0
    assert 0.9 < summary["auc_fake_probability"]["auc"] <= 1.0


def _write(path: Path, rows: list[dict], columns: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _saved_run(out: Path, complete: bool = True) -> None:
    out.mkdir(parents=True, exist_ok=True)
    sample = ep.stratified_sample(_manifest(), "eval", 6, 3, seed=0)
    ep.write_sample(out / "sample.csv", sample)
    ep.run_scoring(sample if complete else sample[:4], out, out / "scores.csv", workers=0, threads=1,
                   scorer=_fake_scorer)
    config = {"rule": {"authentic_below": 0.417, "flagged_at_or_above": 0.577},
              "sample": {"split": "eval", "seed": 0, "size": len(sample)}, "inference": "float32"}
    (out / "config.json").write_text(json.dumps(config), encoding="utf-8")


def test_summarise_writes_from_saved_rows_and_owns_one_index_section(tmp_path):
    out = tmp_path / "audio_end_to_end_eval"
    _saved_run(out)
    index = tmp_path / "INDEX.md"
    index.write_text("| a | b | c | d | e |\n<!-- begin:other -->\n| keep | 1 | `f` | `k` | 2 |\n<!-- end:other -->\n",
                     encoding="utf-8")
    results, figure = tmp_path / "pipeline_eval.json", tmp_path / "fig.png"
    payload = ep.summarise(out, results_file=results, figure=figure, index=index)

    la = payload["audio"]["asvspoof2019_la_eval"]
    assert la["status"] == "done"
    assert la["classes"]["bonafide"]["authentic"]["rate"] == 1.0
    assert payload["audio"]["in_the_wild"]["status"] == "not_run"
    assert {v["status"] for v in payload["video"].values()} == {"not_run"}
    assert json.loads(results.read_text(encoding="utf-8"))["audio"]["asvspoof2019_la_eval"]["status"] == "done"
    assert figure.stat().st_size > 0
    rates = json.loads((out / "verdict_rates.json").read_text(encoding="utf-8"))
    assert rates["scores_sha256"] and rates["checkpoint_sha256"] == ["abc"]
    text = index.read_text(encoding="utf-8")
    assert "| keep | 1 | `f` | `k` | 2 |" in text
    assert "<!-- begin:audio_end_to_end_eval -->" in text and "A07: flagged" in text


def test_summarise_refuses_an_unfinished_run(tmp_path):
    out = tmp_path / "run"
    _saved_run(out, complete=False)
    with pytest.raises(SystemExit, match="not scored yet"):
        ep.summarise(out, results_file=tmp_path / "r.json", figure=tmp_path / "f.png", index=tmp_path / "I.md")


def test_a_completed_run_is_not_scored_again(tmp_path, monkeypatch):
    monkeypatch.setattr(ep, "_git", lambda *args: "")
    manifest = tmp_path / "manifest.csv"
    _write(manifest, _manifest(), ["utt_id", "relative_path", "split", "label", "attack_id"])
    ep.append_log(tmp_path / "eval_log.csv", "complete", "dev", "abc", 10)
    with pytest.raises(SystemExit, match="already holds a completed run"):
        ep.main(["audio-la", "--split", "dev", "--manifest", str(manifest), "--output-dir", str(tmp_path),
                 "--asvspoof-root", str(tmp_path)])


def test_tf32_comparison_reads_the_stored_scores_side_by_side(tmp_path):
    phase2 = tmp_path / "eval_scores.csv"
    _write(phase2, [{"utt_id": "a", "attack_id": "-", "label": 0, "score": 3.0},
                    {"utt_id": "b", "attack_id": "A07", "label": 1, "score": -2.0}],
           ["utt_id", "attack_id", "label", "score"])
    rows = [{"utt_id": "a", "label": "0", "mean_spoof_logit": "-2.95", "error": ""},
            {"utt_id": "b", "label": "1", "mean_spoof_logit": "2.0", "error": ""}]
    result = ep.tf32_comparison(rows, phase2)
    assert result["n"] == 2 and abs(result["max_abs_mean_logit_difference"] - 0.05) < 1e-9
    assert result["auc_float32_mean_logit"] == result["auc_tf32_mean_logit"] == 1.0
    assert ep.tf32_comparison(rows, tmp_path / "missing.csv") is None
