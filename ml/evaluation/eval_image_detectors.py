#!/usr/bin/env python3
"""Per-image scores for an image test manifest (H560, T2 and its variants).

For every manifest row this records, as one JSON line:

* each scene detector's P(AI) and the fused P(AI) from ``score_scene`` in
  ``backend/app/ml/image_pipeline.py``, computed on the image exactly as the
  pipeline sees it (screenshot borders cropped first);
* when borders were cropped, the same scores on the uncropped image (for the
  border-crop ablation);
* optional extra scorers (``--extra-scorers``) such as published baselines,
  run on the original file with their own preprocessing;
* with ``--end-to-end``: the verdict, final probability, verdict basis (guard
  rule) and the probability rules that fired in ``analyze_image``;
* latency and the file's sha256.

Resumable: rows already in the output file are skipped; a failing image is
logged to ``<output>.errors.jsonl`` and retried on the next run. Inference runs
in float32 (the script checks the loaded detectors' dtype).

Manifest format: see ``paper/README.md``.

Usage (PowerShell, from the repository root)::

    python ml/evaluation/eval_image_detectors.py --manifest paper/manifests/h560.csv `
        --image-root "$env:DEEPSENTINEL_DATA\\H560" --output paper_results/image_h560/scores.jsonl --end-to-end
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path, PureWindowsPath
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import ml.common  # noqa: E402,F401  (puts backend/ on sys.path)

MANIFEST_COLUMNS = ["image_id", "relative_path", "label", "generator", "source", "condition", "group"]


def read_image_manifest(path: Path) -> list[dict]:
    """Read and validate an image manifest (see paper/README.md)."""
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in MANIFEST_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path.name}: missing columns {missing}")
        rows = list(reader)
    seen: set[str] = set()
    for line, row in enumerate(rows, start=2):
        if row["image_id"] in seen:
            raise ValueError(f"{path.name}:{line}: duplicate image_id {row['image_id']}")
        seen.add(row["image_id"])
        if row["label"] not in {"0", "1"}:
            raise ValueError(f"{path.name}:{line}: label must be 0 or 1")
        row["label"] = int(row["label"])
        if row["label"] == 0 and row["generator"] != "real":
            raise ValueError(f"{path.name}:{line}: a real image must have generator 'real'")
        if row["label"] == 1 and row["generator"] in {"", "real"}:
            raise ValueError(f"{path.name}:{line}: an AI image needs its generator")
        rel = row["relative_path"]
        if rel.startswith(("/", "\\")) or PureWindowsPath(rel).drive or ".." in PureWindowsPath(rel).parts:
            raise ValueError(f"{path.name}:{line}: relative_path must be relative to the image root")
        if not row["group"]:
            row["group"] = row["image_id"]
    return rows


def group_split_problems(rows: list[dict], split_column: str = "split") -> list[str]:
    """Groups (an original and its edited copies) spread over more than one split."""
    splits: dict[str, set[str]] = {}
    for row in rows:
        if split_column in row:
            splits.setdefault(row["group"], set()).add(row[split_column])
    return [f"group {g} in splits {sorted(s)}" for g, s in sorted(splits.items()) if len(s) > 1]


def done_ids(output: Path) -> set[str]:
    if not output.is_file():
        return set()
    ids: set[str] = set()
    with open(output, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                ids.add(json.loads(line)["image_id"])
    return ids


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def end_to_end_record(path: Path, job_id: str) -> dict:
    """Run the full image pipeline and keep the verdict and the rules that shaped it."""
    from app.ml.image_pipeline import analyze_image

    with tempfile.TemporaryDirectory(prefix="ds-eval-") as evidence_dir:
        t0 = time.perf_counter()
        result = analyze_image(path, evidence_dir, job_id)
        latency = (time.perf_counter() - t0) * 1000
    evidence = result.evidence
    forensics = evidence.get("forensics", {})
    tampering = forensics.get("tampering", {})
    return {
        "verdict": result.verdict.value if hasattr(result.verdict, "value") else str(result.verdict),
        "final_probability": result.fake_probability,
        "verdict_basis": evidence.get("verdict_basis"),
        "threat_code": evidence.get("threat_code"),
        "rules": {
            "c2pa_ai_disclosed": bool(forensics.get("provenance_threat", {}).get("ai_generation_disclosed")),
            "ai_metadata": bool(forensics.get("metadata_forensics", {}).get("ai_metadata_detected")),
            "fusion_verdict": forensics.get("risk_engine", {}).get("evidence_fusion", {}).get("fusion_verdict"),
            "copy_move_review": bool(tampering.get("copy_move_detected"))
            and tampering.get("cloned_feature_pairs", 0) >= 12,
            "editor_cap": evidence.get("threat_code") == "DIGITAL_RETOUCHING",
        },
        "latency_ms_end_to_end": round(latency, 1),
    }


def score_row(
    row: dict,
    image_root: Path,
    scene_scorer: Callable,
    extra_scorers: dict[str, Callable],
    end_to_end: bool,
) -> dict:
    from app.ml.forensics.recapture import crop_recapture_borders
    from PIL import Image

    path = image_root / row["relative_path"]
    with Image.open(path) as opened:
        image = opened.convert("RGB")
    cropped, recapture = crop_recapture_borders(image)

    t0 = time.perf_counter()
    scene = scene_scorer(cropped)
    latency = (time.perf_counter() - t0) * 1000
    record: dict[str, Any] = {
        **{k: row[k] for k in MANIFEST_COLUMNS},
        "sha256": sha256_file(path),
        "width": image.size[0],
        "height": image.size[1],
        "border_cropped": bool(recapture["letterbox_detected"]),
        "framed": bool(recapture["framed"]),
        "border_area_ratio": recapture["border_area_ratio"],
        "fused": scene["scene_ai_prob"],
        "detectors": scene["model_scores"],
        "latency_ms_scene": round(latency, 1),
    }
    if recapture["letterbox_detected"]:
        uncropped = scene_scorer(image)
        record["fused_uncropped"] = uncropped["scene_ai_prob"]
        record["detectors_uncropped"] = uncropped["model_scores"]
    extra: dict[str, float] = {}
    extra_latency: dict[str, float] = {}
    for name, scorer in extra_scorers.items():
        t0 = time.perf_counter()
        extra[name] = scorer(path)
        extra_latency[name] = round((time.perf_counter() - t0) * 1000, 1)
    if extra:
        record["extra"] = extra
        record["latency_ms_extra"] = extra_latency
    if end_to_end:
        record["end_to_end"] = end_to_end_record(path, f"eval-{row['image_id']}")
    return record


def run(
    rows: list[dict],
    image_root: Path,
    output: Path,
    scene_scorer: Callable,
    extra_scorers: dict[str, Callable] | None = None,
    end_to_end: bool = False,
    limit: int | None = None,
) -> dict:
    """Score every row not yet in ``output``; returns counts."""
    output.parent.mkdir(parents=True, exist_ok=True)
    errors_path = output.with_suffix(".errors.jsonl")
    done = done_ids(output)
    todo = [r for r in rows if r["image_id"] not in done][:limit]
    print(f"{len(done):,} already scored, {len(todo):,} to score", flush=True)
    scored = failed = 0
    t0 = time.perf_counter()
    with open(output, "a", encoding="utf-8") as out, open(errors_path, "a", encoding="utf-8") as err:
        for i, row in enumerate(todo, start=1):
            try:
                record = score_row(row, image_root, scene_scorer, extra_scorers or {}, end_to_end)
            except Exception as exc:  # one bad file must not stop the run
                failed += 1
                err.write(json.dumps({"image_id": row["image_id"], "error": f"{type(exc).__name__}: {exc}"}) + "\n")
                err.flush()
                continue
            out.write(json.dumps(record) + "\n")
            out.flush()
            scored += 1
            if i % 25 == 0 or i == len(todo):
                rate = i / max(time.perf_counter() - t0, 1e-6)
                print(f"  {i:,}/{len(todo):,} | {rate:.2f} img/s | ETA {(len(todo) - i) / max(rate, 1e-6) / 60:.1f} min",
                      flush=True)
    return {"already_done": len(done), "scored": scored, "failed": failed}


def detector_records() -> list[dict]:
    """Model ids, revisions and dtypes of the loaded scene detectors (float32 enforced)."""
    import torch
    from app.ml.image_pipeline import get_scene_detector

    records = []
    for detector in get_scene_detector():
        dtype = next(detector.pipe.model.parameters()).dtype
        if dtype != torch.float32:
            raise SystemExit(f"{detector.spec.model_id} runs in {dtype}; inference must be float32")
        records.append(
            {
                "model_id": detector.spec.model_id,
                "weight": detector.spec.weight,
                "revision": getattr(detector.pipe.model.config, "_commit_hash", None),
                "dtype": str(dtype),
                "device": str(detector.pipe.device),
            }
        )
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="JSON Lines file")
    parser.add_argument("--end-to-end", action="store_true")
    parser.add_argument("--extra-scorers", nargs="*", default=[], help="names from ml/evaluation/baselines")
    parser.add_argument("--condition", default=None, help="score only rows with this condition")
    parser.add_argument("--limit", type=int, default=None, help="score at most N new rows (timing tests)")
    return parser.parse_args()


def main() -> None:
    from app.ml.image_pipeline import score_scene

    from ml.provenance import collect_provenance

    args = parse_args()
    rows = read_image_manifest(args.manifest)
    if args.condition:
        rows = [r for r in rows if r["condition"] == args.condition]
    extra = {}
    if args.extra_scorers:
        from ml.evaluation.baselines import load_scorer

        extra = {name: load_scorer(name) for name in args.extra_scorers}

    detectors = detector_records()
    counts = run(rows, args.image_root, args.output, score_scene, extra, args.end_to_end, args.limit)
    config_path = args.output.with_name(args.output.stem + "_config.json")
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {"runs": []}
    config["runs"].append(
        {
            "manifest": args.manifest.as_posix(),
            "image_root": "<image root>" if args.image_root.is_absolute() else args.image_root.as_posix(),
            "condition": args.condition,
            "end_to_end": args.end_to_end,
            "extra_scorers": args.extra_scorers,
            "scene_detectors": detectors,
            "counts": counts,
            "provenance": collect_provenance(args.manifest),
        }
    )
    config_path.write_text(json.dumps(config, indent=2, default=str), encoding="utf-8")
    print(json.dumps(counts))
    if os.environ.get("DS_EVAL_STRICT") and counts["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
