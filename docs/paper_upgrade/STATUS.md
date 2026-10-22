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

### Phase 1: ASVspoof 2019 LA protocol pipeline (code done; data run in progress)
- `ml/preprocessing/build_asvspoof2019_la.py`: manifest from the three official CM protocol files; checks files, sample rate, utterance and speaker split integrity, attack design and the official totals; records protocol sha256s.
- `ml/preprocessing/asvspoof_features.py`: `logmel` (the serving function, 64 bands) and `lfcc` (20 + deltas + double deltas, 20 ms / 10 ms, 512-point FFT); 4 s windows (repeat if short; consecutive windows plus the tail if long); resumable float16 cache.
- `ml/training/asvspoof_dataset.py`: datasets returning (features, label, utt_id); window 0 for training, all windows for scoring.
- Tests: `backend/tests/test_asvspoof_pipeline.py` (parser, split integrity, attack sets, windows, front ends, cache round trip and resume).

### Phase 2: LCNN on ASVspoof 2019 LA (code done; runs not started)
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

### Backend tests
Phase 0: 178 passed, 11 skipped. After Phases 1, 2 and 4 code: 244 passed, 12 skipped (the 11 `pypdf` report tests, plus the real-manifest test, which now runs and passes). `pypdf` is in no requirements file.

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

## Blocked (needs you)

- **H560:** where are the 560 images, or are they lost? Phase 4 cannot re-measure the paper's image numbers without them. If they are lost, the image configuration can be frozen as it is now (`paper/config/freeze_image_config.py`) and the paper must say the H560 figures cannot be reproduced.
- **RAISE-1k:** the download form needs your name, affiliation and email (see `RESOURCES.md`).
- **Long runs:** the full LCNN trainings (Phase 2) are yours to run; commands follow in the Phase 1–2 report.
- `pypdf` for the 11 skipped report tests (before Phase 7).

## Next

1. **You run the Phase 2 trainings** (PowerShell, repository root):
   ```powershell
   $env:DEEPSENTINEL_DATA = "C:\deepsentinel_data"
   python ml\training\train_asvspoof.py --features logmel --seed 0
   python ml\training\train_asvspoof.py --features lfcc --seed 0
   python ml\evaluation\select_asvspoof_frontend.py
   # it prints the selected front end and the two commands for seeds 1 and 2; run them, then:
   python ml\evaluation\select_asvspoof_frontend.py --write
   git add paper\config\audio_model_selection.json paper_results\audio_asvspoof2019la\dev_runs
   git commit -m "Select ASVspoof front end on dev; freeze checkpoints before eval"
   ```
   Each run writes `checkpoints\audio_lcnn_asvspoof_<features>_seed<k>.pt` (not committed) and `paper_results\audio_asvspoof2019la\dev_runs\<run>\` (`train_log.csv`, `dev_scores.csv`, `dev_metrics.json`, `run_config.json`). An interrupted run continues with the same command plus `--resume`.
2. Then I score eval once per seed (`eval_asvspoof.py --confirm-final-eval`), run `paper/analysis/audio_asvspoof_report.py`, and continue Phase 3.
3. **Phase 3 heuristics run (about 45 minutes), when you approve:** `python ml\evaluation\audio_heuristics_dev.py` writes `paper_results\audio_heuristics_dev\` (`subsample.csv`, `scores.csv`, `config.json`). It does not need the LCNN; its column is added after Phase 2.
4. Decide H560; then freeze the image configuration and build T2 (Synthbuster is downloaded; RAISE-1k needs your form; team photographs).
