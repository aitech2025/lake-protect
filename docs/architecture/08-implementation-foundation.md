# 08 — Implementation Foundation

## Scope and status
This is an additive implementation increment, not a production certification. Existing prototype
tables, IDs, workflows and frontend contracts remain intact while the statewide model is introduced
alongside them.

## Database
Migration 0004 introduces canonical UUID public asset identities linked to legacy integer asset IDs;
administrative hierarchy; parcel registry and many-to-many asset/parcel links; effective-dated asset
responsibilities; source provenance and ingestion batches; STAC scene metadata; processing runs;
candidate-to-asset spatial links; model registry/evaluations; and a transactional outbox. Legacy
assets are imported as DERIVED, never as authoritative. GiST and B-tree indexes cover spatial and
lookup paths. No existing table is dropped or renamed.

## Backend
Versioned /api/v1/platform registry endpoints coexist with the prototype endpoints. Reads require
authentication; writes require admin or nodal roles. This first increment does not yet implement
department ABAC or PostgreSQL RLS. Those are mandatory gates before real multi-department data is
loaded. Do not treat authentication alone as tenant isolation.

## ML
A versioned, owner-blind feature contract and transparent baseline triage are introduced. The
baseline is not a trained ML model and must not be represented as one. A trained model requires
lineage, leakage-safe spatial/temporal splits, blind backtest, slice metrics, calibration, shadow
deployment and approval. Predictions only rank human review; they cannot determine legal status,
title, demolition or enforcement.

## Remaining production gates
1. Implement department/jurisdiction ABAC and PostgreSQL RLS; prove cross-department isolation.
2. Add S3-compatible object storage, STAC API/pgSTAC and short-lived signed URL access.
3. Add an outbox publisher with retry, dead-letter and idempotent consumers.
4. Implement scene/tile processing and spatial matching; M2/M3 scientific backtest remains a separate gate.
5. Add external SSO/MFA, secrets management, observability, HA/DR, load and restore tests.
6. Validate migrations on a restored production-like database before any real-data cutover.
