# Module: Audio Forensics

## 1. Purpose
The Audio Forensics module detects synthetic speech, AI voice clones, spliced recordings, and acoustic tampering in voice audio files, combining light convolutional neural networks with acoustic physics and electrical network frequency analysis.

---

## 2. Input
- **Supported Formats:** WAV, MP3, AAC, FLAC, OGG, M4A.
- **Preprocessing:** Resampled to 16 kHz mono floating-point waveform; analyzed across 4-second sliding analysis windows.
- **Minimum Duration:** 1.0 second (recommended $> 3.0$ seconds for glottal and ENF analysis).

---

## 3. Processing Pipeline (8 Stages)

1. **Ingestion & Waveform Normalization:** Ingests audio, computes SHA-256 digest, normalizes peak amplitude, and enforces 16 kHz sample rate.
2. **Container & Codec DNA:** Parses audio container headers, bit-depth, codec framing, and metadata tags for re-encoding artifacts or synthetic software signatures.
3. **Spectral Acoustic Features:** Extracts 120+ time and frequency acoustic descriptors, including Mel-Frequency Cepstral Coefficients (MFCC), spectral centroid, spectral flatness, and zero-crossing rate.
4. **Glottal Inverse Filtering (IAIF):** Applies Iterative Adaptive Inverse Filtering (IAIF) to estimate glottal airflow pulses; synthetic vocoders often produce unnaturally regular or mathematically idealized glottal waveforms.
5. **Electrical Network Frequency (ENF) Forensics:** Extracts subtle power grid hum (50 Hz or 60 Hz fundamental and harmonics) embedded in recorded microphones to verify continuity and detect temporal splices.
6. **Splicing & Silence Boundary Analysis:** Inspects background noise floor continuity across phrase pauses to identify abrupt room-acoustic changes indicative of spliced words.
7. **Deep LCNN Inference:** Passes log-power spectrograms through a Light Convolutional Neural Network (LCNN) with Max-Feature-Map (MFM) activations specialized for synthetic voice detection.
8. **Fusion & Evidence Aggregation:** Synthesizes neural classifier scores with acoustic physics heuristics into a calibrated verdict.

---

## 4. Output
- **Audio Authenticity Verdict:** `AUTHENTIC`, `AI_SYNTHESIZED_VOICE`, `TAMPERED_SPLICE`, or `UNCERTAIN`.
- **Synthetic Voice Probability:** Calibrated score $0.0 \dots 1.0$.
- **Acoustic Anomaly Index:** Quantitative measure of vocal tract unnaturalness.
- **Visual Plots:**
  - Mel-spectrogram with high-frequency anomaly highlights
  - Glottal pulse waveform reconstruction
  - ENF frequency stability trace

---

## 5. Evidence Generated
- Audio stream properties (Sample rate, channels, bit depth, codec).
- Glottal pulse irregularity coefficient (Jitter/Shimmer anomalies).
- Spectral roll-off consistency metric.
- Identified splice timestamps (if localized tampering is detected).

---

## 6. Limitations
- Highly compressed audio ($< 64$ kbps MP3/AAC) removes high-frequency harmonics needed for subtle vocoder detection.
- Audio clips under 2 seconds provide insufficient data for stable ENF extraction.
- Re-recording through acoustic speakers ("acoustic replay attack") strips original container and electrical network signatures.
