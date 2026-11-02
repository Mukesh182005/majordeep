# Round 4: rules fixed before training (2026-10-31)

Goal: close the three accuracy gaps in KNOWN_ISSUES #16, #17, #19. A change becomes the default only if
it passes its rule on data never used to train it or to choose its threshold. Otherwise it is
documented as rejected and the current default stays.

## Image (fine-tune v5)
Training: v3's data plus 2,400 more GPT Image 2 and Nano Banana 2 images, 2,400 more MLLM Real photos,
and 3,000 COCO test2017 photos (COCO val2017 is the test set, so no overlap). Weight and calibration
chosen on validation only.
Switch only if, on the held-out sets used for the current numbers (`evaluation/E2E-02`):
- newest generators called MANIPULATED rises above 44.0 %;
- COCO + Synthbuster test: real called MANIPULATED stays 0 / 296 and AI called MANIPULATED stays >= 97.4 %
  (current 98.4 %, at most 1 point lower);
- `accuracy_test`: real called MANIPULATED stays 0 / 60 and AI called MANIPULATED stays >= 38.3 %.

## Video (AI-video detector retrained with more real video)
Training adds a second vidor part; a sample of it is held out as a fresh real test set never used
for training or thresholds. Switch `AIVIDEO_IN_VERDICT` on only if, in the full pipeline:
- held-out Veo 3 called MANIPULATED >= 60 %;
- real DFD held-out: <= 1 / 40 called MANIPULATED (this set decided round 3, so it is reported with
  that caveat) and fresh vidor real test: <= 2 % called MANIPULATED;
- DFD face swaps called MANIPULATED >= 72.5 %.

## Audio (phone-quality speech)
Data: downloaded real speech recorded or degraded like phone audio (NISQA corpus, Common Voice) and
AI speech (Common Voice clones, audiospoofing-mini); split by file hash into validation (for any
tuning) and test. First the current pellav2 is measured on test. A change (narrowband handling or a
different pretrained model) is adopted only if, on the test split:
- real called MANIPULATED falls; and AI called MANIPULATED falls by at most 5 points;
- ASVspoof 5 sample: real called MANIPULATED <= 15.0 % and AI called MANIPULATED >= 72.0 %;
- ASVspoof 2019 LA: AI called MANIPULATED >= 95 % and real <= 1 %.
