# Model Card

## Image Detector

| Property | Value |
|---|---|
| **Architecture** | EfficientNet-B4 (fine-tuned) |
| **Task** | Binary classification: authentic vs. AI-generated/manipulated |
| **Input** | RGB image, resized to 380×380 (B4) or 224×224 (B0) |
| **Output** | Probability (0.0–1.0) that the image is AI-generated or manipulated |
| **Preprocessing** | MTCNN face detection → crop (if face detected), otherwise center crop; ImageNet normalization |
| **Checkpoint** | `checkpoints/image_detector.pt` (~67 MB) |
| **Lightweight variant** | `checkpoints/image_detector_b0.pt` (~16 MB, EfficientNet-B0) |
| **Framework** | PyTorch 2 |
| **Calibration** | Platt scaling on validation set |

### Training Data Categories

- Real: camera photos, smartphone photos, screenshots, social media, HDR, retouched, compressed, resized
- AI: GAN-generated, diffusion-generated, face swaps, inpainted, outpainted, image-to-image, edited

### Known Limitations

- Heavy JPEG compression can degrade detection signals
- Social media re-encoding affects reliability
- Completely novel generators may evade detection
- Very small images (<128×128) are unreliable
- Heavily retouched real photos may trigger false positives

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
