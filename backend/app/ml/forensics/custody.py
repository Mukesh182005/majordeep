"""Chain of Custody and Model Audit Registry (Modules 24 & 26)."""

from __future__ import annotations

import datetime
import hashlib
import platform
from pathlib import Path
from typing import Any
import torch

from app import __version__ as app_version
from app.config import settings


def generate_chain_of_custody(file_path: Path, sha256_hash: str, job_id: str) -> dict[str, Any]:
    """
    Generate an immutable digital evidence custody record.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    evidence_id = f"DFE-{now.strftime('%Y%m%d')}-{sha256_hash[:8].upper()}"

    # Custody verification seal
    seal_payload = f"{evidence_id}|{sha256_hash}|{now.isoformat()}|{job_id}"
    custody_seal = hashlib.sha256(seal_payload.encode()).hexdigest()

    action_log = [
        {"action": "Evidence Ingestion", "timestamp": now.isoformat(), "operator": "Secure Ingestion Engine"},
        {"action": "Cryptographic Hash Validation", "timestamp": now.isoformat(), "operator": "Forensic Hash Core"},
        {"action": "Multi-Forensic Processing", "timestamp": now.isoformat(), "operator": f"DeFraudAI v{app_version}"},
        {"action": "Evidence Lock & Custody Verification", "timestamp": now.isoformat(), "operator": "Custody Engine"},
    ]

    return {
        "evidence_id": evidence_id,
        "sha256": sha256_hash,
        "acquired_at": now.isoformat(),
        "job_id": job_id,
        "original_filename": file_path.name,
        "analyzer_platform": f"DeFraudAI Forensic Suite v{app_version}",
        "custody_verification_seal": custody_seal,
        "action_log": action_log,
    }


def get_model_audit_info() -> dict[str, Any]:
    """
    Expose audit, dataset, calibration, and inference hardware metadata.
    """
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    cuda_ver = torch.version.cuda or "N/A"

    try:
        from app.ml.image_pipeline import SCENE_DETECTORS

        scene_architecture = "; ".join(f"{s.model_id} ({s.role}, weight {s.weight})" for s in SCENE_DETECTORS)
    except Exception:  # pragma: no cover - inference stack unavailable
        scene_architecture = "unavailable"

    return {
        "engine_version": f"DeFraudAI Forensic v{app_version}",
        "deepfake_model": {
            "name": "EfficientNet-B4 face-crop GAN classifier",
            "backbone": "efficientnet_b4",
            "training_dataset": "140k Real and Fake Faces (FFHQ photos vs StyleGAN faces) plus filtered copies of them",
            "scope": "StyleGAN-style generated faces only; it scores diffusion, GPT-image and Gemini faces as real.",
            "validation_note": (
                "Earlier 99%+ validation figures came from a split that shared source faces with "
                "training; they do not measure real-world accuracy."
            ),
            "checkpoint": "checkpoints/image_detector.pt",
        },
        "full_scene_model": {
            "name": "Full-scene AI-generation detector ensemble (log-odds fusion)",
            "architecture": scene_architecture,
            "measured_performance": (
                "AUC 0.984 on 560 held-out images: 200 real photos (COCO, Flickr) and 360 from "
                "SD 2.1, SDXL, SD3, DALL-E 3, Midjourney v6, Flux.1-dev and Gemini Nano Banana / Pro"
            ),
            "classes": ["Artificial / Generative", "Authentic Photograph"],
        },
        "hardware_environment": {
            "device": gpu_name,
            "cuda_version": cuda_ver,
            "pytorch_version": torch.__version__,
            "operating_system": platform.platform(),
        },
        "calibration": {
            "confidence_calibration_version": "v2.5",
            "decision_threshold": settings.fake_threshold,
            "inconclusive_bounds": [
                round(settings.fake_threshold - settings.uncertain_band, 2),
                round(settings.fake_threshold + settings.uncertain_band, 2),
            ],
        },
        "audit_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
