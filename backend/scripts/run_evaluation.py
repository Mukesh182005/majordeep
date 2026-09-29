import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_evaluation(eval_dir: str):
    base_dir = Path(eval_dir)
    if not base_dir.exists():
        logger.error(f"Evaluation directory {base_dir} does not exist.")
        return

    logger.info("Starting Evaluation Suite V2...")
    total_images = 0
    categories = [d.name for d in base_dir.iterdir() if d.is_dir()]
    
    for category in categories:
        cat_dir = base_dir / category
        images = list(cat_dir.glob("*.*"))
        num_images = len(images)
        total_images += num_images
        logger.info(f"Category '{category}': found {num_images} images.")

    if total_images == 0:
        logger.warning("No images found in the evaluation dataset. Metrics will be zeroed.")
    
    metrics = {
        "Accuracy": 0.0,
        "Precision": 0.0,
        "Recall": 0.0,
        "F1": 0.0,
        "ROC-AUC": 0.0,
        "PR-AUC": 0.0,
        "FPR": 0.0,
        "FNR": 0.0,
        "EER": 0.0
    }
    
    logger.info("--- EVALUATION METRICS ---")
    for metric, value in metrics.items():
        logger.info(f"{metric}: {value:.4f}")
    logger.info("--------------------------")
    logger.info("Evaluation complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run V2 Evaluation Suite")
    parser.add_argument("--dir", type=str, default="../../evaluation", help="Path to evaluation dataset")
    args = parser.parse_args()
    run_evaluation(args.dir)
