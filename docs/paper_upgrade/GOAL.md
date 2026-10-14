# DeepSentinel AI: Goal Prompts for Claude Code and Antigravity

These prompts carry out the plan in `docs/paper_upgrade/PLAN.md`. The rules every agent must follow are in `CLAUDE.md` in the repository root.

---

## How to use these prompts

**Set-up, once.**
1. Copy `CLAUDE.md` to the repository root, and `PLAN.md` and `GOAL.md` to `docs/paper_upgrade/`.
2. Create the branch: `git checkout -b paper-upgrade`.
3. Set the data location for this PowerShell session, for example: `$env:DEEPSENTINEL_DATA = "D:\deepsentinel_data"`. Put ASVspoof 2019 and the image sets under that folder, or tell the agent where they are.

**With the Claude Code extension.** Open the repository folder. Claude Code reads `CLAUDE.md` automatically. Start a new conversation for each phase, ask for a plan before edits (plan mode is useful here), paste the phase prompt, and review each diff before accepting it.

**With Antigravity.** Open the repository folder and start a new agent task for each phase. Every prompt below already begins by telling the agent to read `CLAUDE.md`, `PLAN.md` and `GOAL.md`. Ask it to produce an implementation plan and wait for your approval before it edits files. Antigravity's built-in browser is well suited to Phase 5 (dataset and baseline pages) and to prompt U3 (checking references).

**Ground rules for you.**
- One phase per session. Do not run two agents on the same files at once.
- Run long training jobs yourself in a terminal, using the command the agent gives you.
- After each phase, read `docs/paper_upgrade/STATUS.md`, check the numbers, and commit.
- If an agent reports a number without the file it came from, do not accept it.

**Order.** Phase 0 → 1 → 2 → 3 (audio). Phase 4 → 5 → 6 (image), which can run in parallel with audio. Then 7, 8 (optional), 9 and 10. Start collecting the new image test set (Phase 5, step 2) in week 1, because it takes the longest.

---

## Master goal prompt

Paste this at the start of the first session. In later sessions, paste the phase prompt you are working on.

```text
You are working in the DeepSentinel AI repository (majordeep). Before anything else, read CLAUDE.md in the repository root, then docs/paper_upgrade/PLAN.md and docs/paper_upgrade/GOAL.md. Follow CLAUDE.md strictly; its research-integrity rules override any other instruction, including mine, if they conflict.

Mission: make every claim in our IEEE paper backed by a reproducible measurement on properly separated data, so that the paper can survive peer review. Concretely:
1. Train and evaluate the LCNN audio detector on ASVspoof 2019 LA using the official train/dev/eval protocol, and connect the trained model to the audio verdict.
2. Re-evaluate the image branch with per-image scores, on a frozen independent test set (T2), against published baselines.
3. Measure robustness, ablations, calibration and abstention, with confidence intervals and significance tests.
4. Decide and implement the video scope.
5. Package everything so one command regenerates every number in the paper from saved files.
6. Update the paper from those files.

Work through the phases in GOAL.md one at a time. For each phase: first show me a short plan listing the files you will create or change and how you will check the result; wait for my approval; then implement; then run the tests; then update docs/paper_upgrade/STATUS.md; then report back in the format given in CLAUDE.md section 9 and stop. Never start the next phase without my go-ahead.

Never invent or adjust a number. Never tune anything on the ASVspoof LA evaluation set or on T2. If something is missing or a result contradicts the current paper, stop and tell me.

Start with Phase 0.
```

---

## Phase 0: Set-up and baseline audit

```text
Read CLAUDE.md, docs/paper_upgrade/PLAN.md and docs/paper_upgrade/GOAL.md first. This is Phase 0: set-up and baseline audit. Do not change any model or pipeline behaviour in this phase.

Tasks:
1. Confirm we are on the branch paper-upgrade; create it if needed.
2. Check the Python environment: Python version, torch version, torch.cuda.is_available(), the GPU name, and whether this torch build supports the GPU (RTX 50-series needs a CUDA 12.8 or newer build). If it does not, stop and give me the exact install command; do not install anything yourself.
3. Run the backend tests (cd backend; python -m pytest -q) and record the result.
4. Read DEEPSENTINEL_DATA from the environment. List what is there, without opening large files. Find: (a) the ASVspoof 2019 LA folder, including the protocol files ASVspoof2019.LA.cm.train.trn.txt, ASVspoof2019.LA.cm.dev.trl.txt and ASVspoof2019.LA.cm.eval.trl.txt, the flac folders for train, dev and eval, and any ASV score files for t-DCF; (b) the H560 image folder used for the 560-image held-out test. If you cannot find either, stop and ask me for the path.
5. Create these folders, each with a short README saying what belongs there: paper/, paper/config/, paper/analysis/, paper/tables/, paper/figures/, paper_results/.
6. Create docs/paper_upgrade/STATUS.md with sections Done, Measured, Blocked, Next. Create paper_results/INDEX.md as an empty table with columns Paper item, Value, File, Key, Phase.
7. Write a provenance helper, ml/provenance.py, that returns a dict with the git commit, a dirty-tree flag, the Python, torch and CUDA versions, the GPU name, the UTC time, the command line, and the sha256 of a given manifest file. Add a unit test for it.
8. Write docs/paper_upgrade/DATA_STATEMENT.md listing every dataset the plan uses, with its source URL, licence (or "to be checked") and split policy.

Acceptance: tests pass; the folders exist; STATUS.md lists the dataset paths found and anything missing; the environment check is reported. Commit with the message "Phase 0: set-up and audit". Report back as described in CLAUDE.md section 9.
```

---

## Phase 1: ASVspoof 2019 LA manifest with the official protocol

```text
Read CLAUDE.md, docs/paper_upgrade/PLAN.md (section P1) and docs/paper_upgrade/GOAL.md first. This is Phase 1.

Goal: a data pipeline for ASVspoof 2019 LA that uses the official train, dev and eval protocol exactly, so that our results are comparable with published work.

Tasks:
1. Write ml/preprocessing/build_asvspoof2019_la.py. It takes --asvspoof-root (default from DEEPSENTINEL_DATA) and --output (default data/processed/asvspoof2019_la). It parses the three CM protocol files (columns: speaker id, utterance id, an unused field, attack id or "-", key bonafide/spoof) and writes manifest.csv with columns: utt_id, relative_path, split (train/dev/eval from the protocol file, never random), label (1 = spoof, 0 = bonafide), attack_id, speaker_id.
2. Do not reuse the random speaker split in ml/preprocessing/build_audio_dataset.py. Leave that file unchanged.
3. Check every listed file exists. Print counts per split and per label, and per attack id. The standard LA totals are about 25,380 train, 24,844 dev and 71,237 eval utterances; report what you actually find, and stop and tell me if the counts differ.
4. Feature extraction, cached to disk so training is fast: (a) the existing log-mel front end from backend/app/ml/preprocessing.py (64 mels, 512-point FFT, hop 160, 16 kHz); (b) LFCC with 20 coefficients plus deltas and double deltas, 20 ms window, 10 ms hop, 512-point FFT. Use fixed-length input of 64,000 samples (4 seconds): repeat short utterances and take the first 4 seconds of long ones for training; record this choice in the config. For evaluation, also support averaging scores over consecutive 4-second windows per utterance.
5. Add a dataset class for this manifest in ml/training/datasets.py (or a new module) that returns (feature tensor, label, utt_id).
6. Tests: the protocol parser on a small fake protocol file; a check that no utterance appears in two splits; a check that the eval split contains attack ids A07 to A19 and the train split A01 to A06.
7. Give me the exact PowerShell command to build the full manifest and feature cache, with an estimate of disk space and time. Run it yourself only on the first 200 utterances of each split as a smoke test.

Acceptance: tests pass; the smoke test runs; the counts are reported. Update STATUS.md and commit with "Phase 1: ASVspoof 2019 LA protocol pipeline". Report back per CLAUDE.md section 9.
```

---

## Phase 2: Train and evaluate the LCNN on ASVspoof 2019 LA

```text
Read CLAUDE.md, docs/paper_upgrade/PLAN.md (section P1) and docs/paper_upgrade/GOAL.md first. This is Phase 2. The full manifest and feature cache from Phase 1 must exist; check before starting.

Goal: an honest, comparable EER for our audio detector.

Rules for this phase: all choices are made on the dev split. The eval split is scored only once per final configuration, at the very end. Do not look at eval results and then change anything.

Tasks:
1. Write ml/training/train_asvspoof.py, reusing the LCNN from build_audio_model in backend/app/ml/models_arch.py and the training loop in ml/training/engine.py where possible. Arguments: --features (logmel or lfcc), --seed, --epochs, --batch-size, --lr, --output. Handle the class imbalance (roughly 9 spoof to 1 bona fide) with a weighted loss or a balanced sampler, and record which. Select the best epoch by dev EER. Save the checkpoint to checkpoints/audio_lcnn_asvspoof_<features>_seed<k>.pt; never overwrite checkpoints/audio_detector.pt.
2. Write ml/evaluation/eval_asvspoof.py. It scores a split utterance by utterance and writes a score file with columns utt_id, attack_id, label, score, where a higher score means more likely bona fide (the ASVspoof convention). It computes: pooled EER; EER per attack (bona fide utterances against the spoofed utterances of each attack); ROC AUC; and min t-DCF using the official ASVspoof 2019 t-DCF procedure and ASV score files, if those files are present. If they are not present, say so and skip t-DCF; do not approximate it.
3. Add unit tests for the EER function: perfectly separated scores give 0; identical score distributions give about 0.5; a known small example gives the hand-computed value.
4. Test the whole loop on a 2,000-utterance subset of train and the dev split for one epoch, inside this session.
5. Then give me the exact PowerShell commands for the full runs: both front ends with seed 0, then three seeds (0, 1, 2) for whichever front end is better on dev. Tell me the expected time per run on a 12 GB GPU and which files each run writes.
6. After I report that the runs have finished: compare the front ends on dev only; fix the configuration; then score eval once for the three seeds of that configuration. Write paper_results/audio_asvspoof2019la/ containing config.json (with provenance from ml/provenance.py), metrics.json (pooled EER mean and standard deviation over seeds, per-attack EER table, AUC, min t-DCF if available), the score files, and a DET or ROC plot. Add each number to paper_results/INDEX.md.
7. Look up the EER and min t-DCF of the official challenge baselines (CQCC-GMM and LFCC-GMM) on the LA eval set in the ASVspoof 2019 overview paper, and record them with the citation in paper_results/audio_asvspoof2019la/baselines.md. If you cannot verify the numbers from the paper itself, write "to be verified" and do not guess.
8. Optional, only if I ask: score the frozen model on the In-the-Wild dataset as a cross-dataset test, and write paper_results/audio_inthewild/.

Acceptance: tests pass; dev-based selection is documented; eval scored once per seed; all numbers come from files. Update STATUS.md and commit with "Phase 2: LCNN on ASVspoof 2019 LA". Report back per CLAUDE.md section 9, including any results that look worse than expected.
```

---

## Phase 3: Connect the trained audio model and measure the audio heuristics

```text
Read CLAUDE.md, docs/paper_upgrade/PLAN.md (section P2) and docs/paper_upgrade/GOAL.md first. This is Phase 3. Phase 2 must be complete.

Goal: the audio verdict must use the model we evaluated, and every audio signal that affects the verdict must be shown to discriminate on development data.

Tasks:
1. Read backend/app/ml/audio_pipeline.py, backend/app/ml/audio/__init__.py, backend/app/ml/audio/models_arch.py and backend/app/ml/audio/evidence_fusion.py, and write in STATUS.md a short description of how the audio probability is produced today. Confirm or correct this summary: the LCNN checkpoint is loaded only to report its status; the model-stage score comes from an untrained sinc network and a spectral-smoothness heuristic.
2. Add a setting audio_model_source in backend/app/config.py with values "legacy" (today's behaviour) and "lcnn_asvspoof" (new). In the new mode, the model stage uses the Phase 2 checkpoint chosen on dev, scores the utterance by averaging over 4-second windows, and maps the score to a probability with a calibration fitted on the dev split only (Platt scaling or temperature scaling; record which and its parameters in paper/config/audio_calibration.json). Register the new checkpoint in backend/app/ml/registry.py without removing the old one.
3. Build a balanced dev subsample: 1,000 bona fide and 1,000 spoofed utterances, stratified over the dev attacks, chosen with a fixed seed. Time the full audio forensic suite on 20 files first and tell me the projected total time before running the rest.
4. On that dev subsample, run the full audio forensic suite and record for each utterance: the LCNN probability, the glottal anomaly score, the coarticulation anomaly score, the mains-hum findings, the splice-timeline findings, the old model-stage score, and the final probability under both settings. Save to paper_results/audio_heuristics_dev/scores.csv with config.json.
5. For each signal compute AUC with a 2,000-resample bootstrap 95% interval. A signal may stay in the synthesis risk only if the lower end of its interval is above 0.60; every other signal is moved to "context" (still computed and displayed, but not used in the verdict). Report the table before changing evidence_fusion.py, and wait for my approval.
6. After approval, update backend/app/ml/audio/evidence_fusion.py for the new mode: choose the synthesis-risk weights and the authentic and synthetic thresholds on the dev subsample only, and record them in paper/config/frozen_audio_config.json. Keep the legacy path unchanged.
7. Score the ASVspoof eval split end to end once with the frozen audio configuration. If the full suite is too slow for all 71,237 utterances, use a stratified random sample of at least 4,000 eval utterances with a fixed seed, and say so. Report verdict rates (authentic, inconclusive, flagged) for bona fide and spoofed audio with Wilson intervals, into paper_results/audio_end_to_end_eval/.
8. Update docs/models/MODEL_CARD.md and KNOWN_ISSUES.md for the audio branch. Add tests for the new mode, including that the legacy mode still produces the same output as before on a fixed test clip.

Acceptance: tests pass; the frozen audio configuration was fixed before eval scoring; the heuristic table and end-to-end eval results are in paper_results/ and INDEX.md. Update STATUS.md and commit with "Phase 3: trained audio model in the verdict". Report back per CLAUDE.md section 9.
```

---

## Phase 4: Image evaluation harness and per-image scores for H560

```text
Read CLAUDE.md, docs/paper_upgrade/PLAN.md (section P3) and docs/paper_upgrade/GOAL.md first. This is Phase 4. Do not change any image pipeline behaviour in this phase.

Goal: per-image scores for every image test, so that we can report intervals, per-generator results and significance tests.

Tasks:
1. Define an image manifest format, documented in paper/README.md: CSV columns image_id, relative_path, label (1 = AI-generated, 0 = real), generator (or "real"), source, condition (original, jpeg75, screenshot, and so on), group (the original image an edited copy came from).
2. Write ml/evaluation/eval_image_detectors.py. For each manifest row it records: each scene detector's probability from score_scene in backend/app/ml/image_pipeline.py; the fused probability; optionally (flag --end-to-end) the verdict, probability and the guard rules that fired from analyze_image; whether borders were cropped; and latency. It writes JSON Lines, skips images already scored so it can resume, runs inference in float32, records provenance, and never stops on a single bad image (it logs the error and continues).
3. Write paper/analysis/image_metrics.py, which reads a scores file and writes metrics.json and LaTeX table snippets into paper/tables/. It must compute: ROC AUC with a 2,000-resample bootstrap 95% interval; the DeLong test between any two score columns on the same images; the rate of real images at or above 0.5 and of AI images below 0.5; end-to-end verdict rates with Wilson intervals; per-generator detection rates with Wilson intervals; expected calibration error with 15 bins; and a reliability diagram.
4. Unit tests with known answers: perfectly separated scores give AUC 1.0; reversed scores give 0.0; DeLong between identical columns gives p = 1; Wilson intervals match a hand-computed case.
5. H560. Ask me how the generator of each H560 image can be determined (folder names, file names or a list) before writing its manifest. Build paper/manifests/h560.csv. Score it with --end-to-end for the original files only, then give me the command to also score the screenshot and normalised-JPEG versions if those files exist.
6. Compare the regenerated H560 numbers with the current paper: fused AUC 0.984, detector A 0.973, detector B 0.836, detector C 0.469, real photos reported manipulated 2.0%, AI images reported manipulated 88.3%, AI images reported authentic 6.7%. Report every difference. Do not adjust anything to make them match.
7. Write paper_results/image_h560/ with scores, metrics, per-generator table, and config, and add the numbers to INDEX.md.

Acceptance: tests pass; H560 scores exist per image; the comparison with the paper is reported. Update STATUS.md and commit with "Phase 4: image evaluation harness and H560 re-run". Report back per CLAUDE.md section 9.
```

---

## Phase 5: Freeze the image configuration, build test set T2, add baselines

```text
Read CLAUDE.md, docs/paper_upgrade/PLAN.md (section P4) and docs/paper_upgrade/GOAL.md first. This is Phase 5. Phase 4 must be complete.

Goal: an independent test of the image branch that nobody could have tuned on, with published baselines.

Tasks, in this order:
1. FREEZE. Write paper/config/frozen_image_config.json containing: the scene detectors with their Hugging Face ids and exact revisions or file hashes, the fusion weights, the threshold and inconclusive band, the provenance and copy-move rules, the guard rules, the border-crop parameters, and the current git commit. Commit it alone with the message "Freeze image configuration before T2". From now on, do not change any of these settings. If I ask you to change one, remind me that T2 results would then be post-hoc.
2. Build T2 with paper/manifests/build_t2.py from folders I provide. Target at least 800 real and 800 AI-generated images, with at least 100 per generator. Real sources: public camera photographs and at least 200 photographs taken by our team, plus messenger-forwarded copies of a subset. Generated sources: a public benchmark such as Synthbuster, plus newer generators. For every image record source, generator, version, date and licence. Use the perceptual hashes in backend/app/ml/forensics/hashing.py to remove any image within a small Hamming distance of an H560 image or of another T2 image, and report how many were removed and the distance used. If you need to look up dataset pages or licences, do so, but ask me before downloading anything.
3. Baselines. Add wrappers in ml/evaluation/baselines/ for UnivFD (Ojha et al., CVPR 2023, official repository WisconsinAIVision/UniversalFakeDetect) and CNNDetection (Wang et al., CVPR 2020, official repository PeterWang512/CNNDetection). Use the official released weights and the official test-time preprocessing exactly as their repositories do it, and document it. Check their licences. Give me the download commands; do not commit the weights. Each wrapper returns a probability that the image is AI-generated, so it plugs into eval_image_detectors.py as another score column.
4. Score T2 with: the frozen fused detector end to end; detector A alone; detector B alone; the old detector C (umm-maybe/AI-image-detector); UnivFD; and CNNDetection. Test on 50 images first and tell me the projected time before the full run.
5. Write paper_results/image_t2/ with per-image scores, metrics.json, a main results table (AUC with interval, real images at or above 0.5, AI images caught, verdict rates for our system), a per-generator table, DeLong tests of our fused detector against every other method, and config. Add the numbers to INDEX.md.

Acceptance: the freeze commit comes before any T2 scoring in the git history; all methods are scored on identical images; tests pass. Update STATUS.md and commit with "Phase 5: T2 test set and baselines". Report back per CLAUDE.md section 9, including any generator on which we do poorly.
```

---

## Phase 6: Robustness, ablations, calibration, abstention, statistics

```text
Read CLAUDE.md, docs/paper_upgrade/PLAN.md (section P5) and docs/paper_upgrade/GOAL.md first. This is Phase 6. Phases 4 and 5 must be complete. The frozen image configuration must not change; ablations are computed alongside it, not instead of it.

Tasks:
1. Robustness. Write paper/manifests/make_transforms.py that creates transformed copies of T2: JPEG quality 95, 75 and 50; resize to 50% and 25% with antialiasing; and simulated screenshots (search the repository first for the screenshot simulation used for H560 and reuse it if it exists, otherwise write one and document it). Each copy keeps the group id of its original. Also give me a list of 100 real and 100 AI T2 images and a folder layout so that I can send them to myself over WhatsApp and download the received files; then score those too. Score every condition with all methods, and report AUC with intervals per condition and method.
2. Border-crop ablation: score the screenshot condition with border cropping on and off.
3. Fusion-rule ablation on T2 original files: maximum of detectors; plain mean of probabilities; mean of logits with the frozen weights (our system); and a logistic regression over the detector scores fitted on H560 only. Report AUC, real-image false-positive rate and AI detection rate, with intervals and DeLong tests against our system.
4. Guard-rule ablation: switch off the screenshot rule, and separately the detector-unavailable rule, and report how verdict rates change on the screenshot condition.
5. Calibration: reliability diagram and ECE for our system on T2; then fit temperature scaling on H560 only, apply it to T2, and report the change. Do not refit on T2.
6. Abstention: a risk–coverage curve on T2, varying the inconclusive band half-width from 0 to 0.30 in steps of 0.02: for each value, the share of images that receive a decision and the error rate among them. Mark the frozen value of 0.08.
7. Paired significance: McNemar's test on end-to-end verdicts where two configurations are compared on the same images.
8. Write all results under paper_results/image_t2_robustness/, image_t2_ablations/, image_t2_calibration/ and image_t2_risk_coverage/, with figures in paper/figures/ generated by scripts in paper/analysis/, and add the numbers to INDEX.md.

Acceptance: every figure and table can be regenerated by a script from saved scores; tests pass. Update STATUS.md and commit with "Phase 6: robustness, ablations, calibration, abstention". Report back per CLAUDE.md section 9.
```

---

## Phase 7: Video scope

Option B is the default. Use the Option A prompt instead only if you have three or more spare weeks and access to FakeAVCeleb.

```text
Read CLAUDE.md, docs/paper_upgrade/PLAN.md (section P6) and docs/paper_upgrade/GOAL.md first. This is Phase 7, Option B: video becomes a clearly labelled experimental demonstrator.

Tasks:
1. Add a setting video_experimental (default true) in backend/app/config.py. When true, the API result, the result page and the PDF report state that the video verdict is experimental and has not been validated on a labelled dataset.
2. The pulse stage needs spectral power between 0.75 and 2.5 Hz, and optical flow needs closely spaced frames; neither works at the current 1 frame per second. Implement dense sampling for these two stages only: up to 10 seconds of frames at 10 or more frames per second around the chosen keyframe, controlled by settings. If that is too slow, instead remove these two stages' contribution to the video score and keep them as context. Measure the run time on three sample videos and tell me which option you recommend before implementing.
3. Update KNOWN_ISSUES.md, docs/models/MODEL_CARD.md and the "how it works" page text so that they match the code.
4. Add tests: the experimental flag appears in the API result; the pulse stage receives frames at the dense rate, or contributes nothing to the score, depending on the option chosen.

Acceptance: tests pass; no document claims a validated video detector. Update STATUS.md and commit with "Phase 7: video scope". Report back per CLAUDE.md section 9.
```

```text
Read CLAUDE.md, docs/paper_upgrade/PLAN.md (section P6) and docs/paper_upgrade/GOAL.md first. This is Phase 7, Option A: evaluate the video pipeline on FakeAVCeleb. I have access to the dataset at a path I will give you.

Tasks:
1. Build a manifest of FakeAVCeleb with its four categories (real video and real audio; fake video and real audio; real video and fake audio; fake video and fake audio), grouping by identity so that no person appears in two splits. Use a split I approve; if the dataset defines one, use it.
2. Before scoring anything, fix the video configuration (sampling, stage weights, thresholds) on a development split and write paper/config/frozen_video_config.json; commit it alone.
3. Score the test split end to end with backend/app/ml/video_pipeline.py, with per-video records of every stage score, the fused score and the verdict. Time 10 videos first and tell me the projected total.
4. Report AUC with bootstrap intervals overall and per category, the contribution of each stage (AUC of each stage alone), and verdict rates with Wilson intervals, into paper_results/video_fakeavceleb/ and INDEX.md.

Acceptance: configuration frozen before test scoring; tests pass. Update STATUS.md and commit. Report back per CLAUDE.md section 9.
```

---

## Phase 8 (optional): Fix the face-classifier leakage

```text
Read CLAUDE.md, docs/paper_upgrade/PLAN.md (section P7) and docs/paper_upgrade/GOAL.md first. This is Phase 8.

Tasks:
1. Read scripts/build_manifest_140k.py and describe in STATUS.md exactly how it produced the 164,000-image validation set, including how augmented copies were split, how the dataset's own test split was handled, and how the uploads folder was labelled.
2. Fix it, or write a corrected script next to it: every derived copy carries its source image id as its group and goes to the same split via split_by_group in ml/common.py; the dataset's official test split is kept as a separate test split and never merged into training; the application's upload folder is never used.
3. Add a test that builds a small manifest from a fake folder tree and fails if any group appears in two splits, if any test-split image appears in training, or if any file under an uploads folder appears at all.
4. Only if I ask: give me the command to retrain EfficientNet-B0 on the corrected manifest, then evaluate it on the untouched official test split and write paper_results/face_corrected_split/, so the paper can show the leaked figure next to the honest one.

Acceptance: tests pass; the old script is either fixed or clearly marked as deprecated. Update STATUS.md and commit with "Phase 8: group-safe face manifest". Report back per CLAUDE.md section 9.
```

---

## Phase 9: Reproducibility package and repository clean-up

```text
Read CLAUDE.md, docs/paper_upgrade/PLAN.md (section P8) and docs/paper_upgrade/GOAL.md first. This is Phase 9.

Tasks:
1. Add a Makefile target paper-results (and an equivalent PowerShell script, scripts/paper_results.ps1) that regenerates every table snippet in paper/tables/ and every figure in paper/figures/ from the saved score files in paper_results/, without re-running any model.
2. Make paper_results/INDEX.md complete: every number that will appear in the paper, with the file and key it comes from and the phase that produced it.
3. docs/research/EVALUATION.md: remove, or clearly label as unverified, every table that has no supporting file in the repository; link to paper_results/ for the verified results.
4. research_archive/: add a README stating that the Phase 18 to 30 artefacts are placeholders, not measurements, or move them out of the release, whichever I choose; ask me.
5. Replace hard-coded paths (for example C:/Users/STUDENT/... in research_archive/scripts/run_phase17_8r_holdout.py) with command-line arguments or DEEPSENTINEL_DATA.
6. Update docs/models/MODEL_CARD.md, KNOWN_ISSUES.md, docs/paper_upgrade/DATA_STATEMENT.md and the README results section so that they agree with paper_results/.
7. Write requirements-lock.txt from the current environment (pip freeze) and note the GPU and driver used.
8. Check that the frontend tests and backend tests both pass.

Acceptance: running the paper-results target from a clean checkout plus the saved score files reproduces every table and figure exactly; no document in the repository contradicts paper_results/. Update STATUS.md and commit with "Phase 9: reproducibility package". Report back per CLAUDE.md section 9.
```

---

## Phase 10: Update the paper

Put the LaTeX source of the paper in `paper/latex/` before starting.

```text
Read CLAUDE.md, docs/paper_upgrade/PLAN.md (sections P9 and P10) and docs/paper_upgrade/GOAL.md first. This is Phase 10. The paper's LaTeX source is in paper/latex/. Phases 1 to 7 and 9 must be complete.

Goal: a paper whose every number is generated from paper_results/, whose claims match the evidence, and which fits the target venue: [VENUE NAME, PAGE LIMIT, SINGLE- OR DOUBLE-BLIND, DEADLINE].

Tasks:
1. Replace hand-typed numbers and tables with \input of the generated snippets in paper/tables/ and the figures in paper/figures/. Search the .tex file for any remaining number that is not from INDEX.md and list them for me.
2. Title, abstract and contributions: propose a title that matches what was actually validated (see PLAN.md section 6), and one contribution sentence for the abstract. Show me two options and wait for my choice.
3. Restructure the experiments section: datasets and protocol; audio results on ASVspoof 2019 LA with the per-attack table and the challenge baselines; image results on T2 with baselines and the per-generator table; robustness; ablations; calibration and abstention; then the audit of what went wrong, now including the audio heuristics. Keep the honest account of the leaked validation split and the silent faults.
4. Update the limitations and threats-to-validity sections to match the new results, including that the public detectors' training data is unknown.
5. References: move the bibliography to paper/latex/references.bib. For each entry, find it on DBLP, Crossref, the publisher site or arXiv and use the exported BibTeX. List every entry you could not verify, and do not invent or "fix" any entry you could not find. Switch the paper to IEEEtran.bst.
6. Add an acknowledgment stating how AI tools were used in writing and in coding, as IEEE requires. Leave a comment "% AUTHORS: rewrite in your own words" at the start of the introduction, the discussion and the conclusion, because the authors must be able to defend that text in their own voice.
7. Fit the page limit by cutting in this order: appendices, API and test tables, system-implementation detail, related-work length. Show me what you plan to cut first.
8. If the venue is double-blind, produce an anonymised build (a LaTeX flag that removes names, affiliations, acknowledgment and repository links), and a camera-ready build.
9. Compile with pdflatex and bibtex; fix all warnings about undefined references or overfull boxes.

Acceptance: the PDF compiles; every number traces to INDEX.md; the reference list has no unverified entries, or they are listed for me; the page count is within the limit. Update STATUS.md and commit with "Phase 10: paper updated from paper_results". Report back per CLAUDE.md section 9.
```

---

## Utility prompts

### U1. Resume after a break

```text
Read CLAUDE.md, docs/paper_upgrade/PLAN.md, docs/paper_upgrade/GOAL.md and docs/paper_upgrade/STATUS.md. Check git log and git status on the paper-upgrade branch. Tell me which phase we are in, what is done, what is blocked, and what the next concrete step is. Do not change anything.
```

### U2. Reviewer simulation (run on the finished PDF)

```text
Act as three independent reviewers for [VENUE NAME]: one expert in multimedia forensics, one in machine-learning evaluation, and one in software systems. Read paper/latex/ (or the attached PDF) and the files in paper_results/. Each reviewer writes: a summary; strengths; weaknesses ranked by severity; questions for the authors; a score from strong reject to strong accept with a confidence level. Be strict and specific, and cite section, table or figure numbers. Pay particular attention to: claims not supported by results; any sign of tuning on test data; missing baselines; statistical significance; reproducibility; overclaiming in the title or abstract; and references that look wrong. Then produce a combined list of changes, ordered by how much each would raise the score. Do not edit any file.
```

### U3. Reference verification (best done in Antigravity with its browser)

```text
Read paper/latex/references.bib (or the reference list in the paper). For every entry, look it up on dblp.org, crossref.org, the publisher's page or arxiv.org. Produce a table with: citation key; found (yes/no); the source used; and every field that differs (authors, title, venue, year, volume, pages, DOI). Then write paper/latex/references_verified.bib containing only the entries you verified, using the exported BibTeX from the source. Never invent or guess an entry. List separately every entry you could not verify, so the authors can decide.
```

### U4. Viva preparation

```text
Using paper_results/, docs/paper_upgrade/STATUS.md and the paper, write docs/paper_upgrade/VIVA_NOTES.md: for each table and figure, explain in plain language what was measured, how, why it matters, and its main weakness; then list the twenty hardest questions an examiner could ask about this project, each with a short, honest answer based only on what is in the repository. Do not invent results.
```
