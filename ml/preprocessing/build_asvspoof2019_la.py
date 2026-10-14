#!/usr/bin/env python3
"""Build the ASVspoof 2019 LA manifest from the official CM protocol files.

The split of every utterance comes from the protocol file it is listed in
(train / dev / eval), never from a random draw, so results are comparable with
published work. ``ml/preprocessing/build_audio_dataset.py`` makes its own
random split and must not be used for this corpus.

Protocol columns (whitespace separated)::

    SPEAKER_ID  UTTERANCE_ID  -  ATTACK_ID|-  bonafide|spoof

Output ``manifest.csv`` columns: utt_id, relative_path, split, label
(1 = spoof, 0 = bona fide), attack_id ("-" for bona fide), speaker_id,
num_samples. ``relative_path`` is relative to the LA root, so the manifest
holds no machine-specific path.

Usage (PowerShell, from the repository root)::

    $env:DEEPSENTINEL_DATA = "C:\\deepsentinel_data"
    python ml/preprocessing/build_asvspoof2019_la.py
    python ml/preprocessing/build_asvspoof2019_la.py --limit-per-split 200 `
        --output data/processed/asvspoof2019_la_smoke
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.common import REPO_ROOT

SPLITS = ("train", "dev", "eval")
PROTOCOL_DIR = "ASVspoof2019_LA_cm_protocols"
PROTOCOL_FILES = {
    "train": "ASVspoof2019.LA.cm.train.trn.txt",
    "dev": "ASVspoof2019.LA.cm.dev.trl.txt",
    "eval": "ASVspoof2019.LA.cm.eval.trl.txt",
}
AUDIO_DIRS = {
    "train": "ASVspoof2019_LA_train",
    "dev": "ASVspoof2019_LA_dev",
    "eval": "ASVspoof2019_LA_eval",
}
# Totals of the official LA protocol; a mismatch means a damaged or partial copy.
EXPECTED_COUNTS = {"train": 25380, "dev": 24844, "eval": 71237}
EXPECTED_ATTACKS = {
    "train": {f"A{i:02d}" for i in range(1, 7)},
    "dev": {f"A{i:02d}" for i in range(1, 7)},
    "eval": {f"A{i:02d}" for i in range(7, 20)},
}
FIELDNAMES = [
    "utt_id",
    "relative_path",
    "split",
    "label",
    "attack_id",
    "speaker_id",
    "num_samples",
]
SAMPLE_RATE = 16000
_ATTACK_RE = re.compile(r"^A\d{2}$")


def default_la_root() -> Path | None:
    data = os.environ.get("DEEPSENTINEL_DATA")
    return Path(data) / "ASVspoof2019" / "LA" if data else None


def parse_protocol(path: Path, split: str) -> list[dict]:
    """Parse one CM protocol file into manifest rows (without num_samples)."""
    if split not in SPLITS:
        raise ValueError(f"Unknown split '{split}'")
    rows: list[dict] = []
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            parts = line.split()
            if not parts:
                continue
            if len(parts) != 5:
                raise ValueError(f"{path.name}:{line_no}: expected 5 columns, got {len(parts)}")
            speaker_id, utt_id, _unused, attack_id, key = parts
            if key == "bonafide":
                if attack_id != "-":
                    raise ValueError(f"{path.name}:{line_no}: bona fide row has attack '{attack_id}'")
                label = 0
            elif key == "spoof":
                if not _ATTACK_RE.match(attack_id):
                    raise ValueError(f"{path.name}:{line_no}: spoof row has attack '{attack_id}'")
                label = 1
            else:
                raise ValueError(f"{path.name}:{line_no}: unknown key '{key}'")
            rows.append(
                {
                    "utt_id": utt_id,
                    "relative_path": f"{AUDIO_DIRS[split]}/flac/{utt_id}.flac",
                    "split": split,
                    "label": label,
                    "attack_id": attack_id,
                    "speaker_id": speaker_id,
                }
            )
    return rows


def split_integrity_problems(rows: list[dict]) -> list[str]:
    """Utterances or speakers that appear in more than one split, or twice."""
    problems: list[str] = []
    seen: dict[str, str] = {}
    for row in rows:
        previous = seen.get(row["utt_id"])
        if previous is not None:
            problems.append(f"{row['utt_id']} listed in both '{previous}' and '{row['split']}'")
        seen[row["utt_id"]] = row["split"]

    # The LA partitions are speaker-disjoint by design.
    speaker_splits: dict[str, set[str]] = {}
    for row in rows:
        speaker_splits.setdefault(row["speaker_id"], set()).add(row["split"])
    for speaker, splits in sorted(speaker_splits.items()):
        if len(splits) > 1:
            problems.append(f"speaker {speaker} appears in splits {sorted(splits)}")
    return problems


def attack_problems(rows: list[dict], expected: dict[str, set[str]] = EXPECTED_ATTACKS) -> list[str]:
    """Splits whose spoof attack ids differ from the official design."""
    problems: list[str] = []
    for split, wanted in expected.items():
        found = {r["attack_id"] for r in rows if r["split"] == split and r["label"] == 1}
        if not found:
            continue  # split not built (e.g. a partial smoke manifest)
        if found != wanted:
            problems.append(
                f"{split}: attacks {sorted(found)} differ from expected {sorted(wanted)}"
            )
    return problems


def summarise(rows: list[dict]) -> dict:
    summary: dict = {"total": len(rows), "splits": {}}
    for split in SPLITS:
        part = [r for r in rows if r["split"] == split]
        if not part:
            continue
        summary["splits"][split] = {
            "utterances": len(part),
            "bonafide": sum(1 for r in part if r["label"] == 0),
            "spoof": sum(1 for r in part if r["label"] == 1),
            "speakers": len({r["speaker_id"] for r in part}),
            "per_attack": dict(sorted(Counter(r["attack_id"] for r in part if r["label"] == 1).items())),
        }
        if all("num_samples" in r for r in part):
            seconds = [int(r["num_samples"]) / SAMPLE_RATE for r in part]
            summary["splits"][split]["duration_seconds"] = {
                "total": round(sum(seconds), 1),
                "min": round(min(seconds), 3),
                "mean": round(sum(seconds) / len(seconds), 3),
                "max": round(max(seconds), 3),
                "longer_than_4s": sum(1 for s in seconds if s > 4.0),
            }
    return summary


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_num_samples(rows: list[dict], la_root: Path) -> list[str]:
    """Read each file's header for its length; returns missing or invalid files."""
    import soundfile as sf

    problems: list[str] = []
    for index, row in enumerate(rows, start=1):
        path = la_root / row["relative_path"]
        if not path.is_file():
            problems.append(f"missing file: {row['relative_path']}")
            continue
        info = sf.info(str(path))
        if info.samplerate != SAMPLE_RATE or info.channels != 1:
            problems.append(
                f"{row['relative_path']}: {info.samplerate} Hz, {info.channels} channel(s)"
            )
        row["num_samples"] = int(info.frames)
        if index % 10000 == 0:
            print(f"  read {index:,}/{len(rows):,} headers", flush=True)
    return problems


def write_manifest(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def read_manifest(path: Path, splits: tuple[str, ...] | None = None) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["label"] = int(row["label"])
        row["num_samples"] = int(row["num_samples"])
    return [r for r in rows if splits is None or r["split"] in splits]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--asvspoof-root",
        type=Path,
        default=default_la_root(),
        help="The extracted LA folder (default: $DEEPSENTINEL_DATA/ASVspoof2019/LA)",
    )
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "data/processed/asvspoof2019_la")
    parser.add_argument(
        "--limit-per-split",
        type=int,
        default=None,
        help="Keep only the first N protocol rows of each split (smoke tests only)",
    )
    parser.add_argument(
        "--allow-count-mismatch",
        action="store_true",
        help="Write the manifest even if the split totals differ from the official ones",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.asvspoof_root is None:
        raise SystemExit("Set DEEPSENTINEL_DATA or pass --asvspoof-root (the extracted LA folder).")
    la_root = args.asvspoof_root
    protocol_dir = la_root / PROTOCOL_DIR
    if not protocol_dir.is_dir():
        raise SystemExit(f"Protocol folder not found: {protocol_dir}")

    rows: list[dict] = []
    protocol_hashes: dict[str, str] = {}
    for split in SPLITS:
        protocol = protocol_dir / PROTOCOL_FILES[split]
        if not protocol.is_file():
            raise SystemExit(f"Protocol file not found: {protocol}")
        protocol_hashes[PROTOCOL_FILES[split]] = sha256_file(protocol)
        part = parse_protocol(protocol, split)
        print(f"{split}: {len(part):,} rows in {protocol.name}")
        if args.limit_per_split is not None:
            part = part[: args.limit_per_split]
        rows.extend(part)

    problems = split_integrity_problems(rows)
    if args.limit_per_split is None:
        problems += attack_problems(rows)

    print("Reading audio headers ...", flush=True)
    problems += add_num_samples(rows, la_root)

    summary = summarise(rows)
    count_problems = []
    if args.limit_per_split is None:
        for split, expected in EXPECTED_COUNTS.items():
            found = summary["splits"].get(split, {}).get("utterances", 0)
            if found != expected:
                count_problems.append(f"{split}: {found:,} utterances, official total {expected:,}")

    print(json.dumps(summary, indent=2))
    for problem in problems[:50]:
        print(f"PROBLEM: {problem}")
    if len(problems) > 50:
        print(f"... and {len(problems) - 50} more problems")
    for problem in count_problems:
        print(f"COUNT MISMATCH: {problem}")

    if problems:
        print("Manifest NOT written: fix the problems above first.")
        return 1
    if count_problems and not args.allow_count_mismatch:
        print("Manifest NOT written: split totals differ from the official protocol. "
              "Check the download; use --allow-count-mismatch only after deciding why.")
        return 2

    manifest_path = args.output / "manifest.csv"
    write_manifest(manifest_path, rows)
    summary.update(
        {
            "protocol_sha256": protocol_hashes,
            "limit_per_split": args.limit_per_split,
            "split_policy": "official ASVspoof 2019 LA CM protocol files (train.trn / dev.trl / eval.trl)",
            "manifest_sha256": sha256_file(manifest_path),
        }
    )
    (args.output / "dataset_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {manifest_path} ({len(rows):,} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
