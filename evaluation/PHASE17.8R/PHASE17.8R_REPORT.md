# PHASE 17.8R - FUSION HOLDOUT VERIFICATION
    
## Dataset Audit
- Train: 120
- Validation: 60
- Leakage: None (deterministic offsets)

## Ablation (Validation Set)
| Metric | ViT-Only | ViT+ResNet |
|--------|---------:|-----------:|
| F1     | 0.5263 | 0.7273 |
| FPR    | 40.00% | 16.67% |
| Recall | 50.00% | 66.67% |
| Brier  | 0.2578 | 0.1829 |
| ECE    | 0.0529 | 0.0369 |

## Coefficients
- ResNet (Phase 17): 2.3966
- ViT-1: 0.2826
- ViT-2: 0.2833
- Intercept: -1.1552

## Production Recommendation
Extract the coefficients and build the `FusionLinearHead` for production testing, as the Phase 17 ResNet demonstrably aids validation-set performance.
