"""Statistics for the paper: confidence intervals and paired tests.

* ``bootstrap_auc_ci``: percentile interval of ROC AUC from a stratified
  bootstrap (classes resampled separately, so every resample has both).
* ``delong_test``: DeLong et al. (1988) test for two correlated AUCs computed
  on the same items, using the fast midrank algorithm of Sun & Xu (2014).
* ``wilson_interval``: Wilson score interval for a proportion.
* ``expected_calibration_error``: equal-width-bin ECE and the reliability table.
* ``mcnemar_test``: exact (binomial) McNemar test for paired binary outcomes.
"""

from __future__ import annotations

import math

import numpy as np

from ml.evaluation.metrics import roc_auc

Z95 = 1.959963984540054


def wilson_interval(successes: int, total: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval; (0, 1) when ``total`` is zero."""
    if total <= 0:
        return 0.0, 1.0
    p = successes / total
    denom = 1.0 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def rate_with_ci(flags) -> dict:
    flags = np.asarray(flags, dtype=bool)
    k, n = int(flags.sum()), int(flags.size)
    low, high = wilson_interval(k, n)
    return {"k": k, "n": n, "rate": k / n if n else None, "ci95": [low, high]}


def bootstrap_auc_ci(labels, scores, n_resamples: int = 2000, seed: int = 0, alpha: float = 0.05) -> dict:
    """AUC with a stratified percentile bootstrap interval."""
    labels = np.asarray(labels).astype(int).ravel()
    scores = np.asarray(scores, dtype=np.float64).ravel()
    pos, neg = np.flatnonzero(labels == 1), np.flatnonzero(labels == 0)
    if pos.size == 0 or neg.size == 0:
        raise ValueError("AUC needs both classes")
    rng = np.random.default_rng(seed)
    point = roc_auc(labels, scores)
    samples = np.empty(n_resamples)
    for b in range(n_resamples):
        idx = np.concatenate([rng.choice(pos, pos.size), rng.choice(neg, neg.size)])
        samples[b] = roc_auc(labels[idx], scores[idx])
    low, high = np.quantile(samples, [alpha / 2, 1 - alpha / 2])
    return {"auc": float(point), "ci95": [float(low), float(high)], "n_resamples": n_resamples, "seed": seed,
            "n_pos": int(pos.size), "n_neg": int(neg.size)}


def _midrank(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    n = values.size
    ranks = np.empty(n, dtype=np.float64)
    i = 0
    while i < n:
        j = i
        while j < n and sorted_values[j] == sorted_values[i]:
            j += 1
        ranks[i:j] = 0.5 * (i + j - 1) + 1.0
        i = j
    out = np.empty(n, dtype=np.float64)
    out[order] = ranks
    return out


def delong_covariance(labels, score_columns) -> tuple[np.ndarray, np.ndarray]:
    """AUCs of several score columns on the same items and their DeLong covariance."""
    labels = np.asarray(labels).astype(int).ravel()
    columns = np.atleast_2d(np.asarray(score_columns, dtype=np.float64))
    pos = columns[:, labels == 1]
    neg = columns[:, labels == 0]
    m, n = pos.shape[1], neg.shape[1]
    if m < 2 or n < 2:
        raise ValueError("DeLong needs at least two items of each class")
    k = columns.shape[0]
    tx = np.vstack([_midrank(pos[r]) for r in range(k)])
    ty = np.vstack([_midrank(neg[r]) for r in range(k)])
    tz = np.vstack([_midrank(np.concatenate([pos[r], neg[r]])) for r in range(k)])
    aucs = tz[:, :m].sum(axis=1) / (m * n) - (m + 1.0) / (2.0 * n)
    v01 = (tz[:, :m] - tx) / n
    v10 = 1.0 - (tz[:, m:] - ty) / m
    cov = np.atleast_2d(np.cov(v01)) / m + np.atleast_2d(np.cov(v10)) / n
    return aucs, cov


def delong_test(labels, scores_a, scores_b) -> dict:
    """Two-sided DeLong test of AUC(a) = AUC(b) on the same items."""
    from scipy.stats import norm

    aucs, cov = delong_covariance(labels, np.vstack([scores_a, scores_b]))
    diff = float(aucs[0] - aucs[1])
    var = float(cov[0, 0] + cov[1, 1] - 2 * cov[0, 1])
    if var <= 1e-15:
        p = 1.0 if abs(diff) < 1e-12 else 0.0
        z = 0.0 if p == 1.0 else math.copysign(math.inf, diff)
    else:
        z = diff / math.sqrt(var)
        p = float(2 * norm.sf(abs(z)))
    return {"auc_a": float(aucs[0]), "auc_b": float(aucs[1]), "difference": diff, "z": z, "p_value": p}


def expected_calibration_error(labels, probabilities, n_bins: int = 15) -> dict:
    """ECE over equal-width probability bins, plus the per-bin reliability table."""
    labels = np.asarray(labels, dtype=np.float64).ravel()
    probs = np.asarray(probabilities, dtype=np.float64).ravel()
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_index = np.clip(np.digitize(probs, edges[1:-1], right=False), 0, n_bins - 1)
    table, ece = [], 0.0
    for b in range(n_bins):
        mask = bin_index == b
        count = int(mask.sum())
        if count:
            confidence, accuracy = float(probs[mask].mean()), float(labels[mask].mean())
            ece += count / probs.size * abs(accuracy - confidence)
        else:
            confidence = accuracy = None
        table.append({"bin": [float(edges[b]), float(edges[b + 1])], "count": count,
                      "mean_probability": confidence, "fraction_positive": accuracy})
    return {"ece": float(ece), "n_bins": n_bins, "bins": table}


def mcnemar_test(correct_a, correct_b) -> dict:
    """Exact McNemar test on paired correct/incorrect outcomes."""
    from scipy.stats import binomtest

    a = np.asarray(correct_a, dtype=bool)
    b = np.asarray(correct_b, dtype=bool)
    only_a, only_b = int(np.sum(a & ~b)), int(np.sum(~a & b))
    discordant = only_a + only_b
    p = 1.0 if discordant == 0 else float(binomtest(only_a, discordant, 0.5).pvalue)
    return {"only_a_correct": only_a, "only_b_correct": only_b, "p_value": p}
