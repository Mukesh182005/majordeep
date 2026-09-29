import random
from pathlib import Path
from typing import List, Tuple, Dict
from PIL import Image, ImageFilter, ImageEnhance
import torch
from torch.utils.data import Dataset
import torchvision.transforms as T

class HardNegativeTransforms:
    """
    On-the-fly transformations to simulate real-world degradation.
    Ensures the model learns that degradation != AI-generated.
    """
    @staticmethod
    def apply_whatsapp_compression(img: Image.Image) -> Image.Image:
        # WhatsApp usually downscales to ~1600px max side and applies heavy JPEG (Q~60-75)
        # Here we simulate the degradation.
        img.thumbnail((1024, 1024), Image.Resampling.BILINEAR)
        # Simulation: In memory JPEG compression
        import io
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=random.randint(40, 75))
        buffer.seek(0)
        return Image.open(buffer)

    @staticmethod
    def apply_retouching(img: Image.Image) -> Image.Image:
        # Simulate skin smoothing or sharpening
        if random.random() > 0.5:
            return img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.5)))
        else:
            return img.filter(ImageFilter.UnsharpMask(radius=2, percent=150))

    @staticmethod
    def get_random_hard_transform(img: Image.Image) -> Image.Image:
        choice = random.choice(["whatsapp", "retouch", "jpeg_heavy", "none"])
        if choice == "whatsapp":
            return HardNegativeTransforms.apply_whatsapp_compression(img)
        elif choice == "retouch":
            return HardNegativeTransforms.apply_retouching(img)
        elif choice == "jpeg_heavy":
            import io
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=random.randint(20, 50))
            buffer.seek(0)
            return Image.open(buffer)
        return img


class V2HardNegativeDataset(Dataset):
    """
    Dataset that aggressively samples hard negatives for REAL images.
    REAL + WhatsApp, REAL + Instagram, REAL + Photoshop, etc.
    """
    def __init__(self, data_manifest: List[Dict], transform=None, hard_negative_prob: float = 0.5):
        self.data_manifest = data_manifest
        self.transform = transform
        self.hard_negative_prob = hard_negative_prob

    def __len__(self):
        return len(self.data_manifest)

    def __getitem__(self, idx) -> Tuple[torch.Tensor, int]:
        item = self.data_manifest[idx]
        image_path = item["path"]
        label = item["label"]  # 0 for Real, 1 for AI

        try:
            with Image.open(image_path) as img:
                img = img.convert("RGB")
        except Exception:
            # Fallback for corrupted images
            img = Image.new("RGB", (224, 224), (0, 0, 0))

        # Apply hard negative augmentations ONLY to real images to force the model
        # to learn that degraded != fake.
        if label == 0 and random.random() < self.hard_negative_prob:
            img = HardNegativeTransforms.get_random_hard_transform(img)

        if self.transform:
            img = self.transform(img)
        else:
            img = T.ToTensor()(img)

        return img, label
