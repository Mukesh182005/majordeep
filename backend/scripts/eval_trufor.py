"""TruFor on real photos, controlled splices and whole-image AI images.

Splices are made here, deterministically (seed 0): for each real COCO photo, a
feathered ellipse cut from another COCO photo of the same split is pasted in
(5-25 % of the area) and the result saved as JPEG quality 90 with its
ground-truth mask. This is a controlled test of local edits, not a public
benchmark: real-world composites are usually cleaner (matched lighting, careful
masks), so treat the recall here as an upper bound.

Reports, per split (dev = threshold choice, test = held out):
  AUC of the integrity score (real vs spliced), real photos flagged and splices
  caught at each threshold, mean IoU of the localisation map (> 0.5) with the
  pasted mask, and the score distribution on AI images and on accuracy_test.
The recommended flag threshold is the lowest on dev whose real-photo flag rate
is at most 2 %.

  python scripts/eval_trufor.py --manifest ../evaluation/E2E-01/image_manifest.csv \\
      --root C:/deepsentinel_data/E2E_images --accuracy-test ../accuracy_test
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BACKEND = Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(REPO))

from ml.evaluation.metrics import roc_auc  # noqa: E402

THRESHOLDS = (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
MAX_REAL_FLAG = 0.02


def make_splice(target: Path, donor: Path, rng, out_img: Path, out_mask: Path) -> None:
    base = Image.open(target).convert("RGB")
    src = Image.open(donor).convert("RGB")
    w, h = base.size
    area = rng.uniform(0.05, 0.25) * w * h
    aspect = rng.uniform(0.6, 1.6)
    ew, eh = int(min(w * 0.9, np.sqrt(area * aspect))), int(min(h * 0.9, np.sqrt(area / aspect)))
    x0, y0 = int(rng.integers(0, max(1, w - ew))), int(rng.integers(0, max(1, h - eh)))
    sw, sh = src.size
    sx, sy = int(rng.integers(0, max(1, sw - ew))), int(rng.integers(0, max(1, sh - eh)))
    patch = src.crop((sx, sy, sx + ew, sy + eh)).resize((ew, eh))
    mask = Image.new("L", (ew, eh), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, ew - 1, eh - 1), fill=255)
    soft = mask.filter(ImageFilter.GaussianBlur(max(1, min(ew, eh) // 40)))
    base.paste(patch, (x0, y0), soft)
    full = Image.new("L", (w, h), 0)
    full.paste(mask, (x0, y0))
    out_img.parent.mkdir(parents=True, exist_ok=True)
    base.save(out_img, quality=90)
    full.save(out_mask)


def score_one(path: Path, loaded, mask_path: Path | None = None) -> dict:
    import torch
    from torch.nn import functional as F

    from app.config import settings
    from app.ml.trufor import _input_tensor

    tensor, resized, _ = _input_tensor(Image.open(path), settings.trufor_max_side)
    t0 = time.perf_counter()
    with torch.inference_mode():
        pred, conf, det, _ = loaded.module(tensor.to(loaded.device, dtype=torch.float32))
        score = float(torch.sigmoid(det).item())
        heat = F.softmax(pred.squeeze(0), dim=0)[1].float().cpu().numpy()
    rec = {"score": score, "area": float((heat >= 0.5).mean()), "seconds": time.perf_counter() - t0}
    if mask_path is not None:
        gt = np.asarray(Image.open(mask_path).resize(resized.size, Image.NEAREST)) > 127
        pr = heat >= 0.5
        union = (gt | pr).sum()
        rec["iou"] = float((gt & pr).sum() / union) if union else 0.0
    return rec


def rates(scores_real, scores_fake) -> dict:
    out = {}
    for t in THRESHOLDS:
        out[str(t)] = {"real_flagged": float(np.mean(np.array(scores_real) >= t)) if scores_real else None,
                       "fake_caught": float(np.mean(np.array(scores_fake) >= t)) if scores_fake else None}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--accuracy-test", type=Path, default=None)
    parser.add_argument("--splice-dir", type=Path, default=Path("C:/deepsentinel_data/E2E_splices"))
    parser.add_argument("--ai-per-generator", type=int, default=20)
    parser.add_argument("--out", type=Path, default=REPO / "evaluation" / "TRUFOR-01" / "results.json")
    args = parser.parse_args()

    from app.ml.trufor import get_trufor

    loaded = get_trufor()
    if loaded is None:
        print("ERROR: TruFor did not load (see the log).")
        return 1
    rows = list(csv.DictReader(open(args.manifest, newline="", encoding="utf-8")))
    real = [r for r in rows if r["label"] == "0"]
    rng = np.random.default_rng(0)
    records = []
    for split in ("dev", "test"):
        pool = [r for r in real if r["split"] == split]
        donors = rng.permutation(len(pool))
        for i, r in enumerate(pool):
            donor = pool[int(donors[i])] if int(donors[i]) != i else pool[(i + 1) % len(pool)]
            img = args.splice_dir / split / f"{Path(r['path']).stem}_splice.jpg"
            msk = args.splice_dir / split / f"{Path(r['path']).stem}_mask.png"
            if not img.is_file():
                make_splice(args.root / r["path"], args.root / donor["path"], rng, img, msk)
            records.append({"set": "coco_real", "split": split, "label": 0, "id": r["id"],
                            **score_one(args.root / r["path"], loaded)})
            records.append({"set": "coco_splice", "split": split, "label": 1, "id": r["id"] + "_splice",
                            **score_one(img, loaded, msk)})
        print(f"  {split}: {len(pool)} real + {len(pool)} spliced", flush=True)
    ai = [r for r in rows if r["label"] == "1" and r["split"] == "test"]
    for gen in sorted({r["group"] for r in ai}):
        for r in [x for x in ai if x["group"] == gen][: args.ai_per_generator]:
            records.append({"set": "synthbuster_ai", "split": "test", "label": 1, "id": r["id"], "group": gen,
                            **score_one(args.root / r["path"], loaded)})
    if args.accuracy_test:
        for folder in ("100_real", "100_real_whatsapp", "100_real_edited", "100_ai", "100_ai_processed"):
            for p in sorted((args.accuracy_test / folder).glob("*")):
                records.append({"set": f"accuracy_test/{folder}", "split": "test", "label": int("_ai" in folder),
                                "id": f"{folder}/{p.name}", **score_one(p, loaded)})

    summary = {}
    for split in ("dev", "test"):
        r0 = [x["score"] for x in records if x["set"] == "coco_real" and x["split"] == split]
        r1 = [x["score"] for x in records if x["set"] == "coco_splice" and x["split"] == split]
        y = np.r_[np.zeros(len(r0)), np.ones(len(r1))]
        summary[split] = {"n_real": len(r0), "n_splice": len(r1), "auc": roc_auc(y, np.r_[r0, r1]),
                          "mean_iou_splices": float(np.mean([x["iou"] for x in records if x["set"] == "coco_splice" and x["split"] == split])),
                          "at": rates(r0, r1)}
    ok = [t for t in THRESHOLDS if summary["dev"]["at"][str(t)]["real_flagged"] <= MAX_REAL_FLAG]
    recommended = min(ok) if ok else None
    sets = {}
    for s in sorted({x["set"] for x in records}):
        sc = np.array([x["score"] for x in records if x["set"] == s])
        sets[s] = {"n": int(sc.size), "median": float(np.median(sc)), **{f"flagged_at_{t}": float(np.mean(sc >= t)) for t in THRESHOLDS}}
    result = {
        "script": "backend/scripts/eval_trufor.py", "utc_time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "device": loaded.device, "weights_sha256": "ac1d90e329a72e0d66e8665e123a19e94bfae3209c3ef8a4f9ca3b91578c7844",
        "splices": "feathered ellipse from another COCO photo of the same split, 5-25 % of the area, JPEG q90, seed 0",
        "recommended_flag_threshold": recommended,
        "rule": f"lowest threshold on dev with real photos flagged <= {MAX_REAL_FLAG:.0%}",
        "splits": summary, "sets": sets, "records": records,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    for split, s in summary.items():
        print(f"\n== {split}: real {s['n_real']}, splices {s['n_splice']}, AUC {s['auc']:.3f}, mean IoU {s['mean_iou_splices']:.3f}")
        for t, a in s["at"].items():
            print(f"   threshold {t}: real flagged {a['real_flagged']:6.1%}   splices caught {a['fake_caught']:6.1%}")
    print(f"\nrecommended flag threshold (dev): {recommended}")
    for s, d in sets.items():
        print(f"   {s:<32} n={d['n']:<4} median {d['median']:.3f}  flagged at 0.5 {d['flagged_at_0.5']:6.1%}"
              + (f"  at {recommended}: {d[f'flagged_at_{recommended}']:6.1%}" if recommended else ""))
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
