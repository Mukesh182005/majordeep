# Round 3: rules fixed before any training (2026-10-31)

A change becomes the default only if it meets its rule on held-out data that no
training or threshold choice used. Otherwise it is documented as rejected.

## Video: AI-generated video detector

- Test: one whole generator that the detector never saw in training or
  validation, plus the 40 real clips of `DFD_heldout80` (never used for training).
- Switch only if, through the full pipeline (`scripts/eval_end_to_end.py score-video`):
  - AI videos called MANIPULATED >= 60 % (baseline 17.5 %, `evaluation/VIDEO-AIGEN-01`);
  - real DFD held-out videos called MANIPULATED <= 1 of 40;
  - face swaps called MANIPULATED on `DFD_heldout80` >= 72.5 % (baseline, `evaluation/VIDEO-GEND-01`).
- The decision threshold is chosen on validation only.

## Image: Community Forensics fine-tune v5

- Switch only if newest generators called MANIPULATED > 44.0 % (`evaluation/E2E-02`),
  COCO real photos called MANIPULATED stays 0 of 296, and no other test set gets worse.

## Audio

- No new fine-tune (two were rejected: `evaluation/E2E-03`, `evaluation/AUDIO-FT2-01`).
- A narrowband INCONCLUSIVE band only if the user's own phone recordings show false
  alarms; none were provided (`C:\deepsentinel_data\MY_TEST` does not exist), so no
  audio change this round.
