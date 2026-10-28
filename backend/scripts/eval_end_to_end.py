"""Whole-pipeline accuracy: every file through app.ml.pipeline.analyze, the function the worker runs.

Unlike the model-only scripts, this measures what a user is told: the verdict
(AUTHENTIC / INCONCLUSIVE / MANIPULATED) after every rule, guard and override,
the final probability, and how often each analysis stage raises a flag on real
versus fake files (whether its diagnosis carries information).

  score-image  --manifest M.csv --root R --name NAME
               M has columns id, path (relative to R), label (0 real, 1 AI), group, split.
  score-audio  --asvspoof-root LA --per-class N --name NAME      (ASVspoof 2019 LA eval sample)
               --asvspoof5-root V5 --per-class N --name NAME     (ASVspoof 5 eval clips on disk)
               --data D --name NAME                              (D/real/<source>/, D/fake/<generator>/)
  summarise    reads every <name>.jsonl in --out-dir, writes summary.json, prints the tables.

Scoring is resumable (rows already in <name>.jsonl are skipped; failures go to
<name>.errors.jsonl and are retried). Nothing is tuned here. Run from backend/.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
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

DEFAULT_OUT = REPO / "evaluation" / "E2E-01"
VERDICTS = ("AUTHENTIC", "INCONCLUSIVE", "MANIPULATED")
PASSING = {"PASSED", "RECORDED", "NORMAL", "SECURE", "NEUTRAL", "INFO", "SKIPPED", None}


# --------------------------------------------------------------------------- scoring


def _done(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    return {json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def _stages(evidence: dict) -> dict[str, dict]:
    modules = evidence.get("pipeline_modules") or (evidence.get("forensics") or {}).get("pipeline_modules") or []
    return {f"{m.get('stage')}: {m.get('name')}": {"status": m.get("status")} for m in modules if m.get("stage") is not None}


def _record(media: str, item: dict, result, latency_s: float) -> dict:
    ev = result.evidence or {}
    rec = {
        "id": item["id"], "label": int(item["label"]), "group": item["group"], "split": item.get("split", ""),
        "media": media, "verdict": str(result.verdict.value if hasattr(result.verdict, "value") else result.verdict),
        "fake_probability": float(result.fake_probability), "model_name": result.model_name,
        "threat_code": ev.get("threat_code"), "verdict_basis": ev.get("verdict_basis"),
        "stages": _stages(ev), "latency_s": round(latency_s, 3),
    }
    if media == "image":
        rec["scene_model_scores"] = ev.get("scene_model_scores")
        rec["faces_detected"] = ev.get("faces_detected")
    else:
        mo = ev.get("models_output") or {}
        rec["codec"] = item.get("codec")
        rec["verdict_source"] = (ev.get("fusion_decision") or {}).get("verdict_source")
        rec["pellav2"] = (mo.get("pellav2") or {}).get("prob")
        rec["lcnn"] = (mo.get("lcnn_asvspoof") or {}).get("probability")
        rec["experimental"] = ev.get("experimental")
        rec["codec_guard"] = ev.get("codec_guard")
    return rec


def score(media: str, items: list[dict], out_dir: Path, name: str) -> None:
    from app.ml.pipeline import analyze
    from app.models import MediaType

    out_dir.mkdir(parents=True, exist_ok=True)
    out, errors = out_dir / f"{name}.jsonl", out_dir / f"{name}.errors.jsonl"
    done = _done(out)
    todo = [i for i in items if i["id"] not in done]
    print(f"{name}: {len(items)} items, {len(done)} already scored, {len(todo)} to score", flush=True)
    kind = MediaType.IMAGE if media == "image" else MediaType.AUDIO
    for n, item in enumerate(todo, 1):
        with tempfile.TemporaryDirectory(prefix="ds-e2e-") as evidence_dir:
            t0 = time.perf_counter()
            try:
                result = analyze(kind, item["path"], evidence_dir, f"e2e-{item['id']}")
            except Exception as exc:
                with open(errors, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"id": item["id"], "error": repr(exc)[:500]}) + "\n")
                continue
            record = _record(media, item, result, time.perf_counter() - t0)
        with open(out, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        if n % 50 == 0 or n == len(todo):
            print(f"  {n}/{len(todo)}", flush=True)


def image_items(manifest: Path, root: Path) -> list[dict]:
    with open(manifest, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [{**r, "path": root / r["path"], "label": int(r["label"])} for r in rows]


def audio_items(args) -> list[dict]:
    rng = np.random.default_rng(args.seed)
    if args.asvspoof_root:
        root = args.asvspoof_root
        rows = []
        for line in (root / "ASVspoof2019_LA_cm_protocols" / "ASVspoof2019.LA.cm.eval.trl.txt").read_text().splitlines():
            p = line.split()
            if len(p) == 5:
                rows.append({"id": p[1], "path": root / "ASVspoof2019_LA_eval" / "flac" / f"{p[1]}.flac",
                             "label": int(p[4] == "spoof"), "group": p[3] if p[4] == "spoof" else "bonafide"})
        return _balanced(rows, args.per_class, rng, "group")
    if args.asvspoof5_root:
        root = args.asvspoof5_root
        present = {p.stem: p for p in (root / "flac_E_eval").glob("E_*.flac")}
        rows = []
        for line in (root / "ASVspoof5.eval.track_1.tsv").read_text().splitlines():
            p = line.split()
            if len(p) >= 9 and p[1] in present:
                spoof = p[8] == "spoof"
                rows.append({"id": p[1], "path": present[p[1]], "label": int(spoof),
                             "group": p[7] if spoof else "bonafide", "codec": p[3]})
        return _balanced(rows, args.per_class, rng, "codec")
    items = []
    for split, label in (("real", 0), ("fake", 1)):
        for group in sorted(d for d in (args.data / split).iterdir() if d.is_dir()):
            for f in sorted(group.rglob("*")):
                if f.is_file():
                    items.append({"id": f.relative_to(args.data).as_posix(), "path": f, "label": label,
                                  "group": f"{split}/{group.name}"})
    return items


def _balanced(rows: list[dict], per_class: int, rng, spread_real_by: str) -> list[dict]:
    """``per_class`` real (spread over ``spread_real_by``) and ``per_class`` fake (spread over attacks)."""
    picked = []
    for label, key in ((0, spread_real_by), (1, "group")):
        pool = [r for r in rows if r["label"] == label]
        strata: dict[str, list[dict]] = {}
        for r in pool:
            strata.setdefault(r.get(key) or "-", []).append(r)
        keys = sorted(strata)
        quota = [per_class // len(keys) + (i < per_class % len(keys)) for i in range(len(keys))]
        for k, n in zip(keys, quota):
            s = strata[k]
            picked += [s[i] for i in rng.choice(len(s), min(n, len(s)), replace=False)]
    return sorted(picked, key=lambda r: r["id"])


# --------------------------------------------------------------------------- summary


def _wilson(k: int, n: int) -> list[float] | None:
    if n == 0:
        return None
    z, p = 1.96, k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)]


def _rate(k: int, n: int) -> dict:
    return {"k": k, "n": n, "rate": None if n == 0 else k / n, "ci95": _wilson(k, n)}


def summarise_set(rows: list[dict], seed: int = 0) -> dict:
    real = [r for r in rows if r["label"] == 0]
    fake = [r for r in rows if r["label"] == 1]
    confusion = {cls: {v: sum(r["verdict"] == v for r in group) for v in VERDICTS}
                 for cls, group in (("real", real), ("fake", fake))}
    decided = [r for r in rows if r["verdict"] != "INCONCLUSIVE"]
    correct = sum((r["verdict"] == "MANIPULATED") == (r["label"] == 1) for r in decided)
    out = {
        "n_real": len(real), "n_fake": len(fake), "confusion": confusion,
        "real_called_authentic": _rate(confusion["real"]["AUTHENTIC"], len(real)),
        "real_called_manipulated": _rate(confusion["real"]["MANIPULATED"], len(real)),
        "fake_called_manipulated": _rate(confusion["fake"]["MANIPULATED"], len(fake)),
        "fake_called_authentic": _rate(confusion["fake"]["AUTHENTIC"], len(fake)),
        "inconclusive": _rate(sum(r["verdict"] == "INCONCLUSIVE" for r in rows), len(rows)),
        "accuracy_on_decided": _rate(correct, len(decided)),
        "accuracy_all": _rate(correct, len(rows)),
        "latency_s": {"p50": float(np.percentile([r["latency_s"] for r in rows], 50)),
                      "p95": float(np.percentile([r["latency_s"] for r in rows], 95))} if rows else None,
    }
    if real and fake:
        y = np.array([r["label"] for r in rows]); s = np.array([r["fake_probability"] for r in rows])
        rng = np.random.default_rng(seed)
        pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]
        boots = [roc_auc(y[i], s[i]) for i in (np.r_[rng.choice(pos, pos.size), rng.choice(neg, neg.size)] for _ in range(1000))]
        out["auc_final_probability"] = {"auc": roc_auc(y, s), "ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]}
    groups = {}
    for g in sorted({r["group"] for r in rows}):
        sub = [r for r in rows if r["group"] == g]
        lab = sub[0]["label"]
        groups[g] = {"label": lab, **{v: sum(r["verdict"] == v for r in sub) for v in VERDICTS}, "n": len(sub)}
    out["per_group"] = groups
    codecs = sorted({r.get("codec") for r in rows if r.get("codec")})
    if codecs:
        out["per_codec"] = {c: {cls: {v: sum(r["verdict"] == v for r in rows if r.get("codec") == c and r["label"] == lab)
                                      for v in VERDICTS} for cls, lab in (("real", 0), ("fake", 1))} for c in codecs}
    stages = {}
    for name in sorted({k for r in rows for k in r["stages"]}, key=lambda k: (int(k.split(":")[0]) if k.split(":")[0].isdigit() else 99, k)):
        flags = {cls: [r["stages"][name]["status"] not in PASSING for r in group if name in r["stages"]]
                 for cls, group in (("real", real), ("fake", fake))}
        fr = sum(flags["real"]) / len(flags["real"]) if flags["real"] else None
        ff = sum(flags["fake"]) / len(flags["fake"]) if flags["fake"] else None
        stages[name] = {"flagged_real": fr, "flagged_fake": ff,
                        "balanced_accuracy": None if fr is None or ff is None else (ff + (1 - fr)) / 2,
                        "statuses": sorted({r["stages"][name]["status"] for r in rows if name in r["stages"]} - {None})}
    out["stage_diagnosis"] = stages
    out["threat_codes"] = {cls: dict(sorted({t: sum(r.get("threat_code") == t for r in group)
                                             for t in {r.get("threat_code") for r in group}}.items(), key=lambda x: -x[1]))
                           for cls, group in (("real", real), ("fake", fake))}
    return out


def _p(v) -> str:
    return "  n/a" if v is None else f"{100 * v:5.1f}%"


def print_set(name: str, s: dict) -> None:
    c = s["confusion"]
    print(f"\n== {name}  (real {s['n_real']}, fake {s['n_fake']})")
    print(f"  verdict        AUTHENTIC  INCONCLUSIVE  MANIPULATED")
    for cls in ("real", "fake"):
        print(f"  {cls:<12} {c[cls]['AUTHENTIC']:>10} {c[cls]['INCONCLUSIVE']:>13} {c[cls]['MANIPULATED']:>12}")
    auc = s.get("auc_final_probability")
    print(f"  real called MANIPULATED {_p(s['real_called_manipulated']['rate'])}   fake called MANIPULATED "
          f"{_p(s['fake_called_manipulated']['rate'])}   INCONCLUSIVE {_p(s['inconclusive']['rate'])}   "
          f"accuracy on decided {_p(s['accuracy_on_decided']['rate'])}   AUC {auc['auc']:.3f}" if auc else "")
    print("  per group (fake: MANIPULATED / n; real: MANIPULATED / n):")
    for g, d in s["per_group"].items():
        print(f"    {g:<26} {d['MANIPULATED']:>4}/{d['n']:<4}  inconclusive {d['INCONCLUSIVE']}")
    print("  stage diagnosis (flagged on real vs fake; balanced accuracy, 0.5 = no information):")
    for st, d in s["stage_diagnosis"].items():
        ba = d["balanced_accuracy"]
        print(f"    {st[:52]:<52} real {_p(d['flagged_real'])}  fake {_p(d['flagged_fake'])}  BA {'n/a' if ba is None else f'{ba:.2f}'}")


def _provenance() -> dict:
    def git(*a):
        try:
            return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    import torch

    from app.config import settings

    return {"utc_time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git_commit": git("rev-parse", "HEAD"),
            "git_branch": git("branch", "--show-current"), "tracked_changes": bool(git("status", "--porcelain", "-uno")),
            "python": platform.python_version(), "torch": torch.__version__, "device": settings.device,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "settings": {k: getattr(settings, k) for k in ("commfor_enabled", "commfor_weight", "face_model_in_verdict",
                                                           "audio_pellav2_in_verdict", "audio_model_source", "fake_threshold",
                                                           "uncertain_band")}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    img = sub.add_parser("score-image")
    img.add_argument("--manifest", type=Path, required=True)
    img.add_argument("--root", type=Path, required=True)
    aud = sub.add_parser("score-audio")
    group = aud.add_mutually_exclusive_group(required=True)
    group.add_argument("--asvspoof-root", type=Path)
    group.add_argument("--asvspoof5-root", type=Path)
    group.add_argument("--data", type=Path)
    aud.add_argument("--per-class", type=int, default=300)
    aud.add_argument("--seed", type=int, default=0)
    for p in (img, aud):
        p.add_argument("--name", required=True)
        p.add_argument("--split", default=None, help="score only manifest rows with this split")
    summ = sub.add_parser("summarise")
    for p in (img, aud, summ):
        p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if args.cmd == "score-image":
        items = image_items(args.manifest, args.root)
        if args.split:
            items = [i for i in items if i.get("split") == args.split]
        score("image", items, args.out_dir, args.name)
        return 0
    if args.cmd == "score-audio":
        score("audio", audio_items(args), args.out_dir, args.name)
        return 0

    summary = {"script": "backend/scripts/eval_end_to_end.py", "provenance": _provenance(), "sets": {}}
    for path in sorted(args.out_dir.glob("*.jsonl")):
        if path.name.endswith(".errors.jsonl"):
            continue
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        errors = args.out_dir / f"{path.stem}.errors.jsonl"
        summary["sets"][path.stem] = {**summarise_set(rows),
                                      "errors": len(errors.read_text().splitlines()) if errors.is_file() else 0}
        print_set(path.stem, summary["sets"][path.stem])
    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"\nWrote {args.out_dir / 'summary.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
