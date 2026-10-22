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

## fix/p5-security

### Login: httpOnly cookie
- `POST /api/auth/login` and `POST /api/auth/register` now set the cookie `deepsentinel_session` (httpOnly, SameSite=Lax, `Path=/api`, Secure in production). They still return `access_token` in the body for API clients.
- Every endpoint accepts the cookie or `Authorization: Bearer`. Browsers: send requests with `credentials: 'include'` and stop storing the token in localStorage.
- `POST /api/auth/logout` (204) clears the cookie.

### `?token=` is gone
The report download and the job WebSocket no longer read a token from the query string. Use:
- **Signed links**: `POST /api/jobs/{id}/links` (cookie, Bearer, or a guest job) returns `{"report_url", "ws_url", "expires_at"}`. Both URLs are relative to the API origin, carry `exp` and `sig`, open only this job, and expire after 5 minutes (`SIGNED_URL_TTL_SECONDS`). Ask for new links when they expire.
- Same-origin requests with the cookie also work for both endpoints.

### Upload limits
- `ENABLED_MEDIA_TYPES` (default `image,audio,video`): an upload of a disabled type gets **403** "… analysis is not enabled on this server."
- `MAX_AUDIO_SECONDS` (600) / `MAX_VIDEO_SECONDS` (300): longer files get **400** "The audio is N s long; this server analyses at most M s of audio."
- `GET /api/upload/limits` now also returns `enabled_media_types`, `max_duration_seconds` (`{"audio", "video"}`) and `guest_retention_hours`; `allowed_extensions` lists enabled types only.

### Retention and deletion
- Guest jobs (no account) are deleted with every file after `RETENTION_HOURS` (default 72) by the hourly `beat` service. Registered users' jobs are kept until they delete them.
- `DELETE /api/history/{id}` now removes the upload, every evidence image (every `*_file` value and every `EVIDENCE_DIR/<job id>_*` file), the report PDFs and their charts.

### Client IP behind a proxy
`X-Forwarded-For` is never used. `X-Real-IP` is used only when the connection comes from `TRUSTED_PROXIES` (docker-compose: the frontend nginx at 172.28.0.10). If another proxy (Caddy, Cloudflare Tunnel) sits in front of nginx, nginx must be configured with `set_real_ip_from` and `real_ip_header` so its `$remote_addr` is the visitor, or every visitor shares one rate-limit bucket.

## ml/audio-wire

The ASVspoof 2019 LA LCNN is now the audio verdict (`AUDIO_MODEL_SOURCE=lcnn_asvspoof`, the default).

| Field | Meaning |
|---|---|
| `fake_probability` | The LCNN's calibrated spoof probability alone. |
| `verdict` | From the thresholds frozen on ASVspoof dev: AUTHENTIC below `evidence.decision_threshold - evidence.uncertain_band` (0.417), MANIPULATED at or above `+ band` (0.577), INCONCLUSIVE between. |
| `experimental` | `false` (trained model). `true` only with `AUDIO_MODEL_SOURCE=legacy`. |
| `model_name` / `model_version` | `"LCNN (LFCC), ASVspoof 2019 LA"` / `audio-lcnn-asvspoof2019la-lfcc-seed2`. |
| `evidence.segment_scores` | The LCNN's per-window probabilities, the main timeline: `segment_index`, `start_s`, `end_s`, `fake_probability`, `status` (`FLAGGED` / `INCONCLUSIVE` / `AUTHENTIC`), `source: "lcnn_asvspoof"`. `evidence.segment_scores_source` says which timeline it is. |
| `evidence.splice_segment_scores` | The old splice-timeline heuristic, context only. |
| `evidence.fusion_decision.verdict_source` | `"lcnn_asvspoof"` or `"hand_set_rule"`. |
| `evidence.fusion_decision.context_signals` | Tampering risk, glottal and coarticulation scores and the hand-set rule score: shown as "Supporting signals (unvalidated)", **no weight**. |
| `evidence.models_output.lcnn_asvspoof.windows` | Per-window spoof logit and probability with times. |

`evidence.notes[0]` states the model's validation scope (ASVspoof 2019 LA only; not real-world recordings); show it next to the result.
