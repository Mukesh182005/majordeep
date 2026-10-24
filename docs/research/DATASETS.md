# Datasets

Which data each model and each result in `results/` comes from. Sources,
licences, checksums and split policies are recorded in full in
[`docs/paper_upgrade/DATA_STATEMENT.md`](../paper_upgrade/DATA_STATEMENT.md);
this page is the short version. Raw data lives outside the repository
(`DEEPSENTINEL_DATA`); only manifests and per-item score files are committed.
Every count below is read from the file named next to it.

## Used for models and results

### ASVspoof 2019, logical access (LA)

- **Role:** training, selection and evaluation of the audio model (LCNN on
  LFCC), and every audio result in `results/`.
- **Source and licence:** Edinburgh DataShare, DOI 10.7488/ds/2555; ODC-By 1.0.
- **Splits:** the official countermeasure protocol files only. Train for
  training; dev for every choice (epoch, front end, calibration, verdict
  thresholds, which heuristics may carry weight); eval scored only after those
  choices were committed.
- **Counts:** `paper_results/audio_asvspoof2019la/dataset_summary.json`
  (`splits.<split>.utterances`, `.bonafide`, `.spoof`), also listed in
  `paper_results/INDEX.md`.
- **Attacks:** train and dev hold attacks A01-A06; eval holds A07-A19
  (checked by `ml/preprocessing/build_asvspoof2019_la.py`).

### 140k Real and Fake Faces (Kaggle)

- **Role:** training data of the face-crop classifier
  (`checkpoints/image_detector*.pt`). Real faces from FFHQ, fake faces from
  StyleGAN.
- **Splits:** the dataset's own train / valid / test folders. The group-safe
  manifest builder (`scripts/expand_training_dataset.py`) keeps derived copies
  in their source image's split.
- **Known problem:** the validation set the current checkpoint reports was
  built with derived copies of training images (see
  `paper_results/face_manifest_audit/derived_sources.json` and
  `docs/paper_upgrade/STATUS.md`, Phase 8), so its reported validation numbers
  are not evidence of accuracy.
- **Other use:** 20 test-folder images are the image inputs of the latency
  benchmark (`results/latency.json`); no accuracy is computed on them.

## Located, not yet used for any result

| Dataset | Intended role | Status |
|---|---|---|
| In-the-Wild (Müller et al., 2022) | Cross-dataset audio test | Licence conflict (Apache 2.0 vs CC BY-SA 4.0) unresolved; not downloaded. `results/pipeline_eval.json` records it as not run. |
| H560 (internal, 560 images) | Development set for image settings | Not found on this machine; `results/image_eval.json` records it as not run. |
| Synthbuster (Bammey, 2023) | AI-generated part of the image test set T2 | Downloaded and verified; not extracted; not scored. |
| RAISE-1k, COCO | Real part of T2 | Not downloaded. |
| FaceForensics++ (c23), Celeb-DF v2 | Face-swap video training and test | Access not granted yet; `results/pipeline_eval.json` records the video sets as not run. |

T2 is scored only after the image configuration is frozen
(`paper/config/frozen_image_config.json`, `CLAUDE.md` section 3).

## Never used as evidence

These folders exist locally but cannot support an accuracy claim
(`DATA_STATEMENT.md`, section 3):

- `data/raw/massive_audio`, `data/processed/audio*`: NumPy-synthesised tones,
  not speech. The retired `checkpoints/audio_detector.pt` was trained on them.
- `data/raw/massive_social`, `data/raw/expansion_300k`: filtered copies of
  faces-140k training images.
- `accuracy_test/`, `evaluation/V2-DIAGNOSTIC-01`: copies of training images,
  or of undocumented origin.
- Uploaded files in `storage/` and `backend/storage/`: unlabelled user data.
