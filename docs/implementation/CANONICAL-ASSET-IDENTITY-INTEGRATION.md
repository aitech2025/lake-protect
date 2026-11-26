# Canonical Asset Identity Integration

**Status:** implementation increment prepared on `consolidated`; pending migration and CI validation.

## Objective

Use the UUID `public_assets.id` as GeoGuard's permanent cross-domain asset identity while retaining the existing bigint `assets.id` for the lake monitoring engine and current API compatibility.

## Changes in this increment

- Add `assets.platform_asset_id` as a one-to-one link to `public_assets.id`.
- Backfill a canonical registry row for every existing operational asset except `reported_place` support rows.
- Generate a stable, non-geographic legacy bridge code (`TG-LEGACY-########`) for rows that need reconciliation. This code is permanent once created; it does not encode mutable district, mandal, village, department or asset category.
- Add database triggers so new operational assets are reconciled to the canonical registry, and propagate the UUID to boundaries, detections/candidates, incidents/alerts, monitoring history and signals.
- Expose the canonical UUID and GeoGuard Asset Code in the legacy asset API; expose `legacy_asset_id` in the platform registry API.
- Keep candidate assets and their internal `reported_place` support records outside the registered asset identity space.

## Identity rules

1. `public_assets.id` is the permanent internal identity. `asset_code` is the permanent human-readable identity. Neither is reused.
2. `assets.id` remains a compatibility/operational key during the expand–migrate–contract period. It is not the cross-domain identity.
3. A platform asset may have no `legacy_asset_id` when it is registered but does not participate in the legacy lake engine.
4. A legacy operational asset must resolve to exactly one canonical registry row unless its type is `reported_place`.
5. Candidate assets, watch targets and registered assets remain distinct. Citizen reports outside a registered asset create a candidate asset and incident; they do not create a registered asset.
6. GIS boundary validation and legal/administrative approval remain separate. This identity bridge does not certify boundaries or change legal status.
7. No government system integration, expanded RBAC role or automatic legal conclusion is introduced.

## Compatibility and migration

The migration is additive. Existing integer primary keys and routes remain available. New UUID fields are nullable on child records for support rows and records without a registered asset. The migration deliberately fails if a non-`reported_place` operational asset cannot be reconciled; it does not silently omit records.

## Validation required before calling this complete

- Upgrade a clean database through Alembic head.
- Upgrade a copy of the current database and compare operational asset counts before/after.
- Verify one-to-one mapping, no duplicate GeoGuard Asset Codes, no missing canonical UUIDs for registered operational assets, and no UUID assigned to `reported_place`.
- Verify UUID propagation for a new asset, boundary, candidate, incident, monitoring change and signal.
- Verify platform and legacy asset APIs return the same canonical identity.
- Run API/PostGIS and pipeline suites; inspect migration output and test report.
- Only after validation, update the status to complete. No claim of production readiness is made by this increment.
