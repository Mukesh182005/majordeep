"""Train the AI-generated video detector (backend/app/ml/aivideo.py).

  features --manifest M.csv --out F.npz   CLIP video features for every row (path,label,source,split)
  train    --features F.npz --out DIR     logistic regression; weight decay and threshold on validation
  evaluate --features F.npz --head DIR --out R.json   test split only, per source

Splits come from the manifest: ``train`` and ``val`` are used here, ``test`` never is.
Frames are the ones the pipeline uses: ``sample_video_frames`` at the configured fps,
then ``settings.video_scene_frames`` evenly spaced among them.
The threshold is the lowest score at which at most ``--max-real-val`` of validation real
videos score at or above it.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))


def pick_frames(path: str):
    from app.config import settings
    from app.ml.preprocessing import sample_video_frames

    frames, _ = sample_video_frames(path, target_fps=settings.video_sample_fps, max_frames=settings.video_max_frames)
    n = max(1, min(settings.video_scene_frames, len(frames)))
    idx = sorted({round(k * (len(frames) - 1) / max(1, n - 1)) for k in range(n)})
    return [frames[i][1] for i in idx]


def cmd_features(args) -> int:
    from app.ml.aivideo import video_features

    rows = list(csv.DictReader(open(args.manifest, newline="", encoding="utf-8")))
    done = {}
    if args.out.exists():
        old = np.load(args.out, allow_pickle=True)
        done = dict(zip(old["path"].tolist(), old["x"]))
    feats, keep, t0 = [], [], time.time()
    for n, r in enumerate(rows, 1):
        f = done.get(r["path"])
        if f is None:
            try:
                f = video_features(pick_frames(r["path"]))
            except Exception as exc:
                print(f"  skip {r['path']}: {exc}", flush=True)
                f = None
        if f is not None:
            feats.append(f)
            keep.append(r)
        if n % 100 == 0:
            print(f"  {n}/{len(rows)} ({(time.time() - t0) / 60:.1f} min)", flush=True)
            np.savez(args.out, x=np.stack(feats), **{k: np.array([r[k] for r in keep]) for k in ("path", "label", "source", "split")})
    np.savez(args.out, x=np.stack(feats), **{k: np.array([r[k] for r in keep]) for k in ("path", "label", "source", "split")})
    print(f"features: {len(keep)} of {len(rows)} videos -> {args.out}")
    return 0


def auc(y, s) -> float:
    from scipy.stats import rankdata

    r = rankdata(s)
    pos = y == 1
    return float((r[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * (~pos).sum()))


def fit(x, y, weight_decay: float, epochs: int = 300):
    import torch

    xt, yt = torch.tensor(x), torch.tensor(y, dtype=torch.float32)
    w = torch.zeros(x.shape[1], requires_grad=True)
    b = torch.zeros(1, requires_grad=True)
    pos_weight = torch.tensor((y == 0).sum() / max(1, (y == 1).sum()), dtype=torch.float32)  # class balance
    opt = torch.optim.LBFGS([w, b], lr=0.5, max_iter=epochs, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        loss = torch.nn.functional.binary_cross_entropy_with_logits(xt @ w + b, yt, pos_weight=pos_weight)
        loss = loss + weight_decay * (w * w).sum()
        loss.backward()
        return loss

    opt.step(closure)
    return w.detach().numpy(), float(b.item())


def cmd_train(args) -> int:
    _, x, y, source, split = load_features(args.features)
    tr, va = split == "train", split == "val"
    mean, scale = x[tr].mean(axis=0), x[tr].std(axis=0) + 1e-6
    z = (x - mean) / scale
    best = None
    for wd in args.weight_decays:
        w, b = fit(z[tr], y[tr], wd)
        s = z[va] @ w + b
        a = auc(y[va], s)
        print(f"weight decay {wd:g}: val AUC {a:.4f}")
        if best is None or a > best[0]:
            best = (a, wd, w, b)
    a, wd, w, b = best
    s_val = 1 / (1 + np.exp(-(z[va] @ w + b)))
    real = np.sort(s_val[y[va] == 0])[::-1]
    k = int(np.floor(args.max_real_val * len(real)))  # this many real val videos may sit at or above
    # Midway between the k-th and (k+1)-th highest real scores, so recomputing a score in a
    # different float order cannot move a video across it.
    threshold = float((real[k - 1] + real[k]) / 2) if 0 < k < len(real) else (float(real[0]) + 1) / 2
    caught = float((s_val[y[va] == 1] >= threshold).mean())
    per_source = {src: float((s_val[source[va] == src] >= threshold).mean()) for src in sorted(set(source[va]))}
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO).stdout.strip()
    except OSError:
        commit = ""
    head = {
        "coef": w.tolist(), "intercept": b, "mean": mean.tolist(), "scale": scale.tolist(), "threshold": threshold,
        "metadata": {
            "encoder": "openai/clip-vit-large-patch14", "features": "mean, std, mean |consecutive diff| of L2-normalised frame embeddings",
            "weight_decay": wd, "val_auc": a, "val_fake_flagged": caught,
            "val_real_flagged": float((s_val[y[va] == 0] >= threshold).mean()), "val_flagged_by_source": per_source,
            "max_real_val": args.max_real_val, "n_train": int(tr.sum()), "n_val": int(va.sum()),
            "train_sources": sorted(set(source[tr])), "features_files": [str(f) for f in args.features], "git_commit": commit,
        },
    }
    (args.out / "head.json").write_text(json.dumps(head), encoding="utf-8")
    print(json.dumps(head["metadata"], indent=1))
    return 0


def load_features(paths: list[Path]):
    """Concatenate feature files; a path seen twice keeps its last row."""
    by_path: dict[str, tuple] = {}
    for p in paths:
        d = np.load(p, allow_pickle=True)
        for row in zip(d["path"], d["x"], d["label"], d["source"], d["split"]):
            by_path[str(row[0])] = row
    rows = list(by_path.values())
    return (np.array([r[0] for r in rows]), np.stack([r[1] for r in rows]).astype(np.float32),
            np.array([int(r[2]) for r in rows]), np.array([r[3] for r in rows]), np.array([r[4] for r in rows]))


def cmd_evaluate(args) -> int:
    head = json.loads((args.head / "head.json").read_text(encoding="utf-8"))
    _, x, y, source, split = load_features(args.features)
    te = split == "test"
    z = (x[te] - np.asarray(head["mean"], np.float32)) / np.asarray(head["scale"], np.float32)
    s = 1 / (1 + np.exp(-(z @ np.asarray(head["coef"], np.float32) + head["intercept"])))
    t = head["threshold"]
    out = {
        "threshold": t, "n_test": int(te.sum()), "auc": auc(y[te], s),
        "real_flagged": float((s[y[te] == 0] >= t).mean()), "fake_flagged": float((s[y[te] == 1] >= t).mean()),
        "flagged_by_source": {src: {"n": int((source[te] == src).sum()), "flagged": float((s[source[te] == src] >= t).mean())}
                              for src in sorted(set(source[te]))},
        "head_metadata": head["metadata"],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "head_metadata"}, indent=1))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("features")
    f.add_argument("--manifest", type=Path, required=True)
    f.add_argument("--out", type=Path, required=True)
    t = sub.add_parser("train")
    t.add_argument("--features", type=Path, nargs="+", required=True)
    t.add_argument("--out", type=Path, required=True)
    t.add_argument("--weight-decays", type=float, nargs="+", default=[1e-4, 1e-3, 1e-2, 1e-1])
    t.add_argument("--max-real-val", type=float, default=0.02)
    e = sub.add_parser("evaluate")
    e.add_argument("--features", type=Path, nargs="+", required=True)
    e.add_argument("--head", type=Path, required=True)
    e.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    return {"features": cmd_features, "train": cmd_train, "evaluate": cmd_evaluate}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
