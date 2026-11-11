# 10 — Production Storage and Event Delivery

## Object storage
The API now supports a pluggable object store:
- Local disk for development and isolated tests.
- S3-compatible storage for production, including AWS S3 and MinIO-compatible endpoints.
- SHA-256 metadata, content type, optional KMS server-side encryption, byte-range reads for raster access, and short-lived pre-signed GET URLs.

Set LP_STORAGE_BACKEND=s3 and provide LP_S3_BUCKET, LP_S3_REGION and the endpoint/credentials appropriate to the approved object store. Credentials should come from a secrets manager or workload identity, not committed environment files. Prefer workload identity over static keys when the platform supports it.

The application adapter does not provision the bucket. Infrastructure must configure private access, versioning, encryption, lifecycle/retention, replication, audit logging and backup/restore. Do not expose public bucket access. Evidence pack generation still downloads evidence objects through the API; very large COG delivery should use pre-signed URLs or a dedicated tile service rather than loading complete rasters into application memory.

## Transactional outbox dispatcher
The scheduled worker now optionally dispatches outbox events to a configured HTTPS webhook:
- Claims events in a short transaction using FOR UPDATE SKIP LOCKED and a lease.
- Publishes outside the database transaction.
- Sends a stable Idempotency-Key based on event_id; consumers must deduplicate.
- Retries with bounded exponential backoff and moves exhausted events to a dead-letter state.
- Uses worker-specific RLS context and verifies lease ownership before finalizing.

Delivery is at-least-once, not exactly-once. A receiver must persist event_id/idempotency key before applying side effects. Configure LP_OUTBOX_WEBHOOK_URL and an authentication token through secrets management. If no webhook is configured, events remain safely queued; they are not silently discarded.

## Remaining production gates
- Run integration tests against the actual non-owner runtime role; the current CI database role is an administrator and cannot prove RLS isolation.
- Add real consumer contract tests, dead-letter alerting, replay tooling and operational dashboards.
- Configure and verify production object-store policies, lifecycle, KMS, versioning, replication and restore.
- Implement STAC catalogue ingestion, COG asset lifecycle, Sentinel-1/2 preprocessing and scene/tile-based change detection.
- Add approved SSO/MFA, secrets manager/workload identity, WAF/rate limits, vulnerability scanning and threat modelling.
- Perform load, soak, failover and disaster-recovery exercises before production rollout.
