# Paper-upgrade status

Branch `paper-upgrade`, started from `main` at `1de4b2e`. Rules: `CLAUDE.md`.
Plan: `PLAN.md`. Phase prompts: `GOAL.md`. External resources: `RESOURCES.md`.

Last updated: 2026-10-14.

## Done

### Phase 0: set-up and baseline audit (commit `7c6f9ce`)
- Branch, `CLAUDE.md`, `PLAN.md`, `GOAL.md`; `paper/` and `paper_results/` skeletons; `ml/provenance.py` with tests; `DATA_STATEMENT.md`.

### Resources gathered (2026-10-14; details and checksums in `RESOURCES.md`)
- ASVspoof 2019 LA downloaded from Edinburgh DataShare to `C:\deepsentinel_data` (it was not on this machine), with the README, licence, evaluation plan and challenge paper.
- Official ASVspoof EER / t-DCF code kept outside the repository (no licence in its repository) and used to cross-check ours.
- UnivFD and CNNDetection official code and weights in `C:\deepsentinel_data\baselines`; wrappers verified against the official code paths.
- Synthbuster downloaded and verified (MD5 matches Zenodo): 9,000 PNGs, 1,000 from each of nine generators; not yet extracted.
- COCO val2017 and In-the-Wild located with sizes, checksums and licences; download commands in `RESOURCES.md`.
- References for every dataset, baseline and statistical method checked on Crossref (DOIs in `RESOURCES.md`).
- H560 searched for on C:, D: and Google Drive: not found. A paper draft exists as a Google Doc (link in `RESOURCES.md`); no LaTeX source found.

### Phase 1: ASVspoof 2019 LA protocol pipeline (done)
- `ml/preprocessing/build_asvspoof2019_la.py`: manifest from the three official CM protocol files; checks files, sample rate, utterance and speaker split integrity, attack design and the official totals; records protocol sha256s.
- `ml/preprocessing/asvspoof_features.py`: `logmel` (the serving function, 64 bands) and `lfcc` (20 + deltas + double deltas, 20 ms / 10 ms, 512-point FFT); 4 s windows (repeat if short; consecutive windows plus the tail if long); resumable float16 cache.
- `ml/training/asvspoof_dataset.py`: datasets returning (features, label, utt_id); window 0 for training, all windows for scoring.
- Tests: `backend/tests/test_asvspoof_pipeline.py` (parser, split integrity, attack sets, windows, front ends, cache round trip and resume).

### Phase 2: LCNN on ASVspoof 2019 LA (done 2026-10-22; results under Measured)
- Runs (2026-10-22, inside the agent session at your request): logmel and lfcc with seed 0 in parallel, then lfcc seeds 1 and 2 in parallel; about 23 s per epoch, 6–12 minutes per run with early stopping.
- Dev-based selection committed alone in `0d74dc1` (`paper/config/audio_model_selection.json`), before any eval scoring; eval then scored once per seed, all three at that commit (`paper_results/audio_asvspoof2019la/eval_log.csv`).
- `ml/evaluation/asvspoof_metrics.py`: EER and minimum normalised t-DCF exactly as in the 2019 evaluation plan; matches the official code to 1e-12 on random scores with ties.
- `ml/training/train_asvspoof.py`: LCNN from `build_audio_model`, weighted loss (or balanced sampler), epoch chosen by dev EER, resumable, refuses to overwrite any checkpoint.
- `ml/evaluation/eval_asvspoof.py`: per-utterance scores (higher = bona fide), pooled and per-attack EER, AUC, min t-DCF with the organisers' ASV scores; eval scoring needs `--confirm-final-eval` and a committed dev-based selection, and is logged.
- `ml/evaluation/select_asvspoof_frontend.py`: the dev-only front-end choice and the frozen list of seed checkpoints.
- `paper/analysis/audio_asvspoof_report.py`: mean and SD over seeds, LaTeX tables, DET figure, `INDEX.md` rows, from saved files only.
- `paper_results/audio_asvspoof2019la/baselines.md` and `.json`: official baselines B01 and B02, read from Table 1 of the challenge paper itself.
- Tests: `test_asvspoof_metrics.py` (EER and t-DCF known answers, official-code agreement) and `test_asvspoof_training_loop.py` (one epoch, dev scoring, overwrite and eval guards on a fake corpus).
- Full feature cache built for train, dev and eval, both front ends (15 GB, about 710 utterances/s with 24 workers).
- Smoke test on the real data, both front ends: 2,000 random training utterances, 1 epoch, full dev scoring with min t-DCF from the organisers' dev ASV scores, about 10 s per epoch and 25 s per run. Outputs went to a scratch folder; they are **not** results (one epoch on 8 % of the training data) and are not in `paper_results/`.
- Estimate for a full run (30 epochs maximum, early stop after 10 epochs without a dev gain): about 15–20 minutes on the RTX 5070, extrapolated from the smoke epoch.

### Phase 4: image evaluation harness (code done; H560 blocked)
- Manifest format in `paper/README.md`; `ml/evaluation/eval_image_detectors.py` (per-image scores, uncropped scores when borders were cropped, extra scorers, `--end-to-end` verdicts and rules, resumable, errors logged, float32 enforced, detector revisions recorded).
- `ml/evaluation/stats.py`: stratified bootstrap AUC intervals, DeLong (fast midrank), Wilson, ECE, McNemar.
- `paper/analysis/image_metrics.py`: metrics, LaTeX tables, reliability diagrams and `INDEX.md` rows per condition.
- Smoke test with the real detectors on 4 images (scratch output, not a paper number): GPU, float32, detector A revision `4ae1822603cb1ec980c217cfde1ef1b8e0477a16`, detector B revision `b37fede8562cb72b89ec201c0987f96ba21b518a`; about 50 ms per image for the scene scores and 250 ms end to end after warm-up.
- Tests: `test_paper_stats.py`, `test_image_eval_harness.py`.

### Phase 3 preparation (legacy audio signals; nothing changed in the backend)
- `ml/evaluation/audio_heuristics_dev.py`: balanced dev subsample (1,000 bona fide, 1,000 spoofed spread over A01–A06, seed 0) and, per utterance, every legacy signal (glottal, coarticulation, ENF/mains hum, splice timeline, model-stage branches, R_synth, R_tamper, final probability and verdict) from the full `run_comprehensive_audio_forensics`; resumable; torch seeded for the untrained SincRawNet. Test: `test_audio_heuristics_subsample.py`.
- Timing on 20 dev files (scratch output): 1.34 s per utterance, so about **45 minutes** for all 2,000. Per `GOAL.md`, the full run waits for your go-ahead.
- Early observation from those 20 files only (all bona fide; not a measurement): the splice-timeline detector fired on every file, R_tamper was 0.5 and the legacy verdict was INCONCLUSIVE for all of them. The full run will show whether this holds.

### Phase 3 task 2: trained LCNN in the audio verdict, behind a setting (2026-10-22)
- `AUDIO_MODEL_SOURCE` in `backend/app/config.py`: `legacy` (default, unchanged behaviour) or `lcnn_asvspoof`. `AUDIO_LCNN_CALIBRATION_FILE` points at `paper/config/audio_calibration.json`.
- `ml/evaluation/calibrate_audio_lcnn.py` → `paper/config/audio_calibration.json` (dev only): served checkpoint = the frozen seed with the lowest dev EER, `audio_lcnn_asvspoof_lfcc_seed2.pt` (0.190 %); class-balanced Platt scaling of the mean window spoof logit, a = 1.420, b = −3.064 (p = 0.497 at the dev EER threshold). Dev is almost separable, so these probabilities are very confident; on unseen attacks they will be overconfident.
- `backend/app/ml/asvspoof_frontend.py`: windows and LFCC moved here from `ml/preprocessing/asvspoof_features.py`, which now imports them, so training and serving share one implementation. On 15 dev and 15 eval utterances the backend features (via `load_audio`, no peak normalisation) equal the cached training features bit for bit.
- `backend/app/ml/registry.py`: `get_audio_lcnn_asvspoof()` loads the checkpoint named in the calibration file and refuses it if its sha256 differs; the old `audio` entry is unchanged.
- `backend/app/ml/audio/lcnn_asvspoof.py`: LFCC of every 4 s window, float32 model, mean window logit, calibrated probability. In `lcnn_asvspoof` mode `run_comprehensive_audio_forensics` replaces the model-stage probability with it (the legacy value is kept as `legacy_fused_ai_probability`, context only); `analyze_audio` and the video pipeline pass the waveform before peak normalisation. The evidence fusion weights and thresholds are unchanged until task 6.
- Tests: `backend/tests/test_audio_lcnn_mode.py` (7): the legacy mode reproduces a reference recorded on the unchanged code (`backend/tests/fixtures/audio_legacy_reference.json`, identical across two processes); front-end shapes and float16 rounding; front end equals the training cache on real data (runs when `DEEPSENTINEL_DATA` is set); balanced Platt recovers known parameters and ignores class duplication; LCNN score equals the calibrated mean window logit; LCNN mode replaces the model stage; a checkpoint with the wrong sha256 is refused.
- **Found: inference was not strict float32.** PyTorch enables TF32 for cuDNN convolutions by default (`torch.backends.cudnn.allow_tf32 = True`), so all Phase 2 dev and eval scores used TF32 convolutions, against `CLAUDE.md` §6. Strict float32 (CPU, or GPU with TF32 off) gives identical scores on both devices, differing from the stored scores by up to 0.034 on a ±10 scale. Re-scoring **dev** in strict float32 (scratch output, not committed): EER unchanged for seeds 0 and 1, seed 2 0.1901 % → 0.1878 %; min t-DCF changes in the 4th–5th decimal; the front-end choice and the served seed are unaffected. `ml/provenance.py` now records `cudnn_allow_tf32` and `matmul_allow_tf32`. Eval not re-scored: your decision (see Blocked).

### Phase 5 preparation (nothing frozen, nothing scored)
- `ml/evaluation/baselines/`: `umm_maybe` (old detector C), `univfd`, `cnndetection`, and `verify_official.py`.
- `paper/config/freeze_image_config.py`: writes `frozen_image_config.json` (detector revisions and file hashes, weights, threshold, band, rules, border-crop constants, implementation file hashes). Not run: when to freeze is your decision (see Blocked).

### Phase 8: group-safe face manifest (2026-10-22)
- **Which script leaked.** Not `scripts/build_manifest_140k.py`, as `CLAUDE.md` and `PLAN.md` said: that script kept the faces-140k train / valid / test folders as train / val / test and added nothing else. The leak was in the old `scripts/expand_training_dataset.py` (commit `02dd9db`; fixed on `main` in `1de4b2e`). `CLAUDE.md` is corrected; `build_manifest_140k.py` is now a deprecated wrapper for the checked builder.
- **How the 164,000-image validation set was made** (reconstructed from the old code and the folder counts on disk): faces-140k train (100,000) and test (20,000) went to training and valid (20,000) to validation; every folder of derived copies was split 85 / 15 at random, file by file; every image in `backend/storage/uploads` and a local IDE upload folder was added to training as fake. 15 % of the 960,000 derived images now on disk (massive_social 660,000 + expansion_300k 300,000) is 144,000, so validation = 20,000 + 144,000 = 164,000 and training = 120,000 + 816,000 + 9 = 936,009, both exactly as in `checkpoints/image_detector.summary.json`; the 9 are consistent with the upload folders. The committed old script reads only `massive_social`, so `expansion_300k` was presumably inside it at the time; the repository cannot confirm this.
- **Where the copies come from** (`ml/evaluation/face_derived_sources_audit.py` → `paper_results/face_manifest_audit/derived_sources.json`): copy `<folder>_<i>` is made from the `i mod 50,000`-th sorted faces-140k **train** image of its class. In 11 folders, 150 of 150 sampled copies per folder are within 4 pHash bits of that image (an unrelated face: at least 12 bits). `inpaint_fake` (40,000), checked file by file on the pixels outside the blurred patch: 35,000 are copies of train/**real** images and 5,000 of train/fake images. So all 660,000 copies come from training faces, and under the old split every validation copy's source was in training.
- **Label finding:** 35,000 of the 40,000 `inpaint_fake` images are real FFHQ photographs with a blurred central patch, labelled fake. The current generator code uses fake sources, so these files came from an earlier, uncommitted version of it.
- **Fix** (`scripts/expand_training_dataset.py`): each massive_social copy gets its source face's group (`faces140k_<class>_<stem>`) and split; `inpaint_fake` copies are matched to their source class by pixels outside the patch (refused if no candidate matches); `expansion_300k` (no generator script, sources unknown) is excluded unless `--include-unverified-derived`; `--extra` data is split with `split_by_group` (stratified); any file under an `uploads` or `.user_uploaded` folder, any group or file in two splits, makes the builder refuse to write. `--raw-root` replaces the fixed data path. On the real data it writes 800,000 rows: train 380,000 real + 380,000 fake, val 10,000 + 10,000, test 10,000 + 10,000 (the official faces-140k folders only). Built into a scratch folder; `data/processed/faces/manifest.csv` was not overwritten.
- Test: `backend/tests/test_face_manifest.py` (9 tests: official splits kept, test never in training, copies follow their source, inpaint source matching and refusal, unverified sets excluded, `--extra` split by group, uploads refused, group / file leak checks).
- Not done: retraining EfficientNet-B0 on the corrected manifest (GOAL: only if you ask).

### Phase 7 preparation: video timing (2026-10-22; nothing changed in the backend)
- `ml/evaluation/video_pipeline_timing.py` → `paper_results/video_timing/timing.json`: three synthetic 640×480, 30 fps clips of StyleGAN faces (10, 30, 60 s; no real person, no audio track because ffmpeg is not installed), run through `analyze_video`, then the extra cost of a dense 10 s window at 10 fps around the keyframe. A decision aid, not a paper result; another CPU-bound job ran at the same time.
- Now (1 fps, at most 32 frames): 1.7 s, 4.1 s and 4.2 s for the 10, 30 and 60 s clips; the per-frame face model (stage 3, 0.6–1.9 s) and optical flow (stage 9, 0.4–1.4 s) take most of it. The audio stage adds 1.9–4.0 s for 10–60 s of speech.
- Dense window for pulse and flow: +7.5 to +8.0 s per clip (face detection on 100 frames 2.6–3.0 s, optical flow 4.7–4.8 s, pulse 0.1 s), so about 3–5× the current video time.
- See audit finding 13: at 1 fps the pulse and flow results carry no physiological or motion meaning.
- **Recommendation (needs your choice; GOAL asks before implementing):** Option B, with the pulse and flow stages taken out of the video score and kept as context, and the pulse stage reporting "not measurable" below 5 fps instead of clamping. Reason: no labelled video data exists to show either stage works even when sampled densely, so the extra 8 s per video would buy plausibility, not evidence. Dense sampling is affordable if you prefer it (or if Option A with FakeAVCeleb is chosen later).

### Phase 9 (part): hard-coded paths removed (2026-10-22)
- The 8 files in audit finding 7 now derive the repository root from their own location (`Path(__file__).resolve().parents[k]`; the PowerShell script uses `$PSScriptRoot`); checked to resolve to the same folders as before. `git grep "C:/Users"` over `*.py`, `*.ps1`, `Makefile` and `*.toml` finds nothing. `checkpoints/*.summary.json` still record absolute paths; they describe past runs and were left unchanged.

## Measured

### Environment (Phase 0)
Python 3.11.9; torch 2.12.0.dev20260408+cu128 (nightly); CUDA 12.8; NVIDIA GeForce RTX 5070, 12,227 MiB, driver 595.95, `sm_120` supported. `.env` sets `DEVICE=cuda`. 64 GB RAM, 32 logical CPUs.

### ASVspoof 2019 LA manifest (Phase 1)
From `data/processed/asvspoof2019_la/dataset_summary.json` (copy in `paper_results/audio_asvspoof2019la/dataset_summary.json`, indexed in `paper_results/INDEX.md`). The totals match the official protocol exactly:

| Split | Utterances | Bona fide | Spoof | Attacks | Protocol speaker ids | Longer than 4 s |
|---|---|---|---|---|---|---|
| train | 25,380 | 2,580 | 22,800 | A01–A06, 3,800 each | 20 | 6,991 |
| dev | 24,844 | 2,548 | 22,296 | A01–A06, 3,716 each | 20 | 7,440 |
| eval | 71,237 | 7,355 | 63,882 | A07–A19, 4,914 each | 67 | 15,845 |

- Every listed file exists, is 16 kHz mono, and no utterance or speaker id appears in two splits.
- The flac folders also hold ASV enrolment files not in the CM protocols (dev 24,986 files, eval 71,933), which the manifest ignores, as intended.
- **To note:** the corpus README describes 20 / 10 / 48 speakers, while the CM protocols list 20 / 20 / 67 speaker ids. Reported as found; not investigated further.
- ASV scores for t-DCF are present (`ASVspoof2019.LA.asv.{dev,eval}.gi.trl.scores.txt`, with per-attack spoof scores), so min t-DCF will be computed, not skipped.
- Feature smoke test (first 200 utterances per split, both front ends): log-mel values in [-80, 0] dB, LFCC finite, shapes (64, 401) and (60, 401).

### ASVspoof 2019 LA: LCNN results (Phase 2)
Dev (front-end choice, from `paper_results/audio_asvspoof2019la/dev_runs/*/run_config.json`):

| Run | Best epoch | Dev EER | Dev min t-DCF |
|---|---|---|---|
| logmel seed 0 | 7 | 0.462 % | 0.0126 |
| lfcc seed 0 | 4 | 0.354 % | 0.0113 |
| lfcc seed 1 | 23 | 0.314 % | 0.0104 |
| lfcc seed 2 | 20 | 0.190 % | 0.0042 |

Selected front end: **lfcc** (lower seed-0 dev EER, the rule fixed beforehand).

Eval, 71,237 utterances, 3 seeds (`paper_results/audio_asvspoof2019la/metrics.json`, `summary.*`; per seed in `eval/*_eval_metrics.json`):

| | EER (%) | min t-DCF | AUC |
|---|---|---|---|
| Seeds 0 / 1 / 2 | 5.99 / 4.99 / 4.78 | 0.1268 / 0.1020 / 0.1025 | 0.978 / 0.984 / 0.986 |
| Mean ± SD | **5.26 ± 0.65** | **0.110 ± 0.014** | 0.983 ± 0.004 |
| B01 CQCC-GMM (published) | 9.57 | 0.2366 | |
| B02 LFCC-GMM (published) | 8.09 | 0.2116 | |

- Per attack (mean EER %): A07 0.32, A08 1.74, A09 0.10, A10 0.78, A11 0.41, A12 0.30, A13 0.39, A14 2.44, A15 2.74, A16 0.55, **A17 26.90 ± 3.87**, A18 2.06, A19 3.53. A17 is the clear weakness; all other attacks are below 4 %.
- Dev EER (0.19–0.35 %) is far below eval EER (4.8–6.0 %): dev contains only the training attacks A01–A06, eval only unseen attacks A07–A19, so dev is no estimate of eval performance.
- Tables `paper/tables/audio_asvspoof_pooled.tex`, `audio_asvspoof_per_attack.tex`; figure `paper/figures/audio_asvspoof_det.pdf`; rows in `paper_results/INDEX.md`.
- The backend serves log-mel features; the selected model uses LFCC, so Phase 3 needs an LFCC front end in the backend. The model was also trained on waveforms **without** the peak normalisation `analyze_audio` applies, which changes the LFCC energy coefficient; Phase 3 must feed it the un-normalised waveform.

### Backend tests
Phase 0: 178 passed, 11 skipped. After Phases 1, 2 and 4 code: 244 passed, 12 skipped (the 11 `pypdf` report tests, plus the real-manifest test, which now runs and passes). After Phase 3 preparation and Phase 8 (2026-10-22): 256 passed, 11 skipped (`pypdf`). `pypdf` is in no requirements file.

## Audit findings (facts for later phases and for the paper's audit section)

1. **The H560 numbers have no supporting script or files.** The figures in `backend/app/ml/image_pipeline.py` (lines 55–63), `docs/models/MODEL_CARD.md` and `CHANGELOG.md` (AUC 0.984, 0.973, 0.836, 0.469; 2.0 %, 88.3 %, 6.7 %) were produced by no script in the repository, and neither the images nor per-image scores were found.
2. **`checkpoints/audio_detector.pt` was trained on synthetic tones.** Its validation support (12,582 + 12,582) equals the `val` count of `data/processed/audio_massive`, generated with NumPy by `scripts/generate_massive_audio_dataset.py`; it reports AUC 1.0 and EER 0.0 there. It was also trained on 80-band log-mels (`AudioWindowDataset` default), not the 64 bands the documentation states.
3. **The audio verdict does not use the LCNN.** Confirmed for Phase 3, with corrections to the summary in `CLAUDE.md`:
   - `analyze_audio` loads the LCNN through `get_audio_model()` only for `weights_status` and a note.
   - The probability is `0.45 x "SSL" + 0.30 x SincRawNet + 0.25 x tabular` (`backend/app/ml/audio/models_arch.py`, `classify_audio`), then `evidence_fusion.py`.
   - The "WavLM layer 18" and "Whisper layer 4" probabilities do not come from WavLM or Whisper: both are a high-frequency spectral-smoothness formula over the first 16,384 samples, and the "Whisper" value is `0.92 x WavLM + 0.04`. The output keys name models that are never loaded.
   - `SincRawNet` is built with random weights and never loads a checkpoint, so its output depends on the random initialisation of each process: the same 4 s test clip scored 0.506 and 0.484 in two fresh processes (demonstration run on 2026-10-14; Phase 3 will quantify it on dev).
   - The tabular branch is hand-set rules (glottal score, jitter/HNR, LFCC energy).
4. **The "speaker-disjoint" synthetic audio split is per clip** (167,772 "speakers" for 167,772 windows).
5. **`accuracy_test/` is not independent:** `backend/scripts/build_real_dataset.py` copies it from `massive_social`, filtered copies of faces-140k training images.
6. **Two manifest builders exist:** `scripts/expand_training_dataset.py` already keeps derived copies training-only; `scripts/build_manifest_140k.py` is the leaky one (Phase 8). *Corrected in Phase 8:* the leak was in the old `expand_training_dataset.py`; `build_manifest_140k.py` never leaked (see the Phase 8 section).
7. **Hard-coded `C:/Users/STUDENT/...` paths** (Phase 9): `scripts/generate_massive_audio_dataset.py:17`, `scripts/generate_massive_social_dataset.py:29`, `scripts/run_massive_training_pipeline.ps1:2`, `backend/scripts/build_real_dataset.py:10-11`, `research_archive/scripts/run_phase17_training.py:40`, `run_phase17_5_validation.py:30-31`, `run_phase17_8_fusion.py:38-39`, `run_phase17_8r_holdout.py:31-32`; `checkpoints/*.summary.json` store absolute paths.
8. **Licences:** detector B (cc-by-nc-3.0), CNNDetection and Synthbuster (CC BY-NC-SA 4.0) and RAISE (non-commercial research and education) are non-commercial; detector B also runs in the deployed platform. In-the-Wild's licence is stated differently on its page (Apache 2.0) and its Hugging Face card (CC BY-SA 4.0).
9. **Detector A's training data is not stated** on its model card (threat to validity).
10. **torch is a nightly build**; Phase 9 should pin it.
11. **The audio "conformal prediction" is not implemented.** `backend/app/ml/audio/evidence_fusion.py` labels its decision step "Conformal Prediction Set (alpha = 0.01)" with the comment "Bounded false positive rate: P(Authentic flagged as fake) <= 1%" and returns `conformal_alpha_guarantee: 0.01`, but the thresholds are fixed constants (0.35 and 0.70), nothing is calibrated on held-out data, and `alpha` is never used. No such guarantee can be claimed.
12. **The audio "likelihood ratios" are constants** (25,000, 450 or 0.0001 by verdict), not computed from data.
13. **The video pulse (rPPG) stage misreads its own frame rate.** `backend/app/ml/video/rppg_biometrics.py:102` clamps the measured sampling rate to at least 5 fps, but the pipeline samples at 1 fps, so every frequency is read 5 times too high: slow changes at 0.15–0.5 Hz (head motion, lighting drift) land in the 0.75–2.5 Hz "cardiac band" and are reported as a heart rate. At 1 fps no frequency above 0.5 Hz can be measured at all. On the synthetic StyleGAN-face clips of the Phase 7 timing it reported `PHYSIOLOGICAL_PULSE_CONFIRMED` for 2 of 3 clips. The optical-flow stage likewise compares frames 1 s apart, not consecutive frames.

## Blocked (needs you)

- **TF32 and the eval numbers:** keep the Phase 2 eval results (computed with TF32 convolutions, PyTorch's default) and state this in the paper, or re-score eval once in strict float32 (logged with the reason; overwrites the committed eval score files, old ones stay in git history). On dev the difference is at most 0.002 percentage points of EER.
- **Phase 3 heuristics table:** approve which audio signals stay in the synthesis risk (rule: bootstrap 95 % lower bound above 0.60) before `evidence_fusion.py` changes (task 6).
- **Phase 7 option:** pulse and flow out of the video score (recommended) or dense sampling (+about 8 s per video).
- **H560:** where are the 560 images, or are they lost? If lost, the image configuration can be frozen as it is now (`paper/config/freeze_image_config.py`) and the paper must say the H560 figures cannot be reproduced.
- **RAISE-1k:** the download form needs your name, affiliation and email (see `RESOURCES.md`).
- `pypdf` for the 11 skipped report tests (before Phase 7 changes the report).

## Next

1. After your approval of the heuristics table: Phase 3 task 6 (synthesis-risk weights and thresholds for the LCNN mode, on the dev subsample only, into `paper/config/frozen_audio_config.json`), then task 7 (end-to-end eval scoring, at least 4,000 stratified eval utterances; about 1.3 s each, so about 1.5 hours for 4,000: yours to run or approve).
2. Phase 7 after your choice of option.
3. Decide H560; then freeze the image configuration and build T2 (Synthbuster is downloaded; RAISE-1k needs your form; team photographs).
4. Optional (Phase 8, only if you ask): retrain EfficientNet-B0 on the corrected face manifest.
