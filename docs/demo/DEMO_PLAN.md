# Demo Plan

## Target Duration: 10–12 minutes

## Prerequisites

- Backend running on `http://localhost:8000`
- Frontend running on `http://localhost:3000`
- At least one test image prepared (one authentic, one AI-generated)
- Browser open, logged in (or register a new account live)

---

## Part 1 — Introduction (1 min)

**Say:**

> "This is Deepfake Detective, a multi-modal forensic analysis platform for detecting AI-generated and manipulated media. It analyzes images, audio, and video using a combination of deep neural networks and classical forensic signal analysis, and produces evidence-backed assessments with integrity-hashed PDF reports."

Show: Landing page briefly.

---

## Part 2 — Upload & Analyze an Image (3 min)

1. Navigate to the **Analyse** page
2. Upload a prepared **AI-generated image**
3. Show the upload progress
4. Show the real-time job status (WebSocket updates)
5. When complete, show the **Result page**:
   - Verdict (MANIPULATED / AUTHENTIC / INCONCLUSIVE)
   - Fake probability and confidence
   - Evidence breakdown
   - Grad-CAM heatmap (if available)
   - Signal-level forensic findings
   - File metadata and SHA-256 hash

**Key point to emphasize:**

> "Notice how the system doesn't just say 'fake' — it shows *which signals* support that conclusion and what the confidence level is."

---

## Part 3 — Analyze an Authentic Image (2 min)

1. Upload a **real photograph**
2. Show result: AUTHENTIC verdict with supporting evidence
3. Point out the difference in signal patterns between AI and authentic

**Key point:**

> "The system analyzes the same forensic signals and reaches a different conclusion based on the evidence."

---

## Part 4 — Audio Analysis (2 min)

1. Upload a prepared **audio file** (if available)
2. Show the audio-specific analysis:
   - Waveform and spectrogram visualization
   - Signal intelligence metrics
   - Glottal analysis results
   - File container analysis

*(If no audio test file is available, briefly describe the audio pipeline's capabilities without live demo.)*

---

## Part 5 — Forensic Report (2 min)

1. From a completed analysis, click **Generate Report**
2. Show the PDF report:
   - Case reference number
   - File metadata and hash
   - Analysis results
   - Evidence summary
   - Timestamp
   - SHA-256 report hash for integrity
3. Show the report verification feature

**Key point:**

> "The report is SHA-256 hashed. Anyone can verify that the report hasn't been modified since generation."

---

## Part 6 — History & Security (1 min)

1. Show the **History** page — previous analyses for this user
2. Briefly mention:
   - JWT authentication
   - Upload rate limiting
   - Request tracing
   - Production safety enforcement

---

## Part 7 — Conclusion (1 min)

**Say:**

> "To summarize: Deepfake Detective combines neural network detection with signal-level forensics across images, audio, and video. It produces explainable evidence rather than opaque scores, handles uncertainty honestly with the INCONCLUSIVE verdict, and preserves evidence integrity through cryptographic hashing. The system is deployed as a complete web application with authentication, a task queue, and Docker-based deployment."

---

## Fallback Plan

If the backend is unavailable or model loading fails:

- Have **pre-captured screenshots** of each key screen
- Have a **previously generated PDF report** ready to show
- Clearly state: "This is a previously generated real result" if showing cached outputs

## Do NOT Demo

- Admin/system health pages (mention briefly if asked)
- All evaluation benchmarks (summarize in slides instead)
- Docker deployment process (describe in architecture slide)
- Model training process (describe in methodology slide)
