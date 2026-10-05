# Known Issues

## Active Issues

### 1. `ml_v1` directory is a duplicate of `ml`
- **Location:** `backend/app/ml_v1/`
- **Description:** The `ml_v1` directory contains an identical copy of the production ML pipeline (`backend/app/ml/`). It was preserved during an architecture migration but is not actively imported by the production runtime.
- **Impact:** Repository bloat (~100 KB of duplicate code). No runtime impact.
- **Status:** REQUIRES_REVIEW — needs verification that no test or deployment path imports from `ml_v1` before removal.

### 2. JWT tokens stored in localStorage
- **Description:** Frontend stores JWT tokens in `localStorage`, which is accessible to JavaScript and vulnerable to XSS token theft.
- **Impact:** Low risk for the current use case; documented in the API client code.
- **Recommendation:** For deployments handling sensitive case material, migrate to httpOnly cookies.

### 3. SQLite concurrent write limitations
- **Description:** Development mode uses SQLite, which does not handle concurrent writes well.
- **Impact:** Under concurrent requests, SQLite may return "database is locked" errors.
- **Workaround:** Use PostgreSQL for production or multi-user scenarios.

### 4. Video analysis frame sampling gaps
- **Description:** Videos are sampled at configurable FPS (default: 1.0). Manipulation occurring entirely between sampled frames may be missed.
- **Impact:** Potential false negatives for very short manipulation segments.

### 5. ENF analysis requires mains hum
- **Description:** Audio ENF forensics requires the recording to contain detectable electrical network frequency (50/60 Hz hum). Outdoor recordings or isolated environments may not contain ENF.
- **Impact:** ENF signal is unavailable for some legitimate recordings.

### 6. Phase runner scripts in `backend/scripts/`
- **Description:** The `backend/scripts/` directory contains numerous `run_phase*.py` scripts from development phases 17–30. These are historical development/validation scripts, not production tools.
- **Impact:** Repository clutter. No runtime impact.

### 7. Root-level generated files
- **Description:** Several generated evaluation outputs remain at the repository root: `calibration_curve.png`, `confusion_matrix.png`, `eval_results.json`, `robustness_report.*`, `validation_audit_report.*`, `threshold_optimization.json`.
- **Impact:** Repository clutter. These are historical evaluation artifacts.

### 8. `false_negative_gallery` and `false_positive_gallery` contain dummy files
- **Description:** These directories contain placeholder files (`fn_dummy_1.jpg` with text content "dummy image content"), not actual error analysis images.
- **Impact:** Misleading directory names. No runtime impact.

### 9. Face-crop checkpoint only knows StyleGAN faces
- **Description:** `checkpoints/image_detector.pt` was trained on the 140k Real and Fake Faces dataset (FFHQ vs StyleGAN) and filtered copies of it. On real photos with faces it flagged 21% of real faces and 15% of AI faces.
- **Impact:** Its score is reported but excluded from image and video verdicts (`FACE_MODEL_IN_VERDICT=false`). Retrain on real photos plus genuine current-generator images (`scripts/expand_training_dataset.py --extra <labelled.csv>`) and validate before re-enabling.

### 10. No trained face-swap detector
- **Description:** The face-region heuristic (noise / sharpness / catchlight comparisons) fired on 30% of real portraits in evaluation, the same rate as on AI images.
- **Impact:** Reported as an unvalidated indicator only. Face-swap deepfakes on otherwise real photos are not reliably detected.

### 11. Video segment timeline uses face-model frame scores
- **Description:** The per-segment "fake probability" timeline in video results is still drawn from face-model frame scores.
- **Impact:** Display only — the video verdict no longer uses those scores — but the timeline can show spikes on real footage.

### 12. Jobs analysed before 2026-10-05 keep their old verdicts
- **Description:** Stored results are not recomputed; a few contain `NaN` face scores from the old half-precision bug.
- **Impact:** Re-upload media to get the corrected analysis.

## Resolved Issues

### AI images reported authentic; real photos reported manipulated (fixed 2026-10-05)
- `umm-maybe/AI-image-detector` (AUC 0.469 on current generators, below chance) replaced by `haywoodsloan/ai-image-detector-deploy`; max-of-experts fusion (flagged 26–36% of real photos) replaced by log-odds fusion with `Organika/sdxl-detector` (AUC 0.984).
- Screenshot viewer borders are cropped before analysis; an unflagged screenshot without camera metadata is INCONCLUSIVE, not AUTHENTIC.
- Non-discriminative heuristics no longer force verdicts: the M28 statistical score (AUC 0.26), the Fourier/wavelet "artifact" (50% of real vs 47% of AI), missing CFA traces (100% of real JPEGs), the face-seam heuristic and a standalone matte.
- A filename rule capped AI scores below 0.49 for any file named "whatsapp", "instagram" or "snapchat"; removed.
- An image with no face no longer reports a "face" score from the face model run on the whole scene.

### Pipeline crashes and invalid evidence (fixed 2026-10-05)
- Half-precision face-model inference produced `NaN`, crashing 4% of image analyses (`cannot convert float NaN to integer`) and writing `NaN` into evidence JSON. Inference now runs in float32 and evidence is sanitised before it is stored.
- Video scene-AI detection always returned 0.0: ensemble records were called as functions and the error was swallowed. Video now uses the shared scene scorer.

### Training data leakage and mislabelling (fixed 2026-10-05)
- `scripts/expand_training_dataset.py` put re-encoded copies of training faces into validation (144,000 of 164,000 validation images), merged the held-out test split into training, and added unlabelled uploads as "fake". Derived copies are now training-only, the faces-140k test split stays held out, and only explicitly labelled `--extra` data is added.
