from typing import List, Dict, Any, Optional

def assess_face_quality(box: tuple, image_size: tuple) -> float:
    """
    Assess if the face is large enough and of sufficient quality 
    to be reliably scored by the facial manipulation detector.
    Returns a quality score 0.0 - 1.0.
    """
    x1, y1, x2, y2 = box
    face_w, face_h = x2 - x1, y2 - y1
    img_w, img_h = image_size
    
    # Very small faces (e.g. < 64x64) get low quality
    if face_w < 64 or face_h < 64:
        return 0.1
        
    area_ratio = (face_w * face_h) / (img_w * img_h)
    
    # Optimal size is typically 10-40% of the image
    if 0.05 <= area_ratio <= 0.60:
        return 0.9
    elif area_ratio > 0.60:
        return 0.8
    else:
        return 0.5

def route_faces_for_inference(faces: List[Dict[str, Any]], image_size: tuple) -> List[Dict[str, Any]]:
    """
    Only run facial manipulation detection when a valid face is present.
    Filters out very low quality / small faces that cause false positives.
    """
    routed_faces = []
    
    for face_idx, face in enumerate(faces):
        box = face.get("box")
        if not box:
            continue
            
        quality = assess_face_quality(box, image_size)
        
        # Threshold for running inference
        if quality >= 0.5:
            routed_faces.append({
                "face_id": face_idx,
                "bounding_box": box,
                "quality": quality,
                "status": "QUEUED_FOR_INFERENCE"
            })
        else:
            routed_faces.append({
                "face_id": face_idx,
                "bounding_box": box,
                "quality": quality,
                "status": "SKIPPED_LOW_QUALITY"
            })
            
    return routed_faces
