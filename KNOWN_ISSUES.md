# Known Issues

## Active Issues

### 1. `ml_v1` directory is a duplicate of `ml`
- **Location:** `backend/app/ml_v1/`
- **Description:** The `ml_v1` directory contains an identical copy of the production ML pipeline (`backend/app/ml/`). It was preserved during an architecture migration but is not actively imported by the production runtime.
- **Impact:** Repository bloat (~100 KB of duplicate code). No runtime impact.
- **Status:** REQUIRES_REVIEW — needs verification that no test or deployment path imports from `ml_v1` before removal.

### 2. JWT tokens stored in localStorage
- **Description:** Frontend stores JWT tokens in `localStorage`, which is accessible to JavaScript and vulnerable to XSS token theft.
- **Impact:** Low risk for the current use case; documented in the API client code.
- **Recommendation:** For deployments handling sensitive case material, migrate to httpOnly cookies.

### 3. SQLite concurrent write limitations
- **Description:** Development mode uses SQLite, which does not handle concurrent writes well.
- **Impact:** Under concurrent requests, SQLite may return "database is locked" errors.
- **Workaround:** Use PostgreSQL for production or multi-user scenarios.

### 4. Video analysis frame sampling gaps
- **Description:** Videos are sampled at configurable FPS (default: 1.0). Manipulation occurring entirely between sampled frames may be missed.
- **Impact:** Potential false negatives for very short manipulation segments.

### 5. ENF analysis requires mains hum
- **Description:** Audio ENF forensics requires the recording to contain detectable electrical network frequency (50/60 Hz hum). Outdoor recordings or isolated environments may not contain ENF.
- **Impact:** ENF signal is unavailable for some legitimate recordings.

### 6. Phase runner scripts in `backend/scripts/`
- **Description:** The `backend/scripts/` directory contains numerous `run_phase*.py` scripts from development phases 17–30. These are historical development/validation scripts, not production tools.
- **Impact:** Repository clutter. No runtime impact.

### 7. Root-level generated files
- **Description:** Several generated evaluation outputs remain at the repository root: `calibration_curve.png`, `confusion_matrix.png`, `eval_results.json`, `robustness_report.*`, `validation_audit_report.*`, `threshold_optimization.json`.
- **Impact:** Repository clutter. These are historical evaluation artifacts.

### 8. `false_negative_gallery` and `false_positive_gallery` contain dummy files
- **Description:** These directories contain placeholder files (`fn_dummy_1.jpg` with text content "dummy image content"), not actual error analysis images.
- **Impact:** Misleading directory names. No runtime impact.

## Resolved Issues

*(None documented yet)*
