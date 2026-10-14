#!/usr/bin/env python3
"""Write ``paper/config/frozen_image_config.json`` before any T2 image is scored.

Records everything that decides an image verdict: the scene detectors (Hugging
Face ids, resolved revisions and weight-file hashes), fusion weights, decision
threshold and inconclusive band, the probability-raising and guard rules, the
border-crop parameters, and the sha256 of every source file that implements
them, plus the git commit. Commit the JSON on its own
("Freeze image configuration before T2"); if anything in it changes later,
T2 results are post-hoc.

Usage (from the repository root, on a clean working tree)::

    python paper/config/freeze_image_config.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.common import REPO_ROOT  # noqa: E402

OUTPUT = REPO_ROOT / "paper/config/frozen_image_config.json"
IMPLEMENTATION_FILES = [
    "backend/app/ml/image_pipeline.py",
    "backend/app/ml/forensics/risk_fusion.py",
    "backend/app/ml/forensics/recapture.py",
    "backend/app/ml/forensics/__init__.py",
    "backend/app/ml/base.py",
    "backend/app/config.py",
]
# The rules below are transcribed from analyze_image(); the file hashes above
# are what actually pins them.
PROBABILITY_RULES = [
    "C2PA declares AI generation -> final probability >= 0.97",
    "generator metadata in the file -> final probability >= 0.93",
    "fusion verdict MULTI_SIGNAL_CONSENSUS_MANIPULATION -> >= 0.88",
    "fusion verdict CORROBORATED_MANIPULATION -> >= 0.82",
    "copy-move detected with >= 12 cloned keypoint pairs -> >= 0.55 (asks for review)",
    "editing-software metadata, no AI metadata/provenance, scene < 0.65 and final < 0.65 -> capped at 0.49",
]
GUARD_RULES = [
    "would be AUTHENTIC but no scene detector produced a score -> INCONCLUSIVE (scene_detectors_unavailable)",
    "would be AUTHENTIC but the upload is a framed screenshot without camera metadata -> INCONCLUSIVE (screen_recapture)",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detector_records() -> list[dict]:
    from app.ml.image_pipeline import SCENE_DETECTORS, get_scene_detector
    from huggingface_hub import scan_cache_dir

    loaded = {d.spec.model_id: d for d in get_scene_detector()}
    cache = {repo.repo_id: repo for repo in scan_cache_dir().repos}
    records = []
    for spec in SCENE_DETECTORS:
        detector = loaded.get(spec.model_id)
        revision = getattr(detector.pipe.model.config, "_commit_hash", None) if detector else None
        weight_files = {}
        repo = cache.get(spec.model_id)
        if repo is not None:
            for rev in repo.revisions:
                if revision is None or rev.commit_hash == revision:
                    for f in rev.files:
                        if f.file_name.endswith((".safetensors", ".bin", ".json")):
                            weight_files[f.file_name] = sha256(f.file_path)
        records.append(
            {
                "model_id": spec.model_id,
                "fusion_weight": spec.weight,
                "role": spec.role,
                "loaded": detector is not None,
                "revision": revision,
                "file_sha256": weight_files,
            }
        )
    return records


def main() -> int:
    from app.config import settings
    from app.ml.forensics import recapture

    from ml.provenance import collect_provenance

    provenance = collect_provenance()
    if provenance["git_dirty"]:
        print("WARNING: the working tree has uncommitted changes; commit them first so the freeze names a "
              "reproducible commit.")
    detectors = detector_records()
    if not all(d["loaded"] for d in detectors):
        raise SystemExit("Not every scene detector loaded; refusing to freeze an incomplete configuration.")
    config = {
        "purpose": "Image configuration frozen before scoring the independent test set T2.",
        "frozen_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "scene_detectors": detectors,
        "fusion": "weighted mean of per-detector log-odds, P(AI) = sigmoid(sum w_i logit(p_i) / sum w_i)",
        "decision": {
            "threshold": settings.fake_threshold,
            "inconclusive_half_width": settings.uncertain_band,
            "verdicts": "MANIPULATED if p >= threshold + band; AUTHENTIC if p <= threshold - band; else INCONCLUSIVE",
        },
        "face_model_in_verdict": settings.face_model_in_verdict,
        "probability_rules": PROBABILITY_RULES,
        "guard_rules": GUARD_RULES,
        "border_crop": {
            name: value
            for name, value in vars(recapture).items()
            if name.startswith("_") and name.lstrip("_").isupper() and isinstance(value, int | float)
        },
        "implementation_sha256": {f: sha256(REPO_ROOT / f) for f in IMPLEMENTATION_FILES},
        "inference": {"dtype": "float32", "device_setting": settings.device},
        "provenance": provenance,
    }
    OUTPUT.write_text(json.dumps(config, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)}. Commit it on its own before scoring any T2 image:")
    print('  git add paper/config/frozen_image_config.json')
    print('  git commit -m "Freeze image configuration before T2"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
