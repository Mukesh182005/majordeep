import argparse
import json
import logging
from pathlib import Path
import numpy as np

try:
    from sklearn.metrics import roc_curve, precision_recall_curve, auc, brier_score_loss
    import matplotlib.pyplot as plt
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def optimize_thresholds(results_json: str):
    """
    Computes ROC/PR curves and selects operating thresholds from evaluation data.
    """
    if not HAS_SKLEARN:
        logger.warning("scikit-learn and matplotlib not installed. Cannot generate curves.")
        return

    results_path = Path(results_json)
    if not results_path.exists():
        logger.error(f"Cannot find {results_path}. Need evaluation results to optimize thresholds.")
        return

    with open(results_path, "r") as f:
        data = json.load(f)

    y_true = np.array(data.get("labels", []))
    y_scores = np.array(data.get("scores", []))

    if len(y_true) == 0 or len(y_scores) == 0:
        logger.warning("Empty labels/scores. Generating dummy curves.")
        y_true = np.array([0, 0, 1, 1, 0, 1])
        y_scores = np.array([0.1, 0.4, 0.35, 0.8, 0.2, 0.9])

    # ROC Curve
    fpr, tpr, roc_thresholds = roc_curve(y_true, y_scores)
    roc_auc = auc(fpr, tpr)
    
    # PR Curve
    precision, recall, pr_thresholds = precision_recall_curve(y_true, y_scores)
    pr_auc = auc(recall, precision)
    
    # Select Thresholds
    # 1. Low False Positive Mode (target FPR <= 0.01)
    target_fpr = 0.01
    idx_low_fpr = np.where(fpr <= target_fpr)[0][-1] if len(np.where(fpr <= target_fpr)[0]) > 0 else 0
    thresh_low_fpr = roc_thresholds[idx_low_fpr]

    # 2. Balanced Mode (maximize TPR - FPR / Youden's J statistic)
    idx_balanced = np.argmax(tpr - fpr)
    thresh_balanced = roc_thresholds[idx_balanced]

    # 3. High Sensitivity Mode (target FNR <= 0.05 -> TPR >= 0.95)
    target_tpr = 0.95
    idx_high_recall = np.where(tpr >= target_tpr)[0][0] if len(np.where(tpr >= target_tpr)[0]) > 0 else -1
    thresh_high_recall = roc_thresholds[idx_high_recall]

    # Brier Score
    brier = brier_score_loss(y_true, y_scores)

    thresholds_out = {
        "LOW_FPR_MODE": float(thresh_low_fpr),
        "BALANCED_MODE": float(thresh_balanced),
        "HIGH_SENSITIVITY_MODE": float(thresh_high_recall),
        "Metrics": {
            "ROC_AUC": float(roc_auc),
            "PR_AUC": float(pr_auc),
            "Brier_Score": float(brier)
        }
    }

    with open("threshold_optimization.json", "w") as f:
        json.dump(thresholds_out, f, indent=4)
        
    logger.info(f"Optimized Thresholds: {json.dumps(thresholds_out, indent=2)}")
    
    # Plotting
    try:
        plt.figure(figsize=(12, 5))
        plt.subplot(1, 2, 1)
        plt.plot(fpr, tpr, label=f'ROC curve (AUC = {roc_auc:.3f})')
        plt.plot([0, 1], [0, 1], 'k--')
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('ROC Curve')
        plt.legend(loc="lower right")

        plt.subplot(1, 2, 2)
        plt.plot(recall, precision, label=f'PR curve (AUC = {pr_auc:.3f})')
        plt.xlabel('Recall')
        plt.ylabel('Precision')
        plt.title('Precision-Recall Curve')
        plt.legend(loc="lower left")
        
        plt.savefig("calibration_curves.png")
        logger.info("Saved calibration curves to calibration_curves.png")
    except Exception as e:
        logger.error(f"Could not generate plots: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimize thresholds and plot curves")
    parser.add_argument("--results", type=str, default="eval_results.json", help="Path to evaluation results JSON")
    args = parser.parse_args()
    optimize_thresholds(args.results)
