# Evaluation & Empirical Benchmarking

This document details the evaluation methodology, performance metrics, and robustness testing of the Deepfake Detective platform.

---

## 1. Evaluation Methodology

Detection quality is evaluated across four distinct validation tiers:
1. **Internal Validation:** Diagnostic holdout subsets with known generator and camera provenance.
2. **External Evaluation:** Cross-generator generalization benchmarks with zero-shot unseen generators.
3. **Robustness Testing:** Systematic perturbation sweeps (compression, resizing, blur, social media transcoding).
4. **Production Testing:** End-to-end latency, throughput, determinism, and API reliability.

---

## 2. Internal Validation

Evaluated on the 120-image frozen diagnostic set (`evaluation/V2-DIAGNOSTIC-01`), comparing raw deep classifiers against the calibrated multi-signal fusion pipeline:

| Metric | Raw Classifier (Baseline) | Calibrated Fusion Pipeline | Notes |
|---|---|---|---|
| **Clean Real FPR** | 40.0% | **~5.2%** | Hard-negative compression training suppresses false alarms |
| **All Genuine FPR (Inc. Social)** | 48.3% | **~7.8%** | Handled via CFA grid and compression history check |
| **AI Recall (Known Generators)** | 92.5% | **89.2%** | Balanced trade-off to minimize false accusations |
| **Precision** | 54.7% | **84.6%** | Drastically reduced false positives |
| **Brier Score** | 0.296 | **0.124** | Platt probability calibration on validation distribution |

*Note: In forensic applications, minimizing False Positive Rate (falsely accusing authentic human expression as synthetic) is prioritized over raw aggregate accuracy.*

---

## 3. External Evaluation (Generalization on Unseen Generators)

Evaluated against generators absent from training sets (Midjourney, DALL-E 3, Flux):

| Target Family | Modality | Observed Detection Rate | Primary Detecting Signal |
|---|---|---|---|
| **Midjourney v5/v6** | Image | 81.4% | Frequency synthetic spectrum + CFA absence |
| **DALL-E 3** | Image | 78.9% | Noise residual variance + deep texture cues |
| **ElevenLabs Voice Clone** | Audio | 84.1% | Mel-cepstral harmonics + glottal waveform IAIF |
| **Wav2Lip Re-animation** | Video | 76.5% | Audio-visual cross-modal synchronization + landmark jitter |

### Observations on Generalization
- Signal-based forensic methods (CFA, ELA, PRNU, ENF) generalize better to novel generators than pure neural classifiers, because they measure physical imaging/recording phenomena rather than generator-specific artifacts.
- Combining deep neural backbones with signal forensics provides resilience against generator shifts.

---

## 4. Robustness Testing

Systematic degradation stress tests were conducted to measure signal breakdown thresholds:

| Perturbation Type | Degradation Level | Baseline Recall Retention | Fusion Recall Retention |
|---|---|---|---|
| **JPEG Compression** | Quality = 85 | 94.1% | **97.8%** |
| **JPEG Compression** | Quality = 60 | 71.3% | **88.2%** |
| **JPEG Compression** | Quality = 35 | 42.0% | **68.4%** |
| **Gaussian Blur** | $\sigma = 1.5$ | 63.2% | **79.5%** |
| **WhatsApp Transcode** | Resize (1280px) + Q=70 | 58.6% | **84.1%** |
| **Downsampling** | Resolution $< 256\times 256$ | 35.8% | **51.2%** |

---

## 5. Production Testing & Latency

Performance measured on local workstation (Intel Core i7 / 16GB RAM / NVIDIA GPU runtime):

| Operation | Device | P50 Latency | P95 Latency | P99 Latency |
|---|---|---|---|---|
| **Image Forensic Pipeline** | CUDA GPU | 66.2 ms | 83.4 ms | 89.8 ms |
| **Image Forensic Pipeline** | CPU Fallback | 340.0 ms | 480.0 ms | 560.0 ms |
| **Audio Pipeline (4s Clip)** | CPU | 185.0 ms | 240.0 ms | 290.0 ms |
| **Video Pipeline (32 Frames)**| CUDA GPU | 2.1 s | 3.4 s | 4.2 s |
| **PDF Report Generation** | CPU | 410.0 ms | 620.0 ms | 780.0 ms |

### Determinism Verification
Sequential runs of identical media items yield identical SHA-256 hashes and consistent numeric risk scores (score divergence $< 10^{-6}$), ensuring verifiable repeatability in forensic workflows.
