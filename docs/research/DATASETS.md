# Forensic Datasets Documentation

This document describes the primary datasets used in the training, diagnostic evaluation, and robustness benchmarking of the Deepfake Detective platform.

---

## 1. Primary Dataset Registry

### 1. GenImage Dataset
- **Purpose:** Image deepfake detection training and cross-generator generalization evaluation.
- **Media Type:** Images (JPEG / PNG).
- **Source:** GenImage Benchmark (NeurIPS 2023 / Open-Source Academic Dataset).
- **Generators Covered:** Stable Diffusion (v1.4, v1.5), Midjourney (v4, v5), DALL-E 2, DALL-E 3, ADM, VQDM, Glide, BigGAN, Wukong.
- **Train/Evaluation Role:**
  - Training: Subsets of Stable Diffusion and BigGAN.
  - Evaluation: Unseen generators (Midjourney, DALL-E 3, Glide) for zero-shot generalization testing.
- **Leakage Precautions:** Strict class and seed separation; training images are never present in evaluation or diagnostic holdout splits.

### 2. DeepfakeTIMIT / FakeAVCeleb Subsets
- **Purpose:** Audio deepfake detection and audiovisual temporal synchronization benchmarking.
- **Media Type:** Audio tracks (WAV, 16 kHz mono) and video clips (MP4).
- **Source:** Academic open-access distribution (Idiap Research Institute / KAIST).
- **Manipulations Covered:** Voice conversion, text-to-speech (TTS), face-swapping, lip-sync audio replacement (Wav2Lip).
- **Train/Evaluation Role:** Evaluation and diagnostic validation of the LCNN audio classifier and cross-modal synchronization detectors.
- **Leakage Precautions:** Speaker-independent splits; no identity overlap between training and evaluation partitions.

### 3. Real Camera Benchmark (Diverse Natural Capture)
- **Purpose:** False positive rate (FPR) suppression and baseline authentic calibration.
- **Media Type:** Images (JPEG, WebP, PNG).
- **Source:** Curated authentic camera captures, smartphone photographs (iPhone, Samsung, Pixel), RAW-to-JPEG exports, and uncompressed photo repositories (RAISE / ImageNet authentic splits).
- **Processing Variants:**
  - Clean uncompressed
  - JPEG recompressed (Q=50, 75, 85, 95)
  - Social media transcode simulation (WhatsApp, Instagram, Telegram)
  - Color graded / tone mapped / retouched
  - Screenshots (desktop and mobile)
- **Train/Evaluation Role:** Hard-negative training and calibration validation to prevent misclassifying standard compression artifacts as AI generation.

---

## 2. Generator Taxonomy & Generalization Matrix

| Generator Family | Architecture Type | Known to Training | Evaluation Role |
|---|---|---|---|
| **Stable Diffusion v1.5** | Latent Diffusion Model (LDM) | Yes | In-distribution baseline |
| **BigGAN** | Deep Convolutional GAN | Yes | In-distribution GAN baseline |
| **Midjourney v5** | Proprietary Diffusion | No | Out-of-distribution (OOD) test |
| **DALL-E 3** | Transformer-conditioned Diffusion | No | Out-of-distribution (OOD) test |
| **Flux.1 / SDXL** | Rectified Flow / Next-Gen Diffusion | No | Emergent generator evaluation |
| **ElevenLabs / XTTS** | Neural Voice Cloning | Partially (XTTS) | Speech synthesis evaluation |
| **Wav2Lip** | GAN Lip-Synchronization | No | Video temporal anomaly evaluation |

---

## 3. Data Governance & Ethical Compliance

- **Intellectual Property:** Datasets are used strictly for non-commercial, academic research, and evaluation purposes in compliance with original academic licenses.
- **Privacy Protections:** Benchmark sets do not expose personally identifiable information (PII) of private individuals; public benchmark subjects are handled in accordance with academic research standards.
- **Integrity Verification:** Checksums and directory manifests are maintained under `data/` and `golden_test/` to ensure reproducible diagnostic runs.
