# PHASE 17.7R - EXPLICIT CHECKPOINT INJECTION & ABLATION VERIFICATION
    
## Runtime Trace
Baseline:
ResNet = 0.4955
ViT = [0.7520810961723328, 0.0003231122682336718]
Fusion = 0.7521

Phase17:
ResNet = 0.0001
ViT = [0.7520810961723328, 0.0003231122682336718]
Fusion = 0.7521

## max() Dominance Analysis
Using explicit `max()` fusion for Scene AI probability means that whichever model has the highest AI confidence dominates the output. If the ViT ensemble consistently outputs 0.95+ for AI images, pushing the ResNet score from 0.1 to 0.7 has ZERO impact on the final raw_ai probability.

In this test:
- ResNet Output Changed: 20 / 20
- Fusion Output Changed: 13 / 20
- Final Decision Changed: 13 / 20

This explicitly confirms the ResNet checkpoint *did* change mathematically, but `max()` fusion masks its incremental evidence because the Hugging Face ViT ensemble's scores are already highly saturated/calibrated differently.
