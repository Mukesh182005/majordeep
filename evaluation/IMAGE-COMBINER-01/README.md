# IMAGE-COMBINER-01: learned combination of the image detectors (adopted)

Rules: `evaluation/ROUND5-RULES.md` (fixed before scoring). Fit: `ml/training/fit_image_combiner.py`.
Output: `checkpoints/image_combiner.json`; app code: `backend/app/ml/image_combiner.py`.

Data: held-out images only (MLLM test split: real, FLUX.2, GPT Image 2, Nano Banana 2, Qwen Image 2.1;
COCO real photos from the E2E-01 manifest), each as original, WhatsApp-style (1600 px, JPEG q70),
screenshot-style (rescaled 0.55-0.9, PNG) and small (480-720 px, JPEG q80-90); split by image into
tune (fit and cut-offs) and test. The Synthbuster images of E2E-01 were not available (data folder
deleted 2026-11-02), so older generators (DALL-E 2/3, Midjourney v5, SD 1-XL, GLIDE, Firefly) are not
in this set; `accuracy_test` covers older material.

Combination: class-balanced logistic regression on each detector's log-odds; AUTHENTIC cut-off with
at most 1 % of tune AI images below it, MANIPULATED cut-off with at most 2 % of tune real images above
it, rescaled onto the app's verdict band (0.42 / 0.58).

## Test split (`results.json`, 2,144 real + 3,200 AI files)

| | Hand-set weights (today) | Learned combination |
|---|---|---|
| AI called MANIPULATED | 1,942 (60.7 %) | 2,930 (91.6 %) |
| AI called AUTHENTIC | 233 (7.3 %) | 47 (1.5 %) |
| Real called AUTHENTIC | 2,045 (95.4 %) | 1,768 (82.5 %) |
| Real called MANIPULATED | 2 (0.1 %) | 41 (1.9 %) |
| Correct decided verdicts | 3,987 | 4,698 |

Newest generators called MANIPULATED, today -> learned: GPT Image 2 161 -> 345 of 380, Nano Banana 2
62 -> 269 of 396, FLUX.2 367 -> 415 of 428, Qwen Image 2.1 1,352 -> 1,901 of 1,996.
"Today" is the hand-set fusion with the no-camera-metadata rule; it leaves out the screenshot rule and
the heuristic floors, so it is more favourable to today's app on real images than the app itself.

## Full pipeline checks (`../IMAGE-UPLOADS-01/summary.json`)

- `accuracy_test` (60 real, 60 AI, older material): real called MANIPULATED 0 / 60 (rule met); AI
  called MANIPULATED 23 / 60, as before (38.3 %).
- 28 of the user's own uploads labelled from file name or source (11 AI, 17 "real"): AI called
  MANIPULATED 5 -> 7, AI called AUTHENTIC 2 -> 1; real called AUTHENTIC 11 -> 8 and MANIPULATED 1 -> 4.
  One of those "real" files (`istockphoto-462575727`) carries C2PA Content Credentials declaring
  Google Imagen / Gemini, so the app is right to flag it; excluding it, real called MANIPULATED is
  0 -> 3 of 16 (the fine-tuned detector fires on a real screenshot and a Pexels photo).

## Decision
All rules met on the test split, so the learned combination is the default. Its weak point is real
photos that the fine-tuned detector scores high (screenshots of event photos, some stock photos).
