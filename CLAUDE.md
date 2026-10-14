# CLAUDE.md: DeepSentinel AI (repository `majordeep`)

Read this file completely before doing anything in this repository. It applies to every session and every agent, including Claude Code and Antigravity. The detailed plan is in `docs/paper_upgrade/PLAN.md` and the phase-by-phase tasks are in `docs/paper_upgrade/GOAL.md`.

## 1. What this project is

DeepSentinel AI is a final-year engineering project: a full-stack forensic platform that analyses images, audio and video for AI generation or manipulation, attaches evidence to every decision, and returns one of three verdicts (authentic, manipulated, inconclusive). A research paper about it is being prepared for an IEEE conference.

**The current mission** is to make every claim in that paper backed by a reproducible measurement on properly separated data. Specifically:
- evaluate the audio branch on ASVspoof 2019 LA with the official protocol and connect the trained model to the audio verdict;
- re-evaluate the image branch on a frozen, independent test set with published baselines;
- quantify robustness, ablations, calibration and abstention;
- make the results reproducible from saved files.

## 2. Repository map (verified paths)

| Area | Path | Notes |
|---|---|---|
| Image pipeline | `backend/app/ml/image_pipeline.py` | `score_scene(image)` gives per-detector and fused probabilities; `analyze_image(path, evidence_dir, job_id)` gives the full verdict. Detector A `haywoodsloan/ai-image-detector-deploy` (weight 0.75), detector B `Organika/sdxl-detector` (0.25), fused in log-odds space. |
| Verdict and risk fusion | `backend/app/ml/forensics/risk_fusion.py` | Threshold 0.5, inconclusive band of ±0.08, guard rules. |
| Audio pipeline | `backend/app/ml/audio_pipeline.py`, `backend/app/ml/audio/` | `analyze_audio` loads the LCNN only to report weight status. The score comes from `audio/models_arch.py` (an untrained sinc network plus a heuristic) through `audio/evidence_fusion.py` (synthesis risk 0.50/0.35/0.15; thresholds 0.35 and 0.70). |
| Video pipeline | `backend/app/ml/video/`, `backend/app/ml/video_pipeline.py` | Samples 1 frame per second, at most 32 frames (`backend/app/config.py`). Not evaluated on any labelled dataset. |
| Model definitions | `backend/app/ml/models_arch.py` | `build_audio_model` is the LCNN (144,065 parameters). |
| Preprocessing | `backend/app/ml/preprocessing.py` | `log_mel_spectrogram`: 64 mel bands, 512-point FFT, hop 160 at 16 kHz. |
| Model registry | `backend/app/ml/registry.py` | Maps `audio` to `checkpoints/audio_detector.pt`. |
| Perceptual hashes | `backend/app/ml/forensics/hashing.py` | Use these for de-duplicating test sets. |
| Settings | `backend/app/config.py` | |
| Training | `ml/training/` | `train_audio.py`, `engine.py` (`TrainConfig`, `train_model`), `datasets.py`. |
| Data builders | `ml/preprocessing/` | `build_audio_dataset.py` makes its own random speaker split. **Do not use it for ASVspoof**; the official protocol must be used. |
| Shared helpers | `ml/common.py` | `split_by_group`, `set_seed`, manifest I/O. |
| Evaluation | `ml/evaluation/` | `evaluate.py`, `metrics.py` (`compute_metrics`, `roc_auc`). |
| Leaky manifest builder | `scripts/build_manifest_140k.py` | Split augmented copies at random, merged the test split, and labelled the upload folder as fake. Do not reuse without fixing. |
| Checkpoints | `checkpoints/` | `image_detector.pt` (EfficientNet-B4), `image_detector_b0.pt`, `audio_detector.pt` (trained on synthetic tones, not speech). |
| Earlier results | `evaluation/`, `research_archive/` | Phase 18–30 artefacts in `research_archive/artifacts/` are placeholders, not measurements. |
| Docs | `docs/models/MODEL_CARD.md`, `KNOWN_ISSUES.md`, `docs/research/EVALUATION.md` | `EVALUATION.md` contains tables with no supporting files. |
| Backend tests | `backend/tests/` | Run with `cd backend; python -m pytest -q` (or `make test`). |
| Paper work (new) | `paper/`, `paper_results/`, `docs/paper_upgrade/` | Create these as the plan requires. |

## 3. Research-integrity rules (non-negotiable)

1. **Never invent, estimate, round toward a target, or hand-edit a result.** Every number that may appear in the paper must be written by a script into `paper_results/` and listed in `paper_results/INDEX.md` with the file and key it comes from.
2. **Never tune on a test set.** The ASVspoof 2019 LA **evaluation** partition and the new image test set **T2** are touched only for final scoring. Model selection, thresholds, calibration, fusion weights and the choice of heuristics use training or development data only (ASVspoof dev; H560 for image settings).
3. **Freeze before scoring T2.** The image configuration must be committed to `paper/config/frozen_image_config.json` before any T2 image is scored. If it changes afterwards, T2 results are invalid and must be re-collected or clearly reported as post-hoc.
4. **No leakage.** Augmented or derived copies always stay in the same split as their source. ASVspoof splits follow the official protocol files. Remove near-duplicates between test sets and anything used for selection.
5. **Report what happens.** If a result is worse than expected or contradicts the current paper, report it plainly. Do not search for a different setting or subset that looks better, unless the procedure is decided on development data and documented.
6. **Every results folder records its provenance:** the git commit, a hash of the data manifest, seeds, library versions, GPU name, command line and date, in `config.json`.
7. **Do not fabricate references.** Every reference added to the paper must come from DBLP, Crossref, the publisher or arXiv, with a DOI or URL that a person can check.

## 4. Data rules

- Raw data lives outside the repository. Read its location from the environment variable `DEEPSENTINEL_DATA` or a command-line argument. Never hard-code paths such as `C:/Users/...`.
- Never commit datasets, model weights or generated images. Commit manifests (relative paths, labels, groups, hashes) and per-item score files.
- Never delete or overwrite raw data or existing checkpoints. Write new checkpoints under new names.
- Respect dataset licences. Record each dataset's source, licence and split policy in `docs/paper_upgrade/DATA_STATEMENT.md`.
- Photographs of people need their consent. Prefer scenes without identifiable people.

## 5. Engineering rules

- Work on the `paper-upgrade` branch. Commit after each completed phase with a clear message. **Do not push** unless the user asks.
- Before every commit, run the backend tests (`cd backend; python -m pytest -q`). Add tests for new evaluation and data code, especially split-integrity and metric code.
- Keep backend behaviour changes behind settings in `backend/app/config.py`, so that the previous behaviour can be restored.
- Write scripts that resume after interruption and log progress, so long runs can be stopped and restarted.
- Keep `docs/paper_upgrade/STATUS.md` updated: what was done, what was measured, what is blocked, and what is next.

## 6. Environment

- The user works on **Windows**. Give commands that work in **PowerShell** and use `pathlib` in Python. Run Python as `python`.
- The GPU is an NVIDIA RTX 50-series card with 12 GB of memory. RTX 50-series cards need a PyTorch build for CUDA 12.8 or newer. Check `torch.cuda.is_available()` and the device name before any training.
- Keep batch sizes within 12 GB; use mixed precision for training but **run inference in float32** (half-precision inference produced not-a-number outputs in this project before).

## 7. Long-running jobs

- Do not start runs longer than about 20 minutes inside the agent session unless the user asks. Write the script, test it on a tiny subset, then give the user the exact PowerShell command to run, and tell them which output files to expect.
- After the user reports a run has finished, read its output files and continue from there.

## 8. When to stop and ask the user

- A dataset, folder or file the task needs cannot be found.
- A result differs from the current paper by more than its confidence interval, or contradicts it.
- A choice would change what the paper claims, its title, or its scope.
- A licence or consent question comes up.
- A step would delete, move or overwrite data, checkpoints or published results.

## 9. How to report back at the end of each phase

1. What changed (files, with one line each).
2. What was measured (numbers, with the file each comes from).
3. Tests run and their result.
4. Anything that did not work, or that contradicts the paper.
5. The exact commands the user must run next, if any.
