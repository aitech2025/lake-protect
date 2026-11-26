# GeoGuard — Solution Architecture

**Version:** 0.1.0-review | **Date:** 26 November 2026  
**Status:** Target architecture proposal; production design and technology choices subject to approval.

## 1. Architecture objectives

- Deliver a statewide, auditable geospatial intelligence platform without coupling every capability to satellite detection.
- Preserve trusted identity, boundary provenance, evidence chain of custody and human authority.
- Separate source ingestion, processing, domain workflow, presentation and integration.
- Support multiple asset categories and departments incrementally.
- Keep government connectors replaceable and disabled until authorized.
- Scale raster processing independently while keeping the business application a modular monolith initially.

## 2. System context

### Upstream sources
- Government departments: asset registers, cadastral/survey maps, legal notifications, GOs, FTL/buffer records, permits, court/dispute records.
- Earth observation: Sentinel-2 optical, Sentinel-1 radar, approved commercial archives/tasking and other licensed imagery.
- Citizens: web/mobile web and WhatsApp.
- Public social/news: approved APIs, licensed listening providers and public feeds.
- Administrative geography and approved GIS services.
- Messaging/notification providers.

### GeoGuard platform
- Intake and integration adapters.
- Validation and authoritative Asset Registry.
- Imagery catalogue, acquisition and processing.
- Physical-change detection and evidence generation.
- Intelligence intake, incident/case and inspection support.
- Evidence/document repository and audit.
- Dashboards, map, Asset 360, exports and read-only Copilot.
- High-resolution imagery request and provider tasking.

### Downstream consumers
- Authorized departmental users and leadership.
- GIS/remote-sensing analysts.
- Citizen submitters (limited safe status).
- Auditors and records/legal reviewers.
- Approved external systems through controlled APIs/adapters.

## 3. Logical architecture

```text
GOVERNMENT RECORDS     EARTH OBSERVATION       CITIZEN / PUBLIC SIGNALS
(asset, cadastral,     (Sentinel, commercial)  (web, WhatsApp, public APIs)
 legal, permits)                |                         |
       |                        |                         |
       v                        v                         v
+-------------------+  +--------------------+   +----------------------+
| Government Intake |  | Imagery Catalogue  |   | Intelligence Intake  |
| file/API adapters |  | archive/tasking    |   | citizen/social/news  |
+---------+---------+  +----------+---------+   +----------+-----------+
          |                       |                        |
          v                       v                        v
+-------------------+  +--------------------+   +----------------------+
| Validation & GIS  |  | QA / Preprocess    |   | Lead triage, privacy |
| review             |  | clip, COG, masks   |   | dedup, geolocation   |
+---------+---------+  +----------+---------+   +----------+-----------+
          |                       |                        |
          v                       v                        v
+-------------------+  +--------------------+   +----------------------+
| ASSET REGISTRY    |<-- spatial context -->| Detection / Evidence    |
| asset + boundary  |                       | physical change only   |
| versions + legal  |                       +-----------+------------+
+---------+---------+                                   |
          |                         +---------------------+
          |                         v
          |              +-----------------------------+
          +------------->| INCIDENT / CASE MANAGEMENT  |
                         | leads, incidents, cases,     |
                         | inspections, action records |
                         +---------------+-------------+
                                         |
                    +--------------------+--------------------+
                    v                    v                    v
             +-------------+      +-------------+      +---------------+
             | Evidence &  |      | Command     |      | Asset 360 &   |
             | Audit       |      | dashboards  |      | Read-only AI  |
             +-------------+      +-------------+      +---------------+
                                         ^
                                         |
                         +---------------+----------------+
                         | High-resolution imagery request|
                         | archive -> approval -> tasking  |
                         | acquisition -> reprocessing    |
                         +--------------------------------+
```

## 4. Proposed technology architecture

The following aligns with the current repository's technology foundations; final choices remain subject to engineering review.

| Layer | Proposed technology | Responsibility |
|---|---|---|
| Web UI | React, TypeScript, Tailwind/shadcn-style components | Admin, map desk, citizen web, dashboards, Asset 360 |
| Mapping | MapLibre GL JS | Vector/raster layers, time comparison, spatial interaction |
| API/application | Python FastAPI modular monolith | Domain APIs, auth, workflow, validation orchestration |
| Transactional data | PostgreSQL + PostGIS | Asset, boundaries, workflow, spatial query, audit metadata |
| Geospatial processing | Python, GDAL, Rasterio, GeoPandas/Shapely | Raster/vector processing, clipping, reprojection, geometry QA |
| ML/analytics | Python rule-based and ML/NLP components | Physical-change candidates, text/location extraction, scoring |
| Object storage | S3-compatible/object storage with versioning | Source imagery, uploads, evidence, derived COG/chips |
| Async work | Queue + worker processes; scheduler | Ingestion, imagery, processing, notifications, retries |
| Search/RAG | PostgreSQL full text initially; vector index only if justified | Legal document and evidence retrieval |
| Observability | Structured logs, metrics, traces and alerting | Operational health and audit support |
| Delivery | Containers, CI/CD, environment separation | Repeatable build, deployment and rollback |

Do not split the modular monolith into microservices until measured throughput, isolation, deployment cadence or team boundaries justify it. Raster workers can be separately scaled as processing workloads demand.

## 5. Domain boundaries and service responsibilities

1. **Identity & Access:** users, current roles, authorization policy, sessions, department/jurisdiction scope when approved.
2. **Asset Registry:** immutable identity, aliases, category, custodian, watch targets, candidate assets and asset lifecycle.
3. **Boundary & GIS:** boundary versions, CRS, topology, administrative geometry, survey parcels, GIS validation and approval references.
4. **Legal Records:** documents, permits, court matters, legal metadata and verification status.
5. **Source & Integration:** provider adapters, source registry, submissions, webhook validation, rate limits, retry and lineage.
6. **Imagery Catalogue:** products, observations, archive search, coverage and suitability.
7. **Geospatial Processing:** preprocessing, COGs, masks, change detection, spatial matching and reprocessing.
8. **Intelligence:** citizen submissions, social/news leads, duplicate clustering and triage.
9. **Incident & Case:** incidents, reviews, cases, links and workflow history.
10. **Inspection & Enforcement Support:** factual inspection records and authorized action references; role/workflow approval-gated.
11. **Evidence & Audit:** files, hashes, evidence packages, chain of custody and audit events.
12. **Notifications:** templates, preferences, consent, delivery status and retry.
13. **High-Resolution Requests:** archive-first search, approval, procurement, tasking and acquisition.
14. **Analytics & Copilot:** authorized metrics, structured queries, RAG citations and audit.
15. **Presentation:** command dashboards, map, Asset 360, exports and citizen status.

## 6. Canonical data model

### 6.1 Identity and geography
- `Asset(id UUID, asset_code UNIQUE, category, name, department_ref, custodian, lifecycle_status, created_at)`
- `AssetAlias(asset_id, language, alias, source)`
- `WatchTarget(id, geometry, source, created_by, status, optional_asset_id)`
- `CandidateAsset(id, geometry, origin_incident_id, match_status, verification_status)`
- `AssetBoundaryVersion(id, asset_id, boundary_kind, geometry, CRS, effective_from/to, source_id, authority_state, approved_by, supersedes_id)`
- `AdministrativeUnit(id, type, parent_id, official_code, names)`
- `SurveyParcel(id, survey_number, subdivision, geometry, land_category, source_id, verification_state)`

### 6.2 Submission and legal records
- `SubmissionPackage`, `SubmissionFile`, `ValidationRun`, `GISReview`, `LegalApproval`, `SourceRecord`
- `LegalDocument`, `PermitOrAuthorizedWork`, `CourtMatter`, `Dispute`

### 6.3 Imagery and detection
- `ImageryProvider`, `ImageryProduct`, `ImageryObservation`, `MonitoringSchedule`, `ProcessingRun`
- `Detection`, `DetectionEvidence`, `DetectionReview`

### 6.4 Intelligence and operations
- `CitizenSubmission`, `ConsentRecord`, `IntelligenceLead`, `Incident`, `IncidentReview`, `Case`, `CaseLink`, `Inspection`, `InspectionObservation`, `EnforcementAction`

### 6.5 Platform and procurement
- `EvidenceItem`, `EvidencePackage`, `AuditEvent`, `Notification`, `NotificationDelivery`, `IntegrationRun`, `HighResolutionImageryRequest`, `ProviderTask`, `CostApproval`, `CopilotQuery`, `CopilotReference`

Use UUID primary keys, database constraints and explicit state transitions. Use PostGIS geometry with explicit SRID. Use effective dates and immutable versions for legal/spatial records. Large files remain in object storage with metadata and cryptographic hash in PostgreSQL.

## 7. Key data flows

### 7.1 Department onboarding
Submission adapter → immutable raw file → virus/file checks → schema/CRS/geometry validation → GIS review → legal/administrative approval → registry identity and boundary version → monitoring activation.

### 7.2 Weekly monitoring
Scheduler → per-asset due list → archive search → observation suitability → acquire/cache → preprocess → detector → spatial association against applicable boundary version → detection/evidence record → review queue. A job execution and a usable imagery observation are separate records.

### 7.3 Citizen report
Portal/WhatsApp adapter → consent and attachment controls → incident ID → geocode/match → known asset link or candidate asset → duplicate/moderation checks → triage → case/inspection association under policy.

### 7.4 Social/news
Permitted source connector → source rights and timestamp capture → language/location extraction → duplicate clustering → unverified lead → human review → association/dismissal.

### 7.5 High-resolution imagery
Request → archive query → estimate/rights → approval → provider task → acquisition result → ingest/QA → reprocess → evidence link. Tasking and capture are separate outcomes.

### 7.6 Copilot
Authenticated user → policy context → permission-filtered structured query/RAG → source ranking → cited answer or abstention → prompt/reference/output audit. No write tool is exposed in the initial version.

## 8. Evidence and audit architecture

Every evidence object should carry:
- unique ID, source type, source URI/reference, source owner/provider and acquisition/capture timestamp;
- upload/processing timestamp, media type, size and cryptographic hash;
- parent/derived relationship and transformation lineage;
- associated asset, boundary version, observation, detection, incident, case or inspection;
- access classification, retention policy, legal hold where applicable;
- uploader/collector, verification state and audit events.

Evidence packages are manifests of immutable evidence references plus generated reports; they should not silently replace source objects. Hashing proves byte-level integrity after capture, not truth, legality or source authenticity. Chain-of-custody policy and signing requirements need legal approval.

## 9. Security and privacy

- Enforce authentication and authorization at API/service/data layers.
- Current approved app roles remain admin/viewer; do not assume expanded role model.
- Design department/jurisdiction scoping as policy dimensions, but activate only after RBAC and governance approval.
- Apply PostgreSQL RLS only with tested session context and service-role controls; migration/schema presence is not end-to-end proof.
- Encrypt transport and storage; manage secrets outside source code.
- Scan uploads, validate webhooks, rate-limit public endpoints and protect against SSRF/path traversal/malware.
- Minimize citizen PII, separate contact details from public incident summaries, and define consent/retention.
- Social sources must be permitted public/licensed sources; retain source terms and collection basis.
- Log sensitive reads, exports, approvals and administrative changes.
- Conduct threat modelling, VAPT, dependency scanning and incident-response testing before production.

## 10. Integration architecture

Use adapter interfaces with contract tests and explicit provider configuration. Government connectors are placeholders until authorized. Each integration must define identity, data contract, authentication, rate limits, retry/idempotency, error handling, provenance, freshness, legal basis and operational owner.

Do not scrape Bhu Bharati, CCLA or other portals or use third-party app data without authorization. Government-supplied exports and approved APIs are the intended integration boundary.

## 11. Deployment and environments

Proposed environments: local development, CI/test, demo/staging and production. Separate credentials, datasets, storage buckets and keys. Demo data must be labelled and isolated from operational summaries.

Deployment model, India hosting/residency, cloud/provider selection, network zones, HA, RPO/RTO, backup/restore and DR are open decisions. Production architecture must include private data plane, controlled public ingress, WAF/API protection, managed secrets, monitoring, vulnerability management and restore drills.

## 12. Operations

Monitor:
- scheduled run success and per-asset completion;
- imagery coverage, suitability and age of last usable observation;
- processing queue depth, latency, failures and retries;
- provider/API availability, quotas, licence expiry and cost;
- incident/lead review queue and ageing;
- storage growth, database health, backups and restore test;
- security events, privileged access and audit integrity.

Operational dashboards must distinguish a pipeline failure from no suitable imagery and no candidate detected.

## 13. Performance and scale design

Capacity-plan from expected asset count, AOI size, revisit frequency, raster volume, concurrent users, citizen submissions and evidence retention. Use spatial indexes, raster windowing/COGs, asynchronous workers, idempotent jobs, caching and partitioning where measurements justify them. Numeric SLOs are TBD.

## 14. Architecture risks

- Mixed authority boundary data: retain authority state and prevent unverified geometry from becoming legal ground truth.
- Provider variability: normalize metadata but preserve source-specific facts and rights.
- Detection uncertainty: independent blind backtest and manual review.
- Data leakage via Copilot: policy filtering before retrieval and tests for cross-scope leakage.
- Monolith coupling: domain boundaries and internal APIs, but no premature distributed transactions.
- Procurement uncertainty: archive-first high-resolution request lifecycle and cost approval.

## 15. Open architecture decisions

See [ADR register](GEOGUARD-ADR-REGISTER.md). This document is a target architecture and must be updated when decisions are approved or implementation diverges.
