import argparse
import hashlib
import json
import logging
from pathlib import Path
from collections import defaultdict
from PIL import Image
import imagehash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def hash_image(file_path: Path):
    try:
        with Image.open(file_path) as img:
            phash = str(imagehash.phash(img))
            dhash = str(imagehash.dhash(img))
            whash = str(imagehash.whash(img))
        with open(file_path, "rb") as f:
            sha256 = hashlib.sha256(f.read()).hexdigest()
        return {
            "path": str(file_path),
            "sha256": sha256,
            "phash": phash,
            "dhash": dhash,
            "whash": whash
        }
    except Exception as e:
        logger.error(f"Error hashing {file_path}: {e}")
        return None

def audit_dataset(dataset_dir: str):
    base_dir = Path(dataset_dir)
    if not base_dir.exists():
        logger.error(f"Directory {base_dir} does not exist.")
        return

    sha256_dict = defaultdict(list)
    phash_dict = defaultdict(list)
    
    logger.info(f"Scanning {base_dir} for images...")
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        for file_path in base_dir.rglob(ext):
            result = hash_image(file_path)
            if result:
                sha256_dict[result["sha256"]].append(result["path"])
                phash_dict[result["phash"]].append(result["path"])

    duplicates = {
        "exact_duplicates": {k: v for k, v in sha256_dict.items() if len(v) > 1},
        "perceptual_duplicates": {k: v for k, v in phash_dict.items() if len(v) > 1}
    }

    report_json = "dataset_audit_report.json"
    with open(report_json, "w") as f:
        json.dump(duplicates, f, indent=2)
    logger.info(f"Saved dataset audit report to {report_json}")

    report_html = "dataset_audit_report.html"
    with open(report_html, "w") as f:
        f.write("<html><body><h1>Dataset Audit Report</h1><pre>")
        f.write(json.dumps(duplicates, indent=2))
        f.write("</pre></body></html>")
    logger.info(f"Saved HTML report to {report_html}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit dataset for leakage and duplicates")
    parser.add_argument("--dir", type=str, required=True, help="Path to dataset directory")
    args = parser.parse_args()
    audit_dataset(args.dir)
