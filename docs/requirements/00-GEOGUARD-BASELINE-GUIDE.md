# GeoGuard requirements baseline — review package

**Version:** 0.1.0-review  
**Assessment date:** 26 November 2026  
**Repository:** `aitech2025/lake-protect`  
**Target branch:** `consolidated`  
**Approval state:** Draft for product-owner and government-stakeholder review; not an approved government specification.

## Purpose

This package consolidates the product vision, business requirements, product requirements, target architecture, decision register, implementation status and traceability for GeoGuard. It is intended to prevent requirements from being lost across earlier conversations, `CONTEXT.md`, `DECISIONS.md`, the implementation plan, module status and focused technical notes.

The package is a **proposed statewide product baseline**. It does not itself authorize government integrations, procurement, operational enforcement, expanded roles or legal decisions.

## Document map

| Document | Purpose |
|---|---|
| [Business Requirements](01-GEOGUARD-BRD.md) | Business problem, outcomes, stakeholders, scope, business processes and measures |
| [Product Requirements](02-GEOGUARD-PRD.md) | Functional/non-functional requirements, workflows, UX, acceptance criteria and releases |
| [Solution Architecture](../architecture/GEOGUARD-SOLUTION-ARCHITECTURE.md) | Context, logical/physical architecture, data domains, integrations, security and operations |
| [Architecture Decision Register](../architecture/GEOGUARD-ADR-REGISTER.md) | Selected decisions, legacy conflicts, proposed decisions and open questions |
| [Implementation Status](../implementation/GEOGUARD-IMPLEMENTATION-STATUS.md) | Audited repository status, evidence, gaps, dependencies and suggested sequencing |
| [Requirements Traceability](GEOGUARD-TRACEABILITY.csv) | Requirement-to-acceptance-to-status-to-evidence mapping |
| [Government Data Exchange](../integration/GOVERNMENT-DATA-EXCHANGE.md) | File formats, validation, metadata, hand-off and future connector contracts |

## Baseline authority and precedence

Apply these sources in order when interpreting this review package:

1. Explicit, dated product-owner decisions in current conversations and the latest applicable entries in `DECISIONS.md`.
2. This review package for the consolidated proposed requirements, subject to owner approval.
3. Current implementation and tests as evidence of what exists, not as proof of business approval.
4. `CONTEXT.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/MODULE_IMPLEMENTATION_STATUS.md`, `PROGRESS.md` and focused design notes, interpreted with their dates and known conflicts.
5. Older architecture proposals and superseded workflows only as historical context.

This package does not silently rewrite historical decisions. Conflicts are called out in the ADR register. In particular:
- D-057's currently approved application roles remain `admin` and `viewer`; jurisdiction-aware field roles require a separate explicit RBAC approval.
- D-057's simple incident lifecycle remains the implementation baseline unless a replacement lifecycle is approved.
- The older field app, field-officer routing, second-person closure, escalation timers and retired role concepts are not approved for reintroduction merely because they appear in older architecture material.
- D-063's reported-place/pseudo-asset concept is clarified here as an incident-linked **candidate asset**, not a registered government asset.
- D-061 admin-created locations remain watch targets and are distinct from formally registered government assets.
- Government integrations remain placeholders/templates until agreements, credentials, data-sharing authority and security approvals exist.

## Decisions selected by the product owner for this proposed baseline

The following are treated as selected design directions, not as blanket approval of every implementation detail:

1. Every asset has an immutable internal UUID and a permanent human-readable GeoGuard Asset Code; neither is reused.
2. A citizen report about unknown land creates an incident and candidate asset, never an automatically registered government asset.
3. Detection, Intelligence Lead, Incident, Case and Inspection are separate domain entities.
4. GIS validation and legal/administrative boundary approval are separate controls.
5. Jurisdiction-aware field roles are gated on approval of an expanded RBAC model.
6. Social monitoring is limited to permitted public sources; content is unverified intelligence.
7. The AI Copilot is read-only initially, with citations, source permissions and audit.
8. High-resolution imagery has a separate request, approval, provider-tasking, acquisition and reprocessing lifecycle.
9. Weekly scheduling is the monitoring target; suitable imagery acquisition is recorded independently.
10. Automated systems describe potential physical changes and do not make legal conclusions.

## Status vocabulary

- **Implemented:** code and/or tests demonstrate the capability in the prototype. This does not mean production-ready.
- **Partially implemented:** some required capability exists, but important acceptance criteria remain.
- **Not implemented:** no adequate implementation evidence found in the audited repository.
- **Intentionally deferred:** held back by explicit product direction or external approval.
- **Needs decision:** requirements or governance choice remains open.
- **Not verified:** the repository contains indications or a claimed status, but the relevant end-to-end behavior was not independently verified in this audit.

## Baseline limitations

- The audit is a repository-document and branch-content review; it is not a fresh execution of every automated test.
- The status assessment is dated 26 November 2026 and must be refreshed against the branch before each release.
- Existing milestone/test counts quoted in repository documents are historical evidence, not a claim that tests were rerun for this package.
- No production government data integration, legal certification, provider procurement, security accreditation or statewide operational readiness is implied.
- Satellite revisit cadence and actual usable observations depend on sensor, orbit, cloud, tasking, licensing, AOI and provider availability. Weekly job execution is not a promise of a clear weekly image.

## Approval workflow

1. Review BRD business outcomes and in/out-of-scope items.
2. Review PRD requirements and acceptance criteria with product owner and representative departments.
3. Resolve open decisions in the ADR register.
4. Obtain legal, GIS, security, privacy, procurement and departmental approvals where applicable.
5. Mark this package as an approved baseline only after explicit sign-off; record approver, date, version and change request.
6. Update traceability and implementation status on every meaningful implementation increment.

## Change control

Every material change must include: requirement ID(s), reason, owner, impact on data model/API/UI/security/legal/process, acceptance criteria, migration/backward-compatibility plan, test evidence and decision reference. Do not remove historical evidence or mutate asset/boundary identity to accommodate a change.
