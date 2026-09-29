# Limitations

This document describes known limitations of the Deepfake Detective platform. Understanding these limitations is essential for correctly interpreting forensic results.

## Detection Accuracy

- **No detector is perfect.** Both false positives (authentic media flagged as manipulated) and false negatives (manipulated media missed) will occur. The system reports calibrated probabilities rather than binary decisions to reflect this uncertainty.
- **The INCONCLUSIVE verdict exists for a reason.** When model confidence falls within the uncertainty band, the system explicitly refuses to classify rather than forcing an incorrect prediction.

## Unseen AI Generators

- Models are trained on specific categories of AI-generated content (GANs, diffusion models, face swaps, etc.). Entirely novel generator architectures not represented in training may evade detection.
- The OOD (out-of-distribution) detection module flags inputs that are statistically dissimilar to training data, but it cannot guarantee detection of every new generator.

## Image-Specific Limitations

- **Heavy JPEG compression** can destroy subtle forensic signals (ELA, PRNU, frequency artifacts).
- **Social media processing** (Instagram, WhatsApp, Twitter) re-encodes images and strips metadata, reducing signal quality.
- **Screenshots** lose original container/metadata information entirely.
- **Heavily retouched real photos** may trigger false positives due to editing artifacts that resemble AI generation.
- **Very small images** (below ~128×128 pixels) provide insufficient spatial information for reliable analysis.

## Audio-Specific Limitations

- **Low-bitrate audio** (below 64 kbps) degrades spectral features required for voice quality and AI detection.
- **Very short clips** (under 2 seconds) provide insufficient signal for reliable statistical analysis.
- **Background noise** can mask glottal and phonemic features used for voice authenticity assessment.
- **ENF (Electrical Network Frequency) analysis** requires audio recorded in environments with detectable mains hum; outdoor or isolated recordings may not contain ENF.
- **Re-recording through speakers** destroys most container-level and some signal-level forensic evidence.

## Video-Specific Limitations

- **Frame sampling:** Long videos are analyzed at a configurable FPS (default: 1 frame/second). Manipulation in unsampled frames may be missed.
- **Heavily compressed video** (low bitrate, multiple re-encodings) degrades spatial forensic signals.
- **Non-facial video content** receives limited analysis from face-specific detectors.
- **Container format diversity:** Not all video container formats are fully supported.

## Metadata and Provenance

- **EXIF/metadata can be stripped or forged.** The system uses metadata as supporting evidence, not as definitive proof.
- **The system cannot prove who created media** or establish chain of custody beyond what is technically observable in the file itself.
- **"Earliest discovered source" is not "original source."** Source discovery, when available, finds indexed occurrences — it cannot guarantee completeness.

## Report and Evidence Integrity

- **SHA-256 hashing verifies file integrity**, not authenticity of content. A hash proves a file has not been modified since hashing, not that the original content was genuine.
- **Reports reflect the state of analysis at generation time.** If models are updated, re-analysis may produce different results.

## Infrastructure

- **GPU acceleration** significantly improves inference speed but is not required. CPU-only inference is supported but slower.
- **This is a standalone tool**, not a real-time monitoring system or internet-scale scanner.
- **Storage requirements** scale with the number and size of uploaded media files.

## General Principles

- **AI predictions are not facts.** Every model output should be interpreted as a technical signal requiring human judgment.
- **Absence of detected manipulation does not prove authenticity.** It means no manipulation was detected by the available methods.
- **Multiple signals are stronger than one.** The evidence fusion approach is designed to weigh multiple independent forensic signals, but individual signals can be unreliable in isolation.
