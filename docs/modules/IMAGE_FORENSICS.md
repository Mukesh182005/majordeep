# Module: Image Forensics

## 1. Purpose
The Image Forensics module analyzes static images (photographs, social media uploads, digital graphics) to detect signs of generative AI synthesis, localized splicing, retouching, or digital manipulation, providing interpretable visual heatmaps and calibrated confidence scores.

---

## 2. Input
- **Supported Formats:** JPEG, PNG, WebP, BMP, TIFF.
- **Constraints:** Minimum recommended resolution $128 \times 128$; maximum file size 50 MB (configurable).
- **Metadata:** EXIF, XMP, and ICC color profile metadata if present in the file container.

---

## 3. Processing Pipeline (8 Stages)

1. **Ingestion & Integrity:** Computes immutable SHA-256 digest, extracts file container header, and parses EXIF metadata.
2. **Face Extraction & Alignment:** Utilizes MTCNN to detect and crop human faces with facial landmark alignment. Falls back to whole-image analysis if no face is detected.
3. **Color Filter Array (CFA) Forensics:** Tests for Bayer color filter demosaicing patterns typical of optical camera sensors; synthetic images typically lack natural CFA demosaicing residuals.
4. **Error Level Analysis (ELA):** Re-compresses the image at known JPEG compression rates (e.g., 90%) and evaluates error differentials to detect non-uniform compression grids.
5. **Noise Residual & PRNU Analysis:** Applies high-pass spatial filtering and wavelet denoising to isolate sensor photo-response non-uniformity (PRNU) patterns and noise variance across color channels.
6. **Frequency Domain Spectrum (FFT):** Computes fast Fourier transform to detect periodic checkerboard patterns and high-frequency spectral roll-offs characteristic of upsampling artifacts in GANs and diffusion decoders.
7. **Deep Neural Inference:** Evaluates fine-tuned EfficientNet / ResNet neural backbones against the normalized image to predict generative AI feature representations.
8. **Calibrated Evidence Fusion:** Combines physical signal descriptors with deep neural probabilities using Platt scaling and uncertainty thresholds to determine final authenticity verdicts.

---

## 4. Output
- **Overall Verdict:** `AUTHENTIC`, `AI_GENERATED`, `MANIPULATED`, or `UNCERTAIN`.
- **Authenticity Score:** Continuous calibrated probability $0.0 \dots 1.0$.
- **Uncertainty Flag:** Boolean indicator when scores fall within the boundary zone $(0.45 \le p \le 0.55)$.
- **Visual Evidence Plates:**
  - ELA error differential heatmap
  - Noise residual distribution map
  - FFT power spectrum display
  - CFA periodicity confidence metric

---

## 5. Evidence Generated
- Cryptographic hash (SHA-256) of input image.
- Camera metadata timeline (Make, Model, Software, Timestamps).
- Per-feature risk scores (CFA score, ELA anomaly score, FFT synthetic score, neural probability).
- Forensic explanation summary explaining which signals contributed most heavily to the verdict.

---

## 6. Limitations
- Extreme compression (JPEG $Q < 40$) severely degrades CFA patterns and noise residuals.
- Very small images ($< 128 \times 128$) do not provide sufficient pixel grids for reliable spectral or PRNU analysis.
- Heavy post-processing filters (e.g., strong beauty filters, grain addition) can simulate synthetic texture variance.
