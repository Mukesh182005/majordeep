# Known Issues

## Active Issues

### 1. `ml_v1` directory is a duplicate of `ml`
- **Location:** `backend/app/ml_v1/`
- **Description:** The `ml_v1` directory contains an identical copy of the production ML pipeline (`backend/app/ml/`). It was preserved during an architecture migration but is not actively imported by the production runtime.
- **Impact:** Repository bloat (~100 KB of duplicate code). No runtime impact.
- **Status:** REQUIRES_REVIEW — needs verification that no test or deployment path imports from `ml_v1` before removal.

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

### 12. Jobs analysed before 2026-10-05 keep their old verdicts
- **Description:** Stored results are not recomputed; a few contain `NaN` face scores from the old half-precision bug.
- **Impact:** Re-upload media to get the corrected analysis.

### 13. In-the-Wild not yet evaluated
- **Description:** The audio model has been evaluated on ASVspoof 2019 LA only (studio-quality English read speech). Its In-the-Wild scripts exist (`ml/preprocessing/build_in_the_wild.py`, `ml/evaluation/eval_in_the_wild.py`), but the dataset's licence is stated two ways (Apache 2.0 on its page, CC BY-SA 4.0 on Hugging Face) and it has not been downloaded.
- **Impact:** No real-world audio error rate exists; the audio result carries a note saying so.

### 14. The LCNN (audio fallback model) flags MP3 and resampled genuine speech as AI-generated
- **Description:** The LCNN was trained on ASVspoof 2019 LA audio as distributed (16 kHz, uncompressed). On the balanced dev subsample (1,000 bona fide; `paper_results/audio_codec_dev/metrics_audio_lcnn_asvspoof_lfcc_seed2.json`), under the frozen rule it flags 0.2 % of bona fide utterances as distributed, but 100 % after MP3 at any of 32-128 kbit/s, 63-76 % after Opus decoded by ffmpeg, 98 % after resampling to 22.05, 44.1 or 48 kHz and back with soxr (the path `load_audio` takes for every upload not at 16 kHz) and 67 % with ffmpeg's resampler (the path of a video's audio track); AAC leaves it at 0.1-0.2 %. On the eval sample, MP3 64 kbit/s flags 100 % of bona fide (`results/robustness.json`). Which resampling path changes the verdict is not simple: Opus decoded by libsndfile and resampled with soxr flagged none of 150 bona fide utterances (`paper_results/audio_codec_dev/resampling_diagnostic.json`).
- **Status (2026-10-28):** The LCNN no longer decides the audio verdict by default: pellav2 does (`AUDIO_PELLAV2_IN_VERDICT=true`), and on the same re-encoded LA eval clips it flags 0-2 % of genuine speech after MP3, Opus and resampling (`evaluation/AUDIO-PELLAV2-01/results.json`, `codec_robustness`). This issue applies again if the LCNN decides (pellav2 disabled or unavailable). pellav2's own limits are #16.
- **Impact:** Most real recordings are not 16 kHz uncompressed, so whenever the LCNN decides the audio verdict it calls most genuine real-world speech AI-generated, and a video's audio track can push the video score up. A codec- and resampling-augmented model is being trained under `paper/config/audio_codec_plan.json` (amendment v2); `AUDIO_CODEC_GUARD` can withhold the audio verdict for the affected formats.

### 15. The API's audio probability is rounded to four decimals
- **Description:** `analyze_audio` returns `round(p, 4)`. On the LA eval sample 2,024 of 4,004 utterances report exactly 0 and 442 exactly 1, so the returned value ranks them worse (AUC 0.973) than the model's own probability (AUC 0.986; `results/pipeline_eval.json`). Verdicts use the unrounded value and are unaffected.
- **Impact:** Anyone ranking or thresholding the API's `fake_probability` loses resolution near 0 and 1.

### 16. pellav2 (the audio verdict model) fails on neural and narrowband codecs and some attacks
- **Description:** pellav2 is a pretrained detector whose training data is not published. On an ASVspoof 5 eval sample (`evaluation/AUDIO-PELLAV2-01-ASVSPOOF5/results.json`) its EER is 18.5 %; at its threshold it flags 17.3 % of genuine speech and misses 19.5 % of fakes. Genuine speech passed through the EnCodec neural codec is flagged 58-68 % of the time (C04, C07), and 9-22 % after narrowband codecs (C08-C10). It catches 7 % of attack A27, 21 % of A32 and 47 % of A30. On re-encoded ASVspoof 2019 LA eval clips it flags 14 % of genuine speech after AAC at 32 kbit/s (`evaluation/AUDIO-PELLAV2-01/results.json`, `codec_robustness`). Only the first 32 s of a clip are scored.
- **Tried:** a codec-augmented fine-tune cut false alarms on ASVspoof 5 genuine speech from 15.0 % to 4.0 % but also cut detected fakes from 77.0 % to 54.0 %, so it is not the default (`evaluation/E2E-03`, `docs/research/EVALUATION.md`). A second fine-tune with 2,500 more genuine LibriSpeech clips: false alarms 15.0 % -> 4.7 %, detected fakes 77.0 % -> 62.7 %; also not the default (`evaluation/AUDIO-FT2-01`).
- **Impact:** A verdict on phone-call, VoIP or neural-codec audio is much less reliable than the ASVspoof 2019 figures suggest; the scope note on every audio result says so. Because the training data is unknown, the ASVspoof 2019 figures may be optimistic if it was trained on that set. It has not been measured on the team's own phone and WhatsApp recordings (`--data` in `scripts/eval_audio_detector.py`).

- **Phone-quality note:** narrowband audio (energy above 4 kHz cut off, as after a phone or VoIP codec) is detected and every such result carries a reliability note. Withholding 'fake' verdicts on it was measured on ASVspoof 5 (real called MANIPULATED 15.0 % -> 11.7 %, fakes caught 77.0 % -> 49.0 %; `evaluation/QUICK-GUARDS-01/audio_narrowband_guard_asvspoof5.json`) and is off (`AUDIO_NARROWBAND_GUARD`).

### 17. The newest image generators are mostly INCONCLUSIVE, not flagged
- **Description:** On held-out test images (`evaluation/E2E-02/summary.json`, `sets.image_newest_generators`) the image verdict calls 44.0 % of FLUX.2 / GPT Image 2 / Nano Banana 2 / Qwen Image 2.1 images MANIPULATED, 44.4 % INCONCLUSIVE and 11.6 % AUTHENTIC; GPT Image 2 46/195 and Nano Banana 2 8/192 are flagged. 19.3 % of that set's real photos are INCONCLUSIVE. The original Community Forensics scores these generators as real and outvotes the fine-tuned model; the fine-tuned model alone would flag more of them but scored 6.4 % of COCO test photos as AI (`evaluation/COMMFOR-FT-01/old_v3.json`).
- **Impact:** An image from a current generator is usually reported as "cannot confirm", not as AI-generated. No real test photo was called MANIPULATED. A larger fine-tune (v4, `evaluation/COMMFOR-FT-02`) flags 84 % of these generators but wrongly calls 2.0 % of COCO photos MANIPULATED and misses most small thumbnails, so it is not the default (see `docs/research/EVALUATION.md` section 5).

- **Optional rule:** `IMAGE_FT_OVERRIDE_AT=0.97` lets the fine-tuned model alone flag an image. On the test sets it raises newest-generator images called MANIPULATED from 44 % to 69 % (GPT Image 2 46 -> 132 of 195, Nano Banana 2 8 -> 52 of 192) but real COCO photos from 0 to 7 of 296 (`evaluation/QUICK-GUARDS-01/image_ft_override.json`), so it is off by default.

### 18. Composites and local edits are not part of the image verdict
- **Description:** The three AI detectors look at whole-image generation; an edited region pasted into a real photo is often scored as real. TruFor localises such edits (AUC 0.962 on controlled splices, `evaluation/TRUFOR-01/results.json`) but is shown, not used in the verdict, because it flags 10 % of re-compressed social-media photos in `accuracy_test`.
- **Impact:** A composite with no AI-generated pixels can be reported "No manipulation detected"; the TruFor heatmap on the result page is then the evidence to check.

### 19. Video: heuristic stages are unvalidated; fully generated video is mostly missed
- **Description:** On DFD (`evaluation/VIDEO-GEND-01/summary.json`, `stage_diagnosis`) rPPG flags 70-80 % of real and of fake videos and LipForensics 78-90 %; neither separates them (balanced accuracy 0.44-0.52). They are shown as context and no longer force verdicts. GenD was measured on face-swap video only (DFD); fully AI-generated video, talking-head generators and phone or WhatsApp recordings have no labelled test here.
- **Labelled:** a video judged AI-generated by the scene detectors alone now says the detection is not validated on video.
- **Measured:** 14 of 80 Veo 3 / HunyuanVideo clips were called MANIPULATED (Veo 3 10/40, HunyuanVideo 4/40), 11 INCONCLUSIVE, the rest AUTHENTIC (`evaluation/VIDEO-AIGEN-01/summary.json`).
- **Impact:** A fully generated video is judged by the scene AI detectors averaged over 8 frames, which are image models, and is usually reported as authentic.
- **Available, off by default:** an AI-video detector trained here catches 40 of 40 held-out Veo 3 clips in the full pipeline but also flags 2 of 40 real DFD clips (`evaluation/AIVIDEO-01`); its score is shown on every video result, and `AIVIDEO_IN_VERDICT=true` lets it decide. With GenD in the verdict, 1 of 40 held-out real DFD videos was called MANIPULATED.

## Resolved Issues

### No trained face-swap detector; video timeline used the StyleGAN face model (fixed 2026-10-29; were #10, #11)
- GenD (pretrained, MIT) scores face frames; the mean over frames is in the video verdict and the per-frame timeline plots GenD scores. On 400 DFD videos its face AUC is 0.941 against 0.533 for the old checkpoint (`evaluation/VIDEO-GEND-01/results.json`). The StyleGAN face checkpoint (#9) is still shown for images.

### JWT tokens stored in localStorage (fixed 2026-10-29; was #2)
- Login sets an httpOnly, SameSite=Lax cookie (`backend/app/routers/auth.py`); the frontend sends it on every request (`credentials: 'include'` in `frontend/src/lib/api.js`, `xhr.withCredentials` for uploads, `AuthedImage.jsx` for evidence images) and stores no token. Report downloads and the live-status WebSocket use the signed 5-minute links from `POST /api/jobs/{id}/links`. Only the non-secret user profile is cached in localStorage. Checked by uploading through the site and downloading every PDF via the signed link.

### Untrained audio branches and standards claims in outputs (fixed 2026-10-22, branch `fix/p1-honest-outputs`)
- The audio model stage reported a random-weight "Sinc-RawNet" score and "WavLM layer 18" / "Whisper layer 4" scores that were an FFT smoothness formula (the second 0.92 x the first + 0.04); none of these models ran. All three, and the typology and generator-family breakdowns built on them, were removed. Without the trained LCNN, audio results are now marked experimental.
- The audio decision claimed a conformal guarantee (alpha = 0.01) and reported likelihood ratios that were constants (25,000 / 450 / 0.0001). Removed.
- The PDF, the audio vault and the API description claimed ISO/IEC 27037/27042, SWGDE and Daubert compliance, write-blocker access, and suitability for cybercrime complaints. Removed.
- Video generator attribution matched keywords in the file name ("sora", "veo", ...). Removed; the attribution is labelled unvalidated.

### `checkpoints/audio_detector.pt` was trained on synthetic tones (retired 2026-10-22, branch `ml/audio-asvspoof`)
- `scripts/run_audio_pipeline.ps1` trained it on NumPy-generated clips from `scripts/generate_massive_audio_dataset.py` (low-frequency modulation as "speech", high-frequency artefacts as "TTS"), which is why it reported AUC 1.0 and EER 0. Both scripts are in `scripts/archive/`, the audio steps were removed from `scripts/run_massive_training_pipeline.ps1`, and the backend no longer loads the checkpoint (the file is kept, unchanged).
- The audio model is the LCNN trained on ASVspoof 2019 LA with the official protocols (`ml/training/train_asvspoof.py`); its eval results are in `results/audio_eval.json` and `paper_results/audio_asvspoof2019la/`.

### AI images reported "Authentic Camera Photograph" (fixed 2026-10-29)
- On the COCO + Synthbuster test half, AI images were called AUTHENTIC 21.5 % of the time and every low score was labelled an authentic camera photograph, though no test file carried camera metadata. Community Forensics now counts in the verdict (original plus a fine-tuned copy), and without camera metadata AUTHENTIC needs P(AI) < 0.02 and is labelled "No manipulation detected (origin unverified)". Same test half now: 0.1 % AI called AUTHENTIC, 98.4 % called MANIPULATED, no real photo called MANIPULATED (`evaluation/E2E-01` vs `evaluation/E2E-02`).

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
