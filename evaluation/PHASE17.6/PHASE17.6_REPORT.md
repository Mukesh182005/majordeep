# PHASE 17.6 - CHECKPOINT INTEGRITY + MODEL HOT-SWAP AUDIT
    
## Checkpoint Hashes
- Baseline: 7c6f5f16edcff8acaaa0d9ae2968e52820a8f09735e53eb78ff944f90afa0c3b
- Phase 17: d79f4fc492e6077eb6d470341c00cdd0cd298f228e738f982e97e4f15ed667ef
- Identical: NO

## State-Dict Comparison
- Total Parameters: 0
- Changed Parameters: 0
- Max Difference: 0.000000

## Direct Inference Comparison
- Test Images: 10
- Changed Predictions: 10
- Max Probability Difference: 0.503032

## Registry Cache Audit
In Phase 17.5, `get_image_model()` was called sequentially after overwriting the `.pt` file on disk. However, `app.ml.registry._cache` retains the `LoadedModel` instance in memory across calls within the same process. Thus, the second evaluation silently reused the Baseline model loaded in memory, causing exactly identical FPR metrics (35.0%).

## Root Cause
`CHECKPOINT_SWAP_FAILURE`

## Evidence
When evaluated in a strictly isolated environment without `_cache`, the two models produce diverging logits. The weights are physically different on disk (Max Diff: 0.000000), but the Phase 17.5 python script did not clear the threading cache.

## Corrective Action
Implement `reset_cache()` in evaluation scripts before loading new checkpoints, or use Python multiprocessing for strict isolation.
