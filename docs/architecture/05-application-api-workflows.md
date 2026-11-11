# 05 — Application, APIs and Workflows

## 1. Backend modules
Use a modular FastAPI application with clear domains. Deploy raster and ML workers separately.

| Module | Responsibility |
|---|---|
| Identity/access | Government SSO, users, roles, departments, jurisdiction and service accounts |
| Asset registry | Assets, categories, administrative hierarchy and asset-parcel links |
| Land records | Imported parcel/survey references, reconciliation and quality |
| Boundary management | Immutable versions, legal sources, approval and derived geometries |
| Satellite catalogue | STAC scenes, provider/licence and coverage |
| Ingestion orchestration | Adapters, jobs, retries, idempotency and status |
| Geospatial engine | Geometry validation, spatial joins, tiles and exports |
| Detection | Inference jobs, model registry and prediction records |
| Risk/triage | Transparent configurable prioritisation |
| Alert management | Queue, assignment, transitions, due dates and escalation |
| Case management | Field verification, legal review and officer decisions |
| Evidence | Source objects, hashes, manifests, packs and retention |
| Analytics | Dashboards, reports, coverage and workload metrics |
| Notifications | Approved gateways, outbox and delivery status |

## 2. Persona views
State dashboard: coverage, asset inventory, candidates, unresolved cases and department workload.
Department/district dashboard: only approved jurisdiction.
Asset 360: identity, parcels, responsibility, boundary history, imagery timeline, detections, field checks and cases.
GIS explorer: boundaries, source imagery, candidates and time slider.
Analyst desk: before/after review, source quality, legal context and reasoned disposition.
Field app: assigned tasks, offline capture, geotagged photos, GPS accuracy, sync and Telugu/English.
Legal/officer workspace: notices, hearings, orders, actions and case chronology.
Audit/reporting: action history, overdue work, monthly reports, model and data quality.

## 3. API conventions
Prefix APIs with /api/v1 and publish OpenAPI. Use UUIDs, cursor pagination, filters by category/department/jurisdiction/status/time/bbox, GeoJSON for geometry and vector tiles for map scale. Require idempotency keys for imports, field sync and action submission. Include correlation IDs and structured errors. Enforce request size, geometry vertex, area-of-interest and export limits. Expensive processing returns asynchronous job IDs.

Illustrative route groups:
- GET/POST /api/v1/assets; GET /assets/{id}; GET /assets/{id}/360
- GET /api/v1/parcels; GET/POST /api/v1/assets/{id}/boundaries
- GET/POST /api/v1/scenes; POST /api/v1/ingestion/jobs; GET /ingestion/jobs/{id}
- GET /api/v1/observations; GET/POST /api/v1/candidates
- GET/POST /api/v1/alerts; POST /alerts/{id}/assign; POST /alerts/{id}/transitions
- POST /alerts/{id}/field-verifications; POST /alerts/{id}/legal-review
- POST /alerts/{id}/officer-decision; GET/POST /api/v1/cases
- GET/POST /api/v1/evidence; GET /api/v1/reports and /analytics/*

These are target contracts. Preserve compatible existing routes and version breaking changes.

## 4. End-to-end workflow
**Asset onboarding:** import records; validate IDs/geometry/CRS; attach source documents; classify boundary authority; approve operational use; assign custodian, jurisdiction and department separately; set baseline and monitoring coverage.

**Observation:** ingest suitable imagery; run approved detection; create candidate with source/model lineage and date bracket; intersect against the boundary version effective at observation time; apply transparent triage; queue human review.

**Analyst:** confirm visible change, reject false detection, classify authorised/seasonal change or hold for insufficient evidence/boundary uncertainty. Require reason and audit every decision.

**Field:** route by configured jurisdiction/responsibility; assign safe field task; capture location, GPS accuracy, time, photos and outcome; support encrypted offline queue and idempotent sync.

**Legal/officer:** collect boundary, parcel, notification, permit, authorised-work, dispute and court references; display source date/authority/caveats; flag conflicts; provide evidence index; allow only authorised officers to record findings and action.

**Closure:** require reason and actor; use second-person approval for policy-defined high-risk closure types. Later observations can reopen a case under explicit rules while preserving prior closure history. Legal holds/stays take precedence according to approved rules.

## 5. Department routing
Never hardcode “lake = HYDRAA” or “government land = Revenue” as a universal rule. Resolve recipient from asset category, effective-dated jurisdiction, custodian, statutory source, case type, organisation structure and special agency arrangements. Store rule version, inputs, recipient and override reason. Competent legal/administrative owners approve the routing configuration.

## 6. Field and notification controls
PWA-first unless native capabilities are required. Offline storage is encrypted; submissions are idempotent; device and server times are separate; GPS accuracy and permission are recorded; photo hashes and metadata are preserved; Telugu strings receive native review. The app must state that an observation is not a survey and prohibit unauthorised entry onto private land.

Use transactional outbox for notifications. Record provider, attempt, delivery status and timestamps. Do not mark delivered merely because a gateway accepted a request. Citizen reporting is a later opt-in module requiring privacy, moderation and complaint-handling policy.

## 7. Analytics
Define each metric, query, denominator and time window. Separate asset/boundary coverage, candidates, analyst acceptance/rejection, field confirmation, legal/officer turnaround, overdue workload, evidence completeness and model performance. Do not claim prevented encroachments, savings or environmental outcomes without auditable measurement.