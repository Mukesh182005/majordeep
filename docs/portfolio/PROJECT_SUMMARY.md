# Project Summary

## One-Line

Multi-modal forensic platform that detects AI-generated/manipulated images, audio, and video using neural networks + signal-level forensics, producing explainable, integrity-hashed forensic reports.

## Three-Line

Built a full-stack multi-modal forensic analysis platform for deepfake detection across images, audio, and video. Combined EfficientNet-B4 and LCNN neural classifiers with classical forensic techniques (ELA, PRNU, Grad-CAM, glottal analysis, optical flow) and calibrated evidence fusion with uncertainty handling. Implemented as a production web application with React frontend, FastAPI backend, Celery task queue, JWT auth, Docker deployment, and SHA-256 evidence integrity.

## Short Paragraph

Designed and implemented Deepfake Detective, a multi-modal forensic media analysis platform that detects AI-generated and manipulated content across images, audio, and video. The system combines deep neural network inference (EfficientNet-B4, LCNN) with signal-level forensic analysis (Error Level Analysis, PRNU sensor noise, Grad-CAM attention mapping, glottal voice quality, ENF forensics, optical flow) to produce structured, explainable evidence rather than opaque confidence scores. Built as a full-stack production application with React/Vite frontend, FastAPI/Python backend, Celery/Redis task queue, PostgreSQL database, JWT authentication, and Docker Compose deployment. Key design principles include calibrated uncertainty handling (explicit INCONCLUSIVE verdict), cryptographic evidence integrity (SHA-256 hashing of all uploads and reports), and honest limitation documentation.

## Resume Bullet Points

- Developed a multi-modal forensic deepfake detection platform analyzing images (EfficientNet-B4 + ELA/PRNU/Grad-CAM), audio (LCNN + signal intelligence/glottal analysis), and video (temporal + optical flow analysis) with calibrated evidence fusion
- Built full-stack web application: React 18/Vite frontend with real-time WebSocket updates, FastAPI backend, Celery/Redis async task queue, SQLAlchemy/PostgreSQL, JWT authentication, Docker Compose deployment
- Implemented evidence-oriented forensic architecture with SHA-256 integrity hashing, structured evidence generation, uncertainty handling (INCONCLUSIVE verdict), and timestamped PDF forensic reports
- Designed signal-level forensic analyzers: Error Level Analysis, PRNU sensor noise, Grad-CAM attention maps, glottal voice quality (IAIF), ENF grid forensics, optical flow anomaly detection, file container DNA analysis

## LinkedIn Description

Deepfake Detective — Multi-Modal Forensic Media Intelligence Platform

Built a complete forensic analysis platform that detects AI-generated and manipulated media across images, audio, and video. The system combines deep learning classifiers with classical forensic signal analysis to produce structured, explainable evidence and integrity-hashed PDF reports.

Key technical contributions:
• Multi-modal detection: EfficientNet-B4 (image), LCNN (audio), frame-aggregated (video)
• Signal-level forensics: ELA, PRNU, Grad-CAM, glottal analysis, ENF, optical flow
• Evidence fusion with calibrated probability and explicit uncertainty handling
• Full-stack: React, FastAPI, Celery, PostgreSQL, Docker, JWT auth
• Forensic integrity: SHA-256 hashing, audit trails, production security

Tech: Python, PyTorch, FastAPI, React, PostgreSQL, Redis, Docker
