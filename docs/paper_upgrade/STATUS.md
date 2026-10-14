# Paper-upgrade status

Branch `paper-upgrade`, started from `main` at `1de4b2e`. Rules: `CLAUDE.md`.
Plan: `PLAN.md`. Phase prompts: `GOAL.md`.

Last updated: 2026-10-14, end of Phase 0.

## Done

### Phase 0: set-up and baseline audit (2026-10-14)
- Created branch `paper-upgrade`; copied `CLAUDE.md` to the repository root and `PLAN.md`, `GOAL.md` to `docs/paper_upgrade/` (byte-identical to `DeepSentinel_Paper_Upgrade_Kit`).
- Created `paper/` (`config/`, `analysis/`, `tables/`, `figures/`) and `paper_results/`, each with a README, plus an empty `paper_results/INDEX.md`.
- Added `ml/provenance.py` (`collect_provenance`, `sha256_file`) and `backend/tests/test_provenance.py` (4 tests).
- Wrote `docs/paper_upgrade/DATA_STATEMENT.md`: sources, licences (read from the source pages on 2026-10-14, or marked "to be checked") and split policy for every dataset and third-party model in the plan, plus the local data that must not be used as evidence.
- No model or pipeline behaviour was changed.

## Measured

### Environment (Phase 0)
| Item | Value |
|---|---|
| Python | 3.11.9 (`.venv`) |
| torch | 2.12.0.dev20260408+cu128 (a **nightly** build), torchvision 0.27.0.dev20260407+cu128 |
| CUDA build | 12.8; `torch.cuda.is_available()` = True |
| GPU | NVIDIA GeForce RTX 5070, compute capability 12.0, 12,227 MiB, driver 595.95 |
| GPU support | `sm_120` is in `torch.cuda.get_arch_list()`; a test matmul on the GPU ran. No install needed. |

### Backend tests (Phase 0)
`cd backend; python -m pytest -q`: **178 passed, 11 skipped**, 0 failed (including the 4 new provenance tests). All 11 skips are PDF-report tests in `tests/test_report.py` that need `pypdf`, which is not installed and is not listed in any `backend/requirements*.txt`.

### Data search (Phase 0)
- `DEEPSENTINEL_DATA` is **not set**.
- The repository's `data` link points to `C:\Users\STUDENT\Downloads\FORENSICS (2)\FORENSICS\data` and contains `raw/faces-140k`, `raw/massive_audio`, `raw/massive_social`, `raw/expansion_300k`, `processed/audio`, `processed/audio_massive`, `processed/faces`.
- **ASVspoof 2019 LA: not found.** No file or folder matching `*ASVspoof2019*` under `C:\` (depth 6, excluding Windows, Program Files and AppData) or `D:\` (depth 6). Protocol files, flac folders and ASV score files are all missing.
- **H560: not found.** No folder of 560 images, and no folder named after its generators, under `C:\Users\STUDENT` (depth 6). `evaluation/` holds 96 images, `accuracy_test/` 120, `golden_test/` none.

## Audit findings (facts for later phases)

1. **The H560 numbers have no supporting script or files.** The figures in `backend/app/ml/image_pipeline.py` (lines 55–63), `docs/models/MODEL_CARD.md` and `CHANGELOG.md` (AUC 0.984, 0.973, 0.836, 0.469; 2.0%, 88.3%, 6.7%) were not produced by any script in the repository, and neither the images nor per-image scores are archived. Phase 4 can only re-measure them if the images are found.
2. **`checkpoints/audio_detector.pt` was trained on synthetic tones.** `data/raw/massive_audio` is generated with NumPy by `scripts/generate_massive_audio_dataset.py`. The checkpoint's validation support (12,582 + 12,582 = 25,164) equals the `val` count of `data/processed/audio_massive`, where it reports AUC 1.0 and EER 0.0.
3. **The "speaker-disjoint" audio split is per clip.** `data/processed/audio*/dataset_summary.json` reports 167,772 speakers for 167,772 windows.
4. **`accuracy_test/` is not independent.** `backend/scripts/build_real_dataset.py` copies it from `massive_social`, which consists of filtered copies of faces-140k training images.
5. **Two manifest builders exist.** `scripts/expand_training_dataset.py` already keeps derived copies training-only and the faces-140k test split held out. `scripts/build_manifest_140k.py` is the leaky one named in `CLAUDE.md` (Phase 8).
6. **Hard-coded `C:/Users/STUDENT/...` paths** (Phase 9): `scripts/generate_massive_audio_dataset.py:17`, `scripts/generate_massive_social_dataset.py:29`, `scripts/run_massive_training_pipeline.ps1:2`, `backend/scripts/build_real_dataset.py:10-11`, `research_archive/scripts/run_phase17_training.py:40`, `run_phase17_5_validation.py:30-31`, `run_phase17_8_fusion.py:38-39`, `run_phase17_8r_holdout.py:31-32`. `checkpoints/*.summary.json` also store absolute checkpoint paths.
7. **Non-commercial licences.** Detector B (`Organika/sdxl-detector`, cc-by-nc-3.0), CNNDetection (CC BY-NC-SA 4.0) and Synthbuster (CC BY-NC-SA 4.0) are non-commercial. That fits an academic paper and project, but detector B also runs in the deployed platform.
8. **Detector A's training data is not stated** on its model card, so overlap with any test set cannot be ruled out; this belongs in threats to validity.
9. **torch is a nightly build.** It is recorded by `ml/provenance.py`; Phase 9 should pin it in `requirements-lock.txt`.

## Blocked

- **Phase 1–3 (audio): ASVspoof 2019 LA is not on this machine.** Needed: the extracted `LA` folder (protocol files `ASVspoof2019.LA.cm.{train.trn,dev.trl,eval.trl}.txt`, `ASVspoof2019_LA_{train,dev,eval}/flac/`, and the ASV score files for t-DCF). Source: `LA.zip` (7.12 GB) from https://doi.org/10.7488/ds/2555. Waiting for the user's path, or for the download.
- **Phase 4 (H560 re-run): the 560 images are not on this machine.** Waiting for the user's path, or confirmation that they are lost (then the plan relies on T2, and the paper must say the H560 figures cannot be reproduced).
- `DEEPSENTINEL_DATA` is not set.

## Next

1. User: give the ASVspoof 2019 LA path (or download `LA.zip`) and the H560 path; set `DEEPSENTINEL_DATA`.
2. Phase 1: ASVspoof 2019 LA protocol manifest and feature cache, after plan approval.
3. Start collecting T2 now (team photographs, Synthbuster and RAISE-1k download), as `GOAL.md` recommends for week 1.
4. Before Phase 7 (which changes the PDF report): add `pypdf` to `backend/requirements-dev.txt` so the 11 report tests run.
