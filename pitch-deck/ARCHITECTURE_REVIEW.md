# Architecture review: the Telangana GeoGuard drafts

Reviewed on 24 November 2026. The two pages in this folder were checked against four things:

- the TISC 2026 problem statement;
- the shortlisted proposal (Lake Protect, November 2026);
- `CONTEXT.md`, the solution design;
- the code at commit `898166d`.

The drafts as received are in commit `b364074`, so `git diff b364074 -- pitch-deck` shows every change.

## Verdict

The layering is sound. Two guardrails in the drafts are right and were kept:

- use the latest valid look, never just the latest scene;
- the system makes no legal conclusions.

As drafted, though, the pages had four problems:

1. They described a heavier product than the one the jury shortlisted and the one that runs.
2. They left out the parts that make cases hold up: the boundary-status gate, the legal check, the field app and the sealed evidence pack.
3. They included a data source the State cannot get.
4. They gave no sign of what already exists.

All of this is fixed in place. Every component now carries a **Built**, **Pilot** or **Later** tag, and each page opens with a "running today" line of real figures.

## Findings and changes

| # | Severity | Finding | Change made |
|---|---|---|---|
| 1 | Critical | **Boundary status was missing.** The drafts assume an "approved FTL" everywhere. About 23% of HMDA lakes (765 of 3,342) have a final FTL notice, and all 99 real lakes in the prototype have derived outlines. Rule 2 of the proposal says only confirmed boundaries lead to action. | Added a note that boundary status decides what an alert may do (cohorts A to D), and boundary status in the registry. R05 is now split by cohort E and F. |
| 2 | Critical | **No legal check and no baseline date.** The drafts had an overlay but not the checks: out of scope, before the 19 Jul 2024 baseline, authorised work or permit, live court matter, boundary not notified. These are what turn a detection into a case that holds up. | Added an "Automatic legal check" card in layer 04 and a highlighted step in the data flow. |
| 3 | Critical | **Social-media listening is not available or defensible.**<br>- Meta's Content Library is limited to academic and non-profit researchers; CrowdTangle closed in August 2024.<br>- The X API is paid.<br>- A government watching citizens' posts conflicts with owner-blind detection (rule 4) and invites a privacy challenge.<br>- It is not in the proposal. | Replaced with ground signals the State already has: HYDRAA's 900 CCTV cameras on 264 lakes, lake guards, Praja Vani and 1070. News reports are used only to build the backtest case list. |
| 4 | Critical | **The stack contradicted the proposal and the drafts' own principle.**<br>- The drafts listed Kong, RabbitMQ, Temporal, Redis, Kubernetes and a GPU node.<br>- The proposal says: modular monolith with an outbox, and Kafka, Kubernetes or microservices only on measured need.<br>- The drafts' own principle was "modular backend before microservices sprawl". | Outbox plus one worker for the pilot. Broker, workflow engine and Kubernetes are marked Later. FastAPI sits behind the State's gateway. |
| 5 | Critical | **Nothing said what exists.** The jury will ask, and the proposal's rule 6 forbids implying results that do not exist. | Added Built, Pilot and Later tags, plus a "running today" line: 99 lakes, 7,652 clear looks, 58 candidate changes on the watch list, no accuracy claimed before the backtest. |
| 6 | High | **The imagery tiers were inverted.**<br>- Construction used sub-metre imagery as the primary sensor ("1 m screening"). That is unaffordable weekly at 900+ lakes and contradicts the proposal's screen, confirm, verify tiers.<br>- R01 (water spread) was an alert rule, but water loss alone never alerts, because of season and drought. | Three tiers stated on both pages. Built-up screening is at 10 m, 1,000 sq m or more, confirmed by radar. Sheds under 10 m are never claimed from Sentinel. R01 is context only. The false-alarm controls are listed. |
| 7 | High | **The field app and the evidence pack were missing.** These are the two built pieces the proposal sells hardest: the offline field app in Telugu, and the sealed pack with the Section 63(4) BSA certificate and `lp verify-pack`. | Added to layer 05 and to lane 4 of the data flow. |
| 8 | High | **The Copilot was shown as a core layer.** It risks hallucinated legal statements. If it reads the database directly, it also bypasses owner-blind and area rules. It is not in the proposal. | Marked Later, after the pilot gates. Its rules:<br>- it retrieves only through the officer's own permission-checked API;<br>- it never says whether a change is legal and never suggests an action;<br>- it runs on a model hosted in India;<br>- it never cites unverified OCR text. |
| 9 | High | **Deep learning was presented as current** (SegFormer, YOLO, ChangeFormer). No labelled Hyderabad training data exists. The prototype uses explainable index rules, and the proposal says "heuristic score into tested models". | Deep learning is marked Later, trained on officer-verified outcomes. Governance names the rules hash, the frozen rules and the blind backtest gate. MLflow and CVAT are Later. |
| 10 | High | **"Pilot sized for 10–15 lakes"** contradicted the proposal's phases. | The principles now give the proposal's phases: about 20 recovered assets, then 100 lakes and 10 parcels, then 900+ lakes. |
| 11 | Medium | **Notifications skipped two operational requirements.**<br>- SMS needs DLT-registered templates.<br>- WhatsApp messages sent by the business need approved templates.<br>- Acknowledgement and repeat after 24 hours were missing. | Added. |
| 12 | Medium | **DPDP timing.** The Rules were notified in November 2025. Notice, consent and security duties apply from about 13–14 May 2027, which falls during the paid pilot. | Added to cross-cutting governance. |
| 13 | Medium | **Drones need airspace permission.** The Drone Rules 2021 airspace map needs air traffic control permission in yellow zones near operational airports. Hyderabad has several airfields, so check each site on Digital Sky. | Added to governance. |
| 14 | Medium | **GeoServer was named as the overlay engine.** The overlay is PostGIS SQL; GeoServer only publishes layers. | Removed. Publishing to department GIS is OGC API Features (Pilot). |
| 15 | Medium | **A citizen mobile app adds install friction.** The proposal says web portal plus WhatsApp. | Web portal and WhatsApp, in English, Telugu and Urdu. One-time password only if the citizen wants updates. |
| 16 | Medium | **A GPU node is not needed for the pilot.** The first real screen of 99 lakes took 28 minutes on a laptop CPU. | Compute card corrected. GPU only for later deep learning on sub-metre images. |
| 17 | Low | **Evidence provenance cited MLflow.** The provenance that matters is the scene IDs, rules hash, boundary version and photo hashes. | Fixed. |
| 18 | Low | **Vocabulary.** The drafts said "incident"; the app and proposal say "alert" and "case". | Aligned. |

## Left for you to decide

- **Name.** These pages say "Telangana GeoGuard"; the shortlisted proposal and the app say "Lake Protect". Pick one before the jury. Two names will read as two products. The pages were not renamed.
- **Proposal slide 26 claims more than the code has.** Its "Built and tested" box lists these four items; the code has less:

  | Claimed | What the code has |
  |---|---|
  | Statewide registry | One key per asset; no statewide registry |
  | Department security | Role checks only; no department or area scope and no row-level security |
  | S3 storage | An S3-style interface over local disk |
  | Durable outbox | No outbox |

  Move these four to "Next" or call them "designed".
- **Slide 26 is also out of date.** It still lists "Detection on Sentinel-2" as next. That is now done, and the real-data screen above could replace it.

## How the pages were checked

Both pages were opened in headless Chromium, with no network, at 1440 px and 390 px wide. There was no horizontal overflow and no script errors at either width.

## Sources for the outside facts

- DPDP Rules 2025, phased commencement: [YourStory](https://yourstory.com/2025/11/digital-personal-data-protection-dpdp-rules-2025-rollout-over-18-months), [Taxmann](https://www.taxmann.com/post/blog/analysis-indias-dpdp-act-and-rules/), [PIB](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf)
- Meta Content Library eligibility and the CrowdTangle shutdown: [TechCrunch](https://techcrunch.com/2024/08/15/meta-shut-down-crowdtangle-a-tool-for-tracking-disinformation-heres-how-its-replacement-compares), [Columbia Journalism Review](https://cjr.org/tow_center/meta-is-getting-rid-of-crowdtangle.php)
- Drone airspace zones: [PIB, Ministry of Civil Aviation](https://pib.gov.in/PressReleasePage.aspx?PRID=1757850), [Telangana Today](https://telanganatoday.com/airspace-map-to-boost-drone-industry-in-india)
- Everything else (HYDRAA, LPC, BuildNow, CCMS, MeeSeva on WhatsApp, Section 63(4)) is from `CONTEXT.md` section 17 and the proposal, with their sources.
