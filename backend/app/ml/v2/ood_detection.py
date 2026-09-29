from typing import List, Dict, Any
import numpy as np

def compute_ensemble_disagreement(model_scores: List[float]) -> float:
    """
    Computes disagreement among ensemble models.
    Returns a normalized disagreement score (0.0 to 1.0).
    """
    if not model_scores or len(model_scores) < 2:
        return 0.0
        
    variance = np.var(model_scores)
    # Max possible variance for scores in [0, 1] is 0.25 (e.g. [0, 1])
    normalized_disagreement = float(min(variance * 4.0, 1.0))
    return normalized_disagreement

def check_out_of_distribution(
    image_features: Dict[str, Any], 
    ensemble_scores: List[float], 
    threshold_disagreement: float = 0.8
) -> Dict[str, Any]:
    """
    Determines if the image is out-of-distribution (OOD) making the 
    prediction INCONCLUSIVE.
    """
    disagreement = compute_ensemble_disagreement(ensemble_scores)
    
    # Heuristic based on image resolution or extreme formats
    width, height = image_features.get("resolution", (0, 0))
    is_extreme_resolution = width < 64 or height < 64 or width > 10000 or height > 10000
    
    is_ood = (disagreement > threshold_disagreement) or is_extreme_resolution
    
    return {
        "is_ood": is_ood,
        "ood_reason": "High ensemble disagreement" if disagreement > threshold_disagreement else ("Extreme resolution" if is_extreme_resolution else "None"),
        "disagreement_score": round(disagreement, 3)
    }
