# DIAGNOSTIC_REPORT
    
## 1. Executive Summary
Initial empirical diagnostic benchmark executed on 120 images.
- Clean Real FPR: 40.0% [MEASURED]
- AI Recall: 48.3% [MEASURED]
- Retouch Recall: 0.0% [MEASURED]

## 6. False-Positive Analysis
- Primary characteristic: Missing metadata and social media footprint trigger the raw ViT model to output 1.0 AI probability. [MEASURED]
- Cause: The ViT models learned compression as a feature of AI generation. [HYPOTHESIS]

## 8. Retouching Failure Analysis
- Mechanism: The raw `scene_ai_prob` outputs extreme confidence (0.95+) on compressed images, which overrides the Retouching state in the fusion engine (which expects AI scores to be lower for retouching). [MEASURED]

## 11. Transformation Analysis
- JPEG 60 transformation increased calibrated AI probability on genuine images by an average of 45%. [MEASURED]

## 18. Recommended Hard-Negative Categories
1. Social Media Compressed (WhatsApp/Instagram) genuine photos
2. JPEG Q40-60 genuine photos
3. Resized/Cropped genuine photos

## 19. Limitations
120 images is insufficient for production significance. 

## 20. Next Experimental Steps
Execute Hard-Negative Training (Phase 17) using WhatsApp/JPEG-compressed authentic images to force the ViT/ResNet models to unlearn compression artifacts as generative signals.
