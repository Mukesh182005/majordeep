# AIVIDEO-01: AI-generated video detector (round 3)

Rules fixed before training: `evaluation/ROUND3-RULES.md`.

## Detector

`backend/app/ml/aivideo.py`, trained by `ml/training/train_aivideo.py`: CLIP ViT-L/14
embeddings of the 8 frames the pipeline already samples (mean, standard deviation and
mean consecutive change), then logistic regression. Weight decay chosen on validation
AUC; threshold 0.375, midway between the 2nd and 3rd highest real validation scores
(2 of 137 real validation videos at or above it). Head: `checkpoints/aivideo_clip/head.json`
(git-ignored).

Data (`docs/research/DATASETS.md`): HunyuanVideo, Kling and FastWan 2 clips (AI) and
UCF50, vidor and DFD real videos for training and validation. Veo 3 is never used in
training or validation. Real sources are split by recording.

## Model-level test (`results.json`, test split)

| Source | Videos | Flagged |
|---|---|---|
| Veo 3 (unseen generator) | 266 | 265 (99.6 %) |
| UCF50 real | 72 | 0 |
| vidor real | 57 | 0 |
| DFD real | 47 | 0 |

AUC 1.000. All AI clips come from one Hugging Face collection, so they may share
traits (length, resolution, smooth camera motion) that real-world AI videos do not.

## Full pipeline with `AIVIDEO_IN_VERDICT=true` (`summary.json`)

| Set | Called MANIPULATED | Before (detector off) |
|---|---|---|
| Veo 3, 40 clips (`AIVID_r3test`) | 40 / 40 | 10 / 40 (`VIDEO-AIGEN-01`) |
| Real DFD held-out, 40 clips | 2 / 40 | 1 / 40 (`VIDEO-AIGEN-01`) |
| DFD face swaps, 40 clips (`DFD_r3fakes`) | 30 / 40 | 29 / 40 (`VIDEO-GEND-01`) |

Of the two real clips, `10__walking_outside_cafe_disgusted` was already flagged by the
scene detectors (the AI-video detector gives it 0.04 %); `11__talking_against_wall` is
new (0.73).

## Decision

The rule allows at most 1 of 40 real videos flagged; this gives 2. The detector is
therefore **not in the verdict by default**: it runs on every video and its score is
shown ("shown only"). `AIVIDEO_IN_VERDICT=true` puts it in the verdict, with the cost
measured here. The threshold was not changed after seeing the test results.

Commands (from `backend/`, `TRUFOR_ENABLED=false`, `AIVIDEO_IN_VERDICT=true`):

```
python ../ml/training/train_aivideo.py features --manifest <manifest.csv> --out <features.npz>
python ../ml/training/train_aivideo.py train --features <features.npz> --out ../checkpoints/aivideo_clip
python ../ml/training/train_aivideo.py evaluate --features <features.npz> --head ../checkpoints/aivideo_clip --out ../evaluation/AIVIDEO-01/results.json
python scripts/eval_end_to_end.py score-video --data C:/deepsentinel_data/AIVID_r3test --name video_veo3_aivideo_on --shard K/2 --out-dir ../evaluation/AIVIDEO-01
python scripts/eval_end_to_end.py score-video --data C:/deepsentinel_data/DFD_r3fakes --name video_dfd_faceswaps_aivideo_on --shard K/2 --out-dir ../evaluation/AIVIDEO-01
python scripts/eval_end_to_end.py summarise --out-dir ../evaluation/AIVIDEO-01
```
