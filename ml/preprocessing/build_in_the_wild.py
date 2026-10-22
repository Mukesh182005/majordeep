#!/usr/bin/env python3
"""Manifest for the In-the-Wild audio deepfake dataset (cross-dataset test only).

In-the-Wild (Mueller et al., Interspeech 2022) contains recordings of public
figures and deepfakes of the same speakers, collected from the internet. It is
used here only as an external test of the ASVspoof-trained LCNN: nothing is
trained, selected or calibrated on it.

Licence: its project page says Apache 2.0 and its Hugging Face card says
CC BY-SA 4.0 (docs/paper_upgrade/RESOURCES.md). Resolve this before using it
in the paper; this script refuses to run without ``--licence-confirmed``.

Expected layout (the released ``release_in_the_wild.zip``, extracted)::

    <root>/meta.csv          columns: file, speaker, label ("bona-fide" or "spoof")
    <root>/<file>            one WAV per row

Writes ``data/processed/in_the_wild/manifest.csv`` (utt_id, relative_path,
label 0 = bona fide / 1 = spoof, speaker_id) and
``paper_results/audio_in_the_wild/dataset_summary.json`` (counts and the
sha256 of meta.csv). Speaker names stay in the uncommitted manifest only; the
committed summary has counts.

Usage (PowerShell)::

    $env:DEEPSENTINEL_DATA = "C:\\deepsentinel_data"
    python ml/preprocessing/build_in_the_wild.py --licence-confirmed
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.common import REPO_ROOT  # noqa: E402
from ml.provenance import collect_provenance, sha256_file  # noqa: E402

LABELS = {"bona-fide": 0, "bonafide": 0, "spoof": 1}
DEFAULT_MANIFEST = REPO_ROOT / "data/processed/in_the_wild/manifest.csv"
DEFAULT_SUMMARY = REPO_ROOT / "paper_results/audio_in_the_wild/dataset_summary.json"


def default_root() -> Path | None:
    data = os.environ.get("DEEPSENTINEL_DATA")
    return Path(data) / "release_in_the_wild" if data else None


def parse_meta(meta_path: Path) -> list[dict]:
    """Rows of meta.csv with a numeric label; refuses unknown labels and duplicate files."""
    rows: list[dict] = []
    seen: set[str] = set()
    with open(meta_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = {"file", "speaker", "label"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{meta_path.name}: missing column(s) {sorted(missing)}")
        for line_no, row in enumerate(reader, start=2):
            label = row["label"].strip().lower()
            if label not in LABELS:
                raise ValueError(f"{meta_path.name}:{line_no}: unknown label {row['label']!r}")
            name = row["file"].strip()
            if name in seen:
                raise ValueError(f"{meta_path.name}:{line_no}: duplicate file {name}")
            seen.add(name)
            rows.append({"file": name, "speaker": row["speaker"].strip(), "label": LABELS[label]})
    return rows


def build(root: Path, manifest_path: Path, summary_path: Path) -> dict:
    meta = root / "meta.csv"
    if not meta.is_file():
        raise SystemExit(f"meta.csv not found under {root}")
    rows = parse_meta(meta)
    missing = [r["file"] for r in rows if not (root / r["file"]).is_file()]
    if missing:
        raise SystemExit(f"{len(missing)} file(s) listed in meta.csv are missing, e.g. {missing[:3]}")

    speakers = {name: f"spk{i:03d}" for i, name in enumerate(sorted({r["speaker"] for r in rows}))}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["utt_id", "relative_path", "label", "speaker_id", "speaker"])
        for row in rows:
            writer.writerow([Path(row["file"]).stem, row["file"], row["label"], speakers[row["speaker"]], row["speaker"]])

    by_label = Counter(r["label"] for r in rows)
    spoofed_speakers = {r["speaker"] for r in rows if r["label"] == 1}
    bona_speakers = {r["speaker"] for r in rows if r["label"] == 0}
    summary = {
        "dataset": "In-the-Wild (Mueller et al., Interspeech 2022)",
        "use": "external test only; never used for training, selection or calibration",
        "n_utterances": len(rows),
        "n_bonafide": by_label[0],
        "n_spoof": by_label[1],
        "n_speakers": len(speakers),
        "n_speakers_with_both_classes": len(spoofed_speakers & bona_speakers),
        "meta_csv_sha256": sha256_file(meta),
        "manifest_sha256": sha256_file(manifest_path),
        "provenance": collect_provenance(manifest_path),
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=default_root(), help="folder with meta.csv (default: $DEEPSENTINEL_DATA/release_in_the_wild)")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--licence-confirmed", action="store_true",
                        help="confirm the licence conflict (Apache 2.0 vs CC BY-SA 4.0) has been resolved")
    args = parser.parse_args()
    if not args.licence_confirmed:
        raise SystemExit("In-the-Wild's licence is stated two ways (Apache 2.0 / CC BY-SA 4.0). Resolve it, record "
                         "it in docs/paper_upgrade/DATA_STATEMENT.md, then rerun with --licence-confirmed.")
    if args.root is None:
        raise SystemExit("Set DEEPSENTINEL_DATA or pass --root.")
    summary = build(args.root, args.manifest, args.summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "provenance"}, indent=2))


if __name__ == "__main__":
    main()
