"""ASVspoof 2019 metrics: EER and minimum normalised t-DCF.

Implements the procedure of the ASVspoof 2019 evaluation plan (Section 5,
Table 2), with the same threshold enumeration as the organisers' scoring code
(``compute_det_curve`` / ``compute_eer`` / ``compute_tDCF_legacy`` in the
official package) so the numbers are comparable with published results:

* scores are countermeasure (CM) scores where **higher means more likely bona
  fide**;
* the miss rate at threshold s counts bona fide trials with score <= s, the
  false-alarm rate counts spoof trials with score > s; every sorted score is a
  candidate threshold (ties are not merged, as in the official code);
* EER is the mean of miss and false-alarm rates where their absolute
  difference is smallest;
* the ASV operating point is the ASV EER threshold on target vs nontarget
  scores; min t-DCF is normalised by min(C1, C2).

``backend/tests/test_asvspoof_metrics.py`` checks these functions against hand
computed cases and, when a copy is available locally, against the official
code itself.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

# Table 2 of the ASVspoof 2019 evaluation plan (logical access).
COST_MODEL_2019 = {
    "Ptar": 0.9405,
    "Pnon": 0.0095,
    "Pspoof": 0.05,
    "Cmiss_asv": 1.0,
    "Cfa_asv": 10.0,
    "Cmiss_cm": 1.0,
    "Cfa_cm": 10.0,
}

ASV_SCORE_FILES = {
    "dev": "ASVspoof2019_LA_asv_scores/ASVspoof2019.LA.asv.dev.gi.trl.scores.txt",
    "eval": "ASVspoof2019_LA_asv_scores/ASVspoof2019.LA.asv.eval.gi.trl.scores.txt",
}


def det_curve(target_scores, nontarget_scores) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Miss and false-alarm rates at every candidate threshold.

    ``target`` is the positive class (bona fide for a CM, target speaker for
    ASV). Returns ``(p_miss, p_fa, thresholds)`` with one more entry than the
    number of scores: the first threshold lies below every score.
    """
    target = np.asarray(target_scores, dtype=np.float64).ravel()
    nontarget = np.asarray(nontarget_scores, dtype=np.float64).ravel()
    if target.size == 0 or nontarget.size == 0:
        raise ValueError("both classes need at least one score")
    scores = np.concatenate([target, nontarget])
    is_target = np.concatenate([np.ones(target.size), np.zeros(nontarget.size)])
    order = np.argsort(scores, kind="mergesort")
    is_target = is_target[order]

    targets_at_or_below = np.cumsum(is_target)
    nontargets_at_or_below = np.arange(1, scores.size + 1) - targets_at_or_below
    p_miss = np.concatenate([[0.0], targets_at_or_below / target.size])
    p_fa = np.concatenate([[1.0], (nontarget.size - nontargets_at_or_below) / nontarget.size])
    thresholds = np.concatenate([[scores[order[0]] - 0.001], scores[order]])
    return p_miss, p_fa, thresholds


def eer(target_scores, nontarget_scores) -> tuple[float, float]:
    """Equal error rate (fraction, not percent) and its threshold."""
    p_miss, p_fa, thresholds = det_curve(target_scores, nontarget_scores)
    index = int(np.argmin(np.abs(p_miss - p_fa)))
    return float((p_miss[index] + p_fa[index]) / 2.0), float(thresholds[index])


def asv_error_rates(tar_asv, non_asv, spoof_asv, threshold: float) -> tuple[float, float, float]:
    """ASV false-alarm, miss and spoof-miss rates at a fixed ASV threshold."""
    tar_asv, non_asv, spoof_asv = (np.asarray(a, dtype=np.float64) for a in (tar_asv, non_asv, spoof_asv))
    if spoof_asv.size == 0:
        raise ValueError("t-DCF needs ASV scores of spoofed trials")
    p_fa = float(np.mean(non_asv >= threshold))
    p_miss = float(np.mean(tar_asv < threshold))
    p_miss_spoof = float(np.mean(spoof_asv < threshold))
    return p_fa, p_miss, p_miss_spoof


def min_tdcf(
    bonafide_cm,
    spoof_cm,
    tar_asv,
    non_asv,
    spoof_asv,
    cost_model: dict = COST_MODEL_2019,
) -> dict:
    """Minimum normalised t-DCF (ASVspoof 2019 definition) with its ingredients."""
    bonafide_cm = np.asarray(bonafide_cm, dtype=np.float64)
    spoof_cm = np.asarray(spoof_cm, dtype=np.float64)
    combined = np.concatenate([bonafide_cm, spoof_cm])
    if not np.isfinite(combined).all():
        raise ValueError("CM scores contain NaN or inf")
    if np.unique(combined).size < 3:
        raise ValueError("t-DCF needs soft CM scores, not hard decisions")
    priors = cost_model["Ptar"] + cost_model["Pnon"] + cost_model["Pspoof"]
    if abs(priors - 1.0) > 1e-10:
        raise ValueError("priors must sum to one")

    asv_eer, asv_threshold = eer(tar_asv, non_asv)
    p_fa_asv, p_miss_asv, p_miss_spoof_asv = asv_error_rates(tar_asv, non_asv, spoof_asv, asv_threshold)

    c1 = cost_model["Ptar"] * (cost_model["Cmiss_cm"] - cost_model["Cmiss_asv"] * p_miss_asv) - (
        cost_model["Pnon"] * cost_model["Cfa_asv"] * p_fa_asv
    )
    c2 = cost_model["Cfa_cm"] * cost_model["Pspoof"] * (1.0 - p_miss_spoof_asv)
    if c1 < 0 or c2 < 0:
        raise ValueError(f"negative t-DCF weights (C1={c1}, C2={c2}); check the ASV error rates")

    p_miss_cm, p_fa_cm, thresholds = det_curve(bonafide_cm, spoof_cm)
    curve = (c1 * p_miss_cm + c2 * p_fa_cm) / min(c1, c2)
    index = int(np.argmin(curve))
    return {
        "min_tdcf": float(curve[index]),
        "cm_threshold": float(thresholds[index]),
        "C1": float(c1),
        "C2": float(c2),
        "asv_eer": asv_eer,
        "asv_threshold": asv_threshold,
        "asv_p_fa": p_fa_asv,
        "asv_p_miss": p_miss_asv,
        "asv_p_miss_spoof": p_miss_spoof_asv,
    }


def load_asv_scores(path: Path) -> dict[str, np.ndarray]:
    """Organisers' ASV scores: columns source (bonafide or attack id), key, score."""
    sources, keys, scores = [], [], []
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            parts = line.split()
            if not parts:
                continue
            if len(parts) != 3:
                raise ValueError(f"{Path(path).name}:{line_no}: expected 3 columns, got {len(parts)}")
            if parts[1] not in {"target", "nontarget", "spoof"}:
                raise ValueError(f"{Path(path).name}:{line_no}: unknown key '{parts[1]}'")
            sources.append(parts[0])
            keys.append(parts[1])
            scores.append(float(parts[2]))
    return {"source": np.array(sources), "key": np.array(keys), "score": np.array(scores, dtype=np.float64)}


def evaluate_scores(
    scores,
    labels,
    attack_ids,
    asv: dict[str, np.ndarray] | None = None,
) -> dict:
    """Pooled and per-attack metrics for one score file.

    ``labels``: 1 = spoof, 0 = bona fide. ``scores``: higher = more bona fide.
    Per-attack EER compares all bona fide trials with the spoofed trials of
    one attack. t-DCF is included only when ASV scores are supplied; it is
    never approximated.
    """
    from ml.evaluation.metrics import roc_auc

    scores = np.asarray(scores, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.int64)
    attack_ids = np.asarray(attack_ids)
    bona = scores[labels == 0]
    spoof = scores[labels == 1]

    pooled_eer, pooled_threshold = eer(bona, spoof)
    result: dict = {
        "n_bonafide": int(bona.size),
        "n_spoof": int(spoof.size),
        "eer": pooled_eer,
        "eer_threshold": pooled_threshold,
        # AUC of separating bona fide (positive) from spoof with these scores.
        "auc_bonafide_vs_spoof": roc_auc((labels == 0).astype(int), scores),
        "per_attack": {},
    }
    for attack in sorted({a for a, lab in zip(attack_ids, labels, strict=True) if lab == 1}):
        attack_scores = scores[(labels == 1) & (attack_ids == attack)]
        attack_eer, _ = eer(bona, attack_scores)
        result["per_attack"][attack] = {"n_spoof": int(attack_scores.size), "eer": attack_eer}

    if asv is None:
        result["min_tdcf"] = None
        result["tdcf_note"] = "ASV score file not available; t-DCF not computed"
        return result

    tar = asv["score"][asv["key"] == "target"]
    non = asv["score"][asv["key"] == "nontarget"]
    spoof_asv = asv["score"][asv["key"] == "spoof"]
    pooled = min_tdcf(bona, spoof, tar, non, spoof_asv)
    result["min_tdcf"] = pooled["min_tdcf"]
    result["tdcf_details"] = pooled
    for attack, entry in result["per_attack"].items():
        attack_asv = asv["score"][(asv["key"] == "spoof") & (asv["source"] == attack)]
        if attack_asv.size == 0:
            entry["min_tdcf"] = None
            continue
        attack_scores = scores[(labels == 1) & (attack_ids == attack)]
        entry["min_tdcf"] = min_tdcf(bona, attack_scores, tar, non, attack_asv)["min_tdcf"]
    return result
