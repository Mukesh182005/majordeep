# VIDEO-FINAL-01: the deployed video verdict, after the scene-score fix (2026-11-02)

Settings as deployed: GenD in the verdict, AI-video detector in the verdict (`AIVIDEO_IN_VERDICT=true`,
round-3 head `checkpoints/aivideo_clip/`), TruFor off for speed, code at `3c7c2e3` (video frames scored with
the hand-set scene fusion, not the learned image combination). Test videos re-downloaded with the same
ids as VIDEO-GEND-01 / VIDEO-AIGEN-01.

`summary.json`:

| Set | Called MANIPULATED | INCONCLUSIVE |
|---|---|---|
| Veo 3 (AI-generated, unseen generator) | 40 / 40 | 0 |
| Real DFD held-out | 2 / 40 | 0 |
| DFD face swaps | 29 / 40 | 1 |

Same as the round-3 measurement (`evaluation/AIVIDEO-01`). Before the fix, the learned image combination
had moved frame scores from about 0.07 to 0.6 and the same face swaps fell to 24 / 40 with 7 INCONCLUSIVE.

The round-4 head (`AIVIDEO-02`) was not re-tested in full and is not used.
