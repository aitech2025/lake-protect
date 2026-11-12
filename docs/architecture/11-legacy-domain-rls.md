# 11 — Legacy Operational-Domain Row-Level Security

## Purpose
The statewide registry and the original lake workflow share one department access boundary.
Migrations 0007–0009 extend PostgreSQL row-level security from canonical registry records to
the operational lake records, without removing the lake-specific workflow.

## Access path
A legacy lake asset is visible when its canonical `public_assets` row maps to its legacy integer ID
and that canonical asset has an effective-dated `asset_responsibilities` record for a department in
which the current user has active `user_department_access`. The existing transaction-local
`lp_current_user_id()`, `lp_is_platform_admin()` and `lp_is_pipeline_ingest()` functions are reused.
The current auditor role also receives a trusted transaction-local `lp_is_auditor()` flag.

## Covered operational records
- Legacy assets and append-only boundary versions.
- Candidates and observation rows; legal checks and matched permit, authorised-work and court-case records.
- Alerts, closure requests, field checks, owner claims, readiness items, evidence packs, officer records
  and imagery requests.
- Signals and audit-log rows.
- Monthly bulletins are platform-admin-only because they aggregate across assets.

## Special authorization cases
- Department members with MANAGE access can append a boundary version for an asset assigned to one
  of their departments. Existing boundary immutability triggers still reject UPDATE, DELETE and TRUNCATE.
- The pipeline credential is validated before machine-ingest context is set. That context permits
  the pipeline to read its input asset/boundary/legal-reference records and insert candidate,
  observation, legal-check and alert records in the same transaction.
- Auditors receive global read access to the audit chain and alerts used by the closure-sample view.
  The audit hash chain is global; filtering its rows by department would create false verification
  failures because each event's previous hash may refer to another department's event.
- Platform administrators retain statewide registry and operational visibility.

## Rollout safety
- Legacy assets must be mapped to canonical public assets and approved department responsibilities
  before department users can see them. Unmapped records are invisible to non-admin users by default.
- Runtime API and worker roles must be non-superuser, non-BYPASSRLS and distinct from the migration
  owner. A superuser connection bypasses RLS and cannot validate tenant isolation.
- CI creates a dedicated NOLOGIN, non-owner role and switches to it for the cross-department test.
  Repeat the same negative tests using the actual deployed `lakeprotect_app` database role.
- Application role checks remain mandatory: RLS isolates data by department but does not decide
  whether a user may close an alert, certify a boundary or record a field action.
- Validate migrations 0007–0009 on a restored PostGIS database and run API, pipeline and browser
  suites before production rollout.

## Limitations
This closes the database-level isolation gap for the current lake operational domain. It does not
implement SSO/MFA, complete statewide data-sharing agreements, or a trained satellite-change model.
Sentinel-1/2 processing and independent spatial-temporal backtesting remain separate acceptance gates.
