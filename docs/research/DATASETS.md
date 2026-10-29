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

### ASVspoof 5 (evaluation set, sample)

- **Role:** held-out test of both audio models (`evaluation/AUDIO-PELLAV2-01-ASVSPOOF5/`). Never used for
  training, thresholds or any other choice.
- **Source and licence:** Zenodo record 14498691 (v0.1, DOI 10.5281/zenodo.14498691); ODC-By 1.0. Cite
  the ASVspoof 5 database paper and the 2024 workshop paper, as its README asks.
- **What is on disk:** the protocol archive (MD5 matches the README) and a sample streamed from one of
  the ten eval archives, `flac_E_aa.tar`. Only its first part was read, so that archive's MD5 could not
  be checked; every kept clip was decoded instead (16 kHz, no failures). Kept: 125 bona fide clips per
  codec condition (none and C01-C11) and 94 spoofed clips per attack (A17-A32), first come in archive
  order, 3,004 in all. The file list and labels are in the results file (`files.asvspoof5_eval`).
- **Labels:** `ASVspoof5.eval.track_1.tsv` (attack, codec, codec quality per clip).

### COCO val2017 (real photos) and Synthbuster (AI images)

- **Role:** image test set. Manifest `evaluation/E2E-01/image_manifest.csv`: 600 COCO val2017 photos and 200
  images from each of Synthbuster's nine generators (seed 0), split 50/50 by image id into a **dev** half
  (Community Forensics weight, the 0.02 authentic cut-off, TruFor's threshold, and training replay for the
  fine-tuned model) and a **test** half used only for reporting.
- **Sources and licences:** COCO (https://cocodataset.org; images keep their Flickr licences, annotations
  CC BY 4.0); Synthbuster (Bammey 2023, Zenodo DOI 10.5281/zenodo.10066460, CC BY-NC-SA 4.0). No image is
  redistributed in this repository.

### MLLM-Generated Image Detection Dataset (newest generators)

- **Role:** fine-tuning and testing on current generators (`evaluation/COMMFOR-FT-01`).
- **Source and licence:** Hugging Face `zr-zhang/MLLM-Generated-Image-Detection-Dataset` (Zhang et al. 2026,
  arXiv 2608.01258); Apache-2.0 metadata, and its card restricts use to research on AI-generated content
  detection. Cite the paper.
- **What was used:** a seeded subset of 1,000 images per generator (FLUX.2, GPT Image 2, Nano Banana 2,
  Qwen Image 2.1) and 3,611 real photos (`subset.csv`), split 60/20/20 per generator and category;
  **Qwen Image 2.1 is test only** (never trained on). 4,800 further GPT Image 2 / Nano Banana 2 images, disjoint
  from the subset, are training only (`extra.csv`; one truncated file removed). Splits: `checkpoints/commfor_ft_v3/splits.csv`.
- **Shortcut control:** its AI images are PNG and its real photos mostly JPEG, so every training and test
  image is resized and re-encoded as JPEG before scoring.

### TruFor splice test (made here)

- 600 spliced copies of the COCO photos above (a feathered region from another photo of the same split, JPEG
  q90, seed 0; `backend/scripts/eval_trufor.py`). A controlled test of local edits, not a public benchmark.

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
| RAISE-1k | Real photos matched to Synthbuster | Not downloaded (COCO val2017 is used instead). |
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
