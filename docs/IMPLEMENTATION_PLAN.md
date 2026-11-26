# GeoGuard implementation plan

**Branch:** `feature/consolidated`  
**Plan owner:** Product owner / implementation agent  
**Baseline commit:** `99b56e06a0eb6395280797a8b154b16af8924a41` (after PRs #31–#36)  
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
| Canonical development branch | `feature/consolidated` at `0588ab2` | PRs #19, #21–#23, #25–#27 merged |
| M0–M19 | Recorded as complete in `PROGRESS.md` | Milestone history; verify current code before extending |
| M3 scored blind backtest | Not started / not scored | `PROGRESS.md`; M2 tuning is explicitly not an accuracy result |
| Backtest code | Partial, materially hardened | Weekly replay is implemented; scorer now requires replay `detected_at`, stable unique detection IDs and valid EPSG:4326 geometry. Verified cases and a scored run remain blocked |
| Ground-truth case set | Not ready | `data/case_lake_search.yml` contains name patterns, not verified event labels/boundaries |
| Rule freeze | Not done | `detect_rules.yaml` is `detect-v2`; no git tag exists at baseline |
| Historical disclosure | Required | Durgam Cheruvu was seen once before tuning (D-042); disclose in M3 report |
| Tuning evidence | Available | Five non-scored tuning lakes; see `reports/m2-tuning/README.md` |
| Geospatial engine | Backend integrated; UI drill-down advanced | Existing Asset 360 plus PR #27 district/mandal filters and boundary-source provenance; full official registry hierarchy remains open |
| Government sources | Templates/file imports | No live government integration without agreement |
| API CI | Green on merged increments | PR #21 baseline repair; PRs #25–#27 passed their CI workflows. PR #28 merged after API/PostGIS, pipeline, web and E2E CI passed. |
| Department data isolation | Not production-ready | Department-level RLS deliberately deferred in PR #19 |
| AI copilot/RAG | Not implemented | Separate future phase; must cite source records and avoid legal conclusions |

## 3. Delivery phases and priorities

### Phase 0 — Establish a reliable engineering baseline

**Goal:** make every subsequent change measurable and safe.

- [x] P0.1 Confirm canonical branch and baseline commit.
- [x] P0.2 Review CI status after PR #19.
- [x] P0.3 Classify all 40 API/PostGIS failures into test-fixture/product-contract mismatches, an obsolete source-test expectation and one WhatsApp product defect.
- [x] P0.4 Establish reproducible API/PostGIS, pipeline and web test commands; record environment and baseline results in `docs/ci-baseline-triage.md`.
- [x] P0.5 Repair the 40-failure API baseline without weakening demo isolation or database invariants; full API/PostGIS suite now passes.
- [x] P0.6 Add JUnit XML reports, always-run job summaries and artifact uploads for API/PostGIS and pipeline jobs; all three checks run on PRs.

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
- [x] M3.8 Implement/complete a weekly historical replay runner from the Sentinel-2 and Sentinel-1 STAC archives. `lp historical-replay` reuses the production screen; Sentinel-1 checks are enabled by default for built candidates.
- [x] M3.9 Enforce strict as-of filtering: every scene acquisition timestamp must be at or before that replay date. The STAC query, returned-item filter and raster readers enforce this; `pipeline/tests/test_no_lookahead.py` covers the catalogue and pixel-reader guards.
- [x] M3.10 Make runs resumable and cache windowed asset imagery; never download full scenes unnecessarily. The replay checkpoints each date and fingerprints the AOI/rules/range; existing STAC and windowed COG caches are reused.
- [ ] M3.11 Run the scored set once against the frozen rules. Any rerun after rule changes must use a new tag and be disclosed.

#### 1C. Score, inspect and report

- [x] M3.12 Complete scorer validation. PR #32 requires explicit EPSG:4326 detection CRS, validates Polygon/MultiPolygon bounds and computes IoU in EPSG:32644; adds median lead time and sensor/season/event-type breakdowns. Full false-flags-per-lake-year and signed report remain in M3.14–M3.17.
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
- [ ] P2.2 Complete the statewide registry hierarchy. Existing asset map/list and dashboard drill-down are present; PR #27 adds district → mandal filters. Department/source hierarchy and authoritative master-code mapping remain.
- [ ] P2.3 Complete Asset 360 integration. Existing page links boundaries/versions, registry links, survey parcels, weekly screens and documents; incident/evidence cross-linking and full source completeness remain.
- [x] P2.4 Add conservative boundary provenance classes in Asset 360. PR #33 adds source classes, source metadata and authority state; PR #35 fixes OSM-vs-generic-derived classification. Both are merged and CI passed.
- [ ] P2.5 Add imagery freshness and coverage states, including no usable look and failed processing.
- [ ] P2.6 Show geospatial screening candidates as review leads; never present MNDWI/radar output as a legal finding.
- [ ] P2.7 Provide clear provider configuration states: not configured, demo/sample, configured, connected, failed. Do not imply live provider connectivity when credentials are absent.
- [ ] P2.8 Complete API/UI integration tests. PR #27 adds district/mandal filter E2E coverage; registry search, asset detail, boundary provenance and processing-run coverage still need a consolidated acceptance suite.

**Exit criteria:** a senior official can navigate from State/district to asset, inspect authoritative status/provenance and see the latest screening state without using raw APIs.

### Phase 3 — Improve the current two-role incident and citizen workflows

**Goal:** complete the latest approved product workflow, not the superseded multi-role workflow.

- [ ] P3.1 Validate the complete citizen journey: web report → location resolution → incident association/creation → satellite review → official notification → review/decision → citizen-safe status update.
- [ ] P3.2 Add operational health/queue visibility for citizen satellite review jobs and retries. Implemented and merged in PR #28; full CI passed.
- [ ] P3.3 Expose provider-ready WhatsApp inbound configuration and disabled state. Readiness and disabled state are visible in merged PR #28; actual webhook remains disabled until State credentials/authorization are supplied.
- [ ] P3.4 Keep SMS/WhatsApp outbound templates held until the relevant gateway, DLT/WhatsApp approvals and owner authorization; no live provider activation in this demo.
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

## 6. Current status ledger — 26 November 2026

| Task | Status | Latest evidence / next action |
|---|---|---|
| P0 baseline and CI | Complete | API/PostGIS, pipeline and web CI were restored in PR #21; latest canonical runs after PRs #31–#34 are green. |
| M2 detect-v2 diagnostics | Implemented; review pending | PR #25 exports sub-threshold levelling diagnostics separately from alert candidates. PR #31 adds run4/run5 polygon comparison CLI. The run4/run5 comparison has completed: 14 run4 candidates vs 3 run5 candidates; 2 spatial matches, 12 unmatched run4 footprints and 1 unmatched run5 footprint. All remain human-review leads, not accuracy labels. |
| M3.1–M3.5 case evidence | Blocked on external evidence | 27 discovery leads are recorded; none is independently verified. Exact event dates, public-action dates, affected areas and verified event polygons are still required. |
| M3.6–M3.7 rule review/freeze | Blocked | Five-lake non-scored tuning exists, but run4/run5 footprint review is incomplete. No immutable detect-v2 tag exists. |
| M3.8–M3.10 replay | Implemented | Weekly resumable replay and no-look-ahead controls exist; replay detections now explicitly carry EPSG:4326 CRS metadata. |
| M3.11 scored replay | Blocked | Do not run until the eligible case manifest is independently verified and detector rules are frozen. |
| M3.12 scorer validation | Complete in code | PR #32 enforces explicit detection CRS, geometry contract, metric IoU and auditable scoring breakdowns. |
| M3.13–M3.17 scoring/report | Partial / blocked | Temporal matching and review-gated precision exist. Scored run, complete false-flag rates, case chips, independent adjudication and signed report remain. |
| P2 registry / Asset 360 | Improved; partial | PR #27 adds district/mandal filters; PR #33 adds boundary provenance classes and display. Official department hierarchy, coverage/freshness states and consolidated acceptance suite remain. |
| P3 citizen workflow | Partial | PR #28 adds admin review/retry operations visibility. Real non-demo queue/retry journey validation and provider authorization remain. |
| P4 intelligence | Not started as a product capability | ML foundations exist; no approved production model or source-grounded RAG copilot. |
| P5 readiness diagnostics | Implemented as diagnostics only | PR #34 adds admin-only `GET /readiness`. It always reports production certification as not performed and lists RLS, SSO/MFA, government authorization, HA/DR and security review as unverified. |
| P5 production gates | Not complete | Government agreements, RLS, SSO/MFA, India-region hosting, VAPT, backup restore, HA/DR and load/resilience tests remain. |

## 7. Current execution checkpoint

**First active work item:** M3.1–M3.5 — blind-backtest case evidence inventory and validation.

The first increment has started on `feature/m3-case-validation`:
1. Inspected the PRD's section 13 starter list and `data/case_lake_search.yml`; name matches are discovery hints, not ground truth.
2. Added `data/case-register.csv` with 27 leads and explicit source-review status, event-date precision, public-action-date precision, case role and scoring lane. Reporting/action dates are not misrepresented as the date the underlying change began.
3. Classified 2014–2023 cases as historical detection-only, restoration actions as controls, Khajaguda boundary disputes as boundary controls, Durgam Cheruvu as exposed under D-042, and ambiguous Pedda Cheruvu identity as unresolved.
4. Added the empty GeoJSON manifest, evidence register documentation, strict validator and `lp-geo validate-cases` command.
5. Hardened `geospatial/backtest.py`: only validator-eligible cases can score; detections must occur on/after event and strictly before public action; exactly 0.25 acre is excluded; unknown public-action dates cannot be counted as early-warning hits; unmatched detections are not false positives until reviewed with reviewer identity, review date and evidence.
6. Added focused scorer tests in `pipeline/tests/test_backtest_scoring.py` and updated legacy backtest fixtures to satisfy the evidence contract.
7. Added `docs/m3-government-evidence-request.md`, a structured request checklist for TGRAC, HYDRAA, HMDA, Irrigation and Revenue records.

**Still blocked:** none of the 27 leads has a verified event footprint and complete event/action evidence. The scoring manifest remains empty. The scored backtest will not run until source evidence is independently verified and detector rules are frozen.


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
- This checkpoint was written before merge; PR #20 was subsequently merged to `feature/consolidated` as `cb3b8d7913b922b3e6075e4bb2e3a8583dcb9206` (see the merge log below).


### 26 November 2026 — PRD case leads inventoried

- Added `data/case-register.csv` with 21 leads from CONTEXT.md section 13.
- The register preserves the PRD's approximate date anchors and reported area notes as text. It does not convert month/year ranges into exact event dates or infer affected polygons.
- All 21 rows remain `unverified` and `needs_verification`, except the Bhagirathamma/Tautanikunta boundary-uncertainty cases explicitly marked `exclude_pending_boundary`.
- The GeoJSON scoring manifest remains empty until exact dates, public-action dates, independently supported areas, source evidence and verified event footprints are available.
- PR #20 has been updated with the inventory; the latest commit will receive a fresh CI run.


### 26 November 2026 — Recommended next increment executed

- Expanded the discovery inventory from 21 to **27 named leads** using the PRD list and additional cases described in the SANDRP Hyderabad lakes review and other cited reporting.
- Reworked the register so it distinguishes event-date precision from public-action-date precision and separates primary candidates from historical-only cases, authorized-restoration controls, boundary-uncertainty controls and unresolved identities.
- Identified a scoring integrity defect in the previous backtest: a case with unknown public-action date could be matched and labelled `before_public_action=true`; the scorer also treated exactly 0.25 acre as eligible despite the PRD requiring over 0.25 acre, and counted every unmatched detection as a false positive without human review.
- Reworked the scorer to use the case validator's primary eligibility set, enforce event-date/public-action-date ordering, apply the strict area threshold and require documented human review before counting false positives. Unmatched detections now keep precision pending rather than silently inflating/deflating it.
- Added focused temporal and adjudication tests. CI run `45765808663`: pipeline **77 passed**, web build passed; API/PostGIS **347 passed / 40 failed**, matching the pre-existing baseline.
- Merged PR #20 into `feature/consolidated` as `cb3b8d7913b922b3e6075e4bb2e3a8583dcb9206`.
- No cases have been promoted to verified ground truth; no detection metrics have been generated. This is intentional until official records, imagery dates and event footprints are verified.

### Evidence sources consulted

- SANDRP, *Hyderabad Lakes 2025: Degradation Continues Amid HYDRAA Efforts*: https://sandrp.in/2026/02/17/hyderabad-lakes-2025-degradation-continues-amid-hydraa-efforts/
- The News Minute, *Telangana: 171 natural water tanks encroached in past 10 years, says govt report*: https://www.thenewsminute.com/telangana/telangana-171-natural-water-tanks-encroached-in-past-10-years-says-govt-report
- The News Minute, Khajaguda boundary/procedure case: https://www.thenewsminute.com/telangana/telangana-hc-raps-hydraa-again-for-hasty-evictions-questions-proof-of-violations
- Deccan Chronicle, *HYDRAA Protects Muskin Cheruvu From Encroachers*: https://www.deccanchronicle.com/southern-states/telangana/hydraa-protects-muskin-cheruvu-from-encroachers-1960200

These articles are discovery references only. They are not substitutes for certified boundaries, official event records or independently traced event polygons.


### 26 November 2026 — Government evidence request prepared

- Added `docs/m3-government-evidence-request.md` with the exact spatial, temporal, legal-status and provenance fields needed from TGRAC, HYDRAA, HMDA, Irrigation and Revenue departments.
- Requested the original 171-tank report and spatial annexures, exact comparison dates, dated enforcement records, official boundary versions, event footprints and five non-scored tuning lakes.
- The document explicitly asks departments to distinguish physical event date from first public/official action date, and total FTL area from the actual event footprint.
- Latest CI run `45765808663` completed: pipeline **77 passed**, web build passed, API/PostGIS **347 passed / 40 failed** (same baseline failure count).


### 26 November 2026 — PR #20 merged

- PR #20 merged to `feature/consolidated`: https://github.com/aitech2025/lake-protect/pull/20
- Merge commit: `cb3b8d7913b922b3e6075e4bb2e3a8583dcb9206`.
- Validation run: https://github.com/aitech2025/lake-protect/actions/runs/45765808663
- Pipeline: **77 passed**. Web build: **passed**. API/PostGIS: **347 passed, 40 failed**, same 40 pre-existing baseline failures.
- The case register, strict validator, hardened scorer, tests and government evidence request are now part of the canonical branch.

### 26 November 2026 — Latest canonical-branch CI status (run #269)

- Branch: `feature/consolidated`; commit: `d17fce6cad68bb321b3590f7cd22afcdcbd6f993`.
- Workflow run: https://github.com/aitech2025/lake-protect/actions/runs/45766083814
- Overall GitHub Actions conclusion: **failure**.
- Pipeline tests: **77 passed** (job succeeded).
- Web type-check/build: **passed** (job succeeded).
- API/PostGIS integration tests: **347 passed, 40 failed** (job failed; 1 warning). The API failure set remains the outstanding CI blocker; the run log records failures across boundaries, citizen reports, dashboard, lifecycle, locations, monthly reports, notifications, rules mode and source fixtures.
- This confirms the M3 pipeline changes and web build remain green on the canonical branch. It does **not** make the complete CI pipeline green. The 40 API/PostGIS failures still need root-cause classification and remediation; do not describe them as fixed.
- No change to backtest evidence status: 27 discovery leads remain unverified, the scoring manifest is empty and no detection metrics have been generated.

### 26 November 2026 — P0.3–P0.6 CI baseline restored

- Compared API/PostGIS logs from runs `45765808663` and `45766083814`; all 40 failing test names and signatures are identical. Both runs report 347 passed / 40 failed.
- Inspected the failing tests, test factories, API filtering and current D-057/D-065 behavior. Classified 38 failures as ordinary test fixtures incorrectly marked demo, one source test as an obsolete expectation that demo connector samples should appear in the real-asset API, and one as a genuine WhatsApp handler `NameError`.
- Added `docs/ci-baseline-triage.md` with evidence, classifications, CI commands/environment and repair acceptance criteria.
- On `feature/p0-ci-triage`, changed ordinary API test factory defaults to non-demo while allowing explicit demo fixtures; updated the demo SMTP isolation test to create an explicit demo notification; updated the source sample test to assert demo records remain hidden; passed the existing WhatsApp `is_demo` argument into `_step()` to remove the runtime NameError.
- The first repair CI run reduced the 40 failures to 7. The next run exposed two remaining test assumptions after the demo-default correction; both were fixed by explicitly marking the fixtures as demo, not by weakening production filters.
- Fixed a genuine evidence-pack defect: the demo watermark was positioned outside the printable page and therefore absent from extracted PDF text. It now appears in normal page flow.
- Added `scripts/ci_junit_summary.py` and workflow steps that write totals/failing test names to GitHub job summaries and upload API/PostGIS and pipeline JUnit reports even when tests fail.
- Final PR #21 CI run #275: API/PostGIS **387 passed, 0 failed**; pipeline **77 passed**; web type-check/build **passed**. All jobs succeeded: https://github.com/aitech2025/lake-protect/actions/runs/45776369043
- P0.3–P0.6 are complete on this feature branch. No tests were skipped, xfailed or waived. PR #21 is ready for merge; the canonical branch is unchanged until merge.
- Next plan gate: M3.1–M3.5 still require independently verifiable case records, exact event/action dates and event polygons. The government evidence request remains the next external dependency; do not invent ground truth or score unverified cases.


### 26 November 2026 — M3.8 historical replay runner started

- PR #21 merged to `feature/consolidated` as `4156a9034be7b67c9604537dcc8e88b70b20576b`; P0.3–P0.6 are complete and the canonical CI baseline is green.
- Created `feature/m3-historical-replay` from the merged canonical commit.
- Added `pipeline/lake_protect/replay.py` and the `lp historical-replay` command. It reuses the production screen at weekly as-of dates, writes a report per week, checkpoints each completed date, fingerprints the exact rules/AOI/date range, and refuses to resume into a changed configuration.
- Aggregated detections retain the first replay as-of date in `detected_at`; this is deliberately distinct from retrospective `first_changed_at` so lead-time scoring does not claim the detector knew about a change before it could satisfy its persistence rules.
- Added `pipeline/tests/test_historical_replay.py` for weekly date generation, de-duplication, earliest detection date, resume behavior and configuration mismatch refusal. Added `docs/m3-historical-replay.md` with usage and interpretation safeguards.
- PR #22 CI run: API/PostGIS **387 passed**, pipeline **84 passed**, web build **passed**; all jobs succeeded: https://github.com/aitech2025/lake-protect/actions/runs/45777436579.
- Existing no-look-ahead guards and tests were reviewed; M3.9 is marked complete. M3.8 and M3.10 remain in progress pending CI validation and confirmation that Sentinel-1 historical checks are included in the replay.
- No historical replay has been run and no detection metrics have been produced. The 27 discovery leads remain unverified; official case evidence and event polygons are still required before scoring. M3.6–M3.7 rule review/freeze and M3.1–M3.5 evidence acquisition remain prerequisites to the scored replay.


### 26 November 2026 — M3.6 detect-v2 review and D-058 correction

- The first detect-v2 tuning run revealed that `change.detect()` excluded `OTHER` from informative observations, making the configured `other>bare: levelling` transition unreachable. Corrected the temporal stack so only `MASKED` looks are uninformative; added a synthetic levelling regression test and per-transition raw/kept pixel counters.
- Corrected five-lake run5 (detect-v2, as-of 2026-11-20, rules SHA-256 `7e3ae2398bab87c1133a7a6ecefafe5b4407c8a7a428fdc0b7999cb998fa2a36`) emitted 3 clearing candidates totalling 5.78 acres. It observed 2,068 raw levelling pixels and 72 pixels after temporal controls, but no final levelling candidate.
- This differs materially from detect-v1 run4 (14 clearing candidates / 20.19 acres). The 11 candidate footprints that no longer appear need before/after review; no accuracy or improvement claim is made.
- Workflow artifact: https://github.com/aitech2025/lake-protect/actions/runs/45780430533 (artifact ID `15098336015`). The artifact contains the three candidate chips, per-lake weekly imagery, GeoJSON and summary.
- M3.6 remains in progress; M3.7 remains blocked. Next implementation: diagnostic geometry/chips for levelling components that survive controls but fail final candidate extraction, then compare run4/run5 footprints. Do not freeze or score yet.


## 8. Fan-out execution checkpoint — 26 November 2026

The following implementation increments were delivered in parallel on short-lived branches and merged into `feature/consolidated`:

| PR | Workstream | Result | CI |
|---|---|---|---|
| #23 | M2 detect-v2 tuning and workflow correction | Merged | Passed |
| #25 | M2 sub-threshold levelling diagnostics and before/after review chips | Merged | Passed |
| #26 | M3 scorer guardrails: replay-time `detected_at`, unique IDs and geometry validation | Merged | Passed |
| #27 | P2 statewide registry district/mandal drill-down and boundary-source label | Merged | Passed |
| #28 | P3 citizen operations queue, retry visibility and provider-readiness dashboard | Merged | Passed |

### Current implementation facts

- M2 diagnostic components are now kept separately from alert candidates. Sub-threshold levelling patches can be inspected through `diagnostics.geojson` and `chips/diagnostics/*`; they do not lower the candidate area threshold or enter alert workflows.
- M3 scoring no longer accepts retrospective `first_changed_at` as the detection timestamp. A scored detection must have a valid replay `detected_at`, a unique stable ID and valid EPSG:4326 geometry.
- P2 registry filters operate on the existing authoritative `/assets` response, keeping map and list in sync. The selected district constrains mandal options.
- P3 operations visibility is implemented in PR #28. It excludes demo messages and exposes no reporter phone numbers, names, message bodies, exact coordinates or photos.
- PR #24 was closed because its documentation branch conflicted with merged tuning changes. This checkpoint supersedes that stale documentation branch.

### Remaining critical gates

1. Review the 12 unmatched run4 footprints, the 1 unmatched run5 footprint and the 2 partial-overlap matches; review all diagnostic chips.
2. Independently verify exact event dates, public-action dates, event polygons and affected areas for the scoring case manifest.
3. Freeze detect-v2 only after human review; then run the scored replay once and publish full metrics and limitations.
4. Finish PR #28 CI and merge; then validate the end-to-end citizen operations page against a real (non-demo) queued review and retry scenario.
5. Complete the remaining P2 source hierarchy/coverage acceptance suite and the P5 security/production gates.

No scored detection accuracy claim is authorized by these implementation increments.


## 9. Next fan-out execution checkpoint — 26 November 2026

| PR | Workstream | Result | CI |
|---|---|---|---|
| #31 | M2 run4/run5 spatial candidate comparison CLI and tests | Merged | Passed |
| #32 | M3 scorer CRS contract, metric IoU and scoring breakdowns; replay CRS stamping | Merged | Passed |
| #33 | P2 Asset 360 boundary provenance API/UI and tests | Merged | Passed |
| #34 | P5 admin-only readiness diagnostics and tests | Merged | Passed |
| #35 | P2 OSM provenance class correction | Merged | Passed |

### What is now implemented

- `lp-geo compare-tuning` compares two non-scored candidate exports by asset, change type and projected polygon IoU, producing matched/disappeared/added review leads. It does not determine truth or enforcement status.
- Historical replay output now stamps `geometry_crs=EPSG:4326`; the scorer rejects missing or projected detection coordinates and computes spatial IoU in EPSG:32644.
- Backtest output now includes median lead time and matched/unmatched breakdowns by sensor, season and event type. Precision remains unavailable while any unmatched candidate lacks complete human review.
- Asset 360 now displays conservative boundary provenance, including source class, source date/reference, agency, provenance completeness and whether the specific HMDA LPC notification-reference criteria were met.
- `GET /readiness` is an admin-only configuration diagnostic. It does not certify production readiness and intentionally reports all security/authorization/HA-DR sign-offs as unverified.

### Immediate next actions

1. PR #35 is merged; verify the updated source classes in the Asset 360 demo journey.
2. Download the existing run5 tuning artifact and run `lp-geo compare-tuning` against the committed run4 candidates; inspect every disappeared/added footprint and diagnostic chip.
3. Record human review dispositions with reviewer, date and evidence; only then decide whether detect-v2 can be frozen.
4. Continue the government evidence request for independently verified M3 cases. No scored replay until the manifest and frozen rules are approved.
5. Complete P2 coverage/freshness and official hierarchy; complete P3 non-demo queue validation.
6. Treat the readiness endpoint as an operator checklist only; complete actual P5 controls before any production deployment.

No detection accuracy or production-readiness claim is authorized by this fan-out.


### 26 November 2026 — Run4/run5 spatial comparison executed

- Executed the merged `lp-geo compare-tuning` command against committed run4 candidates and the archived run5 tuning artifact.
- Workflow: [45819230496](https://github.com/aitech2025/lake-protect/actions/runs/45819230496); output artifact: [m2-run4-run5-spatial-diff](https://github.com/aitech2025/lake-protect/actions/runs/45819230496/artifacts/15117485673).
- Results: run4 had 14 clearing features; run5 had 3. The spatial comparison found 2 one-to-one partial matches (IoU 0.348 and 0.319), 12 unmatched run4 features and 1 unmatched run5 feature.
- The 12 unmatched run4 features are split across `osm-way-158331211` (4) and `osm-way-265159686` (8). The unmatched run5 feature is on `osm-way-158331211`, dated 2026-11-08, 0.5931 acres.
- The two matched pairs changed materially in area: 12.0340→4.6209 acres and 1.7792→0.5683 acres. These are partial spatial correspondences, not stable/equivalent footprints.
- Added `reports/m2-tuning/run4-run5-spatial-review.md` with results, identifiers, caveats and the human-review checklist.
- No unmatched footprint is classified as a false positive or true positive. Human inspection of all 15 review leads plus PR #25 levelling diagnostics remains a prerequisite to rule freeze.


## UI redesign checkpoint — 26 November 2026

A new owner-requested Civic Slate & Water-Ledger refresh is in progress on `feat/geoguard-civic-ui-refresh`. See [UI redesign specification](UI_REDESIGN.md).

- [x] Shared civic theme tokens, semantic status palette and shadcn-inspired controls.
- [x] Responsive workspace shell with grouped navigation and account/language controls.
- [x] Shared styling refresh for page surfaces, panels, forms, tables, maps, badges and evidence.
- [x] Mandatory evidentiary disclaimer surfaced on Alert Detail and Evidence Pack preview.
- [ ] Validate the full route set, existing E2E selectors and English/Telugu responsive layouts.
- [ ] Refine page-specific overview, queue, Asset 360, records, inbox and admin interactions based on QA.

**Governance:** this is a frontend-only redesign. It preserves the current `admin` / `viewer` roles, server-authorized actions and D-057 incident lifecycle. It does not restore retired field-officer workflows, dual sign-off, officer routing or SLA timers. ACTION / VERIFY / WATCH will not be inferred from boundary data until the backend exposes an authoritative operating-mode contract. No API, ML, data, database, PWA or government-integration contract has been changed.
