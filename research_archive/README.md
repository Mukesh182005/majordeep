# Research Archive — Historical Validation & Phase Artifacts

This directory contains historical development scripts, validation reports, evaluation datasets, and phase-specific artifacts generated during the iterative engineering of the Deepfake Detective platform (Phases 17 through 30).

---

## 1. Directory Structure

```
research_archive/
├── artifacts/     # Historical phase artifacts and intermediate validation outputs
│   ├── phase17_9/ # Hard-negative image detection validation
│   ├── phase18/   # Image generalization & benchmark outputs
│   ├── phase19/   # Audio forensics & LCNN validation
│   ├── phase20/   # Video deepfake & temporal consistency validation
│   ├── phase21/   # Multimodal correlation outputs
│   ├── phase22/   # Media genealogy & provenance graphs
│   ├── phase23/   # AI-assisted investigation test outputs
│   ├── phase24/   # Cross-case intelligence artifacts
│   ├── phase25/   # Investigation orchestration test runs
│   ├── phase26/   # Security validation & red-teaming outputs
│   ├── phase27/   # Large-scale external benchmark runs
│   ├── phase28/   # Productionization & load stress test reports
│   ├── phase29/   # Code hygiene & dead-code audit logs
│   ├── phase29_5/ # Repository reorganization records
│   └── phase30/   # Complete frontend & backend integration test suites
│
├── reports/       # Pre-release evaluation metrics and empirical test summaries
│   ├── eval_results.json
│   ├── real_empirical_validation_report.json
│   ├── robustness_report.*
│   ├── threshold_optimization.json
│   └── validation_audit_report.*
│
├── scripts/       # Historical phase execution runners (run_phase*.py)
│
└── galleries/     # Historical test galleries and holdout inspection samples
```

---

## 2. Scientific Reproducibility

These files are preserved to ensure that all empirical claims, ablation studies, and security red-teaming evaluations conducted during the system's development can be independently traced, audited, and reproduced.

None of the files in this directory are required for active production runtime or live user operations. Production runtime components are located strictly within `backend/` and `frontend/`.
