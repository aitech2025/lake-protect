# 12 — Unified Architecture Decision and Current Implementation Status

**Status:** Accepted architecture direction  
**Decision date:** 15 November 2026  
**Applies to:** `aitech2025/lake-protect`  
**Baseline branch:** `feature/initial`  
**Baseline commit reviewed:** `eef2582e0c158dd194cc2ff20a14e634f05caabe`

## 1. Executive decision

Adopt **one unified Lake Protect architecture**:

- Keep the existing repository as the implementation foundation.
- Keep the current React/PWA + FastAPI modular-monolith control plane and PostgreSQL/PostGIS operational system.
- Treat the statewide architecture pack as the target design for multi-department, multi-asset expansion.
- Add a separately scalable geospatial intelligence plane for imagery discovery, raster processing, inference and model evaluation.
- Integrate geospatial outputs into the existing candidate/observation/alert workflow through versioned contracts and provenance.
- Do not create a second backend, asset registry, case-management system, or parallel ML scoring platform.

This is an additive evolution, not a rewrite. The architecture choice does not imply that all target components are already implemented or that the platform is production-certified.

## 2. What the repository implements today

This assessment is based on the repository source and migrations, not on architecture diagrams alone. It is a code review; it does not claim that a fresh local build, complete test suite, load test or production deployment was executed during this review.

### 2.1 Application and operational control plane

The current application is a modular monolith:

- React, TypeScript, Vite, React Router, MapLibre and a PWA/offline field experience.
- FastAPI API with SQLAlchemy, Alembic, GeoAlchemy2 and Shapely.
- PostgreSQL 16 with PostGIS 3.4 as the operational and spatial database.
- A Python worker for escalation/timers and outbox delivery.
- Local-disk and S3-compatible object-storage adapters.
- Docker Compose as the current deployment topology.

The code includes asset and boundary management, observations/candidates, legal checks, alert lifecycle, permits/authorised works/court references, field verification, closure requests, evidence packs, officer records, audit, monthly reporting and department-scoped access.

The frontend includes map layers, Telugu/English support, offline field queues and synchronisation. These are working product foundations to preserve; they should not be replaced by a new application simply to match a target architecture diagram.

### 2.2 Data architecture

Two related domain models currently coexist:

1. **Legacy lake operational domain:** lake assets, boundaries, observations, candidates, legal checks, alerts, permits, authorised works, court cases, field checks, evidence, officer records, audit and reporting.
2. **Canonical statewide platform foundation:** UUID-based `public_assets`, asset responsibilities, parcel links, administrative links, departments, administrative units and candidate-to-asset reconciliation.

The canonical registry links to legacy lake records through a compatibility relationship. Responsibility types distinguish owner, custodian, possessor, jurisdiction, operational, enforcement and data-steward roles. Effective dates and source provenance are important parts of this model.

**Decision:** the canonical statewide asset identity is the long-term identity. The legacy lake schema remains supported during a controlled compatibility period. Do not drop or bulk-rewrite legacy tables until mappings, data migration, historical case replay, evidence references and rollback have been proven.

PostGIS is the spatial system of record for authoritative operational geometries and spatial relationships. Geometry validity, spatial intersection and indexed queries belong in the database where appropriate.

### 2.3 Detection and ML status

The candidate ingestion path accepts outputs from a detection pipeline and validates geometry, asset/boundary association, temporal conditions and repeat observations before persisting candidates and observations. It records candidate-to-asset relationships and an outbox event.

The current intelligence scoring implementation is a deterministic, explainable weighted heuristic. Its features include area, growth, persistence, observation timing, sensor agreement, boundary quality and preventability. Prediction records retain score, model/version labels, schema version, feature/factor data and a disclaimer.

This score is a **review-priority heuristic**, not a trained predictive model, calibrated probability, proof of encroachment or legal finding.

The following target capabilities must not be represented as complete merely because optional dependencies, schemas or architecture documents exist:

- Production Sentinel-1/Sentinel-2 discovery and ingestion.
- STAC/pgSTAC catalogue operation.
- Scene/tile raster preprocessing and Cloud Optimized GeoTIFF (COG) production.
- Validated water/built-up/land-cover change detection.
- Asset-specific trained inference.
- Governed labelled datasets, blind historical backtests and independent evaluation.
- MLflow model lifecycle, drift monitoring and model promotion controls.

### 2.4 Security, evidence and event delivery

The current code includes JWT validation against live user records, database-derived roles, transaction-local security context, canonical and legacy row-level security policies, department access and pipeline authentication before setting pipeline context.

Evidence storage has local and S3-compatible adapters, content hashes and evidence-pack verification. The audit chain is hash-linked and tamper-evident within the application database; it is not, by itself, an externally anchored immutable archive.

Candidate ingestion uses a transactional outbox. The worker claims events with leases/locking, delivers outside the transaction, uses event identifiers for idempotency and applies bounded retry behaviour. Delivery is at-least-once; consumers must deduplicate.

Production SSO/MFA, workload identity, key management and external audit anchoring, security operations, HA/DR and full production-role verification remain release gates.

## 3. Unified target architecture

| Plane | Target responsibility | Preferred foundation |
|---|---|---|
| Experience | State/department dashboards, GIS, Asset 360, analyst desk, field PWA | Existing React/TypeScript/MapLibre/PWA |
| Transactional control plane | Registry, parcels, boundaries, legal rules, alerts, cases, field work, evidence, audit, reports | Existing FastAPI modular monolith |
| Identity and policy | Government identity federation, MFA, RBAC + ABAC, department and jurisdiction policy | Keycloak/OIDC or approved government IdP; PostgreSQL RLS as defence in depth |
| Operational geospatial data | Assets, parcels, versioned boundaries, observations, candidate geometries, administrative relationships | PostgreSQL + PostGIS |
| Imagery catalogue | Searchable, versioned scene metadata and footprints | STAC API / pgSTAC where operationally justified |
| Object and raster storage | Source imagery, derived COGs, evidence and long-lived artefacts | MinIO or approved S3-compatible storage |
| Geospatial intelligence plane | Scene discovery, preprocessing, tiling, raster analysis, candidate generation and spatial matching | Python, GDAL, Rasterio, xarray/odc-stac, Shapely/GeoPandas as appropriate |
| Workflow orchestration | Retryable, observable, resumable geospatial batch DAGs | Argo Workflows for Kubernetes deployment; simpler worker scheduling during pilot |
| ML lifecycle | Dataset lineage, experiments, evaluation, model approval and serving metadata | MLflow plus versioned datasets/artifacts |
| Map delivery | Raster COG tiles and efficient vector tiles | TiTiler and Martin or equivalent, introduced when scale requires |
| Events and integrations | Durable notifications, departmental adapters, retries and reconciliation | Existing transactional outbox first; broker only when measured throughput/decoupling requires |
| Observability | Logs, metrics, traces, alerting and SLOs | OpenTelemetry, Prometheus, Grafana and Loki |
| Deployment | Portable pilot and resilient statewide topology | Docker Compose for development/pilot; Kubernetes + GitOps for production when operationally supported |

The transactional control plane must remain usable when satellite processing or ML is unavailable. The geospatial plane scales independently because raster workloads have different CPU, memory, storage and scheduling requirements from case-management APIs.

Do not introduce Kafka, Redis, Kubernetes or microservices simply as checklist technologies. Add each component when a measured availability, throughput, isolation, operational or ownership requirement justifies it.

## 4. End-to-end data and decision flow

1. **Onboard and govern:** ingest approved asset, parcel, boundary, department and administrative data with source authority, effective dates, licence, confidence and provenance.
2. **Discover imagery:** query approved providers/catalogues and record scene metadata, footprint, acquisition time, processing level and licence.
3. **Process once by scene/tile:** store source objects, run quality/cloud/no-data checks, generate required raster products and COGs. Do not download and process the same scene independently for every lake.
4. **Detect observable change:** run task-specific algorithms/models and record processing-run, model, dataset, parameters and source lineage.
5. **Spatially reconcile:** intersect candidate geometries with versioned asset boundaries and parcels using PostGIS; preserve the boundary version used.
6. **Triage, do not adjudicate:** create review-priority candidates and route them into the existing candidate/observation/alert workflow. Persist uncertainty and reasons.
7. **Human verification:** analyst review, field verification, permit/authorised-work checks, legal scrutiny and competent-authority action.
8. **Evidence and audit:** retain source references, hashes, processing metadata, boundary/rule versions, field evidence and every human action.
9. **Learn safely:** use reviewed outcomes for governed datasets and evaluation; do not silently feed unverified alerts back as truth.

## 5. Domain model: common platform, asset-specific policy

Use one canonical asset registry and common observation/case/evidence services. Do not force every asset category into identical detection or legal rules.

| Asset category | Example observable change | Category-specific assessment |
|---|---|---|
| Lakes and tanks | Water spread, FTL/buffer activity, construction, boundary change | Notified FTL/buffer, irrigation and local-body records, permits and orders |
| Reservoirs, dams and canals | Water/structure change, occupation, channel obstruction | Dam/irrigation authority boundaries and safety/operational rules |
| Government lands | New structures, occupation, land-cover change | Land classification, survey/cadastral records, assignment and lease records |
| Forests | Tree-cover loss, clearing, land conversion | Forest notifications, compartment boundaries, approvals and statutory process |
| Parks/open spaces | Construction, occupation, land-cover conversion | Master plan, reservation and local-body records |
| Nalas/drainage | Narrowing, blockage, construction, diversion | Drainage plans, flood lines, easements and competent authority records |
| Endowment and other notified institutional lands | Parcel occupation or land-use change | Institution-specific title, notification, legal and custodial records |

A common physical-change signal does not establish illegality. The competent authority, current law, source record and applicable procedure govern the legal determination. Asset-specific rules and model thresholds require validation and versioning.

## 6. Keep, evolve, build — definitive consolidation decision

### Keep as the implementation foundation

- Existing React/MapLibre/PWA and offline field workflow.
- FastAPI modular transactional application.
- PostgreSQL/PostGIS as operational and spatial source of truth.
- Canonical public-asset registry, responsibility and department foundations.
- Existing lake legal assessment, alert state machine and field/case workflows.
- Boundary versioning, evidence packs, audit and object-storage abstraction.
- Transactional outbox and operational escalation worker.
- Existing RLS and department-scope security foundations.

### Evolve without parallel replacements

- Move legacy integer asset identity toward canonical UUID identity through explicit mapping and compatibility, not destructive rewrite.
- Generalise lake workflows into reusable services with asset-category policy modules.
- Keep the current heuristic as a transparent baseline; add trained models behind versioned interfaces and evaluation gates.
- Separate geospatial batch processing from the operational escalation worker.
- Use MinIO/S3-compatible storage for production objects; local disk remains a development adapter.
- Keep Compose for local development and controlled pilot; introduce Kubernetes only with a production operations team and tested runbooks.
- Extend the outbox only when delivery volume and integration requirements justify a broker.

### Build as new, independently testable capabilities

1. STAC catalogue and approved satellite-provider adapters.
2. Source imagery ingestion, metadata validation, storage lifecycle and COG production.
3. Scene/tile-based raster workflow and processing-run registry.
4. Sentinel-1/Sentinel-2 change-detection baselines and asset-specific inference.
5. Dataset governance, annotation protocol, blind backtesting and model promotion.
6. Production identity federation/MFA, service identity, secrets and key management.
7. Raster/vector tile delivery and cache strategy at measured scale.
8. Observability, SLOs, HA database/object storage, backup, restore and disaster recovery.
9. Departmental data adapters, reconciliation, ownership and refresh SLAs.
10. Load, soak, security, privacy and field-network acceptance testing.

### Do not introduce or retain as competing architectures

- A second backend or parallel asset registry.
- A second alert/case/evidence lifecycle.
- A second independent scoring service that duplicates candidate triage.
- Full microservice decomposition before workload and ownership boundaries are measured.
- Destructive replacement of the legacy lake schema before migration proof.
- Automatic legal verdicts based solely on model output.

This is the authoritative consolidation decision for future implementation and pull-request review.

## 7. Research and standards alignment

The target favours open geospatial interfaces and portable infrastructure:

- [OGC SpatioTemporal Asset Catalog (STAC)](https://www.ogc.org/standards/stac/) provides a standard structure for describing geospatial assets and their spatiotemporal metadata.
- [OGC STAC API](https://docs.ogc.org/cs/25-005/25-005.html) provides a standard API model for discovering catalogue items.
- [OGC Cloud Optimized GeoTIFF](https://www.ogc.org/standards/ogc-cloud-optimized-geotiff/) and its [implementation standard](https://docs.ogc.org/is/21-026/21-026.html) support efficient access to tiled raster data and overviews, including partial reads.
- PostGIS remains the spatial relational foundation; COG/STAC complement it rather than replace the operational database.
- MinIO, Keycloak, Argo Workflows, MLflow, OpenTelemetry, Prometheus, Grafana, TiTiler and Martin are candidate self-hostable components. Their adoption is subject to version compatibility, security review, licence review, operational capability and benchmark results.

Standards compliance and product selection do not establish government data access, legal authority, model accuracy or production readiness.

## 8. Implementation sequence and acceptance gates

| Sequence | Work package | Acceptance evidence |
|---|---|---|
| 0 | Baseline and architecture boundaries | Reproducible build/test baseline, schema backup/restore, API contracts and explicit module ownership |
| 1 | Canonical registry and governance | Cross-category asset onboarding; effective-dated responsibility; source lineage; historical boundary replay; department isolation tests |
| 2 | STAC, storage and scene processing | One approved scene ingested once; checksummed source object; COG output; resumable/idempotent processing run |
| 3 | Spatial candidate integration | One tile/scene matched against many assets; no duplicate candidates; boundary/model/run provenance retained |
| 4 | Detection validation | Frozen blind test set; authorised-work and negative samples; no look-ahead leakage; independent metrics and false-positive workload acceptance |
| 5 | Department workflow | End-to-end analyst, field, legal and officer acceptance with approved SOPs and jurisdiction routing |
| 6 | Production security and resilience | SSO/MFA, least privilege, runtime RLS verification, secrets/key management, monitoring, restore/DR and load/soak reports |
| 7 | Statewide rollout | Department-by-department data agreements, data stewards, refresh SLAs, training, support and operational sign-off |

### Immediate engineering backlog

1. Maintain a source-to-target schema map and canonical identity reconciliation report.
2. Add integration tests that execute under the actual non-owner, non-superuser, non-BYPASSRLS application role.
3. Define STAC item/collection mapping, object-key policy, retention and licence metadata.
4. Define versioned geospatial processing-run and candidate-output contracts.
5. Implement a small scene/tile vertical slice before broad model development.
6. Establish annotation, ground-truth and blind-backtest governance before selecting a production model.
7. Add model registry/evaluation only alongside reproducible datasets and promotion controls.
8. Define SSO, threat model, data classification, audit retention and secrets-management decisions.
9. Add deployment, observability, backup/restore and disaster-recovery runbooks.
10. Run measured capacity tests before final statewide infrastructure sizing.

## 9. Production-readiness and rollout constraints

The current codebase is a meaningful operational prototype, not a certified statewide production service. Do not enable automated enforcement or statewide legal alerts until all relevant gates are approved.

Required external decisions include:

- Data-sharing authority, source-system owners, licences and refresh SLAs.
- Competent authority and jurisdiction mapping for each asset class and geography.
- Legal validation of notifications, FTL/buffer definitions, parcel records, permitted works and due process.
- Government hosting, identity, security, privacy, retention and audit requirements.
- Satellite source/resolution/revisit suitability and procurement/licensing.
- Ground-truth availability, independent model validation and acceptable false-positive workload.
- Service ownership, support, incident response, disaster recovery and departmental operating procedures.

Scale figures elsewhere in this architecture pack are planning envelopes only. Benchmark actual geographic coverage, imagery cadence, asset count, concurrent users, tile traffic, retention and processing latency before procurement.

## 10. Change control

Future implementation pull requests must:

- Extend the canonical platform rather than add a competing domain implementation.
- Include migrations and rollback/compatibility considerations for schema changes.
- Preserve provenance and effective-dated history.
- Include tests for department isolation and asset-category policy where relevant.
- Keep AI output explicitly non-adjudicative.
- Update `PROGRESS.md` to distinguish implemented, tested, deployed and proposed work.
- Never mark a target component complete solely because a dependency, schema, placeholder or documentation entry exists.

This document supersedes conflicting architectural direction in earlier exploratory notes. Existing detailed documents remain valid where consistent; this document records the consolidated decision and current implementation boundary.
