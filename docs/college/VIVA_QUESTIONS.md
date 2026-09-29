# Viva Questions & Answers

## Core Project Questions

### Why this project?

AI-generated deepfakes are becoming increasingly realistic and accessible. Existing detection tools typically analyze only one modality (usually images), provide opaque single-score predictions without explaining their reasoning, and force every input into binary "real" or "fake" classification. We built a multi-modal platform that combines neural detection with signal-level forensics and produces explainable, evidence-backed assessments with honest uncertainty handling.

### What problem does it solve?

It helps determine whether digital media (images, audio, video) may be AI-generated or manipulated, by providing structured forensic evidence rather than just a confidence score. It also generates integrity-hashed PDF reports for documentation.

### What is a deepfake?

A deepfake is synthetic media created using AI/ML techniques — typically involving face-swapping in video using autoencoders, generating realistic images using GANs or diffusion models, or cloning voices using text-to-speech systems. The term originally referred to face-swap videos but now broadly covers any AI-generated media designed to appear authentic.

---

## Image Detection

### How does image detection work?

We use a fine-tuned EfficientNet-B4 convolutional neural network. The model was trained on a dataset of real photographs and AI-generated images (from GANs, diffusion models, face swaps, etc.). During inference, the model outputs a probability that the image is AI-generated. This is supplemented by signal-level forensic analysis: Error Level Analysis (ELA), PRNU sensor noise analysis, Grad-CAM attention visualization, edge tampering detection, and steganography checks.

### Why EfficientNet-B4?

EfficientNet uses compound scaling (depth, width, resolution) to achieve high accuracy with fewer parameters than alternatives like ResNet. B4 provides a good balance between accuracy and inference speed. We also support B0 as a lightweight alternative.

### What is ELA (Error Level Analysis)?

ELA re-saves the image at a known JPEG quality level and computes the pixel-level difference between the original and re-saved version. In an unmodified image, the error levels are relatively uniform. In a manipulated image, edited regions may show different error levels because they were compressed at different quality levels.

### What is PRNU?

Photo Response Non-Uniformity is a sensor-specific noise pattern unique to each camera sensor. Real photographs contain this pattern; AI-generated images typically do not because they were never captured by a physical sensor. We extract and analyze this noise fingerprint as a forensic signal.

### What is Grad-CAM?

Gradient-weighted Class Activation Mapping highlights which spatial regions of the image most influenced the neural network's classification decision. This helps explain *where* the model sees evidence of manipulation, rather than just providing a single score.

---

## Audio Detection

### How does audio detection work?

We use an LCNN (Light Convolutional Neural Network) trained on real and synthetic speech. The neural prediction is supplemented by 120+ signal descriptors (MFCCs, spectral features, zero-crossing rate, RMS energy), glottal voice quality analysis using IAIF (Iterative Adaptive Inverse Filtering), ENF (Electrical Network Frequency) forensics, and file container DNA analysis.

### What is glottal analysis?

IAIF estimates the glottal excitation signal — the airflow pattern produced by vocal fold vibration. Real human speech has characteristic aerodynamic properties. AI-generated voices may violate these physical constraints because they generate speech mathematically rather than through physical vocal production.

### What is ENF forensics?

Electrical Network Frequency (50 Hz in India/Europe, 60 Hz in the US) from the power grid is often embedded as a faint hum in audio recordings. ENF varies slightly over time. If an audio recording has been spliced, the ENF phase may show discontinuities at the splice point.

---

## Video Detection

### How does video detection work?

Videos are sampled at a configurable frame rate (default: 1 FPS). Each extracted frame undergoes the image forensic pipeline. Additional temporal analysis includes optical flow anomaly detection, face bounding-box jitter measurement, lip-sync consistency analysis, compression DNA inspection, and audio-video cross-modal correlation.

### What is optical flow?

Optical flow measures the apparent motion of objects between consecutive frames. Natural video has smooth, physically plausible motion. Deepfake manipulation (particularly face swaps) can introduce unnatural motion patterns, especially at blending boundaries.

---

## Architecture & Design

### Why multi-modal?

Deepfakes can be images, audio, or video. A system that only analyzes images cannot detect voice clones or video deepfakes. Multi-modal analysis is necessary to cover the full scope of synthetic media threats.

### What is evidence fusion?

Evidence fusion combines multiple independent forensic signals into a single calibrated probability. Rather than relying on a single neural network's output, we weight the neural prediction alongside signal-level forensic measurements (ELA, PRNU, spectral analysis, etc.) to produce a more robust assessment.

### What is calibration?

Model calibration ensures that the reported probabilities are reliable. A well-calibrated model that reports 80% confidence should be correct approximately 80% of the time. We use Platt scaling on validation data to adjust raw model outputs to calibrated probabilities.

### What is OOD detection?

Out-of-Distribution detection flags inputs that are statistically dissimilar to the training data. If the model receives media from a completely novel AI generator it has never seen, the OOD detector can flag this uncertainty rather than producing an overconfident incorrect prediction.

### What database is used and why?

SQLite for development (zero configuration), PostgreSQL for production (ACID compliance, concurrent writes, scalability). SQLAlchemy ORM provides database-agnostic code with Alembic managing schema migrations.

---

## Security

### How is security handled?

JWT-based authentication with bcrypt password hashing. The application refuses to start in production with default secrets. Upload validation, file size limits, rate limiting, CORS restrictions, security headers, and request ID tracing are all implemented.

### How is evidence integrity preserved?

Every uploaded file is SHA-256 hashed at ingestion. Generated PDF reports are also SHA-256 hashed. These hashes are stored in the database and can be independently verified through a dedicated verification endpoint.

---

## Evaluation & Limitations

### What are the limitations?

No detector achieves 100% accuracy. Heavy compression, social media processing, metadata stripping, and completely novel AI generators can all reduce detection reliability. The system cannot prove who created media or guarantee the absence of manipulation. See the full LIMITATIONS.md document.

### How was the system evaluated?

Internal evaluation on curated datasets of real photographs and AI-generated images from multiple generators (GANs, diffusion models, face swaps). Robustness testing with compressed, resized, and social-media-processed variants. The evaluation measures accuracy, precision, recall, and calibration quality.

### What happens when the model is wrong?

The model can and will make mistakes. The INCONCLUSIVE verdict is designed to reduce false classification when confidence is low. The evidence breakdown allows a human reviewer to see *why* the model reached its conclusion and make an informed judgment.

### Can you prove who created a deepfake?

No. The system can provide evidence that media may be AI-generated or manipulated, but it cannot attribute creation to a specific individual or tool. Attribution is a fundamentally different and much harder problem.

### What would you improve in future?

- Larger and more diverse training datasets
- Additional model architectures (Vision Transformers, wav2vec)
- Real-time video stream analysis
- Integration with C2PA content provenance standards
- Federated model updates for new AI generators
- Mobile-optimized inference
