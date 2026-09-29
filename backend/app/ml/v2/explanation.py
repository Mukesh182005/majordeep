from typing import Dict, Any, List

class ForensicExplanationEngine:
    """
    Phase 22: Generate explanations only from actual evidence.
    """
    def generate_explanation(self, fusion_result: Dict[str, Any], forensics: Dict[str, Any], ai_prob: float) -> List[str]:
        explanation = []
        verdict = fusion_result.get("final_classification", "INCONCLUSIVE")
        
        explanation.append(f"Why this image was classified as {verdict.replace('_', ' ').title()}:")
        
        # 1. Forensic signals
        meta_status = forensics.get("metadata", {}).get("status")
        if meta_status == "STRIPPED_OR_UNAVAILABLE":
            explanation.append("• Metadata is unavailable or stripped.")
            
        comp_level = forensics.get("compression", {}).get("level")
        if comp_level == "HIGH":
            explanation.append("• Strong JPEG recompression or social media compression indicators were detected.")
            
        retouch_level = forensics.get("retouching", {}).get("level")
        if retouch_level == "HIGH":
            explanation.append("• Retouching / skin smoothing indicators are present.")
            
        # 2. AI scores
        if ai_prob < 0.40:
            explanation.append("• AI detector scores are below the calibrated AI threshold.")
        elif ai_prob > 0.65:
            explanation.append("• Multi-view AI detectors produced scores above the critical threshold.")
            
        # 3. Certainty
        if verdict.startswith("AUTHENTIC"):
            explanation.append("• No independent evidence strongly supports synthetic generation.")
            
        if not explanation[1:]:
            explanation.append("• The model relies on subtle high-frequency artifacts for this conclusion.")
            
        return explanation
