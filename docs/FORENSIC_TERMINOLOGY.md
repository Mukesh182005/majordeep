# Forensic Terminology Guide

This document defines the key terms used throughout the Deepfake Detective platform.

## Verdicts

| Term | Meaning |
|---|---|
| **AUTHENTIC** | The system's forensic signals predominantly indicate the media is unmanipulated and not AI-generated. This is a technical assessment, not a guarantee. |
| **MANIPULATED** | The system's forensic signals predominantly indicate the media has been artificially generated or significantly manipulated. |
| **INCONCLUSIVE** | The model's confidence falls within the uncertainty band, or conflicting signals prevent a clear determination. The system explicitly declines to classify. |

## Evidence Types

| Term | Meaning |
|---|---|
| **Neural prediction** | Output of a trained deep neural network (e.g., EfficientNet, LCNN). Represents a learned statistical pattern, not a deterministic rule. |
| **Signal-level evidence** | Measurements derived from the media's signal properties (frequency spectrum, noise patterns, compression artifacts) using established forensic methods. |
| **Metadata evidence** | Information extracted from the file's container and embedded metadata (EXIF, RIFF headers, codec parameters). |
| **Structural evidence** | Properties of the file's binary structure (container format, encoding layers, trailing data, embedded objects). |

## Confidence and Probability

| Term | Meaning |
|---|---|
| **Fake probability** | The model's estimated probability (0.0–1.0) that the media is AI-generated or manipulated. |
| **Confidence** | A measure of how certain the system is in its assessment, accounting for calibration and the uncertainty band. |
| **Calibrated probability** | A probability that has been adjusted (via Platt scaling or similar) so that, for example, a reported 80% probability corresponds to approximately 80% empirical accuracy on validation data. |
| **Uncertainty band** | A configurable range around the decision threshold where the system reports INCONCLUSIVE rather than forcing a classification. |

## Forensic Signals (Image)

| Term | Meaning |
|---|---|
| **ELA (Error Level Analysis)** | Re-compresses the image at a known quality and examines the difference. Uniform ELA suggests original compression; localized differences may indicate editing. |
| **PRNU (Photo Response Non-Uniformity)** | Sensor-specific noise pattern. Real cameras leave characteristic noise; AI-generated images typically lack it. |
| **Grad-CAM** | Gradient-weighted Class Activation Mapping. Highlights which spatial regions most influenced the neural network's decision. |
| **Steganography analysis** | Examines least-significant bit (LSB) planes for statistical anomalies that may indicate hidden data. |

## Forensic Signals (Audio)

| Term | Meaning |
|---|---|
| **MFCC** | Mel-Frequency Cepstral Coefficients. A compact representation of the audio spectrum commonly used in speech/audio analysis. |
| **Glottal analysis** | Examines whether the audio exhibits physical characteristics consistent with human vocal fold vibration (IAIF aerodynamic tracking). |
| **ENF (Electrical Network Frequency)** | The 50/60 Hz hum from electrical grids embedded in audio recordings. Phase discontinuities may indicate splicing. |
| **File DNA** | Deep analysis of the audio file's container structure (RIFF, MP4, etc.) to detect transcoding history, truncation, or structural anomalies. |

## Forensic Signals (Video)

| Term | Meaning |
|---|---|
| **Optical flow** | The pattern of apparent motion between consecutive frames. Anomalous flow patterns may indicate frame manipulation. |
| **Face temporal consistency** | Whether detected faces maintain consistent geometry, lighting, and identity across frames. |
| **Compression DNA** | Analysis of video codec artifacts and quantization patterns to detect re-encoding or manipulation. |
| **AV synchronization** | Whether the audio and video tracks are temporally aligned. Misalignment may indicate post-production editing. |

## Important Distinctions

- **"Detected as manipulated" ≠ "is manipulated."** Detection is probabilistic, not deterministic.
- **"No manipulation detected" ≠ "is authentic."** It means available methods did not find evidence of manipulation.
- **"Model confidence" ≠ "certainty."** High confidence means the model's statistical features strongly match one class, but the model can be wrong with high confidence.
- **"Metadata present" ≠ "metadata trustworthy."** Metadata can be forged, stripped, or inherited from other files.
