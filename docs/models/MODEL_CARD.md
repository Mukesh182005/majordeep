# Model Card

## Image Detection

Image verdicts come from a full-scene detector ensemble and from provenance.
The project's own face-crop checkpoint is reported but, by default, not used
in verdicts (see below).

### Full-scene AI-generation ensemble (primary)

| Property | Value |
|---|---|
| **Models** | `haywoodsloan/ai-image-detector-deploy` (SwinV2, weight 0.75); `Organika/sdxl-detector` (Swin, weight 0.25) |
| **Source** | Hugging Face, downloaded on first use (~0.75 GB + ~0.33 GB cache) |
| **Fusion** | Weighted mean of log-odds; each model's P(AI) = 1 − P(its "real" class) |
| **Input** | Whole image after screenshot / letterbox borders are cropped |
| **Evaluation** | 560 held-out images: 200 real (COCO, Flickr), 360 AI (SD 2.1, SDXL, SD3, DALL-E 3, Midjourney v6, Flux.1-dev, Gemini Nano Banana / Pro) |
| **AUC** | 0.984 original files · 0.975 resized JPEG · 0.983 screenshots (border-cropped) |
| **Real photos ≥ 0.5** | 3.5% |

Model selection was measured, not taken from model cards: `umm-maybe/AI-image-detector`
(previously the primary model) scored AUC 0.469 on current generators — below
chance — and was removed; Organika alone flags 23% of real photos.

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

| Property | Value |
|---|---|
| **Architecture** | LCNN (Light Convolutional Neural Network) |
| **Task** | Binary classification: authentic vs. AI-generated speech |
| **Input** | Audio waveform, resampled to 16 kHz, 4-second window |
| **Output** | Probability (0.0–1.0) that the audio is AI-generated |
| **Checkpoint** | `checkpoints/audio_detector.pt` (~0.6 MB) |
| **Framework** | PyTorch 2 |

### Supplementary Analysis

The audio pipeline supplements neural detection with:
- 120+ signal descriptors (MFCC, spectral features, time-domain features)
- Glottal voice quality analysis (IAIF)
- ENF (Electrical Network Frequency) forensics
- File container DNA analysis
- Splicing timeline analysis

### Known Limitations

- Low-bitrate audio (<64 kbps) degrades spectral features
- Very short clips (<2 seconds) provide insufficient signal
- Background noise can mask glottal features
- Re-recording through speakers destroys container-level evidence

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
