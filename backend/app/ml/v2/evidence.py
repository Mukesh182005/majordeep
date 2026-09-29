from typing import Dict, Any

class EvidenceEngine:
    def __init__(self):
        self.ai_evidence = []
        self.manipulation_evidence = []
        self.retouching_evidence = []
        self.forensic_evidence = []

    def add_ai_score(self, model_name: str, score: float, calibrated_prob: float):
        self.ai_evidence.append({
            "model": model_name,
            "raw_score": score,
            "calibrated_prob": calibrated_prob
        })

    def add_manipulation_signal(self, signal_type: str, confidence: str):
        self.manipulation_evidence.append({
            "type": signal_type,
            "confidence": confidence
        })
        
    def add_retouching_signal(self, indicator: str):
        self.retouching_evidence.append({
            "indicator": indicator
        })
        
    def add_forensic_observation(self, observation: Dict[str, Any]):
        self.forensic_evidence.append(observation)

    def summarize(self) -> Dict[str, Any]:
        """
        Keeps deterministic observations separate from probabilistic predictions.
        """
        return {
            "ai_generation": {
                "evidence": self.ai_evidence,
                "summary": "AI probabilities from generative models"
            },
            "traditional_manipulation": {
                "evidence": self.manipulation_evidence,
                "summary": "Evidence of splicing, cloning, or structural manipulation"
            },
            "digital_retouching": {
                "evidence": self.retouching_evidence,
                "summary": "Evidence of software-based color grading, smoothing, or enhancement"
            },
            "forensics": {
                "evidence": self.forensic_evidence,
                "summary": "Compression, metadata, and sensor characteristics"
            }
        }
