# Backend and ML implementation

## Runtime architecture

The backend remains a FastAPI modular monolith over PostgreSQL 16/PostGIS 3.4. Existing lake workflows and bigint IDs remain operational. Statewide identity uses `public_assets.id` (UUID), joined to legacy lake assets through `public_assets.legacy_asset_id`. The worker continues to deliver transactional outbox events with leases, bounded retries and dead-letter state.

## ML boundary

The current production-safe default is the transparent `baseline-1.0.0` review-priority scorer. It is deterministic and owner-blind. It is not a trained model and its score is not a probability of encroachment. Candidate ingestion stores the feature snapshot, model/version, factors and disclaimer in `candidate_predictions`.

The optional training package adds a scikit-learn Random Forest experiment for *physical-change review priority*. Training requires independently field-verified binary labels and a CSV with exactly these columns:

`asset_id,label,area_sq_m,area_growth,persistence_count,observation_gap_days,sensor_agreement,boundary_quality,stage_preventability`

Label 1 means physical change confirmed by independent field verification; label 0 means no physical change on verification. Owner/claimant identifiers and unrecognised columns are rejected. The trainer requires at least 40 examples and 20 examples per class, then holds out entire assets (not random rows) to reduce entity leakage. It reports ROC-AUC, average precision, Brier score, precision/recall at a fixed 0.5 threshold, confusion matrix and split counts. Artifacts are SHA-256 hashed. Training does not automatically register, approve or deploy a model.

Install optional dependencies with `pip install -e ".[ml]"`. Train with:

```bash
python -m lake_protect.intelligence.train_cli --dataset verified-labels.csv --artifact artifacts/change-review-priority.joblib --report reports/model-card.json --dataset-ref verified-labels-2026-11-v1
```

A trained artifact must be placed in controlled object storage, registered in `ml_model_versions`, evaluated into `ml_evaluations`, and explicitly approved by an administrator. The API approval endpoint requires a valid artifact hash and a passing evaluation. Do not expose an artifact path from an untrusted source to the API.

## API

- `POST /api/v1/intelligence/models`: register an artifact after object-store SHA-256 verification.
- `GET /api/v1/intelligence/models`: model registry metadata and model cards.
- `POST /api/v1/intelligence/models/{id}/evaluations`: record a versioned evaluation and human pass/fail decision.
- `GET /api/v1/intelligence/evaluations`: evaluation metrics and slices.
- `GET /api/v1/intelligence/processing-runs`: processing lineage and run status.
- `GET /api/v1/intelligence/candidates/{id}/predictions`: authorised prediction history.
- `POST /api/v1/intelligence/models/{id}/approve`: admin-only approval after passing evaluation.

## Production gates

Before any trained model is promoted: verify label provenance; use time-based and district-held-out external validation; report precision/recall and calibration by district, asset category, sensor and season; conduct blind field backtests; review false positives/negatives with domain officers; document drift thresholds and rollback; and obtain explicit departmental approval. A physical-change prediction must never itself trigger a legal notice, ownership determination, demolition, or enforcement action. Legal checks remain deterministic, separately versioned and human-governed.
