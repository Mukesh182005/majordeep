# Backend API changes for the frontend

Written by the backend branches for the frontend work (Antigravity). Each
section names the branch that made the change. Field paths are relative to the
`GET /api/jobs/{id}/result` response unless stated otherwise.

## fix/p1-honest-outputs

### New fields
| Field | Meaning |
|---|---|
| `experimental` (bool, top level) | `true` when the verdict does not come from a trained, evaluated model. Today: audio with `AUDIO_MODEL_SOURCE=legacy`. Show an "Experimental" badge. |
| `experimental_reason` (string or null, top level) | Why; show it next to the badge. Also in `evidence.experimental_reason`. |
| `disclaimer` | Now: "Automated assessment only. Not forensic or legal evidence. ..." |
| `evidence.models_output.model_stage_label` (audio) | `"heuristic (unvalidated)"` or `"trained model (ASVspoof 2019 LA)"`. |
| `evidence.models_output.heuristic_scores.tabular_rules_prob` (audio) | The hand-set rule score, labelled unvalidated. |
| `evidence.fusion_decision.decision_set`, `.decision_rule` (audio) | Replace `conformal_prediction_set`; `decision_rule` states the thresholds are hand-set, not calibrated. |
| `evidence.fusion_decision.flagged_signals` (audio) | Replaces `orthogonal_signals_details`. |
| `evidence.generator_attribution.validated` = `false`, `.label` (video) | Generator attribution is an unvalidated heuristic; label it so. Same in `evidence.attribution` from the video fusion. |

### Removed fields (the UI must stop showing them, and must not show defaults in their place)
| Field | Why removed |
|---|---|
| `evidence.models_output.model_branch_scores` (`rawnet_waveform_prob`, `wavlm_l18_acoustic_prob`, `whisper_l4_semantic_prob`, `tabular_physics_prob`) | The "RawNet" network had random weights; the "WavLM"/"Whisper" values were an FFT formula. |
| `evidence.models_output.typology_breakdown`, `.generator_family_attribution` | Derived from the removed values. |
| `evidence.fusion_decision.conformal_prediction_set`, `.conformal_alpha_guarantee` | No conformal procedure exists; no false-positive bound holds. |
| `evidence.fusion_decision.forensic_likelihood_ratio`, `.verbal_scale_interpretation` (and the same keys at `evidence.*`) | Constants (25,000 / 450 / 0.0001), not computed from data. |
| `evidence.fusion_decision.orthogonal_signals_count`, `.orthogonal_signals_details` | Renamed (see above). |
| `evidence.forensics.vault_record.compliance`, `.write_blocker_emulated`, `.chain_of_custody_status`, `.integrity_verified` | Standards and procedure claims that were not true. |
| Evidence-graph edge `weight` values | Invented; they did not match the fusion formula. |

Audio `model_name` is now `"Hand-set audio rules (heuristic, unvalidated)"` (legacy mode) or `"LCNN (LFCC), ASVspoof 2019 LA, with hand-set signal rules"`.

### Frontend files that still show removed names, fields or standards claims
Counts of matching lines at commit time (`grep` for WavLM, Whisper, RawNet, SWGDE, Daubert, ISO 27037/27042, judicial/court, 10-engine and the removed field names, tests excluded):

| File | Lines |
|---|---|
| `frontend/src/components/AudioForensicsView.jsx` | 16 (branch cards with `?? 0.5` defaults, typology bar with invented defaults such as 58 %, likelihood ratio, conformal set) |
| `frontend/src/components/AudioPipelineVisualizer.jsx` | 13 |
| `frontend/src/components/InteractiveArchitectureDiagram.jsx` | 18 (ISO 27037, Daubert, FRE 901/902) |
| `frontend/src/pages/HowItWorks.jsx` | 15 (ISO 27037, Daubert, RawNet, WavLM, ElevenLabs) |
| `frontend/src/pages/Landing.jsx` | 8 |
| `frontend/src/components/PipelineAuditVisualizer.jsx` | 2 |
| `frontend/src/components/VideoPipelineVisualizer.jsx` | 1 |
| `frontend/src/pages/Upload.jsx` | 1 |
