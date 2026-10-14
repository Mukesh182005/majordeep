#!/usr/bin/env python3
"""Choose the ASVspoof front end on dev and freeze the checkpoints for eval.

Rule (fixed before any eval scoring): the front end with the lower pooled dev
EER at seed 0 is selected; seeds 0, 1 and 2 of that front end are the final
models, each with its own dev-selected epoch. Nothing here reads eval data.

Step 1, after ``logmel`` and ``lfcc`` have been trained with seed 0::

    python ml/evaluation/select_asvspoof_frontend.py

prints the comparison and the commands for seeds 1 and 2.

Step 2, after those runs::

    python ml/evaluation/select_asvspoof_frontend.py --write

writes ``paper/config/audio_model_selection.json``. Commit that file on its own
before scoring the eval split.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.common import REPO_ROOT  # noqa: E402

DEV_RUNS = REPO_ROOT / "paper_results/audio_asvspoof2019la/dev_runs"
SELECTION_FILE = REPO_ROOT / "paper/config/audio_model_selection.json"
FRONTENDS = ("logmel", "lfcc")
SEEDS = (0, 1, 2)
RULE = "lower pooled dev EER at seed 0 selects the front end; seeds 0-2 of it are the final models"


def run_record(frontend: str, seed: int) -> dict | None:
    path = DEV_RUNS / f"audio_lcnn_asvspoof_{frontend}_seed{seed}" / "run_config.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def choose_frontend(dev_eer: dict[str, float]) -> str:
    """Lower dev EER wins; an exact tie keeps the serving front end (logmel)."""
    return min(FRONTENDS, key=lambda f: (dev_eer[f], f != "logmel"))


def main() -> int:
    from ml.provenance import collect_provenance

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true", help="write the selection file")
    args = parser.parse_args()

    seed0 = {f: run_record(f, 0) for f in FRONTENDS}
    missing = [f for f, record in seed0.items() if record is None]
    if missing:
        print(f"Missing seed-0 runs for: {', '.join(missing)}. Train them first, e.g.")
        for frontend in missing:
            print(f"  python ml/training/train_asvspoof.py --features {frontend} --seed 0")
        return 1

    dev_eer = {f: float(seed0[f]["dev_eer"]) for f in FRONTENDS}
    chosen = choose_frontend(dev_eer)
    for frontend in FRONTENDS:
        print(f"{frontend:7s} seed 0: dev EER {dev_eer[frontend] * 100:.3f}% (epoch {seed0[frontend]['best_epoch']})")
    print(f"Selected front end: {chosen}  [{RULE}]")

    records = {seed: run_record(chosen, seed) for seed in SEEDS}
    pending = [seed for seed, record in records.items() if record is None]
    if pending:
        print("Train the remaining seeds, then rerun with --write:")
        for seed in pending:
            print(f"  python ml/training/train_asvspoof.py --features {chosen} --seed {seed}")
        return 0 if not args.write else 1

    selection = {
        "rule": RULE,
        "dev_eer_seed0": dev_eer,
        "selected_frontend": chosen,
        "selected_checkpoints": [
            {
                "checkpoint": records[seed]["checkpoint"],
                "sha256": records[seed]["checkpoint_sha256"],
                "seed": seed,
                "best_epoch": records[seed]["best_epoch"],
                "dev_eer": records[seed]["dev_eer"],
                "dev_min_tdcf": records[seed]["dev_min_tdcf"],
            }
            for seed in SEEDS
        ],
        "decided_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "provenance": collect_provenance(),
        "note": "Chosen on the dev split only. Commit this file before scoring the eval split.",
    }
    for entry in selection["selected_checkpoints"]:
        print(f"  seed {entry['seed']}: epoch {entry['best_epoch']}, dev EER {entry['dev_eer'] * 100:.3f}%")
    if args.write:
        SELECTION_FILE.parent.mkdir(parents=True, exist_ok=True)
        SELECTION_FILE.write_text(json.dumps(selection, indent=2, default=str), encoding="utf-8")
        print(f"Wrote {SELECTION_FILE.relative_to(REPO_ROOT)}. Commit it, then score eval once per seed:")
        for entry in selection["selected_checkpoints"]:
            print(f"  python ml/evaluation/eval_asvspoof.py --checkpoint {entry['checkpoint']} "
                  "--split eval --confirm-final-eval")
    else:
        print("Rerun with --write to record this selection.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
