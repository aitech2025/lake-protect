# GeoGuard module implementation status

**Assessment date:** 26 November 2026  
**Canonical development branch:** `feature/consolidated`  
**Status branch:** `docs/fanout-progress-update`  
**Product baseline:** [GeoGuard BRD/PRD](product/GEOGUARD-BRD-PRD.md)  
**Requirements traceability:** [GeoGuard RTM](product/GEOGUARD-RTM.csv)  
**Execution plan:** [Implementation plan](IMPLEMENTATION_PLAN.md)

> Status is based on repository code, merged PRs, CI evidence and explicit owner decisions. "Implemented" means a capability exists in the prototype; it does not imply production certification, authoritative government data, or operational approval.

## Executive summary

- The existing lake-protection workflow and the statewide geospatial foundations are integrated into one application.
- The application/control plane, map-first desk, asset/boundary foundations, case workflow, evidence/reporting foundations, STAC/Sentinel-2 screening, ingestion APIs and weekly replay code exist.
- The key product gate is still **the scored blind historical backtest**. The scorer and replay guardrails are stronger, but no validated detection precision/recall/lead-time result exists.
- Detect-v2 is not frozen. Its five-lake non-scored tuning run has completed; sub-threshold levelling components now export review geometries/chips, but the run4/run5 footprint comparison and human review remain open.
- Government connectors remain placeholders/demo adapters. No live government integration is activated.
- The existing Asset 360 is now extended with district/mandal filters and boundary-source display; authoritative department hierarchy and production controls remain incomplete.

## Module inventory

| # | Module | Status | What is implemented | Remaining work / acceptance gate |
|---:|---|---|---|---|
| 1 | Application foundation and architecture | **Implemented** | FastAPI modular monolith/control plane, React/TypeScript web app, PostgreSQL/PostGIS, Alembic migrations, Docker-based services; separate Python geospatial processing plane | Production deployment topology, HA/DR and operational SLOs |
| 2 | Identity, roles and authorization | **Partial** | Application authentication and role-aware workflow/API checks; department-isolation work exists in the wider history | Reconcile current two-role owner-approved model, database RLS and actual deployment roles; SSO/MFA not complete |
| 3 | Asset registry and permanent identity | **Partial** | Lake asset catalogue, asset IDs, source records, statewide public-asset/parcel registry schema and ingestion APIs; OSM-derived lake inventory | Government master-code mapping, authoritative asset onboarding, deduplication/merge governance and full statewide registry UI |
| 4 | Boundary and legal provenance | **Partial** | Versioned/append-only boundary records, provenance foundations, legal/rule checks and audit history | Certified departmental boundaries, maker-checker approval, boundary conflict workflow and counsel approval |
| 5 | Source onboarding and ingestion | **Partial** | File/import foundations, source registry, provenance, authenticated pipeline ingestion for batches/scenes/processing runs and social signal payloads | Provider-specific connectors, source refresh scheduling, retry/monitoring and live government integrations (approval-gated) |
| 6 | Satellite catalogue and acquisition | **Partial** | STAC discovery, Sentinel-2 Earth Search collection access, suitability checks, scene registration, windowed imagery caching and COG/S3-compatible outputs | Production pgSTAC/catalogue operations, provider licensing/configuration, resilient scheduled acquisition/backfill and coverage SLAs |
| 7 | Raster preprocessing and map products | **Partial** | Rasterio-based windowed processing, MNDWI masks, COG generation, offline basemap/tile foundations and temporal water comparison | Full production tile-serving/imagery timeline integration, provider health visibility and broader sensor harmonisation |
| 8 | Sentinel-2 physical-change detection | **Partial** | MNDWI water screening and class-based physical-change rules for clearing, soil fill, building and D-058 levelling; persistence, seasonality, novelty, established-state and area controls | Review-only levelling component geometries/chips are exported separately from alert candidates; run4/run5 spatial diff, human review, immutable rule freeze, independent case validation and scored performance gate |
| 9 | Sentinel-1 / radar confirmation | **Partial** | Calibrated VV threshold screening foundation and radar confirmation check for built candidates; replay code includes Sentinel-1 archive checks | Verify historical RTC processing and scene availability end-to-end; document calibration/terrain correction limitations; independent radar evaluation |
| 10 | Historical replay and backtesting | **Partial — critical gate** | Strict case validator, 27-lead discovery register, evidence/eligibility rules, scorer requiring replay-time `detected_at`/unique IDs/valid geometry, weekly resumable replay, no-look-ahead guards and run fingerprints | Verify cases and event polygons, freeze detector rules, run the scored set, manually adjudicate false flags, publish metrics/chips and signed limitations |
| 11 | Candidate, alert and case workflow | **Implemented for prototype** | Candidate ingestion, alert lifecycle/state machine, priority/rules checks, legal record references, role-gated actions, audit trail and watch-list handling | Validate current approved workflow against owner decisions; authoritative boundaries/legal records required before operational progression |
| 12 | Map-first GeoGuard desk | **Partial** | MapLibre command UI, map/layer controls, asset/alert inspection, district → mandal registry filters, boundary-source display, theme/language foundations and existing workflow screens | Wire statewide registry/ingestion APIs, district/mandal/asset drill-down, Asset 360, imagery freshness/coverage and processing-run inspection |
| 13 | Citizen reporting portal | **Partial** | Citizen web reporting, incident association, satellite review and citizen-safe status workflow; admin operations queue/retry dashboard is in PR #28 pending CI | Full end-to-end journey tests, location resolution edge cases, queue/retry visibility and citizen-safe status lifecycle |
| 14 | WhatsApp / SMS channels | **Partial** | WhatsApp webhook verification/signature handling, inbound signal normalization and explicit provider-readiness state; PR #28 exposes inbound disabled/configured status and SMS/WhatsApp readiness | Provider credentials/configuration, media retrieval/scanning, approved outbound templates, DLT/WhatsApp approvals and delivery receipts |
| 15 | Social/news intelligence | **Partial** | Provider-neutral social signal ingestion API, normalization, hashed author references, idempotency and keyword hints | No provider-specific API clients/OAuth lifecycle, approved source permissions, backfill/scheduling, correlation and operational review queue |
| 16 | Notifications, routing and SLA escalation | **Partial** | Notification/outbox, reminders, digests, delivery log/channel status APIs and privacy-safe citizen retry/operations visibility (PR #28 pending CI) | Confirm current owner-approved scope; provider delivery, officer routing/contact registry, retries, SLA dashboards and digest/reminder acceptance tests |
| 17 | Field operations and evidence capture | **Legacy/prototype capability; scope restricted** | Earlier milestone history records a field PWA, offline queue, photo hashes and field evidence | Do not reintroduce superseded field-app/field-officer flows without a new owner decision; retain only explicitly approved evidence capabilities |
| 18 | Evidence packs, audit and reporting | **Partial** | Append-only audit, evidence-pack generation/hash verification, monthly reporting/bulletin foundations and export logging | Revalidate currently approved pack workflow, counsel wording/signature authority, current report requirements and production retention |
| 19 | ML model registry and review prioritisation | **Partial** | Model registry/evaluation/approval/promotion APIs and baseline/fallback inference foundations | No independently trained/approved production model on Telangana verified labels; no model should drive enforcement or legal conclusions |
| 20 | AI Copilot / RAG | **Not implemented** | No production copilot/RAG experience established | Future phase: permission-aware, read-only, source-grounded answers with citations and explicit unknowns |
| 21 | Government system integrations | **Placeholder only** | API contracts, adapter seams, file-import templates and demo/seed pathways | No live calls or production credentials; wait for government sponsorship, data-sharing agreements, ownership and API approval |
| 22 | Security, privacy and production operations | **Partial / not production-ready** | Audit, secret/config patterns, pipeline token boundary, CI and data-isolation foundations | SSO/MFA, department RLS verification, secrets/workload identity, India-region hosting, encryption, VAPT, HA/DR, restore/load/soak and incident response |

## Detection and backtest checkpoint

### Non-scored tuning evidence

The detect-v2 workflow run completed successfully on 26 November 2026 (PR #23 merged):

- Workflow run: [45780430533](https://github.com/aitech2025/lake-protect/actions/runs/45780430533)
- Artifact: `m2-detect-v2-tuning-2026-11-20` (artifact ID `15098336015`)
- As-of date: 20 November 2026; five non-scored tuning lakes.
- Rules SHA-256: `7e3ae2398bab87c1133a7a6ecefafe5b4407c8a7a428fdc0b7999cb998fa2a36`.
- Three clearing candidates totalling 5.78 acres; no final levelling candidate.
- 2,068 raw OTHER→BARE pixels; 72 remained after temporal controls.
- Detect-v1 run4 had 14 clearing candidates / 20.19 acres. The 11 former candidate footprints that disappeared require diagnostic comparison.

PR #25 adds review-only sub-threshold levelling component geometries and before/after chips in `diagnostics.geojson` and `chips/diagnostics/`; these are excluded from candidate/alert outputs. The 11 disappeared detect-v1 candidate footprints still require a run4/run5 spatial comparison and human review. This is tuning evidence only, not a detection accuracy result. Do not freeze detect-v2 or run the scored backtest until the diagnostic review is complete.

### Scored case evidence

The 27 entries in `data/case-register.csv` are discovery leads, not verified ground truth. The scoring manifest remains empty until each admitted case has independently supported exact event date, public-action date, affected area, event geometry and provenance. Durgam Cheruvu's pre-tuning exposure must be disclosed in the final report.

## CI and branch checkpoint

- PR #21 merged: P0.3–P0.6 CI baseline repair. Its recorded validation was API/PostGIS 387 passed, pipeline 77 passed and web build passed.
- PR #22 merged: weekly resumable historical replay. Its recorded validation was API/PostGIS 387 passed, pipeline 84 passed and web build passed.
- PR #23 merged: detect-v2 tuning workflow/correction; tuning and standard CI passed.
- PR #25 merged: sub-threshold levelling diagnostics and review chips; CI passed.
- PR #26 merged: M3 replay timestamp/unique-ID/geometry guardrails; CI passed.
- PR #27 merged: district/mandal registry filters and boundary-source label; CI passed.
- PR #28 open: privacy-safe citizen operations queue/retry/provider-readiness dashboard; full CI in progress.
- PR #24 closed without merge because its docs branch conflicted with the updated plan; this status update replaces it.
- Canonical development branch remains `feature/consolidated`. Do not merge feature work directly to `main` without a separate release decision.

## Recommended next implementation sequence

1. **Complete the run4/run5 spatial diff** for the 11 disappeared detect-v1 candidate footprints; inspect the new levelling diagnostic chips and record human dispositions.
2. **Verify M3 case evidence**: exact event dates, public-action dates, affected areas, event polygons and provenance. Do not infer missing facts.
3. **Freeze and score** only after the independent case set and detect-v2 rule review are complete; run once and publish metrics, misses, false flags, lead times and limitations.
4. **Finish P2 acceptance**: authoritative department hierarchy, source-class normalisation, imagery coverage/freshness and consolidated UI integration tests.
5. **Finish PR #28** after all CI checks pass, then validate real (non-demo) citizen review/retry scenarios.
6. **Production gates**: government authorization, RLS/SSO, security, hosting, HA/DR and counsel review remain later gates.

## Explicit non-goals until owner approval

- No live government API calls, scraping or use of government credentials.
- No treating OSM-derived or user-drawn boundaries as certified legal boundaries.
- No legal verdict, encroachment finding, demolition recommendation or automatic enforcement action from imagery or AI.
- No claim of guaranteed weekly high-resolution satellite imagery.
- No restoration of superseded field-officer, multi-person closure, escalation-timer or officer-record functionality without an explicit owner decision.
