# Round 5: image verdicts on upload-like files (rules fixed before scoring, 2026-11-02)

Problem (user uploads, 2026-10-31): AI images called AUTHENTIC when the two Community Forensics models
outvote a confident haywoodsloan; real screenshots and photos without camera metadata called
INCONCLUSIVE; the fine-tuned model flags some real screenshots.

Data: `UPLOAD_SET` (built from held-out test images only: E2E-01 test half, MLLM test split), each image
in four versions (original, WhatsApp-style, screenshot-style, small). Split by image: `tune` (fit and
thresholds only) and `test` (final numbers only).

Change: a learned combination (logistic regression on each detector's log-odds, optionally image v5)
replaces the hand-set weights, and the AUTHENTIC / MANIPULATED cut-offs are chosen on `tune`:
the AUTHENTIC cut-off so that at most 1 % of tune AI images fall below it, the MANIPULATED cut-off so
that at most 2 % of tune real images reach it.

Switch only if, on `test`:
- AI images called AUTHENTIC <= 1.5 % (all versions together);
- real images called MANIPULATED <= 3 %;
- correct decided verdicts (real AUTHENTIC + AI MANIPULATED) rise compared with the current rule;
- and, on the older held-out sets, it is not worse than today: `accuracy_test` real called MANIPULATED
  stays 0 / 60.
