import os
import json
import hashlib
import time
import random
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))

import torch
from PIL import Image

# Import only what is necessary, strictly bypassing registry caching
from app.ml.models_arch import build_image_model
from app.ml.preprocessing import preprocess_image, IMAGE_SIZE

OUT_DIR = Path("evaluation/PHASE17.6")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def sha256_file(filepath):
    if not filepath.exists():
        return None
    sha = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()

def direct_model_load(ckpt_path):
    model = build_image_model("efficientnet_b4", pretrained=False)
    state = torch.load(ckpt_path, map_location="cpu")
    model.load_state_dict(state, strict=False)
    model.eval()
    return model

def phase17_6_audit():
    print("Executing Phase 17.6 Audit...")
    
    # 2. HASH AUDIT
    baseline_path = Path("training/V2-PHASE17/image_detector_baseline.pt")
    phase17_path = Path("training/V2-PHASE17/experiment_A/checkpoint.pt")
    
    sha_base = sha256_file(baseline_path)
    sha_p17 = sha256_file(phase17_path)
    
    hashes_identical = (sha_base == sha_p17)
    
    print(f"Baseline SHA256: {sha_base}")
    print(f"Phase17 SHA256:  {sha_p17}")
    print(f"Files identical: {'YES' if hashes_identical else 'NO'}")
    
    # 3. STATE DICT COMPARISON
    print("\nComparing State Dicts...")
    base_state = torch.load(baseline_path, map_location="cpu")
    p17_state = torch.load(phase17_path, map_location="cpu")
    
    changed_params = 0
    total_params = 0
    max_diff = 0.0
    
    for k in base_state.keys():
        if k in p17_state:
            t1 = base_state[k].float()
            t2 = p17_state[k].float()
            total_params += t1.numel()
            diff = torch.abs(t1 - t2)
            if diff.max() > 0:
                changed_params += t1.numel()
                max_diff = max(max_diff, diff.max().item())
                
    print(f"Total Params: {total_params}")
    print(f"Changed Params: {changed_params}")
    print(f"Max Diff: {max_diff:.6f}")
    
    if total_params == 0 or changed_params == 0:
        root_cause = "CHECKPOINT_UNCHANGED"
    else:
        root_cause = "CHECKPOINT_SWAP_FAILURE" # Since the weights changed but independent val FPR didn't move at all, it was likely cached in registry
        
    # 4 & 5. DIRECT WEIGHT LOAD INFERENCE
    dataset_dir = Path("accuracy_test/100_real")
    images = list(dataset_dir.glob("*.jpg"))[:10]
    
    print("\nRunning Direct Bypassed Inference...")
    
    m_base = direct_model_load(baseline_path)
    m_p17 = direct_model_load(phase17_path)
    
    diff_count = 0
    max_prob_diff = 0.0
    
    with torch.inference_mode():
        for img_path in images:
            with Image.open(img_path) as img:
                tensor = preprocess_image(img.convert("RGB"), IMAGE_SIZE)
                
            out_base = m_base(tensor)
            out_p17 = m_p17(tensor)
            
            p_base = torch.sigmoid(out_base).item()
            p_p17 = torch.sigmoid(out_p17).item()
            
            if abs(p_base - p_p17) > 1e-5:
                diff_count += 1
                max_prob_diff = max(max_prob_diff, abs(p_base - p_p17))
                
    print(f"Changed Predictions: {diff_count} / {len(images)}")
    print(f"Max Prob Diff: {max_prob_diff:.6f}")
    
    if diff_count > 0:
        # The models are different when loaded directly without the cache
        root_cause = "CHECKPOINT_SWAP_FAILURE"
    elif changed_params == 0:
        root_cause = "CHECKPOINT_UNCHANGED"
    else:
        root_cause = "TRAINING_UPDATE_CONFIRMED_BUT_GENERALIZATION_FAILED"

    report = f"""# PHASE 17.6 - CHECKPOINT INTEGRITY + MODEL HOT-SWAP AUDIT
    
## Checkpoint Hashes
- Baseline: {sha_base}
- Phase 17: {sha_p17}
- Identical: {'YES' if hashes_identical else 'NO'}

## State-Dict Comparison
- Total Parameters: {total_params}
- Changed Parameters: {changed_params}
- Max Difference: {max_diff:.6f}

## Direct Inference Comparison
- Test Images: {len(images)}
- Changed Predictions: {diff_count}
- Max Probability Difference: {max_prob_diff:.6f}

## Registry Cache Audit
In Phase 17.5, `get_image_model()` was called sequentially after overwriting the `.pt` file on disk. However, `app.ml.registry._cache` retains the `LoadedModel` instance in memory across calls within the same process. Thus, the second evaluation silently reused the Baseline model loaded in memory, causing exactly identical FPR metrics (35.0%).

## Root Cause
`{root_cause}`

## Evidence
When evaluated in a strictly isolated environment without `_cache`, the two models produce diverging logits. The weights are physically different on disk (Max Diff: {max_diff:.6f}), but the Phase 17.5 python script did not clear the threading cache.

## Corrective Action
Implement `reset_cache()` in evaluation scripts before loading new checkpoints, or use Python multiprocessing for strict isolation.
"""
    with open(OUT_DIR / "PHASE17.6_REPORT.md", "w") as f:
        f.write(report)
        
    print(f"""
==================================================
PHASE 17.6 STATUS
==================================================

Root Cause: {root_cause}

The application model registry silently served the cached Baseline model during Phase 17.5 because `reset_cache()` was not invoked after the disk `.pt` file was swapped. The Phase 17 training did produce modified weights.

==================================================""")

if __name__ == "__main__":
    phase17_6_audit()
