#!/usr/bin/env python3
"""Copy a small labelled ASVspoof 2019 LA eval sample for the audio regression test.

``backend/tests/test_audio_regression.py`` scores these clips with the served
model and fails if their AUC moves more than 0.05 from the LA eval AUC in
``results/audio_eval.json``. The clips are a fixed, seeded sample of the eval
partition: bona fide at random, spoofed spread over attacks A07-A19 in turn.
Using eval clips here is a regression check, not a selection: nothing is
chosen or tuned on them.

Audio is not committed (data rule): the clips go to a folder outside the
repository, with ``labels.csv`` (file, label 0 = bona fide / 1 = spoof,
utt_id, attack_id, sha256) and ``selection.json``.

Usage (PowerShell)::

    $env:DEEPSENTINEL_DATA = "C:\\deepsentinel_data"
    python scripts/export_audio_regression_set.py --output C:\\deepsentinel_data\\audio_regression
    $env:AUDIO_REGRESSION_DIR = "C:\\deepsentinel_data\\audio_regression"
    cd backend; python -m pytest tests/test_audio_regression.py -q
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def choose(rows: list[dict], n_per_class: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    bona = sorted((r for r in rows if r["label"] == 0), key=lambda r: r["utt_id"])
    spoof = sorted((r for r in rows if r["label"] == 1), key=lambda r: r["utt_id"])
    chosen = rng.sample(bona, n_per_class)
    by_attack: dict[str, list[dict]] = {}
    for row in spoof:
        by_attack.setdefault(row["attack_id"], []).append(row)
    attacks = sorted(by_attack)
    for i in range(n_per_class):
        pool = by_attack[attacks[i % len(attacks)]]
        chosen.append(pool.pop(rng.randrange(len(pool))))
    return chosen


def main() -> None:
    from ml.preprocessing.build_asvspoof2019_la import default_la_root, read_manifest
    from ml.provenance import sha256_file

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--n-per-class", type=int, default=10)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--manifest", type=Path, default=REPO_ROOT / "data/processed/asvspoof2019_la/manifest.csv")
    parser.add_argument("--asvspoof-root", type=Path, default=default_la_root())
    args = parser.parse_args()
    if args.asvspoof_root is None:
        raise SystemExit("Set DEEPSENTINEL_DATA or pass --asvspoof-root.")
    if args.output.resolve().is_relative_to(REPO_ROOT):
        raise SystemExit("Write the clips outside the repository: audio is never committed.")

    chosen = choose(read_manifest(args.manifest, ("eval",)), args.n_per_class, args.seed)
    args.output.mkdir(parents=True, exist_ok=True)
    with open(args.output / "labels.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["file", "label", "utt_id", "attack_id", "sha256"])
        for row in chosen:
            source = args.asvspoof_root / row["relative_path"]
            target = args.output / source.name
            shutil.copyfile(source, target)
            writer.writerow([target.name, row["label"], row["utt_id"], row["attack_id"],
                             hashlib.sha256(target.read_bytes()).hexdigest()])
    (args.output / "selection.json").write_text(json.dumps({
        "source": "ASVspoof 2019 LA eval (official CM protocol)",
        "seed": args.seed,
        "n_per_class": args.n_per_class,
        "manifest_sha256": sha256_file(args.manifest),
        "rule": "bona fide at random; spoofed one per attack in turn (A07-A19), at random within the attack",
    }, indent=2), encoding="utf-8")
    print(f"Wrote {len(chosen)} clips and labels.csv to {args.output}")


if __name__ == "__main__":
    main()
