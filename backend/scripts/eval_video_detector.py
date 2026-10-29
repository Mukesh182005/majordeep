"""Measure GenD against the legacy face model on labelled videos.

Inputs (either or both):
  --data D         D/real/<source>/ and D/fake/<method>/ folders of videos (mp4, mov, avi, webm, mkv)
  --dfdc-sample D  a Kaggle DFDC train_sample_videos folder; labels from its metadata.json (REAL / FAKE)

Each video is sampled exactly as the pipeline samples it (settings.video_sample_fps,
video_max_frames); faces come from the pipeline's extract_faces; GenD scores the 1.3x
square crop of the detector's box (app/ml/gend.py). Per video: GenD mean and max over
face frames, the legacy EfficientNet mean, and the number of face frames. Videos with
no face are counted apart (GenD does not apply to them).

Reported for GenD-mean, GenD-max and legacy: AUC, accuracy and false-positive rate at
0.5, and the detection rate per folder. --full also runs the whole analyze_video and
records its final fake_probability and verdict. Metrics use numpy only.

  python scripts/eval_video_detector.py --data D:/datasets/video_test [--dfdc-sample PATH] [--full]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

BACKEND = Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(REPO))

from ml.evaluation.metrics import roc_auc  # noqa: E402

VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".webm", ".mkv", ".m4v"}
DEFAULT_OUT = REPO / "evaluation" / "VIDEO-GEND-01"


def collect(data: Path | None, dfdc: Path | None) -> list[dict]:
    items = []
    if data:
        for split, label in (("real", 0), ("fake", 1)):
            for group in sorted(d for d in (data / split).iterdir() if d.is_dir()) if (data / split).is_dir() else []:
                for f in sorted(group.rglob("*")):
                    if f.suffix.lower() in VIDEO_SUFFIXES:
                        items.append({"id": f.relative_to(data).as_posix(), "path": f, "label": label, "group": f"{split}/{group.name}"})
    if dfdc:
        meta = json.loads((dfdc / "metadata.json").read_text(encoding="utf-8"))
        for name, m in sorted(meta.items()):
            f = dfdc / name
            if f.is_file() and m.get("label") in ("REAL", "FAKE"):
                label = int(m["label"] == "FAKE")
                items.append({"id": f"dfdc/{name}", "path": f, "label": label, "group": f"dfdc/{'fake' if label else 'real'}"})
    return items


def score_video(item: dict, full: bool) -> dict:
    import torch

    from app.ml.faces import extract_faces
    from app.ml.gend import score_faces, square_face_crop
    from app.ml.preprocessing import preprocess_image, sample_video_frames
    from app.ml.registry import get_image_model

    t0 = time.perf_counter()
    frames, _meta = sample_video_frames(item["path"])
    loaded = get_image_model()
    crops, legacy = [], []
    for _, frame in frames:
        face = extract_faces(frame)[0]
        if face.box is None or face.detection_box is None:
            continue
        crops.append(square_face_crop(frame, face.detection_box))
        with torch.no_grad():
            tensor = preprocess_image(face.image, loaded.input_size).to(loaded.device)
            legacy.append(float(torch.sigmoid(loaded.module(tensor)).item()))
    gend = score_faces(crops)
    rec = {"id": item["id"], "label": item["label"], "group": item["group"], "frames": len(frames), "face_frames": len(crops),
           "gend_mean": float(np.mean(gend)) if gend else None, "gend_max": float(np.max(gend)) if gend else None,
           "legacy_mean": float(np.mean(legacy)) if legacy else None, "gend_frames": [round(g, 4) for g in gend]}
    if full:
        from app.ml.video import analyze_video

        with tempfile.TemporaryDirectory(prefix="ds-vid-") as ev:
            r = analyze_video(item["path"], ev, f"eval-{abs(hash(item['id'])) % 10**8}")
        rec["full_fake_probability"] = float(r.fake_probability)
        rec["full_verdict"] = str(r.verdict.value if hasattr(r.verdict, "value") else r.verdict)
    rec["seconds"] = round(time.perf_counter() - t0, 2)
    return rec


def metrics(rows: list[dict], key: str) -> dict | None:
    rows = [r for r in rows if r.get(key) is not None]
    if not rows:
        return None
    y = np.array([r["label"] for r in rows]); s = np.array([r[key] for r in rows], dtype=float)
    out = {"n_real": int((y == 0).sum()), "n_fake": int((y == 1).sum()),
           "accuracy_at_0.5": float(np.mean((s >= 0.5) == (y == 1))),
           "real_flagged_at_0.5": float(np.mean(s[y == 0] >= 0.5)) if (y == 0).any() else None,
           "fake_caught_at_0.5": float(np.mean(s[y == 1] >= 0.5)) if (y == 1).any() else None}
    if 0 < y.sum() < y.size:
        out["auc"] = roc_auc(y, s)
    out["per_group"] = {g: float(np.mean([r[key] >= 0.5 for r in rows if r["group"] == g])) for g in sorted({r["group"] for r in rows})}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path)
    ap.add_argument("--dfdc-sample", type=Path)
    ap.add_argument("--full", action="store_true", help="also run the whole analyze_video")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.data and not args.dfdc_sample:
        ap.error("give --data and/or --dfdc-sample")
    items = collect(args.data, args.dfdc_sample)
    print(f"{len(items)} videos ({sum(i['label'] for i in items)} fake)", flush=True)
    rows = []
    for n, item in enumerate(items, 1):
        try:
            rows.append(score_video(item, args.full))
        except Exception as exc:
            rows.append({"id": item["id"], "label": item["label"], "group": item["group"], "error": repr(exc)[:300]})
        if n % 10 == 0 or n == len(items):
            print(f"  {n}/{len(items)}", flush=True)
    scored = [r for r in rows if "error" not in r]
    with_face = [r for r in scored if r["face_frames"] > 0]
    results = {k: metrics(with_face, k) for k in ("gend_mean", "gend_max", "legacy_mean")}
    if args.full:
        results["full_pipeline"] = metrics(scored, "full_fake_probability")
    print(f"\nvideos with a face {len(with_face)}, without {len(scored) - len(with_face)}, errors {len(rows) - len(scored)}")
    print(f"{'score':<22}{'AUC':>8}{'acc@0.5':>10}{'real flagged':>14}{'fake caught':>13}")
    f = lambda v: "   n/a" if v is None else f"{100 * v:5.1f}%"
    for k, m in results.items():
        if m:
            print(f"{k:<22}{m.get('auc', float('nan')):>8.3f}{f(m['accuracy_at_0.5']):>10}{f(m['real_flagged_at_0.5']):>14}{f(m['fake_caught_at_0.5']):>13}")
    if results.get("gend_mean"):
        print("per folder, flagged at 0.5 (GenD mean):")
        for g, v in results["gend_mean"]["per_group"].items():
            print(f"  {g:<30} {f(v)}")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    from app.config import settings

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = {"script": "backend/scripts/eval_video_detector.py", "git_commit": commit,
           "utc_time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "gend_model": settings.gend_model_id,
           "data": str(args.data) if args.data else None, "dfdc_sample": str(args.dfdc_sample) if args.dfdc_sample else None,
           "n_videos": len(rows), "n_with_face": len(with_face), "results": results, "videos": rows}
    (args.out_dir / "results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"Wrote {args.out_dir / 'results.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
