"""Measure pellav2 against the served ASVspoof LCNN on the same clips.

Sets (either or both):
  --asvspoof-root D  the ASVspoof 2019 LA folder (holding ASVspoof2019_LA_cm_protocols/
                     and ASVspoof2019_LA_{dev,eval}/flac/). Samples --per-class bona fide
                     and spoof clips (spoof spread evenly over the attacks) from eval,
                     and --dev-per-class of each from dev, with a fixed seed.
  --data D           D/real/<source>/ (label 0) and D/fake/<generator>/ (label 1),
                     any audio format load_audio reads.

Each file is read with app.ml.preprocessing.load_audio at 16 kHz and scored by
pellav2 (score_clip: mean of up to AUDIO_PELLAV2_MAX_WINDOWS 4 s windows) and by
the served LCNN (score_lcnn_asvspoof: calibrated probability).

Reported per model and set: AUC and EER (bootstrap 95% CIs), the EER threshold,
accuracy / real-flagged rate / fakes-missed rate at 0.5 (the authors' threshold)
and, for information, at the dev EER threshold, and the detection rate per
attack or folder. Metrics use
ml/evaluation/metrics.py (numpy only), the code the LCNN results came from.

--codecs re-encodes a --codec-per-class subsample of the eval sample with each
condition of ml/preprocessing/audio_codecs.py (MP3, AAC, Opus, resampling round
trips; the conditions behind KNOWN_ISSUES #14) and scores both models on every copy.

--write-verdict-config fixes the pellav2 verdict thresholds on the dev sample
(rule in DEV_RULE) and writes them to AUDIO_PELLAV2_CONFIG_FILE; eval and
--data are never used to choose them.

Run from backend/:
  python scripts/eval_audio_detector.py --asvspoof-root C:/deepsentinel_data/ASVspoof2019/LA --write-verdict-config
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

BACKEND = Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(REPO))

from app.config import settings  # noqa: E402
from app.ml.audio import pellav2 as pv  # noqa: E402
from app.ml.base import resolve_device  # noqa: E402
from app.ml.preprocessing import load_audio  # noqa: E402
from ml.evaluation.metrics import equal_error_rate, roc_auc, roc_curve  # noqa: E402

AUDIO_SUFFIXES = {".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".webm", ".wma", ".aiff", ".aif"}
DEFAULT_OUT = REPO / "evaluation" / "AUDIO-PELLAV2-01"
BOOTSTRAP = 1000
AUTHORS_THRESHOLD = 0.5  # pellav2_infer.py: FAKE if p >= 0.5
DEV_RULE = (
    "threshold = 0.5, the authors' operating point (pellav2_infer.py), fixed before any scoring; the ASVspoof "
    "2019 LA dev sample only checks it (its EER threshold is reported, not used: the scores saturate near 0 and "
    "1, so the EER point falls anywhere in the gap between the classes); inconclusive band = the platform "
    "default UNCERTAIN_BAND (0.08), fixed in advance and not tuned on audio"
)


# --------------------------------------------------------------------------- data


def _protocol(root: Path, split: str) -> list[dict]:
    name = {"dev": "ASVspoof2019.LA.cm.dev.trl.txt", "eval": "ASVspoof2019.LA.cm.eval.trl.txt"}[split]
    rows = []
    for line in (root / "ASVspoof2019_LA_cm_protocols" / name).read_text().split("\n"):
        parts = line.split()
        if len(parts) == 5:
            speaker, utt, _, attack, key = parts
            rows.append({
                "path": root / f"ASVspoof2019_LA_{split}" / "flac" / f"{utt}.flac",
                "id": utt, "label": int(key == "spoof"), "group": attack if key == "spoof" else "bonafide",
                "speaker": speaker,
            })
    return rows


def sample_asvspoof(root: Path, split: str, per_class: int, seed: int) -> list[dict]:
    """``per_class`` bona fide clips at random; ``per_class`` spoof clips spread evenly over the attacks."""
    rows = _protocol(root, split)
    rng = np.random.default_rng(seed)
    bona = [r for r in rows if r["label"] == 0]
    picked = [bona[i] for i in rng.choice(len(bona), min(per_class, len(bona)), replace=False)]
    by_attack: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["label"] == 1:
            by_attack[r["group"]].append(r)
    attacks = sorted(by_attack)
    quota = [per_class // len(attacks) + (i < per_class % len(attacks)) for i in range(len(attacks))]
    for attack, n in zip(attacks, quota):
        pool = by_attack[attack]
        picked += [pool[i] for i in rng.choice(len(pool), min(n, len(pool)), replace=False)]
    return [{**r, "set": f"asvspoof2019_la_{split}"} for r in picked]


def collect_folders(data: Path) -> tuple[list[dict], list[str]]:
    items, missing = [], []
    for split, label in (("real", 0), ("fake", 1)):
        parent = data / split
        groups = sorted(d for d in parent.iterdir() if d.is_dir()) if parent.is_dir() else []
        if not groups:
            missing.append(f"{split}/")
        for group in groups:
            files = sorted(p for p in group.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_SUFFIXES)
            if not files:
                missing.append(f"{split}/{group.name}")
            items += [{"path": p, "id": p.relative_to(data).as_posix(), "label": label,
                       "group": f"{split}/{group.name}", "set": "own_clips"} for p in files]
    return items, missing


# --------------------------------------------------------------------------- scoring


def _lcnn_scorer():
    try:
        from app.ml.audio.lcnn_asvspoof import load_verdict_config, score_lcnn_asvspoof

        config = load_verdict_config()
        return score_lcnn_asvspoof, config
    except Exception as exc:
        print(f"WARNING: the served LCNN is unavailable ({exc}); only pellav2 is scored.")
        return None, None


def score_all(items: list[dict], loaded, lcnn_score, max_windows: int) -> list[dict]:
    records = []
    for n, item in enumerate(items, 1):
        record = {k: (str(v) if isinstance(v, Path) else v) for k, v in item.items()}
        try:
            wave, sr = load_audio(item["path"], pv.SAMPLE_RATE)
        except Exception as exc:
            record["error"] = f"load failed: {exc}"
            records.append(record)
            continue
        record["seconds"] = round(len(wave) / sr, 3)
        t0 = time.perf_counter()
        clip = pv.score_clip(wave, sr, max_windows, loaded=loaded)
        record["pellav2_seconds"] = round(time.perf_counter() - t0, 4)
        record["pellav2"] = None if clip is None else round(clip["prob"], 6)
        record["pellav2_max"] = None if clip is None else round(clip["max_prob"], 6)
        record["pellav2_windows"] = None if clip is None else clip["window_probs"]
        if lcnn_score is not None:
            try:
                record["lcnn"] = round(float(lcnn_score(wave, sr)["probability"]), 6)
            except Exception as exc:
                record["lcnn"] = None
                record["lcnn_error"] = str(exc)
        records.append(record)
        if n % 200 == 0 or n == len(items):
            print(f"  {n}/{len(items)}", flush=True)
    return records


def score_codecs(items: list[dict], conditions: list[str], loaded, lcnn_score, max_windows: int) -> list[dict]:
    """Every item re-encoded with every condition, scored by both models (16 kHz decode, as in KNOWN_ISSUES #14)."""
    from ml.preprocessing.audio_codecs import encode_decode, ffmpeg_exe

    exe, records = ffmpeg_exe(), []
    total = len(items) * len(conditions)
    for i, item in enumerate(items):
        for condition in conditions:
            record = {"id": item["id"], "label": item["label"], "group": item["group"], "condition": condition}
            try:
                wave = encode_decode(Path(item["path"]), condition, exe=exe)
            except Exception as exc:
                record["error"] = f"encode failed: {exc}"
                records.append(record)
                continue
            clip = pv.score_clip(wave, pv.SAMPLE_RATE, max_windows, loaded=loaded)
            record["pellav2"] = None if clip is None else round(clip["prob"], 6)
            if lcnn_score is not None:
                try:
                    record["lcnn"] = round(float(lcnn_score(wave, pv.SAMPLE_RATE)["probability"]), 6)
                except Exception as exc:
                    record["lcnn"], record["lcnn_error"] = None, str(exc)
            records.append(record)
        done = (i + 1) * len(conditions)
        if done % 500 < len(conditions) or done == total:
            print(f"  {done}/{total}", flush=True)
    return records


def codec_summary(records: list[dict], conditions: list[str], seed: int) -> dict:
    out = {}
    for condition in ["original", *conditions]:
        rows = [r for r in records if r["condition"] == condition]
        out[condition] = {m: evaluate(rows, m, {"0.5": 0.5}, seed) for m in ("pellav2", "lcnn")}
    return out


def print_codecs(summary: dict) -> None:
    print("\n== codec robustness (eval subsample; at 0.5: real flagged / fakes caught; AUC)")
    for condition, models in summary.items():
        cells = []
        for m, r in models.items():
            if r:
                a = r["at"]["0.5"]
                cells.append(f"{m:<8} real flagged {_fmt(a['real_flagged_rate'])}  fakes caught "
                             f"{_fmt(None if a['fakes_missed_rate'] is None else 1 - a['fakes_missed_rate'])}  AUC {_fmt(r.get('auc'), False)}")
        print(f"  {condition:<20} " + "   |   ".join(cells))


# --------------------------------------------------------------------------- metrics


def _rates(y: np.ndarray, s: np.ndarray, threshold: float) -> dict:
    flagged = s >= threshold
    real, fake = y == 0, y == 1
    return {
        "threshold": threshold,
        "accuracy": float((flagged == fake).mean()),
        "real_flagged_rate": float(flagged[real].mean()) if real.any() else None,
        "fakes_missed_rate": float((~flagged[fake]).mean()) if fake.any() else None,
    }


def _bootstrap(y: np.ndarray, s: np.ndarray, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]
    aucs, eers = [], []
    for _ in range(BOOTSTRAP):
        idx = np.r_[rng.choice(pos, pos.size), rng.choice(neg, neg.size)]  # stratified resample
        aucs.append(roc_auc(y[idx], s[idx]))
        eers.append(equal_error_rate(y[idx], s[idx])[0])
    return {"auc_ci95": [float(np.percentile(aucs, 2.5)), float(np.percentile(aucs, 97.5))],
            "eer_ci95": [float(np.percentile(eers, 2.5)), float(np.percentile(eers, 97.5))]}


def evaluate(records: list[dict], key: str, thresholds: dict[str, float], seed: int) -> dict | None:
    rows = [r for r in records if r.get(key) is not None]
    if not rows:
        return None
    y = np.array([r["label"] for r in rows], dtype=int)
    s = np.array([r[key] for r in rows], dtype=float)
    out: dict = {"n_real": int((y == 0).sum()), "n_fake": int((y == 1).sum())}
    if 0 < y.sum() < y.size:
        eer, eer_threshold = equal_error_rate(y, s)
        out.update(auc=roc_auc(y, s), eer=eer, eer_threshold=eer_threshold, **_bootstrap(y, s, seed))
    out["at"] = {name: _rates(y, s, t) for name, t in thresholds.items()}
    groups: dict[str, dict] = {}
    for g in sorted({r["group"] for r in rows}):
        gs = np.array([r[key] for r in rows if r["group"] == g])
        label = next(r["label"] for r in rows if r["group"] == g)
        groups[g] = {"label": label, "n": int(gs.size),
                     **{f"{'flagged' if label == 0 else 'caught'}_at_{name}": float((gs >= t).mean())
                        for name, t in thresholds.items()}}
    out["per_group"] = groups
    return out


def dev_verdict_config(records: list[dict], loaded) -> dict:
    rows = [r for r in records if r.get("pellav2") is not None]
    y = np.array([r["label"] for r in rows]); s = np.array([r["pellav2"] for r in rows])
    eer, eer_threshold = equal_error_rate(y, s)
    threshold = AUTHORS_THRESHOLD
    dev_at_threshold = _rates(y, s, threshold)
    # The platform default, not this machine's UNCERTAIN_BAND: a frozen rule must not depend on a local .env.
    band = float(type(settings).model_fields["uncertain_band"].default)
    low, high = max(threshold - band, 0.0), min(threshold + band, 1.0)
    return {
        "purpose": "pellav2 audio verdict rule (AUDIO_PELLAV2_IN_VERDICT=true), fixed on ASVspoof 2019 LA dev only",
        "model": pv.MODEL_LABEL,
        "hub_repo": pv.HUB_REPO,
        "revision": loaded.metadata.get("revision"),
        "weights_sha256": loaded.metadata.get("weights_sha256"),
        "max_windows": settings.audio_pellav2_max_windows,
        "threshold": float(threshold),
        "threshold_rule": DEV_RULE,
        "inconclusive_band": band,
        "authentic_below": float(low),
        "flagged_at_or_above": float(high),
        "decision_rule": f"pellav2 probability p: authentic if p < {low:.4f}, flagged (AI-generated) if p >= {high:.4f}, "
                         "inconclusive otherwise; heuristic signals carry no weight",
        "dev_sample": {"n_bonafide": int((y == 0).sum()), "n_spoof": int((y == 1).sum()), "eer": float(eer),
                       "eer_threshold_information_only": float(eer_threshold), "at_threshold": dev_at_threshold,
                       "note": "dev holds only the training attacks A01-A06; these numbers are optimistic"},
    }


# --------------------------------------------------------------------------- output


def _fmt(v, pct=True) -> str:
    return "   n/a" if v is None else (f"{100 * v:5.1f}%" if pct else f"{v:.4f}")


def print_table(name: str, results: dict) -> None:
    print(f"\n== {name}")
    print(f"  {'model':<9} {'n real/fake':>12} {'AUC':>7} {'EER':>7}  {'EER 95% CI':>15}   "
          + "   ".join(f"{'@' + k:>24}" for k in next(iter(r for r in results.values() if r))["at"]))
    for model, r in results.items():
        if r is None:
            continue
        ci = f"{100 * r['eer_ci95'][0]:.1f}-{100 * r['eer_ci95'][1]:.1f}%" if "eer_ci95" in r else "n/a"
        at = "   ".join(f"acc {_fmt(a['accuracy'])} FP {_fmt(a['real_flagged_rate'])} FN {_fmt(a['fakes_missed_rate'])}"
                       for a in r["at"].values())
        print(f"  {model:<9} {r['n_real']:>5}/{r['n_fake']:<6} {_fmt(r.get('auc'), False):>7} {_fmt(r.get('eer')):>7}  {ci:>15}   {at}")
    print("  per group (real: flagged; fake: caught):")
    groups = sorted({g for r in results.values() if r for g in r["per_group"]})
    for g in groups:
        cells = []
        for model, r in results.items():
            if r and g in r["per_group"]:
                d = r["per_group"][g]
                cells.append(f"{model} " + " ".join(f"{k.split('_at_')[1]} {_fmt(v)}" for k, v in d.items() if "_at_" in k))
        n = next(r["per_group"][g]["n"] for r in results.values() if r and g in r["per_group"])
        print(f"    {g:<22} n={n:<5} " + "  |  ".join(cells))


def save_roc(path: Path, sets: dict[str, list[dict]]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(sets), figsize=(5 * len(sets), 4.5), squeeze=False)
    for ax, (name, records) in zip(axes[0], sets.items()):
        for key, label in (("pellav2", pv.MODEL_LABEL), ("lcnn", "LCNN (served)")):
            rows = [r for r in records if r.get(key) is not None]
            y = np.array([r["label"] for r in rows]); s = np.array([r[key] for r in rows])
            if rows and 0 < y.sum() < y.size:
                fpr, tpr, _ = roc_curve(y, s)
                ax.plot(fpr, tpr, label=f"{label} (AUC {roc_auc(y, s):.3f})")
        ax.plot([0, 1], [0, 1], ls=":", c="grey")
        ax.set(title=name, xlabel="real clips flagged (FPR)", ylabel="fakes caught (TPR)")
        ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _provenance(loaded) -> dict:
    import torch
    import transformers

    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    return {
        "utc_time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command_line": sys.argv,
        "git_commit": git("rev-parse", "HEAD"),
        "git_branch": git("branch", "--show-current"),
        "git_dirty": bool(git("status", "--porcelain")),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "device": loaded.device,
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() and loaded.device.startswith("cuda") else None,
        "pellav2": loaded.metadata,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--asvspoof-root", type=Path, help="ASVspoof 2019 LA folder")
    parser.add_argument("--data", type=Path, help="folder with real/<source>/ and fake/<generator>/")
    parser.add_argument("--per-class", type=int, default=300, help="eval clips per class (default 300)")
    parser.add_argument("--dev-per-class", type=int, default=None, help="dev clips per class (default: --per-class)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-windows", type=int, default=settings.audio_pellav2_max_windows)
    parser.add_argument("--no-lcnn", action="store_true", help="score pellav2 only")
    parser.add_argument("--codecs", action="store_true", help="also score re-encoded copies (needs --asvspoof-root)")
    parser.add_argument("--codec-per-class", type=int, default=200, help="eval clips per class re-encoded (default 200)")
    parser.add_argument("--write-verdict-config", action="store_true",
                        help=f"fix pellav2 thresholds on the dev sample and write {Path(settings.audio_pellav2_config_file).name}")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if not args.asvspoof_root and not args.data:
        parser.error("give --asvspoof-root, --data, or both")
    if args.write_verdict_config and not args.asvspoof_root:
        parser.error("--write-verdict-config needs --asvspoof-root (thresholds are fixed on its dev split)")

    loaded = pv.get_pellav2()
    if loaded is None:
        print("ERROR: pellav2 could not be loaded (see the log above).")
        return 1
    lcnn_score, lcnn_config = (None, None) if args.no_lcnn else _lcnn_scorer()
    print(f"pellav2 on {resolve_device()}; LCNN {'on' if lcnn_score else 'off'}")

    sets: dict[str, list[dict]] = {}
    missing: list[str] = []
    if args.asvspoof_root:
        for split, n in (("dev", args.dev_per_class or args.per_class), ("eval", args.per_class)):
            items = sample_asvspoof(args.asvspoof_root, split, n, args.seed)
            print(f"Scoring ASVspoof 2019 LA {split}: {len(items)} clips")
            sets[f"asvspoof2019_la_{split}"] = score_all(items, loaded, lcnn_score, args.max_windows)
    codec = None
    if args.codecs and args.asvspoof_root:
        from ml.preprocessing.audio_codecs import ALL_CONDITIONS

        rng = np.random.default_rng(args.seed + 1)
        sub = []
        for label in (0, 1):
            pool = [r for r in sets["asvspoof2019_la_eval"] if r["label"] == label and "error" not in r]
            sub += [pool[i] for i in rng.choice(len(pool), min(args.codec_per_class, len(pool)), replace=False)]
        print(f"Codec robustness: {len(sub)} eval clips x {len(ALL_CONDITIONS)} conditions")
        originals = [{"id": r["id"], "label": r["label"], "group": r["group"], "condition": "original",
                      "pellav2": r.get("pellav2"), "lcnn": r.get("lcnn")} for r in sub]
        codec_records = originals + score_codecs(sub, ALL_CONDITIONS, loaded, lcnn_score, args.max_windows)
        codec = {"conditions": ALL_CONDITIONS, "n_per_class": args.codec_per_class,
                 "decode": "ml/preprocessing/audio_codecs.encode_decode (ffmpeg to 16 kHz PCM, or soxr/ffmpeg round trip)",
                 "summary": codec_summary(codec_records, ALL_CONDITIONS, args.seed), "files": codec_records}
    if args.data:
        items, missing = collect_folders(args.data)
        for m in missing:
            print(f"WARNING: no audio in {args.data / m}; left out.")
        if items:
            print(f"Scoring {args.data}: {len(items)} clips")
            sets["own_clips"] = score_all(items, loaded, lcnn_score, args.max_windows)

    verdict_config = None
    thresholds = {"0.5": 0.5}
    if "asvspoof2019_la_dev" in sets:
        verdict_config = dev_verdict_config(sets["asvspoof2019_la_dev"], loaded)
        thresholds["dev_eer_thr"] = verdict_config["dev_sample"]["eer_threshold_information_only"]
    results: dict[str, dict] = {}
    for name, records in sets.items():
        results[name] = {
            "pellav2": evaluate(records, "pellav2", thresholds, args.seed),
            "pellav2_max": evaluate(records, "pellav2_max", {"0.5": 0.5}, args.seed),
            "lcnn": evaluate(records, "lcnn", {"0.5": 0.5}, args.seed) if lcnn_score else None,
        }
        print_table(name, {k: v for k, v in results[name].items() if k != "pellav2_max"})

    if codec:
        print_codecs(codec["summary"])

    latency = np.array([r["pellav2_seconds"] for rs in sets.values() for r in rs if "pellav2_seconds" in r])
    args.out_dir.mkdir(parents=True, exist_ok=True)
    save_roc(args.out_dir / "roc.png", sets)
    out = {
        "script": "backend/scripts/eval_audio_detector.py",
        "provenance": _provenance(loaded),
        "score_convention": "higher = more likely fake; label 1 = spoof / fake",
        "sampling": {"seed": args.seed, "eval_per_class": args.per_class,
                     "dev_per_class": args.dev_per_class or args.per_class,
                     "spoof_sampling": "spread evenly over the attacks of the split"},
        "max_windows": args.max_windows,
        "clip_score": "pellav2: mean of the window probabilities; pellav2_max: highest window; lcnn: calibrated probability",
        "lcnn_verdict_rule": None if lcnn_config is None else lcnn_config.get("decision_rule"),
        "pellav2_dev_verdict_config": verdict_config,
        "missing_or_empty_folders": missing,
        "latency_seconds_per_clip": None if latency.size == 0 else {
            "device": loaded.device, "p50": float(np.percentile(latency, 50)), "p95": float(np.percentile(latency, 95)),
            "n": int(latency.size), "note": "pellav2 forward pass incl. preprocessing, file decoding excluded"},
        "results": results,
        "codec_robustness": codec,
        "files": sets,
    }
    (args.out_dir / "results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nWrote {args.out_dir / 'results.json'} and roc.png")
    if args.write_verdict_config and verdict_config:
        path = Path(settings.audio_pellav2_config_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({**verdict_config, "frozen_utc": out["provenance"]["utc_time"],
                                    "source": "evaluation/AUDIO-PELLAV2-01/results.json"}, indent=2), encoding="utf-8")
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
