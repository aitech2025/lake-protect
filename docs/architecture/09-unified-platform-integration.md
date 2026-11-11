# 09 — Unified Platform Integration and Security Hardening

## Purpose
This increment joins the original lake-protection operational workflow to the statewide platform model. It does not replace the existing lake-specific legal, alert, field, evidence or audit domain. It establishes a safe bridge from legacy lake assets and candidate detections to canonical platform assets.

## Implemented in this increment
- Department memberships are effective-dated and support READ, CONTRIBUTE and MANAGE access levels.
- Membership records are themselves protected by RLS; users can see their own memberships, while only platform administrators can grant or revoke them.
- Authenticated requests set transaction-local PostgreSQL context from the current database user record. Role claims in JWTs are not trusted for authorization.
- RLS protects canonical departments, assets, responsibilities, parcel links, parcels, candidate links, prediction records, ingest idempotency records and the outbox.
- The machine candidate endpoint sets pipeline context only after its shared token is validated and uses a transaction-scoped advisory lock plus payload hash to make exact retries idempotent.
- Every accepted legacy candidate is joined to its canonical UUID asset and exact legacy boundary version. Spatial relationship and overlap area are recorded.
- Every candidate receives a reproducible, owner-blind REVIEW_PRIORITY baseline record with feature schema, model/version, factors and a clear non-legal disclaimer.
- Candidate detection is written to the transactional outbox in the same database transaction as the candidate, prediction and alert workflow.

## Security deployment requirements
RLS is not a substitute for database grants. Production must use a dedicated API database role that is NOT superuser, does NOT have BYPASSRLS, and is not the owner of the protected tables. The migration owner and runtime API role must be separate. FORCE ROW LEVEL SECURITY protects against accidental table-owner bypass, but PostgreSQL superusers can still bypass RLS. The current single-user Docker Compose configuration is a development topology and must not be treated as a production security boundary. A role bootstrap template is provided at [ops/postgres/runtime-roles.sql](../../ops/postgres/runtime-roles.sql). Install PostGIS as a DBA, run Alembic as the separate `lakeprotect_migrator` role, and configure `LP_DATABASE_URL` for `lakeprotect_app`. Set both role passwords out-of-band. Confirm both roles have `rolsuper=false` and `rolbypassrls=false` before go-live.

The original lake-specific endpoints retain their existing role/field-area controls. They are a single-program pilot workflow until a department responsibility mapping has been formally approved for each legacy lake asset. Do not expose mixed-department records through those endpoints until equivalent legacy-table RLS and authorization tests are in place.

## ML semantics
The baseline score is a queue-ordering heuristic, not a probability of encroachment, not a trained model, and not a legal conclusion. The existing detection confidence remains separately recorded on the candidate. A future approved model version must be registered with its immutable dataset, artifact hash, feature schema, evaluation report, and independent approval before inference is enabled.

## Operational limitations and go-live gates
- No production identity provider/SSO or MFA adapter is included yet.
- No durable outbox publisher, retry/dead-letter consumer or orchestration service is included yet.
- No STAC API/pgSTAC deployment, COG object-store adapter or complete Sentinel-1/2 processing pipeline is included yet.
- The existing local disk object store is suitable for development only; production requires approved S3-compatible/object storage and retention controls.
- RLS tests must run using a non-owner, non-superuser application role. The existing test harness's administrative database connection cannot prove isolation by itself.
- Validate migration 0005 forward and rollback on a restored PostGIS database; run API, pipeline and browser test suites; execute cross-department negative tests using the non-owner `lakeprotect_app` role; load-test spatial queries; test backups/restores and failover before deployment.
- Configure bounded SQLAlchemy connection-pool settings (`LP_DB_POOL_*`) from measured concurrency and database capacity; monitor pool wait time and saturation.
