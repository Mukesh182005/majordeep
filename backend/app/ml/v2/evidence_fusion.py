from typing import Dict, Any

class EvidenceFusionEngine:
    def __init__(self, thresholds: dict):
        self.ai_threshold = thresholds.get("BALANCED_MODE", 0.65)
        self.real_threshold = 0.35  # Threshold below which we are confident it's real

    def fuse(self, ai_prob: float, ood_status: bool, strong_forensic_evidence: list, strong_retouching_evidence: list) -> Dict[str, Any]:
        """
        Implements the final decision engine conceptualized in Phase 19.
        Does not rely on single hardcoded threshold values.
        """
        verdict = "INCONCLUSIVE"
        confidence = 0.5
        
        # 1. Check Out of Distribution first
        if ood_status:
            verdict = "INCONCLUSIVE"
            confidence = 0.0
            return self._format_result(verdict, confidence)
            
        has_strong_synthetic = any(ev for ev in strong_forensic_evidence if ev.get("type") == "SYNTHETIC_MATTE" or ev.get("type") == "PROVENANCE")
        has_manipulation = any(ev for ev in strong_forensic_evidence if ev.get("type") == "SPLICING" or ev.get("type") == "COPY_MOVE")
        has_retouching = len(strong_retouching_evidence) > 0
        
        # 2. Strong deterministic provenance / synthesis
        if has_strong_synthetic:
            verdict = "AI_GENERATED"
            confidence = 0.95
        # 3. Structural manipulation
        elif has_manipulation:
            verdict = "TRADITIONALLY_MANIPULATED"
            confidence = 0.90
        # 4. Retouched Authentic (Weak AI probability + strong retouching indicators)
        elif has_retouching and ai_prob < self.ai_threshold:
            verdict = "AUTHENTIC_DIGITALLY_RETOUCHED"
            confidence = 1.0 - ai_prob
        # 5. Model probability threshold
        elif ai_prob >= self.ai_threshold:
            verdict = "AI_GENERATED"
            confidence = ai_prob
        elif ai_prob <= self.real_threshold:
            verdict = "AUTHENTIC"
            confidence = 1.0 - ai_prob
        else:
            verdict = "INCONCLUSIVE"
            confidence = ai_prob if ai_prob > 0.5 else (1.0 - ai_prob)

        return self._format_result(verdict, confidence)
        
    def _format_result(self, verdict: str, confidence: float) -> Dict[str, Any]:
        return {
            "final_classification": verdict,
            "calibrated_confidence": round(confidence, 3),
            "uncertainty": verdict == "INCONCLUSIVE"
        }
