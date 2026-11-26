# GeoGuard — Business Requirements Document (BRD)

**Version:** 0.1.0-review | **Date:** 26 November 2026  
**Status:** Proposed baseline for review; not approved for government operations.

## 1. Executive summary

GeoGuard is proposed as a statewide Government Land & Asset Protection Intelligence Platform for Telangana. It brings together authoritative government asset records, geospatial boundaries, satellite observations, automated physical-change screening, citizen and public-source intelligence, official review and inspection support, evidence management, command dashboards and a read-only AI research assistant.

The product is not simply a satellite map or an automated encroachment verdict engine. Its purpose is to help authorized officials see **where a potential physical change has occurred, what source evidence supports it, which asset or boundary version may be affected, what is known and unknown, and what review is outstanding**. Legal status and enforcement decisions remain with competent government authorities.

The common foundation is a trusted Asset Registry, Incident/Case Management and Evidence Management capability. Satellite detection, citizen reports and public social/news signals are separate intake channels that can be associated with the same asset or case without being collapsed into one record type.

## 2. Business context and problem

Government departments hold land, lakes, water bodies, public utilities and other public assets across heterogeneous systems and document formats. Boundary records may be fragmented, outdated, derived or differently interpreted by departments. Monitoring evidence is episodic and may not be linked to the authoritative asset record, legal notifications, citizen complaints or field inspection history.

The business problems to address are:
- no single, provenance-aware view of government assets and their boundary versions;
- difficulty comparing suitable satellite observations consistently over time;
- lack of a clear distinction between no detected change and no usable imagery;
- fragmented citizen complaints, media leads, imagery detections and official inspections;
- weak linkage between a physical observation and the applicable legal/administrative record;
- difficulty prioritising review queues and understanding state/district/mandal/village trends;
- costly or slow procurement of high-resolution imagery without an auditable request lifecycle;
- manual preparation of asset histories, evidence packs and senior-official briefings.

These are target business problems, not a claim that every department currently lacks its own systems.

## 3. Vision and business outcomes

### 3.1 Vision

Provide a trusted, auditable, map-first intelligence platform through which authorized Telangana departments can protect public assets using authoritative records, multi-source observations and accountable human review.

### 3.2 Outcomes

| ID | Desired outcome | Illustrative measure |
|---|---|---|
| BO-01 | Improve visibility of government assets and their authoritative status | Percentage of in-scope assets with validated identity, boundary provenance and legal-record index |
| BO-02 | Improve timeliness of potential physical-change screening | Scheduled screening completion and age of last suitable observation, reported separately |
| BO-03 | Reduce fragmented intelligence intake | Percentage of reports/leads linked to an asset, candidate asset or case |
| BO-04 | Improve review prioritisation | Queue age, review turnaround and unresolved item ageing |
| BO-05 | Improve evidence traceability | Percentage of reviewed detections with source imagery, timestamps, hashes and boundary version |
| BO-06 | Improve senior-official situational awareness | Availability and freshness of state/district/mandal summaries |
| BO-07 | Improve procurement transparency for high-resolution imagery | Request-to-approval and request-to-acquisition status, cost and outcome visibility |
| BO-08 | Improve access to records and historical context | Time to assemble an asset history/evidence package with citations |

Targets, SLAs, baselines and denominators are open decisions; do not invent numeric commitments.

## 4. Stakeholders and business personas

Potential stakeholder groups (final departmental mapping and authority must be validated):
- State-level sponsoring department and senior leadership.
- District, mandal and village administrative authorities.
- Land/revenue and survey/settlement departments.
- Irrigation and water-resource authorities for lake/FTL records.
- Urban development and municipal authorities.
- Forest, endowment, Wakf and other custodial departments where in scope.
- HYDRAA and other enforcement/protection agencies, subject to mandate.
- GIS, remote-sensing and technical operations teams.
- Legal, records-management, audit, privacy and cybersecurity teams.
- Citizens and community organizations using reporting channels.
- Approved imagery, messaging and data service providers.

The existing prototype's approved application roles are only `admin` and `viewer` under D-057. Business personas listed above do not automatically imply application roles or permissions. Jurisdiction-specific field roles require explicit RBAC approval.

## 5. Scope

### 5.1 Business capabilities in the proposed product vision

1. **Government data onboarding and Asset Registry:** authoritative asset submissions, cadastral records, legal records, validation, approval, versioning and permanent identity.
2. **Satellite imagery and change intelligence:** source discovery, acquisition, quality assessment, preprocessing, screening, physical-change candidates and observation history.
3. **Citizen intelligence:** web/mobile web and WhatsApp intake, incident acknowledgement/status, attachments and triage.
4. **Public social/news intelligence:** permitted public-source monitoring, location/entity extraction and unverified intelligence leads.
5. **Official review, inspection and enforcement support:** case preparation, factual field observations and action records; expanded field roles/workflows are approval-gated.
6. **Command dashboards:** state through asset-level map and operational views.
7. **Asset 360 and AI Copilot:** unified asset history and read-only, cited natural-language access to authorized records.
8. **High-resolution imagery requests:** archive search, cost/approval, provider tasking, acquisition and reprocessing.

### 5.2 Initial product focus

The existing repository is lake-protection-led and contains a meaningful prototype around lakes, boundaries, satellite screening, incidents and citizen intake. Broader asset categories and statewide departmental workflows are a product expansion baseline, not evidence that all categories are already onboarded or production-supported.

Initial live category rollout, geography and agency selection require owner/government agreement.

### 5.3 Out of scope unless separately approved

- Automated legal determinations, guilt attribution, demolition recommendations or enforcement decisions.
- Automatic creation of registered government assets from citizen/social reports.
- Unapproved live government-system integration, scraping or bypassing access controls.
- Private or restricted social content collection.
- Copilot writes, approvals, notices, boundary edits or enforcement actions.
- A promise of weekly 30 cm imagery or weekly clear observations across the state.
- Expanded field-officer roles, jurisdiction routing, offline field app or dual-signoff closure before RBAC/workflow approval.
- Replacement of existing departmental systems of record without an approved migration and governance plan.

## 6. Business process overview

### 6.1 Asset onboarding

Department submission → intake receipt → technical format/geometry validation → GIS review → legal/administrative review → authorized approval → permanent identity assignment → registry activation → monitoring configuration. Rejected or incomplete submissions retain validation findings and provenance.

### 6.2 Monitoring and detection

Scheduled screening → imagery search/acquisition → quality/suitability decision → preprocessing → change analysis → spatial relationship to asset and boundary version → potential-change record → human review → incident/case association where appropriate. No suitable image must be represented as an observation gap, not as no change.

### 6.3 Citizen intelligence

Citizen submission → acknowledgement → moderation/duplicate/spam checks → location resolution → known-asset match or candidate-asset creation → triage → investigation/inspection if approved → case association → citizen-safe status update → closure with audit.

### 6.4 Social intelligence

Permitted public source capture → source/rights metadata → language and location extraction → duplicate clustering → analyst triage → intelligence lead → link to asset/incident/case or dismiss. Public post content remains unverified unless independently corroborated.

### 6.5 Inspection and enforcement support

Case/inspection assignment under an approved authorization model → factual observations and media capture → supervisor/competent-authority review → legal/administrative decision outside automated detection → action/notice/order record where authorized → follow-up and closure evidence.

### 6.6 High-resolution imagery

AOI request → archive search → quality/resolution/date assessment → estimate/licence/cost → approval → tasking → acquisition success/failure → ingestion and QA → processing/reprocessing → link evidence to asset/detection/case → completion.

## 7. Business information requirements

The platform must maintain:
- official asset identifiers, department references, names/aliases and custodianship;
- administrative geography and survey/cadastral references;
- geometry, CRS, extent, source, provenance and boundary version;
- legal notifications, government orders, title/custodianship and restrictions, disputes and court references, permits and authorized works;
- imagery source/product, acquisition date, sensor, resolution, cloud/quality, suitability, coverage, license and processing lineage;
- physical-change candidates, detector/rule version, confidence, spatial relationship and before/after evidence;
- citizen incidents, consent/contact handling, attachments and status history;
- public-source intelligence references and collection rights;
- cases, reviews, inspections, factual observations and official action records;
- evidence hashes, access history, retention and audit events;
- high-resolution request costs, approvals, tasking and acquisition outcomes.

## 8. Governance and business rules

1. Asset UUID and GeoGuard Asset Code are permanent and never reused.
2. Official assets, admin watch targets and candidate assets are distinct concepts.
3. A report about unknown land creates an incident and candidate asset only.
4. GIS validity is not legal authority. Technical validation and legal/administrative approval are separate.
5. Boundaries are versioned and historically retrievable; never silently overwrite approved geometry.
6. Automated detection describes potential physical change, not illegality or ownership.
7. Imagery acquisition date, processing date, suitability and freshness are always visible.
8. Absence of a suitable image is not evidence of no change.
9. Citizen and public social content is unverified until corroborated.
10. All important decisions, access and evidence transformations are auditable.
11. Copilot is read-only and permission-constrained at retrieval/query time.
12. Government connectors remain mocks/templates until formally authorized.

## 9. Business risks and controls

| Risk | Business impact | Required control |
|---|---|---|
| Incorrect or unverified boundary | False association or harmful action | Provenance, boundary status, GIS review and separate legal approval |
| Cloud/revisit gaps | Missed or delayed observation | Explicit no-usable-look state and freshness indicators |
| False positive detection | Wasted field effort or reputational harm | Confidence, limitations, human review and validated backtest |
| Misinterpreted citizen/social post | Defamation, privacy or operational risk | Unverified lead classification, moderation and corroboration |
| Stale legal documents | Incorrect legal context | Document dates, source, verification and version status |
| Unauthorized access | Exposure of sensitive records | Least privilege, isolation, audit and security testing |
| Unapproved government integration | Legal/operational breach | Placeholder adapters and formal approval gates |
| Commercial imagery cost/licence | Budget and reuse constraints | Archive-first search, cost approval and rights metadata |
| AI hallucination or leakage | Incorrect advice or data exposure | Read-only retrieval, citations, permissions, audit and abstention |

## 10. Assumptions, dependencies and open matters

The business case depends on department-provided authoritative records, legal interpretation, data-sharing permissions, imagery availability/licensing, procurement, hosting/security approvals and agreement on the first rollout cohort. Open choices are maintained in the ADR register and must not be treated as settled.

## 11. Business acceptance

The BRD can be accepted only when the product owner and relevant government stakeholders agree on:
- initial departments, asset categories and geographic rollout;
- business outcomes and measurable targets;
- authoritative data custodians and approval authorities;
- legal and records-management controls;
- operating model, responsibilities and escalation;
- budget/procurement and imagery strategy;
- data protection, hosting and security constraints.

**Approval record:** Pending.
