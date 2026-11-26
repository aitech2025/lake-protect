# GeoGuard R0 — Source-of-truth and demo-readiness audit

**Assessment date:** 26 November 2026  
**Repository:** aitech2025/lake-protect  
**Audited ref:** feature/latest (6012af309f41efcbe99c4190b6ebd41d6fdfcc86)

## 1. Executive outcome

The most advanced inspected product branch is feature/latest, not the repository default branch and not the merged geospatial feature branch. It contains the public citizen portal and later M10–M19 product increments. PRs #12–#14 were merged into feat/p0-p1-p5-geospatial-integrations; that branch is not the same source tree as feature/latest.

GitHub comparison between the geospatial feature branch head (5e77af275a5ab377304d9ab33d19a4ee34d7b2e7) and feature/latest (6012af309f41efcbe99c4190b6ebd41d6fdfcc86) reports diverged: 20 commits ahead and 115 behind, with 253 changed files. Do not merge, rebase or build production work on either branch by assumption. A deliberate reconciliation decision is required.

R0 is a source audit, not production certification. Repository files and tests were inspected through GitHub; API, pipeline, web-build and browser tests were not executed in a local runtime during this audit.

## 2. Source-of-truth and branch findings

| Ref | Observed state | Audit conclusion |
|---|---|---|
| feature/initial | Repository default branch | Older prototype baseline; not suitable as current feature baseline without review |
| feat/p0-p1-p5-geospatial-integrations | PRs #9–#14 merged into this branch | Contains statewide platform foundations and geospatial work, but not later citizen portal found on latest |
| feature/latest | Contains M10–M19 work, citizen portal, source engine, notification workflows and satellite-source administration | Most advanced inspected application baseline; divergent from merged geospatial branch |
| main | Older tree | Not the current application baseline |

PR #12 (command-centre UI), #13 (BRD/PRD and government onboarding specification) and #14 (RTM) are merged into feat/p0-p1-p5-geospatial-integrations. This does not automatically mean those changes are present in feature/latest.

**R0 decision required:** nominate one canonical integration branch and reconcile the two lines before further feature PRs. Do not silently treat feature/latest as a descendant of the geospatial branch.

## 3. Verified application capabilities on feature/latest

### 3.1 Citizen portal and incident lifecycle — implemented in code

Evidence: web/src/App.tsx exposes public /report and /report/track routes outside authentication; web/src/portal/Portal.tsx implements the public portal; api/app/routers/citizen.py provides public configuration, report intake, reference-based status, OTP and WhatsApp webhook routes; api/app/routers/reports.py provides staff intake/list/detail/photo/placement; api/app/citizen contains service, incident, location and action workflows. Tests exist in api/tests/test_citizen.py, api/tests/test_incident_actions.py and e2e/tests/m15-citizen.spec.ts.

Verified flow: unauthenticated report in English/Telugu; map pin/location, category, description and photos; report reference; place resolution or staff placement; duplicate/nearby incident linking; satellite review queued; area officials notified; acknowledgement, notes, imagery comparison, legal records and recorded decision; citizen tracking by reference.

**Classification:** Implemented code path. Production acceptance still requires a clean environment run and end-to-end test execution. The citizen portal must not be classified as missing.

### 3.2 Government data onboarding — demo placeholder foundation

Evidence: api/app/sources/base.py defines connector/data contracts; connectors.py contains HMDA Lake Protection Committee, Irrigation, Bhu Bharati and HYDRAA templates; transports.py provides file-drop, sample and official API transports; sources.yaml deliberately leaves API endpoints and agreement references unconfigured; samples/ contains fictional CSV/GeoJSON packages; routers/sources.py exposes connector status, dry-run/apply and run history; api/tests/test_sources.py covers validation and sample paths.

The connector code explicitly states it does not call government systems. Official API transport requires an agreement reference, endpoint and credential. This is an appropriate pre-agreement demo pattern.

**Classification:** Demo-ready adapter architecture / future production integration placeholder. Not a live government integration.

### 3.3 Satellite imagery — partially operational, provider-dependent

Evidence: api/app/routers/pipeline.py provides watchlist, screening runs and citizen incident review; routers/satellites.py and services/satellites.py maintain the source catalogue and history; web/src/desk/Satellites.tsx provides administration; pipeline and API tests exist.

The source catalogue is configuration, not proof that every provider is connected or that a resolution/revisit is guaranteed. Sentinel screening depends on the reviewer/screening service and internet access. Commercial tasking depends on provider, licence, order and credentials.

**Classification:** Existing screening workflow plus provider catalogue. Commercial tasking and guaranteed weekly high-resolution coverage remain external dependencies. Show acquisition status and imagery gaps honestly.

### 3.4 WhatsApp and citizen notifications — adapter exists; live delivery gated

Evidence: api/app/citizen/whatsapp.py handles WhatsApp conversations and signed webhook validation; routers/citizen.py exposes webhook routes; citizen/sender.py and notify/channels.py handle SMS/WhatsApp/email delivery; citizen tests cover workflow behaviour.

Real WhatsApp requires the State's Business agreement/channel and app-secret configuration. SMS requires a gateway and approved DLT template. Unconfigured notification channels can be held. The latest branch documentation says the demo WhatsApp simulator was removed with the demo world.

**Classification:** Webhook and delivery adapter foundations implemented; live WhatsApp/SMS not activated. For the government demo, use a clearly labelled simulated event console or sample messages, never claim messages were sent.

### 3.5 Social intelligence — not evidenced on feature/latest

The inspected feature/latest tree does not expose the social-ingestion module found in the older merged geospatial branch. No approved social-listening provider connector, collection configuration, triage UI or social-to-incident workflow was evidenced on this branch.

**Classification:** Planned / not implemented on the audited branch. Reconcile the other branch's social ingestion deliberately before counting it.

### 3.6 Legal documents, dashboards and notifications

Evidence includes routers/documents.py for asset-linked legal document upload/reference and audited download; routers/dashboard.py and services/dashboard.py for roll-up endpoints; routers/notifications.py and app/notify for inbox, acknowledgements, delivery attempts, retries and weekly digest; web desk pages for reports, inbox, officials, dashboard and records.

The audited branch README describes an officials' inbox, email outbox and SMS/WhatsApp channels held until gateways are configured. It does not contain the same standalone field PWA visible in the older branch; reconcile field operations against current scope rather than assuming it is present.

## 4. Demo-vs-production integration matrix

| Integration | Demo now | Production later | Current classification |
|---|---|---|---|
| HMDA/LPC | Sample connector, file-drop package, dry-run/apply | Approved data exchange/API or agreed SFTP/drop | Placeholder foundation |
| Irrigation | Sample connector and file-drop package | Approved API/SFTP and schema mapping | Placeholder foundation |
| Bhu Bharati | Sample parcel/ROR extracts with privacy sanitisation | Approved, purpose-limited data-sharing channel | Placeholder foundation |
| HYDRAA | Sample FTL/recovered-parcel data | Approved data exchange and provenance | Placeholder foundation |
| Government SSO | Demo roles/accounts | OIDC/SAML federation, MFA and provisioning | Not evidenced |
| Sentinel imagery | Existing screening pipeline and screening outputs | Operational scheduled acquisition and processing | Partial |
| Commercial imagery | Source catalogue and cost metadata | Provider account, tasking/order API, licence and delivery | Placeholder/configuration only |
| Citizen web | Application workflow against configured database | Production hosting, security, support and privacy controls | Implemented code path |
| WhatsApp | Simulated event evidence needed for demo | Official business number, provider setup and templates | Adapter exists; activation gated |
| SMS | Held/unavailable state can be demonstrated | Gateway, DLT registration and templates | Activation gated |
| Email | Local file outbox; SMTP configurable | Government-approved SMTP relay | Adapter exists |
| Social monitoring | Curated sample feed can be added as demo capability | Approved provider/API and legal approval | Not evidenced on this branch |
| Legal records | Sample/uploaded asset-linked documents | Authoritative records and verified legal metadata | Partial; no government source link |
| Copilot / legal RAG | Not evidenced | Permission-aware, cited, read-only assistant | Not evidenced |

## 5. Important demo integrity and product risks

1. Branch divergence is the highest engineering risk. Latest product work and merged statewide platform work are on divergent lines.
2. Demo data semantics need a clear policy. Latest README says the demo world was removed and real locations/data are used, while government source connectors ship fictional sample packages. Keep sample submissions isolated and visibly labelled; never mix them with operational records or present them as government-supplied.
3. A connector contract, configured catalogue or webhook endpoint is not a live external connection. UI labels should distinguish Demo/Sample, Configured, Connected, Last successful sync, Awaiting approval and Unavailable.
4. Satellite coverage is not a weekly high-resolution guarantee. Scheduled attempt, usable observation, cloud gap, processing failure and no-change result must remain distinct.
5. Citizen report is not an enforcement finding. Keep human review, evidence provenance and legal authority visible.
6. Social listening must not be simulated as live collection. Use a curated sample feed labelled as sample data.
7. No production-readiness claim yet. Security, privacy/legal, government SSO, HA/DR, backup/restore, monitoring, load, penetration and operational-runbook gates remain.

## 6. R0 acceptance checklist

- [x] Identify repository default branch.
- [x] Identify merged PRs #12–#14 and target branch.
- [x] Locate citizen portal implementation on feature/latest.
- [x] Inspect citizen routes, portal UI, incident workflow and related tests.
- [x] Inspect government connector contracts, transports, samples and API gating.
- [x] Inspect satellite source administration and screening endpoints.
- [x] Inspect WhatsApp/SMS/email activation gates.
- [x] Check whether social ingestion is present on audited branch.
- [ ] Run API, pipeline, web-build and browser E2E suites against a clean checkout of selected canonical branch.
- [ ] Reconcile and nominate canonical branch with product owner.
- [ ] Produce one consolidated RTM for that canonical branch.

Unchecked items require an executable checkout/CI run or explicit branch decision; they are not claimed complete by source inspection.

## 7. Recommended next increments

**R0.1 — Branch reconciliation (P0):** select canonical branch; compare unique commits and migrations; integrate in a controlled branch; run clean database migration and full test suites. Do not cherry-pick blindly.

**R0.2 — Demo integration control plane (P0):** one integration registry showing connector mode, sample/live status, approval dependency, configuration completeness, last attempt and last success. Demo mode must prevent accidental outbound calls.

**R0.3 — Government demo data room (P0):** curated, visibly fictional submission packages for HMDA/LPC, Irrigation, Bhu Bharati and HYDRAA; demonstrate upload, validation, conflict report, dry run, approval simulation and asset registration. Preserve provenance and separate sample tenant/data.

**R0.4 — Citizen portal acceptance (P0):** clean-environment E2E for report, OTP-unavailable path, photo sanitisation, tracking, duplicate linking, official review and notifications.

**R0.5 — Integration demo simulators (P1):** WhatsApp inbound simulator, SMS delivery preview, social sample feed and commercial imagery request lifecycle. Each must display SIMULATED — NOT SENT / NOT CONNECTED.

**R0.6 — Consolidated RTM (P1):** reconcile existing RTM and BRD/PRD with feature/latest code and test evidence; avoid two conflicting product baselines.

## 8. Source files inspected

README.md, PROGRESS.md, CONTEXT.md; web/src/App.tsx and portal/Portal.tsx; desk Reports, Inbox, Officials, Sources and Satellites; api/app/main.py; routers citizen, reports, sources, satellites, pipeline and documents; citizen service, incident, locate, actions, WhatsApp, sender and OTP; sources base, connectors, transports and sources.yaml; notify/channels.py; API source/citizen/incident tests; E2E M15 citizen and M19 satellite tests.