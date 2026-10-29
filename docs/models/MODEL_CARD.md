# Model Card

## Image Detection

Image verdicts come from a full-scene detector ensemble and from provenance.
The project's own face-crop checkpoint is reported but, by default, not used
in verdicts (see below).

### Full-scene AI-generation ensemble (primary)

| Property | Value |
|---|---|
| **Models** | `haywoodsloan/ai-image-detector-deploy` (SwinV2, weight 0.75); Community Forensics `OwensLab/commfor-model-384` (ViT-S/384, weight 4); the same model fine-tuned on FLUX.2, GPT Image 2 and Nano Banana 2 (`checkpoints/commfor_ft_v3/`, weight 4) |
| **Fusion** | Weighted mean of log-odds; each model's P(AI) = 1 − P(its "real" class) |
| **Input** | Whole image after screenshot / letterbox borders are cropped |
| **Verdict** | MANIPULATED at P(AI) ≥ 0.58; without camera metadata AUTHENTIC only below 0.02, INCONCLUSIVE between |
| **Evaluation** | `docs/research/EVALUATION.md` section 5; files in `evaluation/COMMFOR-02`, `evaluation/COMMFOR-FT-01`, `evaluation/E2E-02` |

How each choice was made, all on data the test sets never touched:

- Community Forensics weight 4: dev half of COCO val2017 + Synthbuster (`evaluation/COMMFOR-02/scene_detector_eval_dev.json`).
- `Organika/sdxl-detector` removed: on the newer-generator validation split it scored AUC 0.596, flagged 15.6 % of real images, and the fusion was unchanged without it (`evaluation/COMMFOR-FT-01/val_ft1.json`).
- Fine-tuned model: `ml/training/finetune_commfor.py` (epoch chosen on validation AUC) and `ml/training/calibrate_commfor.py` (logit offset so ≤ 1 % of validation real images score ≥ 0.5). Training data: `docs/research/DATASETS.md`. Retraining procedure: `docs/models/RETRAINING_IMAGE.md`.
- Original and fine-tuned at equal weight: fixed before scoring the test sets. Without the original, the fine-tuned model scored 6.4 % of held-out COCO photos as AI (`evaluation/COMMFOR-FT-01/old_v3.json`); together, none of the real test photos was called MANIPULATED (`evaluation/E2E-02`).

`umm-maybe/AI-image-detector` (an earlier primary model) scored below chance on current generators and was removed earlier.

### Edit localisation: TruFor (shown, not in the verdict)

TruFor (Guillaro et al., CVPR 2023; GRIP-UNINA licence, nonprofit use only) gives an integrity score and a
heatmap of possibly edited regions. A region is reported at score ≥ 0.8, the lowest threshold flagging ≤ 2 % of
real COCO dev photos (`evaluation/TRUFOR-01/results.json`). It is not in the verdict: it flags 10 % of re-compressed
social-media photos in `accuracy_test`, and it does not detect fully generated images.

### Face-crop GAN classifier (informational)

| Property | Value |
|---|---|
| **Architecture** | EfficientNet-B4, 224×224 MTCNN face crops, ImageNet normalisation |
| **Checkpoint** | `checkpoints/image_detector.pt` (`image_detector_b0.pt`: EfficientNet-B0 variant) |
| **Training data** | 140k Real and Fake Faces (FFHQ photos vs StyleGAN faces) plus filtered / re-encoded copies of those faces. The "diffusion" and "inpaint" classes are PIL filters over StyleGAN faces, not diffusion output. |
| **Calibration** | None applied at inference |
| **Verdict use** | Off by default (`FACE_MODEL_IN_VERDICT=false`) |

The recorded 99.98% validation accuracy came from a split in which 144,000 of
164,000 validation images were re-encoded copies of training faces; it measures
memorisation. On real-world photos with faces the model flagged 21% of real
faces and 15% of AI faces, so its score cannot support a verdict. Retrain it on
real photos and genuine current-generator images (`scripts/expand_training_dataset.py --extra`)
and validate it before enabling it.

### Known Limitations

- Screenshots and re-shares strip C2PA / EXIF provenance; unflagged screenshots are reported INCONCLUSIVE
- No trained face-swap detector; the face-region heuristic is reported only (it fired on 30% of real portraits)
- End to end on original files: 88.3% of AI images MANIPULATED, 6.7% AUTHENTIC (most often SD 2.1, SD3, SDXL, Midjourney v6); 2.0% of real photos MANIPULATED
- Heavily retouched real photos were not part of the evaluation set
- Very small images (<128×128) are unreliable

---

## Audio Detector

### Verdict model: pellav2 (pretrained, not trained here)

| Property | Value |
|---|---|
| **Source** | Hugging Face `Sadanie/pellav2-audio-deepfake-detector`, revision `29daea8b04acf2d3f11d1d0da6b01c17fc8a1e4b`, MIT licence; weights sha256 `d21aedfb52e2f87706c2753715a29665482b0f4a034800c31579df5d458559ac` |
| **Architecture** | w2v-BERT 2.0 encoder (`facebook/w2v-bert-2.0` configuration) with a softmax-weighted sum of all hidden layers and a linear head; 580.5 M parameters (`backend/app/ml/audio/pellav2.py`, copied from the authors' `pellav2_infer.py`) |
| **Training data** | Not published by the authors |
| **Input** | 16 kHz mono; DC removal, 20 Hz high-pass; each consecutive 4 s window (up to 8, the first 32 s) loudness-normalised to -23 LUFS; 80-bin Kaldi filterbank |
| **Output** | Mean of the window probabilities; AI-generated at >= 0.58, authentic below 0.42, inconclusive between (the authors' 0.5 +/- the platform band; `paper/config/pellav2_verdict_config.json`) |
| **Served when** | `AUDIO_PELLAV2_IN_VERDICT=true` (default). If pellav2 cannot run, the LCNN below decides |
| **Evaluation** | `docs/research/EVALUATION.md` section 7: EER 1.6 % on an ASVspoof 2019 LA eval sample, 18.5 % on an ASVspoof 5 eval sample; limits in `KNOWN_ISSUES.md` #16 |

### Fallback and context model: LCNN

| Property | Value |
|---|---|
| **Architecture** | LCNN (Light Convolutional Neural Network, 144,065 parameters; `build_audio_model` in `backend/app/ml/models_arch.py`) |
| **Task** | Binary classification: bona fide vs. spoofed (text-to-speech or voice-converted) speech |
| **Training data** | ASVspoof 2019 logical access, official train protocol (25,380 utterances, attacks A01–A06); epoch, front end, served seed and calibration chosen on the official dev protocol only |
| **Input** | 16 kHz mono waveform as read from the file (no peak normalisation); LFCC (20 coefficients + deltas + double deltas) of every 4-second window; a shorter clip is repeated to 4 s |
| **Output** | Mean of the window spoof logits, mapped to a probability by class-balanced Platt scaling fitted on dev (`paper/config/audio_calibration.json`) |
| **Checkpoint** | `checkpoints/audio_lcnn_asvspoof_lfcc_seed2.pt` (lowest dev EER of the three frozen seeds); the backend refuses any file whose sha256 differs from the calibration file |
| **Served when** | `AUDIO_MODEL_SOURCE=lcnn_asvspoof`; with `legacy` no trained model runs and results are marked experimental |
| **Retired** | `checkpoints/audio_detector.pt` (trained on NumPy tones, not speech; see `KNOWN_ISSUES.md`) is no longer loaded |

### Evaluation (ASVspoof 2019 LA eval, attacks A07–A19, unseen in training)

From `results/audio_eval.json` (generated by `ml/evaluation/eval_audio.py` from `paper_results/audio_asvspoof2019la/`):

| | EER | min t-DCF | AUC |
|---|---|---|---|
| Served checkpoint (seed 2), 7,355 bona fide / 63,882 spoofed | 4.78 % | 0.102 | 0.986 |
| Three seeds, mean ± SD | 5.26 ± 0.65 % | 0.110 ± 0.014 | 0.983 ± 0.004 |

Per attack (served checkpoint, `asvspoof2019_la_eval.per_attack_eer`): every attack except A17 is below 3 % EER; **A17 is 23.7 %**.

### Supplementary signals (no weight in the verdict once the LCNN is the verdict)

Glottal-flow, voice-quality, mains-hum (ENF), splice-timeline, container and watermark checks are reported as context. On a balanced ASVspoof 2019 LA dev subsample none of them separated bona fide from spoofed speech: every AUC was between 0.41 and 0.57 (`paper_results/audio_heuristics_dev/signal_auc.json`).

### Known Limitations

- Evaluated on ASVspoof 2019 LA only: studio-quality English read speech from a fixed set of 2019 synthesis systems. Not evaluated on real-world recordings, phone calls, other languages or current commercial voice cloning; the In-the-Wild test is pending (`KNOWN_ISSUES.md` #13).
- Dev error (0.19 % EER) is far below eval error (4.78 %): dev contains only the training attacks, so dev performance says nothing about unseen attacks, and the dev-fitted probabilities are overconfident on them.
- Compression (MP3, Opus, messenger re-encoding) has not been tested.

---

## Video Detector

| Property | Value |
|---|---|
| **Architecture** | Frame-aggregated (uses image detector per frame) |
| **Task** | Video deepfake detection via temporal + spatial analysis |
| **Input** | Video file, sampled at configurable FPS (default: 1.0) |
| **Output** | Aggregated probability + per-frame scores + temporal evidence |
| **Max frames** | 32 (configurable) |
| **Framework** | PyTorch 2 + OpenCV |

### Supplementary Analysis

- Optical flow anomaly detection
- Face temporal consistency (bounding-box jitter)
- Lip-sync forensics
- Compression DNA analysis
- Container forensics
- Audio-video cross-modal correlation

### Known Limitations

- Frame sampling may miss manipulation in unsampled frames
- Heavy re-encoding degrades spatial forensic signals
- Non-facial video content receives limited face-specific analysis

---

## General Notes

- All models are loaded once at startup and cached in memory (GPU VRAM if available)
- Checkpoint integrity is validated at load time
- Models can run on CPU (slower) or CUDA GPU (recommended)
- Model outputs are calibrated where validation data is available
- The uncertainty band prevents forced classification near the decision boundary
