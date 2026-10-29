# Evaluation

What has been measured, on which data, and where each number comes from.
Every number on this page is copied from the file and key named next to it;
`python scripts/regenerate_results.py --check` rebuilds every file in
`results/` from the per-item scores in `paper_results/` and confirms they
match. Anything without a file behind it has been removed (see the end of
this page).

Datasets: [`DATASETS.md`](DATASETS.md).

## 1. Audio model on ASVspoof 2019 LA eval

Until the comparison in section 7, the served model was an LCNN on LFCC features (it is now the
fallback and is shown as context), trained on the LA train
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

Every file goes through `app.ml.pipeline.analyze`, the function the worker runs, with the final settings
(commit `445c4ac`; Community Forensics original + fine-tuned at weight 4 each, haywoodsloan 0.75;
AUTHENTIC without camera metadata only below 0.02). TruFor was switched off for this run: it does not change
verdicts (`TRUFOR_IN_VERDICT=false`). None of these files carries camera metadata.

Source: `evaluation/E2E-02/summary.json` (key `sets.<name>`), per-image rows in `evaluation/E2E-02/*.jsonl`,
written by `backend/scripts/eval_end_to_end.py`. Datasets and splits: `DATASETS.md`. No setting was chosen on
these test files.

| Test set | real / AI | Real called MANIPULATED | AI called MANIPULATED | AI called AUTHENTIC | AI INCONCLUSIVE | Real INCONCLUSIVE | AUC |
|---|---|---|---|---|---|---|---|
| COCO + Synthbuster test half (9 generators) | 296 / 919 | 0 (0.0 %) | 98.4 % | 1 (0.1 %) | 1.5 % | 5.7 % | 1.000 |
| FLUX.2, GPT Image 2, Nano Banana 2, Qwen Image 2.1 | 653 / 1481 | 0 (0.0 %) | 44.0 % | 172 (11.6 %) | 44.4 % | 19.3 % | 0.917 |
| `accuracy_test` (256 px thumbnails) | 60 / 60 | 0 (0.0 %) | 38.3 % | 17 (28.3 %) | 33.3 % | 3.3 % | 0.920 |

Per generator, AI images called MANIPULATED (`per_group`):

- dalle2 106/106, dalle3 102/104, firefly 108/108, glide 90/95, midjourney-v5 102/104, stable-diffusion-1-3 99/99, stable-diffusion-1-4 94/94, stable-diffusion-2 103/108, stable-diffusion-xl 100/101.
- FLUX.2 139/194, GPT_Image_2 46/195, Nano_Banana_2 8/192, Qwen_Image_2.1 458/900.

Before these changes (`evaluation/E2E-01/summary.json`, `sets.image_test_commfor_w0`: same COCO + Synthbuster test
half, Community Forensics at weight 0, any score below the band called AUTHENTIC): real called MANIPULATED 2.0 %, AI called MANIPULATED 74.5 %, AI called AUTHENTIC 21.5 %.

The newest generators remain the weak point: GPT Image 2 and Nano Banana 2 are mostly INCONCLUSIVE rather than
flagged, because the original Community Forensics scores them as real and outvotes the fine-tuned model. The
fine-tuned model without the original flags more of them but also scored 6.4 % of COCO test photos as AI
(`evaluation/COMMFOR-FT-01/old_v3.json`, `COMMFOR_WEIGHT=4.0`), which a forensic tool should not do. Model-level comparisons of the original,
fine-tuned and combined detectors: `evaluation/COMMFOR-FT-01/`.

**A tried and rejected alternative (v4).** A second fine-tune (`checkpoints/commfor_ft_v4/`) added 1,600 more COCO
photos, 1,350 unused Synthbuster images and 2,400 more GPT Image 2 / Nano Banana 2 images, and validation (which
now also held COCO and Synthbuster images) chose it alone at weight 8 (0.7 % of validation real images MANIPULATED).
On the held-out test sets (`evaluation/COMMFOR-FT-02/*_v4.json`, verdict thresholds as above) it called 84.2 % of
newest-generator images MANIPULATED (GPT Image 2 85.6 %, Nano Banana 2 55.7 %) but also 6 of 296 COCO photos
(2.0 %), and caught 8.3 % of `accuracy_test` AI images. The rule fixed beforehand was to switch only if no test
set got worse, so the original + v3 ensemble stays. v4 can be enabled with `COMMFOR_FT_CHECKPOINT` and the weights
`COMMFOR_WEIGHT=0`, `COMMFOR_FT_WEIGHT=8`, at the cost stated here.

Stage diagnosis (`stage_diagnosis`): apart from the AI-detection stage, no forensic stage separated real from AI
images on these sets (balanced accuracy 0.5).

## 5a. Audio verdicts end to end

Same script, pellav2 deciding (`evaluation/E2E-01/summary.json`, `sets.audio_*`), 300 bona fide and 300 spoofed
clips per set:

| Set | Real called MANIPULATED | Fake called MANIPULATED | INCONCLUSIVE | AUC |
|---|---|---|---|---|
| ASVspoof 2019 LA eval | 0.3 % | 97.7 % | 0.0 % | 0.998 |
| ASVspoof 5 eval sample | 15.0 % | 77.0 % | 5.7 % | 0.894 |

On ASVspoof 5 the audio verdict wrongly calls 15 % of genuine speech AI-generated (KNOWN_ISSUES #16). As for
images, only the model stage separated real from fake; the heuristic stages flagged nothing on either set.

**A tried and rejected audio alternative.** `ml/training/finetune_pellav2.py` fine-tuned pellav2's top 4 encoder layers
on ASVspoof 5 train/dev and ASVspoof 2019 LA train clips, each passed through random codecs (MP3, AAC, Opus, AMR,
Speex, GSM, G.722, EnCodec; none from the eval sample), and calibrated it so 2 % of validation bona fide windows
score >= 0.5. Same full-pipeline samples as above (`evaluation/E2E-03/summary.json`): ASVspoof 5 real called
MANIPULATED 15.0 % -> 4.0 % (EnCodec C04 + C07: 30/50 -> 6/50), but fakes called MANIPULATED 77.0 % -> 54.0 %;
ASVspoof 2019 fakes 97.7 % -> 84.7 % (real 0.3 % -> 0.0 %). The rule fixed before testing (fewer false alarms
*and* at most a 5-point loss of detection, and >= 95 % on ASVspoof 2019) was not met, so the original pellav2
stays the default. The fine-tuned checkpoint was deleted to free disk space; `finetune_pellav2.py prepare` and
`train` rebuild it from the same samples.

## 6. Video

Test data: the Google/Jigsaw DeepFake Detection (DFD) videos, 200 real and 200 face-swapped clips of paid,
consenting actors (`DATASETS.md`). GenD did not train on DFD; its authors report DFD as a cross-dataset test.

**Face models** (`evaluation/VIDEO-GEND-01/results.json`, `scripts/eval_video_detector.py`, all 400 videos, every
one with a face; P(fake) averaged over the sampled face frames):

| Face model | AUC | Accuracy at 0.5 | Real flagged | Face swaps caught |
|---|---|---|---|---|
| GenD (CLIP ViT-L/14), mean over frames | 0.941 | 85.5 % | 10.0 % | 81.0 % |
| GenD, worst frame | 0.937 | 63.0 % | 73.5 % | 99.5 % |
| EfficientNet-B4 face checkpoint (StyleGAN-trained) | 0.533 | 51.2 % | 0.0 % | 2.5 % |

**Whole-pipeline verdicts** (`evaluation/VIDEO-GEND-01/summary.json`, `backend/scripts/eval_end_to_end.py score-video`):

| Run | Videos | Real called MANIPULATED | Face swaps called MANIPULATED | Verdict AUC (95 % CI) |
|---|---|---|---|---|
| Old rules (`video_dfd120_gend_off`) | 60 / 60 | 26 (43.3 %) | 31 (51.7 %) | 0.549 (0.446–0.654) |
| Fixed rules, GenD off (`video_dfd_heldout80_gend_off`) | 40 / 40 | 0 (0.0 %) | 1 (2.5 %) | 0.521 (0.379–0.642) |
| Fixed rules, GenD on (`video_dfd_heldout80_gend_on`) | 40 / 40 | 1 (2.5 %) | 29 (72.5 %) | 0.886 (0.802–0.949) |

The first 120 videos showed that two unvalidated heuristics (LipForensics and the generator profile match) forced
26 of 60 real videos to MANIPULATED; per-stage balanced accuracy 0.47–0.52. They were stopped from forcing
verdicts, and the change was measured on 80 other DFD videos (40 + 40) that no decision used. The rule set before
measuring allowed GenD into the verdict if real videos called MANIPULATED rose by at most 2 points; it rose by 2.5
points (one video of 40), and the project owner accepted it. Median latency per video: 20.7 s (GenD on, RTX 5070).

Not measured: fully AI-generated video (no labelled set here), and real videos from phones or WhatsApp.

## 7. Audio: pellav2 compared with the LCNN



pellav2 is a pretrained detector (w2v-BERT 2.0 backbone, Hugging Face `Sadanie/pellav2-audio-deepfake-detector`,

revision `29daea8`, MIT licence); its training data is not published, so it may have seen any of these sets.

Nothing was trained or tuned here. Its threshold is the authors' 0.5, fixed before scoring; ASVspoof 2019 LA

dev only checks it (`pellav2_dev_verdict_config` in the first file). Since this comparison pellav2 decides the

audio verdict (`AUDIO_PELLAV2_IN_VERDICT=true`) and the LCNN is shown as context. Both models scored the same

files; samples are seeded, with spoof spread evenly over the attacks.



Sources: `evaluation/AUDIO-PELLAV2-01/results.json` (ASVspoof 2019 LA) and

`evaluation/AUDIO-PELLAV2-01-ASVSPOOF5/results.json` (ASVspoof 5), both written by

`backend/scripts/eval_audio_detector.py`; key `results.<set>.<model>`. Errors at threshold 0.5.



| Set and model | real / fake | EER (95 % CI) | AUC | real flagged | fakes missed |

|---|---|---|---|---|---|

| ASVspoof 2019 LA dev, pellav2 | 1,000 / 1,000 | 0.8 % (0.4 %–1.3 %) | 1.000 | 0.9 % | 0.5 % |

| ASVspoof 2019 LA dev, LCNN | 1,000 / 1,000 | 0.3 % (0.1 %–0.5 %) | 1.000 | 0.2 % | 0.3 % |

| ASVspoof 2019 LA eval, pellav2 | 2,000 / 2,000 | 1.6 % (1.1 %–1.9 %) | 0.998 | 0.5 % | 2.0 % |

| ASVspoof 2019 LA eval, LCNN | 2,000 / 2,000 | 5.0 % (4.4 %–5.8 %) | 0.979 | 0.2 % | 13.8 % |

| ASVspoof 5 eval sample, pellav2 | 1,500 / 1,504 | 18.5 % (17.1 %–19.9 %) | 0.902 | 17.3 % | 19.5 % |

| ASVspoof 5 eval sample, LCNN | 1,500 / 1,504 | 40.0 % (38.2 %–41.8 %) | 0.635 | 81.1 % | 9.7 % |



On LA eval pellav2's weakest attack is A10 (74.7 % caught); the LCNN's is A17 (8.4 %).

On the ASVspoof 5 sample pellav2 misses most of A27 (7.4 % caught), A32 (21.3 % caught), A30 (46.8 % caught).



**Re-encoding** (`codec_robustness.summary`, 200 + 200 LA eval clips, each re-encoded with every condition of

`ml/preprocessing/audio_codecs.py`): real speech flagged at 0.5.



| Condition | pellav2 | LCNN |

|---|---|---|

| original | 0.0 % | 0.0 % |

| mp3_32k | 1.5 % | 100.0 % |

| mp3_64k | 0.5 % | 100.0 % |

| mp3_96k | 0.5 % | 100.0 % |

| mp3_128k | 0.5 % | 100.0 % |

| aac_32k | 14.0 % | 0.0 % |

| aac_64k | 1.0 % | 0.0 % |

| aac_96k | 0.5 % | 0.0 % |

| opus_16k | 2.0 % | 61.5 % |

| opus_24k | 1.5 % | 45.5 % |

| opus_32k | 1.5 % | 46.0 % |

| opus_48k | 1.5 % | 47.5 % |

| resample_22k | 0.0 % | 95.5 % |

| resample_44k | 0.0 % | 95.5 % |

| resample_48k | 0.0 % | 95.5 % |

| resample_48k_ffmpeg | 0.0 % | 48.5 % |



**ASVspoof 5 per codec** (`results.asvspoof5_eval.<model>.per_codec`; 125 real clips per condition; codec names

from `ASVspoof5.codec.config.csv`): real speech flagged at 0.5.



| Codec | pellav2 | LCNN |

|---|---|---|

| - (none) | 0.0 % | 72.0 % |

| C01 (Opus WB) | 8.8 % | 92.8 % |

| C02 (AMR WB) | 6.4 % | 96.0 % |

| C03 (Speex WB) | 13.6 % | 94.4 % |

| C04 (EnCodec WB) | 68.0 % | 90.4 % |

| C05 (MP3 WB) | 0.8 % | 94.4 % |

| C06 (M4A WB) | 0.0 % | 67.2 % |

| C07 (MP3 + EnCodec WB) | 58.4 % | 92.0 % |

| C08 (Opus NB) | 21.6 % | 73.6 % |

| C09 (AMR NB) | 8.8 % | 63.2 % |

| C10 (Speex NB) | 20.8 % | 65.6 % |

| C11 (MST) | 0.0 % | 72.0 % |



Latency (`latency_seconds_per_clip`): pellav2 p50 0.029 s, p95 0.052 s per clip on NVIDIA GeForce RTX 5070, file decoding excluded (n = 6,000).

ROC curves: `roc.png` in each folder. The ASVspoof 5 sample comes from one of the ten eval archives

(`flac_E_aa.tar`); see `DATASETS.md`.




## Removed from the previous version of this page

The previous page reported numbers that no file in the repository produces,
and they have been deleted rather than carried over: the "120-image frozen
diagnostic set" FPR, recall, precision and Brier score; detection rates for
Midjourney, DALL-E 3, ElevenLabs and Wav2Lip; the JPEG, blur, WhatsApp and
downsampling robustness table; the latency table; and the determinism claim
stated as a score divergence. Where this page now covers the same question,
the number comes from a script and its results file.
