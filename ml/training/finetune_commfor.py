#!/usr/bin/env python3
"""Fine-tune the Community Forensics ViT-S/384 on newer generators.

Starts from the authors' weights (OwensLab/commfor-model-384) and adapts them to
images from FLUX.2, GPT Image 2 and Nano Banana 2 (zr-zhang/MLLM-Generated-Image-
Detection-Dataset, research use), while replaying the COCO + Synthbuster dev half
so older generators are not forgotten.

Splits (written to <out>/splits.csv, seed 0):
  * MLLM subset, per generator x category: 60 % train, 20 % val, 20 % test;
    Qwen Image 2.1 is never trained on: all of it is test (an unseen generator);
  * evaluation/E2E-01/image_manifest.csv: its dev half is training replay, its test
    half is never read here.

Shortcut control: in that dataset every AI image is PNG and almost every real one
JPEG. Every training and validation image, real or AI, is therefore resized to a
random scale and re-encoded as JPEG at random quality before the model sees it,
so file format carries no label information. Validation uses fixed (seeded)
re-encodings so epochs are comparable.

Model selection: the epoch with the best validation AUC. Inference elsewhere is
float32; training uses bf16 autocast.

  python ml/training/finetune_commfor.py --mllm-root C:/deepsentinel_data/MLLM_subset \\
      --e2e-root C:/deepsentinel_data/E2E_images --out checkpoints/commfor_ft_mllm
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO))

from ml.evaluation.metrics import roc_auc  # noqa: E402

TRAIN_GENERATORS = ("FLUX.2", "GPT Image 2", "Nano Banana 2")
UNSEEN_GENERATOR = "Qwen Image 2.1"
MEAN, STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)


def build_splits(mllm_root: Path, e2e_manifest: Path, e2e_root: Path, extra_root: Path | None = None) -> list[dict]:
    rows = list(csv.DictReader(open(mllm_root / "subset.csv", newline="", encoding="utf-8")))
    rng = random.Random(0)
    out = []
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        groups.setdefault((r["generator"], r["category"]), []).append(r)
    for (gen, cat), items in sorted(groups.items()):
        items = sorted(items, key=lambda r: r["path"])
        rng.shuffle(items)
        n = len(items)
        for i, r in enumerate(items):
            if gen == UNSEEN_GENERATOR:
                split = "test"
            else:
                split = "train" if i < 0.6 * n else ("val" if i < 0.8 * n else "test")
            out.append({"path": str(mllm_root / r["path"]), "label": int(gen != "Real"), "source": f"mllm/{gen}",
                        "category": cat, "split": split})
    if extra_root is not None:  # extra images of the hardest generators: training only, never in the subset
        for r in csv.DictReader(open(extra_root / "extra.csv", newline="", encoding="utf-8")):
            out.append({"path": str(extra_root / r["path"]), "label": 1, "source": f"mllm/{r['generator']}",
                        "category": r["category"], "split": "train"})
    for r in csv.DictReader(open(e2e_manifest, newline="", encoding="utf-8")):
        if r["split"] == "dev":  # replay of older generators; the test half is never read here
            out.append({"path": str(e2e_root / r["path"]), "label": int(r["label"]), "source": r["group"],
                        "category": "", "split": "train"})
    return out


def damage(img: Image.Image, rng: random.Random) -> Image.Image:
    """Training-only degradations seen in real uploads: blur, screenshot-style resampling, a second JPEG pass."""
    from PIL import ImageFilter

    if rng.random() < 0.25:
        # Thumbnail: shrunk to 128-320 px on the short side (it is enlarged again at inference).
        w, h = img.size
        f = rng.uniform(128, 320) / min(w, h)
        if f < 1:
            img = img.resize((max(32, round(w * f)), max(32, round(h * f))), Image.BICUBIC)
    if rng.random() < 0.3:
        img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 1.5)))
    if rng.random() < 0.3:
        w, h = img.size
        f = rng.uniform(0.4, 0.8)
        img = img.resize((max(64, round(w * f)), max(64, round(h * f))), Image.BILINEAR).resize((w, h), Image.BICUBIC)
    if rng.random() < 0.5:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=rng.randint(50, 90))
        buf.seek(0)
        img = Image.open(buf).convert("RGB")
    return img


def reencode(img: Image.Image, rng: random.Random, strong: bool = False) -> Image.Image:
    """Random downscale and JPEG quality, applied to real and AI images alike (plus ``damage`` if strong)."""
    img = img.convert("RGB")
    if strong:
        img = damage(img, rng)
    w, h = img.size
    short = rng.uniform(384, max(384, min(1024, min(w, h))))
    scale = short / min(w, h)
    if scale < 1:
        img = img.resize((max(384, round(w * scale)), max(384, round(h * scale))), Image.BICUBIC)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=rng.randint(60, 95))
    buf.seek(0)
    return Image.open(buf).convert("RGB")


class Images(Dataset):
    def __init__(self, rows: list[dict], train: bool, strong: bool = False):
        from torchvision import transforms

        self.rows, self.train, self.strong = rows, train, strong
        norm = [transforms.ToTensor(), transforms.Normalize(MEAN, STD)]
        self.tf = transforms.Compose(
            # Training sees images at the inference scale (short side 440, as in app/ml/commfor.py),
            # so small uploads are enlarged in training exactly as they are at inference.
            ([transforms.Resize(440), transforms.RandomCrop(384), transforms.RandomHorizontalFlip()] if train
             else [transforms.Resize(440), transforms.CenterCrop(384)]) + norm)

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        r = self.rows[i]
        rng = random.Random() if self.train else random.Random(hash(r["path"]) & 0xFFFFFFFF)
        img = reencode(Image.open(r["path"]), rng, strong=self.train and self.strong)
        return self.tf(img), torch.tensor(float(r["label"]))


def load_base() -> nn.Module:
    import timm
    from safetensors.torch import load_file

    from app.ml.commfor import ARCHITECTURE, DEFAULT_MODEL_ID, _KEY_PREFIX, _resolve_weights

    state = load_file(str(_resolve_weights(DEFAULT_MODEL_ID)), device="cpu")
    state = {k[len(_KEY_PREFIX):] if k.startswith(_KEY_PREFIX) else k: v for k, v in state.items()}
    model = timm.create_model(ARCHITECTURE, pretrained=False, num_classes=1)
    model.load_state_dict(state, strict=True)
    return model


@torch.no_grad()
def evaluate(model, loader, device) -> tuple[float, np.ndarray, np.ndarray]:
    model.eval()
    probs, labels = [], []
    for x, y in loader:
        logits = model(x.to(device, dtype=torch.float32)).float().squeeze(1)
        probs.append(torch.sigmoid(logits).cpu().numpy())
        labels.append(y.numpy())
    p, y = np.concatenate(probs), np.concatenate(labels)
    return roc_auc(y, p), p, y


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mllm-root", type=Path, required=True)
    ap.add_argument("--e2e-root", type=Path, required=True)
    ap.add_argument("--e2e-manifest", type=Path, default=REPO / "evaluation/E2E-01/image_manifest.csv")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--extra-root", type=Path, default=None, help="folder with extra.csv: more training images")
    ap.add_argument("--strong-aug", action="store_true", help="add blur / resampling / double-JPEG damage in training")
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    torch.manual_seed(0); random.seed(0); np.random.seed(0)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    rows = build_splits(args.mllm_root, args.e2e_manifest, args.e2e_root, args.extra_root)
    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / "splits.csv", "w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=["path", "label", "source", "category", "split"]); w.writeheader(); w.writerows(rows)
    train = [r for r in rows if r["split"] == "train"]
    val = [r for r in rows if r["split"] == "val"]
    # Balance real and AI within the training stream.
    weights = np.array([1.0 / sum(x["label"] == r["label"] for x in train) for r in train])
    sampler = torch.utils.data.WeightedRandomSampler(weights, num_samples=len(train), replacement=True,
                                                     generator=torch.Generator().manual_seed(0))
    tl = DataLoader(Images(train, True, args.strong_aug), batch_size=args.batch, sampler=sampler, num_workers=args.workers,
                    persistent_workers=args.workers > 0, drop_last=True)
    vl = DataLoader(Images(val, False), batch_size=64, num_workers=args.workers)
    print(f"train {len(train)} (real {sum(r['label'] == 0 for r in train)}), val {len(val)}, device {device}", flush=True)

    model = load_base().to(device)
    base_auc, _, _ = evaluate(model, vl, device)
    print(f"epoch 0 (authors' weights): val AUC {base_auc:.4f}", flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.05)
    steps = args.epochs * len(tl)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, s / 200) * 0.5 * (1 + math.cos(math.pi * min(s, steps) / steps)))
    loss_fn = nn.BCEWithLogitsLoss()
    history = [{"epoch": 0, "val_auc": base_auc}]
    best = (base_auc, 0)
    torch.save(model.state_dict(), args.out / "best_state.pt")
    for epoch in range(1, args.epochs + 1):
        model.train(); t0 = time.time(); total = 0.0
        for i, (x, y) in enumerate(tl):
            with torch.autocast(device_type=device, dtype=torch.bfloat16, enabled=device == "cuda"):
                logits = model(x.to(device)).squeeze(1)
            loss = loss_fn(logits.float(), y.to(device))
            opt.zero_grad(set_to_none=True); loss.backward(); opt.step(); sched.step()
            total += loss.item()
        auc, _, _ = evaluate(model, vl, device)
        history.append({"epoch": epoch, "train_loss": total / len(tl), "val_auc": auc, "minutes": (time.time() - t0) / 60})
        print(f"epoch {epoch}: loss {total / len(tl):.4f}  val AUC {auc:.4f}  ({(time.time() - t0) / 60:.1f} min)", flush=True)
        if auc > best[0]:
            best = (auc, epoch)
            torch.save(model.state_dict(), args.out / "best_state.pt")

    from safetensors.torch import save_file

    state = torch.load(args.out / "best_state.pt", map_location="cpu", weights_only=True)
    save_file({f"vit.{k}": v.contiguous() for k, v in state.items()}, str(args.out / "model.safetensors"))
    (args.out / "best_state.pt").unlink()
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    meta = {"base": "OwensLab/commfor-model-384", "architecture": "vit_small_patch16_384", "best_epoch": best[1],
            "best_val_auc": best[0], "history": history, "train_n": len(train), "val_n": len(val),
            "train_generators": list(TRAIN_GENERATORS), "unseen_test_generator": UNSEEN_GENERATOR,
            "replay": "evaluation/E2E-01/image_manifest.csv dev half", "shortcut_control": "random resize + JPEG q60-95 on every image",
            "extra_root": str(args.extra_root) if args.extra_root else None, "strong_aug": args.strong_aug,
            "lr": args.lr, "epochs": args.epochs, "batch": args.batch, "git_commit": commit,
            "utc_time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "data_licence": "zr-zhang/MLLM-Generated-Image-Detection-Dataset: research use only"}
    (args.out / "metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"best epoch {best[1]} (val AUC {best[0]:.4f}); wrote {args.out / 'model.safetensors'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
