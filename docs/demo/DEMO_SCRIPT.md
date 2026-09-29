# Demo Script

## Before Starting

- [ ] Backend running: `http://localhost:8000/docs` loads
- [ ] Frontend running: `http://localhost:3000` loads
- [ ] Test images ready: one AI-generated, one authentic photo
- [ ] Audio test file ready (optional)
- [ ] Browser console open (minimized) to verify no errors
- [ ] Logged in or ready to register

---

## Script

### Opening (30 seconds)

"Good morning/afternoon. Today I'll demonstrate Deepfake Detective, a multi-modal forensic analysis platform we built to detect AI-generated and manipulated media."

"The platform analyzes images, audio, and video using deep neural networks combined with signal-level forensic analysis, and produces explainable, evidence-backed forensic reports."

---

### Navigate to Upload (30 seconds)

*Click "Analyse" in the navigation*

"This is our analysis interface. Users can upload images, audio files, or video for forensic examination. The system supports common formats and validates uploads before processing."

---

### Upload AI-Generated Image (1 minute)

*Drag or select the AI-generated test image*

"I'm uploading an AI-generated image. Watch the upload progress — the file is being SHA-256 hashed for evidence integrity."

*Wait for upload to complete and job to start*

"The analysis job is now queued. We're connected via WebSocket for real-time status updates — you can see the pipeline stages as they execute."

---

### Show Analysis Result (2 minutes)

*Result page loads*

"Here's the result. The system has classified this image as MANIPULATED with [X]% probability."

"But the important part is not just the verdict — it's the evidence. Let me walk through what the system found:"

*Point to each section:*

- "The neural network's confidence score"
- "The Grad-CAM heatmap showing which regions triggered the detection" *(if visible)*
- "The Error Level Analysis results"
- "The PRNU sensor noise analysis — notice how AI images lack the camera sensor fingerprint"
- "The file metadata — you can see the SHA-256 hash, file format, and other properties"

"Every finding is a separate forensic signal. The evidence fusion engine combines these signals using calibrated probability weighting to produce the final assessment."

---

### Upload Authentic Image (1.5 minutes)

*Upload the real photograph*

"Now let's compare with an authentic photograph."

*Wait for result*

"This one is classified as AUTHENTIC. Notice how the evidence looks different — the signal patterns are consistent with a real camera capture rather than AI generation."

---

### Audio Analysis (1.5 minutes, if available)

*Upload audio file*

"The platform also analyzes audio. The audio pipeline uses an LCNN neural detector supplemented by signal intelligence — over 120 signal descriptors including spectral features, glottal voice quality analysis, and file container forensics."

*Show result if available, or describe briefly if not*

---

### Generate Report (1.5 minutes)

*Click "Generate Report" on one of the completed analyses*

"Any analysis can produce a formal forensic report. Let me generate one."

*Show the PDF*

"The report includes the case reference number, file metadata, SHA-256 hash, analysis results, evidence summary, and a timestamp. The report itself is SHA-256 hashed — this hash is stored server-side so anyone can verify the report hasn't been tampered with after generation."

---

### History (30 seconds)

*Navigate to History*

"All analyses are preserved in the user's history with their results. The system requires authentication for history access."

---

### Closing (1 minute)

"To summarize our key contributions:"

"First, multi-modal detection — images, audio, and video in a single platform."

"Second, explainable evidence — not just a score, but a breakdown of forensic signals supporting the conclusion."

"Third, honest uncertainty handling — when the system isn't confident, it says INCONCLUSIVE rather than guessing."

"Fourth, evidence integrity — cryptographic hashing of all media and reports."

"And fifth, a production-grade architecture — FastAPI, Celery task queue, PostgreSQL, Docker deployment, JWT authentication."

"The system has known limitations which we've documented — no detector is perfect, and we believe acknowledging limitations is part of building trustworthy forensic tools."

"Thank you. I'm happy to take questions."
