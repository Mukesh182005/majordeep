# Resources for the paper upgrade

Everything the plan needs from outside the repository: what is already on this
machine, what can be downloaded with one command, and what only you can obtain.
Checked 2026-10-14. Data lives under `C:\deepsentinel_data` (set
`$env:DEEPSENTINEL_DATA = "C:\deepsentinel_data"`); none of it is committed.

## 1. On this machine (downloaded and verified)

| Resource | Local path | Size | Verified | Source and licence | Used in |
|---|---|---|---|---|---|
| ASVspoof 2019 LA (`LA.zip`) | `downloads\asvspoof2019\LA.zip`, extracted to `ASVspoof2019\LA` | 7,640,952,520 B | MD5 `30c98f11d8b2bc21f2c257bfd78bb5c5`, as published on DataShare | https://doi.org/10.7488/ds/2555; Open Data Commons Attribution License 1.0 (README.txt) | Phases 1–3 |
| ASVspoof 2019 README, licence, evaluation plan, challenge paper | `downloads\asvspoof2019\` | – | MD5s match DataShare | same record | t-DCF definition; baselines |
| Official ASVspoof EER / t-DCF code (`eval_metrics.py`, incl. `compute_tDCF_legacy` for 2019) | `tools\asvspoof_eval_metrics_official.py` | 19 KB | – | `asvspoof-challenge/2021`, `eval-package/` (no top-level licence, so not copied into this repository) | Cross-check in `backend/tests/test_asvspoof_metrics.py` |
| UnivFD official code + linear head `fc_weights.pth` | `baselines\UniversalFakeDetect` (commit `030495a`) | – | – | https://github.com/WisconsinAIVision/UniversalFakeDetect, MIT | Phase 5 baseline |
| CLIP ViT-L/14 weights for UnivFD | `baselines\clip_weights\ViT-L-14.pt` | 932,768,134 B | SHA-256 `b8cca3fd…a03836` = OpenAI's published hash | OpenAI CLIP release | Phase 5 baseline |
| CNNDetection official code + `blur_jpg_prob0.5.pth` | `baselines\CNNDetection` (commit `ea0b562`) | 282,442,597 B | SHA-256 `3533f3e58a3b82215f21197f2faf4e99b911ec42a4a6e2d7823e04d5f3fd245a` | https://github.com/PeterWang512/CNNDetection, CC BY-NC-SA 4.0 | Phase 5 baseline |
| Synthbuster (T2 generated images) | `downloads\synthbuster.zip` (not yet extracted; 13.58 GB unpacked) | 12,372,557,226 B | MD5 `0695bd328e16ea21c5c9cc2ae1d994ff`, as published on Zenodo | https://doi.org/10.5281/zenodo.10066460, CC BY-NC-SA 4.0 | Phase 5 (T2): 9,000 PNGs, 1,000 each from DALL-E 2, DALL-E 3, Adobe Firefly, GLIDE, Midjourney v5, Stable Diffusion 1.3, 1.4, 2 and XL, plus `prompts.csv` |

The wrappers `ml/evaluation/baselines/univfd.py` and `cnndetection.py` were
checked against the official code paths with
`ml/evaluation/baselines/verify_official.py` on four images: UnivFD outputs were
identical (absolute difference 0.0, float32) and CNNDetection matched the
official `demo.py` output on every image.

## 2. Downloadable with one command (not yet downloaded)

Run from PowerShell; each command resumes if interrupted. For large files, `scriptsetch_dataset.py` (parallel byte ranges, reconnects stalled connections, verifies the MD5) is faster: single connections to DataShare and Zenodo slowed to under 0.5 MB/s during the ASVspoof download.

| Resource | Size | Licence | Command |
|---|---|---|---|
| COCO val2017 (T2 real-photo candidates) | 815,585,330 B | Annotations and image terms to be checked on cocodataset.org | `curl.exe -L -C - -o C:\deepsentinel_data\downloads\coco_val2017.zip "http://images.cocodataset.org/zips/val2017.zip"` |
| In-the-Wild audio (optional cross-dataset test) | 8,161,489,023 B | **Conflict:** project page says Apache 2.0, Hugging Face card says CC BY-SA 4.0; resolve before use | `python -c "from huggingface_hub import hf_hub_download; hf_hub_download('mueller91/In-The-Wild', 'release_in_the_wild.zip', repo_type='dataset', local_dir=r'C:\deepsentinel_data\downloads')"` |

Disk (2026-10-14): after extracting ASVspoof, building its 15 GB feature cache and downloading Synthbuster, C: had about 51 GB free; extracting Synthbuster needs 13.6 GB more.

## 3. Only you can obtain these

| Resource | Why I cannot | What to do |
|---|---|---|
| **H560** (the 560 held-out images) | Not on C:, D: or in your Google Drive; no script in the repository produced its numbers. | Tell me where the images are, or confirm they are lost. |
| **RAISE-1k** (real photos that pair with Synthbuster) | The download form asks for your full name, affiliation and email and an agreement to its terms (non-commercial research and education only). | Fill in http://loki.disi.unitn.it/RAISE/confirm.php?package=1k and save the files under `C:\deepsentinel_data\RAISE1k`. |
| Team photographs (at least 200) and messenger-forwarded copies | They must be taken by the team. | Prefer scenes without identifiable people; get written consent from anyone identifiable. |
| Images from newer generators (at least 100 per generator) | Needs your accounts on those services, and their terms. | Record generator, version, date and prompt for every image. |
| FakeAVCeleb (only for Phase 7 Option A) | Access by request form. | https://github.com/DASH-Lab/FakeAVCeleb |
| The paper's LaTeX source (9- and 14-page drafts) | Not found on this machine. | Put it in `paper/latex/` before Phase 10. A Google Doc "DeepSentinel_AI_IEEE_Paper" (created 2026-08-08) exists in your Drive: https://docs.google.com/document/d/1TOTNV6S_9khK0QQtFfUxDdMTWstW0mWxKJFV9ty1-WQ/edit |

## 4. References checked on Crossref (2026-10-14)

| Work | DOI |
|---|---|
| Todisco et al., "ASVspoof 2019: Future Horizons in Spoofed and Fake Audio Detection", Interspeech 2019, pp. 1008–1012 | 10.21437/Interspeech.2019-2249 |
| Wang et al., "ASVspoof 2019: A large-scale public database of synthesized, converted and replayed speech", Computer Speech & Language 64, 101114, 2020 | 10.1016/j.csl.2020.101114 |
| Nautsch et al., "ASVspoof 2019: Spoofing Countermeasures for the Detection of Synthesized, Converted and Replayed Speech", IEEE T-BIOM 3, pp. 252–265, 2021 | 10.1109/TBIOM.2021.3059479 |
| Kinnunen et al., "t-DCF: a Detection Cost Function for the Tandem Assessment of Spoofing Countermeasures and Automatic Speaker Verification", Odyssey 2018, pp. 312–319 | 10.21437/Odyssey.2018-44 |
| Lavrentyeva et al., "STC Antispoofing Systems for the ASVspoof2019 Challenge" (LCNN), Interspeech 2019, pp. 1033–1037 | 10.21437/Interspeech.2019-1768 |
| Müller et al., "Does Audio Deepfake Detection Generalize?", Interspeech 2022, pp. 2783–2787 | 10.21437/Interspeech.2022-108 |
| Ojha, Li and Lee, "Towards Universal Fake Image Detectors that Generalize Across Generative Models", CVPR 2023, pp. 24480–24489 | 10.1109/CVPR52729.2023.02345 |
| Wang et al., "CNN-Generated Images Are Surprisingly Easy to Spot... for Now", CVPR 2020, pp. 8692–8701 | 10.1109/CVPR42600.2020.00872 |
| Bammey, "Synthbuster: Towards Detection of Diffusion Model Generated Images", IEEE Open Journal of Signal Processing, 2024, pp. 1–9 | 10.1109/OJSP.2023.3337714 |
| Dang-Nguyen et al., "RAISE: A Raw Images Dataset for Digital Image Forensics", ACM MMSys 2015, pp. 219–224 | 10.1145/2713168.2713194 |
| Lin et al., "Microsoft COCO: Common Objects in Context", ECCV 2014, LNCS pp. 740–755 | 10.1007/978-3-319-10602-1_48 |
| DeLong, DeLong and Clarke-Pearson, "Comparing the Areas under Two or More Correlated ROC Curves", Biometrics, 1988 | 10.2307/2531595 |
| Sun and Xu, "Fast Implementation of DeLong's Algorithm for Comparing the Areas Under Correlated ROC Curves", IEEE Signal Processing Letters, 2014, pp. 1389–1393 | 10.1109/LSP.2014.2337313 |
| Khalid, Tariq and Woo, "FakeAVCeleb: A Novel Audio-Video Multimodal Deepfake Dataset" | no Crossref DOI found; arXiv:2108.05080 |

These still need the full BibTeX export (DBLP or publisher) in Phase 10.
