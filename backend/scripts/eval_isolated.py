import os
import json
import hashlib
import time
from pathlib import Path
import warnings
import argparse

warnings.filterwarnings("ignore")

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))

import torch
from PIL import Image

from app.ml.preprocessing import preprocess_image, IMAGE_SIZE
from app.ml.models_arch import build_image_model
from app.ml.v2.pipeline import PipelineV2
from app.ml import registry

def direct_model_load(ckpt_path):
    model = build_image_model("efficientnet_b4", pretrained=False)
    state = torch.load(ckpt_path, map_location="cpu")
    model.load_state_dict(state, strict=False)
    model.eval()
    return model

def mock_get_image_model(ckpt_path):
    # Completely hijack the registry for PipelineV2
    module = direct_model_load(ckpt_path)
    return registry.LoadedModel(
        module=module,
        device="cpu",
        weights_status="trained",
        version="v2",
        name="efficientnet_b4-binary-head",
        metadata={"input_size": IMAGE_SIZE}
    )

def evaluate(ckpt_path, out_file):
    # Monkeypatch the registry so PipelineV2 uses our explicit model
    registry.get_image_model = lambda: mock_get_image_model(ckpt_path)
    
    v2 = PipelineV2({"BALANCED_MODE": 0.65})
    
    # Load independent dataset
    with open("evaluation/PHASE17.5R/dataset_manifest.json") as f:
        dataset = json.load(f)
        
    results = []
    
    for item in dataset:
        res = v2.analyze(item["path"])
        
        results.append({
            "image_id": item["path"],
            "filename": Path(item["path"]).name,
            "ground_truth": item["label"],
            "category": item["category"],
            "raw_logit": 0.0, # not exposed by PipelineV2 easily, but probability is
            "ai_probability": res["probabilities"]["calibrated_ai"],
            "final_verdict": res["verdict"],
            "retouch_score": 0.0,
            "ood_score": res["uncertainty"]["ood"],
            "latency_ms": res["latency"]
        })
        
    with open(out_file, "w") as f:
        json.dump(results, f, indent=4)
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ckpt", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    evaluate(args.ckpt, args.out)
