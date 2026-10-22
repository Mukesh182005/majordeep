Agent prompts
Paste each prompt into the agent named in its heading, on that phase's branch. Every
prompt asks for a plan first; approve it before any edits.
Shared rules for both agents
Save this as CLAUDE.md at the repo root and paste the same text into Antigravity's project
rules, so both agents follow one set of rules.
# DeepSentinel AI (repo: majordeep)
Stack: FastAPI, SQLAlchemy, Alembic, Celery + Redis, Postgres (backend/);
React + Vite + Tailwind (frontend/); PyTorch inference in backend/app/ml/.
Live pipelines: app/ml/image_pipeline.py, app/ml/audio_pipeline.py,
app/ml/video/__init__.py. backend/app/ml_v1/ is a legacy copy: never edit it.
Commands
- Backend tests: cd backend && python -m pytest -q
- Frontend tests: cd frontend && npm test -- --run
- Frontend lint: cd frontend && npm run lint
- Full stack: docker compose up --build
Rules
- Never invent metrics, dataset names, model names or citations. Every number
comes from a script in the repo and the results file it writes.
- Never present a heuristic as a trained model. Label unvalidated signals
"unvalidated" in the UI and the PDF.
- No legal or standards-compliance claims (ISO, SWGDE, Daubert, "courtready").
- Never edit files in results/ or checkpoints/ by hand.
- Touch only the files your task needs, and stay on your branch.
- Propose a plan before editing. Before saying a task is done, run the
backend
tests (and the frontend tests if you touched frontend/) and report the
result.
- Pin every dependency you add in backend/requirements*.txt.
Agent prompts
Page 1 of 11
Day 1: Phase 0 and Phase 1
Claude Code · branch fix/p0-deps
Read CLAUDE.md. Task: make the Docker build able to analyse media.
1. backend/app/ml imports librosa, scipy, soundfile and imagehash, but
backend/requirements-ml.txt does not list them. Add them. Add pypdf to
backend/requirements-dev.txt.
2. Create a pinned lock file for the CPU Docker image (uv pip compile or
pip-tools) and make backend/Dockerfile install from it. Keep the CUDA
index
out of the CPU image; put GPU wheels in backend/requirements-gpu.txt.
3. Make the torch version in backend/Dockerfile and RELEASE_MANIFEST.json
agree.
Plan first. Done = docker compose up --build, then one image, one WAV and one
MP4 uploaded through /api/upload each reach status "done", and pytest passes.
Claude Code · branch fix/p1-honest-outputs
Read CLAUDE.md. Task: remove outputs that name models or standards that do
not exist.
1. backend/app/ml/audio/models_arch.py: SincRawNet never loads weights, and
_probe_ssl_representations returns an FFT heuristic labelled "WavLM Layer
18"
and "Whisper Layer 4". Remove both branches. Keep the tabular score,
labelled
"heuristic (unvalidated)".
2. Update every place that prints those names: app/ml/audio/__init__.py
(stage 6), audio_pipeline.py (model_name, model_version) and
app/report/generator.py. List any frontend files that show them; do not
edit
frontend/.
3. Remove legal and standards claims: "Judicial Standard Compliance", SWGDE,
ISO/IEC 27037 and 27042, Daubert, "Write-blocker access emulated"
(app/report/generator.py, app/ml/audio/vault.py,
app/ml/audio/__init__.py),
and "suitable for attaching to a cybercrime complaint" in app/main.py.
4. app/ml/video/generator_attribution.py: delete has_name_hint and all
filename
keyword matching; in container_forensics.py stop scanning file_path.name.
Mark generator attribution "unvalidated" in its output.
5. Until a trained audio model exists, mark audio results "experimental" in
Agent prompts
Page 2 of 11
the API response and add a note saying why.
Update the tests. Plan first. Done = pytest passes, and none of WavLM,
Whisper,
Sinc-RawNet, SWGDE, Daubert, 27037 or 27042 appears in backend/app outside
ml_v1.
Antigravity · branch fix/p1-frontend
Read the project rules. Task: frontend honesty fixes and CI. Do not edit
backend/.
1. In frontend/src, remove or relabel every mention of WavLM, Whisper,
Sinc-RawNet, "10-Engine", SWGDE, ISO, Daubert or court use, including the
ElevenLabs and Sora/Veo attribution claims in HowItWorks.jsx.
2. Add a banner on the Result and Report pages: "Automated assessment only.
Not forensic or legal evidence."
3. When the API marks audio as experimental, show an "Experimental" badge on
the audio result.
4. Add .github/workflows/ci.yml: build backend/Dockerfile, run pytest in that
image, then npm ci, npm test -- --run and npm run build in frontend/.
Plan first. Done = frontend tests pass, the build succeeds, and CI is green
on
this branch.
Days 2–3: Phase 5 and the beta deploy
Claude Code · branch fix/p5-security
Read CLAUDE.md. Task: security and privacy for public users.
1. app/deps.py client_ip trusts the first X-Forwarded-For value, which the
client controls. Use X-Real-IP (set by frontend/nginx.conf) only when the
request comes from a trusted proxy (TRUSTED_PROXIES setting), else
request.client.host. Test that a faked X-Forwarded-For cannot dodge the
guest limit.
2. docker-compose.yml: pass UPLOAD_RATE_LIMIT_PER_HOUR,
GUEST_RATE_LIMIT_PER_HOUR, FACE_MODEL_IN_VERDICT and a new RETENTION_HOURS
to the api and worker services.
3. Add a Celery beat schedule, and a beat service in docker-compose.yml, that
deletes guest jobs older than RETENTION_HOURS: the upload, every evidence
file and every report.
4. app/routers/history.py delete_scan: delete every evidence file the job
produced (every *_file key in evidence, plus files named with the job id
Agent prompts
Page 3 of 11
in
EVIDENCE_DIR), not only the heatmap and spectrogram.
5. Replace ?token= on report download and the job WebSocket with short-lived
signed URLs (HMAC over job id + expiry, 5 minutes).
6. Log in with an httpOnly, Secure, SameSite=Lax cookie; keep Bearer tokens
for API clients.
7. At upload, reject video longer than MAX_VIDEO_SECONDS and audio longer
than
MAX_AUDIO_SECONDS.
8. Add ENABLED_MEDIA_TYPES (default image,audio,video), checked at upload.
9. Use torch.load(weights_only=True) wherever the checkpoint format allows.
Plan first. Done = pytest passes, with new tests for items 1, 3, 4, 5, 7 and
8.
Antigravity · branch fix/p5-frontend
Read the project rules. Claude Code is changing the backend on
fix/p5-security; read its API changes before you start.
Part A, now (frontend/ only):
1. frontend/src/lib/api.js: stop storing the token in localStorage; send
requests with credentials: 'include' and rely on the httpOnly cookie. Use
the signed URLs the API returns for report downloads and the WebSocket.
2. Add a Privacy page: what is stored, the retention window, how to delete,
and that results have no legal standing. Link it from the footer and the
upload page.
Part B, after fix/p5-security is merged:
3. backend/app/main.py lifespan: skip model warm-up when CELERY_BROKER_URL is
set. This is the only backend file you may edit.
4. docker-compose.yml: worker --concurrency=1, preload the Hugging Face scene
detectors in the worker, and a named volume for the HF cache (HF_HOME).
Plan first. Done = frontend tests pass, login and report download work
against the new backend, and only the worker container holds the models.
Agent prompts
Page 4 of 11
Antigravity · branch deploy/beta
Read the project rules. Task: deploy the image-only beta.
1. Target: <Oracle Cloud Always Free ARM VM (2 OCPU, 12 GB RAM) | the lab
RTX 5070 machine behind a Cloudflare Tunnel>. Write deploy/README.md with
the exact steps you ran.
2. Production .env: ENVIRONMENT=production, DEBUG=false, a random 48-byte
JWT_SECRET_KEY, a strong POSTGRES_PASSWORD, CORS_ORIGINS = the real
domain,
ENABLED_MEDIA_TYPES=image.
3. HTTPS with Caddy in front of the frontend container, or the Cloudflare
Tunnel; nginx client_max_body_size must match MAX_UPLOAD_MB.
4. Nightly pg_dump kept for 7 days, and an alert when the media disk passes
80%.
5. An uptime check on /api/health.
6. Browser smoke test: register, upload 3 real photos and 3 AI images,
download a PDF, delete a scan, confirm its files are gone.
Plan first. Done = the beta is reachable over HTTPS and every smoke-test step
passes.
Days 3–5: Phase 2 audio model
The agents write the code; you start each training run yourself on the RTX 5070 before
you stop for the night.
Agent prompts
Page 5 of 11
Claude Code · branch ml/audio-asvspoof
Read CLAUDE.md. Task: train a real audio deepfake detector on ASVspoof 2019
LA,
on my local RTX 5070 (12 GB).
1. Retire checkpoints/audio_detector.pt: scripts/run_audio_pipeline.ps1
trained
it on sine-wave clips from scripts/generate_massive_audio_dataset.py. Move
both scripts to an archive folder and record this in KNOWN_ISSUES.md.
2. Write ml/data/asvspoof_la.py: read the official LA protocol files (train,
dev, eval) from a --root path. No rebalancing that copies files across
splits.
3. Adapt ml/training/train_audio.py: LCNN on LFCC or log-Mel, 4 s windows at
16 kHz, mixed precision, class-weighted loss, early stopping on dev EER.
Save metadata in the checkpoint: dataset, protocol files, epochs,
features,
window, sample rate, git commit, and the threshold chosen on dev.
4. Write ml/evaluation/eval_audio.py: EER on LA eval (min t-DCF too if the
ASV
score files are present), and EER on In-the-Wild when --itw is given.
Write
results/audio_eval.json and a DET or ROC plot.
Plan first, ending with the exact training command. Done = a training run
starts on the GPU, and eval_audio.py writes results/audio_eval.json from a
trained checkpoint.
Agent prompts
Page 6 of 11
Claude Code · branch ml/audio-wire
Read CLAUDE.md. Task: make the trained audio model the audio verdict.
1. audio_pipeline.py loads get_audio_model() but never calls it. Score
sliding
4 s windows (50% overlap), aggregate as the mean of the top 3 windows, and
use that as fake_probability with the threshold stored in the checkpoint.
2. Remove typology_breakdown and generator_family_attribution; they were
built
on the removed branches.
3. Keep glottal, ENF, splicing and signal checks as notes with no weight in
the verdict. Drop the "experimental" flag only when weights_status is
"trained".
4. Feed the per-window scores into the existing segment timeline.
5. Add tests/test_audio_regression.py: load labelled clips from
AUDIO_REGRESSION_DIR (skip when unset) and assert the AUC stays within
0.05
of results/audio_eval.json.
6. The same file scored in two fresh processes must give identical scores;
add a test.
Plan first. Done = pytest passes, and an uploaded LA eval clip gets its
verdict from the trained model.
Antigravity · branch ui/audio-results
Read the project rules. Task: audio result page for the trained model. Do not
edit backend/.
1. AudioForensicsView.jsx: make the trained-model score and the per-window
timeline the main result. Move glottal, ENF and signal checks under
"Supporting signals (unvalidated)".
2. Remove the typology and generator-family panels.
3. Update the tests.
Plan first. Done = frontend tests pass, and the page renders a real response
from the ml/audio-wire backend.
Days 5–9: Phase 3 face-swap model
These start once FF++ and Celeb-DF access arrives. Until then, run the Day 9–13
evaluation and cleanup prompts instead.
Agent prompts
Page 7 of 11
Antigravity · branch ml/faces-data
Read the project rules. Task: build the face-crop dataset from
FaceForensics++
(c23) and Celeb-DF v2.
1. ml/preprocessing/extract_faces.py: sample 32 frames per video, detect
faces
with the same MTCNN setup as backend/app/ml/faces.py, crop with the same
margin and size, save JPEGs at quality 95, and write a CSV: path, label,
manipulation, video_id, identity, split.
2. Splits: the official FF++ train/val/test split files, by video. Celeb-DF:
its official testing-video list is the test set.
3. ml/preprocessing/check_dataset.py: counts per split, class and
manipulation; fail if any video or identity sits in two splits.
Plan first. Done = check_dataset.py passes on the extracted crops.
Claude Code · branch ml/faceswap-train
Read CLAUDE.md. Task: train the EfficientNet-B4 face-swap detector on my
local
RTX 5070 (12 GB).
1. Adapt ml/training/train_image.py to the CSV from extract_faces.py: 224 px
input, the same normalisation as backend/app/ml/preprocessing.py, mixed
precision, batch 32, AdamW, cosine schedule, early stopping on validation
video-level AUC.
2. Augmentations: random JPEG quality 30–95, downscale then upscale, light
blur, horizontal flip, colour jitter.
3. Balance real and fake within each batch (FF++ has 4 fakes per real video).
4. Calibrate with temperature scaling on validation; store the temperature,
threshold, input size and backbone in the checkpoint metadata.
5. ml/evaluation/eval_faces.py: frame- and video-level AUC on the FF++ test
split and Celeb-DF v2 test, per manipulation type; write
results/faceswap_eval.json and ROC plots.
Plan first, ending with the exact training command. Done = a run trains on
the GPU, and eval_faces.py writes results/faceswap_eval.json.
Agent prompts
Page 8 of 11
Claude Code · branch ml/faceswap-wire
Read CLAUDE.md. Task: use the new face-swap model in image and video
verdicts.
1. app/ml/registry.py: load the new checkpoint and apply its temperature and
threshold.
2. image_pipeline.py: when FACE_MODEL_IN_VERDICT=true and a face is found,
include the calibrated face score in the verdict, and report which signal
drove it.
3. Video: group frames into face tracks; a track's score is the mean of its
top 25% frame scores; the video score is the highest track score. The
segment timeline must use these same scores (KNOWN_ISSUES #11).
4. Sample short clips densely: 4 fps under 30 s, else 1 fps, capped by
VIDEO_MAX_FRAMES.
5. Regression test from FACESWAP_REGRESSION_DIR (skip when unset): AUC within
0.05 of results/faceswap_eval.json.
6. Update KNOWN_ISSUES.md (#9, #10, #11) and docs/models/MODEL_CARD.md using
numbers from results/faceswap_eval.json only.
Plan first. Done = pytest passes, and an FF++ test deepfake uploaded through
the API is flagged.
Antigravity · branch ui/video-results
Read the project rules. Task: video result page for the face-swap model. Do
not edit backend/.
1. VideoForensicsView.jsx: show per-track scores and the timeline from the
new response; label generator attribution and other heuristics
"unvalidated".
2. When no face track exists, say: "No face found: face-swap check not
applicable."
3. Update the tests.
Plan first. Done = frontend tests pass with a real response from the
ml/faceswap-wire backend.
Days 9–13: Phase 4,final deploy and Phase 7
Claude Code · branch eval/reproducible
Read CLAUDE.md. Task: reproducible evaluation for every modality.
1. scripts/eval_image.py: run the full image pipeline over a manifest CSV
(path, label, source, generator) and write results/image_eval.json: AUC,
false-positive rate on real photos, recall per generator, verdict counts
including INCONCLUSIVE, confusion matrix. Rebuild the manifest for the
560-image set; if a source is missing, say so instead of filling numbers.
2. scripts/eval_pipeline.py: full-pipeline verdicts for audio (LA eval and
In-the-Wild subsets) and video (FF++ test, Celeb-DF test).
3. scripts/robustness.py: JPEG 95/75/50/30, 0.5x resize, WhatsApp-style
recompression (1600 px, quality 70); MP3 64 kbps and Opus for audio. Write
results/robustness.json.
4. scripts/benchmark_latency.py: p50 and p95 per modality on this machine,
CPU
and GPU, saved with the hardware details.
5. Save ROC curves, confusion matrices and robustness plots to
results/figures/.
6. Rewrite docs/research/EVALUATION.md and docs/research/DATASETS.md so every
number cites a results file; delete numbers with no file behind them.
Plan first. Done = running the scripts from a clean checkout regenerates
every
file in results/.
Antigravity · branch deploy/release
Read the project rules. Task: deploy all three modalities.
1. Set ENABLED_MEDIA_TYPES=image,audio,video on the server and copy the new
checkpoints, checking their SHA-256.
2. If the server has no GPU, cap video at 60 s, measure queue time, and state
the limit on the upload page.
3. Load test: 10 image uploads and 2 videos at once; record queue and finish
times in deploy/README.md.
4. Error tracking (for example Sentry) or a log you check daily; the uptime
check stays green.
5. Browser walkthrough on phone and desktop: each modality, PDF download,
delete, privacy page.
Plan first. Done = all three modalities work on the public URL, and the
load-test numbers are recorded.
Agent prompts
Page 10 of 11
Claude Code · branch chore/p7-cleanup
Read CLAUDE.md. Task: clean up the repo.
1. Move what app/ml/v2/pipeline.py and backend/scripts/run_real_evaluation.py
and run_diagnostic.py import from app/ml_v1 into app/ml, then delete
app/ml_v1 and app/ml/v2 if nothing else uses them. Correct KNOWN_ISSUES.md
#1.
2. Remove the phase-era scripts in backend/scripts that the new eval scripts
replace. Move research_archive/ to a separate archive branch.
3. Replace hardcoded C:\Users\STUDENT\... paths with command-line arguments.
4. Replace the cmd.exe-only Makefile with targets that work on Linux, macOS
and Windows.
5. Move checkpoints to GitHub Releases; add scripts/fetch_checkpoints.py that
downloads them and checks SHA-256; update .gitignore and the Dockerfile.
Plan first. Done = pytest passes and docker compose up --build works from a
fresh clone.
Antigravity · branch chore/p7-frontend
Read the project rules. Task: frontend cleanup. Do not edit backend/.
1. Fix the 171 errors from npm run lint without disabling rules.
2. Lazy-load routes with React.lazy so no chunk exceeds 500 KB.
3. Turn on the React Router v7 future flags the tests warn about.
Plan first. Done = npm run lint shows 0 errors, the tests pass, and the build
prints no chunk-size warning.
Agent prompts
Page 11 of 11
