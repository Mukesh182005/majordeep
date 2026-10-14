# ASVspoof 2019 LA: official challenge baselines

These are published numbers, quoted for comparison. They are **not** our
measurements and must be cited when used.

## Evaluation set (pooled over attacks A07–A19)

| System | Front end, back end | min t-DCF | EER (%) |
|---|---|---|---|
| B01 | CQCC, GMM | 0.2366 | 9.57 |
| B02 | LFCC, GMM | 0.2116 | 8.09 |
| T05 (best primary submission, for context) | fusion | 0.0069 | 0.22 |

Source: Table 1 ("ASVspoof 2019 LA scenario", rows 33, 28 and 1) of
M. Todisco, X. Wang, V. Vestman, Md Sahidullah, H. Delgado, A. Nautsch,
J. Yamagishi, N. Evans, T. Kinnunen and K. A. Lee, "ASVspoof 2019: Future
Horizons in Spoofed and Fake Audio Detection," in *Proc. Interspeech 2019*,
pp. 1008–1012, doi: 10.21437/Interspeech.2019-2249 (DOI checked on Crossref,
2026-10-14).

The numbers were read from the copy of this paper distributed with the
corpus (`asvspoof2019_Interspeech2019_submission.pdf` on the Edinburgh
DataShare record https://doi.org/10.7488/ds/2555, MD5
e0158096cbdf76771718ba62192f1502). The same paper reports that the common ASV
system has an EER of 2.48 % on LA without spoofing attacks.

## Development set (for context on dev-based selection only)

| System | min t-DCF | EER (%) |
|---|---|---|
| LFCC-GMM | 0.0663 | 2.71 |
| CQCC-GMM | 0.0123 | 0.43 |

Source: Table 3 of the ASVspoof 2019 evaluation plan
(`asvspoof2019_evaluation_plan.pdf` on the same DataShare record, MD5
3b9efadef04332528203882c69c06d8f).

## How our numbers are made comparable

- Same partitions: the official CM protocol files (`ml/preprocessing/build_asvspoof2019_la.py`).
- Same metrics: EER and minimum normalised t-DCF computed as in the evaluation
  plan with the 2019 cost model (`ml/evaluation/asvspoof_metrics.py`), checked
  against the organisers' scoring code (`backend/tests/test_asvspoof_metrics.py`).
- Same ASV scores: the organisers' `ASVspoof2019.LA.asv.eval.gi.trl.scores.txt`.

Related reference for the database itself: X. Wang et al., "ASVspoof 2019: A
large-scale public database of synthesized, converted and replayed speech,"
*Computer Speech & Language*, vol. 64, 101114, 2020,
doi: 10.1016/j.csl.2020.101114 (checked on Crossref, 2026-10-14).
