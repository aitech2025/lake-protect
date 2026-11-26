# GeoGuard — Architecture Decision Register

**Version:** 0.1.0-review | **Date:** 26 November 2026  
**Status:** Selected directions captured; remaining decisions open.

## 1. Decision states

- **Selected for baseline:** explicit product-owner selection; may be implemented subject to normal delivery controls.
- **Existing approved constraint:** previously explicit owner decision in repository; remains binding until changed.
- **Open:** no decision; do not infer.
- **Proposed:** recommendation for review, not approved.
- **Superseded/conflicted:** older content is retained for history but must not override a later explicit decision.

## 2. Product-owner-selected decisions

### ADR-GG-001 — Permanent asset identity
**State:** Selected for baseline.  
**Decision:** Every registered asset receives immutable UUID and permanent human-readable GeoGuard Asset Code. Neither may be reused. Do not encode mutable administrative geography or department into the code.  
**Rationale:** stable cross-system identity across administrative changes, boundary revisions, merges and splits.  
**Consequences:** maintain aliases and external department identifiers separately; define merge/split lineage; never physically delete identity.  
**Open detail:** final code syntax and category-specific namespaces.

### ADR-GG-002 — Unknown citizen-reported land is a candidate asset
**State:** Selected for baseline.  
**Decision:** A citizen report about unknown land creates an Incident and Candidate Asset; it does not create a registered government Asset.  
**Rationale:** prevent unverified citizen submissions from contaminating authoritative inventory.  
**Consequences:** candidate matching, deduplication, candidate-to-official-asset promotion only through formal departmental submission/approval.  
**Reconciliation:** clarifies D-063 reported-place/pseudo-asset language.

### ADR-GG-003 — Separate detection, lead, incident, case and inspection
**State:** Selected for baseline.  
**Decision:** These are separate entities with explicit relationships and lifecycles.  
**Rationale:** machine output, unverified intelligence, complaint/review, investigation and field observation have different semantics and authority.  
**Consequences:** many-to-many associations; a case can consolidate multiple signals; evidence lineage is explicit.

### ADR-GG-004 — GIS validation is separate from legal/administrative approval
**State:** Selected for baseline.  
**Decision:** Technical/GIS validation does not confer legal authority. Record GIS review and legal/administrative approval independently.  
**Rationale:** valid geometry is not proof of title, notification or legal boundary.  
**Consequences:** separate approval metadata, state, reviewer and audit. Unapproved geometry remains derived/unverified/watch-only.

### ADR-GG-005 — Jurisdiction-aware field roles require RBAC approval
**State:** Selected for baseline.  
**Decision:** Do not implement jurisdiction-aware field roles until the expanded RBAC model is explicitly approved.  
**Rationale:** preserve D-057's currently approved admin/viewer model and avoid silently restoring retired roles.  
**Consequences:** design for future policy scoping, but no field-officer/district/mandal role activation without a new decision.

### ADR-GG-006 — Social intelligence uses permitted public sources only
**State:** Selected for baseline.  
**Decision:** Public/licensed/authorized sources only; content is unverified intelligence.  
**Rationale:** privacy, platform terms and false allegation risk.  
**Consequences:** source rights and collection basis recorded; no private content or access-control bypass; human corroboration required.

### ADR-GG-007 — Copilot is read-only initially
**State:** Selected for baseline.  
**Decision:** Read-only analytics and retrieval with citations, source permissions and audit.  
**Rationale:** prevent unauthorized actions and legal/operational overreach.  
**Consequences:** no write APIs/tools; permission checks before retrieval; abstention on unsupported answers.

### ADR-GG-008 — High-resolution imagery has a separate lifecycle
**State:** Selected for baseline.  
**Decision:** Separate request, approval, provider tasking, acquisition, ingestion, QA and reprocessing workflow.  
**Rationale:** procurement, cost, tasking and capture are distinct from routine screening.  
**Consequences:** archive-first search; tasking is not capture guarantee; cost/licence/PO and acquisition outcome tracked.

### ADR-GG-009 — Weekly schedule target, observation independent
**State:** Selected for baseline.  
**Decision:** Weekly monitoring schedule is the target; suitable imagery acquisition is recorded independently.  
**Rationale:** cloud, revisit, sensor and licensing constraints make a weekly clear image impossible to guarantee.  
**Consequences:** distinguish scheduled run, imagery observation, suitability and result. No suitable image is not no change.

### ADR-GG-010 — Physical change, not legal conclusion
**State:** Selected for baseline.  
**Decision:** Automated output describes potential physical change only.  
**Rationale:** legality depends on authoritative records, permits, facts and competent authority.  
**Consequences:** factual labels and confidence; no machine-generated illegal/encroachment/violation verdict or enforcement recommendation.

## 3. Existing approved constraints retained

### D-057 — Current application roles and simple incident lifecycle
**State:** Existing approved constraint.  
**Decision:** Current approved roles are `admin` and `viewer`; current simple incident lifecycle and weekly per-asset records are documented in `DECISIONS.md` and `docs/weekly-processing.md`.  
**Consequence:** personas in the BRD are not roles. No additional roles, field routing, two-person closure or escalation timers without approval.

### D-061 — Admin-created locations
**State:** Existing approved constraint.  
**Decision:** Admin may create a location/watch target.  
**Consequence:** watch target is not automatically an authoritative registered government asset.

### D-063 — Citizen reports outside registered assets
**State:** Clarified by ADR-GG-002.  
**Decision:** incident + candidate asset; not registered asset.  
**Consequence:** keep historical D-063 reference but implement candidate semantics.

### Government integration guardrail
**State:** Existing approved constraint.  
**Decision:** government integrations remain templates/placeholders until authorized; no scraping or live government calls.  
**Consequence:** clearly label mocks and demo adapters.

## 4. Legacy concepts not approved for reintroduction

The following appear in older `CONTEXT.md` or architecture proposals but conflict with later owner direction or are not approved in the current baseline:
- analyst/reviewer/field_officer/nodal_officer/legal_officer/senior_officer/auditor/revenue_officer/irrigation_officer as active app roles;
- field app and jurisdictional officer assignment;
- two-person closure/co-sign;
- escalation timers and automatic officer routing;
- retired ACTION/VERIFY/WATCH modes where superseded by current implementation;
- automated legal decision or enforcement recommendations.

They may be revisited only through a new, explicit decision with RBAC, workflow, legal and operational impacts documented.

## 5. Open decisions requiring owner/stakeholder resolution

| ID | Topic | Decision required | Why it matters |
|---|---|---|---|
| ODR-01 | Initial asset scope | Lakes only, or phased rollout to all public asset categories | Data model, rollout and departmental ownership |
| ODR-02 | Asset code | Exact syntax, category namespace and legacy mapping | Stable external identity |
| ODR-03 | Authoritative source | Department/source of record per asset class | Data authority and conflict handling |
| ODR-04 | Boundary authority | Competent approver per boundary type; maker/checker and legal evidence | Legal reliance |
| ODR-05 | Candidate promotion | Required evidence and approvals to convert candidate to registered asset | Registry integrity |
| ODR-06 | RBAC | Roles, scopes, department/mandal hierarchy, delegation and emergency access | Security and workflows |
| ODR-07 | Incident/case lifecycle | Exact state machine, closure authority, reopening and SLA | Operational accountability |
| ODR-08 | Inspection workflow | Whether field app/offline capture/geofencing/assignment are in scope | RBAC and field operations |
| ODR-09 | Enforcement records | Which notices/orders/actions are recorded and who can enter/approve | Legal responsibility |
| ODR-10 | Legal evidence | Required document classes, verification, OCR and evidentiary standards | Defensibility |
| ODR-11 | Notifications | Channels, consent, templates, retry, urgency and SLA | Provider cost and user experience |
| ODR-12 | Social providers | Approved platforms, API/licence, collection basis, retention/takedown | Legal/privacy |
| ODR-13 | Imagery strategy | Free/open vs commercial mix, priority sensors and provider shortlist | Cost, coverage, resolution |
| ODR-14 | High-res approval | Thresholds, approvers, budget, PO and emergency procurement | Financial governance |
| ODR-15 | Data retention | Asset, imagery, citizen PII, social content, evidence and audit retention | Compliance and storage |
| ODR-16 | Hosting/residency | Government cloud/on-prem/India region and network boundaries | Procurement/security |
| ODR-17 | Government integrations | Departments, APIs/files, authentication and data-sharing agreements | Delivery dependencies |
| ODR-18 | SLAs/SLOs | Availability, queue ageing, imagery freshness and support hours | Operations |
| ODR-19 | DR/BCP | RPO/RTO, backup, HA and restore test cadence | Continuity |
| ODR-20 | Citizen identity | Anonymous/optional/verified reporting and contact privacy | Trust and abuse prevention |
| ODR-21 | Department isolation | Tenant model, row-level security and cross-department sharing | Confidentiality |
| ODR-22 | Audit immutability | Hash chain, WORM storage, digital signatures and legal hold | Evidence trust |
| ODR-23 | Deployment model | Managed cloud, government data centre, hybrid | Architecture and cost |
| ODR-24 | Accessibility/languages | Telugu/English scope, translation and accessibility standards | Adoption |
| ODR-25 | Detection performance | Minimum precision/recall/false alerts/lead time by class | Go-live threshold |
| ODR-26 | Copilot scope | Allowed datasets, models, hosting and answer retention | AI governance |
| ODR-27 | Export/sharing | Public vs internal reports, watermarking and approval | Information disclosure |
| ODR-28 | Monitoring cadence | Per-asset schedule, exceptions and operational definition of weekly | Feasibility and KPIs |

## 6. Approval record

No open decision above is approved by inclusion in this register. Record owner, date, option selected, rationale, consequences and superseded documents when resolved.
