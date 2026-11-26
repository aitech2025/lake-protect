# GeoGuard Requirements Traceability Matrix (RTM)

**Document ID:** GG-RTM-001  
**Version:** 1.0  
**Status:** Engineering baseline — requires product-owner validation  
**Assessment date:** 26 November 2026  
**Repository:** [aitech2025/lake-protect](https://github.com/aitech2025/lake-protect)  
**PRD baseline:** [GEOGUARD-BRD-PRD.md](GEOGUARD-BRD-PRD.md)

## 1. Purpose

This RTM maps every functional requirement in the GeoGuard BRD/PRD to the current repository baseline, available implementation evidence, and the remaining work needed for acceptance. It is intended to support sprint planning, implementation sequencing, test planning and stakeholder reviews.

This is a source-based engineering assessment, not a production certification. A status of Implemented means the reviewed repository contains a working implementation and supporting evidence; it does not mean the capability is deployed, approved by a government authority or ready for statewide production. Where evidence is incomplete, the status is deliberately conservative.

## 2. Assessment baseline and constraints

The assessment uses the merged product baseline and repository artefacts available on 26 November 2026, including:

- `README.md`, `CONTEXT.md`, `PROGRESS.md`, `DECISIONS.md`.
- `docs/architecture/12-unified-architecture-decision-and-current-state.md`.
- `docs/architecture/08-implementation-foundation.md` through `11-legacy-domain-rls.md`.
- The BRD/PRD functional requirement catalogue.
- The command-centre UI redesign PR and its changed-file list.
- Recorded milestone test results in `PROGRESS.md`.

The current architecture is an existing React/TypeScript/MapLibre/PWA experience, FastAPI modular monolith, PostgreSQL/PostGIS operational data layer and Python worker. A canonical UUID-based statewide registry and department-scoped security foundations coexist with the legacy lake operational domain under a compatibility model. The target is additive evolution; a second backend or parallel asset/case lifecycle is not recommended.

**Important caveat:** the repository documentation records the citizen web portal as previously outside the original prototype scope, while the product owner has subsequently stated that the citizen web experience is implemented. Accordingly, citizen portal requirements are marked Partial pending a code-path/API/test audit. They must not be treated as fully accepted solely from that statement.

## 3. Status definitions

| Status | Meaning | Planning treatment |
|---|---|---|
| **Implemented** | Code path and supporting tests/evidence are present for the requirement's core behaviour. | Validate acceptance evidence and close remaining production gates. |
| **Partial** | A related foundation or narrower workflow exists, but one or more material parts of the requirement are missing. | Extend existing module; do not rebuild in parallel. |
| **Planned** | No sufficient implementation evidence was found in the reviewed baseline. | Create design/API/data tasks and implement. |
| **Blocked** | Implementation depends on an external approval, provider, credential, licence or data source not yet available. | Resolve dependency and owner before committing delivery dates. |

## 4. Executive coverage

**112 functional requirements assessed:** Implemented: 18, Partial: 45, Planned: 45, Blocked: 4.

| Functional area | Requirements | Implemented | Partial | Planned | Blocked |
|---|---:|---:|---:|---:|---:|
| Asset Registry & onboarding | 15 | 0 | 6 | 9 | 0 |
| GIS & boundaries | 7 | 5 | 2 | 0 | 0 |
| Legal records | 4 | 0 | 2 | 2 | 0 |
| Imagery & monitoring | 11 | 0 | 4 | 7 | 0 |
| Detection & alerts | 10 | 2 | 4 | 4 | 0 |
| Citizen reporting | 13 | 0 | 5 | 7 | 1 |
| Social intelligence | 9 | 0 | 0 | 6 | 3 |
| Field operations | 12 | 7 | 5 | 0 | 0 |
| Dashboards | 9 | 1 | 7 | 1 | 0 |
| Asset 360 | 5 | 0 | 5 | 0 | 0 |
| AI Copilot | 7 | 0 | 0 | 7 | 0 |
| Administration & audit | 10 | 3 | 5 | 2 | 0 |
| **Total** | **112** | **18** | **45** | **45** | **4** |

The totals are requirement counts, not weighted delivery percentages. P0/P1/P2 priorities are retained per requirement in the detailed matrix; a high proportion of Partial items means a foundation exists, not that the feature is ready for acceptance.

## 5. Functional requirements traceability

### FR-REG-001 — P0 — Partial

**Requirement:** System shall support department and source-authority registration with named data owners and authorised submitters.

**Existing implementation evidence:** Canonical UUID public-asset registry, department/responsibility model and provenance exist; full department submission/review workflow is not evidenced.

**Gap / next action:** Build department submission intake, schema/CRS validation, staged GIS/legal approvals and permanent-ID issuance; add attribute versioning and lifecycle lineage.

### FR-REG-002 — P0 — Planned

**Requirement:** System shall publish versioned data submission schemas, templates, field definitions and CRS requirements.

**Existing implementation evidence:** Canonical UUID public-asset registry, department/responsibility model and provenance exist; full department submission/review workflow is not evidenced.

**Gap / next action:** Build department submission intake, schema/CRS validation, staged GIS/legal approvals and permanent-ID issuance; add attribute versioning and lifecycle lineage.

### FR-REG-003 — P0 — Planned

**Requirement:** System shall accept approved vector, tabular, raster and document formats through controlled upload/API channels.

**Existing implementation evidence:** Canonical UUID public-asset registry, department/responsibility model and provenance exist; full department submission/review workflow is not evidenced.

**Gap / next action:** Build department submission intake, schema/CRS validation, staged GIS/legal approvals and permanent-ID issuance; add attribute versioning and lifecycle lineage.

### FR-REG-004 — P0 — Partial

**Requirement:** System shall preserve original submissions, source metadata, received time and cryptographic checksums.

**Existing implementation evidence:** Canonical UUID public-asset registry, department/responsibility model and provenance exist; full department submission/review workflow is not evidenced.

**Gap / next action:** Build department submission intake, schema/CRS validation, staged GIS/legal approvals and permanent-ID issuance; add attribute versioning and lifecycle lineage.

### FR-REG-005 — P0 — Planned

**Requirement:** System shall validate required fields, geometry validity, CRS, topology, duplicates and administrative geography.

**Existing implementation evidence:** Canonical UUID public-asset registry, department/responsibility model and provenance exist; full department submission/review workflow is not evidenced.

**Gap / next action:** Build department submission intake, schema/CRS validation, staged GIS/legal approvals and permanent-ID issuance; add attribute versioning and lifecycle lineage.

### FR-REG-006 — P0 — Planned

**Requirement:** System shall generate downloadable validation reports with errors, warnings and record-level references.

**Existing implementation evidence:** Canonical UUID public-asset registry, department/responsibility model and provenance exist; full department submission/review workflow is not evidenced.

**Gap / next action:** Build department submission intake, schema/CRS validation, staged GIS/legal approvals and permanent-ID issuance; add attribute versioning and lifecycle lineage.

### FR-REG-007 — P0 — Planned

**Requirement:** System shall support GIS and legal review as distinct approval stages.

**Existing implementation evidence:** Canonical UUID public-asset registry, department/responsibility model and provenance exist; full department submission/review workflow is not evidenced.

**Gap / next action:** Build department submission intake, schema/CRS validation, staged GIS/legal approvals and permanent-ID issuance; add attribute versioning and lifecycle lineage.

### FR-REG-008 — P0 — Partial

**Requirement:** System shall issue a unique permanent Asset ID only after configured approvals.

**Existing implementation evidence:** Canonical UUID public-asset registry, department/responsibility model and provenance exist; full department submission/review workflow is not evidenced.

**Gap / next action:** Build department submission intake, schema/CRS validation, staged GIS/legal approvals and permanent-ID issuance; add attribute versioning and lifecycle lineage.

### FR-REG-009 — P0 — Partial

**Requirement:** System shall prevent physical deletion and ID reuse for registered assets.

**Existing implementation evidence:** Canonical UUID public-asset registry, department/responsibility model and provenance exist; full department submission/review workflow is not evidenced.

**Gap / next action:** Build department submission intake, schema/CRS validation, staged GIS/legal approvals and permanent-ID issuance; add attribute versioning and lifecycle lineage.

### FR-REG-010 — P0 — Partial

**Requirement:** System shall version asset attributes and geometries with actor, reason, effective date and approval history.

**Existing implementation evidence:** Canonical UUID public-asset registry, department/responsibility model and provenance exist; full department submission/review workflow is not evidenced.

**Gap / next action:** Build department submission intake, schema/CRS validation, staged GIS/legal approvals and permanent-ID issuance; add attribute versioning and lifecycle lineage.

### FR-REG-011 — P1 — Planned

**Requirement:** System shall support asset merge, split, transfer, retirement and supersession with lineage links.

**Existing implementation evidence:** Canonical UUID public-asset registry, department/responsibility model and provenance exist; full department submission/review workflow is not evidenced.

**Gap / next action:** Build department submission intake, schema/CRS validation, staged GIS/legal approvals and permanent-ID issuance; add attribute versioning and lifecycle lineage.

### FR-REG-012 — P1 — Planned

**Requirement:** System shall support category-specific attributes and configurable validation rules.

**Existing implementation evidence:** Canonical UUID public-asset registry, department/responsibility model and provenance exist; full department submission/review workflow is not evidenced.

**Gap / next action:** Build department submission intake, schema/CRS validation, staged GIS/legal approvals and permanent-ID issuance; add attribute versioning and lifecycle lineage.

### FR-REG-013 — P1 — Planned

**Requirement:** System shall support bulk onboarding with row-level result reporting and resumable processing.

**Existing implementation evidence:** Canonical UUID public-asset registry, department/responsibility model and provenance exist; full department submission/review workflow is not evidenced.

**Gap / next action:** Build department submission intake, schema/CRS validation, staged GIS/legal approvals and permanent-ID issuance; add attribute versioning and lifecycle lineage.

### FR-REG-014 — P1 — Planned

**Requirement:** System shall identify potential duplicate assets for human resolution.

**Existing implementation evidence:** Canonical UUID public-asset registry, department/responsibility model and provenance exist; full department submission/review workflow is not evidenced.

**Gap / next action:** Build department submission intake, schema/CRS validation, staged GIS/legal approvals and permanent-ID issuance; add attribute versioning and lifecycle lineage.

### FR-REG-015 — P1 — Partial

**Requirement:** System shall support asset source-quality and legal-verification status indicators.

**Existing implementation evidence:** Canonical UUID public-asset registry, department/responsibility model and provenance exist; full department submission/review workflow is not evidenced.

**Gap / next action:** Build department submission intake, schema/CRS validation, staged GIS/legal approvals and permanent-ID issuance; add attribute versioning and lifecycle lineage.

### FR-GIS-001 — P0 — Partial

**Requirement:** System shall store authoritative geometries with explicit CRS/SRID and source provenance.

**Existing implementation evidence:** PostGIS/GeoAlchemy2 geometry model, versioned boundaries, MapLibre layers and spatial matching are present. Some category-wide metadata/status handling remains incomplete.

**Gap / next action:** Complete authoritative/source status UX and category-specific spatial QA; preserve source geometry and boundary version in every downstream record.

### FR-GIS-002 — P0 — Implemented

**Requirement:** System shall support polygon, multipolygon, line and point geometries as appropriate to asset category.

**Existing implementation evidence:** PostGIS/GeoAlchemy2 geometry model, versioned boundaries, MapLibre layers and spatial matching are present. Some category-wide metadata/status handling remains incomplete.

**Gap / next action:** Complete authoritative/source status UX and category-specific spatial QA; preserve source geometry and boundary version in every downstream record.

### FR-GIS-003 — P0 — Implemented

**Requirement:** System shall display asset boundaries and configured spatial overlays on the map.

**Existing implementation evidence:** PostGIS/GeoAlchemy2 geometry model, versioned boundaries, MapLibre layers and spatial matching are present. Some category-wide metadata/status handling remains incomplete.

**Gap / next action:** Complete authoritative/source status UX and category-specific spatial QA; preserve source geometry and boundary version in every downstream record.

### FR-GIS-004 — P0 — Partial

**Requirement:** System shall distinguish official, proposed, derived, unverified and superseded geometries visually and in metadata.

**Existing implementation evidence:** PostGIS/GeoAlchemy2 geometry model, versioned boundaries, MapLibre layers and spatial matching are present. Some category-wide metadata/status handling remains incomplete.

**Gap / next action:** Complete authoritative/source status UX and category-specific spatial QA; preserve source geometry and boundary version in every downstream record.

### FR-GIS-005 — P0 — Implemented

**Requirement:** System shall prevent machine detections from modifying authoritative geometries.

**Existing implementation evidence:** PostGIS/GeoAlchemy2 geometry model, versioned boundaries, MapLibre layers and spatial matching are present. Some category-wide metadata/status handling remains incomplete.

**Gap / next action:** Complete authoritative/source status UX and category-specific spatial QA; preserve source geometry and boundary version in every downstream record.

### FR-GIS-006 — P1 — Implemented

**Requirement:** System shall support spatial intersection, proximity, containment and area calculations with stated measurement CRS/method.

**Existing implementation evidence:** PostGIS/GeoAlchemy2 geometry model, versioned boundaries, MapLibre layers and spatial matching are present. Some category-wide metadata/status handling remains incomplete.

**Gap / next action:** Complete authoritative/source status UX and category-specific spatial QA; preserve source geometry and boundary version in every downstream record.

### FR-GIS-007 — P1 — Implemented

**Requirement:** System shall retain boundary version history and effective dates.

**Existing implementation evidence:** PostGIS/GeoAlchemy2 geometry model, versioned boundaries, MapLibre layers and spatial matching are present. Some category-wide metadata/status handling remains incomplete.

**Gap / next action:** Complete authoritative/source status UX and category-specific spatial QA; preserve source geometry and boundary version in every downstream record.

### FR-LEG-001 — P0 — Partial

**Requirement:** System shall attach legal/administrative documents to assets and boundary versions.

**Existing implementation evidence:** Legacy legal checks, permits, authorised works and court references exist; a general asset-linked legal document library/index is not evidenced.

**Gap / next action:** Implement a versioned document repository linked to assets/boundary versions, with access classes, OCR indexing and page citations.

### FR-LEG-002 — P0 — Partial

**Requirement:** System shall record document type, authority, reference number, dates, verification status and checksum.

**Existing implementation evidence:** Legacy legal checks, permits, authorised works and court references exist; a general asset-linked legal document library/index is not evidenced.

**Gap / next action:** Implement a versioned document repository linked to assets/boundary versions, with access classes, OCR indexing and page citations.

### FR-LEG-003 — P1 — Planned

**Requirement:** System shall support document supersession, restricted access and review workflows.

**Existing implementation evidence:** Legacy legal checks, permits, authorised works and court references exist; a general asset-linked legal document library/index is not evidenced.

**Gap / next action:** Implement a versioned document repository linked to assets/boundary versions, with access classes, OCR indexing and page citations.

### FR-LEG-004 — P1 — Planned

**Requirement:** System shall provide a searchable legal-document index and page-level references where available.

**Existing implementation evidence:** Legacy legal checks, permits, authorised works and court references exist; a general asset-linked legal document library/index is not evidenced.

**Gap / next action:** Implement a versioned document repository linked to assets/boundary versions, with access classes, OCR indexing and page citations.

### FR-IMG-001 — P0 — Planned

**Requirement:** System shall maintain an imagery catalogue with provider, sensor, acquisition time, footprint, resolution, quality and licence metadata.

**Existing implementation evidence:** Observation records and synthetic demo image pairs exist. Production STAC catalogue, provider ingestion and scheduled acquisition are not evidenced.

**Gap / next action:** Build provider adapters and STAC catalogue; add acquisition scheduler, suitability/coverage states, licence tracking and real imagery timeline. Wire imagery request approval and fulfilment.

### FR-IMG-002 — P0 — Partial

**Requirement:** System shall associate observations with intersecting assets and areas of interest.

**Existing implementation evidence:** Observation records and synthetic demo image pairs exist. Production STAC catalogue, provider ingestion and scheduled acquisition are not evidenced.

**Gap / next action:** Build provider adapters and STAC catalogue; add acquisition scheduler, suitability/coverage states, licence tracking and real imagery timeline. Wire imagery request approval and fulfilment.

### FR-IMG-003 — P0 — Partial

**Requirement:** System shall distinguish acquisition time, ingestion time and processing time.

**Existing implementation evidence:** Observation records and synthetic demo image pairs exist. Production STAC catalogue, provider ingestion and scheduled acquisition are not evidenced.

**Gap / next action:** Build provider adapters and STAC catalogue; add acquisition scheduler, suitability/coverage states, licence tracking and real imagery timeline. Wire imagery request approval and fulfilment.

### FR-IMG-004 — P0 — Planned

**Requirement:** System shall support per-asset monitoring policies and configurable schedules.

**Existing implementation evidence:** Observation records and synthetic demo image pairs exist. Production STAC catalogue, provider ingestion and scheduled acquisition are not evidenced.

**Gap / next action:** Build provider adapters and STAC catalogue; add acquisition scheduler, suitability/coverage states, licence tracking and real imagery timeline. Wire imagery request approval and fulfilment.

### FR-IMG-005 — P0 — Planned

**Requirement:** System shall record scheduled, attempted, acquired, unsuitable, unavailable and failed monitoring outcomes.

**Existing implementation evidence:** Observation records and synthetic demo image pairs exist. Production STAC catalogue, provider ingestion and scheduled acquisition are not evidenced.

**Gap / next action:** Build provider adapters and STAC catalogue; add acquisition scheduler, suitability/coverage states, licence tracking and real imagery timeline. Wire imagery request approval and fulfilment.

### FR-IMG-006 — P0 — Planned

**Requirement:** System shall not infer no change when no suitable observation exists.

**Existing implementation evidence:** Observation records and synthetic demo image pairs exist. Production STAC catalogue, provider ingestion and scheduled acquisition are not evidenced.

**Gap / next action:** Build provider adapters and STAC catalogue; add acquisition scheduler, suitability/coverage states, licence tracking and real imagery timeline. Wire imagery request approval and fulfilment.

### FR-IMG-007 — P1 — Planned

**Requirement:** System shall support multiple optical and SAR sources where licensed and technically integrated.

**Existing implementation evidence:** Observation records and synthetic demo image pairs exist. Production STAC catalogue, provider ingestion and scheduled acquisition are not evidenced.

**Gap / next action:** Build provider adapters and STAC catalogue; add acquisition scheduler, suitability/coverage states, licence tracking and real imagery timeline. Wire imagery request approval and fulfilment.

### FR-IMG-008 — P1 — Partial

**Requirement:** System shall support baseline/current imagery timeline and visual comparison when paired imagery exists.

**Existing implementation evidence:** Observation records and synthetic demo image pairs exist. Production STAC catalogue, provider ingestion and scheduled acquisition are not evidenced.

**Gap / next action:** Build provider adapters and STAC catalogue; add acquisition scheduler, suitability/coverage states, licence tracking and real imagery timeline. Wire imagery request approval and fulfilment.

### FR-IMG-009 — P1 — Partial

**Requirement:** System shall support imagery request creation, approval, provider tracking and delivery validation.

**Existing implementation evidence:** Observation records and synthetic demo image pairs exist. Production STAC catalogue, provider ingestion and scheduled acquisition are not evidenced.

**Gap / next action:** Build provider adapters and STAC catalogue; add acquisition scheduler, suitability/coverage states, licence tracking and real imagery timeline. Wire imagery request approval and fulfilment.

### FR-IMG-010 — P1 — Planned

**Requirement:** System shall record provider licence and permitted use for each imagery asset.

**Existing implementation evidence:** Observation records and synthetic demo image pairs exist. Production STAC catalogue, provider ingestion and scheduled acquisition are not evidenced.

**Gap / next action:** Build provider adapters and STAC catalogue; add acquisition scheduler, suitability/coverage states, licence tracking and real imagery timeline. Wire imagery request approval and fulfilment.

### FR-IMG-011 — P2 — Planned

**Requirement:** System shall optimise acquisition and processing by geography, priority, provider coverage and cost.

**Existing implementation evidence:** Observation records and synthetic demo image pairs exist. Production STAC catalogue, provider ingestion and scheduled acquisition are not evidenced.

**Gap / next action:** Build provider adapters and STAC catalogue; add acquisition scheduler, suitability/coverage states, licence tracking and real imagery timeline. Wire imagery request approval and fulfilment.

### FR-DET-001 — P0 — Planned

**Requirement:** System shall execute configured detection rules against suitable imagery observations.

**Existing implementation evidence:** Candidate/observation ingest, spatial reconciliation and alert state machine exist. Production imagery-driven detection/backtesting remains incomplete.

**Gap / next action:** Implement production scene/tile processing and validated detection rules; retain run/model/observation/boundary lineage, separate confidence dimensions and blind backtests.

### FR-DET-002 — P0 — Partial

**Requirement:** System shall retain source observation IDs, algorithm/rule version and processing provenance for each detection.

**Existing implementation evidence:** Candidate/observation ingest, spatial reconciliation and alert state machine exist. Production imagery-driven detection/backtesting remains incomplete.

**Gap / next action:** Implement production scene/tile processing and validated detection rules; retain run/model/observation/boundary lineage, separate confidence dimensions and blind backtests.

### FR-DET-003 — P0 — Partial

**Requirement:** System shall store detection geometry, class, observed time window and separate confidence dimensions.

**Existing implementation evidence:** Candidate/observation ingest, spatial reconciliation and alert state machine exist. Production imagery-driven detection/backtesting remains incomplete.

**Gap / next action:** Implement production scene/tile processing and validated detection rules; retain run/model/observation/boundary lineage, separate confidence dimensions and blind backtests.

### FR-DET-004 — P0 — Implemented

**Requirement:** System shall spatially relate detections to assets, approved boundaries and configured buffers.

**Existing implementation evidence:** Candidate/observation ingest, spatial reconciliation and alert state machine exist. Production imagery-driven detection/backtesting remains incomplete.

**Gap / next action:** Implement production scene/tile processing and validated detection rules; retain run/model/observation/boundary lineage, separate confidence dimensions and blind backtests.

### FR-DET-005 — P0 — Implemented

**Requirement:** System shall create reviewable alerts according to configurable severity and deduplication rules.

**Existing implementation evidence:** Candidate/observation ingest, spatial reconciliation and alert state machine exist. Production imagery-driven detection/backtesting remains incomplete.

**Gap / next action:** Implement production scene/tile processing and validated detection rules; retain run/model/observation/boundary lineage, separate confidence dimensions and blind backtests.

### FR-DET-006 — P0 — Partial

**Requirement:** System shall support analyst validation, dismissal, escalation and request-for-imagery decisions with notes.

**Existing implementation evidence:** Candidate/observation ingest, spatial reconciliation and alert state machine exist. Production imagery-driven detection/backtesting remains incomplete.

**Gap / next action:** Implement production scene/tile processing and validated detection rules; retain run/model/observation/boundary lineage, separate confidence dimensions and blind backtests.

### FR-DET-007 — P1 — Planned

**Requirement:** System shall group related detections across repeated observations into an evolving event.

**Existing implementation evidence:** Candidate/observation ingest, spatial reconciliation and alert state machine exist. Production imagery-driven detection/backtesting remains incomplete.

**Gap / next action:** Implement production scene/tile processing and validated detection rules; retain run/model/observation/boundary lineage, separate confidence dimensions and blind backtests.

### FR-DET-008 — P1 — Partial

**Requirement:** System shall support alert thresholds and rules by asset category and department.

**Existing implementation evidence:** Candidate/observation ingest, spatial reconciliation and alert state machine exist. Production imagery-driven detection/backtesting remains incomplete.

**Gap / next action:** Implement production scene/tile processing and validated detection rules; retain run/model/observation/boundary lineage, separate confidence dimensions and blind backtests.

### FR-DET-009 — P1 — Planned

**Requirement:** System shall provide model/rule performance monitoring and reviewer feedback capture.

**Existing implementation evidence:** Candidate/observation ingest, spatial reconciliation and alert state machine exist. Production imagery-driven detection/backtesting remains incomplete.

**Gap / next action:** Implement production scene/tile processing and validated detection rules; retain run/model/observation/boundary lineage, separate confidence dimensions and blind backtests.

### FR-DET-010 — P2 — Planned

**Requirement:** System shall support model retraining and champion/challenger evaluation through governed ML operations.

**Existing implementation evidence:** Candidate/observation ingest, spatial reconciliation and alert state machine exist. Production imagery-driven detection/backtesting remains incomplete.

**Gap / next action:** Implement production scene/tile processing and validated detection rules; retain run/model/observation/boundary lineage, separate confidence dimensions and blind backtests.

### FR-CIT-001 — P0 — Partial

**Requirement:** Citizen portal shall accept report category, description, location and supporting media.

**Existing implementation evidence:** Citizen-facing web experience is reported as implemented, but the repo baseline still lacks a fully evidenced citizen incident lifecycle and WhatsApp integration.

**Gap / next action:** Complete citizen incident API/state machine, acknowledgement and secure tracking; reviewer decisions/notes, duplicate linking and upload abuse controls. Integrate WhatsApp after approved provider credentials and webhook setup.

### FR-CIT-002 — P0 — Partial

**Requirement:** System shall generate a unique Incident ID and acknowledgement for each accepted submission.

**Existing implementation evidence:** Citizen-facing web experience is reported as implemented, but the repo baseline still lacks a fully evidenced citizen incident lifecycle and WhatsApp integration.

**Gap / next action:** Complete citizen incident API/state machine, acknowledgement and secure tracking; reviewer decisions/notes, duplicate linking and upload abuse controls. Integrate WhatsApp after approved provider credentials and webhook setup.

### FR-CIT-003 — P0 — Partial

**Requirement:** System shall record channel, received time, location provenance and consent/privacy metadata.

**Existing implementation evidence:** Citizen-facing web experience is reported as implemented, but the repo baseline still lacks a fully evidenced citizen incident lifecycle and WhatsApp integration.

**Gap / next action:** Complete citizen incident API/state machine, acknowledgement and secure tracking; reviewer decisions/notes, duplicate linking and upload abuse controls. Integrate WhatsApp after approved provider credentials and webhook setup.

### FR-CIT-004 — P0 — Planned

**Requirement:** System shall support incident review decisions: acknowledge, accept, decline and request information.

**Existing implementation evidence:** Citizen-facing web experience is reported as implemented, but the repo baseline still lacks a fully evidenced citizen incident lifecycle and WhatsApp integration.

**Gap / next action:** Complete citizen incident API/state machine, acknowledgement and secure tracking; reviewer decisions/notes, duplicate linking and upload abuse controls. Integrate WhatsApp after approved provider credentials and webhook setup.

### FR-CIT-005 — P0 — Planned

**Requirement:** Every review decision shall capture actor, timestamp, reason and notes.

**Existing implementation evidence:** Citizen-facing web experience is reported as implemented, but the repo baseline still lacks a fully evidenced citizen incident lifecycle and WhatsApp integration.

**Gap / next action:** Complete citizen incident API/state machine, acknowledgement and secure tracking; reviewer decisions/notes, duplicate linking and upload abuse controls. Integrate WhatsApp after approved provider credentials and webhook setup.

### FR-CIT-006 — P0 — Partial

**Requirement:** Citizen shall be able to track the status of their own report using authenticated access or an approved secure tracking method.

**Existing implementation evidence:** Citizen-facing web experience is reported as implemented, but the repo baseline still lacks a fully evidenced citizen incident lifecycle and WhatsApp integration.

**Gap / next action:** Complete citizen incident API/state machine, acknowledgement and secure tracking; reviewer decisions/notes, duplicate linking and upload abuse controls. Integrate WhatsApp after approved provider credentials and webhook setup.

### FR-CIT-007 — P0 — Partial

**Requirement:** System shall associate incidents with existing assets where confidence and review policy permit.

**Existing implementation evidence:** Citizen-facing web experience is reported as implemented, but the repo baseline still lacks a fully evidenced citizen incident lifecycle and WhatsApp integration.

**Gap / next action:** Complete citizen incident API/state machine, acknowledgement and secure tracking; reviewer decisions/notes, duplicate linking and upload abuse controls. Integrate WhatsApp after approved provider credentials and webhook setup.

### FR-CIT-008 — P0 — Planned

**Requirement:** System shall create a candidate asset verification task—not an approved Asset ID—when a report concerns an unregistered location.

**Existing implementation evidence:** Citizen-facing web experience is reported as implemented, but the repo baseline still lacks a fully evidenced citizen incident lifecycle and WhatsApp integration.

**Gap / next action:** Complete citizen incident API/state machine, acknowledgement and secure tracking; reviewer decisions/notes, duplicate linking and upload abuse controls. Integrate WhatsApp after approved provider credentials and webhook setup.

### FR-CIT-009 — P1 — Blocked

**Requirement:** System shall integrate WhatsApp Business or another approved messaging provider for inbound reports and status messages.

**Existing implementation evidence:** Citizen-facing web experience is reported as implemented, but the repo baseline still lacks a fully evidenced citizen incident lifecycle and WhatsApp integration.

**Gap / next action:** Complete citizen incident API/state machine, acknowledgement and secure tracking; reviewer decisions/notes, duplicate linking and upload abuse controls. Integrate WhatsApp after approved provider credentials and webhook setup.

### FR-CIT-010 — P1 — Planned

**Requirement:** System shall detect possible duplicate incidents and allow reviewer linking without deleting submissions.

**Existing implementation evidence:** Citizen-facing web experience is reported as implemented, but the repo baseline still lacks a fully evidenced citizen incident lifecycle and WhatsApp integration.

**Gap / next action:** Complete citizen incident API/state machine, acknowledgement and secure tracking; reviewer decisions/notes, duplicate linking and upload abuse controls. Integrate WhatsApp after approved provider credentials and webhook setup.

### FR-CIT-011 — P1 — Planned

**Requirement:** System shall support request-for-more-information and citizen response handling.

**Existing implementation evidence:** Citizen-facing web experience is reported as implemented, but the repo baseline still lacks a fully evidenced citizen incident lifecycle and WhatsApp integration.

**Gap / next action:** Complete citizen incident API/state machine, acknowledgement and secure tracking; reviewer decisions/notes, duplicate linking and upload abuse controls. Integrate WhatsApp after approved provider credentials and webhook setup.

### FR-CIT-012 — P1 — Planned

**Requirement:** System shall provide configurable citizen-safe closure and status messages.

**Existing implementation evidence:** Citizen-facing web experience is reported as implemented, but the repo baseline still lacks a fully evidenced citizen incident lifecycle and WhatsApp integration.

**Gap / next action:** Complete citizen incident API/state machine, acknowledgement and secure tracking; reviewer decisions/notes, duplicate linking and upload abuse controls. Integrate WhatsApp after approved provider credentials and webhook setup.

### FR-CIT-013 — P1 — Planned

**Requirement:** System shall apply rate limits, abuse controls, spam review and malware scanning to uploads.

**Existing implementation evidence:** Citizen-facing web experience is reported as implemented, but the repo baseline still lacks a fully evidenced citizen incident lifecycle and WhatsApp integration.

**Gap / next action:** Complete citizen incident API/state machine, acknowledgement and secure tracking; reviewer decisions/notes, duplicate linking and upload abuse controls. Integrate WhatsApp after approved provider credentials and webhook setup.

### FR-SOC-001 — P1 — Blocked

**Requirement:** System shall support configurable keywords, hashtags, languages, sources and geographic themes.

**Existing implementation evidence:** No approved social listening connector, source register, NLP/geocoding pipeline or review queue is evidenced.

**Gap / next action:** Obtain legal/platform approval and provider access; then implement configurable source monitoring, provenance, NLP place extraction, geocoding confidence and human-review queue.

### FR-SOC-002 — P1 — Blocked

**Requirement:** Collection shall use approved APIs, licensed providers or other legally authorised public-source methods.

**Existing implementation evidence:** No approved social listening connector, source register, NLP/geocoding pipeline or review queue is evidenced.

**Gap / next action:** Obtain legal/platform approval and provider access; then implement configurable source monitoring, provenance, NLP place extraction, geocoding confidence and human-review queue.

### FR-SOC-003 — P1 — Planned

**Requirement:** System shall preserve source references, publication and collection timestamps and collection provenance.

**Existing implementation evidence:** No approved social listening connector, source register, NLP/geocoding pipeline or review queue is evidenced.

**Gap / next action:** Obtain legal/platform approval and provider access; then implement configurable source monitoring, provenance, NLP place extraction, geocoding confidence and human-review queue.

### FR-SOC-004 — P1 — Planned

**Requirement:** NLP shall classify relevance and extract candidate place names, survey references and location descriptions.

**Existing implementation evidence:** No approved social listening connector, source register, NLP/geocoding pipeline or review queue is evidenced.

**Gap / next action:** Obtain legal/platform approval and provider access; then implement configurable source monitoring, provenance, NLP place extraction, geocoding confidence and human-review queue.

### FR-SOC-005 — P1 — Planned

**Requirement:** System shall geocode candidate locations and expose geocoding confidence and ambiguity.

**Existing implementation evidence:** No approved social listening connector, source register, NLP/geocoding pipeline or review queue is evidenced.

**Gap / next action:** Obtain legal/platform approval and provider access; then implement configurable source monitoring, provenance, NLP place extraction, geocoding confidence and human-review queue.

### FR-SOC-006 — P1 — Planned

**Requirement:** Social leads shall enter a human-review queue before conversion to an incident or case.

**Existing implementation evidence:** No approved social listening connector, source register, NLP/geocoding pipeline or review queue is evidenced.

**Gap / next action:** Obtain legal/platform approval and provider access; then implement configurable source monitoring, provenance, NLP place extraction, geocoding confidence and human-review queue.

### FR-SOC-007 — P1 — Planned

**Requirement:** System shall link related posts and incidents while retaining original source references.

**Existing implementation evidence:** No approved social listening connector, source register, NLP/geocoding pipeline or review queue is evidenced.

**Gap / next action:** Obtain legal/platform approval and provider access; then implement configurable source monitoring, provenance, NLP place extraction, geocoding confidence and human-review queue.

### FR-SOC-008 — P1 — Blocked

**Requirement:** System shall enforce source terms, retention rules, privacy and access restrictions.

**Existing implementation evidence:** No approved social listening connector, source register, NLP/geocoding pipeline or review queue is evidenced.

**Gap / next action:** Obtain legal/platform approval and provider access; then implement configurable source monitoring, provenance, NLP place extraction, geocoding confidence and human-review queue.

### FR-SOC-009 — P2 — Planned

**Requirement:** System shall provide trend summaries by topic and geography without profiling private individuals.

**Existing implementation evidence:** No approved social listening connector, source register, NLP/geocoding pipeline or review queue is evidenced.

**Gap / next action:** Obtain legal/platform approval and provider access; then implement configurable source monitoring, provenance, NLP place extraction, geocoding confidence and human-review queue.

### FR-FLD-001 — P0 — Partial

**Requirement:** Authorised users shall create an inspection task from an alert, incident, case or asset.

**Existing implementation evidence:** Existing field PWA supports assigned alerts, offline capture/sync, GPS, notes, photos and hashes. Generalised incident/case inspection workflow needs extension.

**Gap / next action:** Generalise existing alert field checks into inspection tasks from incidents/cases/assets; add supervisor review/clarification and citizen-safe progress updates.

### FR-FLD-002 — P0 — Partial

**Requirement:** System shall support assignment by department, district, mandal and officer.

**Existing implementation evidence:** Existing field PWA supports assigned alerts, offline capture/sync, GPS, notes, photos and hashes. Generalised incident/case inspection workflow needs extension.

**Gap / next action:** Generalise existing alert field checks into inspection tasks from incidents/cases/assets; add supervisor review/clarification and citizen-safe progress updates.

### FR-FLD-003 — P0 — Implemented

**Requirement:** Inspector shall see assigned task, location, asset context and available evidence.

**Existing implementation evidence:** Existing field PWA supports assigned alerts, offline capture/sync, GPS, notes, photos and hashes. Generalised incident/case inspection workflow needs extension.

**Gap / next action:** Generalise existing alert field checks into inspection tasks from incidents/cases/assets; add supervisor review/clarification and citizen-safe progress updates.

### FR-FLD-004 — P0 — Implemented

**Requirement:** Inspector shall submit observations, notes, visit times and photo/document evidence.

**Existing implementation evidence:** Existing field PWA supports assigned alerts, offline capture/sync, GPS, notes, photos and hashes. Generalised incident/case inspection workflow needs extension.

**Gap / next action:** Generalise existing alert field checks into inspection tasks from incidents/cases/assets; add supervisor review/clarification and citizen-safe progress updates.

### FR-FLD-005 — P0 — Implemented

**Requirement:** System shall retain original uploaded evidence and integrity metadata.

**Existing implementation evidence:** Existing field PWA supports assigned alerts, offline capture/sync, GPS, notes, photos and hashes. Generalised incident/case inspection workflow needs extension.

**Gap / next action:** Generalise existing alert field checks into inspection tasks from incidents/cases/assets; add supervisor review/clarification and citizen-safe progress updates.

### FR-FLD-006 — P0 — Partial

**Requirement:** Inspection report shall support submit, review, request clarification and accept/reject workflow.

**Existing implementation evidence:** Existing field PWA supports assigned alerts, offline capture/sync, GPS, notes, photos and hashes. Generalised incident/case inspection workflow needs extension.

**Gap / next action:** Generalise existing alert field checks into inspection tasks from incidents/cases/assets; add supervisor review/clarification and citizen-safe progress updates.

### FR-FLD-007 — P0 — Implemented

**Requirement:** System shall maintain full task status and reassignment history.

**Existing implementation evidence:** Existing field PWA supports assigned alerts, offline capture/sync, GPS, notes, photos and hashes. Generalised incident/case inspection workflow needs extension.

**Gap / next action:** Generalise existing alert field checks into inspection tasks from incidents/cases/assets; add supervisor review/clarification and citizen-safe progress updates.

### FR-FLD-008 — P1 — Implemented

**Requirement:** Mobile field experience shall support low-bandwidth and intermittent-connectivity operation.

**Existing implementation evidence:** Existing field PWA supports assigned alerts, offline capture/sync, GPS, notes, photos and hashes. Generalised incident/case inspection workflow needs extension.

**Gap / next action:** Generalise existing alert field checks into inspection tasks from incidents/cases/assets; add supervisor review/clarification and citizen-safe progress updates.

### FR-FLD-009 — P1 — Implemented

**Requirement:** System shall capture GPS accuracy and distinguish device capture metadata from server receipt time.

**Existing implementation evidence:** Existing field PWA supports assigned alerts, offline capture/sync, GPS, notes, photos and hashes. Generalised incident/case inspection workflow needs extension.

**Gap / next action:** Generalise existing alert field checks into inspection tasks from incidents/cases/assets; add supervisor review/clarification and citizen-safe progress updates.

### FR-FLD-010 — P1 — Partial

**Requirement:** System shall record official action references, notices and outcomes entered by authorised officers.

**Existing implementation evidence:** Existing field PWA supports assigned alerts, offline capture/sync, GPS, notes, photos and hashes. Generalised incident/case inspection workflow needs extension.

**Gap / next action:** Generalise existing alert field checks into inspection tasks from incidents/cases/assets; add supervisor review/clarification and citizen-safe progress updates.

### FR-FLD-011 — P1 — Implemented

**Requirement:** System shall support escalation and overdue inspection reminders.

**Existing implementation evidence:** Existing field PWA supports assigned alerts, offline capture/sync, GPS, notes, photos and hashes. Generalised incident/case inspection workflow needs extension.

**Gap / next action:** Generalise existing alert field checks into inspection tasks from incidents/cases/assets; add supervisor review/clarification and citizen-safe progress updates.

### FR-FLD-012 — P1 — Partial

**Requirement:** System shall provide citizen-safe status updates without disclosing protected investigation details.

**Existing implementation evidence:** Existing field PWA supports assigned alerts, offline capture/sync, GPS, notes, photos and hashes. Generalised incident/case inspection workflow needs extension.

**Gap / next action:** Generalise existing alert field checks into inspection tasks from incidents/cases/assets; add supervisor review/clarification and citizen-safe progress updates.

### FR-DASH-001 — P0 — Partial

**Requirement:** System shall provide a statewide command dashboard.

**Existing implementation evidence:** Map-first command overview and monthly officer report exist; complete statewide/district/mandal aggregation and coverage reporting are not yet evidenced.

**Gap / next action:** Add hierarchy-aware state/district/mandal/village aggregates, coverage/freshness indicators, filters, trends and governed exports.

### FR-DASH-002 — P0 — Partial

**Requirement:** System shall support drill-down by district, mandal, village and asset.

**Existing implementation evidence:** Map-first command overview and monthly officer report exist; complete statewide/district/mandal aggregation and coverage reporting are not yet evidenced.

**Gap / next action:** Add hierarchy-aware state/district/mandal/village aggregates, coverage/freshness indicators, filters, trends and governed exports.

### FR-DASH-003 — P0 — Partial

**Requirement:** Dashboard shall expose asset inventory, monitoring coverage, alerts, incidents and inspection workload.

**Existing implementation evidence:** Map-first command overview and monthly officer report exist; complete statewide/district/mandal aggregation and coverage reporting are not yet evidenced.

**Gap / next action:** Add hierarchy-aware state/district/mandal/village aggregates, coverage/freshness indicators, filters, trends and governed exports.

### FR-DASH-004 — P0 — Partial

**Requirement:** Dashboard filters shall include department, asset category, jurisdiction, severity and date range.

**Existing implementation evidence:** Map-first command overview and monthly officer report exist; complete statewide/district/mandal aggregation and coverage reporting are not yet evidenced.

**Gap / next action:** Add hierarchy-aware state/district/mandal/village aggregates, coverage/freshness indicators, filters, trends and governed exports.

### FR-DASH-005 — P0 — Implemented

**Requirement:** Map selections shall open the relevant asset, alert or incident details subject to permissions.

**Existing implementation evidence:** Map-first command overview and monthly officer report exist; complete statewide/district/mandal aggregation and coverage reporting are not yet evidenced.

**Gap / next action:** Add hierarchy-aware state/district/mandal/village aggregates, coverage/freshness indicators, filters, trends and governed exports.

### FR-DASH-006 — P1 — Partial

**Requirement:** System shall provide trends, ageing, SLA/target performance and department comparisons.

**Existing implementation evidence:** Map-first command overview and monthly officer report exist; complete statewide/district/mandal aggregation and coverage reporting are not yet evidenced.

**Gap / next action:** Add hierarchy-aware state/district/mandal/village aggregates, coverage/freshness indicators, filters, trends and governed exports.

### FR-DASH-007 — P1 — Partial

**Requirement:** System shall provide exportable, permission-filtered reports with generation metadata.

**Existing implementation evidence:** Map-first command overview and monthly officer report exist; complete statewide/district/mandal aggregation and coverage reporting are not yet evidenced.

**Gap / next action:** Add hierarchy-aware state/district/mandal/village aggregates, coverage/freshness indicators, filters, trends and governed exports.

### FR-DASH-008 — P1 — Partial

**Requirement:** System shall distinguish live counts, demo data, stale data and unavailable data.

**Existing implementation evidence:** Map-first command overview and monthly officer report exist; complete statewide/district/mandal aggregation and coverage reporting are not yet evidenced.

**Gap / next action:** Add hierarchy-aware state/district/mandal/village aggregates, coverage/freshness indicators, filters, trends and governed exports.

### FR-DASH-009 — P1 — Planned

**Requirement:** Senior-officer reports shall include data coverage and caveats to avoid misleading conclusions.

**Existing implementation evidence:** Map-first command overview and monthly officer report exist; complete statewide/district/mandal aggregation and coverage reporting are not yet evidenced.

**Gap / next action:** Add hierarchy-aware state/district/mandal/village aggregates, coverage/freshness indicators, filters, trends and governed exports.

### FR-A360-001 — P0 — Partial

**Requirement:** Each registered asset shall have a consolidated Asset 360 page.

**Existing implementation evidence:** Asset detail and boundary history exist, but a unified Asset 360 timeline across legal files, imagery, incidents, inspections and actions is incomplete.

**Gap / next action:** Compose existing asset, boundary, legal, observation, alert, incident, inspection, evidence and audit services into a permission-aware timeline.

### FR-A360-002 — P0 — Partial

**Requirement:** Asset 360 shall show identity, geography, department, current approved boundary and verification status.

**Existing implementation evidence:** Asset detail and boundary history exist, but a unified Asset 360 timeline across legal files, imagery, incidents, inspections and actions is incomplete.

**Gap / next action:** Compose existing asset, boundary, legal, observation, alert, incident, inspection, evidence and audit services into a permission-aware timeline.

### FR-A360-003 — P0 — Partial

**Requirement:** Asset 360 shall show legal documents, imagery observations, detections, incidents, inspections and actions.

**Existing implementation evidence:** Asset detail and boundary history exist, but a unified Asset 360 timeline across legal files, imagery, incidents, inspections and actions is incomplete.

**Gap / next action:** Compose existing asset, boundary, legal, observation, alert, incident, inspection, evidence and audit services into a permission-aware timeline.

### FR-A360-004 — P0 — Partial

**Requirement:** Asset 360 shall show historical versions and audit history to authorised users.

**Existing implementation evidence:** Asset detail and boundary history exist, but a unified Asset 360 timeline across legal files, imagery, incidents, inspections and actions is incomplete.

**Gap / next action:** Compose existing asset, boundary, legal, observation, alert, incident, inspection, evidence and audit services into a permission-aware timeline.

### FR-A360-005 — P1 — Partial

**Requirement:** Asset 360 shall provide an imagery timeline and comparison when valid imagery pairs exist.

**Existing implementation evidence:** Asset detail and boundary history exist, but a unified Asset 360 timeline across legal files, imagery, incidents, inspections and actions is incomplete.

**Gap / next action:** Compose existing asset, boundary, legal, observation, alert, incident, inspection, evidence and audit services into a permission-aware timeline.

### FR-AI-001 — P1 — Planned

**Requirement:** Copilot shall accept natural-language questions about assets, incidents, monitoring and legal documents.

**Existing implementation evidence:** No permission-aware natural-language Copilot or grounded legal-document retrieval is evidenced.

**Gap / next action:** Build read-only RAG plus structured PostGIS queries with row-level permission filtering, document/page citations, uncertainty and curated evaluation.

### FR-AI-002 — P1 — Planned

**Requirement:** Copilot shall enforce the same access permissions as the underlying application.

**Existing implementation evidence:** No permission-aware natural-language Copilot or grounded legal-document retrieval is evidenced.

**Gap / next action:** Build read-only RAG plus structured PostGIS queries with row-level permission filtering, document/page citations, uncertainty and curated evaluation.

### FR-AI-003 — P1 — Planned

**Requirement:** Copilot answers shall cite source records and document/page references where available.

**Existing implementation evidence:** No permission-aware natural-language Copilot or grounded legal-document retrieval is evidenced.

**Gap / next action:** Build read-only RAG plus structured PostGIS queries with row-level permission filtering, document/page citations, uncertainty and curated evaluation.

### FR-AI-004 — P1 — Planned

**Requirement:** Copilot shall distinguish authoritative records, machine detections, citizen reports and social leads.

**Existing implementation evidence:** No permission-aware natural-language Copilot or grounded legal-document retrieval is evidenced.

**Gap / next action:** Build read-only RAG plus structured PostGIS queries with row-level permission filtering, document/page citations, uncertainty and curated evaluation.

### FR-AI-005 — P1 — Planned

**Requirement:** Copilot shall state uncertainty and missing data rather than fabricate an answer.

**Existing implementation evidence:** No permission-aware natural-language Copilot or grounded legal-document retrieval is evidenced.

**Gap / next action:** Build read-only RAG plus structured PostGIS queries with row-level permission filtering, document/page citations, uncertainty and curated evaluation.

### FR-AI-006 — P1 — Planned

**Requirement:** Initial Copilot shall be read-only and shall not approve, modify or issue official actions.

**Existing implementation evidence:** No permission-aware natural-language Copilot or grounded legal-document retrieval is evidenced.

**Gap / next action:** Build read-only RAG plus structured PostGIS queries with row-level permission filtering, document/page citations, uncertainty and curated evaluation.

### FR-AI-007 — P2 — Planned

**Requirement:** Copilot may prepare draft summaries or reports for human review, clearly labelled as AI-generated.

**Existing implementation evidence:** No permission-aware natural-language Copilot or grounded legal-document retrieval is evidenced.

**Gap / next action:** Build read-only RAG plus structured PostGIS queries with row-level permission filtering, document/page citations, uncertainty and curated evaluation.

### FR-ADM-001 — P0 — Implemented

**Requirement:** System shall support role-based and jurisdiction-scoped access control.

**Existing implementation evidence:** JWT/database-derived roles, department RLS, audit chain and outbox foundations exist; government SSO, external notifications and approved retention policy remain open.

**Gap / next action:** Complete policy configuration, in-app notifications, provider delivery/status, retention/legal holds and auditor export controls; validate under production runtime identities.

### FR-ADM-002 — P0 — Partial

**Requirement:** System shall support configurable departments, jurisdictions, asset categories and workflow rules.

**Existing implementation evidence:** JWT/database-derived roles, department RLS, audit chain and outbox foundations exist; government SSO, external notifications and approved retention policy remain open.

**Gap / next action:** Complete policy configuration, in-app notifications, provider delivery/status, retention/legal holds and auditor export controls; validate under production runtime identities.

### FR-ADM-003 — P0 — Implemented

**Requirement:** System shall record audit events for governed create, update, approval, rejection, assignment, access and export actions.

**Existing implementation evidence:** JWT/database-derived roles, department RLS, audit chain and outbox foundations exist; government SSO, external notifications and approved retention policy remain open.

**Gap / next action:** Complete policy configuration, in-app notifications, provider delivery/status, retention/legal holds and auditor export controls; validate under production runtime identities.

### FR-ADM-004 — P0 — Implemented

**Requirement:** Audit events shall include actor/service identity, timestamp, action, target, outcome and correlation reference.

**Existing implementation evidence:** JWT/database-derived roles, department RLS, audit chain and outbox foundations exist; government SSO, external notifications and approved retention policy remain open.

**Gap / next action:** Complete policy configuration, in-app notifications, provider delivery/status, retention/legal holds and auditor export controls; validate under production runtime identities.

### FR-ADM-005 — P0 — Partial

**Requirement:** System shall prevent ordinary users from editing or deleting audit events.

**Existing implementation evidence:** JWT/database-derived roles, department RLS, audit chain and outbox foundations exist; government SSO, external notifications and approved retention policy remain open.

**Gap / next action:** Complete policy configuration, in-app notifications, provider delivery/status, retention/legal holds and auditor export controls; validate under production runtime identities.

### FR-ADM-006 — P0 — Partial

**Requirement:** System shall provide in-app notifications for relevant assignments and decisions.

**Existing implementation evidence:** JWT/database-derived roles, department RLS, audit chain and outbox foundations exist; government SSO, external notifications and approved retention policy remain open.

**Gap / next action:** Complete policy configuration, in-app notifications, provider delivery/status, retention/legal holds and auditor export controls; validate under production runtime identities.

### FR-ADM-007 — P1 — Planned

**Requirement:** System shall support approved email/SMS/WhatsApp notification providers and templates.

**Existing implementation evidence:** JWT/database-derived roles, department RLS, audit chain and outbox foundations exist; government SSO, external notifications and approved retention policy remain open.

**Gap / next action:** Complete policy configuration, in-app notifications, provider delivery/status, retention/legal holds and auditor export controls; validate under production runtime identities.

### FR-ADM-008 — P1 — Partial

**Requirement:** System shall support notification delivery status, retries and dead-letter handling.

**Existing implementation evidence:** JWT/database-derived roles, department RLS, audit chain and outbox foundations exist; government SSO, external notifications and approved retention policy remain open.

**Gap / next action:** Complete policy configuration, in-app notifications, provider delivery/status, retention/legal holds and auditor export controls; validate under production runtime identities.

### FR-ADM-009 — P1 — Planned

**Requirement:** System shall support configurable retention and legal hold policies.

**Existing implementation evidence:** JWT/database-derived roles, department RLS, audit chain and outbox foundations exist; government SSO, external notifications and approved retention policy remain open.

**Gap / next action:** Complete policy configuration, in-app notifications, provider delivery/status, retention/legal holds and auditor export controls; validate under production runtime identities.

### FR-ADM-010 — P1 — Partial

**Requirement:** System shall provide audit export and evidence integrity verification to authorised auditors.

**Existing implementation evidence:** JWT/database-derived roles, department RLS, audit chain and outbox foundations exist; government SSO, external notifications and approved retention policy remain open.

**Gap / next action:** Complete policy configuration, in-app notifications, provider delivery/status, retention/legal holds and auditor export controls; validate under production runtime identities.


## 6. Cross-cutting implementation evidence

### 6.1 Implemented foundations to preserve

| Capability | Evidence in repository | RTM implication |
|---|---|---|
| Application foundation | React, TypeScript, Vite, React Router, MapLibre, PWA; FastAPI, SQLAlchemy, Alembic, GeoAlchemy2; PostgreSQL/PostGIS | Extend existing modular application and GIS model |
| Asset/boundary core | Asset APIs, boundary history, append-only boundary protections, geometry versioning and spatial queries | Reuse for canonical asset onboarding and version governance |
| Workflow and alerts | Candidate ingest, legal checks, priority factors, 24-rule state machine, timers/escalation, role-based transitions | Extend alert workflow for broader incident/case intake |
| Field PWA | IndexedDB offline queue, idempotent sync, GPS accuracy, capture/server timestamps, photo hashes, English/Telugu | Reuse field capture and add inspection task abstraction |
| Evidence | Versioned evidence packs, SHA-256 manifest, verification command, PDF/ZIP export | Extend evidence lineage to citizen/social/imagery inputs |
| Officer action/reporting | Officer records, monthly bulletin, overdue list and PDF | Extend to multi-department hierarchy and statewide KPIs |
| Audit/security | Hash-linked audit chain, JWT/live-user checks, department RLS, pipeline authentication and outbox | Complete government identity federation, key management and external audit anchoring |
| Storage/events | Local/S3-compatible object storage adapter and durable outbox dispatcher | Add production bucket config, consumers and integration contract tests |
| Command UI | Map-first command overview, layers, alert inspector, theme modes, measurement and comparison controls | Treat as shell/foundation; build remaining module pages and workflows |

### 6.2 Explicitly incomplete or not production-proven

- Production Sentinel-1/Sentinel-2 discovery, acquisition and ingestion.
- STAC/pgSTAC catalogue operation and scene/tile raster preprocessing.
- Validated detection model/rule performance, blind historical backtest and independent evaluation.
- Scheduled weekly observation execution; a schedule must not be represented as a guarantee of suitable weekly imagery.
- Citizen incident lifecycle and WhatsApp integration end-to-end; citizen web code requires focused verification.
- Approved social listening provider/API, lawful collection basis and geolocation pipeline.
- Generic legal-document library, OCR/page-citation and access-classification workflow.
- Full state/district/mandal/village drill-down dashboard.
- Unified Asset 360 timeline.
- Permission-aware AI Copilot and grounded legal-document retrieval.
- Government SSO/MFA, production secrets/key management, HA/DR, security certification and statewide operational acceptance.

## 7. Recommended delivery sequence

The sequence below is dependency-aware. It does not simply follow the PRD section order.

| Increment | Scope | Requirements primarily addressed | Exit evidence |
|---|---|---|---|
| **R0 — Baseline verification** | Confirm merged branch, inspect citizen portal code paths, API routes, migrations and tests; reconcile canonical vs legacy IDs | All | Signed-off code inventory and updated RTM evidence links |
| **R1 — Registry & department onboarding** | Department data submission, schema/CRS validation, staging, GIS/legal review, approval, permanent ID, boundary/attribute versions | REG, GIS, LEG, ADM | End-to-end department package accepted/rejected with audit and permanent ID only after approval |
| **R2 — Legal records & Asset 360 foundation** | Document repository/index, access classes, asset timeline and version replay | LEG, A360, GIS | Asset page shows sourced legal files, boundaries and complete historical changes |
| **R3 — Imagery platform vertical slice** | One approved source adapter, STAC catalogue, scene metadata, storage, quality gates, COG and monitoring attempt states | IMG | One scene ingested once, processed reproducibly and associated with multiple assets |
| **R4 — Detection & alert validation** | Detection rules, provenance, confidence dimensions, deduplication, reviewer workbench, blind backtest | DET, IMG, GIS | Reproducible detections on frozen test set; measured precision/recall and review workload |
| **R5 — Citizen incident lifecycle** | Verify/complete web portal, incident API/state machine, acknowledgement, review decisions, secure tracking, duplicate linking | CIT, ADM, DASH | Citizen report tracked end-to-end with role-isolated internal notes |
| **R6 — WhatsApp channel** | Approved WhatsApp Business provider, inbound webhook, media handling, status templates and retries | CIT, ADM | Verified inbound and outbound contract tests using approved provider credentials |
| **R7 — Social intelligence** | Approved sources, configurable keywords, provenance, NLP place extraction, geocoding and human triage | SOC, CIT | Source-compliant leads enter review queue with location confidence and source traceability |
| **R8 — Field operations generalisation** | Task abstraction across alerts/incidents/cases/assets, supervisor review, citizen-safe status | FLD, CIT | Field task closed with complete evidence, audit and citizen-safe status |
| **R9 — Statewide dashboards** | State/district/mandal/village hierarchy, workload/coverage KPIs, filters, stale-data caveats and exports | DASH, ADM | Role-scoped dashboard totals reconcile with underlying records |
| **R10 — Copilot** | Permission-aware RAG + structured GIS queries, source/page citations, uncertainty and evaluation | AI, A360, ADM | Adversarial permission tests and grounded-answer evaluation pass |
| **R11 — Production readiness** | SSO/MFA, runtime RLS tests, KMS/secrets, HA/DR, observability, load/security/privacy reviews | ADM and NFRs | Government security and operations sign-off |

### Recommended first engineering increment

Start with **R0 + R1**, not the AI or social-media features. The platform needs a trusted and governed Asset Registry before it can reliably associate imagery detections, citizen reports, social leads and field actions with official assets.

R0 is deliberately a short verification gate: the citizen web portal is stated to exist, and it should be inspected before deciding whether its requirements are implemented or partial. R1 then creates the common government data onboarding foundation on which the remaining workflows depend.

## 8. Key cross-requirement dependencies

| Dependency | Blocks or constrains | Required decision / owner |
|---|---|---|
| Department source data, codes and sharing agreement | REG, GIS, LEG, A360, dashboards | Nodal department and data owners |
| Legal boundary authority and effective dates | REG, GIS, LEG, DET, A360 | Competent legal/department authority |
| Imagery licence, provider access and budget | IMG, DET, monitoring coverage | GIS authority and procurement |
| Ground-truth and backtest cases | DET, model promotion | Programme owner and independent reviewer |
| WhatsApp Business account, webhook and template approval | CIT messaging | Citizen-channel owner and provider |
| Approved social APIs/licences and lawful basis | SOC | Legal, communications and IT |
| Official identity federation and jurisdiction master | ADM, all protected workflows | Government IT/security |
| Retention, legal hold and privacy policy | CIT, SOC, FLD, LEG, ADM | Records officer, legal and privacy stakeholders |
| District/mandal/village master data | REG, DASH, routing | State data governance |
| Document OCR/indexing and access classification | LEG, A360, AI | Legal records custodian |

## 9. Test and acceptance traceability

Each requirement should ultimately link to one or more automated tests and an acceptance artefact. Minimum test classes:

1. **API contract tests:** required fields, state transitions, idempotency, validation errors and version conflicts.
2. **Database invariants:** no asset-ID reuse, no hard delete, append-only audit/evidence/boundary history, correct RLS.
3. **GIS tests:** CRS handling, invalid geometry, spatial joins, boundary-version replay and measurement method.
4. **Workflow tests:** submit/review/approve/decline/reassign/escalate/close with separation of duties.
5. **Channel tests:** citizen web, WhatsApp webhook signature, duplicate delivery, media validation and secure tracking.
6. **Imagery tests:** missing/unsuitable scenes, acquisition-vs-ingestion time, provider errors, licence metadata and idempotent reprocessing.
7. **Detection tests:** frozen blind test set, negative/authorised-work samples, no look-ahead leakage and confidence calibration.
8. **Field tests:** offline capture, retry/idempotent sync, evidence hash integrity and server/device timestamp separation.
9. **Dashboard tests:** hierarchy aggregation reconciles with source records; permissions filter counts and exports.
10. **Copilot tests:** access-control adversarial cases, source citation validity, uncertainty handling and no unsupported legal conclusions.
11. **Operational tests:** restore, DR, queue retry/dead-letter, observability and load/soak tests.

A requirement is only moved to Implemented after its acceptance test and evidence link are recorded. A UI screen without its API, persistence, authorisation and tests does not satisfy the requirement.

## 10. Governance and maintenance

- Keep requirement IDs stable; do not recycle IDs.
- Every code PR should reference the FR IDs it implements or changes.
- Every status change must cite a code path, test, PR or accepted external dependency.
- Review this RTM at each release and at least once per sprint during active delivery.
- Record owner, target increment, issue/PR and test evidence in the engineering tracker.
- If a requirement is descoped, retain it in the RTM with an approved disposition; do not delete it.
- Keep the BRD/PRD as the business baseline and this RTM as the implementation traceability view.

## 11. Source documents

- [BRD/PRD](GEOGUARD-BRD-PRD.md)
- [Government data onboarding specification](GOVERNMENT-DATA-ONBOARDING-SPEC.md)
- [Architecture index](../architecture/README.md)
- [Unified architecture decision and current implementation status](../architecture/12-unified-architecture-decision-and-current-state.md)
- [Repository progress](../../PROGRESS.md)
- [Repository decisions](../../DECISIONS.md)
