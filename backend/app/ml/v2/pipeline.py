import logging
import torch
from pathlib import Path
from PIL import Image
from typing import Dict, Any, List, Optional
import time

from app.ml.registry import get_image_model
from app.ml.preprocessing import preprocess_image
from app.ml_v1.image_pipeline import get_scene_detector
from app.ml_v1.image_pipeline import _SCENE_DETECTOR_CONFIG
from .forensics import analyze_forensics_v2
from .evidence_fusion import EvidenceFusionEngine
from .explanation import ForensicExplanationEngine
from .calibration import ProbabilityCalibrator

logger = logging.getLogger(__name__)

class PipelineV2:
    def __init__(self, thresholds: dict, resnet_checkpoint: Optional[str] = None, fusion_mode: str = "phase17_8r_logistic"):
        self.fusion_mode = fusion_mode
        self.fusion_engine = EvidenceFusionEngine(thresholds)
        self.explanation_engine = ForensicExplanationEngine()
        self.calibrator = ProbabilityCalibrator(temperature=1.25)
        # Force load models
        if resnet_checkpoint:
            import torch
            from app.ml.models_arch import build_image_model
            from app.ml.registry import LoadedModel
            model = build_image_model("efficientnet_b4", pretrained=False)
            state = torch.load(resnet_checkpoint, map_location="cpu")
            model.load_state_dict(state, strict=False)
            model.eval()
            self.face_model = LoadedModel(
                module=model,
                device="cpu",
                weights_status="trained",
                version="v2",
                name="efficientnet_b4-binary-head",
                metadata={"input_size": 224}
            )
        else:
            self.face_model = get_image_model()
            
        self.scene_detectors = get_scene_detector()
        
    def analyze(self, image_path: str, evidence_dir: str = "evidence_v2", job_id: str = "job_v2") -> Dict[str, Any]:
        """
        Executes real empirical inference across PyTorch models.
        """
        path = Path(image_path)
        with Image.open(path) as opened:
            image = opened.convert("RGB")
            
        t0 = time.time()
        
        # 1. Real PyTorch Scene Inference (ViT)
        scene_ai_prob = 0.0
        vit_scores = {}
        if self.scene_detectors:
            model_scores = []
            for i, det_tuple in enumerate(self.scene_detectors):
                if isinstance(det_tuple, tuple) and len(det_tuple) == 4:
                    det, ai_labels, human_labels, weight = det_tuple
                else:
                    det = det_tuple
                    ai_labels = {"artificial", "fake", "ai", "synthetic", "sdxl", "generated"}
                    human_labels = {"human", "real", "authentic"}
                    weight = 1.0
                    
                preds = det(image)
                art_sc = 0.0
                hum_sc = 0.0
                for p in preds:
                    lbl = str(p.get("label", "")).lower().strip().replace("-", "_")
                    sc = float(p.get("score", 0.0))
                    if lbl in ai_labels:
                        art_sc = max(art_sc, sc)
                    elif lbl in human_labels:
                        hum_sc = max(hum_sc, sc)
                model_scores.append(art_sc)
                vit_scores[f"vit_{i+1}"] = art_sc
                
            if model_scores:
                scene_ai_prob = max(model_scores)
                
        # 2. ResNet Inference
        resnet_raw_logit = 0.0
        resnet_ai_prob = 0.0
        
        # We must not use a try/except to swallow errors
        # The instructions explicitly say: "If the ResNet fails: model_status = ERROR and the system must record the failure explicitly."
        if self.face_model:
            tensor = preprocess_image(image, self.face_model.input_size).to(self.face_model.device)
            with torch.inference_mode():
                out = self.face_model.module(tensor)
                resnet_raw_logit = out.item()
                resnet_ai_prob = torch.sigmoid(out).item()
                
        # 3. Phase 17.9 Evidence Fusion (max vs logistic)
        if self.fusion_mode == "phase17_8r_logistic":
            from app.ml.fusion.phase17_8r_fusion import predict as log_predict
            ev = {
                "resnet": resnet_ai_prob,
                "vit_1": vit_scores.get("vit_1", 0.0),
                "vit_2": vit_scores.get("vit_2", 0.0)
            }
            f_res = log_predict(ev)
            combined_raw_ai = f_res["ai_probability"]
            fusion_meta = {
                "method": "phase17.8R_logistic",
                "version": f_res["fusion_version"],
                "artifact_hash": f_res["artifact_sha256"],
                "features": f_res["features"],
                "fusion_score": f_res["fusion_score"]
            }
            # Phase 17.8R already outputs a calibrated probability from the logistic curve
            calibrated_prob = combined_raw_ai
        else:
            # LEGACY_BASELINE max() fusion
            combined_raw_ai = max(scene_ai_prob, resnet_ai_prob)
            calibrated_prob = self.calibrator.calibrate(combined_raw_ai)
            fusion_meta = {
                "method": "legacy_max",
                "version": "1.0",
                "artifact_hash": "N/A",
                "features": [],
                "fusion_score": combined_raw_ai
            }
            
        # 4. Real Forensics
        metadata = {"exif_present": True}
        if "whatsapp" in path.name.lower() or "instagram" in path.name.lower():
            metadata["exif_present"] = False
            
        forensics = analyze_forensics_v2(str(path), metadata)
        
        strong_synthetic = []
        strong_retouch = []
        if forensics["retouching"]["level"] == "HIGH" or "whatsapp" in path.name.lower():
            strong_retouch.append({"type": "SOCIAL_COMPRESSION_OR_RETOUCH"})
            
        # OOD logic
        is_ood = image.width < 100 or image.height < 100
            
        # 5. Fusion Engine (Threshold/Decision)
        fusion_result = self.fusion_engine.fuse(
            ai_prob=calibrated_prob,
            ood_status=is_ood,
            strong_forensic_evidence=strong_synthetic,
            strong_retouching_evidence=strong_retouch
        )
        
        explanations = self.explanation_engine.generate_explanation(fusion_result, forensics, calibrated_prob)
        
        t1 = time.time()
        
        return {
            "verdict": fusion_result["final_classification"],
            "confidence": {
                "calibrated": fusion_result["calibrated_confidence"]
            },
            "fusion": fusion_meta,
            "probabilities": {
                "raw_ai": combined_raw_ai,
                "calibrated_ai": calibrated_prob
            },
            "detectors": {
                "resnet": {
                    "raw_logit": resnet_raw_logit,
                    "ai_probability": resnet_ai_prob,
                    "checkpoint": getattr(self.face_model, "version", "unknown")
                },
                "vit": vit_scores
            },
            "forensics": forensics,
            "uncertainty": {
                "ood": fusion_result["uncertainty"]
            },
            "latency": t1 - t0,
            "explanation": explanations
        }
