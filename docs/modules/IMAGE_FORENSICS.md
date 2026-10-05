# Module: Image Forensics

## 1. Purpose
The Image Forensics module analyzes static images (photographs, social media uploads, digital graphics) to detect signs of generative AI synthesis, localized splicing, retouching, or digital manipulation, providing interpretable visual heatmaps and calibrated confidence scores.

---

## 2. Input
- **Supported Formats:** JPEG, PNG, WebP, BMP, TIFF.
- **Constraints:** Minimum recommended resolution $128 \times 128$; maximum file size 50 MB (configurable).
- **Metadata:** EXIF, XMP, and ICC color profile metadata if present in the file container.
- **Screenshots:** accepted, but see §6 — the original file is always the better evidence.

---

## 3. Processing Pipeline

1. **Ingestion & Integrity:** Computes immutable SHA-256 digest, extracts file container header, and parses EXIF metadata.
2. **Screenshot / letterbox framing:** Uniform viewer bars (black frames, toolbars, editor gutters) are detected and cropped so every later stage analyses the picture, not the screen around it. A subject cut out onto a black background is not cropped (the bar's inner edge must meet content along most of its length).
3. **Face Extraction:** MTCNN detects and crops faces for the face-crop model.
4. **Full-scene AI-generation detectors (primary signal):** `haywoodsloan/ai-image-detector-deploy` (SwinV2, weight 0.75) and `Organika/sdxl-detector` (Swin, weight 0.25), fused as a weighted mean of log-odds. Each model's P(AI) is 1 − P(its "real" class).
5. **Provenance:** C2PA Content Credentials that declare AI generation (`trainedAlgorithmicMedia`) and generator parameters in metadata are decisive evidence of AI generation.
6. **Signal forensics (context):** ELA, noise residual, CFA demosaicing, FFT spectrum, copy-move (ORB), matte detection, watermark and steganography probes. These are reported as findings; only those shown to separate real from AI images influence the verdict (§4).
7. **Face-crop GAN model (informational):** EfficientNet-B4 trained on StyleGAN faces. Its score is reported but kept out of verdicts (`FACE_MODEL_IN_VERDICT=false`) because it is not discriminative on current content.
8. **Evidence fusion & verdict:** see §4.

---

## 4. Output
- **Verdict:** `AUTHENTIC`, `INCONCLUSIVE` or `MANIPULATED`.
  - `MANIPULATED` at probability ≥ `FAKE_THRESHOLD + UNCERTAIN_BAND`, `AUTHENTIC` at ≤ `FAKE_THRESHOLD − UNCERTAIN_BAND`, otherwise `INCONCLUSIVE`.
  - A screenshot with no camera metadata that the detectors do not flag is `INCONCLUSIVE` (threat `SCREEN_RECAPTURE_UNVERIFIABLE`), never `AUTHENTIC`.
  - If the scene detectors cannot be loaded, the result is never `AUTHENTIC` (threat `INSUFFICIENT_EVIDENCE`).
- **Fake probability:** the fused scene-detector probability, raised by decisive provenance (C2PA ≥ 0.97, generator metadata ≥ 0.93) or by corroborated forensic signals; a copy-move match alone raises it only into the inconclusive band.
- **Evidence:** per-model scene scores (`scene_model_scores`), screenshot framing (`recapture`), corroborating and context signals, ELA / noise / tampering / combined heatmaps.

### Measured performance (560 held-out images)
200 real photos (COCO, Flickr) and 360 AI images (SD 2.1, SDXL, SD3, DALL-E 3, Midjourney v6, Flux.1-dev, Gemini Nano Banana / Pro), each scored as the original file, a size/codec-normalised JPEG, and a simulated screenshot:

| Scene-detector configuration | AUC (original) | AUC (screenshot, cropped) | Real photos ≥ 0.5 |
|---|---|---|---|
| haywoodsloan + Organika, log-odds 0.75/0.25 (current) | 0.984 | 0.983 | 3.5% |
| haywoodsloan alone | 0.973 | 0.968 | 3.5% |
| Organika alone | 0.836 | 0.837 | 23% |
| umm-maybe/AI-image-detector (removed) | 0.469 | 0.468 | 26% |

---

## 5. Evidence Generated
- Cryptographic hash (SHA-256) of input image.
- Camera metadata timeline (Make, Model, Software, Timestamps).
- Per-model scene-detector scores, signal-forensics findings, and the list of signals that did / did not count toward the verdict.
- Forensic explanation summary explaining which signals contributed most heavily to the verdict.

---

## 6. Limitations
- **Screenshots and re-shares** strip C2PA / EXIF provenance and blur generator traces. Upload the original file whenever possible.
- **No trained face-swap detector.** The face-region heuristic fired on 30% of real portraits in evaluation, so it is reported but not scored.
- **The face-crop model only knows StyleGAN faces** (trained on the 140k Real and Fake Faces dataset and filtered copies of it).
- End to end on original files, 6.7% of current-generator images were still called AUTHENTIC and 5.0% INCONCLUSIVE — most often SD 2.1, SD3, SDXL and Midjourney v6 — while 2.0% of real photos were called MANIPULATED. Retouched real photos were not part of the evaluation set.
- Extreme compression (JPEG $Q < 40$) severely degrades CFA patterns and noise residuals; CFA traces are absent from virtually all resized web JPEGs, so their absence is not evidence of AI generation.
- Very small images ($< 128 \times 128$) do not provide sufficient pixel grids for reliable spectral or PRNU analysis.
