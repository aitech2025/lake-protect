# 04 — AI/ML Detection and Governance

## 1. Principles
Use task-specific models and geospatial rules, not one opaque encroachment model. A model estimates observable change; it cannot decide ownership, title, permit validity, legal status or enforcement. ML feeds candidate review; the legal rules engine remains separate.

## 2. Model portfolio
| Task | Candidate approach | Main caveat |
|---|---|---|
| Water extent | MNDWI/NDWI, Sentinel-1 SAR features, temporal statistics | Seasonal fluctuation, turbidity, vegetation and shadow |
| New built-up structures | Spectral/texture features, supervised segmentation; U-Net or Siamese U-Net after labels exist | Sentinel-2 10 m is too coarse for many small structures |
| Filling / land conversion | Multi-temporal classification; Random Forest baseline, later segmentation | Soil, construction, agriculture and restoration can look alike |
| Forest disturbance | Sentinel-2 + SAR temporal features and segmentation | Legal forest status comes from authoritative records |
| Nala obstruction | GIS corridor rules plus object/change segmentation | Requires accurate corridor geometry and field validation |
| Candidate triage | Transparent rules, XGBoost or calibrated classifier | Score is triage, not probability of illegality |

ChangeFormer and Siamese U-Net are possible later alternatives, not default choices. Begin with indices, statistical baselines and Random Forest/XGBoost. Deep learning requires representative labels and a meaningful baseline comparison.

## 3. Two-stage screening
Stage A: broad tile-level screening using routine open imagery and lightweight methods. Generate candidate polygons with quality flags and temporal context.

Stage B: targeted high-resolution imagery and detailed segmentation for priority candidates, followed by analyst review and field verification.

Do not promise weekly/monthly observation for every asset until provider revisit, cloud, licence, budget and capacity are measured. Display observation coverage honestly.

## 4. Prediction provenance
Store candidate geometry, task/class taxonomy version, score and calibration status, model ID/version/hash, configuration and preprocessing version, training dataset manifest, source scene IDs/acquisition times/quality, processing run, asset/boundary versions, rule version, uncertainty flags and human review state.

A model score is not a legal probability. Do not label an uncalibrated score as “90% certain encroachment”.

## 5. Dataset governance
Build labels from verified historical events, non-events, authorised construction/restoration/desilting, seasonal water changes, agriculture/soil exposure, sensor artefacts and ambiguous cases. Use CVAT or equivalent. Publish annotation guidance; second-review disagreements; record licences; split train/validation/test by geography and time to prevent adjacent-tile leakage; maintain a blind holdout unavailable to model developers.

Historical news dates are not automatically construction dates. Independently verify event dates and geometries.

## 6. Validation gates
Report precision, recall, F1, area IoU, false alerts per 100 assets / square kilometre / review month, detection lead time, duplicate rate, calibration where applicable, imagery coverage and analyst/field confirmation. Break down by task, sensor, asset class, season and geography; include sample sizes and confidence intervals.

Blind backtest: freeze independently verified positive and negative cases; reproduce imagery available at each historical date; forbid look-ahead; score before official/public action; report misses, late detections, false positives and unobservable cases separately. Agree minimum thresholds and false-positive workload with the department before pilot.

## 7. Human workflow
Recommended states: MODEL_CANDIDATE → SPATIALLY_MATCHED → ANALYST_REVIEW → FIELD_VERIFICATION → FIELD_CONFIRMED_CHANGE → LEGAL_REVIEW → AUTHORITY_FINDING → ACTION_RECORDED / MONITORING / CLOSED.

Alternative outcomes: NOT_A_CHANGE, AUTHORISED_WORK, SEASONAL_OR_ENVIRONMENTAL_CHANGE, BOUNDARY_UNCERTAIN, INSUFFICIENT_EVIDENCE and DUPLICATE.

Model confidence, analyst judgement, field observation and legal finding are distinct fields. Only authorised officials can record formal findings.

## 8. MLOps
Use PyTorch for deep learning, scikit-learn/XGBoost for baselines, MLflow for experiment/model registry, DVC or immutable dataset manifests, CVAT for annotation, Prefect or equivalent orchestration and Evidently or equivalent monitoring.

Promotion: experiment → reproducible training → frozen holdout evaluation → domain review → staging shadow run → limited human-reviewed pilot → approved release → monitoring/rollback. Never rewrite historical predictions when a model changes.

## 9. Monitoring and safe language
Monitor sensor mix, resolution, cloud/quality, feature distributions, candidate rates, class mix, calibration, analyst rejection and field-confirmation rates. Pause/downgrade a model when validation or source quality degrades.

Use “possible built-up change detected”, “candidate overlaps mapped buffer”, “field verification requested” and “first observed between dates”. Avoid automated labels of illegal encroachment, guilt, demolition or unsupported exact construction dates.

Do not buy GPU capacity before profiling proves a need. Accurate boundaries, labels, data rights and field verification matter more than model novelty.