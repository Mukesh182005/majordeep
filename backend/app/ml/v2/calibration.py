import numpy as np

class ProbabilityCalibrator:
    def __init__(self, temperature: float = 1.0):
        self.temperature = temperature

    def fit_temperature(self, logits: np.ndarray, labels: np.ndarray):
        """
        Fits the temperature scaling parameter using NLL (Negative Log Likelihood).
        Since this is a stub for the V2 architecture, it demonstrates the setup.
        In a real scenario, we use L-BFGS to optimize the temperature.
        """
        # Placeholder for actual optimization
        self.temperature = 1.5  # Example calibrated temperature
        return self.temperature

    def calibrate(self, raw_score: float) -> float:
        """
        Applies temperature scaling to a single probability/raw score.
        Assuming raw_score is a probability [0, 1], we convert to logit, 
        scale it, and convert back.
        """
        # Prevent math domain errors
        p = max(min(raw_score, 1.0 - 1e-7), 1e-7)
        logit = np.log(p / (1 - p))
        scaled_logit = logit / self.temperature
        calibrated_prob = 1.0 / (1.0 + np.exp(-scaled_logit))
        return float(calibrated_prob)

    def compute_ece(self, preds: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
        """
        Computes the Expected Calibration Error (ECE).
        """
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        bin_lowers = bin_boundaries[:-1]
        bin_uppers = bin_boundaries[1:]
        
        ece = 0.0
        for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
            in_bin = (preds > bin_lower) & (preds <= bin_upper)
            prop_in_bin = float(np.mean(in_bin))
            if prop_in_bin > 0:
                accuracy_in_bin = np.mean(labels[in_bin])
                avg_confidence_in_bin = np.mean(preds[in_bin])
                ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin
                
        return float(ece)
