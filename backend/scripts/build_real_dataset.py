import os
import shutil
import random
from pathlib import Path
import glob

random.seed(42)

def build_dataset():
    src_base = Path("C:/Users/STUDENT/Desktop/deepfake/deepfake/data/raw/massive_social")
    dst_base = Path("C:/Users/STUDENT/Desktop/deepfake/deepfake/accuracy_test")
    
    # We will sample 20 images per category for a quick empirical run
    num_samples = 20
    
    mapping = {
        "instagram_real": dst_base / "100_real",
        "facebook_real": dst_base / "100_real_edited",
        "snapchat_real": dst_base / "100_real_whatsapp",
        "instagram_fake": dst_base / "100_ai_processed",
        "diffusion_fake": dst_base / "100_ai",
        "inpaint_fake": dst_base / "100_ai"
    }
    
    for src_folder, dst_folder in mapping.items():
        src_path = src_base / src_folder
        if not src_path.exists():
            print(f"Skipping {src_path} (does not exist)")
            continue
            
        dst_folder.mkdir(parents=True, exist_ok=True)
        images = list(src_path.glob("*.jpg")) + list(src_path.glob("*.png"))
        
        if not images:
            print(f"No images in {src_path}")
            continue
            
        sampled = random.sample(images, min(len(images), num_samples))
        for img in sampled:
            shutil.copy2(img, dst_folder / img.name)
            
    print("Dataset built.")

if __name__ == "__main__":
    build_dataset()
