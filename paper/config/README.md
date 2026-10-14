# paper/config/

Frozen configurations. Each file here is committed on its own **before** the
test set it governs is scored, so the git history proves nothing was tuned on
that test set (CLAUDE.md, research-integrity rules 2 and 3).

Expected files:
- `frozen_image_config.json`: image detectors with revisions or hashes, fusion weights, threshold, inconclusive band, guard rules, border-crop parameters, git commit (Phase 5, before any T2 image is scored).
- `audio_calibration.json`: calibration method and parameters, fitted on ASVspoof 2019 LA **dev** only (Phase 3).
- `frozen_audio_config.json`: synthesis-risk weights and verdict thresholds, chosen on dev only (Phase 3).

If a frozen file changes after its test set was scored, the results on that set are post-hoc and must be reported as such.
