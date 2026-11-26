# Telangana GeoGuard — Business Requirements & Product Requirements Document

**Document ID:** GG-BRD-PRD-001  
**Version:** 1.0  
**Status:** Product baseline for stakeholder validation  
**Date:** 26 November 2026  
**Product:** Telangana GeoGuard (working name)  
**Repository:** aitech2025/lake-protect

> This document defines the proposed statewide product capability and target operating model. It is not a statement that every capability is already implemented. Refer to the implementation status and release roadmap below; production integrations, legal authority, procurement, data-sharing agreements and operational policies require government approval.

---

## 1. Executive summary

Telangana GeoGuard is a government-wide geospatial asset protection and intelligence platform. It establishes a trusted registry of public assets and their authoritative spatial/legal records, continuously screens available earth-observation imagery for physical changes, accepts intelligence from citizens and permitted public sources, coordinates official field verification, and provides decision support through dashboards and an AI-assisted natural-language interface.

The platform is designed to expand beyond lakes to government land parcels, parks, public buildings, roads, canals, nalas, feeder channels and other notified public assets.

The core product principle is **one authoritative Asset Registry with multiple intelligence channels**. Government-submitted records establish the asset inventory. Satellite detections, citizen complaints and social-media leads are separate observations or reports that may be associated with an asset. They must not independently alter an asset's legal identity, ownership or approved boundary.

GeoGuard supports officials; it does not determine title, establish a legal violation, adjudicate a complaint or execute enforcement autonomously. Authorised government officers retain those responsibilities.

### 1.1 Product vision

Provide Telangana authorities with a reliable, auditable, statewide view of public assets, observed physical changes, citizen intelligence, field verification and official action—down to an individual asset and its complete history.

### 1.2 Product outcomes

1. Establish a verified, versioned and auditable digital register of in-scope government assets.
2. Improve the detection and prioritisation of possible encroachments and other physical changes.
3. Bring satellite, citizen, social and field intelligence into a common workflow.
4. Reduce the time between a signal being received, reviewed, assigned and field-verified.
5. Give citizens a transparent way to submit and track reports.
6. Provide state, district, mandal and asset-level operational visibility.
7. Make legal records, spatial boundaries, imagery and action history accessible through Asset 360.
8. Enable evidence-grounded natural-language search without delegating official decisions to AI.

---

## 2. Business context and problem statement

Government asset information is often distributed across departments, GIS systems, spreadsheets, cadastral records, notifications, scanned documents and local offices. Monitoring may be periodic, fragmented or dependent on manual observation. Citizen reports arrive through disconnected channels and can be difficult to route, deduplicate and track. Public social content may contain useful leads but is noisy and difficult to locate reliably. Field inspections and follow-up actions may be recorded in separate systems.

This creates several business problems:

- No single, consistently governed inventory of in-scope assets.
- Inconsistent spatial formats, coordinate reference systems, survey references and data quality.
- Limited visibility of when an asset was last observed with suitable imagery.
- Slow identification and triage of possible changes.
- Citizen reports that cannot be consistently associated with assets or tracked end-to-end.
- Lack of a shared incident and inspection lifecycle across intelligence sources.
- Legal documents and boundary evidence that are difficult to retrieve alongside the map.
- Limited district and mandal-level performance reporting.
- Risk of confusing an AI detection or public allegation with an established legal finding.

GeoGuard addresses these problems through common identifiers, data contracts, provenance, versioned records, workflow, GIS, evidence management and role-aware reporting.

---

## 3. Objectives, measures and non-goals

### 3.1 Business objectives

| ID | Objective | Intended outcome |
|---|---|---|
| BO-01 | Establish a trusted Asset Registry | Approved assets have permanent IDs, verified source references and versioned geometries |
| BO-02 | Operationalise recurring observation | Eligible assets have monitoring policies, observation history and transparent coverage status |
| BO-03 | Improve signal triage | Potential changes and reports are deduplicated, prioritised and routed |
| BO-04 | Close the field-verification loop | Assigned inspections produce structured findings and evidence |
| BO-05 | Improve citizen transparency | Every accepted submission receives a trackable incident reference and status |
| BO-06 | Enable administrative oversight | State-to-asset dashboards expose workload, coverage and outcomes |
| BO-07 | Improve access to records | Asset 360 unifies spatial, legal, imagery, incident and inspection history |
| BO-08 | Support evidence-grounded queries | Copilot answers with source references and permission-aware retrieval |

### 3.2 Success measures

Targets must be baselined during the pilot and approved by the programme steering committee. The following are proposed measures, not guaranteed service levels.

| Measure | Definition |
|---|---|
| Asset onboarding completeness | Percentage of approved assets with mandatory attributes, accepted geometry and required provenance |
| Boundary verification coverage | Percentage of active assets with a boundary verification status and source document reference |
| Monitoring coverage | Percentage of eligible assets with a valid observation in the configured monitoring window |
| Observation suitability rate | Percentage of acquired scenes that pass configured quality checks |
| Alert review time | Time from alert creation to first authorised review |
| Incident acknowledgement time | Time from citizen submission to acknowledgement |
| Incident decision time | Time from submission to accept, decline or request-for-information decision |
| Inspection completion time | Time from assignment to submitted inspection report |
| Evidence completeness | Percentage of closed inspections with required notes, timestamps and evidence |
| Citizen status visibility | Percentage of citizen-submitted incidents with a current trackable status |
| Audit completeness | Percentage of governed create/update/approve/decision actions with attributable audit events |
| Copilot grounded-answer rate | Percentage of sampled answers with valid source citations and no unsupported factual claims |

### 3.3 Non-goals

The initial product is not intended to:

- Replace cadastral, land-registration, revenue, municipal or departmental systems of record.
- Determine ownership or title from imagery or AI.
- Automatically declare encroachment, illegality or guilt.
- Automatically alter notified FTL, buffer, cadastral or government-land boundaries.
- Issue legal notices or initiate coercive enforcement without authorised human action.
- Guarantee weekly high-resolution satellite acquisition for every asset.
- Treat every social-media post or citizen allegation as verified evidence.
- Conduct covert surveillance or identify private individuals from social content.
- Replace official field inspection or legal due process.
- Expose confidential case material to citizens or unauthorised departments.

---

## 4. Scope

### 4.1 In-scope capabilities

1. Departmental data onboarding and validation.
2. Permanent Asset Registry and asset lifecycle governance.
3. Spatial boundary, legal record and document versioning.
4. Imagery catalogue, monitoring scheduler and acquisition orchestration.
5. GIS/AI change screening and alert management.
6. Citizen reporting through web and WhatsApp, with incident tracking.
7. Public social-media intelligence through approved APIs/providers and permitted content.
8. Incident review, triage, assignment and case association.
9. Official field inspection and evidence capture.
10. High-resolution imagery request, approval and fulfilment tracking.
11. State, district, mandal, village and asset dashboards.
12. Asset 360 record and historical timeline.
13. AI-powered GeoGuard Copilot with role-aware, source-grounded answers.
14. Notifications, audit, administration, configuration and reporting.

### 4.2 Initial asset categories

The registry must support configurable categories. Initial categories proposed:

- Lakes and water bodies.
- Government land parcels.
- Parks and open spaces.
- Public buildings and facilities.
- Roads and right-of-way assets.
- Canals, nalas, feeder channels and drainage assets.
- Other public assets approved by the programme.

Category-specific attributes and validation rules must be configurable; the platform must not assume every asset has an FTL or buffer.

### 4.3 Out of scope for initial release

- Fully automated legal adjudication.
- Automatic boundary correction from satellite imagery.
- Autonomous enforcement or notice issuance.
- Unapproved scraping or collection from social platforms.
- Nationwide expansion outside Telangana.
- Guaranteed sub-metre or 30 cm weekly imagery.
- Predictive claims that cannot be supported by validated historical data.

---

## 5. Stakeholders, actors and roles

### 5.1 Stakeholder groups

- State programme sponsor and steering committee.
- Nodal department and state-level administrators.
- Revenue, Irrigation, Municipal Administration, HMDA and other participating authorities, as applicable.
- District collectors / district-level designated officers.
- Mandal and local officers.
- GIS and remote-sensing reviewers.
- Legal reviewers and authorised record custodians.
- Field inspectors.
- Citizen users and complainants.
- Government IT, cybersecurity, data-protection and audit teams.
- Imagery providers and approved technology/service partners.

### 5.2 Application roles

| Role | Main permissions |
|---|---|
| State Administrator | State configuration, department onboarding, user governance, statewide oversight |
| Department Administrator | Manage department-scoped submissions, asset records and departmental users |
| District Officer | Review district queue, assign inspections, monitor district assets and incidents |
| Mandal Officer | View permitted mandal assets, review local reports and coordinate field work |
| Field Inspector | View assigned tasks, capture evidence and submit inspection reports |
| GIS Reviewer | Validate geometry, coordinate systems, overlays and imagery observations |
| Legal Reviewer | Review legal documents, legal boundary references and verification status |
| Incident Reviewer | Acknowledge, accept, decline or request information on reports |
| Senior Officer | Read dashboards, escalations and performance reports |
| Auditor | Read-only access to authorised audit records and evidence provenance |
| Citizen | Submit and track own reports; see only citizen-safe status and responses |
| Platform Service Account | Narrow, non-interactive permissions for scheduled ingestion and processing |

Roles are further constrained by department, jurisdiction, asset sensitivity, case assignment and record-level permissions. A role must not grant unrestricted access across all districts by default.

### 5.3 Separation of duties

- A data submitter should not be the sole approver of the same asset's legal boundary.
- A GIS reviewer validates geometry; a legally authorised official validates legal authority and effect.
- A field inspector records observations but does not independently change the authoritative asset boundary.
- A citizen cannot view internal deliberations, protected evidence or another citizen's report.
- System administrators do not receive legal decision authority merely by virtue of technical administration.

---

## 6. Core domain concepts and identifiers

The following records must remain distinct.

| Record | Meaning | Example identifier |
|---|---|---|
| Asset | Permanent identity of a registered public asset | TG-HYD-SER-LAKE-000001 |
| Asset Boundary Version | A version of the asset's approved or proposed geometry | ABV-000001-03 |
| Data Submission | A department's submitted package and its validation history | SUB-2026-000045 |
| Imagery Observation | A source scene/acquisition intersecting an area of interest | OBS-2026-000321 |
| Detection | A machine-generated potential physical change | DET-2026-000782 |
| Incident | A complaint or intelligence report received by the platform | INC-2026-000125 |
| Case | An officially accepted investigation/follow-up record | CASE-2026-000087 |
| Inspection | A field visit and its findings | INSP-2026-000233 |
| Imagery Request | Request to obtain sharper or more suitable imagery | IMGREQ-2026-000019 |
| Legal Document | A source document with metadata and controlled versions | DOC-2026-000514 |
| Enforcement Action | A recorded official action and outcome | ACT-2026-000102 |
| Audit Event | An attributable record of a governed action | AUD-2026-009821 |

Identifiers must be unique, non-semantic where practical, generated by the platform and never reused. Human-readable prefixes may be included, but database primary keys must not depend on district names, asset categories or other mutable attributes.

### 6.1 Asset identity and non-deletion policy

- Once an asset is formally registered, its Asset ID is permanent.
- Physical deletion of a registered asset is prohibited through normal application workflows.
- Assets may be marked inactive, retired, transferred, superseded, merged or split only through governed lifecycle actions.
- A correction creates a new version and retains the prior value, actor, reason, approval and effective dates.
- A merged or split asset retains lineage links to predecessor/successor IDs.
- Duplicate registrations are resolved through a reviewed merge/supersession process; identifiers are never recycled.
- Legal boundary changes require source authority, document references, effective date, reviewer and approver.
- Retention, archival and lawful disposal of personal data/evidence must follow approved government retention schedules. Non-deletion of an Asset ID does not mean all attached personal data must be retained forever.

### 6.2 Asset lifecycle

Proposed states:

Draft → Submitted → Validation Failed / Validation Passed → GIS Review → Legal Review → Approved → Active Monitoring → Suspended / Inactive → Retired / Superseded.

Transitions require role checks, reason codes and audit events. Rejection must preserve the submission and review record. A draft candidate asset must not be presented as a legally verified asset.

---

## 7. End-to-end business workflows

### 7.1 Government data onboarding and asset registration

1. Department is onboarded with a named data owner and authorised submitters.
2. GeoGuard issues the department's data specification, schema, coordinate reference system guidance, templates and secure submission method.
3. Department submits spatial data, attributes and supporting legal/administrative records.
4. Platform creates a Data Submission ID and preserves original files and checksums.
5. Automated validation checks schema, mandatory fields, geometry validity, CRS, topology, duplicates, administrative codes and document references.
6. Validation report identifies errors, warnings and accepted records.
7. GIS reviewer checks geometry and spatial relationships.
8. Legal reviewer / authorised authority checks the supporting legal source and status.
9. Designated approver approves or rejects registration.
10. Approved record receives permanent Asset ID and first approved boundary version.
11. Monitoring profile and baseline observation requirements are assigned.
12. Asset becomes visible to permitted dashboards and Asset 360.

A failed or incomplete submission remains traceable and can be corrected by a new submission version. Source data must never be silently overwritten.

### 7.2 Recurring satellite monitoring and alert generation

1. Active assets are selected by monitoring policy, category, priority, geography, season and provider coverage.
2. Scheduler creates monitoring jobs and records expected observation windows.
3. Acquisition service searches configured government and commercial catalogues.
4. Eligible scenes are checked for acquisition time, spatial coverage, resolution, cloud/shadow, quality, licensing and sensor suitability.
5. No suitable scene results in a coverage exception / overdue observation state, not a no-change result.
6. Suitable imagery is catalogued and linked to intersecting assets.
7. Processing pipeline normalises imagery and runs configured detection rules.
8. Detection record captures model/rule version, source observations, processing parameters, geometry, class and separate confidence dimensions.
9. GIS spatial matching determines whether the detected area intersects an approved boundary, buffer or other configured zone.
10. Duplicate or related detections are grouped for reviewer triage.
11. Alert is created or updated according to policy.
12. Authorised reviewer validates, dismisses, requests more imagery or creates/links an incident/case.
13. Relevant officers receive notifications and assignment tasks.

**Observation honesty:** monitoring cadence is a target schedule, not a guarantee of imagery capture. The platform must expose last successful acquisition, last suitable observation, next scheduled attempt, missing coverage and provider/licence constraints.

### 7.3 Citizen incident submission

1. Citizen submits through the web portal or WhatsApp channel.
2. Capture channel, received timestamp, citizen-provided location, media, description and consent/privacy metadata.
3. Platform generates an Incident ID and acknowledges receipt.
4. Location is resolved to an existing asset where possible; uncertainty is retained.
5. Duplicate detection suggests related open incidents without discarding the new submission.
6. Automated safety, spam and completeness checks may be applied.
7. Incident enters administrative review queue.
8. Reviewer may acknowledge, accept, decline or request additional information with mandatory notes/reason.
9. Accepted report is associated with an existing Asset ID, or routed to candidate asset verification if no asset exists.
10. A case, monitoring watch or field inspection may be created according to policy.
11. Citizen receives status updates that are safe to disclose.
12. Closure records the outcome and citizen-visible explanation where permitted.

A report about an unregistered location creates an incident first. It does not automatically create a permanent Asset ID. Candidate asset onboarding requires source authority and approval.

### 7.4 Social intelligence workflow

1. Configure permitted sources, API/provider credentials, keywords, hashtags, languages, geographies and retention policy.
2. Collect public content only within provider terms and applicable law.
3. Store source URL/ID, source platform, publication timestamp, collection timestamp and permitted content snapshot/reference.
4. NLP classifies topic, extracts place references and estimates relevance.
5. Geocoding resolves candidate locations with confidence and evidence.
6. Candidate is compared with the Asset Registry and open incidents.
7. Reviewer sees source context, extracted location, confidence and limitations.
8. Reviewer may dismiss, request review, create an incident or associate with an existing incident/case.
9. Social content remains a lead unless independently verified.

The platform must not infer a person's guilt, sensitive traits or private location from public content. It must not scrape private accounts, bypass access controls or use unsupported collection methods.

### 7.5 Field assignment and inspection

1. A reviewer or authorised workflow creates an inspection request against an asset, detection, incident or case.
2. Assignment rules propose the responsible district/mandal team.
3. Authorised officer accepts or reassigns the task.
4. Inspector receives location, map, asset boundary, reason, risk/priority, available imagery and safety instructions.
5. Inspector records visit start/end, GPS (with accuracy), observations, notes, photos and attachments.
6. System preserves original uploaded media and records integrity metadata.
7. Inspector submits report; subsequent edits create versions and audit events.
8. Supervisor reviews, requests clarification, accepts findings or escalates.
9. Case owner records next action, closure or further inspection.
10. Citizen receives only the permitted status update if the inspection originated from a citizen report.

GPS and timestamps are supporting metadata, not proof by themselves. Device clocks may be incorrect; server receipt time and capture metadata must be distinguished.

### 7.6 High-resolution imagery request

1. Official selects an asset or draws an area of interest.
2. Request captures reason, intended use, target resolution, required date window, urgency and linked detection/case.
3. Platform checks existing catalogue for suitable scenes before requesting new acquisition.
4. System presents provider coverage, likely resolution, acquisition constraints, cloud risk, licensing and estimated cost where available.
5. Authorised approver reviews priority and budget.
6. Request is sent to approved provider or government source.
7. Status progresses through submitted, accepted, scheduled, acquired, delivered, quality checked, rejected or cancelled.
8. Delivered scene is ingested, checksum/catalogue metadata recorded and linked to asset/case.
9. Processing is rerun where authorised and reviewer is notified.

No capture time or resolution may be promised unless confirmed by the provider. Provider licence and permitted redistribution must be recorded.

### 7.7 Asset 360 and legal record management

Asset 360 provides a unified view of identity, department, jurisdiction, geometry versions, source provenance, legal documents, imagery timeline, detections, incidents, cases, inspections, actions and audit history.

Documents are uploaded by authorised staff and include issuing authority, reference number, issue/effective dates, document type, related asset/boundary version, verification state, uploader, checksum and access classification. Superseded documents remain linked and visible to authorised users.

### 7.8 AI Copilot workflow

1. User submits a natural-language question.
2. Identity, role, jurisdiction and record-level permissions are resolved.
3. Intent is routed to structured GIS/database query, document retrieval, imagery metadata or a combination.
4. Query execution is read-only in initial releases.
5. Results are assembled with source IDs, document/page references, observation dates and uncertainty.
6. Answer clearly distinguishes official record, machine-generated observation, citizen allegation and social lead.
7. If evidence is missing or conflicting, Copilot says so and offers the relevant record/workflow.
8. User can open the underlying asset, incident, document or map feature.

Copilot must not expose records outside the user's permissions, invent legal conclusions, modify authoritative data or initiate enforcement actions.

---

## 8. Functional requirements

Priority definitions: **P0** = foundational / required for a controlled pilot; **P1** = important for operational rollout; **P2** = advanced capability or later optimisation. Priority is a planning classification, not a commitment to a release date.

### 8.1 Government onboarding and Asset Registry

| ID | Priority | Requirement |
|---|---|---|
| FR-REG-001 | P0 | System shall support department and source-authority registration with named data owners and authorised submitters. |
| FR-REG-002 | P0 | System shall publish versioned data submission schemas, templates, field definitions and CRS requirements. |
| FR-REG-003 | P0 | System shall accept approved vector, tabular, raster and document formats through controlled upload/API channels. |
| FR-REG-004 | P0 | System shall preserve original submissions, source metadata, received time and cryptographic checksums. |
| FR-REG-005 | P0 | System shall validate required fields, geometry validity, CRS, topology, duplicates and administrative geography. |
| FR-REG-006 | P0 | System shall generate downloadable validation reports with errors, warnings and record-level references. |
| FR-REG-007 | P0 | System shall support GIS and legal review as distinct approval stages. |
| FR-REG-008 | P0 | System shall issue a unique permanent Asset ID only after configured approvals. |
| FR-REG-009 | P0 | System shall prevent physical deletion and ID reuse for registered assets. |
| FR-REG-010 | P0 | System shall version asset attributes and geometries with actor, reason, effective date and approval history. |
| FR-REG-011 | P1 | System shall support asset merge, split, transfer, retirement and supersession with lineage links. |
| FR-REG-012 | P1 | System shall support category-specific attributes and configurable validation rules. |
| FR-REG-013 | P1 | System shall support bulk onboarding with row-level result reporting and resumable processing. |
| FR-REG-014 | P1 | System shall identify potential duplicate assets for human resolution. |
| FR-REG-015 | P1 | System shall support asset source-quality and legal-verification status indicators. |

### 8.2 Spatial and legal records

| ID | Priority | Requirement |
|---|---|---|
| FR-GIS-001 | P0 | System shall store authoritative geometries with explicit CRS/SRID and source provenance. |
| FR-GIS-002 | P0 | System shall support polygon, multipolygon, line and point geometries as appropriate to asset category. |
| FR-GIS-003 | P0 | System shall display asset boundaries and configured spatial overlays on the map. |
| FR-GIS-004 | P0 | System shall distinguish official, proposed, derived, unverified and superseded geometries visually and in metadata. |
| FR-GIS-005 | P0 | System shall prevent machine detections from modifying authoritative geometries. |
| FR-GIS-006 | P1 | System shall support spatial intersection, proximity, containment and area calculations with stated measurement CRS/method. |
| FR-GIS-007 | P1 | System shall retain boundary version history and effective dates. |
| FR-LEG-001 | P0 | System shall attach legal/administrative documents to assets and boundary versions. |
| FR-LEG-002 | P0 | System shall record document type, authority, reference number, dates, verification status and checksum. |
| FR-LEG-003 | P1 | System shall support document supersession, restricted access and review workflows. |
| FR-LEG-004 | P1 | System shall provide a searchable legal-document index and page-level references where available. |

### 8.3 Imagery and monitoring

| ID | Priority | Requirement |
|---|---|---|
| FR-IMG-001 | P0 | System shall maintain an imagery catalogue with provider, sensor, acquisition time, footprint, resolution, quality and licence metadata. |
| FR-IMG-002 | P0 | System shall associate observations with intersecting assets and areas of interest. |
| FR-IMG-003 | P0 | System shall distinguish acquisition time, ingestion time and processing time. |
| FR-IMG-004 | P0 | System shall support per-asset monitoring policies and configurable schedules. |
| FR-IMG-005 | P0 | System shall record scheduled, attempted, acquired, unsuitable, unavailable and failed monitoring outcomes. |
| FR-IMG-006 | P0 | System shall not infer no change when no suitable observation exists. |
| FR-IMG-007 | P1 | System shall support multiple optical and SAR sources where licensed and technically integrated. |
| FR-IMG-008 | P1 | System shall support baseline/current imagery timeline and visual comparison when paired imagery exists. |
| FR-IMG-009 | P1 | System shall support imagery request creation, approval, provider tracking and delivery validation. |
| FR-IMG-010 | P1 | System shall record provider licence and permitted use for each imagery asset. |
| FR-IMG-011 | P2 | System shall optimise acquisition and processing by geography, priority, provider coverage and cost. |

### 8.4 Change detection and alerts

| ID | Priority | Requirement |
|---|---|---|
| FR-DET-001 | P0 | System shall execute configured detection rules against suitable imagery observations. |
| FR-DET-002 | P0 | System shall retain source observation IDs, algorithm/rule version and processing provenance for each detection. |
| FR-DET-003 | P0 | System shall store detection geometry, class, observed time window and separate confidence dimensions. |
| FR-DET-004 | P0 | System shall spatially relate detections to assets, approved boundaries and configured buffers. |
| FR-DET-005 | P0 | System shall create reviewable alerts according to configurable severity and deduplication rules. |
| FR-DET-006 | P0 | System shall support analyst validation, dismissal, escalation and request-for-imagery decisions with notes. |
| FR-DET-007 | P1 | System shall group related detections across repeated observations into an evolving event. |
| FR-DET-008 | P1 | System shall support alert thresholds and rules by asset category and department. |
| FR-DET-009 | P1 | System shall provide model/rule performance monitoring and reviewer feedback capture. |
| FR-DET-010 | P2 | System shall support model retraining and champion/challenger evaluation through governed ML operations. |

Detection categories shall be configurable. Initial candidates include new construction, water spread change, land filling, vegetation removal, excavation/levelling, road/paved-surface expansion and channel obstruction. Applicability depends on source resolution, season, sensor and validation.

### 8.5 Citizen channels and incidents

| ID | Priority | Requirement |
|---|---|---|
| FR-CIT-001 | P0 | Citizen portal shall accept report category, description, location and supporting media. |
| FR-CIT-002 | P0 | System shall generate a unique Incident ID and acknowledgement for each accepted submission. |
| FR-CIT-003 | P0 | System shall record channel, received time, location provenance and consent/privacy metadata. |
| FR-CIT-004 | P0 | System shall support incident review decisions: acknowledge, accept, decline and request information. |
| FR-CIT-005 | P0 | Every review decision shall capture actor, timestamp, reason and notes. |
| FR-CIT-006 | P0 | Citizen shall be able to track the status of their own report using authenticated access or an approved secure tracking method. |
| FR-CIT-007 | P0 | System shall associate incidents with existing assets where confidence and review policy permit. |
| FR-CIT-008 | P0 | System shall create a candidate asset verification task—not an approved Asset ID—when a report concerns an unregistered location. |
| FR-CIT-009 | P1 | System shall integrate WhatsApp Business or another approved messaging provider for inbound reports and status messages. |
| FR-CIT-010 | P1 | System shall detect possible duplicate incidents and allow reviewer linking without deleting submissions. |
| FR-CIT-011 | P1 | System shall support request-for-more-information and citizen response handling. |
| FR-CIT-012 | P1 | System shall provide configurable citizen-safe closure and status messages. |
| FR-CIT-013 | P1 | System shall apply rate limits, abuse controls, spam review and malware scanning to uploads. |

### 8.6 Social intelligence

| ID | Priority | Requirement |
|---|---|---|
| FR-SOC-001 | P1 | System shall support configurable keywords, hashtags, languages, sources and geographic themes. |
| FR-SOC-002 | P1 | Collection shall use approved APIs, licensed providers or other legally authorised public-source methods. |
| FR-SOC-003 | P1 | System shall preserve source references, publication and collection timestamps and collection provenance. |
| FR-SOC-004 | P1 | NLP shall classify relevance and extract candidate place names, survey references and location descriptions. |
| FR-SOC-005 | P1 | System shall geocode candidate locations and expose geocoding confidence and ambiguity. |
| FR-SOC-006 | P1 | Social leads shall enter a human-review queue before conversion to an incident or case. |
| FR-SOC-007 | P1 | System shall link related posts and incidents while retaining original source references. |
| FR-SOC-008 | P1 | System shall enforce source terms, retention rules, privacy and access restrictions. |
| FR-SOC-009 | P2 | System shall provide trend summaries by topic and geography without profiling private individuals. |

### 8.7 Cases, field operations and enforcement support

| ID | Priority | Requirement |
|---|---|---|
| FR-FLD-001 | P0 | Authorised users shall create an inspection task from an alert, incident, case or asset. |
| FR-FLD-002 | P0 | System shall support assignment by department, district, mandal and officer. |
| FR-FLD-003 | P0 | Inspector shall see assigned task, location, asset context and available evidence. |
| FR-FLD-004 | P0 | Inspector shall submit observations, notes, visit times and photo/document evidence. |
| FR-FLD-005 | P0 | System shall retain original uploaded evidence and integrity metadata. |
| FR-FLD-006 | P0 | Inspection report shall support submit, review, request clarification and accept/reject workflow. |
| FR-FLD-007 | P0 | System shall maintain full task status and reassignment history. |
| FR-FLD-008 | P1 | Mobile field experience shall support low-bandwidth and intermittent-connectivity operation. |
| FR-FLD-009 | P1 | System shall capture GPS accuracy and distinguish device capture metadata from server receipt time. |
| FR-FLD-010 | P1 | System shall record official action references, notices and outcomes entered by authorised officers. |
| FR-FLD-011 | P1 | System shall support escalation and overdue inspection reminders. |
| FR-FLD-012 | P1 | System shall provide citizen-safe status updates without disclosing protected investigation details. |

### 8.8 Dashboards and reporting

| ID | Priority | Requirement |
|---|---|---|
| FR-DASH-001 | P0 | System shall provide a statewide command dashboard. |
| FR-DASH-002 | P0 | System shall support drill-down by district, mandal, village and asset. |
| FR-DASH-003 | P0 | Dashboard shall expose asset inventory, monitoring coverage, alerts, incidents and inspection workload. |
| FR-DASH-004 | P0 | Dashboard filters shall include department, asset category, jurisdiction, severity and date range. |
| FR-DASH-005 | P0 | Map selections shall open the relevant asset, alert or incident details subject to permissions. |
| FR-DASH-006 | P1 | System shall provide trends, ageing, SLA/target performance and department comparisons. |
| FR-DASH-007 | P1 | System shall provide exportable, permission-filtered reports with generation metadata. |
| FR-DASH-008 | P1 | System shall distinguish live counts, demo data, stale data and unavailable data. |
| FR-DASH-009 | P1 | Senior-officer reports shall include data coverage and caveats to avoid misleading conclusions. |

### 8.9 Asset 360 and Copilot

| ID | Priority | Requirement |
|---|---|---|
| FR-A360-001 | P0 | Each registered asset shall have a consolidated Asset 360 page. |
| FR-A360-002 | P0 | Asset 360 shall show identity, geography, department, current approved boundary and verification status. |
| FR-A360-003 | P0 | Asset 360 shall show legal documents, imagery observations, detections, incidents, inspections and actions. |
| FR-A360-004 | P0 | Asset 360 shall show historical versions and audit history to authorised users. |
| FR-A360-005 | P1 | Asset 360 shall provide an imagery timeline and comparison when valid imagery pairs exist. |
| FR-AI-001 | P1 | Copilot shall accept natural-language questions about assets, incidents, monitoring and legal documents. |
| FR-AI-002 | P1 | Copilot shall enforce the same access permissions as the underlying application. |
| FR-AI-003 | P1 | Copilot answers shall cite source records and document/page references where available. |
| FR-AI-004 | P1 | Copilot shall distinguish authoritative records, machine detections, citizen reports and social leads. |
| FR-AI-005 | P1 | Copilot shall state uncertainty and missing data rather than fabricate an answer. |
| FR-AI-006 | P1 | Initial Copilot shall be read-only and shall not approve, modify or issue official actions. |
| FR-AI-007 | P2 | Copilot may prepare draft summaries or reports for human review, clearly labelled as AI-generated. |

### 8.10 Administration, notifications and audit

| ID | Priority | Requirement |
|---|---|---|
| FR-ADM-001 | P0 | System shall support role-based and jurisdiction-scoped access control. |
| FR-ADM-002 | P0 | System shall support configurable departments, jurisdictions, asset categories and workflow rules. |
| FR-ADM-003 | P0 | System shall record audit events for governed create, update, approval, rejection, assignment, access and export actions. |
| FR-ADM-004 | P0 | Audit events shall include actor/service identity, timestamp, action, target, outcome and correlation reference. |
| FR-ADM-005 | P0 | System shall prevent ordinary users from editing or deleting audit events. |
| FR-ADM-006 | P0 | System shall provide in-app notifications for relevant assignments and decisions. |
| FR-ADM-007 | P1 | System shall support approved email/SMS/WhatsApp notification providers and templates. |
| FR-ADM-008 | P1 | System shall support notification delivery status, retries and dead-letter handling. |
| FR-ADM-009 | P1 | System shall support configurable retention and legal hold policies. |
| FR-ADM-010 | P1 | System shall provide audit export and evidence integrity verification to authorised auditors. |

---

## 9. Government data onboarding specification

A separate implementation-ready data contract should be maintained alongside this PRD. The following is the baseline requirement.

### 9.1 Submission package

Each department submission should contain:

1. Manifest file with submission ID, department, source authority, dataset name, date, CRS and contact.
2. Asset attribute table.
3. Spatial geometry dataset.
4. Legal/administrative document index.
5. Supporting document files.
6. Optional reference imagery/raster.
7. Data dictionary and code lists where department-specific values are used.

### 9.2 Accepted formats

| Data type | Preferred format | Also accepted subject to validation |
|---|---|---|
| Vector GIS | GeoPackage | GeoJSON, Shapefile ZIP, KML/KMZ |
| Tabular attributes | CSV UTF-8 | XLSX |
| Coordinates | CSV with explicit coordinate columns and CRS | GeoJSON Point |
| Raster maps | GeoTIFF / Cloud Optimized GeoTIFF | Other georeferenced raster after review |
| Legal records | PDF/PDF-A where available | TIFF or image scan with OCR review |
| Metadata/manifest | JSON or CSV | XLSX template for manual submissions |

Shapefile submissions must include all required sidecar files in one archive. GeoPackage is preferred for packaged vector exchange because it avoids common multi-file Shapefile problems.

### 9.3 Coordinate reference system requirements

- Every spatial dataset must declare its CRS using an EPSG code or complete WKT.
- Latitude/longitude values must explicitly identify datum and axis order.
- The platform must not assume that unlabelled coordinates are WGS 84.
- Source geometry must be preserved; reprojection creates a derived copy with transformation metadata.
- Official cadastral/projected datasets should be delivered in the authority's declared CRS and accompanied by transformation information if required.
- Geometry precision and area calculations must use an appropriate projected CRS; display reprojection must not be mistaken for survey-grade measurement.

### 9.4 Minimum common asset schema

| Field | Required | Description |
|---|---|---|
| source_asset_ref | Yes | Department's existing identifier, if one exists |
| asset_name | Yes | Official/common asset name |
| asset_category | Yes | Configured category code |
| department_code | Yes | Owning/custodian authority code |
| district_code | Yes | Official district code |
| mandal_code | Yes | Official mandal code |
| village_code | Conditional | Official village code where applicable |
| survey_number | Conditional | Survey number and subdivision reference |
| extent_value | Conditional | Declared extent |
| extent_unit | Conditional | Acre, hectare, square metre, etc. |
| geometry | Yes for spatial asset | Polygon/multipolygon/line/point as category requires |
| source_crs | Yes | EPSG or WKT |
| source_document_refs | Yes for legal registration | References to supporting authority documents |
| legal_status | Yes | Controlled status code; not free-text inference |
| source_authority | Yes | Issuing/providing authority |
| source_effective_date | Conditional | Date source record became effective |
| source_record_date | Conditional | Date of source record |
| data_contact | Yes | Departmental data owner/contact role |
| submission_version | Yes | Department dataset version |

### 9.5 Additional lake/water-body attributes

- Official lake/water-body name and local aliases.
- Existing department/lake identifier.
- Notified extent and unit.
- FTL geometry and source reference.
- Buffer geometry and applicable buffer rule/source.
- Feeder/nala/channel relationships where documented.
- Catchment or hydrological reference where available.
- Notification/GO references and effective dates.
- Legal verification status and reviewing authority.

FTL and buffer must be represented as separately sourced/versioned spatial records. They must not be inferred solely from visible water spread.

### 9.6 Validation rules

- Mandatory fields are present and use valid code lists.
- Geometry is parseable, non-empty and valid; self-intersections and invalid rings are reported.
- CRS is explicit and supported.
- Geometry type matches asset category.
- Geometry coordinates fall within plausible jurisdiction bounds.
- Duplicate source IDs and likely spatial duplicates are flagged.
- Survey number formats are retained as source values and are not silently normalised.
- Declared extent is compared with geometry-derived area as a quality check; differences are flagged, not silently corrected.
- Legal document references resolve to submitted files or a recorded external authority reference.
- Administrative codes are validated against the approved government master list.
- Geometry overlaps, gaps and topology are flagged according to category-specific rules.
- Original submitted files are retained and checksummed.

### 9.7 Submission outcomes

Each submission record shall return:
- Submission ID and received timestamp.
- File-level validation result.
- Record-level validation result.
- Error and warning codes.
- Accepted, rejected and pending-review counts.
- Re-submission instructions.
- Review and approval history.
- Resulting Asset IDs only for records approved for registration.

---

## 10. Data model overview

Core entities and relationships:

- Department 1..N Data Submission.
- Data Submission 1..N Submission Record.
- Registered Asset 1..N Asset Attribute Version.
- Registered Asset 1..N Asset Boundary Version.
- Registered Asset 1..N Legal Document Link.
- Registered Asset 1..N Imagery Observation Link.
- Imagery Observation 1..N Detection.
- Detection N..N Asset (a detection may intersect multiple assets; relation records spatial basis).
- Incident N..N Asset (one report may concern multiple assets; an asset may have multiple reports).
- Incident 0..1 or 1..N Case links according to configured investigation policy.
- Case 1..N Inspection / Action / Evidence records.
- Asset 1..N Inspection.
- Imagery Request N..1 Asset or area-of-interest.
- All governed entities 1..N Audit Event.

Spatial data, evidence files and searchable document text should be stored in appropriate services while stable metadata and relationships remain queryable through the application data layer. Original evidence should not be overwritten by processed derivatives.

---

## 11. Notifications and escalation

### 11.1 Notification events

- Submission received / validation completed / review required.
- Asset approved / rejected / activated / suspended.
- Monitoring job overdue / imagery unavailable / processing failed.
- New detection / alert severity changed / alert assigned.
- Citizen incident acknowledged / information requested / accepted / declined / status changed / closed.
- Social lead awaiting review.
- Inspection assigned / accepted / due / overdue / submitted / returned / approved.
- Imagery request approved / provider update / acquisition delivered / quality rejected.
- Case escalation and action due date.

### 11.2 Notification principles

- Notifications must be role- and jurisdiction-aware.
- Sensitive information must not be included in unsecured message content.
- Citizen notifications must expose only citizen-safe information.
- Delivery attempts, provider response, retries and failures must be recorded.
- In-app task queues remain the system of record; SMS/email/WhatsApp are notification channels, not the authoritative workflow store.

---

## 12. Dashboards and reporting requirements

### 12.1 State dashboard

Show total registered assets, assets by category/department, boundary verification coverage, monitoring coverage, imagery suitability, open detections, incidents, social leads, inspections, overdue work and official action status.

### 12.2 District dashboard

Show district asset distribution, alert/incident ageing, monitoring gaps, assigned officers, inspection workload, unresolved cases and department-level breakdown.

### 12.3 Mandal dashboard

Show local assets on a map, recent changes, open citizen reports, pending inspections, repeat detections and last suitable observation.

### 12.4 Asset dashboard / Asset 360

Show complete identity, legal and spatial records, imagery timeline, detection history, citizen/social incidents, inspections, official actions and audit history.

### 12.5 Reporting rules

- Every metric must define numerator, denominator, time window and inclusion rules.
- Dashboards must display last refresh time and data freshness.
- Missing observations must be shown as coverage gaps, not zero detections.
- Demo/test records must be visibly labelled and excluded from official metrics.
- Exports must be permission-filtered and include generation timestamp and filter criteria.
- Sensitive reports must be access-controlled and logged.

---

## 13. AI, analytics and evidence governance

### 13.1 Separate confidence dimensions

At minimum, maintain distinct measures for:

1. **Image suitability:** Whether the source observation is adequate for the detection task.
2. **Detection confidence:** Model/rule confidence that a physical feature/change is present.
3. **Spatial/legal match:** Strength of the spatial relationship to a configured authoritative boundary or zone.

These dimensions must not be collapsed into a legal conclusion. A high AI score does not prove encroachment. A spatial intersection does not establish title or intent.

### 13.2 Detection provenance

Every detection must retain:
- Source imagery observation IDs and provider.
- Acquisition date/time and sensor.
- Processing timestamp and pipeline run ID.
- Algorithm/model/rule name and version.
- Parameters and relevant quality flags.
- Output geometry and class.
- Confidence dimensions and their definitions.
- Spatial layer/boundary version used for matching.
- Reviewer decisions and feedback history.

### 13.3 Human oversight

- All consequential alert disposition is performed by an authorised reviewer.
- Boundary and legal status changes require designated approval.
- Copilot outputs are advisory and source-grounded.
- AI-generated text must be labelled and reviewable before it becomes an official record.
- Models must be evaluated across seasons, land cover, sensor types and geographies before operational reliance.
- Performance, false positives, false negatives and drift must be monitored.

---

## 14. Non-functional requirements

The following are target design requirements. Exact service levels, sizing and retention values require architecture validation, procurement input and government approval.

### 14.1 Security and access

- Integrate with approved government identity/SSO where available.
- Enforce least privilege, role-based access and jurisdiction/department scoping.
- Support MFA for privileged and official roles where identity provider permits.
- Encrypt data in transit and at rest using approved government standards.
- Store secrets in an approved secrets manager; never in source control.
- Separate public citizen endpoints from official administration and data services.
- Apply malware scanning, file type validation, upload size limits and rate limits.
- Log privileged access, bulk exports, permission changes and sensitive record access.
- Conduct threat modelling, vulnerability assessment and penetration testing before production.

### 14.2 Privacy and data protection

- Collect only personal data required for the stated workflow.
- Provide clear notice and purpose at citizen submission.
- Define retention, deletion, archival and legal-hold policies with the government data owner.
- Restrict citizen identity/contact data from broad dashboard access.
- Avoid collecting sensitive personal data from social content.
- Support access, correction and grievance processes as approved by the responsible authority.
- Do not expose complainant identity to subjects of complaints through public tracking.
- Complete applicable privacy impact and legal reviews before launch.

### 14.3 Audit and integrity

- Audit events must be append-only from the application perspective.
- Use trusted server-side timestamps and stable actor/service identities.
- Record before/after values or immutable version references for governed changes.
- Store checksums for original submissions and evidence.
- Restrict audit modification to controlled infrastructure administration; operational users cannot edit audit history.
- Support export and verification of evidence packages.
- Define immutable/WORM storage and retention according to government policy.

### 14.4 Availability and resilience

- Design for recoverable failures in ingestion, imagery acquisition, AI processing and notification delivery.
- Use retryable asynchronous jobs, idempotency keys and dead-letter queues.
- Back up database, object storage metadata and configuration.
- Test restore and disaster recovery procedures.
- Define RPO/RTO with government stakeholders before production.
- Ensure failed external integrations do not corrupt core asset or incident records.

### 14.5 Performance and scale

- Support spatial queries and map rendering for statewide datasets through spatial indexing, tiling and bounded queries.
- Process large imagery asynchronously; do not block interactive requests.
- Support bulk onboarding and monitoring queues with backpressure.
- Establish pilot and statewide workload profiles before setting numeric latency/throughput SLAs.
- Provide pagination, filtering and server-side aggregation for large tables and dashboards.

### 14.6 Accessibility and usability

- Support responsive desktop, tablet and field-mobile layouts.
- Provide keyboard navigation, visible focus and screen-reader labels.
- Use clear status labels and distinguish map symbology by more than colour alone.
- Support approved languages, initially English and Telugu as prioritised by the programme.
- Provide low-bandwidth field workflows and clear offline/sync status.

### 14.7 Observability and operations

- Centralise application, worker, integration and security logs.
- Monitor job queues, imagery provider status, failed tasks, API health and data freshness.
- Trace cross-service workflows using correlation IDs.
- Alert operators on repeated failures and stuck jobs.
- Maintain runbooks, backup procedures, provider contact paths and operational dashboards.

---

## 15. Integration requirements

| Integration | Purpose | Required controls |
|---|---|---|
| Government department systems | Asset records, cadastral and legal documents | Data-sharing agreement, source authority, schema, provenance |
| Government GIS/remote sensing sources | Imagery and authoritative layers | Licence, CRS, acquisition metadata, service availability |
| Commercial imagery providers | Tasked/high-resolution imagery | Procurement, cost approval, licence and delivery SLA |
| WhatsApp Business/provider | Citizen intake and status notifications | Verified business account, webhook security, consent and template policy |
| Public social platforms/listening providers | Public-source leads | Approved API/licence, terms, rate limits and retention |
| Government identity provider | Official authentication | SSO, MFA, role/department claims and deprovisioning |
| SMS/email gateway | Notifications | Approved provider, delivery status and sensitive-data minimisation |
| Maps/tiles/geocoding | Map display and location resolution | Government-approved hosting/licence and accuracy metadata |
| Object storage | Documents, imagery and evidence | Encryption, access policy, versioning and retention |
| Search/document processing | Legal document indexing and retrieval | Access filtering, OCR quality and source/page references |

Every external integration must have a named owner, environment separation, credentials rotation, failure handling, auditability and a documented fallback.

---

## 16. User experience and navigation model

The product should use a role-aware command-centre experience with map-first navigation.

### 16.1 Primary navigation

- Command Overview.
- Asset Registry.
- Data Onboarding.
- Monitoring & Imagery.
- Alerts / Incident Register.
- Citizen Reports.
- Social Intelligence.
- Cases & Field Operations.
- Imagery Requests.
- Reports & Analytics.
- Asset 360.
- GeoGuard Copilot.
- Administration and Audit.

Navigation visibility and actions must be permission-driven.

### 16.2 Command overview

The existing map-first command-centre design is the visual foundation. It should evolve to show jurisdiction context, global search, asset categories, monitoring health, priority alerts, map layers and a contextual inspector. The current implementation is an initial UI foundation; modules listed in this PRD may require new screens and APIs.

### 16.3 Citizen experience

Citizen portal must prioritise simple submission, clear acknowledgement, secure tracking, accessible language and transparent status. It must not expose internal risk scores, confidential legal material or protected inspection evidence.

### 16.4 Field experience

Field UI must be mobile-first, task-oriented and tolerant of intermittent connectivity. It must show assigned work, navigation context, capture controls, required fields and pending synchronisation.

---

## 17. Release roadmap and delivery strategy

### Phase 0 — Product and governance readiness

- Confirm sponsoring authority, participating departments and asset categories.
- Approve data-sharing, legal review and data ownership model.
- Finalise data submission specification and master code lists.
- Define identity, access, retention, privacy and evidence policies.
- Confirm pilot geographies and baseline measures.

### Phase 1 — Registry foundation and operational command

- Department onboarding and controlled submissions.
- Validation engine and review queues.
- Permanent Asset Registry and boundary versioning.
- Legal document catalogue.
- Role/jurisdiction access and audit.
- State/district/mandal dashboards and Asset 360 foundation.
- Migrate and reconcile existing pilot assets.

**Exit criteria:** approved pilot assets have unique permanent IDs, verified source records, approved geometries, audit history and working role restrictions.

### Phase 2 — Imagery monitoring and alerting

- Imagery catalogue and source adapters.
- Monitoring scheduler and coverage status.
- Processing orchestration and detection rules.
- Detection provenance and reviewer workbench.
- Alert notifications and imagery request workflow.

**Exit criteria:** pilot assets have observable monitoring outcomes, valid observation history, reproducible detections and human-reviewed alerts.

### Phase 3 — Citizen and social intelligence

- Citizen report intake and secure tracking.
- WhatsApp integration.
- Incident triage, duplicate linking and asset association.
- Approved social listening integration and lead review.
- Unified incident queues.

**Exit criteria:** reports from enabled channels receive IDs, acknowledgement, review decision and auditable status transitions.

### Phase 4 — Field operations and case lifecycle

- Officer assignment and mobile inspection.
- Evidence capture, integrity and review.
- Case management and official action references.
- Escalation and workload dashboards.

**Exit criteria:** assigned inspections can be completed end-to-end with auditable findings and evidence.

### Phase 5 — Copilot and advanced intelligence

- Permission-aware RAG and structured GIS query.
- Legal document/page citations.
- Asset and district summaries.
- Model evaluation, feedback and drift governance.
- Advanced risk prioritisation and acquisition optimisation.

**Exit criteria:** Copilot answers pass a curated evaluation set for access control, factual grounding, citations and uncertainty handling.

### Pilot approach

Begin with a bounded pilot covering a selected set of lakes and government parcels across agreed districts/mandals. The previously discussed indicative pilot scale of 10–15 lakes and 100–200 parcels can be used for planning, but the final cohort must be confirmed against data availability, legal verification, imagery coverage and departmental participation.

---

## 18. Acceptance criteria and definition of done

A feature is not accepted merely because a screen exists. Acceptance requires API, data, permissions, audit, failure handling and test evidence.

### 18.1 Registry acceptance

- Valid submission can be uploaded and assigned a Submission ID.
- Invalid geometry/CRS/schema produces actionable validation errors.
- Original source files remain retrievable with checksum.
- Approval generates one permanent Asset ID.
- Repeated submission does not create duplicate IDs without review.
- Registered asset cannot be hard-deleted through normal APIs/UI.
- Boundary correction creates a new version and preserves previous version.
- Unauthorised roles cannot approve or change legal records.

### 18.2 Monitoring acceptance

- Scheduler creates monitoring attempts for eligible assets.
- Each attempt records outcome and reason.
- Missing imagery is represented as a coverage gap.
- Detection can be traced to imagery, model/rule version and boundary version.
- Detection does not automatically change asset geometry or legal status.
- Reviewer disposition and notes are audited.
- Duplicate detections can be linked/grouped without losing provenance.

### 18.3 Citizen and social acceptance

- Citizen submission receives an Incident ID and acknowledgement.
- Citizen can see only their own permitted status.
- Reviewer can acknowledge, accept, decline or request information with notes.
- Unknown location is routed to candidate verification rather than auto-registration.
- Social lead retains source link and collection metadata.
- Social lead requires human review before incident/case creation.

### 18.4 Field acceptance

- Assignment is restricted to authorised officers.
- Inspector can submit notes and evidence.
- Original evidence and integrity metadata are retained.
- Supervisor can review or return a report.
- All assignment and review transitions are audited.

### 18.5 Copilot acceptance

- User cannot retrieve records outside their access scope.
- Legal answers include document/source references.
- Copilot distinguishes allegation, detection and official finding.
- Missing or conflicting information is explicitly stated.
- Copilot cannot write to authoritative records in read-only release.

### 18.6 Release readiness

- Automated unit, integration and end-to-end tests pass.
- Security and privacy review is completed.
- Backup/restore and failure-recovery tests are completed.
- Operational runbooks and support ownership exist.
- Data owners and approvers are identified.
- Known limitations and data coverage are visible to users.

---

## 19. Risks, dependencies and mitigations

| Risk / dependency | Impact | Mitigation |
|---|---|---|
| Incomplete or conflicting departmental data | Incorrect asset inventory or boundaries | Formal data contract, validation, provenance and human review |
| No legal authority/document for a boundary | False legal implication | Separate geometry status from legal verification; require authority reference |
| Inconsistent CRS or survey identifiers | Spatial misalignment | Explicit CRS contract, transformation logs and GIS QA |
| Imagery cadence/resolution limitations | Missed or delayed detections | Multi-source strategy, suitability reporting and no-change safeguards |
| Cloud, seasonality and sensor differences | False positives/negatives | Quality gates, sensor-aware models and human review |
| Social API restrictions or provider changes | Reduced monitoring coverage | Approved providers, source register and graceful degradation |
| Citizen spam or malicious uploads | Operational and security risk | Rate limits, malware scan, moderation and duplicate handling |
| False allegations or mistaken geocoding | Reputational/legal harm | Human verification, confidence disclosure and source preservation |
| AI hallucination or permission leakage | Incorrect or sensitive answer | Structured retrieval, access filtering, citations and evaluation |
| Officer adoption and process fragmentation | Incomplete closure of cases | Department-led workflow design, training and operational KPIs |
| Unclear retention/privacy policy | Compliance risk | Government-approved retention schedule and privacy impact review |
| Provider cost and procurement | Budget uncertainty | Cost/coverage estimates, approval gates and usage monitoring |

---

## 20. Assumptions and constraints

1. Participating departments will nominate data owners and authorised approvers.
2. Government authorities remain the source of legal authority and official asset records.
3. Spatial datasets may arrive in different formats, CRSs and levels of accuracy.
4. Imagery availability, resolution, frequency and redistribution rights vary by provider.
5. Weekly processing can be scheduled, but weekly suitable high-resolution imagery cannot be guaranteed.
6. Public social content collection is subject to platform terms, applicable law and approved provider access.
7. Citizen identity and contact data require privacy controls and defined retention.
8. Official SSO, messaging, imagery and GIS integrations depend on government approvals and credentials.
9. The existing application is a prototype/evolving implementation; production readiness requires additional hardening and formal validation.
10. Final RPO, RTO, availability, response-time and data-retention targets must be set by the government programme.

---

## 21. Open decisions requiring stakeholder approval

| ID | Decision | Proposed owner |
|---|---|---|
| OD-01 | Which department is the system owner and which authority is the data controller for each category? | State sponsor |
| OD-02 | Which departments and asset categories are included in the first pilot? | Steering committee |
| OD-03 | Which government master codes are authoritative for district, mandal, village and department? | Nodal departments |
| OD-04 | Which legal authority validates each category's boundary and legal status? | Department/legal authority |
| OD-05 | Which CRS and cadastral exchange standards are mandated for each source department? | GIS/data governance group |
| OD-06 | What is the required monitoring cadence by asset category and priority? | Operations + imagery team |
| OD-07 | What imagery providers, resolutions, budgets and licences are approved? | Procurement + GIS authority |
| OD-08 | Which social platforms and listening providers are approved? | Legal, communications and IT |
| OD-09 | What citizen identity, anonymity and tracking model is permitted? | Programme + privacy/legal |
| OD-10 | What are the retention periods for complaints, personal data, imagery and evidence? | Records officer/legal |
| OD-11 | Which official notifications are allowed and through which providers? | Department operations |
| OD-12 | What are the official case statuses, escalation paths and closure authorities? | Department operations |
| OD-13 | What SSO, hosting, key management, DR and security standards are mandatory? | Government IT/security |
| OD-14 | What languages and accessibility standards are required at launch? | Programme sponsor |
| OD-15 | What numeric SLAs, RPO and RTO apply to the pilot and statewide service? | IT operations |
| OD-16 | Which Copilot use cases are approved and what documents are accessible by each role? | Legal + data owners |

---

## 22. Glossary

| Term | Definition |
|---|---|
| Asset | A registered public/government asset with a permanent platform identity |
| Asset Registry | Authoritative platform index of registered assets and their governed metadata |
| Boundary Version | A dated, sourced version of an asset's geometry |
| FTL | Full Tank Level boundary/level as established by the competent authority |
| Buffer | A legally or administratively defined zone around an asset, with its own source and version |
| Observation | A satellite/aerial image acquisition or other time-stamped source observation |
| Detection | A machine-generated candidate physical change from an observation |
| Alert | A prioritised work item created for authorised review |
| Incident | A citizen or intelligence report received by the platform |
| Case | An officially accepted investigation/follow-up record |
| Inspection | A field visit and structured report |
| Social Lead | A candidate intelligence item derived from permitted public content |
| Asset 360 | Consolidated identity, spatial, legal, imagery and operational history for an asset |
| Copilot | Permission-aware AI interface for querying records and documents |
| Provenance | Information describing the source, transformation, time and authority of a record |

---

## 23. Relationship to current repository implementation

This PRD describes the target product, not a claim that all requirements are implemented.

The repository currently contains an evolving lake-protection application, an initial command-centre UI, existing asset/alert and case/legal/evidence/audit workflows, and geospatial/pipeline work documented elsewhere in the repository. The map-first UI is a foundation for the broader navigation and operational model described here.

Before planning a release, engineering and product owners must map each FR ID to:
- Existing implementation and code path.
- API/data model support.
- Test coverage.
- External integration dependency.
- Status: Implemented, Partial, Planned, Blocked or Not Applicable.
- Acceptance evidence and accountable owner.

The PRD should be reviewed alongside:
- Repository README and CONTEXT.md.
- PROGRESS.md and DECISIONS.md.
- docs/architecture/ architecture pack.
- docs/data-model/ data model specifications.
- docs/implementation/ implementation increments.
- docs/ui/ command-centre design notes.

**Approval:** This document becomes the product baseline only after review and approval by the designated government programme sponsor, participating department data owners, legal authority, security/privacy stakeholders and product/engineering leads.
