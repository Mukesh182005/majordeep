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
- Synthbuster, COCO val2017 and In-the-Wild located with sizes, checksums and licences; download commands in `RESOURCES.md`.
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

### Phase 4: image evaluation harness (code done; H560 blocked)
- Manifest format in `paper/README.md`; `ml/evaluation/eval_image_detectors.py` (per-image scores, uncropped scores when borders were cropped, extra scorers, `--end-to-end` verdicts and rules, resumable, errors logged, float32 enforced, detector revisions recorded).
- `ml/evaluation/stats.py`: stratified bootstrap AUC intervals, DeLong (fast midrank), Wilson, ECE, McNemar.
- `paper/analysis/image_metrics.py`: metrics, LaTeX tables, reliability diagrams and `INDEX.md` rows per condition.
- Smoke test with the real detectors on 4 images (scratch output, not a paper number): GPU, float32, detector A revision `4ae1822603cb1ec980c217cfde1ef1b8e0477a16`, detector B revision `b37fede8562cb72b89ec201c0987f96ba21b518a`; about 50 ms per image for the scene scores and 250 ms end to end after warm-up.
- Tests: `test_paper_stats.py`, `test_image_eval_harness.py`.

### Phase 5 preparation (nothing frozen, nothing scored)
- `ml/evaluation/baselines/`: `umm_maybe` (old detector C), `univfd`, `cnndetection`, and `verify_official.py`.
- `paper/config/freeze_image_config.py`: writes `frozen_image_config.json` (detector revisions and file hashes, weights, threshold, band, rules, border-crop constants, implementation file hashes). Not run: when to freeze is your decision (see Blocked).

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
6. **Two manifest builders exist:** `scripts/expand_training_dataset.py` already keeps derived copies training-only; `scripts/build_manifest_140k.py` is the leaky one (Phase 8).
7. **Hard-coded `C:/Users/STUDENT/...` paths** (Phase 9): `scripts/generate_massive_audio_dataset.py:17`, `scripts/generate_massive_social_dataset.py:29`, `scripts/run_massive_training_pipeline.ps1:2`, `backend/scripts/build_real_dataset.py:10-11`, `research_archive/scripts/run_phase17_training.py:40`, `run_phase17_5_validation.py:30-31`, `run_phase17_8_fusion.py:38-39`, `run_phase17_8r_holdout.py:31-32`; `checkpoints/*.summary.json` store absolute paths.
8. **Licences:** detector B (cc-by-nc-3.0), CNNDetection and Synthbuster (CC BY-NC-SA 4.0) and RAISE (non-commercial research and education) are non-commercial; detector B also runs in the deployed platform. In-the-Wild's licence is stated differently on its page (Apache 2.0) and its Hugging Face card (CC BY-SA 4.0).
9. **Detector A's training data is not stated** on its model card (threat to validity).
10. **torch is a nightly build**; Phase 9 should pin it.

## Blocked (needs you)

- **H560:** where are the 560 images, or are they lost? Phase 4 cannot re-measure the paper's image numbers without them. If they are lost, the image configuration can be frozen as it is now (`paper/config/freeze_image_config.py`) and the paper must say the H560 figures cannot be reproduced.
- **RAISE-1k:** the download form needs your name, affiliation and email (see `RESOURCES.md`).
- **Long runs:** the full LCNN trainings (Phase 2) are yours to run; commands follow in the Phase 1–2 report.
- `pypdf` for the 11 skipped report tests (before Phase 7).

## Next

1. Finish the ASVspoof download, extract, build the full manifest, check the official totals, and smoke-test features (Phase 1), then the 2,000-utterance training smoke test (Phase 2).
2. You run the seed-0 trainings for both front ends; then front-end selection on dev, seeds 1 and 2, freeze, eval once.
3. Decide H560; then freeze the image configuration and build T2 (Synthbuster, RAISE-1k or COCO, team photographs).
