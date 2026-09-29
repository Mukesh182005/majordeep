# Abstract

## Short Version (~150 words)

The proliferation of AI-generated deepfakes poses significant challenges to digital media trust. This project presents Deepfake Detective, a multi-modal forensic analysis platform that detects manipulated and AI-generated images, audio, and video. The system combines deep neural network inference (EfficientNet-B4 for images, LCNN for audio) with signal-level forensic analysis including Error Level Analysis, PRNU sensor noise detection, glottal voice quality assessment, and optical flow anomaly detection. Unlike single-score classifiers, the platform generates structured forensic evidence, produces calibrated probability assessments with explicit uncertainty handling, and creates timestamped, integrity-hashed PDF reports. The system is built as a full-stack web application (React frontend, FastAPI backend, Celery task queue) with JWT authentication, rate limiting, and Docker-based deployment. Experimental evaluation demonstrates the platform's ability to distinguish authentic media from AI-generated and manipulated content across multiple modalities while honestly communicating detection limitations.

## Extended Version (~300 words)

The rapid advancement of generative AI has made it increasingly easy to create convincing synthetic media — from AI-generated photographs and voice clones to deepfake videos. These developments pose serious threats to information integrity, personal privacy, and institutional trust. Existing detection tools often provide opaque binary predictions without supporting evidence, making them difficult to interpret and trust.

This project presents Deepfake Detective, an open-source, multi-modal forensic analysis platform designed to detect manipulated and AI-generated media while providing explainable, evidence-backed assessments. The platform analyzes three media modalities — images, audio, and video — combining deep neural network classifiers with classical signal-processing forensic techniques.

For image analysis, the system employs a fine-tuned EfficientNet-B4 network alongside Error Level Analysis (ELA), Photo Response Non-Uniformity (PRNU) sensor noise analysis, Grad-CAM attention visualization, edge tampering detection, and steganography analysis. Audio analysis uses an LCNN neural detector supplemented by 120+ signal descriptors, glottal voice quality assessment (IAIF), Electrical Network Frequency (ENF) forensics, and file container DNA analysis. Video forensics combines frame-aggregated neural detection with optical flow analysis, face temporal consistency checking, lip-sync forensics, and audio-video cross-modal analysis.

The evidence fusion engine combines signals using calibrated probability estimation with explicit out-of-distribution (OOD) detection. When confidence falls within a configurable uncertainty band, the system reports INCONCLUSIVE rather than forcing a potentially incorrect classification.

The platform is implemented as a production-grade web application with a React frontend, FastAPI backend, Celery/Redis task queue, SQLAlchemy ORM with PostgreSQL support, and Docker Compose deployment. Security features include JWT authentication, bcrypt password hashing, upload validation, rate limiting, request tracing, and cryptographic report integrity verification.

The system is designed around forensic principles: every finding is supported by technical evidence, every uploaded file is SHA-256 hashed, and the platform explicitly documents its limitations rather than overclaiming detection capability.
