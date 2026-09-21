# Deepfake Detective (DFD)

An advanced, multi-modal forensic analysis platform designed for detecting manipulated images, audio, and video content. DFD operates as a "Dual-Core" system (Frontend UI + ML Backend), employing state-of-the-art Deep Neural Networks, signal intelligence, and cybersecurity telemetry to generate comprehensive, mathematically sound forensic evidence.

## 🎨 Design Philosophy: "The Modular Blueprint"

To avoid the "AI-Wrapper" stigma, DFD adopts a **"High-Contrast Laboratory"** aesthetic:
- **Tethered Bento Layouts**: Information is structured in tethered blueprint panels, completely discarding standard floating shadows.
- **Micro-Animations**: Uses `corner-bracket` borders and hover effects to maintain a dynamic, living interface.
- **Log Streams**: Instead of basic loading bars, the UI streams actual terminal-like forensic telemetry to demonstrate "Proof of Work" and technical density.
- **Dual-Core Palette**: 
  - *Deep Obsidian Lab* (Dark Theme): Deep charcoal, electric cyan data signals, and rust/safety orange alerts.
  - *Clinical Ivory* (Light Theme): Stark white surfaces, deep sea blue data signals, and rust orange alerts.

## 🚀 Features & Capabilities

DFD performs an 8-stage modular forensic audit across three major modalities:

### 1. Image Forensics (Pixel Space & Neural Activation)
- **Grad-CAM Attention Mapping**: Highlights specific spatial regions that triggered neural detector responses (ViT ensemble).
- **Error Level Analysis (ELA)**: Exposes differential JPEG compression artifacts to highlight splicing.
- **PRNU Sensor Noise**: Detects missing hardware fingerprints indicative of generative AI.
- **Structural Tampering (Sobel/Canny)**: Edge gradient density analysis.
- **LSB Steganography**: Bit-plane entropy analysis to detect covert payloads.

### 2. Audio Intelligence (Signal & Telemetry Lab)
- **Audio File DNA**: Deep container forensics (RIFF/MP4), trailing data attacks, and inferred transcoding history.
- **Deep Signal Intelligence**: Extracts 120+ descriptors including time-domain (RMS, Zero-crossing) and frequency-domain metrics (MFCC, Spectral Rolloff, Flux).
- **Glottal Physics & Voice Quality**: IAIF aerodynamic tracking to ensure human vocal fold limits are not violated by synthetic AI voices.
- **Grid ENF Forensics**: Detects 50/60 Hz Electrical Network Frequency phase discontinuities for environmental splicing.

### 3. Video Forensics (Temporal & Spatial Fusion)
- **Multi-Track Chrono-Timeline**: Correlated temporal anomalies across visual frame integrity, audio phase, and metadata structure.
- **Optical Flow Motion Anomaly**: Dense optical flow variance to detect localized divergent vectors in deepfake blending seams.
- **Face Box Jitter**: Measures bounding-box acceleration to catch swap-tracker alignment failures.

## 🏗 System Architecture

### Frontend (React + Vite + Tailwind CSS)
- **Real-Time Websocket Updates**: `connectJobWs` streams live forensic pipeline logs.
- **Responsive "Split Loupe"**: A magnifying glass structural slider to reveal Grad-CAM tensors over original media.
- **State Management**: Built with React Hooks and modular UI components (`TabButton`, `ChronoTimeline`, `MetricBadge`).

### Backend (FastAPI + Python + PyTorch)
- **Asynchronous Pipeline**: Uses Celery (or eager execution) for compute-heavy ML tasks.
- **CUDA Acceleration**: Leverages GPU infrastructure for EfficientNet/ViT feature extraction and generation.
- **Modular Micro-Engines**: E.g., `file_dna.py` for cybersecurity, `heatmaps.py` for Grad-CAM generation, `compression_dna.py` for video encoding.

## 💻 Getting Started

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000` to interact with the forensic lab.
