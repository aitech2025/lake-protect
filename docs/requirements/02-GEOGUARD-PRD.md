# GeoGuard — Product Requirements Document (PRD)

**Version:** 0.1.0-review | **Date:** 26 November 2026  
**Status:** Proposed product baseline; approval pending.

## 1. Product definition

GeoGuard is a modular, map-first geospatial intelligence and case-support platform for government land and public-asset protection in Telangana. It unifies an authoritative Asset Registry, imagery observations, physical-change detections, citizen incidents, public-source intelligence leads, cases, inspections, evidence, dashboards, Asset 360, read-only AI Copilot and high-resolution imagery requests.

The product shall preserve the distinction between:
- **Asset:** formally registered government asset.
- **Watch Target:** location configured for monitoring, including an admin-drawn target; not necessarily an officially registered asset.
- **Candidate Asset:** proposed location arising from an unverified report or intelligence signal; not a registered government asset.
- **Detection:** machine-generated potential physical change from an observation.
- **Intelligence Lead:** unverified signal from citizen, social, news or other permitted source.
- **Incident:** intake/reviewable occurrence, potentially associated with an asset or candidate asset.
- **Case:** investigation/administrative matter that may relate to multiple incidents, detections and leads.
- **Inspection:** official factual site observation under an approved authority model.

## 2. Product principles

- Human authority remains central; software does not decide legality.
- Evidence and provenance are first-class data.
- Identity and boundary history are immutable/versioned.
- Separate source signal types; link them rather than flatten them.
- Distinguish no-change from no-observation.
- Make confidence, data freshness and limitations visible.
- Read-only Copilot initially.
- Modular monolith before any microservice decomposition.
- Government integration placeholders until formal authorization.
- Preserve demo/synthetic data isolation and labels.

## 3. User surfaces

1. Government/admin operations console.
2. Map-first state command dashboard.
3. Asset registry and Asset 360.
4. Detection and incident review queue.
5. Citizen web/mobile-web reporting portal.
6. WhatsApp channel adapter.
7. Public-source intelligence review workspace.
8. Case, inspection and enforcement-support workspace (subject to role/workflow approval).
9. High-resolution imagery request workspace.
10. Read-only AI Copilot.
11. System administration, audit and integration health views.

Current prototype roles remain `admin` and `viewer` under D-057. The UI may expose business workflows only to roles permitted by the current model. Do not introduce field roles or jurisdiction routing without approval.

## 4. Functional requirements

### 4.1 Asset Registry and onboarding

**PR-ASSET-001 — Permanent identity.** Assign each registered asset an immutable UUID and permanent human-readable GeoGuard Asset Code. Neither is reused after retirement, merge or split. The code must not encode mutable district/mandal/village/department attributes. Suggested pattern: `TG-LAKE-000001`; final category/code policy is open.

**PR-ASSET-002 — Separate asset classes.** Represent official registered assets, admin watch targets and candidate assets distinctly. Citizen-created candidates must never appear as verified government assets.

**PR-ASSET-003 — Intake formats.** Accept GeoPackage (preferred exchange), GeoJSON, Shapefile, KML/KMZ, CSV/XLSX, GeoTIFF and PDF. Preserve the original upload and checksum.

**PR-ASSET-004 — Validation.** Validate file integrity, CRS, geometry validity, self-intersections, empty geometry, duplicates, overlap/topology, area discrepancies, administrative references, survey-number structure and required metadata. Produce machine-readable and human-readable reports.

**PR-ASSET-005 — Review separation.** Technical validation, GIS review and legal/administrative approval are distinct recorded steps. A geometrically valid polygon is not automatically authoritative.

**PR-ASSET-006 — Provenance.** Retain source department, submitting officer/system, submission date, source reference, license/authority, original file hash, transformation history, validation report, reviewer, approval and rejection reasons.

**PR-ASSET-007 — Boundary versioning.** Store each boundary as a version with geometry, CRS, effective dates, source, author, reason, technical review, legal/administrative approval and supersession relation. Preserve prior versions and allow historical date queries.

**PR-ASSET-008 — Lifecycle.** Support a governed lifecycle (proposed: Draft, Submitted, Under Review, Registered, Active/Monitoring, Suspended, Transferred, Merged, Split, Retired). No physical deletion or identifier reuse. Final states and transition permissions require governance approval.

**PR-ASSET-009 — Asset profile.** Capture department asset reference, names/aliases in Telugu/English, category, custodian, district/mandal/village codes, survey/subdivision numbers, area/extent, geometry, CRS, legal references, monitoring status and supporting files.

**PR-ASSET-010 — Category coverage.** Model lakes/water bodies, FTL/buffer zones, government land, assigned land, endowment/Wakf/forest/public utility assets, government buildings, roads, canals, drains, parks and other notified public assets. Rollout per category is configurable and approval-gated.

### 4.2 Legal and document repository

**PR-DOC-001.** Attach legal/administrative records to assets, boundaries, incidents and cases.
**PR-DOC-002.** Capture document type, title, issuing authority, reference number, date, effective period, source, verification status, access classification and version.
**PR-DOC-003.** Support PDF and scanned documents with OCR/extraction metadata, confidence, page references and human verification.
**PR-DOC-004.** Preserve originals, hashes, versions and access audit. Do not treat OCR as an authoritative legal interpretation.
**PR-DOC-005.** Support GOs, notifications, title/custodianship records, cadastral/survey records, FTL/buffer declarations, court cases/disputes, encumbrances, permits and authorized works.

### 4.3 Imagery observation and monitoring

**PR-IMG-001 — Observation registry.** Store provider, collection/product ID, sensor/bands, acquisition and processing timestamps, GSD/resolution, cloud cover, coverage, quality, suitability, license/usage rights, AOI, lineage and status.

**PR-IMG-002 — Cadence.** Schedule weekly screening as the target cadence. Record each scheduled run independently from whether a suitable image was acquired. No promise of weekly clear imagery.

**PR-IMG-003 — Pipeline.** Scheduled run → source/archive search → acquisition/retrieval → QA → AOI clip → preprocessing → change analysis → spatial relationship → confidence/evidence → review queue.

**PR-IMG-004 — Observation states.** At minimum distinguish `candidate_found`, `no_candidate`, `no_usable_look`, `not_observed`, `failed`, `pending_acquisition` and `processing`. UI wording must never present no usable image as no change.

**PR-IMG-005 — Sensor strategy.** Support optical Sentinel-2 and radar Sentinel-1 foundations, with commercial providers as optional adapters. Sentinel-2 visible/NIR products commonly have 10 m bands; do not imply 30 cm capability. Resolution, revisit and rights are provider/product-specific.

**PR-IMG-006 — Evidence view.** Display before/after images, acquisition dates, resolution, cloud/quality, processing date, AOI coverage, boundary version, detector version, confidence and limitations.

**PR-IMG-007 — Change taxonomy.** Support potential construction/building, FTL/buffer construction, soil fill/dumping, water-spread reduction/expansion, vegetation removal/clearing, excavation/levelling, roads/paving, nala/channel obstruction, boundary-related changes and demolition/removal where evidence and detector capability exist. Taxonomy labels are physical observations, not legal findings.

**PR-IMG-008 — Spatial context.** Record intersection/adjacency, affected area, IoU or other spatial measures where appropriate, boundary kind/version and distance to relevant zone. Do not infer a legal violation from spatial overlap alone.

**PR-IMG-009 — Detector quality.** Track rule/model version, parameters, confidence, calibration and known limitations. Before accuracy claims, require independently verified case labels, frozen detector version, blind backtest, scored precision/recall/F1 and false-alert rate with documented limitations.

**PR-IMG-010 — Lineage.** Preserve source imagery references, derived chips/masks, processing runs, hashes and reprocessing lineage subject to licence/retention policy.

### 4.4 Detection, lead, incident, case and inspection separation

**PR-WF-001.** Detection, Intelligence Lead, Incident, Case and Inspection are separate entities with independent identifiers and lifecycles.

**PR-WF-002.** One asset may have multiple detections, leads and incidents over time. A case may relate to multiple incidents, detections and leads. Avoid forced one-to-one relationships.

**PR-WF-003.** A detection is a machine-generated candidate physical change and must include observation, detector version, geometry, confidence and evidence references.

**PR-WF-004.** An intelligence lead is an unverified external/citizen signal. It may be triaged, linked, dismissed or converted/associated with an incident under policy.

**PR-WF-005.** Incident workflow must remain compatible with current D-057 simple lifecycle unless owner approves change. Current repository baseline: OPEN → UNDER_REVIEW → CONFIRMED or DISMISSED → CLOSED, with system auto-close cases described in `docs/weekly-processing.md`. Citizen-facing status is distinct from internal notes.

**PR-WF-006.** Preserve status history, reviewer, decision, reason, timestamp and audit trail. Do not silently delete or overwrite reviews.

**PR-WF-007.** Case management shall support aggregation of relevant signals, legal records, evidence, review notes and inspection references. Detailed case states and assignment policy are open decisions.

**PR-WF-008.** Inspection is a separate official record containing location, time, factual observations, checklists, photographs/video, attachments, author/authority, correction addenda and review. An observation is not automatically a legal conclusion.

### 4.5 Citizen intelligence

**PR-CIT-001.** Provide citizen web/mobile-web and WhatsApp intake channels, subject to provider/legal approval.
**PR-CIT-002.** Capture location (map pin/GPS/address), category, description, date/time, photos/video/documents, language and optional contact details with consent.
**PR-CIT-003.** Generate an Incident ID and acknowledgement; expose citizen-safe status tracking.
**PR-CIT-004.** Link reports to known assets where match confidence is adequate; otherwise create an incident plus candidate asset. Do not auto-register an asset.
**PR-CIT-005.** Support duplicate detection, spam/abuse controls, attachment scanning, moderation, geocoding and location-confidence display.
**PR-CIT-006.** Preserve submitted content, consent, timestamps and evidence lineage; minimize PII and restrict access.
**PR-CIT-007.** Support Telugu and English initially; additional languages require prioritization and translation-quality review.
**PR-CIT-008.** Citizen status and messaging must not expose internal notes, restricted documents or unverified allegations.
**PR-CIT-009.** WhatsApp inbound/outbound provider state, webhook verification, retries and delivery receipts must be visible. Live provider integration remains incomplete in current audit.

### 4.6 Public social/news intelligence

**PR-SOC-001.** Ingest only permitted public sources, official APIs, licensed listening services or approved feeds; never bypass privacy/access controls.
**PR-SOC-002.** Store platform/source, public URL/reference, captured timestamp, post timestamp, text/media references, permitted author metadata, language, hashtags, keywords, geotags and source rights.
**PR-SOC-003.** Support keyword/hashtag themes such as #LakeEncroachment, #GovernmentLand, #LakeProtection, #LandGrabbing, #FTLViolation and #HyderabadLakes.
**PR-SOC-004.** Extract locations/entities and cluster duplicates; show extraction confidence.
**PR-SOC-005.** Every post is an unverified lead until corroborated. Do not infer guilt, ownership or intent from content or identity.
**PR-SOC-006.** Provide review, dismiss, link-to-asset, associate-to-incident/case actions with audit and retention/legal basis.
**PR-SOC-007.** Respect provider rate limits, licence, takedown and retention requirements.

### 4.7 Field operations and enforcement support

**PR-FIELD-001.** Product architecture shall reserve an inspection and enforcement-support domain.
**PR-FIELD-002.** Jurisdiction-aware roles, district/mandal routing and field-worker access are gated on explicit approval of expanded RBAC; current admin/viewer model remains authoritative.
**PR-FIELD-003.** When approved, capture GPS, timestamp, factual notes, photos/video, checklists, offline capture/sync, optional geofencing, supervisor review and inspection report.
**PR-FIELD-004.** Enforcement records may include notice/order type, issuing authority, reference, issue/service dates, action status, follow-up and closure evidence. Actual issuance/decision remains with competent authority.
**PR-FIELD-005.** Preserve append-only inspection facts and correction addenda. Do not silently edit historical observations.
**PR-FIELD-006.** Do not restore retired field app, officer assignment, two-person closure or escalation timers without separate owner approval.

### 4.8 Dashboards and Asset 360

**PR-DASH-001.** Provide state, district, mandal, village and asset-level views subject to data availability and access policy.
**PR-DASH-002.** KPIs include asset counts by class/status, candidate/watch targets, monitored status, imagery freshness/suitability, detections by type/confidence, review queues, incidents, social leads, inspections, enforcement records, legal records, data quality and ageing.
**PR-DASH-003.** Map layers include asset/boundary versions, survey/cadastral references, imagery, observations, change polygons, incidents, candidate assets, public intelligence and administrative boundaries.
**PR-DASH-004.** Provide layer toggles, filters, time slider, date comparison, AOI drawing and spatial query as capabilities are available.
**PR-DASH-005.** Clearly show not monitored, not observed, no usable imagery, processing delayed, failed and no candidate as distinct states.
**PR-ASSET360-001.** Asset 360 tabs/sections: identity, boundaries and versions, legal documents, imagery timeline, detections, incidents, cases, inspections, enforcement, monitoring health and audit.
**PR-ASSET360-002.** Historical view aligns observation date with boundary version effective at that date.
**PR-DASH-006.** Support PDF/CSV/XLSX/GeoJSON exports and official briefings/evidence packages with access controls and watermarking where policy requires.
**PR-DASH-007.** All charts/maps disclose data freshness, coverage and denominator.

### 4.9 AI Copilot

**PR-AI-001.** Initial Copilot is read-only.
**PR-AI-002.** Support natural-language structured queries and retrieval over authorized asset, imagery, detection, incident, case and legal-document data.
**PR-AI-003.** Example questions: lakes with >10% water-spread reduction; unresolved incidents; documents establishing FTL; compare imagery across two years; mandals with pending inspections; summarize an asset's history.
**PR-AI-004.** Every factual response includes citations to source record/document title and ID, date, page/paragraph where applicable, imagery observation date, asset/detection/case ID, freshness and limitations.
**PR-AI-005.** Enforce authorization at retrieval/query level, not merely in the UI. Prevent cross-department leakage.
**PR-AI-006.** Audit prompts, references, outputs, model/version and access decision with PII minimization.
**PR-AI-007.** Abstain when source support is absent or ambiguous. Distinguish retrieved fact, inference and unknown.
**PR-AI-008.** No writes, approvals, boundary edits, complaint decisions, notices, enforcement actions or legal conclusions.

### 4.10 High-resolution imagery request management

**PR-HR-001.** Provide a separate lifecycle: AOI/asset selection → purpose → archive search → quality/resolution/date/cloud assessment → cost/coverage/licence → approval → provider tasking → acquisition → ingestion → QA → processing/reprocessing → evidence linkage → completion/failure/cancellation.
**PR-HR-002.** Search existing archive first to avoid unnecessary purchases.
**PR-HR-003.** Record provider, product, tasking status, requested/actual acquisition, success/failure reason, cost, purchase order, licence, usage limits, expiry and delivery.
**PR-HR-004.** Tasking is not a guarantee of capture; show status and outcome explicitly.
**PR-HR-005.** Keep commercial high-resolution procurement separate from standard weekly monitoring.
**PR-HR-006.** Proposed states: Draft, Submitted, Review, Archive Search, Cost Approval, Approved, Tasked, Acquired, Ingested, Processing, Completed, Failed, Cancelled. Workflow and approval matrix need decision.

### 4.11 Notifications and integration

**PR-NOT-001.** Support configurable in-app, email, SMS and WhatsApp notification adapters, delivery state, retries, templates, preferences and consent. Channel priorities and SLAs are open.
**PR-INT-001.** Provide documented adapter contracts for departments, cadastral/survey systems, GIS services, satellite providers, public feeds, WhatsApp and notification gateways.
**PR-INT-002.** Until authorized, government integrations are mock/template adapters, visibly labelled as such. No live government API calls or scraping.
**PR-INT-003.** Integration health includes last success, failure, retry, source freshness, rate-limit state and data lineage.

## 5. Non-functional requirements

- **NFR-SEC-001 Security:** authentication, least privilege, role checks, secure sessions/tokens, secret management, API validation, encryption in transit/at rest and security logging.
- **NFR-SEC-002 Authorization:** department/jurisdiction isolation and row-level controls where approved; verify end-to-end, not only schema presence.
- **NFR-SEC-003 Audit:** append-only or tamper-evident audit for identity, access, review, approval, data changes and evidence export.
- **NFR-PRIV-001 Privacy:** data minimization, consent, PII classification, purpose limitation, retention/deletion policy and citizen privacy controls.
- **NFR-DATA-001 Data integrity:** referential integrity, immutable IDs, versioned boundaries, source lineage, checksums and reproducible processing.
- **NFR-GEO-001 Geospatial correctness:** explicit CRS, valid geometries, spatial indexes, topology checks and documented area/measurement CRS.
- **NFR-RES-001 Resilience:** retryable ingestion, idempotency, queue recovery, backup/restore, disaster recovery and provider outage handling.
- **NFR-PERF-001 Performance:** define response-time, throughput, raster processing and concurrency targets after workload sizing.
- **NFR-SCALE-001 Scale:** support statewide inventory and time-series observations through partitioning/indexing/object storage as measured; do not prematurely split into microservices.
- **NFR-UX-001 Accessibility:** responsive desktop/tablet/mobile, keyboard accessibility, readable maps/charts and multilingual UX.
- **NFR-OPS-001 Observability:** structured logs, metrics, traces, queue depth, job state, provider health and alerting.
- **NFR-DR-001 Continuity:** RPO/RTO, backup frequency, restore drills and HA topology require owner/security approval.
- **NFR-COMP-001 Compliance:** hosting/residency, retention, procurement, evidence admissibility and applicable government policies require legal/security review.

Numeric targets remain TBD until workload, agency SLAs and hosting decisions are approved.

## 6. Core data model

Minimum domain entities:
- Asset; AssetIdentifier; AssetAlias; AssetBoundaryVersion; AdministrativeUnit; SurveyParcel; WatchTarget; CandidateAsset.
- SubmissionPackage; ValidationRun; GISReview; LegalApproval; SourceRecord.
- LegalDocument; Permit/AuthorizedWork; CourtMatter/Dispute.
- ImageryProvider; ImageryProduct; ImageryObservation; ProcessingRun; MonitoringSchedule.
- Detection; DetectionEvidence; IntelligenceLead; Incident; IncidentReview; Case; CaseLink; Inspection; InspectionObservation; EnforcementAction.
- CitizenSubmission; ConsentRecord; Attachment; Message/Delivery.
- SocialSourceRecord; HighResolutionImageryRequest; ProviderTask; CostApproval.
- EvidenceItem; EvidencePackage; AuditEvent; Notification; IntegrationRun; CopilotQuery/Reference.

Use stable IDs, timestamps, provenance and explicit lifecycle state. Avoid storing all source signals in one generic incident table.

## 7. UX and content rules

- Use neutral, factual wording: “potential construction detected”, “possible soil fill”, “no suitable observation this week”.
- Avoid “illegal encroachment” or “violation” as machine-generated status.
- Show evidence and limitations adjacent to conclusions.
- Display boundary authority/status and source.
- Distinguish candidate asset from registered asset in map symbology, search and export.
- Show data freshness and observation gaps in dashboard summaries.
- Citizen-facing status must not leak internal notes or protected information.
- Provide Telugu and English initially; translation of legal content must preserve source text and identify machine translation.

## 8. Acceptance and release gates

**Gate A — Requirements and governance:** owner approves BRD/PRD, asset categories, RBAC, legal boundary authority, data sharing and retention.

**Gate B — Trusted registry:** import test pack passes schema/CRS/geometry checks; raw data and validation report retained; GIS and legal approval separated; immutable IDs and boundary history verified.

**Gate C — Monitoring integrity:** scheduled run creates one observation/monitoring record per asset/time window; no-usable-look is not labelled no-change; evidence lineage is reproducible.

**Gate D — Detection quality:** independent verified case set, frozen detector, blind scored backtest, precision/recall/F1 and false-alert rate with limitations; tuning comparison alone does not pass this gate.

**Gate E — Intelligence workflow:** citizen/social signals remain unverified until corroborated; unknown reports create candidate assets; duplicate, privacy and audit tests pass.

**Gate F — Operational readiness:** approved roles, security, VAPT, data isolation, backups/restore, observability, DR and department operating procedures validated.

**Gate G — AI and high-resolution procurement:** Copilot citations/permissions/abstention pass; imagery request lifecycle and financial/licence controls pass.

## 9. Release approach

- **R0 — Prototype baseline:** current lake-focused application, demo/data safeguards, current roles and existing workflows.
- **R1 — Trusted asset and boundary foundation:** permanent identity, submission package, versioned boundaries, legal/GIS approval separation.
- **R2 — Monitoring and detection assurance:** observation registry, weekly run completeness, evidence lineage, detector freeze and independent backtest.
- **R3 — Unified intelligence:** citizen incident and public social lead workflows with deduplication and candidate asset semantics.
- **R4 — Command and Asset 360:** statewide hierarchy, freshness-aware dashboards, exports and historical asset view.
- **R5 — Official field/case operations:** only after expanded RBAC and workflow approval.
- **R6 — Copilot and high-resolution imagery:** permissioned read-only RAG/analytics and procurement/tasking lifecycle.
- **R7 — Government integration and production hardening:** after formal agreements, security and operational approvals.

Release sequencing is proposed and must be reconciled with current implementation plan and owner's priority changes.

## 10. Open decisions

See [Architecture Decision Register](../architecture/GEOGUARD-ADR-REGISTER.md). No unselected option is silently finalized by this PRD.
