# 06 — Production, Security and Operations

## 1. Hosting
Target deployment to a Telangana Government Data Centre, NIC-approved infrastructure or other expressly approved hosting. Final selection depends on data classification, policy, procurement, security audit, residency and integration requirements. Keep containers, configuration, PostgreSQL and S3-compatible storage portable. Do not claim compliance or approval before formal sign-off.

## 2. Deployment
For a smaller pilot, Docker Compose or managed containers may suffice. For production multi-department workloads, consider Kubernetes with separate pools for system/ingress, API, GIS/tile, CPU raster, GPU inference (only if measured need), orchestration and monitoring. Kubernetes is a target option, not a prerequisite for the first pilot.

## 3. Resilience
Run multiple API replicas across failure domains; PostgreSQL HA with tested failover and PITR; object-store versioning/replication; durable queues and idempotent consumers; health/readiness checks; graceful shutdown and rolling deployments. Asset/case workflows remain available during provider/ML outages. Test restore, failover, queue replay and site recovery.

Illustrative design objectives only (not achieved SLAs):
| Capability | Availability objective | RPO | RTO |
|---|---:|---:|---:|
| Core API/case workflow | 99.9% | 15 min | 1 hour |
| PostgreSQL | 99.95% target | 5–15 min | 1 hour |
| Object/evidence storage | 99.9% | 15 min | 4 hours |
| Imagery processing | 99% monthly | Reprocess from retained inputs | 8 hours |
| Analytics | 99% | 24 hours | 8 hours |

Final objectives follow business-impact analysis and service-owner approval.

## 4. Identity and security
Integrate approved government SSO (OIDC/OAuth2 or mandated protocol), MFA for privileged roles, RBAC+ABAC, least-privilege service identities and tested PostgreSQL row-level security. Use TLS, approved encryption/key management, secrets manager, separate environments, WAF/rate limits, signed short-lived evidence URLs, dependency/container scanning, SAST/DAST and incident response.

Minimise personal data. Protect owner/claimant names, court records and field locations through purpose limitation, access logging and retention policy. Citizen reporting needs separate privacy and abuse assessment.

## 5. Audit integrity
Append-only events include actor, role, department, timestamp, action, entity, reason and correlation ID. Use hash-chain or equivalent tamper evidence and periodically anchor signed checkpoints outside the primary database. Use immutable object versions/retention lock where approved. Hashes alone do not prove admissibility. Retain boundary, model, rule and dataset versions used by each case.

## 6. Observability
Prometheus/Grafana for metrics; OpenTelemetry for traces; Loki or approved central logging; Tempo or equivalent trace store; Sentry or approved error tracking; Alertmanager for operations; model/data monitoring; SIEM integration. Monitor API latency, DB locks/connections, queue depth/age, ingestion lag, provider errors, processing time, GPU use, object-store errors, tile latency, audit integrity and notification delivery. Every alert has an owner and runbook.

## 7. Backup and DR
Encrypted Postgres backups and WAL archive; periodic isolated restore; object-store replication/versioning and integrity checks; backup manifests and retention; separate backup credentials/failure domain; IaC and deployment artefacts in version control; documented DR roles and exercises. Back up evidence objects, STAC metadata, model artefacts, configuration and integration cursors as well as the database.

## 8. CI/CD
Lint/type-check/unit tests; API/database integration; spatial CRS/geometry tests; security/dependency scans; container build/SBOM; migration forward/rollback tests; performance smoke tests; staging deployment; approval; controlled rollout and rollback. Use immutable image tags. No destructive production migration without backup and review.

## 9. Capacity and cost
Benchmark concurrent map/dashboard users, spatial joins, ingestion bursts, offline field sync, scene search, tile requests, evidence packs and monthly reports. Scale on queue depth and job duration, not CPU alone. Use PgBouncer, spatial indexes, query plans, bounded exports, caching and read replicas. Partition only after measuring.

Track costs by provider, scene, area, resolution, processing run, storage tier, department and alert. Budget commercial tasking separately from routine screening. Estimate only after measuring coverage, revisit, escalation percentage, storage retention, compute, egress and DR.

## 10. Go-live gates
No operational alerts for a geography/category until source rights and refresh are documented; asset inventory and boundary provenance reviewed; jurisdiction routing approved; model independently validated; analyst/field SOP accepted; security/privacy/hosting signed off; backup/restore and outage exercises pass; dashboard definitions and escalation SLAs approved.

Production readiness requires named owners for service, department, data sources, boundaries, models, security, field workflow, legal workflow and support.