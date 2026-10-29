#!/usr/bin/env python3
"""Calibrate a fine-tuned Community Forensics checkpoint on its validation split.

Fine-tuning shifts the model's scores: it separates real from AI as well as
before but calls more real photos AI at the 0.5 cut-off. This fits one logit
offset b so that at most --max-real-flag of the validation real images score
>= 0.5 after subtracting b, and stores it in <ckpt>/metadata.json as
``calibration``; ``CommForScorer`` applies it. Only the validation split of
<ckpt>/splits.csv is read (the same fixed re-encodings as model selection).

  python ml/training/calibrate_commfor.py --ckpt checkpoints/commfor_ft_mllm_e12
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from finetune_commfor import Images  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ckpt", type=Path, required=True)
    ap.add_argument("--max-real-flag", type=float, default=0.01)
    args = ap.parse_args()

    from app.ml.commfor import CommForScorer

    scorer = CommForScorer(args.ckpt / "model.safetensors")
    scorer.logit_bias = 0.0  # fit from the raw model
    rows = [r for r in csv.DictReader(open(args.ckpt / "splits.csv", newline="", encoding="utf-8")) if r["split"] == "val"]
    for r in rows:
        r["label"] = int(r["label"])
    logits, labels = [], []
    with torch.inference_mode():
        for x, y in DataLoader(Images(rows, False), batch_size=64, num_workers=8):
            logits.append(scorer.model(x.to(scorer.device, dtype=torch.float32)).float().squeeze(1).cpu().numpy())
            labels.append(y.numpy())
    z, y = np.concatenate(logits), np.concatenate(labels)
    bias = max(0.0, float(np.quantile(z[y == 0], 1 - args.max_real_flag)))
    after = {"real_flagged": float(np.mean(z[y == 0] - bias >= 0)), "ai_caught": float(np.mean(z[y == 1] - bias >= 0))}
    before = {"real_flagged": float(np.mean(z[y == 0] >= 0)), "ai_caught": float(np.mean(z[y == 1] >= 0))}
    meta_path = args.ckpt / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["calibration"] = {"logit_bias": bias, "rule": f"at most {args.max_real_flag:.0%} of validation real images >= 0.5",
                           "n_val_real": int((y == 0).sum()), "n_val_ai": int((y == 1).sum()),
                           "val_before": before, "val_after": after}
    meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"logit bias {bias:.3f}; validation before {before}, after {after}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
