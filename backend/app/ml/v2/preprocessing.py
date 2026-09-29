import numpy as np
from PIL import Image, ImageOps
import torch

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

def preprocess_image_v2(image: Image.Image, size: int):
    """
    V2 Preprocessing:
    1. EXIF orientation normalization
    2. RGB conversion
    3. Aspect-ratio-preserving resize
    4. Padding to size
    """
    # 1. EXIF orientation normalization
    image = ImageOps.exif_transpose(image)
    
    # 2. RGB Conversion
    image = image.convert("RGB")
    
    # 3. Aspect-ratio-preserving resize (contain within size x size)
    image.thumbnail((size, size), Image.Resampling.BILINEAR)
    
    # 4. Padding strategy to achieve exact size x size
    padded_image = Image.new("RGB", (size, size), (0, 0, 0))
    offset = ((size - image.width) // 2, (size - image.height) // 2)
    padded_image.paste(image, offset)

    array = np.asarray(padded_image, dtype=np.float32) / 255.0
    array = (array - IMAGENET_MEAN) / IMAGENET_STD

    tensor = torch.from_numpy(
        array.transpose(2, 0, 1)
    ).unsqueeze(0)

    return tensor.contiguous()
