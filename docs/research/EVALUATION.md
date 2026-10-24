# Evaluation

What has been measured, on which data, and where each number comes from.
Every number on this page is copied from the file and key named next to it;
`python scripts/regenerate_results.py --check` rebuilds every file in
`results/` from the per-item scores in `paper_results/` and confirms they
match. Anything without a file behind it has been removed (see the end of
this page).

Datasets: [`DATASETS.md`](DATASETS.md).

## 1. Audio model on ASVspoof 2019 LA eval

The served model is an LCNN on LFCC features, trained on the LA train
partition, with the epoch, front end, seed, calibration and verdict rule all
chosen on dev. Eval was scored once per frozen seed.

Source: `results/audio_eval.json` (`asvspoof2019_la_eval`), built from
`paper_results/audio_asvspoof2019la/eval/audio_lcnn_asvspoof_lfcc_seed2_eval_scores.csv`.

| Metric (served seed 2, all 71,237 eval utterances) | Value | Key |
|---|---|---|
| EER | 4.78 % | `eer` |
| min t-DCF | 0.102 | `min_tdcf` |
| AUC | 0.986 | `auc_bonafide_vs_spoof` |
| EER, mean ± SD over 3 seeds | 5.26 ± 0.65 % | `all_seeds.eer_percent` |
| min t-DCF, mean ± SD over 3 seeds | 0.110 ± 0.014 | `all_seeds.min_tdcf` |

Per attack (`per_attack_eer`), the model is weakest on A17 (EER 23.7 %),
then A19 (2.8 %), A18 (2.7 %), A15 (2.0 %) and A14 (1.9 %); every other eval
attack is below 1 %. ROC: `results/figures/audio_roc.png`.

These scores were computed with cuDNN TF32 enabled (PyTorch's default at the
time). The served scorer now runs in strict float32; on the end-to-end sample
below the largest difference between the two in mean logit is 0.094, and the
AUC on that sample is the same to three decimals (0.9859 vs 0.9859).

## 2. Audio verdicts end to end (ASVspoof 2019 LA eval sample)

A stratified random sample of the eval partition (seed 0): 2,002 bona fide
utterances and 154 of each of the 13 eval attacks (4,004 in total), each run
through the same function the worker runs for an upload, with the verdict
rule frozen on dev before any of them was scored (authentic below 0.417,
flagged at or above 0.577, inconclusive between; heuristic signals carry no
weight). Scored once; no file failed.

Source: `results/pipeline_eval.json` (`audio.asvspoof2019_la_eval`), built
from `paper_results/audio_end_to_end_eval/verdict_rates.json`. Intervals are
95 % Wilson intervals.

| | Authentic | Inconclusive | Flagged |
|---|---|---|---|
| Bona fide (n = 2,002) | 99.8 % [99.5, 99.9] | 0.0 % [0.0, 0.2] | 0.2 % [0.1, 0.5] |
| Spoofed (n = 2,002) | 13.1 % [11.7, 14.6] | 1.3 % [0.9, 2.0] | 85.6 % [84.0, 87.0] |

Flagged rate per attack (`per_attack.<attack>.flagged`, n = 154 each):
A09, A12 and A13 100 %; A07, A10 and A11 99.4 %; A16 97.4 %; A08 95.5 %;
A14 86.4 %; A15 83.8 %; A18 74.0 %; A19 72.1 %; **A17 5.2 %** (8 of 154;
144 were called authentic). Figure: `results/figures/audio_pipeline_verdicts.png`.

AUC on the sample: 0.9859 [0.9823, 0.9892] for the unrounded model
probability (`auc_lcnn_probability_unrounded`), but 0.9734 [0.9686, 0.9782]
for the probability the API returns (`auc_fake_probability`): the API rounds
it to four decimals, so 2,024 of the 4,004 utterances report exactly 0 and
442 exactly 1 (`fake_probability_ties`), and the rounded value cannot rank
them. Verdicts are taken before rounding and are not affected.

**What this does not show.** LA is studio-quality English read speech from
the 2019 generation of TTS and voice-conversion systems. No result here says
how the model behaves on phone calls, real-world recordings, other languages
or current voice-cloning services. In-the-Wild, the planned cross-dataset
test, is not run (licence unresolved; `audio.in_the_wild` in
`results/pipeline_eval.json`).

## 3. Audio robustness to re-encoding

The same 4,004 utterances, each scored by the served model as an upload is
loaded, in three conditions fixed before scoring: the original FLAC, MP3 at
64 kbit/s (libmp3lame) and Opus at 32 kbit/s (libopus), using the ffmpeg 7.1
build bundled with imageio-ffmpeg. Verdicts apply the frozen dev rule to the
model probability. Scored once; no file failed.

Source: `results/robustness.json` (`audio`), built from
`paper_results/audio_codec_robustness/metrics.json`.

| Condition | EER | AUC [95 % bootstrap] | Bona fide called authentic | Spoofed flagged |
|---|---|---|---|---|
| Original FLAC | 4.45 % | 0.9859 [0.9820, 0.9893] | 99.8 % [99.5, 99.9] | 85.6 % [84.0, 87.0] |
| MP3 64 kbit/s | 17.18 % | 0.9112 [0.9023, 0.9202] | **0.0 % [0.0, 0.2]** | 100.0 % [99.8, 100.0] |
| Opus 32 kbit/s | 6.44 % | 0.9796 [0.9752, 0.9835] | 99.6 % [99.1, 99.8] | 82.4 % [80.7, 84.0] |

Keys: `conditions.<condition>.eer`, `.auc`,
`.frozen_rule_verdicts.bonafide.authentic`, `.frozen_rule_verdicts.spoof.flagged`.
Both codecs lower the AUC significantly (DeLong against the original,
`delong_vs_original`: MP3 p = 1.7e-64, Opus p = 2.5e-12).

**MP3 breaks the verdict.** After MP3 encoding every bona fide utterance is
flagged as AI-generated: the model still ranks them partly, but every
calibrated probability rises above the flag threshold. A genuine recording
uploaded as MP3 is therefore called AI-generated (`KNOWN_ISSUES.md` #14). The
model was trained on uncompressed LA audio only. Opus at 32 kbit/s mainly
hurts the attacks the model already finds hardest (A18 and A19 EER 7.8 % and
7.7 %, against 2.7 % and 3.2 % on the original; `per_attack_eer`).

The `original` probabilities equal the end-to-end run's model probabilities
for all 4,004 utterances (`original_vs_end_to_end_run.max_abs_difference` = 0).
Figure: `results/figures/audio_codec_robustness.png`.

Image robustness (JPEG 95/75/50/30, 0.5x resize, WhatsApp-style
recompression) is implemented in `scripts/robustness.py` but not run: there
is no image test set yet (`image` in `results/robustness.json`).

## 4. Latency

End-to-end time per file through the worker's pipeline (evidence plots
included), on one machine: Intel Core i9-14900 (32 logical CPUs), 63.7 GB
RAM, NVIDIA GeForce RTX 5070 (driver 595.95), Windows. Each device ran in its
own process; the first call (model loading) is the cold start and is excluded
from the percentiles, then two warm-up calls are discarded.

Source: `results/latency.json` (`latency.<device>.<modality>`), built from
`paper_results/latency/timings.csv`.

| Modality (input) | GPU p50 / p95 | CPU p50 / p95 | Cold start GPU / CPU | Runs |
|---|---|---|---|---|
| Image (256 x 256 faces-140k test images) | 0.27 / 0.31 s | 0.54 / 0.58 s | 9.8 / 9.1 s | 30 |
| Audio (ASVspoof 2019 LA dev utterances) | 1.11 / 1.49 s | 1.19 / 1.55 s | 2.9 / 2.8 s | 30 |
| Video (10 s, 640 x 480, synthetic, no audio) | 1.77 / 1.83 s | 2.14 / 2.17 s | 1.8 / 2.2 s | 8 |

The image inputs are small; phone photos are larger, so image times here are
a lower bound. Audio takes almost the same time on both devices, so most of
it is spent outside the model. The video clip has no audio track and is
sampled at 1 fps, so real uploads with speech take longer (the audio stage's
extra cost is in `paper_results/video_timing/timing.json`). Figure:
`results/figures/latency.png`.

## 5. Image

Not measured. `results/image_eval.json` records why: the 560-image held-out
set (H560) is not on this machine, the independent test set T2 is not built,
and the image configuration is not frozen, which must happen before any T2
image is scored. `scripts/eval_image.py` computes AUC, the false-positive
rate on real photos, recall per generator and the verdict confusion matrix
(INCONCLUSIVE included) once per-image scores exist.

## 6. Video

Not measured. FaceForensics++ and Celeb-DF v2 are not on this machine
(`video` in `results/pipeline_eval.json`). The video verdict currently relies
on a face classifier trained on StyleGAN faces and on unvalidated heuristics;
no video accuracy is claimed.

## Removed from the previous version of this page

The previous page reported numbers that no file in the repository produces,
and they have been deleted rather than carried over: the "120-image frozen
diagnostic set" FPR, recall, precision and Brier score; detection rates for
Midjourney, DALL-E 3, ElevenLabs and Wav2Lip; the JPEG, blur, WhatsApp and
downsampling robustness table; the latency table; and the determinism claim
stated as a score divergence. Where this page now covers the same question,
the number comes from a script and its results file.
