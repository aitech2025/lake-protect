# Lake Protect — Unified Data Model

**Status:** Canonical data-model specification  
**Repository baseline:** `feature/initial`  
**Physical database:** PostgreSQL 16 + PostGIS 3.4  
**Migration authority:** Alembic under `api/migrations/versions/`

## Purpose

This is the single logical data model for the Lake Protect application as it expands from lake protection to a statewide public-asset protection platform. Lakes remain the first operational domain. Government land, forests, reservoirs, canals, parks, endowment properties and other notified public assets use the same platform identity, provenance, geospatial, workflow, evidence and access foundations, with category-specific rules.

The model is implemented incrementally. It is not a proposal to replace the existing application or to create a second asset registry.

## Read this with

- [Entity catalogue and data dictionary](entity-catalog.md)
- [Logical ER diagram](erd.md)
- [Migration and implementation roadmap](migration-roadmap.md)
- [Architecture decision](../architecture/12-unified-architecture-decision-and-current-state.md)
- [Physical schema migrations](../../api/migrations/versions/)

## Core design decisions

1. **One canonical identity:** `public_assets.id` (UUID) is the long-term identity for every public asset. Department codes, survey numbers, GIS identifiers and legacy IDs are external identifiers, not platform primary keys.
2. **Lake compatibility is intentional:** `public_assets.legacy_asset_id` bridges to `assets.id`. Existing lake workflows keep their current bigint IDs until a verified expand–migrate–contract transition is complete.
3. **Separate legal and operational relationships:** ownership, custodianship, possession, jurisdiction, operational responsibility, enforcement and data stewardship are distinct effective-dated rows in `asset_responsibilities`.
4. **Parcels are not assets:** one asset can span multiple survey parcels and one parcel can intersect multiple assets. Model this with `asset_parcels`.
5. **Administrative geography is temporal:** administrative units and asset-to-unit relationships are versioned by valid dates. Do not assume current district/mandal/village names describe historical records.
6. **Geometry is evidence-backed:** retain source authority, source record, validity dates, recorded time and immutable boundary versions. A derived geometry is never silently promoted to certified/notified.
7. **Detection is not adjudication:** observations and processing runs produce change candidates. Legal checks, alerts, field verification and competent-authority decisions are separate records.
8. **Reproducibility:** each candidate/prediction must be traceable to input scenes, processing run, pipeline/configuration, feature schema, model version and boundary version.
9. **Evidence and audit are append-oriented:** preserve hashes, manifests, actor/time, provenance and decision history. A hash is an integrity check, not proof that an allegation is true.
10. **Security at every layer:** API authorization and PostgreSQL RLS enforce department, jurisdiction and assignment scope. UI filtering is never an authorization boundary.

## Model layers

| Layer | What it owns | Principal entities |
|---|---|---|
| Identity and governance | Users, departments, administrative hierarchy and access | `users`, `departments`, `administrative_units`, `user_department_access` |
| Asset registry | Canonical identity, category and lifecycle | `public_assets` |
| Cadastral and geography | Survey parcels and administrative relationships | `land_parcels`, `asset_parcels`, `asset_admin_links` |
| Responsibility and provenance | Department remit, source records and import lineage | `asset_responsibilities`, `ingestion_batches`, `source_records` |
| Spatial/legal reference | Versioned boundaries, permits, authorised works and court matters | `boundaries`, `permits`, `authorised_works`, `court_cases` |
| Earth observation | Satellite scenes and acquired observations | `satellite_scenes`, `observations` |
| Intelligence | Processing runs, candidates, asset matches and predictions | `processing_runs`, `candidates`, `candidate_asset_links`, `candidate_predictions` |
| ML governance | Model versions and evaluations | `ml_model_versions`, `ml_evaluations` |
| Operational response | Legal checks, alerts, assignments, field work and closure | `legal_checks`, `alerts`, `field_checks`, `closure_requests` |
| Evidence and accountability | Evidence packs, audit events and durable events | `evidence_packs`, `audit_log`, `outbox_events` |

## Identifier and time conventions

- UUID for statewide entities and cross-domain relationships; bigint retained for the legacy lake operational domain during migration.
- UTC `timestamptz` for event/acquisition/recording times; `date` for legal validity dates where time-of-day is not meaningful.
- Use half-open validity intervals `[valid_from, valid_to)` for effective-dated relationships. A null `valid_to` means currently open-ended.
- Preserve both valid time (when a fact applies in the real world) and transaction/recorded time (when the platform learned it).
- Use EPSG:4326 for interchange/storage geometry. Use an appropriate projected CRS for area and distance calculations; never calculate square metres directly from longitude/latitude coordinates.
- Store raster bytes and large evidence objects in S3-compatible object storage. PostgreSQL stores metadata, references, hashes and relationships.

## Implementation status vocabulary

- **Implemented:** represented in current Alembic migrations and/or application code.
- **Partially implemented:** core table/contract exists but full lifecycle, integration or operational controls are incomplete.
- **Target:** required by the accepted architecture but not yet implemented in the current database.
- **Legacy:** active compatibility schema; do not remove until migration gates pass.

See the catalogue for per-entity status. The Alembic migrations, not this document or ORM metadata, are the source of truth for the physical database.
