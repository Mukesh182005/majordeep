# Module: Video Forensics

## 1. Purpose
The Video Forensics module detects video deepfakes, face swaps, facial re-enactment, and lip-sync manipulation through multi-frame temporal consistency, motion flow analysis, and spatial frame forensics.

---

## 2. Input
- **Supported Formats:** MP4, WebM, AVI, MOV, MKV.
- **Frame Sampling:** Configurable frame rate sampling (default: 1.0 frame per second up to 32 representative frames).
- **Streams Analyzed:** Visual frame sequence + Demuxed audio track.

---

## 3. Processing Pipeline (8 Stages)

1. **Demuxing & Container Inspection:** Parses video container atoms/boxes, verifies frame rates, checks codec metadata, and splits the stream into video frames and audio track.
2. **Frame Extraction & Sampling:** Uniformly samples keyframes and intermediate temporal intervals to ensure comprehensive temporal coverage within memory limits.
3. **Per-Frame Spatial Deep Analysis:** Executes the deep image classifier on individual extracted face frames to generate a per-frame synthetic probability sequence.
4. **Facial Landmark Tracking:** Extracts 68 facial landmarks across consecutive frames; calculates inter-frame landmark jitter and facial geometry variance.
5. **Optical Flow Motion Continuity:** Computes dense optical flow (Farnebäck algorithm) between consecutive frames to detect abrupt motion discontinuities around facial boundaries.
6. **Blink & Eye Dynamics:** Analyzes Eye Aspect Ratio (EAR) over temporal sequences to verify natural blink frequency and eye closure duration.
7. **Compression & GOP Structure Analysis:** Inspects Group of Pictures (GOP) structure, I/P/B frame distribution, and quantization parameter consistency across macroblocks.
8. **Temporal Aggregation & Risk Fusion:** Aggregates frame-level probabilities using robust median filtering and top-k anomaly clustering to avoid single-frame outliers.

---

## 4. Output
- **Video Verdict:** `AUTHENTIC`, `DEEPFAKE_VIDEO`, `FACE_SWAP`, or `UNCERTAIN`.
- **Confidence Score:** Aggregated probability $0.0 \dots 1.0$.
- **Per-Frame Probability Timeline:** Temporal graph showing deepfake probability across the duration of the video.
- **Flagged Frames:** List of timestamps where highest anomaly scores were concentrated.

---

## 5. Evidence Generated
- Frame count, duration, resolution, codec profile, average FPS.
- Peak anomaly timestamp and corresponding frame image.
- Landmark stability variance metric.
- Optical flow boundary discontinuity score.

---

## 6. Limitations
- Downsampled or low-framerate videos ($< 15$ fps) restrict optical flow and temporal landmark smoothness analysis.
- Videos without clear human faces rely primarily on global frame artifact detection rather than landmark dynamics.
- Frame-skipping sampling may miss micro-second synthetic insertions if they occur exclusively between sampled keyframes.
