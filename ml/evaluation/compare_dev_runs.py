"""Compare a re-run of an ASVspoof LCNN training run with the recorded run.

Reads saved files only and writes ``comparison.json`` into the re-run's folder:
the dev metrics side by side, whether the per-utterance dev score files are
byte-identical and, when both checkpoints are given, whether every weight
tensor is bit-identical. Nothing is scored here and the eval partition is not
read. The ``audio_lcnn_repro`` section of ``paper_results/INDEX.md`` is
rewritten from the result.

    python ml/evaluation/compare_dev_runs.py ^
        --recorded paper_results/audio_asvspoof2019la/dev_runs/audio_lcnn_asvspoof_lfcc_seed2 ^
        --rerun paper_results/audio_asvspoof2019la/repro_runs/lfcc_seed2 ^
        --recorded-checkpoint checkpoints/audio_lcnn_asvspoof_lfcc_seed2.pt ^
        --rerun-checkpoint checkpoints/audio_lcnn_asvspoof_lfcc_seed2_repro.pt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.common import REPO_ROOT, save_json  # noqa: E402
from ml.provenance import collect_provenance, sha256_file  # noqa: E402
from paper.analysis.index_tools import INDEX, update_index_section  # noqa: E402

METRIC_KEYS = ("eer", "eer_threshold", "min_tdcf", "auc_bonafide_vs_spoof", "n_bonafide", "n_spoof")
INDEX_SECTION = "audio_lcnn_repro"


def _rel(path: Path) -> str:
    """Repository-relative path, or the bare name: never a local absolute path."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def compare_runs(recorded: Path, rerun: Path) -> dict:
    """Dev metrics, best epoch and dev score files of two run folders."""
    metrics_a, metrics_b = _read_json(recorded / "dev_metrics.json"), _read_json(rerun / "dev_metrics.json")
    config_a, config_b = _read_json(recorded / "run_config.json"), _read_json(rerun / "run_config.json")
    scores_a, scores_b = sha256_file(recorded / "dev_scores.csv"), sha256_file(rerun / "dev_scores.csv")
    dev_metrics = {
        key: {"recorded": metrics_a.get(key), "rerun": metrics_b.get(key), "equal": metrics_a.get(key) == metrics_b.get(key)}
        for key in METRIC_KEYS
    }
    return {
        "recorded_run": _rel(recorded),
        "rerun": _rel(rerun),
        "best_epoch": {"recorded": config_a.get("best_epoch"), "rerun": config_b.get("best_epoch"),
                       "equal": config_a.get("best_epoch") == config_b.get("best_epoch")},
        "dev_metrics": dev_metrics,
        "dev_metrics_all_equal": all(entry["equal"] for entry in dev_metrics.values()),
        "dev_scores": {"recorded_sha256": scores_a, "rerun_sha256": scores_b, "byte_identical": scores_a == scores_b},
    }


def _state_dict(path: Path) -> dict:
    import torch

    payload = torch.load(path, map_location="cpu", weights_only=True)
    return payload["state_dict"] if isinstance(payload, dict) and "state_dict" in payload else payload


def compare_weights(recorded: Path, rerun: Path) -> dict:
    """Whether every tensor in the two checkpoints is bit-identical."""
    import torch

    tensors_a, tensors_b = _state_dict(recorded), _state_dict(rerun)
    same_names = list(tensors_a) == list(tensors_b)
    differing = [name for name in tensors_a if name in tensors_b and not torch.equal(tensors_a[name], tensors_b[name])]
    max_abs = max(
        (float((tensors_a[n].double() - tensors_b[n].double()).abs().max())
         for n in tensors_a if n in tensors_b and tensors_a[n].shape == tensors_b[n].shape and tensors_a[n].numel()),
        default=0.0,
    )
    return {
        "recorded": {"checkpoint": _rel(recorded), "sha256": sha256_file(recorded)},
        "rerun": {"checkpoint": _rel(rerun), "sha256": sha256_file(rerun)},
        "n_tensors": len(tensors_a),
        "same_tensor_names": same_names,
        "tensors_differing": differing,
        "max_abs_difference": max_abs,
        "bit_identical": same_names and not differing,
    }


def index_rows(result: dict, comparison_file: str) -> list[tuple[str, str, str, str, str]]:
    """INDEX.md rows (paper item, value, file, key, phase), every value from ``result``."""
    run = f"Re-run {Path(result['rerun']).name} vs recorded {Path(result['recorded_run']).name}"
    source = f"`{comparison_file}`"

    def yes(flag: bool) -> str:
        return "yes" if flag else "no"

    epochs = result["best_epoch"]
    rows = [
        (f"{run}: best epoch equal", f"{yes(epochs['equal'])} ({epochs['recorded']} / {epochs['rerun']})",
         source, "`best_epoch.equal`", "3"),
        (f"{run}: dev EER, EER threshold, min t-DCF and AUC equal", yes(result["dev_metrics_all_equal"]),
         source, "`dev_metrics_all_equal`", "3"),
        (f"{run}: per-utterance dev scores byte-identical", yes(result["dev_scores"]["byte_identical"]),
         source, "`dev_scores.byte_identical`", "3"),
    ]
    if "weights" in result:
        rows.append((f"{run}: checkpoint weights bit-identical", yes(result["weights"]["bit_identical"]),
                     source, "`weights.bit_identical`", "3"))
    return rows


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--recorded", type=Path, required=True, help="recorded run folder")
    parser.add_argument("--rerun", type=Path, required=True, help="re-run folder; comparison.json is written here")
    parser.add_argument("--recorded-checkpoint", type=Path, default=None)
    parser.add_argument("--rerun-checkpoint", type=Path, default=None)
    parser.add_argument("--index", type=Path, default=INDEX, help="INDEX.md whose audio_lcnn_repro section is rewritten")
    parser.add_argument("--no-index", action="store_true", help="do not touch INDEX.md")
    args = parser.parse_args(argv)

    result = compare_runs(args.recorded, args.rerun)
    if args.recorded_checkpoint and args.rerun_checkpoint:
        result["weights"] = compare_weights(args.recorded_checkpoint, args.rerun_checkpoint)
    result["provenance"] = collect_provenance(argv=[Path(sys.argv[0]).as_posix(), *(argv if argv is not None else sys.argv[1:])])
    output = args.rerun / "comparison.json"
    save_json(output, result)
    if not args.no_index:
        update_index_section(INDEX_SECTION, index_rows(result, _rel(output)), index=args.index)

    weights = result.get("weights", {}).get("bit_identical")
    print(f"best epoch equal: {result['best_epoch']['equal']} | dev metrics equal: {result['dev_metrics_all_equal']} | "
          f"dev scores byte-identical: {result['dev_scores']['byte_identical']} | weights bit-identical: {weights}")
    return result


if __name__ == "__main__":
    main()
