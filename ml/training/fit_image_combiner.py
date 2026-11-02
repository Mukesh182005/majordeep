"""Fit the learned image-detector combination (backend/app/ml/image_combiner.py).

  python ml/training/fit_image_combiner.py --manifest UPLOAD_SET/manifest.csv --scores S.jsonl [S2.jsonl]
      --out checkpoints/image_combiner.json --results evaluation/IMAGE-COMBINER-01/results.json

Inputs: the upload-like manifest (path,label,source,variant,image_id,split) and per-detector scores
(score_upload_set.py). Fit on split=tune only: class-balanced logistic regression on each
detector's log-odds. Cut-offs, also on tune: AUTHENTIC at most --max-ai-authentic of tune AI images,
MANIPULATED at most --max-real-flagged of tune real images. The coefficients are rescaled so these
cut-offs land on the app's verdict band. Test numbers (split=test) are written for every variant
and source, next to the current hand-set fusion under the same band.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
EPS = 1e-4
LOW, HIGH = 0.42, 0.58  # settings.fake_threshold -/+ settings.uncertain_band
CURRENT = {"haywoodsloan/ai-image-detector-deploy": 0.75, "OwensLab/commfor-model-384": 4.0, "commfor_ft_v3/model.safetensors": 4.0}


def logit(p):
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def short(key: str) -> str:
    k = key.replace("\\", "/")
    return "/".join(k.split("/")[-2:]) if "checkpoints/" in k else k


def fit_lr(x, y, l2=1e-2, iters=500):
    w = np.zeros(x.shape[1]); b = 0.0
    sw = np.where(y == 1, 0.5 / max(1, (y == 1).sum()), 0.5 / max(1, (y == 0).sum()))
    for _ in range(iters):  # Newton steps on the weighted, L2-penalised log-loss
        z = x @ w + b; p = 1 / (1 + np.exp(-z))
        g = sw * (p - y); gw = x.T @ g + l2 * w; gb = g.sum()
        s = sw * p * (1 - p)
        H = (x * s[:, None]).T @ x + l2 * np.eye(x.shape[1]); hb = s.sum(); hwb = x.T @ s
        A = np.block([[H, hwb[:, None]], [hwb[None, :], np.array([[hb]])]])
        step = np.linalg.solve(A, np.concatenate([gw, [gb]]))
        w -= step[:-1]; b -= step[-1]
        if np.abs(step).max() < 1e-8:
            break
    return w, b


def verdicts(p):
    return np.where(p >= HIGH, "MANIPULATED", np.where(p <= LOW, "AUTHENTIC", "INCONCLUSIVE"))


def table(y, v):
    real, ai = y == 0, y == 1
    f = lambda m, k: int((v[m] == k).sum())
    return {"n_real": int(real.sum()), "n_ai": int(ai.sum()),
            "real_authentic": f(real, "AUTHENTIC"), "real_inconclusive": f(real, "INCONCLUSIVE"), "real_manipulated": f(real, "MANIPULATED"),
            "ai_authentic": f(ai, "AUTHENTIC"), "ai_inconclusive": f(ai, "INCONCLUSIVE"), "ai_manipulated": f(ai, "MANIPULATED"),
            "correct_decided": f(real, "AUTHENTIC") + f(ai, "MANIPULATED")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--scores", type=Path, nargs="+", required=True)
    ap.add_argument("--models", nargs="+", default=list(CURRENT))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--max-ai-authentic", type=float, default=0.01)
    ap.add_argument("--max-real-flagged", type=float, default=0.02)
    args = ap.parse_args()

    scores: dict[str, dict] = {}
    for f in args.scores:
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            scores.setdefault(r["path"], {}).update({short(k): v for k, v in r["scores"].items()})
    rows = [r for r in csv.DictReader(open(args.manifest, encoding="utf-8")) if all(m in scores.get(r["path"], {}) for m in args.models)]
    y = np.array([int(r["label"]) for r in rows]); split = np.array([r["split"] for r in rows])
    P = np.array([[scores[r["path"]][m] for m in args.models] for r in rows]); X = logit(P)
    tune, test = split == "tune", split == "test"

    w, b = fit_lr(X[tune], y[tune])
    z_tune = X[tune] @ w + b
    zr, za = np.sort(z_tune[y[tune] == 0]), np.sort(z_tune[y[tune] == 1])
    z_low = za[int(math.floor(args.max_ai_authentic * len(za)))] - 1e-9   # AI at or below: <= max share
    z_high = zr[int(math.ceil((1 - args.max_real_flagged) * len(zr))) - 1] + 1e-9  # real at or above: <= max share
    if z_low >= z_high:  # well separated: put the band between the two cut-offs
        z_low, z_high = (z_low + z_high) / 2 - 1e-6, (z_low + z_high) / 2 + 1e-6
    a = (math.log(HIGH / (1 - HIGH)) - math.log(LOW / (1 - LOW))) / (z_high - z_low)
    c = math.log(LOW / (1 - LOW)) - a * z_low
    coef, intercept = (a * w).tolist(), float(a * b + c)

    p_new = 1 / (1 + np.exp(-(X @ np.array(coef) + intercept)))
    cw = np.array([CURRENT.get(m, 0.0) for m in args.models])
    p_cur = 1 / (1 + np.exp(-(X @ cw) / cw.sum()))
    v_new, v_cur = verdicts(p_new), verdicts(p_cur)
    v_cur_nocam = np.where((v_cur == "AUTHENTIC") & (p_cur >= 0.02), "INCONCLUSIVE", v_cur)  # today's no-camera rule

    res = {"models": args.models, "n_rows": len(rows), "tune": {"combined": table(y[tune], v_new[tune])}, "test": {}}
    variants = sorted({r["variant"] for r in rows}); sources = sorted({r["source"] for r in rows})
    var = np.array([r["variant"] for r in rows]); src = np.array([r["source"] for r in rows])
    for name, mask in [("all", test)] + [(f"variant/{v}", test & (var == v)) for v in variants] + [(f"source/{s}", test & (src == s)) for s in sources]:
        res["test"][name] = {"combined": table(y[mask], v_new[mask]), "current_fusion_no_camera_rule": table(y[mask], v_cur_nocam[mask]),
                             "current_fusion_band_only": table(y[mask], v_cur[mask])}
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO).stdout.strip()
    except OSError:
        commit = ""
    meta = {"fitted_on": str(args.manifest), "split": "tune", "max_ai_authentic": args.max_ai_authentic,
            "max_real_flagged": args.max_real_flagged, "raw_coef": w.tolist(), "raw_intercept": float(b), "git_commit": commit}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"models": args.models, "coef": coef, "intercept": intercept, "metadata": meta}, indent=1), encoding="utf-8")
    args.results.parent.mkdir(parents=True, exist_ok=True)
    args.results.write_text(json.dumps(res, indent=1), encoding="utf-8")
    t = res["test"]["all"]
    for k in ("combined", "current_fusion_no_camera_rule"):
        print(k, t[k])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
