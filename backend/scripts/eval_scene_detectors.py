"""Measure each scene detector, and choose a fusion weight for Community Forensics.

Scores every image with every expert in the scene ensemble, then re-fuses the
stored per-model scores in log-odds space (as ``score_scene`` does) with the
existing weights plus each COMMFOR_WEIGHT in the grid. The recommended weight
is the one with the best AUC whose real-photo flag rate is at most the
current ensemble's (weight 0) plus one percentage point.

The weight is chosen on the same images it is measured on, so the AUC at the
recommended weight is an optimistic, not a held-out, estimate.

Data, either:
  default   <repo>/accuracy_test/{100_real,100_real_whatsapp,100_real_edited}
            (label 0) and {100_ai,100_ai_processed} (label 1)
  --data D  D/real/<source>/ (label 0) and D/fake/<generator>/ (label 1)

Run from backend/:
  python scripts/eval_scene_detectors.py [--data D] [--out FILE]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

BACKEND = Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from PIL import Image  # noqa: E402

from app.config import settings  # noqa: E402
from app.ml import image_pipeline as ip  # noqa: E402  (also registers the HEIF opener)
from app.ml.base import resolve_device  # noqa: E402
from app.ml.forensics.recapture import crop_recapture_borders  # noqa: E402

REAL_FOLDERS = ("100_real", "100_real_whatsapp", "100_real_edited")
AI_FOLDERS = ("100_ai", "100_ai_processed")
COMMFOR_WEIGHT_GRID = (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0)
FLAG_AT = 0.5
FLAG_RATE_SLACK = 0.01  # one percentage point
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"}
DEFAULT_OUT = REPO / "evaluation" / "COMMFOR-01" / "scene_detector_eval.json"


def _images_in(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)


def collect(data: Path | None) -> tuple[list[tuple[Path, str, int]], list[str]]:
    """(path, folder name, label) for every image, and the folders that were missing or empty."""
    if data is None:
        root = REPO / "accuracy_test"
        folders = [(root / name, name, 0) for name in REAL_FOLDERS] + [(root / name, name, 1) for name in AI_FOLDERS]
    else:
        folders = []
        for split, label in (("real", 0), ("fake", 1)):
            parent = data / split
            if parent.is_dir():
                folders += [(d, f"{split}/{d.name}", label) for d in sorted(parent.iterdir()) if d.is_dir()]
            else:
                folders.append((parent, split, label))
    items, missing = [], []
    for folder, name, label in folders:
        images = _images_in(folder) if folder.is_dir() else []
        if not images:
            missing.append(name)
        items += [(path, name, label) for path in images]
    return items, missing


def auc(scores: np.ndarray, labels: np.ndarray) -> float | None:
    """Mann-Whitney AUC with average ranks for ties; None if a class is empty."""
    n_pos = int(labels.sum())
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    _, inverse, counts = np.unique(scores, return_inverse=True, return_counts=True)
    avg_rank = np.cumsum(counts) - (counts - 1) / 2.0  # 1-based average rank of each distinct value
    ranks = avg_rank[inverse]
    return float((ranks[labels == 1].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def metrics(scores: list[float | None], labels: list[int]) -> dict:
    keep = [i for i, s in enumerate(scores) if s is not None]
    s = np.array([scores[i] for i in keep], dtype=float)
    y = np.array([labels[i] for i in keep], dtype=int)
    flagged = s >= FLAG_AT
    n_real, n_ai = int((y == 0).sum()), int((y == 1).sum())
    real_flagged, ai_caught = int(flagged[y == 0].sum()), int(flagged[y == 1].sum())
    return {
        "auc": auc(s, y),
        "real_flagged_rate": real_flagged / n_real if n_real else None,
        "ai_caught_rate": ai_caught / n_ai if n_ai else None,
        "real_flagged": real_flagged,
        "n_real": n_real,
        "ai_caught": ai_caught,
        "n_ai": n_ai,
        "n_unscored": len(scores) - len(keep),
    }


def fuse(expert_scores: dict[str, float | None], weights: dict[str, float]) -> float | None:
    """Weighted mean in log-odds space over the experts that scored, as in ``score_scene``."""
    weighted = weight_total = 0.0
    for model_id, p in expert_scores.items():
        if p is None:
            continue
        weighted += weights[model_id] * ip._logit(p)
        weight_total += weights[model_id]
    return 1.0 / (1.0 + np.exp(-weighted / weight_total)) if weight_total else None


def score_experts(detectors, image: Image.Image) -> dict[str, float | None]:
    scores: dict[str, float | None] = {}
    for detector in detectors:
        try:
            predictions = detector.pipe(image, top_k=None)
        except Exception as exc:
            print(f"    {detector.spec.model_id} failed: {exc}")
            scores[detector.spec.model_id] = None
            continue
        p_real = sum(float(p["score"]) for p in predictions if str(p["label"]) in detector.real_labels)
        scores[detector.spec.model_id] = min(max(1.0 - p_real, 0.0), 1.0)
    return scores


def _pct(rate: float | None) -> str:
    return "   n/a" if rate is None else f"{100 * rate:5.1f}%"


def _auc_str(value: float | None) -> str:
    return "  n/a" if value is None else f"{value:.3f}"


def _row(name: str, m: dict) -> str:
    return (
        f"  {name:<44} AUC {_auc_str(m['auc'])}   real flagged {_pct(m['real_flagged_rate'])}"
        f" ({m['real_flagged']}/{m['n_real']})   AI caught {_pct(m['ai_caught_rate'])} ({m['ai_caught']}/{m['n_ai']})"
    )


def _git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True)
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True, check=True)
        return out.stdout.strip() + ("-dirty" if dirty.stdout.strip() else "")
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, help="folder holding real/<source>/ and fake/<generator>/")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    items, missing = collect(args.data)
    for name in missing:
        print(f"WARNING: no images in {name}; it is left out.")
    labels = [label for _, _, label in items]
    if 0 not in labels or 1 not in labels:
        print("ERROR: need at least one real and one AI image.")
        return 1

    detectors = ip.get_scene_detector()
    commfor = [d for d in detectors if d.spec.loader == "commfor"]
    if not commfor:
        print(
            "ERROR: Community Forensics did not load (COMMFOR_ENABLED is false, timm/safetensors are "
            f"missing, or {settings.commfor_model_id} could not be fetched). See the log above."
        )
        return 1
    commfor_id = commfor[0].spec.model_id
    base_weights = {d.spec.model_id: d.spec.weight for d in detectors}

    print(f"Scoring {len(items)} images with {len(detectors)} experts on {resolve_device()}...")
    records = []
    for n, (path, folder, label) in enumerate(items, 1):
        with Image.open(path) as opened:
            image = opened.convert("RGB")
        image, _ = crop_recapture_borders(image)  # as analyze_image does before scoring
        records.append(
            {
                "path": path.resolve().relative_to(REPO).as_posix() if path.resolve().is_relative_to(REPO) else str(path),
                "folder": folder,
                "label": label,
                "scores": score_experts(detectors, image),
            }
        )
        if n % 20 == 0 or n == len(items):
            print(f"  {n}/{len(items)}")

    print("\nPer expert (flagged = score >= 0.5):")
    per_expert = {}
    for detector in detectors:
        model_id = detector.spec.model_id
        per_expert[model_id] = metrics([r["scores"][model_id] for r in records], labels)
        print(_row(model_id, per_expert[model_id]))

    print(f"\nFusion, sweeping the {commfor_id} weight (others fixed):")
    per_weight = {}
    for w in COMMFOR_WEIGHT_GRID:
        weights = {**base_weights, commfor_id: w}
        fused = [fuse(r["scores"], weights) for r in records]
        for record, value in zip(records, fused):
            record.setdefault("fused", {})[str(w)] = None if value is None else float(value)
        per_weight[str(w)] = metrics(fused, labels)
        print(_row(f"COMMFOR_WEIGHT={w}", per_weight[str(w)]))

    baseline_flag = per_weight["0.0"]["real_flagged_rate"]
    allowed = baseline_flag + FLAG_RATE_SLACK
    eligible = [
        w for w in COMMFOR_WEIGHT_GRID
        if per_weight[str(w)]["real_flagged_rate"] <= allowed + 1e-12 and per_weight[str(w)]["auc"] is not None
    ]
    # Best AUC; on a tie, the smaller weight.
    best = max(eligible, key=lambda w: (per_weight[str(w)]["auc"], -w))
    print(
        f"\nRecommended COMMFOR_WEIGHT={best}: AUC {_auc_str(per_weight[str(best)]['auc'])} vs "
        f"{_auc_str(per_weight['0.0']['auc'])} today, real flagged {_pct(per_weight[str(best)]['real_flagged_rate'])} "
        f"(limit {_pct(allowed)}). Chosen on this same set, so not a held-out estimate."
    )

    print(f"\nFlagged per folder at COMMFOR_WEIGHT={best}:")
    per_folder = {}
    for folder in dict.fromkeys(r["folder"] for r in records):
        fused = [r["fused"][str(best)] for r in records if r["folder"] == folder]
        scored = [f for f in fused if f is not None]
        flagged = sum(f >= FLAG_AT for f in scored)
        label = next(r["label"] for r in records if r["folder"] == folder)
        per_folder[folder] = {
            "label": label,
            "flagged": flagged,
            "n": len(scored),
            "flagged_rate": flagged / len(scored) if scored else None,
        }
        kind = "real" if label == 0 else "AI"
        print(f"  {folder:<28} ({kind:<4}) {_pct(per_folder[folder]['flagged_rate'])}  ({flagged}/{len(scored)})")

    folder_counts: dict[str, int] = {}
    for r in records:
        folder_counts[r["folder"]] = folder_counts.get(r["folder"], 0) + 1
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "script": "backend/scripts/eval_scene_detectors.py",
        "git_commit": _git_commit(),
        "device": resolve_device(),
        "data": str(args.data) if args.data else "accuracy_test",
        "folder_counts": folder_counts,
        "missing_or_empty_folders": missing,
        "flag_threshold": FLAG_AT,
        "experts": [
            {"model_id": d.spec.model_id, "role": d.spec.role, "weight": d.spec.weight, "loader": d.spec.loader}
            for d in detectors
        ],
        "per_expert": per_expert,
        "commfor_model_id": commfor_id,
        "commfor_weight_grid": list(COMMFOR_WEIGHT_GRID),
        "per_commfor_weight": per_weight,
        "recommendation": {
            "commfor_weight": best,
            "rule": "best AUC with real_flagged_rate <= weight-0 rate + 0.01; ties go to the smaller weight",
            "real_flagged_rate_limit": allowed,
            "note": "Weight chosen on the same images it is measured on; not a held-out estimate.",
        },
        "per_folder_at_recommended": per_folder,
        "images": records,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
