# GeoGuard implementation plan

**Branch:** `feature/consolidated`  
**Plan owner:** Product owner / implementation agent  
**Baseline commit:** `65ce4c4bcf4f1d938987c92c1d2012c49642870f`  
**Plan created:** 26 November 2026  
**Status:** Active — Phase 1 started  
**Source of truth:** `CONTEXT.md`, latest applicable owner decisions in `DECISIONS.md`, current code, and focused design documents.

> This is a living plan. Update the status, evidence, commit/PR and test result for each task as work progresses. Do not mark a task done merely because code exists; its acceptance criteria must be demonstrated.

## 1. Product guardrails

1. Satellite observations describe physical change, not illegality. Officials make decisions; the product must not label a site illegal or recommend demolition.
2. Boundary status and provenance must be visible. Derived/unconfirmed boundaries remain watch-only.
3. Detect new change after the applicable baseline; do not turn legacy structures into new alerts.
4. Detection remains owner-blind. Do not ingest or expose owner/claimant personal data in detection outputs.
5. Government integrations remain templates/placeholders until the owner confirms an agreement. No scraping or live government calls.
6. Distinguish `not_observed`, `no_usable_look`, `failed`, `no_candidate` and `candidate_found`.
7. Use real data only where the current product decision requires it; synthetic samples must be clearly marked and isolated.
8. Follow the latest owner decisions (especially D-057 onward). Do not restore superseded field-app, field-officer, two-person closure, escalation-timer or officer-record functionality without a new owner decision.
9. Preserve append-only boundaries, audit history, evidence hashes and database state guards.
10. Do not claim weekly high-resolution imagery. Revisit, cloud cover, licensing and resolution are provider-dependent.

## 2. Baseline and known gaps

| Area | Baseline at plan creation | Evidence / note |
|---|---|---|
| Canonical development branch | `feature/consolidated` at `65ce4c4` | PR #19 merged |
| M0–M19 | Recorded as complete in `PROGRESS.md` | Milestone history; verify current code before extending |
| M3 scored blind backtest | Not started / not scored | `PROGRESS.md`; M2 tuning is explicitly not an accuracy result |
| Backtest code | Partial | `geospatial/backtest.py` scores supplied GeoJSON; it does not perform historical weekly imagery replay |
| Ground-truth case set | Not ready | `data/case_lake_search.yml` contains name patterns, not verified event labels/boundaries |
| Rule freeze | Not done | `detect_rules.yaml` is `detect-v2`; no git tag exists at baseline |
| Historical disclosure | Required | Durgam Cheruvu was seen once before tuning (D-042); disclose in M3 report |
| Tuning evidence | Available | Five non-scored tuning lakes; see `reports/m2-tuning/README.md` |
| Geospatial engine | Backend integrated | PR #19; registry APIs not yet fully surfaced in the desk |
| Government sources | Templates/file imports | No live government integration without agreement |
| API CI | Known baseline failures | Latest recorded run: API job failed; pipeline and web jobs passed. Earlier baseline and integrated runs both had 40 API failures (see PR #19/run history). |
| Department data isolation | Not production-ready | Department-level RLS deliberately deferred in PR #19 |
| AI copilot/RAG | Not implemented | Separate future phase; must cite source records and avoid legal conclusions |

## 3. Delivery phases and priorities

### Phase 0 — Establish a reliable engineering baseline

**Goal:** make every subsequent change measurable and safe.

- [x] P0.1 Confirm canonical branch and baseline commit.
- [x] P0.2 Review CI status after PR #19.
- [ ] P0.3 Classify the 40 known API/PostGIS failures into product regressions, environment/test-fixture issues and pre-existing defects.
- [ ] P0.4 Establish a reproducible local test command set and record baseline results.
- [ ] P0.5 Resolve only failures that block the backtest or core demo; track unrelated failures separately.
- [ ] P0.6 Ensure CI uploads useful failure summaries and runs pipeline, API/PostGIS and web checks on every PR.

**Exit criteria:** known failures have owners/root causes; test commands and expected baseline are documented; no new regression is hidden by a baseline waiver.

### Phase 1 — Gate 1: complete the blind historical backtest (highest priority)

**Goal:** determine whether the frozen detection rules identify enough independently verified historical events before public action. This is the PRD's first deliverable and must precede accuracy claims in a government pitch.

#### 1A. Case evidence and eligibility

- [ ] M3.1 Create a case register for the 30 target events from the PRD case list.
- [ ] M3.2 Verify each event against a cited public source: exact location, event/change date, public-action date (or explicit null), and independently assessed affected area.
- [ ] M3.3 Obtain/trace a defensible event polygon for each case; record its source, author, date and confidence.
- [ ] M3.4 Record ineligible cases with explicit reasons; do not silently omit them or count them in the denominator.
- [ ] M3.5 Ensure tuning lakes are excluded from the scored set and record the Durgam Cheruvu pre-tuning exposure disclosure.

#### 1B. Freeze and reproduce the detector

- [ ] M3.6 Review the final `detect-v2` rule file and tuning evidence; do not change thresholds using scored-case results.
- [ ] M3.7 Freeze the exact rule file and dependencies in an immutable git tag before scoring. Record commit SHA and SHA-256.
- [ ] M3.8 Implement/complete a weekly historical replay runner from the Sentinel-2 and Sentinel-1 STAC archives.
- [ ] M3.9 Enforce strict as-of filtering: every scene acquisition timestamp must be at or before that replay date. Add tests proving no look-ahead.
- [ ] M3.10 Make runs resumable and cache windowed asset imagery; never download full scenes unnecessarily.
- [ ] M3.11 Run the scored set once against the frozen rules. Any rerun after rule changes must use a new tag and be disclosed.

#### 1C. Score, inspect and report

- [ ] M3.12 Improve scoring to validate CRS, dates, IDs, geometries and eligibility before metrics are calculated.
- [ ] M3.13 Match a detection only when it intersects the event geometry and its alert date precedes the public-action date.
- [ ] M3.14 Report true/false positives, misses, precision, recall, F1, median lead time, false flags per lake-year, sensor/season breakdown and ineligible cases.
- [ ] M3.15 Generate before/after chips for every scored case, including misses, with acquisition dates and sensor labels.
- [ ] M3.16 Manually inspect a sample of false flags against high-resolution history. High-resolution imagery is validation-only, never a pipeline input or evidence-pack input.
- [ ] M3.17 Publish a signed-off report with limitations and the Durgam Cheruvu disclosure.

**Gate 1 pass criterion:** at least 21 of 30 eligible known events over 0.25 acre flagged before public action, per CONTEXT.md. If fewer than 30 eligible cases can be verified, report the actual denominator and do not claim a 21/30 pass. A partial result is still useful but is not a pass.

**Exit criteria:** reproducible frozen run, no-look-ahead tests, complete case accounting, metrics/chips and written limitations. No fabricated or inferred event labels.

### Phase 2 — Complete the geospatial foundation in the product UI

**Goal:** make the newly integrated statewide registry and processing services usable from the existing GeoGuard desk without replacing the current working screens.

- [ ] P2.1 Map the new registry/ingestion APIs to current UI navigation and data contracts.
- [ ] P2.2 Add a statewide registry view with department, administrative unit, asset and parcel hierarchy.
- [ ] P2.3 Add asset 360 linking boundaries and versions, source records, survey references, weekly screens, incidents, documents and evidence.
- [ ] P2.4 Add source/provenance labels: official record, imported file, OSM-derived, user-drawn, demo/sample.
- [ ] P2.5 Add imagery freshness and coverage states, including no usable look and failed processing.
- [ ] P2.6 Show geospatial screening candidates as review leads; never present MNDWI/radar output as a legal finding.
- [ ] P2.7 Provide clear provider configuration states: not configured, demo/sample, configured, connected, failed. Do not imply live provider connectivity when credentials are absent.
- [ ] P2.8 Add API/UI integration tests for registry search, asset detail, boundary provenance and processing-run visibility.

**Exit criteria:** a senior official can navigate from State/district to asset, inspect authoritative status/provenance and see the latest screening state without using raw APIs.

### Phase 3 — Improve the current two-role incident and citizen workflows

**Goal:** complete the latest approved product workflow, not the superseded multi-role workflow.

- [ ] P3.1 Validate the complete citizen journey: web report → location resolution → incident association/creation → satellite review → official notification → review/decision → citizen-safe status update.
- [ ] P3.2 Add operational health/queue visibility for citizen satellite review jobs and retries.
- [ ] P3.3 Complete provider-ready WhatsApp inbound configuration and clearly expose the disabled/unconfigured state.
- [ ] P3.4 Complete approved SMS/WhatsApp outbound templates only after the relevant gateway, DLT/WhatsApp approvals and owner authorization.
- [ ] P3.5 Validate acknowledgement reminders, 48-hour admin follow-up and weekly digests with idempotency tests.
- [ ] P3.6 Complete admin boundary/source conflict resolution tools; never auto-downgrade a boundary.
- [ ] P3.7 Improve the asset legal register for source-linked survey numbers, land category, Section 22A and court status as data becomes lawfully available.
- [ ] P3.8 Keep owner/claimant personal data out of ordinary screens and evidence exports.

**Exit criteria:** end-to-end tests demonstrate the approved two-role workflow and citizen-safe updates, with all external channels honestly marked as placeholders until authorized.

### Phase 4 — Intelligence and advanced detection

**Goal:** add intelligence only after the base detector and data provenance are trustworthy.

- [ ] P4.1 Evaluate levelling separately (D-058) on non-scored tuning data; document false-positive patterns.
- [ ] P4.2 Establish model evaluation/approval gates before any ML model can influence prioritisation.
- [ ] P4.3 Add an AI copilot/RAG over asset, incident, boundary, legal-document and screening records with citations to source documents and timestamps.
- [ ] P4.4 Ensure the copilot distinguishes known facts, missing data and hypotheses; no legal verdicts or enforcement recommendations.
- [ ] P4.5 Add authorized social/news/CCTV signal connectors only when provider permissions and data governance are approved.
- [ ] P4.6 Add forest/endowment land only after category-specific data, boundary authority and detection tuning are ready. Forest vegetation seasonality needs separate validation.

**Exit criteria:** measured evaluation, human review, traceable model/version provenance and no unsupported legal conclusions.

### Phase 5 — Government integration and production readiness

**Goal:** move from demo placeholders to an approved, secure deployment only after government sponsorship and data-sharing authorization.

- [ ] P5.1 Agree data ownership, data-sharing agreements, API contracts, refresh frequency and responsible departments.
- [ ] P5.2 Implement live government connectors behind the existing source-engine interfaces; keep file import as a fallback.
- [ ] P5.3 Implement maker-checker boundary certification with authorized Revenue/Irrigation sign-off, notification/order references and append-only versions.
- [ ] P5.4 Design and test department/jurisdiction-level authorization and PostgreSQL RLS against the consolidated two-role model or an owner-approved expanded role model.
- [ ] P5.5 Add government SSO/MFA, secrets management, encryption, audit review and vulnerability assessment.
- [ ] P5.6 Establish India-region hosting, HA/DR, backups, monitoring, incident response and operational SLAs.
- [ ] P5.7 Obtain counsel approval for buffer rules, field-observation wording and the Section 63(4) certificate before any legal-use claim.
- [ ] P5.8 Complete load, resilience, restore and security testing before production.

**Exit criteria:** written approvals, tested integrations, approved legal templates, security sign-off and operational readiness evidence.

## 4. Work sequencing

The intended order is:

1. Phase 0 baseline and CI triage (in parallel with M3 preparation).
2. Phase 1 blind backtest — first product gate; do not skip it.
3. Phase 2 geospatial UI and asset 360 — makes the merged backend visible to officials.
4. Phase 3 citizen/incident workflow hardening.
5. Phase 4 AI and advanced intelligence.
6. Phase 5 government integrations and production readiness.

Phase 2 UI work can proceed in parallel with M3 data verification, but it must not delay the blind backtest or be presented as evidence of detection accuracy.

## 5. Branching, review and release discipline

- `feature/consolidated` is the canonical development branch for this plan.
- Use short-lived `feature/*` branches for implementation increments and PRs back to `feature/consolidated`.
- Do not merge to `main` or change the repository default branch as part of feature work without a separate release decision.
- Every PR must link plan task IDs, include migration notes where relevant, and state test results.
- Never force-push the canonical branch. Never delete branches referenced by open PRs without review.
- Keep large imagery, cache files, secrets and personal data out of git.
- Update this plan in the same PR/commit as each completed task or meaningful blocker.

## 6. Status ledger

| Task | Status | Latest evidence / next action |
|---|---|---|
| P0.1 canonical branch baseline | Done | `feature/consolidated`, baseline `65ce4c4` |
| P0.2 CI status review | Done | PR #20 run `45757478902`: pipeline 66 passed, web build passed; API 347 passed / 40 failed (same 40 baseline failures) |
| P0.3–P0.6 CI triage | Not started | Classify 40 known API failures and establish a reproducible baseline |
| M3.1–M3.5 case evidence | In progress | 21 PRD starter leads inventoried in `data/case-register.csv`; validator/template/docs implemented; actual event evidence remains unverified and manifest remains empty |
| M3.6–M3.7 freeze rules | Not started | `detect-v2`; no tag exists. Freeze only after confirming the rules and case protocol |
| M3.8–M3.11 weekly replay | Not started | Existing scoring utility only; replay orchestration remains to build |
| M3.12–M3.17 scoring/report | Partial | `geospatial/backtest.py` is a basic scorer; complete validation and report outputs remain |
| P2 geospatial UI | Not started | Registry APIs merged by PR #19; UI wiring remains |
| P3 incident/citizen hardening | Partial | Core M12–M17 flows exist; provider-dependent channels and operational hardening remain |
| P4 intelligence | Not started | ML utilities/registry foundation exist; no approved production model or RAG copilot |
| P5 production readiness | Not started | Government integration placeholders only; department RLS and security/ops gates remain |

## 7. Current execution checkpoint

**First active work item:** M3.1–M3.5 — blind-backtest case evidence inventory and validation.

The first increment has started on `feature/m3-case-validation`:
1. Inspected the PRD's section 13 starter list and `data/case_lake_search.yml`; they are discovery hints, not verified ground truth.
2. Added `data/cases.template.geojson` as an intentionally empty case manifest. No event labels or geometries were invented.
3. Added `docs/backtest-case-register.md` with required evidence, eligibility and privacy rules.
4. Added `pipeline/lake_protect/geospatial/cases.py` and `lp-geo validate-cases` to validate source, dates, area, geometry provenance, CRS, duplicate IDs and personal-data exclusions.
5. Added focused tests in `pipeline/tests/test_backtest_cases.py`. CI/test execution is pending the PR.

**Still blocked:** no independently verified case polygons and event/action dates are present in the repository. The case manifest remains empty. The scored backtest will not run until evidence is verified and the detector rules are frozen.


## 8. Execution log

### 26 November 2026 — M3 case-evidence validation started

- Created this plan on `feature/consolidated` at commit `e7321a7`.
- Created implementation branch `feature/m3-case-validation` from that plan commit.
- Added a machine-readable empty GeoJSON case manifest, case-register documentation, validation module, CLI command and focused tests.
- The validator requires explicit event/action dates, independent area source, verified event-footprint provenance and EPSG:4326 geometry. It excludes cases with unknown action dates, non-exact event dates, unverified geometry, pre-2018 events or area at/below 0.25 acre from the primary gate.
- No actual case was admitted or scored. Source verification and geometry tracing remain human evidence tasks.
- Next: run the focused pipeline suite in CI, fix any failures, then build the evidence inventory from the PRD starter cases without guessing missing values.


### 26 November 2026 — PR #20 CI result

- PR: https://github.com/aitech2025/lake-protect/pull/20
- CI run: https://github.com/aitech2025/lake-protect/actions/runs/45757478902
- Pipeline tests: **66 passed** (including the new case-validation tests).
- Web type-check/build: **passed**.
- API/PostGIS: **347 passed, 40 failed**. The failure count and failure set match the previously recorded baseline; this increment changes no API code. The full API suite is therefore not green, but the new pipeline validation suite is green.
- PR remains open for review; it has not been merged into `feature/consolidated` yet.


### 26 November 2026 — PRD case leads inventoried

- Added `data/case-register.csv` with 21 leads from CONTEXT.md section 13.
- The register preserves the PRD's approximate date anchors and reported area notes as text. It does not convert month/year ranges into exact event dates or infer affected polygons.
- All 21 rows remain `unverified` and `needs_verification`, except the Bhagirathamma/Tautanikunta boundary-uncertainty cases explicitly marked `exclude_pending_boundary`.
- The GeoJSON scoring manifest remains empty until exact dates, public-action dates, independently supported areas, source evidence and verified event footprints are available.
- PR #20 has been updated with the inventory; the latest commit will receive a fresh CI run.
