"""Choose and check the "newer-generator" rule for images, from saved scores only.

Rule: an image the ensemble does not call MANIPULATED is called MANIPULATED when the
fine-tuned Community Forensics model (commfor_ft_v3) alone scores it >= T.

T is chosen on validation (evaluation/QUICK-GUARDS-01/val_three_experts.json): the lowest
value in a fixed grid at which at most --max-real-flag of validation real images reach it.
It is then applied, unchanged, to the whole-pipeline test rows in evaluation/E2E-02,
which already hold every expert's score per image. Nothing is re-run.

Run from backend/:  python scripts/eval_ft_override.py
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
GRID = [0.90, 0.95, 0.97, 0.98, 0.99, 0.995, 0.999]


def ft_key(scores: dict) -> str:
    return next(k for k in scores if "commfor_ft" in k)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--val", type=Path, default=REPO / "evaluation/QUICK-GUARDS-01/val_three_experts.json")
    ap.add_argument("--test-dir", type=Path, default=REPO / "evaluation/E2E-02")
    ap.add_argument("--max-real-flag", type=float, default=0.005)
    ap.add_argument("--out", type=Path, default=REPO / "evaluation/QUICK-GUARDS-01/image_ft_override.json")
    args = ap.parse_args()

    val = json.loads(args.val.read_text(encoding="utf-8"))["images"]
    key = ft_key(val[0]["scores"])
    y = np.array([r["label"] for r in val])
    s = np.array([r["scores"][key] for r in val])
    grid = [{"t": t, "val_real_flagged": float(np.mean(s[y == 0] >= t)), "val_ai_flagged": float(np.mean(s[y == 1] >= t))}
            for t in GRID]
    ok = [g for g in grid if g["val_real_flagged"] <= args.max_real_flag]
    chosen = min(ok, key=lambda g: g["t"]) if ok else None
    print(f"validation ({len(y)} images, {int((y == 0).sum())} real):")
    for g in grid:
        print(f"  T={g['t']:<6} real >= T {g['val_real_flagged']:6.2%}   AI >= T {g['val_ai_flagged']:6.2%}")
    if chosen is None:
        print("no threshold meets the limit")
        return 1
    t = chosen["t"]
    print(f"chosen T = {t}\n")

    tests = {}
    for name in ("image_older_generators", "image_newest_generators", "image_accuracy_test"):
        rows = {}
        for f in sorted(glob.glob(str(args.test_dir / f"{name}*.jsonl"))):
            for line in open(f, encoding="utf-8"):
                if line.strip():
                    r = json.loads(line)
                    rows.setdefault(r["id"], r)
        rows = list(rows.values())
        res = {}
        for label, rule in (("before", False), ("after", True)):
            def verdict(r):
                ft = r["scene_model_scores"].get(ft_key(r["scene_model_scores"]))
                if rule and r["verdict"] != "MANIPULATED" and ft is not None and ft >= t:
                    return "MANIPULATED"
                return r["verdict"]
            v = [(r["label"], verdict(r), r["group"]) for r in rows]
            real = [x for x in v if x[0] == 0]
            fake = [x for x in v if x[0] == 1]
            res[label] = {
                "real_called_manipulated": sum(x[1] == "MANIPULATED" for x in real), "n_real": len(real),
                "ai_called_manipulated": sum(x[1] == "MANIPULATED" for x in fake),
                "ai_called_authentic": sum(x[1] == "AUTHENTIC" for x in fake), "n_ai": len(fake),
                "per_group": {g: sum(x[1] == "MANIPULATED" for x in v if x[2] == g) for g in sorted({x[2] for x in v})},
            }
        tests[name] = res
        b, a = res["before"], res["after"]
        print(f"{name}: real MANIPULATED {b['real_called_manipulated']}/{b['n_real']} -> {a['real_called_manipulated']}/{a['n_real']}"
              f" | AI MANIPULATED {b['ai_called_manipulated']}/{b['n_ai']} -> {a['ai_called_manipulated']}/{a['n_ai']}")
        if name == "image_newest_generators":
            for g in a["per_group"]:
                print(f"    {g:<26} {b['per_group'][g]} -> {a['per_group'][g]}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"script": "backend/scripts/eval_ft_override.py", "rule": "MANIPULATED if commfor_ft_v3 >= T",
                                    "max_real_flag_on_validation": args.max_real_flag, "validation_grid": grid,
                                    "chosen_threshold": t, "test": tests}, indent=1), encoding="utf-8")
    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
