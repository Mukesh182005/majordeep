# Index of paper numbers

Every number that appears in the paper, with the file and key it comes from.
Rows are added by the phase that produces the number; never by hand-typing a
value that no file contains.

| Paper item | Value | File | Key | Phase |
|---|---|---|---|---|
<!-- begin:asvspoof2019la_dataset -->
| ASVspoof 2019 LA train: utterances | 25,380 | `paper_results/audio_asvspoof2019la/dataset_summary.json` | `splits.train.utterances` | 1 |
| ASVspoof 2019 LA train: bona fide | 2,580 | `paper_results/audio_asvspoof2019la/dataset_summary.json` | `splits.train.bonafide` | 1 |
| ASVspoof 2019 LA train: spoof | 22,800 | `paper_results/audio_asvspoof2019la/dataset_summary.json` | `splits.train.spoof` | 1 |
| ASVspoof 2019 LA dev: utterances | 24,844 | `paper_results/audio_asvspoof2019la/dataset_summary.json` | `splits.dev.utterances` | 1 |
| ASVspoof 2019 LA dev: bona fide | 2,548 | `paper_results/audio_asvspoof2019la/dataset_summary.json` | `splits.dev.bonafide` | 1 |
| ASVspoof 2019 LA dev: spoof | 22,296 | `paper_results/audio_asvspoof2019la/dataset_summary.json` | `splits.dev.spoof` | 1 |
| ASVspoof 2019 LA eval: utterances | 71,237 | `paper_results/audio_asvspoof2019la/dataset_summary.json` | `splits.eval.utterances` | 1 |
| ASVspoof 2019 LA eval: bona fide | 7,355 | `paper_results/audio_asvspoof2019la/dataset_summary.json` | `splits.eval.bonafide` | 1 |
| ASVspoof 2019 LA eval: spoof | 63,882 | `paper_results/audio_asvspoof2019la/dataset_summary.json` | `splits.eval.spoof` | 1 |
<!-- end:asvspoof2019la_dataset -->
<!-- begin:audio_asvspoof2019la -->
| Audio LA eval EER, mean (%) | 5.26 | `paper_results/audio_asvspoof2019la/metrics.json` | `summary.eer_percent.mean` | 2 |
| Audio LA eval EER, SD (%) | 0.65 | `paper_results/audio_asvspoof2019la/metrics.json` | `summary.eer_percent.sd` | 2 |
| Audio LA eval AUC, mean | 0.9831 | `paper_results/audio_asvspoof2019la/metrics.json` | `summary.auc_bonafide_vs_spoof.mean` | 2 |
| Audio LA eval min t-DCF, mean | 0.1104 | `paper_results/audio_asvspoof2019la/metrics.json` | `summary.min_tdcf.mean` | 2 |
| Audio LA eval min t-DCF, SD | 0.0142 | `paper_results/audio_asvspoof2019la/metrics.json` | `summary.min_tdcf.sd` | 2 |
| Audio LA eval EER A07, mean (%) | 0.32 | `paper_results/audio_asvspoof2019la/metrics.json` | `summary.per_attack_eer_percent.A07.mean` | 2 |
| Audio LA eval EER A08, mean (%) | 1.74 | `paper_results/audio_asvspoof2019la/metrics.json` | `summary.per_attack_eer_percent.A08.mean` | 2 |
| Audio LA eval EER A09, mean (%) | 0.10 | `paper_results/audio_asvspoof2019la/metrics.json` | `summary.per_attack_eer_percent.A09.mean` | 2 |
| Audio LA eval EER A10, mean (%) | 0.78 | `paper_results/audio_asvspoof2019la/metrics.json` | `summary.per_attack_eer_percent.A10.mean` | 2 |
| Audio LA eval EER A11, mean (%) | 0.41 | `paper_results/audio_asvspoof2019la/metrics.json` | `summary.per_attack_eer_percent.A11.mean` | 2 |
| Audio LA eval EER A12, mean (%) | 0.30 | `paper_results/audio_asvspoof2019la/metrics.json` | `summary.per_attack_eer_percent.A12.mean` | 2 |
| Audio LA eval EER A13, mean (%) | 0.39 | `paper_results/audio_asvspoof2019la/metrics.json` | `summary.per_attack_eer_percent.A13.mean` | 2 |
| Audio LA eval EER A14, mean (%) | 2.44 | `paper_results/audio_asvspoof2019la/metrics.json` | `summary.per_attack_eer_percent.A14.mean` | 2 |
| Audio LA eval EER A15, mean (%) | 2.74 | `paper_results/audio_asvspoof2019la/metrics.json` | `summary.per_attack_eer_percent.A15.mean` | 2 |
| Audio LA eval EER A16, mean (%) | 0.55 | `paper_results/audio_asvspoof2019la/metrics.json` | `summary.per_attack_eer_percent.A16.mean` | 2 |
| Audio LA eval EER A17, mean (%) | 26.90 | `paper_results/audio_asvspoof2019la/metrics.json` | `summary.per_attack_eer_percent.A17.mean` | 2 |
| Audio LA eval EER A18, mean (%) | 2.06 | `paper_results/audio_asvspoof2019la/metrics.json` | `summary.per_attack_eer_percent.A18.mean` | 2 |
| Audio LA eval EER A19, mean (%) | 3.53 | `paper_results/audio_asvspoof2019la/metrics.json` | `summary.per_attack_eer_percent.A19.mean` | 2 |
| Baseline B01 CQCC-GMM eval EER (%) [published] | 9.57 | `paper_results/audio_asvspoof2019la/baselines.json` | `eval.B01_CQCC_GMM.eer_percent` | 2 |
| Baseline B02 LFCC-GMM eval EER (%) [published] | 8.09 | `paper_results/audio_asvspoof2019la/baselines.json` | `eval.B02_LFCC_GMM.eer_percent` | 2 |
<!-- end:audio_asvspoof2019la -->
<!-- begin:audio_heuristics_dev -->
| Audio dev subsample: AUC of LCNN (ASVspoof-trained) probability | 1.000 [1.000, 1.000] | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``signals.lcnn_prob.auc`, `.ci95`` | 3 |
| Audio dev subsample: AUC of Glottal anomaly score | 0.552 [0.527, 0.578] | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``signals.glottal_anomaly.auc`, `.ci95`` | 3 |
| Audio dev subsample: AUC of Coarticulation anomaly score | 0.518 [0.494, 0.543] | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``signals.coarticulation_anomaly.auc`, `.ci95`` | 3 |
| Audio dev subsample: AUC of Environment / mains-hum anomaly | 0.504 [0.499, 0.509] | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``signals.environment_anomaly.auc`, `.ci95`` | 3 |
| Audio dev subsample: AUC of Splice timeline: worst segment | 0.499 [0.498, 0.500] | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``signals.splice_worst_segment.auc`, `.ci95`` | 3 |
| Audio dev subsample: AUC of Splice timeline: F1 spikes | 0.428 [0.404, 0.453] | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``signals.splice_f1_spikes.auc`, `.ci95`` | 3 |
| Audio dev subsample: AUC of Splice timeline flag | 0.499 [0.498, 0.500] | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``signals.splice_flag.auc`, `.ci95`` | 3 |
| Audio dev subsample: AUC of Untrained SincRawNet branch | 0.568 [0.544, 0.592] | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``signals.model_rawnet.auc`, `.ci95`` | 3 |
| Audio dev subsample: AUC of Spectral-smoothness branch (labelled WavLM) | 0.414 [0.389, 0.440] | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``signals.model_spectral_smoothness.auc`, `.ci95`` | 3 |
| Audio dev subsample: AUC of Tabular rules branch | 0.552 [0.527, 0.578] | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``signals.model_tabular.auc`, `.ci95`` | 3 |
| Audio dev subsample: AUC of Legacy model stage (fused) | 0.419 [0.394, 0.444] | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``signals.model_stage_fused.auc`, `.ci95`` | 3 |
| Audio dev subsample: AUC of Synthesis risk R_synth | 0.470 [0.444, 0.496] | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``signals.r_synth.auc`, `.ci95`` | 3 |
| Audio dev subsample: AUC of Tampering risk R_tamper | 0.560 [0.549, 0.570] | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``signals.r_tamper.auc`, `.ci95`` | 3 |
| Audio dev subsample: AUC of Legacy final probability | 0.556 [0.543, 0.569] | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``signals.legacy_final_prob.auc`, `.ci95`` | 3 |
| Audio dev subsample: legacy verdict AUTHENTIC, bonafide | 0.0% (0/1000) | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``legacy_verdict_rates.bonafide.AUTHENTIC.rate`` | 3 |
| Audio dev subsample: legacy verdict INCONCLUSIVE, bonafide | 99.1% (991/1000) | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``legacy_verdict_rates.bonafide.INCONCLUSIVE.rate`` | 3 |
| Audio dev subsample: legacy verdict MANIPULATED, bonafide | 0.9% (9/1000) | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``legacy_verdict_rates.bonafide.MANIPULATED.rate`` | 3 |
| Audio dev subsample: legacy verdict AUTHENTIC, spoof | 0.1% (1/1000) | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``legacy_verdict_rates.spoof.AUTHENTIC.rate`` | 3 |
| Audio dev subsample: legacy verdict INCONCLUSIVE, spoof | 87.0% (870/1000) | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``legacy_verdict_rates.spoof.INCONCLUSIVE.rate`` | 3 |
| Audio dev subsample: legacy verdict MANIPULATED, spoof | 12.9% (129/1000) | ``paper_results/audio_heuristics_dev/signal_auc.json`` | ``legacy_verdict_rates.spoof.MANIPULATED.rate`` | 3 |
<!-- end:audio_heuristics_dev -->
<!-- begin:audio_lcnn_repro -->
| Re-run lfcc_seed2 vs recorded audio_lcnn_asvspoof_lfcc_seed2: best epoch equal | yes (20 / 20) | ``paper_results/audio_asvspoof2019la/repro_runs/lfcc_seed2/comparison.json`` | ``best_epoch.equal`` | 3 |
| Re-run lfcc_seed2 vs recorded audio_lcnn_asvspoof_lfcc_seed2: dev EER, EER threshold, min t-DCF and AUC equal | yes | ``paper_results/audio_asvspoof2019la/repro_runs/lfcc_seed2/comparison.json`` | ``dev_metrics_all_equal`` | 3 |
| Re-run lfcc_seed2 vs recorded audio_lcnn_asvspoof_lfcc_seed2: per-utterance dev scores byte-identical | yes | ``paper_results/audio_asvspoof2019la/repro_runs/lfcc_seed2/comparison.json`` | ``dev_scores.byte_identical`` | 3 |
| Re-run lfcc_seed2 vs recorded audio_lcnn_asvspoof_lfcc_seed2: checkpoint weights bit-identical | yes | ``paper_results/audio_asvspoof2019la/repro_runs/lfcc_seed2/comparison.json`` | ``weights.bit_identical`` | 3 |
<!-- end:audio_lcnn_repro -->
