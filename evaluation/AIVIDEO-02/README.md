# AIVIDEO-02: AI-video detector retrained with more real video (incomplete)

Rules: `evaluation/ROUND4-RULES.md`. The head was retrained with 307 more vidor real clips
(`checkpoints/aivideo_clip_r4/`, not committed); model-level test split (`results.json`): Veo 3 266 / 266
flagged, real 0 / 176.

The full-pipeline runs were interrupted and the video data was deleted with `C:/deepsentinel_data` on
2026-11-02, so the rule could not be checked. The partial `.jsonl` files are kept for reference and no
number from them is used. `AIVIDEO_IN_VERDICT` stays false and the round-3 head (`checkpoints/aivideo_clip/`)
stays the shown detector.
