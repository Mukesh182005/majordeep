import os
import json
import time
import numpy as np
from pathlib import Path
import warnings

# Add backend to path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))

warnings.filterwarnings("ignore")

from app.ml_v1.image_pipeline import analyze_image
from app.ml.v2.pipeline import PipelineV2

def evaluate():
    print("Initializing Models (Cold Start)...")
    t_start_load = time.time()
    v2 = PipelineV2({"BALANCED_MODE": 0.65})
    print(f"Models loaded in {time.time() - t_start_load:.2f}s")
    
    dataset_dir = Path("accuracy_test")
    
    # Categories:
    # 100_real (Authentic)
    # 100_real_edited (Retouched)
    # 100_real_whatsapp (Retouched)
    # 100_ai (AI)
    # 100_ai_processed (AI)
    
    results = []
    latencies = []
    
    files = list(dataset_dir.rglob("*.jpg")) + list(dataset_dir.rglob("*.png"))
    print(f"Found {len(files)} test images for Real Empirical Validation.")
    
    for idx, f in enumerate(files):
        folder_name = f.parent.name
        
        if "real" in folder_name and "whatsapp" not in folder_name and "edited" not in folder_name:
            gt_class = "AUTHENTIC"
        elif "real" in folder_name:
            gt_class = "RETOUCHED"
        else:
            gt_class = "AI"
            
        print(f"[{idx+1}/{len(files)}] Evaluating {f.name} (GT: {gt_class})...")
        
        try:
            res_v2 = v2.analyze(str(f))
            
            latencies.append(res_v2["latency"])
            
            results.append({
                "filename": str(f),
                "ground_truth": gt_class,
                "predicted_class": res_v2["verdict"],
                "raw_score": res_v2["probabilities"]["raw_ai"],
                "calibrated_prob": res_v2["probabilities"]["calibrated_ai"],
                "ood_score": res_v2["uncertainty"]["ood"],
                "latency": res_v2["latency"]
            })
        except Exception as e:
            print(f"Failed to analyze {f.name}: {e}")
            
    print("Inference Complete. Calculating Metrics...")
    
    # Calculate metrics
    real_clean_count = sum(1 for r in results if r["ground_truth"] == "AUTHENTIC")
    real_clean_fp = sum(1 for r in results if r["ground_truth"] == "AUTHENTIC" and "AI" in r["predicted_class"])
    clean_real_fpr = real_clean_fp / max(real_clean_count, 1)
    
    genuine_count = sum(1 for r in results if r["ground_truth"] in ["AUTHENTIC", "RETOUCHED"])
    genuine_fp = sum(1 for r in results if r["ground_truth"] in ["AUTHENTIC", "RETOUCHED"] and "AI" in r["predicted_class"])
    all_genuine_fpr = genuine_fp / max(genuine_count, 1)
    
    ai_count = sum(1 for r in results if r["ground_truth"] == "AI")
    ai_tp = sum(1 for r in results if r["ground_truth"] == "AI" and "AI" in r["predicted_class"])
    ai_pred_count = sum(1 for r in results if "AI" in r["predicted_class"])
    
    ai_precision = ai_tp / max(ai_pred_count, 1)
    ai_recall = ai_tp / max(ai_count, 1)
    ai_f1 = (2 * ai_precision * ai_recall) / max((ai_precision + ai_recall), 1e-7)
    
    retouch_count = sum(1 for r in results if r["ground_truth"] == "RETOUCHED")
    retouch_tp = sum(1 for r in results if r["ground_truth"] == "RETOUCHED" and "RETOUCHED" in r["predicted_class"])
    retouch_pred = sum(1 for r in results if "RETOUCHED" in r["predicted_class"])
    
    retouch_precision = retouch_tp / max(retouch_pred, 1)
    retouch_recall = retouch_tp / max(retouch_count, 1)
    retouch_f1 = (2 * retouch_precision * retouch_recall) / max((retouch_precision + retouch_recall), 1e-7)
    
    # Calibration ECE (simplistic)
    preds = np.array([r["calibrated_prob"] for r in results])
    labels = np.array([1 if r["ground_truth"] == "AI" else 0 for r in results])
    brier = float(np.mean((preds - labels)**2)) if len(preds) > 0 else 0
    
    if len(latencies) > 0:
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)
    else:
        p50 = p95 = p99 = 0
        
    report = {
        "clean_real_ai_fpr": clean_real_fpr,
        "all_genuine_ai_fpr": all_genuine_fpr,
        "ai_precision": ai_precision,
        "ai_recall": ai_recall,
        "ai_f1": ai_f1,
        "retouch_precision": retouch_precision,
        "retouch_recall": retouch_recall,
        "retouch_f1": retouch_f1,
        "brier_score": brier,
        "latency_p50": p50,
        "latency_p95": p95,
        "latency_p99": p99,
        "total_images": len(results)
    }
    
    with open("real_empirical_validation_report.json", "w") as f:
        json.dump(report, f, indent=4)
        
    print(json.dumps(report, indent=4))
    print("EMPIRICAL VALIDATION: COMPLETED")

if __name__ == "__main__":
    evaluate()
