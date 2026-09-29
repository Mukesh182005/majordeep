# Project Objectives

1. **Multi-modal deepfake detection:** Build a system capable of analyzing images, audio, and video for signs of AI generation or manipulation.

2. **Neural + signal forensic analysis:** Combine deep neural network classifiers (EfficientNet-B4 for images, LCNN for audio) with classical forensic signal analysis (ELA, PRNU, spectral analysis, glottal analysis, optical flow) to produce richer evidence than either approach alone.

3. **Explainable evidence generation:** Produce structured forensic evidence for each analysis — including Grad-CAM attention maps, signal metrics, metadata inspection results, and forensic heatmaps — rather than opaque single-score outputs.

4. **Calibrated uncertainty handling:** Report calibrated probability assessments and explicitly use an INCONCLUSIVE verdict when confidence is insufficient, avoiding forced misclassification.

5. **Evidence integrity:** Cryptographically hash all uploaded media (SHA-256) at ingestion and all generated reports, creating a verifiable chain of evidence integrity.

6. **Forensic reporting:** Generate timestamped PDF forensic reports containing analysis results, supporting evidence, file metadata, and integrity hashes suitable for documentation.

7. **Production web application:** Implement the platform as a deployable full-stack web application with:
   - React frontend with real-time job status via WebSocket
   - FastAPI backend with asynchronous Celery/Redis task queue
   - JWT authentication with bcrypt password hashing
   - PostgreSQL/SQLite database with Alembic migrations
   - Docker Compose deployment configuration

8. **Security and audit:** Implement upload validation, rate limiting, request tracing, security headers, and production-safe configuration enforcement.

9. **Honest limitation documentation:** Explicitly document known limitations, false positive/negative risks, and the boundary between what the system can and cannot determine.
