# Data Model Migration and Implementation Roadmap

## Guiding rule

The Alembic migration chain is the physical schema source of truth. Evolve it with additive, reviewable migrations. Do not drop legacy tables or replace bigint IDs until application code, stored evidence, integrations and historical records have been migrated and reconciled.

## Phase 0 — Establish the baseline

- Keep PostgreSQL/PostGIS and the FastAPI modular monolith as the transactional system of record.
- Keep the existing lake operational tables and current frontend/API contracts.
- Treat `public_assets.id` as the long-term canonical identity.
- Keep `public_assets.legacy_asset_id` as the explicit compatibility bridge.
- Ensure SQLAlchemy mappings cover the statewide tables; do not call `Base.metadata.create_all()` in production.
- Add schema drift checks so ORM metadata and Alembic DDL are reviewed together.

## Phase 1 — Canonical identity adoption

1. Reconcile every `assets.id` to exactly one `public_assets.id`.
2. Validate uniqueness and completeness of legacy asset mappings.
3. Create/validate asset external identifiers and aliases (target `asset_identifiers`) before accepting multiple source-system IDs.
4. Replace free-text/array survey-number references with parcel relationships where reliable cadastral records exist.
5. Backfill administrative links and responsibility relationships only from sourced records.
6. Preserve unresolved and conflicting mappings in a reconciliation queue; never invent an owner or authoritative boundary.
7. Add read APIs that resolve a legacy ID to canonical UUID and vice versa for controlled migration.

**Exit criteria:** 100% of active legacy assets are mapped or explicitly quarantined; duplicate identity conflicts are resolved; all mappings are auditable and repeatable.

## Phase 2 — Normalize boundaries and legal references

- Introduce canonical `asset_boundaries` and `boundary_sources` as additive tables.
- Migrate existing lake `boundaries` into canonical boundary versions with a source classification and original legacy key.
- Preserve all original geometry bytes/coordinates, SHA-256, status, valid dates, source metadata and supersession lineage.
- Add a canonical legal-reference model for permits, leases, government orders, court matters, stays, assignments and authorized works.
- Keep the existing `legal_checks` table and rule behavior operational until parity tests pass.
- Keep the exact boundary/rule version on every decision record.

**Exit criteria:** historical candidate/legal-check replay resolves the same source boundary version; geometry checks and spatial query plans pass; no evidence pack loses its original references.

## Phase 3 — Normalize observations and processing lineage

- Introduce `processing_run_scenes`, `raster_products` and `candidate_observations`.
- Backfill current observation arrays into the normalized candidate-observation bridge.
- Keep writing the legacy array during the compatibility window; verify dual-write parity.
- Add unique source IDs, content checksums, licence and source metadata.
- Store raster products as COG/object-storage artifacts; keep only metadata and URIs in Postgres.
- Ensure candidate lineage includes run ID, scene IDs, processing/config hash, model version, feature schema and boundary version.

**Exit criteria:** each candidate can be reproduced from immutable source references and versioned pipeline inputs; no untraceable candidate remains in the active workflow.

## Phase 4 — Unify cases and human decisions

- Add canonical `cases`, `case_assignments`, `candidate_reviews` and `field_verifications` as additive entities.
- Model a case as an operational/legal work unit; do not force one case to equal one candidate.
- Permit multiple candidate observations/findings to contribute to one case and multiple cases to reference one asset.
- Preserve the current `alerts` state machine and controlled closure rules while adapters translate legacy alerts to canonical case IDs.
- Keep legal review, field verification, competent-authority action and closure as distinct decision records.
- Require actor, role, department, timestamps, reason and supporting evidence for all human decisions.

**Exit criteria:** end-to-end parity with current alert/field/evidence workflows; two-person approval and legal hold behavior preserved; no duplicate active cases on reprocessing.

## Phase 5 — Category configuration and additional public assets

- Add governed `asset_categories`, `asset_category_schemas` and `rule_packs`.
- Implement category-specific validation and legal workflows for each asset class.
- Onboard new categories only with authoritative source agreements, data ownership, metadata contract, legal reference rules and acceptance tests.
- Do not assume lake water-spread algorithms transfer directly to forest, government-land, canal or endowment domains.
- Keep the common registry, parcel, provenance, access, case and evidence services shared.

**Exit criteria:** each category has an approved data contract, policy owner, validation suite and operational escalation path before production activation.

## Phase 6 — Data quality, governance and statewide operations

- Add data-quality issue and reconciliation-decision records.
- Add source-system registry, refresh SLAs, data-sharing/redistribution constraints and data retention.
- Add externally protected audit checkpoints and evidence retention policies.
- Add privacy classification and purpose-based access for claimant, court and field data.
- Load test RLS and key spatial queries using the actual non-owner runtime database role.
- Exercise backup/restore, point-in-time recovery, failover and migration rollback.
- Introduce table partitioning only after measured data volume and query patterns justify it.

## Required engineering controls

### Migration discipline

- One Alembic revision per logical schema change.
- Prefer expand → backfill → validate → switch reads/writes → contract.
- Never drop or rename a column in the same release that stops using it.
- Add NOT NULL constraints only after backfill and validation.
- Use concurrent index creation for large production tables where operationally appropriate.
- Include downgrade behavior where safe; for irreversible data transformations, document forward-recovery rather than pretending a lossy downgrade is safe.
- Test migrations from an empty database and from a representative previous release.

### Data integrity

- Foreign keys for relational identity.
- Unique constraints for source-system IDs and idempotency keys.
- Check constraints for valid dates, enumerations and score ranges.
- GiST indexes for spatial geometry and B-tree indexes for join/filter keys.
- Use PostGIS exact predicates after bounding-box index filters.
- Validate geometry type, SRID, validity and non-empty geometry at ingestion.
- Calculate area/distance in a suitable projected CRS.

### Security

- Use the dedicated non-owner application database role with RLS enforced.
- Test SELECT, INSERT, UPDATE and DELETE policies under representative department memberships and expiry dates.
- Ensure RLS policy joins have supporting indexes.
- Separate platform administration from department MANAGE access.
- Do not expose claimant names or sensitive case evidence in general map/API responses.

## Explicit non-goals for this data-model increment

- No destructive rewrite of legacy lake tables.
- No new microservice boundary or distributed database.
- No claim that satellite ingestion, ML training or statewide data integrations are complete.
- No seed of fabricated government ownership, survey, boundary or department responsibility records.
- No production migration applied to a live database by this documentation or ORM mapping change.
