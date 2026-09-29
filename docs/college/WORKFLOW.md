# System Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│  Upload media  →  View progress  →  Inspect results  →  Report │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │   API GATEWAY    │
                    │   (FastAPI)      │
                    │   Auth + Upload  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │        JOB SUBMISSION        │
              │  Validate → Hash → Store →   │
              │  Queue (Celery/Redis or      │
              │  inline eager execution)     │
              └──────────────┬──────────────┘
                             │
              ┌──────────────┴──────────────┐
              │      MEDIA TYPE ROUTING      │
              │  Image? → Image Pipeline     │
              │  Audio? → Audio Pipeline     │
              │  Video? → Video Pipeline     │
              └──────────────┬──────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    IMAGE PIPELINE     AUDIO PIPELINE      VIDEO PIPELINE
    ─────────────      ──────────────      ──────────────
    • Face detection   • Signal metrics    • Frame extraction
    • Neural inference • MFCC/spectral     • Per-frame neural
    • ELA analysis     • Glottal analysis    inference
    • PRNU analysis    • ENF forensics     • Optical flow
    • Grad-CAM maps    • File container    • Face tracking
    • Steganography      DNA               • Compression DNA
    • Edge tampering   • Neural inference  • AV sync
    • Metadata           (LCNN)            • Container forensics
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │      EVIDENCE FUSION         │
              │  Calibrated probability      │
              │  Multi-signal weighting      │
              │  OOD detection               │
              │  Uncertainty estimation      │
              └──────────────┬──────────────┘
                             │
              ┌──────────────┴──────────────┐
              │         VERDICT              │
              │  AUTHENTIC                   │
              │  MANIPULATED                 │
              │  INCONCLUSIVE                │
              └──────────────┬──────────────┘
                             │
              ┌──────────────┴──────────────┐
              │      RESULT STORAGE          │
              │  Evidence → JSON column      │
              │  Heatmaps → file storage     │
              │  Verdict → database          │
              └──────────────┬──────────────┘
                             │
              ┌──────────────┴──────────────┐
              │     REPORT GENERATION        │
              │  PDF with evidence           │
              │  SHA-256 integrity hash      │
              │  Timestamp                   │
              │  Case reference              │
              └─────────────────────────────┘
```

## Step-by-Step

1. **Upload:** User uploads an image, audio file, or video through the web interface.

2. **Validation:** The backend validates file type, size, and rate limits. The file is SHA-256 hashed and stored.

3. **Job creation:** An analysis job is created in the database with status `QUEUED`. The frontend receives the job ID and begins polling or connects via WebSocket for real-time updates.

4. **Pipeline execution:** Based on media type, the appropriate forensic pipeline runs:
   - **Image:** Face detection → neural inference → forensic signal analysis → evidence fusion
   - **Audio:** Signal extraction → neural inference → glottal/ENF/container analysis → evidence fusion
   - **Video:** Frame extraction → per-frame analysis → temporal analysis → AV cross-modal → evidence fusion

5. **Evidence fusion:** Multiple forensic signals are combined using calibrated probability weighting. If the result falls within the uncertainty band, the verdict is INCONCLUSIVE.

6. **Result delivery:** The job status updates to `DONE`. The frontend displays the verdict, probability, evidence breakdown, and forensic visualizations.

7. **Report generation:** On request, a timestamped PDF report is generated containing all findings, SHA-256 hashed for integrity verification.
