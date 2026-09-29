# PHASE 17.8 - CALIBRATED EVIDENCE FUSION
    
## 4. Individual Detector Calibration
- ResNet (Phase 17): Brier 0.281, ECE 0.290
- ViT-1: Brier 0.329, ECE 0.302
- ViT-2: Brier 0.476, ECE 0.481

## 6. Fusion Methods
- max() accuracy: 51.7%
- Mean weighted accuracy: 60.8%
- Logistic Regression fusion accuracy: 69.2%

## 11. Ablation
- Logistic Regression (ViT Only): 55.0%
- Logistic Regression (ViT + ResNet): 69.2%

By fitting a logistic regression curve to the raw uncalibrated probabilities, the fusion engine can appropriately weight the ResNet model without it being masked by ViT saturation, establishing the incremental validity of the Phase 17 checkpoint.

## 18. Recommended Next Step
Extract fusion coefficients from the logistic model and implement a lightweight PyTorch `nn.Linear` fusion head, replacing the `max()` baseline in production.
