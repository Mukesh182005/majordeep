# DeepSentinel AI: Plan to Raise the Paper's Chance of Acceptance

Prepared 13 October 2026 from the repository `Mukesh182005/majordeep` (commit `1de4b2e`) and the current 9- and 14-page drafts.

This plan is about the science and the evidence, because that is what reviewers judge. The wording of the paper is already in reasonable shape. The prompts that let Claude Code or Antigravity carry out each step are in `GOAL.md`, and the rules the agents must follow are in `CLAUDE.md`.

---

## 1. Where the paper stands today

Reviewers at an IEEE conference ask roughly four questions. Here is how the current draft answers them.

| Reviewer question | Current answer | What fixes it |
|---|---|---|
| Is there a clear contribution? | Partly. No new model; the contribution is the fusion design, the evaluation method and the audit. | State it in the abstract, and back it with comparisons that show the fusion and the audit actually matter (P4, P5). |
| Is the evaluation sound and fair? | Weak. One 560-image set (H560) was used both to choose the detectors and weights and to report results. No public benchmark, no published baseline, no per-generator table, no confidence interval on the AUC. | Freeze the configuration, test on a new independent set, add a public benchmark and two published baselines, report intervals (P3, P4, P5). |
| Are the claims supported? | The title says "multimodal", but only images are validated. The audio model was trained on synthetic tones and is not connected to the verdict. Video is unevaluated. | Train and evaluate audio on ASVspoof 2019 LA with the official protocol and connect it (P1, P2). Evaluate video or remove it from the claims (P6). |
| Is it reproducible and well presented? | Code is public, but the H560 images and per-image scores are not archived, some scripts have hard-coded lab paths, and `docs/research/EVALUATION.md` contains tables with no supporting files. The draft is over the usual page limit and the references were not verified. | A reproducibility package where every number in the paper comes from a saved file (P8), a cleaned repository, a verified `.bib` file and a cut to the page limit (P9). |

The two problems most likely to sink the paper are the unvalidated "multimodal" claim and the absence of an independent test set. Everything else is secondary.

---

## 2. What the revised paper should be able to say

Each of these claims is tied to an experiment below. The numbers do not exist yet; they will be whatever the experiments produce, and the paper must report them as they come out.

1. **Audio.** An LCNN trained on ASVspoof 2019 LA with the official train/dev/eval protocol reaches an equal error rate of *X*% on the LA evaluation set, which contains 13 attack types (A07–A19) of which 11 are not in the training data, with a per-attack breakdown and a comparison against the challenge baselines. Optionally, *Y*% on the In-the-Wild dataset as a cross-dataset test.
2. **Image.** On a frozen, independent test set of at least 1,600 images that was collected after the configuration was fixed, the fused detector reaches an AUC of *Z* with a 95% confidence interval. It is compared with each detector alone, with two published detectors (UnivFD and CNNDetection), and it is reported per generator and under compression, resizing, messenger re-encoding and screenshots.
3. **Audit.** The leaking validation split, the silent software faults and the heuristic signals, all quantified, now with the audio heuristics measured as well as the image ones.
4. **Abstention.** A risk–coverage curve showing how the inconclusive band trades the number of decided cases against the error rate among them.
5. **Video.** Either evaluated on a labelled dataset, or clearly stated to be a demonstrator outside the paper's claims.

If the audio work succeeds, the title can keep "multimodal" honestly. If it does not, the paper should be retitled around image detection.

---

## 3. Work plan in priority order

Each item gives the reason, the exact work, the outputs, a rough effort for a student team with one RTX-class GPU, and the main risk.

### P1. Audio detection on ASVspoof 2019 LA (highest impact)

**Why.** It turns the biggest unsupported claim into a measured result on the most widely used benchmark in the field, which also gives you the external comparison reviewers want.

**What exactly.**
- Build a manifest from the official protocol files (`ASVspoof2019.LA.cm.train.trn.txt`, `...dev.trl.txt`, `...eval.trl.txt`). Do not use `ml/preprocessing/build_audio_dataset.py` as it stands, because it makes its own random speaker split; the official split is what makes your number comparable with published work.
- Sanity-check the counts against the protocol files. The standard LA counts are about 25,380 training, 24,844 development and 71,237 evaluation utterances.
- Train the LCNN (`build_audio_model` in `backend/app/ml/models_arch.py`) with two front ends: the current 64-band log-mel, and LFCC, which is the classic LCNN input for this task. Use fixed-length input of about 4 seconds, and score each utterance by averaging over windows.
- Choose every setting (front end, epoch, threshold, calibration) on the development set only. Run the evaluation set once at the end.
- Report the pooled EER on LA eval, the EER per attack (A07–A19), and min t-DCF if the official ASV score files are present. Report the mean and spread over three seeds.
- Optional but valuable: test the frozen model on the In-the-Wild dataset (Müller et al., 2022) to show cross-dataset behaviour. Expect the number to be much worse; that is normal and worth reporting.

**Outputs.** `paper_results/audio_asvspoof2019la/` with per-utterance scores, metrics JSON, DET/ROC plots and the exact configuration.

**Effort.** Three to six days, mostly training time. You already have the full ASVspoof 2019 data locally.

**Risk.** The EER may be higher than published LCNN systems. That is fine; report it honestly with the comparison.

### P2. Make the audio verdict use the trained model, and measure the audio heuristics

**Why.** Today `backend/app/ml/audio_pipeline.py` loads the LCNN only to report its weight status. The probability comes from `backend/app/ml/audio/models_arch.py`, which combines an untrained sinc network with a spectral-smoothness formula. Reviewers who look at the code would see that the system does not use the model you evaluate.

**What exactly.**
- Replace the model stage with the trained LCNN's calibrated utterance score. Fit the calibration (Platt or temperature scaling) on the dev set.
- Measure each audio heuristic (glottal anomaly, coarticulation, mains-hum findings, the splice timeline) on a balanced subsample of the **dev** set, for example 1,000 genuine and 1,000 spoofed utterances. A signal enters the synthesis risk only if its AUC on dev is clearly above 0.5. The rest become context only, exactly as was done for images.
- Re-check the decision thresholds of `backend/app/ml/audio/evidence_fusion.py` on dev, then report the end-to-end audio verdict rates on eval once.

**Outputs.** An updated audio pipeline behind a configuration flag, tests, an updated model card, and `paper_results/audio_heuristics_dev/`.

**Effort.** Two to four days.

**Risk.** Some heuristics will turn out to carry no signal. That strengthens the paper's audit section rather than weakening it.

### P3. Image evaluation harness and per-image scores

**Why.** The H560 results exist only as summary percentages. Without per-image scores you cannot give a per-generator table, confidence intervals on the AUC, or a statistical comparison between configurations.

**What exactly.**
- A script that reads a manifest (path, label, generator, source, condition) and records, for every image, each detector's probability from `score_scene` in `backend/app/ml/image_pipeline.py`, the fused probability, and the end-to-end verdict from `analyze_image`. It must be able to resume after interruption.
- An analysis script that computes AUC with bootstrap 95% intervals, the DeLong test between configurations, per-generator rates, verdict rates with Wilson intervals, and calibration error.
- Re-run H560 if you still have the 560 images. Check that the regenerated numbers match the paper (AUC 0.984, 2.0% real photos flagged, 88.3% AI images caught). If they do not match, the paper must use the regenerated numbers and say why.

**Outputs.** `ml/evaluation/eval_image_detectors.py`, `paper/analysis/image_metrics.py`, `paper_results/image_h560/`.

**Effort.** Two to three days.

**Risk.** The H560 images may be scattered or partly lost. If so, say so and rely on the new test set (P4).

### P4. An independent frozen test set, a public benchmark, and published baselines

**Why.** This answers "you tuned on your test set" and "compared to what?" in one step.

**What exactly.**
- **Freeze first.** Before scoring a single new image, write the detector list, weights, thresholds, band width, guard rules and the git commit to `paper/config/frozen_image_config.json`, and commit it. That commit is your evidence that nothing was tuned on the new set.
- **Build T2, a new test set of at least 800 real and 800 generated images.** These sizes put the false-positive rate within about ±1 percentage point and the detection rate within about ±2.5 points at 95% confidence.
  - *Real:* public camera photographs (for example the RAISE subset distributed with Synthbuster, or COCO images not in H560), plus at least 200 photographs the team takes on its own phones, of scenes or of consenting team members, together with messenger-forwarded copies of some of them.
  - *Generated:* a public benchmark such as Synthbuster, plus images from generators released after H560 was collected, with at least 100 per generator. Record the generator, version, date and prompt.
  - Remove near-duplicates of H560 images using the perceptual hashes already in `backend/app/ml/forensics/hashing.py`.
- **Baselines.** Run UnivFD (Ojha et al., CVPR 2023) and CNNDetection (Wang et al., CVPR 2020) from their official weights on exactly the same images, plus detector A alone, detector B alone and the old detector C.

**Outputs.** `paper_results/image_t2/` with per-image scores for every method, a per-generator table and a results table with intervals.

**Effort.** One to two weeks, most of it collecting and checking images. Start collecting in week 1, in parallel with the audio work.

**Risk.** The public detectors you rely on may have been trained on some of the same generators, and you cannot rule that out. State it as a threat to validity.

### P5. Robustness, ablations, calibration, abstention and statistics

**Why.** These are the experiments that turn "we built a system" into "we understand our system", which is what an applied-paper reviewer looks for.

**What exactly, all on T2 with the frozen configuration.**
- **Robustness grid:** JPEG quality 95, 75 and 50; resizing to 50% and 25%; a real messenger round trip on a subset; and simulated screenshots with and without border cropping.
- **Fusion-rule ablation:** maximum, plain mean, weighted log-odds, and a logistic regression fitted on H560 only.
- **Guard-rule ablation:** the screenshot rule and the detector-unavailable rule, each switched off in turn, reporting the effect on false positives and on recall.
- **Calibration:** a reliability diagram and expected calibration error; optionally temperature scaling fitted on H560 and applied to T2.
- **Abstention:** a risk–coverage curve, varying the half-width of the inconclusive band from 0 to 0.3.
- **Statistics:** bootstrap intervals throughout; DeLong for AUC differences; McNemar for paired verdict differences. In particular, test whether the fused detector is really better than detector A alone (0.984 versus 0.973 on H560 may not be a significant difference).

**Outputs.** `paper_results/image_t2_robustness/`, `.../ablations/`, `.../calibration/`, `.../risk_coverage/`.

**Effort.** Three to five days once P3 and P4 exist.

### P6. Video: decide the scope

**Option B, recommended unless you have three or more spare weeks.** State in the paper that the video pipeline is a demonstrator outside the evaluated claims, and remove video from the title and abstract claims. Mark it as experimental in the interface. In the code, either sample densely enough for the pulse and optical-flow stages to mean something (roughly 10 or more frames per second over a 10-second window), or switch those two stages' scores off.

**Option A.** Request access to FakeAVCeleb, evaluate the video pipeline on its test split, and report the results. This takes longer because of the access request and the pipeline's run time per video.

### P7. Face-classifier leakage fix (optional)

**Why.** It completes the audit story with code that cannot repeat the mistake.

**What exactly.** Fix `scripts/build_manifest_140k.py` so that every augmented copy carries its source image's identifier and is assigned to the same split through `split_by_group` in `ml/common.py`. Never merge the dataset's test split into training. Never add the application's upload folder to training. Add a test that fails if any source identifier appears in two splits. Optionally retrain EfficientNet-B0 on the corrected split and report the honest validation number next to the leaked one.

**Effort.** One to three days, depending on retraining.

### P8. Reproducibility package and repository clean-up

**Why.** Reviewers and examiners who open the repository should find the evidence, not contradictions.

**What exactly.**
- One command that regenerates every table and figure in the paper from the saved per-item scores, for example `make paper-results`.
- `paper_results/INDEX.md`, which maps every number in the paper to the file and key it comes from.
- In `docs/research/EVALUATION.md`, remove or clearly mark the tables that have no supporting files. In `research_archive/`, mark the Phase 18–30 artefacts as placeholders or remove them from the release.
- Remove hard-coded lab paths (for example `C:/Users/STUDENT/...` in `research_archive/scripts/run_phase17_8r_holdout.py`) in favour of command-line arguments.
- Update `docs/models/MODEL_CARD.md` and `KNOWN_ISSUES.md`, and add a short data statement listing each dataset's source, licence and the way it was split.
- Tag a release. Optionally archive it on Zenodo to get a DOI to cite.

**Effort.** Two to three days.

### P9. Rewrite the paper

- **Title** to match what the evidence supports (examples in Section 6).
- **Abstract** with one contribution sentence and the key numbers with intervals.
- **Related work** with a short comparison table against existing detectors and tools.
- **Experiments** organised as: datasets and protocol, audio results, image results on T2, robustness, ablations, abstention, then the audit.
- **Every number** taken from `paper_results/`.
- **References** in a `.bib` file, every entry exported from DBLP, Crossref or the publisher and checked by a person. I wrote the current list from memory, so it must be verified.
- **AI-use disclosure** in the acknowledgment, as IEEE requires.
- **Format:** cut to the venue's page limit (often six pages plus paid extras), and anonymise if the review is double-blind.

### P10. Venue choice and submission

- Choose a venue whose scope includes applied machine learning, multimedia forensics or security systems, and whose proceedings are indexed in IEEE Xplore or Scopus. IEEE CONECCT (organised by the IEEE Bangalore Section) and IEEE INDICON are examples to check; confirm this year's dates, scope, page limit and fees on their official sites. The IEEE conference search at conferences.ieee.org lets you filter by country and topic.
- Avoid "journals" that promise acceptance in days, charge before review, or have no verifiable indexing.
- Before submitting, have your guide or another faculty member review it as a critical reviewer would. `GOAL.md` also has a reviewer-simulation prompt.
- If it is rejected, revise using the reviews and resubmit. Most published papers have been rejected at least once.

---

## 4. Six-week timeline (from 13 October 2026)

Adjust to your chosen venue's deadline.

| Week | Dates | Work |
|---|---|---|
| 1 | 13–19 Oct | Phase 0 set-up; P1 manifest and first LCNN runs; start collecting T2 images and team photographs |
| 2 | 20–26 Oct | Finish P1 (three seeds, eval once); P2 integration and audio heuristics; P3 harness |
| 3 | 27 Oct–2 Nov | Re-run H560 (P3); freeze the configuration; finish T2; run baselines (P4) |
| 4 | 3–9 Nov | P5 robustness, ablations, calibration, abstention, statistics; P6 video decision; P7 if time allows |
| 5 | 10–16 Nov | P8 reproducibility package; P9 paper rewrite from `paper_results/` |
| 6 | 17–23 Nov | Reference verification, internal review, page cut, anonymisation, submission |

---

## 5. Problems that get a paper rejected regardless of its results

- Numbers in the paper that the repository cannot reproduce, or that contradict other documents in it.
- Any choice tuned on the data used for the final results.
- A title or abstract that claims more than the experiments show.
- References that do not exist or are cited incorrectly.
- A similarity score above the venue's threshold.
- Undisclosed AI-generated text, where the venue requires disclosure.
- Template violations, over-length submissions, or author names left in a double-blind submission.

---

## 6. Title options depending on the outcome

- If audio and image both succeed: *DeepSentinel AI: Measurement-Driven Detection of AI-Generated Images and Synthetic Speech in an Evidence-First Forensic Platform*
- If only image succeeds: *Measure Before You Trust: Building and Auditing an Evidence-First Detector for AI-Generated Images*

---

## 7. Using AI coding agents for this work

- Put `CLAUDE.md` in the repository root. Claude Code reads it automatically at the start of every session. In Antigravity, begin each task by telling the agent to read `CLAUDE.md` and `docs/paper_upgrade/GOAL.md` first.
- Work on a branch (`paper-upgrade`), run one phase per session, and ask the agent for a plan before it edits anything.
- Read every diff before accepting it. You will be asked about this code in your viva.
- Run multi-hour training yourself in a terminal from the command the agent writes, not inside the agent's session, because agent sessions can time out.
- Do not let two agents edit the same files at the same time. A reasonable split is Claude Code for changes to the repository, and Antigravity's browser for checking dataset pages, licences and references.
- The agents are told never to invent or adjust a number. Hold them to it. If a result is worse than you hoped, it still goes in the paper.

---

## 8. What to expect

Doing P1 to P5 properly removes the objections most likely to sink the paper and makes a solid IEEE conference a realistic target. It does not guarantee acceptance; nothing does. The results may come out lower than the current H560 figures, especially on newer generators and on In-the-Wild audio. Reported honestly with intervals and analysis, those results are still publishable, and they are far easier to defend in front of reviewers and examiners than numbers that cannot be reproduced.
