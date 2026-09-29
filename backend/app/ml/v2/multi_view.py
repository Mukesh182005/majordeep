from typing import List, Dict, Any
from PIL import Image

def generate_multi_views(image: Image.Image, face_boxes: List[tuple]) -> List[Dict[str, Any]]:
    """
    Generate multiple views for inference:
    1. Full image
    2. Face crops
    3. Center crop
    4. Local tiles (if large enough)
    """
    views = []
    width, height = image.size
    
    # 1. Full Image
    views.append({
        "view_type": "FULL_IMAGE",
        "image": image,
        "box": (0, 0, width, height)
    })
    
    # 2. Face Crops
    for idx, box in enumerate(face_boxes):
        # Extend box slightly for context
        x1, y1, x2, y2 = box
        pad_x = int((x2 - x1) * 0.2)
        pad_y = int((y2 - y1) * 0.2)
        crop_box = (
            max(0, x1 - pad_x),
            max(0, y1 - pad_y),
            min(width, x2 + pad_x),
            min(height, y2 + pad_y)
        )
        views.append({
            "view_type": f"FACE_CROP_{idx}",
            "image": image.crop(crop_box),
            "box": crop_box
        })
        
    # 3. Center Crop
    cx, cy = width // 2, height // 2
    cw, ch = int(width * 0.5), int(height * 0.5)
    center_box = (cx - cw//2, cy - ch//2, cx + cw//2, cy + ch//2)
    views.append({
        "view_type": "CENTER_CROP",
        "image": image.crop(center_box),
        "box": center_box
    })
    
    # 4. Local Tiles (4 quadrants)
    if width >= 512 and height >= 512:
        tiles = [
            (0, 0, cx, cy),          # Top-Left
            (cx, 0, width, cy),      # Top-Right
            (0, cy, cx, height),     # Bottom-Left
            (cx, cy, width, height)  # Bottom-Right
        ]
        for idx, t_box in enumerate(tiles):
            views.append({
                "view_type": f"TILE_{idx+1}",
                "image": image.crop(t_box),
                "box": t_box
            })
            
    return views

def aggregate_multi_view_scores(view_scores: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Robust aggregation. Does not let a single anomalous tile dictate the final verdict.
    """
    if not view_scores:
        return {}
        
    full_image_score = next((v['score'] for v in view_scores if v['view_type'] == 'FULL_IMAGE'), 0.0)
    
    face_scores = [v['score'] for v in view_scores if v['view_type'].startswith('FACE_CROP')]
    avg_face_score = sum(face_scores) / len(face_scores) if face_scores else 0.0
    
    tile_scores = [v['score'] for v in view_scores if v['view_type'].startswith('TILE_')]
    
    # Robust aggregation: e.g., median or trimmed mean instead of max to avoid single-tile anomalies
    sorted_tiles = sorted(tile_scores)
    median_tile_score = sorted_tiles[len(sorted_tiles)//2] if sorted_tiles else full_image_score
    
    return {
        "full_scene_score": full_image_score,
        "face_aggregate_score": avg_face_score,
        "tile_median_score": median_tile_score,
        "raw_views": view_scores
    }
