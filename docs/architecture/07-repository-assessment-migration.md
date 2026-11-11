# 07 — Repository Assessment and Migration Plan

## 1. Executive assessment
The current repository is a substantial working prototype. It is strong in the operational loop: legal checks, alert lifecycle, field verification, evidence generation, audit, monthly reporting and a carefully labelled demo.

The statewide architecture is stronger as the target production blueprint because it generalises beyond the current lake/HYDRAA prototype and explicitly addresses multi-department data governance, statewide geospatial processing, integrations, MLOps, security, resilience and scale.

**Decision: adopt the statewide architecture as the target blueprint, preserve the current implementation and migrate incrementally. Do not delete or wholesale-rewrite the prototype.** This replaces the architectural direction, not tested source code.

## 2. Assessment scope
Repository: aitech2025/lake-protect. Default branch reported by GitHub: feature/initial. Assessment date: 11 November 2026. Reviewed repository tree, README, CONTEXT, DECISIONS, PROGRESS, selected FastAPI models/routes/services, boundary service, candidate ingestion, pipeline CLI and frontend manifest. This was a source/document review; code was not cloned, built or executed. Test counts below are repository-reported, not independently rerun.

## 3. Strengths to retain
| Existing capability | Repository evidence | Recommendation |
|---|---|---|
| FastAPI + PostGIS | api/, migrations, models | Retain; evolve with migrations |
| Asset/boundary management | assets, boundaries, boundary service | Retain immutable versioning; generalise asset classes |
| Legal checks/rule configuration | rules/legal_check.py and YAML | Retain as category-specific versioned rules |
| Alert workflow/escalation | workflow, alert routers, worker | Retain; make department routing configurable |
| Offline field workflow | web/src/field | Retain; harden sync/device security |
| Evidence packs | evidence package and verifier | Retain; extend provenance and retention |
| Audit chain | audit/chain.py | Retain; add protected external checkpoints |
| Monthly bulletin | bulletin package | Retain; extend metrics and department views |
| React/MapLibre/Telugu-English | web/ | Retain and expand personas |
| Synthetic demo discipline | data/demo, E2E, docs/DEMO | Retain clear synthetic-data labels |

PROGRESS.md records M0, M1 and M4–M9 complete with 235 API tests, 4 pipeline tests and 14 browser tests. These are reported results, not independently verified here. It also states M2 Sentinel-2 detection and M3 radar/scored backtest are not started. README says the demo is fictional and no detection result has yet been demonstrated.

## 4. Main gaps against target
| Area | Current prototype | Target gap |
|---|---|---|
| Scope | Lake/government-land prototype, HYDRAA-first | Universal multi-asset, multi-department registry |
| Identity | Demo-role login | Government SSO, MFA, ABAC and service identities |
| Data model | Asset/boundary-centric | Stable UUIDs, parcel links, effective-dated admin and responsibility relationships |
| Responsibility | Prototype personas | Distinct ownership, custody, jurisdiction, legal protection and enforcement |
| Boundaries | Strong append-only versions | Formal authority approval and richer source/valid-time governance |
| Imagery | Pipeline foundation; M2/M3 pending | STAC, COG/object storage, provider adapters, tile processing and orchestration |
| ML | Detection/backtest incomplete | Validated per-task models, blind data, registry and drift monitoring |
| Scale | PostGIS and lake-focused processing | Statewide geographic tiling, multi-asset joins and tile delivery |
| Workflow | Strong alert/field/evidence loop | Configurable cross-department routing and category-specific legal rules |
| Notifications | Audit/overdue flags; gateway stubbed | Durable outbox and delivery tracking |
| Security/operations | Demo constraints and Docker Compose | SSO, ABAC/RLS, KMS, SIEM, HA/DR, restore and load testing |
| Integrations | CSV/import stubs and plans | Approved source adapters, sync and reconciliation SLAs |

The prototype has deeper implemented legal/workflow logic than this architecture pack. Preserve that advantage.

## 5. Decisions
1. Do not rewrite into microservices immediately. Keep modular FastAPI for transactional domains; split raster and ML workers first.
2. Do not replace the database wholesale. Add tables and relationships through Alembic migrations; preserve IDs, evidence and audit history.
3. Do not treat OSM geometry as authoritative. Preserve its derived status.
4. Do not enable statewide alerts until M2/M3 or equivalent independent detection validation passes.
5. Do not hardcode department authority. Add effective-dated responsibility/jurisdiction configuration and obtain approval.
6. Do not call the platform production-grade until security, HA, DR, monitoring, support and operational gates pass.
7. Preserve owner-blind detection and restricted personal data.
8. Retain case-ready evidence as a differentiator.

## 6. Target repository structure
This is a gradual destination, not a mandate to move every file now:
- api/app: identity, registry, parcels, boundaries, observations, candidates, rules, alerts, cases, field, evidence, audit, analytics, integrations
- workers: ingestion, raster, spatial, inference
- pipeline: reproducible research and CLI
- ml: datasets, annotations, experiments, models, evaluation, registry
- web/src: state, department, analyst, field, asset, GIS, reports
- data: schemas, reference, demo
- infra: docker, kubernetes, terraform, monitoring, security, backup/DR
- docs: architecture, data dictionary, integrations, security, operations, validation
- tests: unit, integration, spatial, performance, security, E2E

Do not create empty services just to match this tree. Move code only when a scaling, security, release or ownership boundary justifies it.

## 7. Migration phases and gates
**Phase 0 — baseline:** tag prototype; schema snapshot; restore test; API contract snapshots; keep demo/reference data separated. Gate: reproducible baseline and no loss of evidence/audit.

**Phase 1 — registry/governance:** stable asset identity mapping; categories; parcels and many-to-many links; departments/jurisdictions/responsibilities; boundary authority and valid-time metadata; import batches/reconciliation. Gate: lake, parcel and non-lake sample can be onboarded; historical alert replays with original boundary; jurisdiction tests pass.

**Phase 2 — geospatial platform:** STAC catalogue; object storage; COGs; tile-based jobs; idempotent ingestion; scene-to-many-assets intersection; explicit no-data/failure states. Gate: one scene ingested/processed once and matched to multiple assets without duplicate work.

**Phase 3 — detection validation:** complete M2/M3 or equivalent; freeze positives, negatives and authorised works; no-look-ahead historical backtest; compare index/rule baseline, RF/XGBoost and segmentation only where labels justify it. Gate: independent report accepted and false-positive workload within agreed thresholds.

**Phase 4 — department operations:** configurable routing; department/district dashboards; Asset 360; durable notification outbox; field evidence provenance; legal/officer SOP. Gate: end-to-end acceptance by participating department.

**Phase 5 — production hardening:** SSO/MFA; RBAC+ABAC/RLS; HA database/object store; durable queues; observability/SIEM; security/privacy review; load, restore and DR exercises. Gate: formal government IT/security and service-owner sign-off.

**Phase 6 — statewide expansion:** onboard districts/departments in waves; appoint data stewards; refresh SLAs; train users; add asset categories only after legal and workflow approval. Gate: each wave meets data, workflow, performance, security and operating readiness.

## 8. First engineering backlog
1. ADR for modular transactional backend plus independent workers.
2. Current-to-target schema mapping from models and Alembic migrations.
3. Tests for valid-time boundary lookup and historical case replay.
4. Reference schemas for asset categories, departments, jurisdictions and responsibility.
5. Source authority/provenance and import batch tracking.
6. STAC mapping and object storage key policy.
7. Geographic tile job that processes one scene and intersects many assets.
8. Candidate schema with model, dataset, processing and source lineage.
9. Blind backtest report and validation dataset governance.
10. Threat model, access matrix and backup/restore runbook.

## 9. Risks and open decisions
Government data access/licensing/refresh SLAs are not established by this review. Department authority and routing need current legal verification. Some boundaries are derived or incomplete. Satellite resolution/revisit may not support all structure-level use cases. Model accuracy remains unknown until blind validation. Commercial imagery costs depend on coverage/resolution/licence. Statewide capacity needs measurement. Hosting, SSO and security standards require the designated government IT authority. Certificate wording, survey procedure and buffer rules require counsel.

## 10. Final recommendation
Adopt this architecture pack as Lake Protect's target blueprint. Preserve the existing prototype and migrate additively. First priorities: governed asset/parcel/boundary registry, source provenance, jurisdiction model and reproducible geospatial pipeline. Complete detection validation before operational expansion.