# Image Authenticity Detection Pipeline V2 Architecture

## Overview
This document outlines the architecture for the V2 transition of the AI image authenticity detection platform, designed to dramatically reduce false positives on genuine but heavily compressed or edited real-world photographs.

## Directory Structure and Repositories
- `backend/app/ml/` - Contains the primary ML components and inference logic.
- `backend/app/ml_v1/` - A frozen backup of the V1 pipeline for A/B testing and regression comparison.
- `evaluation/` - A comprehensive holdout and multi-state test suite to benchmark models against real and synthetic cases (compressed, resized, social media).
- `docs/` - System architecture and forensic signal specifications.
- `backend/scripts/` - Utilities for dataset maintenance (e.g. `audit_dataset.py`).

## Core Components
1. **Preprocessing (V2)** (`app/ml/preprocessing_v2.py`)
   - EXIF orientation normalization -> RGB conversion -> Aspect-ratio preserving resize (replacing the strict square crop).

2. **Image States** (`app/ml/states.py`)
   - Transitioning from a binary REAL vs FAKE logic to multiple distinct states:
     - `AUTHENTIC`
     - `AUTHENTIC_DIGITALLY_RETOUCHED`
     - `TRADITIONALLY_MANIPULATED`
     - `AI_ASSISTED`
     - `AI_GENERATED`
     - `AI_MANIPULATED`
     - `INCONCLUSIVE`

3. **Forensic Analysis Layer** (`app/ml/forensics/`)
   - Separates forensic observations (compression, CFA periodicity, EXIF) from AI generation predictions.
   - Designed to avoid automatically classifying missing metadata or heavy quantization as signs of AI generation.

4. **Multi-Model Ensemble & Decision Engine (Upcoming)**
   - V1 relies heavily on hardcoded risk thresholds (e.g., `0.50` and `0.85`).
   - V2 will implement a Calibrated Evidence Fusion Engine that isolates probabilistic AI indicators from deterministic forensic signals (e.g. "missing EXIF != AI Generated").
