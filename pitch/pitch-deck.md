---
marp: true
theme: pitch-deck
paginate: true
header: "Lake Protect"
footer: "TISC 2026 · Confidential"
---

<style>
section { font-size: 26px; padding: 64px 72px; display: flex; flex-direction: column; justify-content: flex-start; }
section.lead, section.big-number, section.invert { justify-content: center; }
section h2 { font-size: 1.45em; margin-bottom: 0.45em; }
section h3 { font-size: 15px; margin-bottom: 0.4em; color: var(--color-accent); }
table { display: table; width: 100%; font-size: 19px; margin: 0.4em 0; }
th { font-size: 14px; padding: 8px 14px; }
td { padding: 8px 14px; color: var(--color-text); }
td:first-child { font-weight: 600; }
.note { font-size: 16px; color: var(--color-text-tertiary); margin-top: 14px; line-height: 1.35; }
.note b { color: var(--color-text-secondary); }
section .steps > div { padding: 22px 24px; font-size: 21px; line-height: 1.35; }
section .steps > div strong { display: block; font-size: 24px; margin-bottom: 6px; }
section .steps > div small { display: block; color: var(--color-text-secondary); font-size: 17px; margin-top: 10px; }
section .metric { padding: 8px; }
section .metric span:first-child { font-size: 2.2em; }
section .metric span:last-child { font-size: 15px; }
.tag { display: inline-block; font-size: 12px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; border-radius: 5px; padding: 2px 7px; vertical-align: middle; }
.tag.built { background: #e3f4e8; color: #1b6b35; }
.tag.pilot { background: #fff1d6; color: #8a5a00; }
.tag.later { background: #ececef; color: #55555a; }
</style>

<!-- _class: lead -->

# Lake Protect

## A weekly satellite watch that reaches the field, and cases that hold up

TISC 2026 · Protecting Lakes and Government Land · Aanvi Infotech

<!--
Open with the promise, not the technology. We are not selling more alerts; we are selling cases that hold up.
Fifteen seconds. Move on.
-->

---

<!-- _class: big-number -->

# 61%

## of Hyderabad's lake area lost between 1979 and 2024 (NRSC)

<div class="note">HYDRAA warns the remaining lakes could vanish within 15 years</div>

<!--
Source: NRSC figures as reported by Deccan Chronicle and NewsMeter (CONTEXT.md section 16).
Then the problem in one line: Telangana can already see its lakes. What it lacks is a recurring loop
that turns each new change into a dated, court-ready case, owned by a named officer with a deadline.
The High Court has stayed actions where boundaries "were not clear" (Khajaguda) and where notice was
missing (Kokapet, May 2026). Weak evidence, not weak detection, is what loses land back.
-->

---

### 1 · Encroachment and how we detect it

## Encroachment takes six forms, and each leaves a different trace

| Form | What changes | How we catch it |
|---|---|---|
| Soil or debris dumped | Water turns to bare soil at the edge | Weekly optical screen |
| Land cleared and levelled | Vegetation turns to bare soil | Optical screen; sub-metre for plot lines |
| Sheds, fences, walls | Smaller than one 10 m pixel | Sub-metre images or a field visit |
| Buildings in FTL or buffer | Built-up index and radar return rise | Optical plus radar; sub-metre footprint |
| Nalas and feeders blocked | Channel narrows or disappears | Sub-metre images |
| Government land occupied | New structures or fencing on a parcel | Same signals, once the parcel boundary is official |

<!--
Walk the stages in order: soil dumped, land levelled, sheds and fences, building rises, family moves in.
We alert at the first three, while the change is still reversible. HYDRAA has said occupied homes will
not be demolished, so time matters. Proposed target: 60% of confirmed cases caught before a permanent
structure (a target, not a result).
Be candid: sheds and walls under 10 m are never claimed from Sentinel. Water loss alone never alerts,
because season and drought shrink lakes too.
Nala blocking and parcel occupation are on the roadmap: they need sub-metre images and official parcel
boundaries respectively.
-->

---

### 1 · Encroachment and how we detect it

## Screen every lake weekly, sharpen only where it matters

<div class="steps">
<div><strong>1 · Screen</strong>Every lake, at least weekly<small>Sentinel-2 optical at 10 m, every 5 days; Sentinel-1 radar sees through monsoon cloud</small></div>
<div><strong>2 · Confirm</strong>Priority cases only<small>Sub-metre images: Cartosat-3 through NRSC, or commercial at 0.3 to 0.5 m</small></div>
<div><strong>3 · Verify</strong>On the ground<small>A field officer with geotagged, hashed photos; CCTV and drones where they exist</small></div>
</div>

<div class="note">Indices: water (MNDWI), vegetation (NDVI), bare soil (BSI), built-up (NDBI), radar return (VV/VH) · each tier may use free, ISRO or commercial imagery, chosen per phase</div>

<!--
This is the cost logic. Sub-metre imagery for 900 lakes every week is unaffordable and unnecessary.
Medium-resolution optical and radar screen everything; sharp images are bought only for the few cases
that reach priority; a person confirms on the ground.
Radar matters most from June to September, when cloud cover over Hyderabad averages 79 to 89%.
Radar-only alerts are marked "optical confirmation pending".
-->

---

### 1 · Encroachment and how we detect it

## Every alert dates the change: last clear image, first changed image

<div class="columns" style="gap:28px">
<div><img src="img/candidate-before.png" style="width:100%;max-height:420px;object-fit:contain"></div>
<div><img src="img/candidate-after.png" style="width:100%;max-height:420px;object-fit:contain"></div>
</div>

<div class="note"><b>Real Sentinel-2 pair, Hyderabad, 1 Jun → 10 Aug 2026:</b> water to bare soil inside the lake outline, 2,700 sq m. A candidate change; its cause is not verified.</div>

<!--
Real images from the prototype's own screen, not a mock-up. Blue is the lake outline, red the buffer,
yellow the changed pixels.
This is Kapra lake, one of our five tuning lakes, where HYDRAA reported restoration works in 2026.
That is the point: restoration looks like encroachment from space. The automatic legal check looks for
authorised works before anyone is sent out.
The dated bracket (last clear look, first changed look) is the most useful single field in a case file:
it answers "when did this start?" before anyone asks.
-->

---

### 2 · Solution architecture

## One core decides what deserves an officer's time

<style scoped>
.arch { display: grid; grid-template-columns: 1fr 26px 1.45fr 26px 1fr; gap: 0; align-items: stretch; margin-top: 4px; }
.arch h4 { font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: var(--color-text-tertiary); margin: 0 0 6px; }
.arch .b { background: var(--color-bg-alt); border-radius: 9px; padding: 6px 11px; margin-bottom: 6px; line-height: 1.2; }
.arch .b b { display: block; font-size: 16px; color: var(--color-text); }
.arch .b span { display: block; font-size: 12.5px; line-height: 1.3; color: var(--color-text-secondary); margin-top: 2px; }
.arch .arrow { display: flex; align-items: center; justify-content: center; color: var(--color-accent); font-size: 28px; font-weight: 700; }
.core { border: 2px solid var(--color-accent); background: var(--color-accent-light); border-radius: 14px; padding: 12px 14px; display: flex; flex-direction: column; justify-content: space-between; }
.core .row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 6px; }
.core .row.three { grid-template-columns: repeat(3, 1fr); }
.core .s { background: #fff; border-radius: 8px; padding: 9px 7px; font-size: 14px; line-height: 1.2; color: var(--color-text); text-align: center; }
.core .s { display: flex; align-items: center; justify-content: center; }
.core .s.key { background: var(--color-accent); color: #fff; font-weight: 600; }
.core .lbl { font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--color-accent); margin: 2px 0 4px; }
.core .found { background: #fff; border-radius: 8px; padding: 6px 8px; font-size: 12.5px; color: var(--color-text-secondary); margin-top: 6px; line-height: 1.3; }
.core .found b { color: var(--color-text); }
.core .loop { font-size: 12px; color: var(--color-accent); text-align: center; margin-top: 6px; font-weight: 600; }
</style>

<div class="arch">
<div>
<h4>Channels in</h4>
<div class="b"><b>Satellite images</b><span>Optical and radar weekly; sub-metre on cue</span></div>
<div class="b"><b>Mobile field app</b><span>Officers: offline, Telugu, geotagged photos</span></div>
<div class="b"><b>WhatsApp</b><span>Citizen reports: photo, pin, note</span></div>
<div class="b"><b>Web app</b><span>Citizen reports; 1070 and Praja Vani entered here</span></div>
<div class="b"><b>Government records</b><span>FTL notices, permits, works, court cases, survey nos.</span></div>
<div class="b"><b>Ground signals</b><span>900 CCTV cameras, lake guards</span></div>
</div>
<div class="arrow">→</div>
<div class="core">
<h4 style="color:var(--color-accent)">Lake Protect core</h4>
<div class="lbl">Process imagery</div>
<div class="row three"><div class="s">Catalogue each scene</div><div class="s">Process it once</div><div class="s">Match every asset</div></div>
<div class="lbl">Analyse</div>
<div class="row"><div class="s">Detect change</div><div class="s key">Legal check</div><div class="s">Set priority</div><div class="s">Analyst review</div></div>
<div class="lbl">Act</div>
<div class="row three"><div class="s">Route, with a deadline</div><div class="s">Field check</div><div class="s key">Seal evidence</div></div>
<div class="found"><b>Asset registry</b> with versioned boundaries and their status · imagery record · case history</div>
<div class="found"><b>Every layer:</b> access by role and area · every action logged in a hash chain · missed deadlines escalate</div>
<div class="loop">↺ Field outcomes feed back to tune detection</div>
</div>
<div class="arrow">→</div>
<div>
<h4>Portals out</h4>
<div class="b"><b>Citizen portal</b><span>Track a report by reference number: received, checked, closed with a reason</span></div>
<div class="b"><b>Officer portal</b><span>Analyst desk, field tasks, case file, deadlines</span></div>
<div class="b"><b>Evidence pack</b><span>Sealed by SHA-256, with a Section 63(4) certificate</span></div>
<div class="b"><b>Leadership page</b><span>Monthly view, State to survey number</span></div>
<div class="b"><b>Notifications</b><span>Inbox, SMS, WhatsApp, daily email</span></div>
</div>
</div>

<!--
Left to right: anything that can signal a change comes in on the left; one core decides what deserves
an officer's time; two portals and three outputs carry the result.
Four things the core guarantees:
1. The legal check runs before routing: out-of-scope, legacy, authorised and court-held changes never
   reach a field team.
2. Boundary status gates action: only final or physically marked boundaries get the full officer path.
3. The citizen portal shows status only: never the accused, never owner names.
4. The field app is both a channel (photos in) and a portal (tasks out).
The heavy pieces (message brokers, Kubernetes, deep learning) are added only when measured load needs
them. Cases and alerts keep working when satellite processing is down.
-->

---

### 3 · Rules enforced

## A legal check runs before anyone moves

| Check, in order | Result |
|---|---|
| Outside the FTL, buffer and watch ring? | Closed: out of scope |
| First changed before the baseline date? | Closed: legacy, logged |
| Matches an authorised work or a valid permit? | Closed: authorised (inside the FTL: flagged) |
| Live court matter? | Hold for the legal officer |
| Lake not yet notified? | Watch list |
| Otherwise | Triage for analyst review |

<div class="note">Each result stores the rule version, the boundary version and the records it matched · only confirmed boundaries (final notice or physically marked) lead to action</div>

<!--
This is what turns a detection into a case that survives the High Court.
Boundary status by cohort: recovered land and lakes with a final notice get the full action path;
preliminary notice is action too; derived outlines go to field verification without an officer path;
survey-number-only land stays watch-only until a parcel boundary exists. Only 765 of 3,342 HMDA lakes
(23%) have a final FTL notice, so starting where boundaries are certain is a choice, not a limitation.
A live court matter moves any alert to a legal hold, whatever the cohort.
-->

---

### 3 · Rules enforced

## Six rules no one can switch off

<style scoped>
.rules { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 6px; }
.rules div { background: var(--color-bg-alt); border-radius: 12px; padding: 14px 16px; border-top: 3px solid var(--color-accent); }
.rules b { display: block; font-size: 21px; color: var(--color-text); margin-bottom: 6px; }
.rules span { font-size: 16px; color: var(--color-text-secondary); line-height: 1.3; display: block; }
</style>

<div class="rules">
<div><b>1 · Officers decide</b><span>No legal labels, no demolition advice; a test checks every English and Telugu string</span></div>
<div><b>2 · Boundary status shown</b><span>Every alert shows how certain its boundary is; only confirmed ones lead to action</span></div>
<div><b>3 · New change only</b><span>Change first seen before the baseline date is closed as legacy</span></div>
<div><b>4 · Owner-blind</b><span>Names appear only after field confirmation, to authorised roles; every view logged</span></div>
<div><b>5 · Nothing closes silently</b><span>24 transition rules in the database; two people to close; missed deadlines escalate</span></div>
<div><b>6 · No invented results</b><span>Demo data is labelled fictional; no accuracy claimed before the blind backtest</span></div>
</div>

<!--
These are enforced in code, not policy text:
- Rule 1: an automated wording test fails the build if words such as "illegal" or "encroacher" appear.
- Rule 5: the alert state machine is a database trigger with 24 transition rules; closures as "not real",
  "false alarm" or "no action" need two different people and a reason code. Deadlines: e.g. assign a
  field officer in 1 working day, site check in 7 days (48 h if urgent). Unacknowledged in 24 hours:
  repeated and escalated. Deadlines are proposals to agree with HYDRAA and the Revenue Department.
- Rule 4 exists so an alert can never be used to target or extort the people named.
- The baseline date for the 99 real lakes is 19 July 2024.
-->

---

### 3 · Rules enforced

## Controls cut 124,203 changed pixels to 58 candidates

<div class="columns" style="grid-template-columns: 0.9fr 1.1fr; gap: 50px; align-items: center">
<div>
<div class="metric"><span>124,203</span><span>changed pixels around 99 lakes</span></div>
<div class="metric"><span>58</span><span>candidate changes kept</span></div>
<div class="metric"><span>25</span><span>building candidates refused by radar</span></div>
</div>
<div>

- **Persistence:** two looks at least 5 days apart, no reversal
- **Minimum area:** 1,000 sq m, about a quarter acre
- **Season and drought:** same months in earlier years; worse than the 5 nearest lakes
- **Buildings:** radar return must rise at least 3 dB
- **Baseline:** nothing first changed before the baseline date

</div>
</div>

<div class="note">Real screen of 22 Nov 2026 · each pixel is 10 m × 10 m · candidates are not findings: accuracy is measured only by the blind backtest</div>

<!--
Real numbers from the prototype's screen of 99 Hyderabad lakes with images up to 22 November 2026.
The controls held back the seasonal and one-off changes; 58 candidate changes remained on 15 lakes
(46 clearing, 11 soil fill, 1 building confirmed by radar at +5.3 dB). Radar refused 25 Sentinel-2
building candidates whose return did not rise.
All 58 sit on the watch list because these lake outlines are derived from OpenStreetMap, not notified.
Thresholds are starting values, tuned only on five separate tuning lakes and frozen before the backtest.
Designed for the monsoon: radar-only alerts, marked "optical confirmation pending" (not yet built).
Do not present 58 as encroachments: they are candidates awaiting review.
-->

---

### 4 · Technology and data

## Optical, radar and sub-metre imagery, each with one job

| Source | Detail | Job |
|---|---|---|
| Sentinel-2 L2A | Optical, 10 m, every 5 days | Weekly screen: water, vegetation, soil, built-up |
| Sentinel-1 | Radar, 10 m, sees through cloud | Confirms buildings; watch through the monsoon |
| Cartosat-3 or commercial | Sub-metre, 0.3 to 0.5 m | Confirms priority cases: footprints, sheds, plots |
| Field, CCTV, drones | Geotagged, hashed photos | Verifies on the ground |
| Boundaries | HMDA and HYDRAA FTL files | Replace the derived outlines used today |

<div class="note">Prototype reads Sentinel-2 from Earth Search and Sentinel-1 from Planetary Computer as cloud-optimised windows, never whole scenes · "Contains modified Copernicus Sentinel data 2026"</div>

<!--
Sentinel data is free and open under the Copernicus licence; every derived image carries the notice.
ISRO high-resolution imagery is free to government bodies under the Indian Space Policy 2023, routed
through NRSC (routing not yet confirmed). Commercial tasking at 30 to 50 cm is the fallback.
Sharing imagery at 30 cm or finer needs IN-SPACe authorisation, so anything shared defaults to 50 cm.
Official FTL files from HMDA or HYDRAA-Raksha replace the OpenStreetMap outlines; until then every
real alert stays on the watch list.
-->

---

### 4 · Technology and data

## An open, portable stack the State can host and own

<style scoped>
.stack { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; margin-top: 4px; }
.stack div { background: var(--color-bg-alt); border-radius: 12px; padding: 14px 18px; }
.stack b { display: block; font-size: 21px; color: var(--color-text); margin-bottom: 4px; }
.stack span { display: block; font-size: 16.5px; color: var(--color-text-secondary); line-height: 1.35; }
</style>

<div class="stack">
<div><b>Detection</b><span>Python, STAC catalogues, Rasterio, NumPy · rules versioned and hashed on every run</span></div>
<div><b>Platform</b><span>FastAPI modular monolith · PostgreSQL 16 with PostGIS 3.4 · append-only tables, hash-chained audit</span></div>
<div><b>Apps</b><span>React and MapLibre analyst desk · offline field app in English and Telugu · WeasyPrint evidence packs</span></div>
<div><b>Hosting</b><span>Docker on one server · State Data Centre or an Indian cloud · State owns all data · runs offline</span></div>
</div>

<div class="note"><span class="tag pilot">Pilot</span> State single sign-on and MFA, row-level security by department and area, S3 storage with object lock, transactional outbox &nbsp; <span class="tag later">Later</span> Kubernetes or a message broker only on measured need; deep learning trained on officer-verified outcomes</div>

<!--
No licence fees in the core stack, and nothing that locks the State to one vendor or one imagery
provider. The whole demo, including maps, runs without internet.
Deep learning is deliberately later: there is no labelled Hyderabad training data today, and explainable
index rules are easier to defend in court. Officer-verified outcomes become the training set.
The pilot additions are designed, not built; say so if asked.
-->

---

### 4 · Technology and data

## Already screening 99 real Hyderabad lakes

<div class="columns-3" style="grid-template-columns: repeat(4, 1fr); gap: 20px; margin-top: 20px">
<div class="metric"><span>99</span><span>lakes inside the ORR</span></div>
<div class="metric"><span>7,652</span><span>clear looks since 2022</span></div>
<div class="metric"><span>14 days</span><span>every lake seen clearly within</span></div>
<div class="metric"><span>28 min</span><span>full screen on one laptop</span></div>
</div>

<div class="note" style="font-size:18px; margin-top:34px">The officer loop (legal check, field app, evidence pack, monthly page) runs end to end, offline, on a labelled fictional demo world · 249 API tests and 15 browser tests pass · no accuracy claimed until the blind backtest on 30 public cases</div>

<!--
Images up to 22 November 2026. Every one of the 99 lakes had a clear look within the last 14 days.
The first screen, from March 2022 to November 2026, took 28 minutes on a laptop CPU; a rerun from
cache takes minutes. No GPU is needed for the pilot.
Coverage is reported honestly: the system never shows "no change" where no valid observation exists.
Offer the live demo here if time allows.
-->

---

### What happens next

## Each phase must earn the next

<div class="steps">
<div><strong>Dec 2026</strong>Blind backtest<small>30 public cases on archived images · gate: at least 21 of 30 flagged before public action · no cost</small></div>
<div><strong>Jan to Mar 2027</strong>Demonstration<small>About 20 recovered assets with HYDRAA · gate: officer named, boundaries shared · no cost</small></div>
<div><strong>Apr to Sep 2027</strong>Paid pilot<small>100 lakes and 10 parcels through one monsoon · ₹40 to 60 lakh</small></div>
<div><strong>From Oct 2027</strong>Core urban region<small>900+ lakes and recovered assets · ₹4.5 to 9.5 crore a year</small></div>
</div>

<div class="note">Indicative cost to Government; planning estimates, not quotes · we stop if the backtest flags under 15 of 30, or precision is under 50% at pilot month 4</div>

<!--
The ask: a named officer and official boundary files for the demonstration on recovered assets.
Pilot targets, to agree with HYDRAA, not results: 70% field-confirmed precision by month 6; 14 days
median from first change to field check (30 in monsoon); 60% of confirmed cases caught before a
permanent structure; 100% of alerts with a named owner and closure reason; 90% of evidence packs
accepted by legal without rework.
Scale: one year of watch for the core urban region costs less than one acre of recovered land
(HYDRAA's market estimate for Ailapur: ₹17.4 crore an acre).
-->

---

<!-- _class: lead -->

# Recovered land stays recovered

## and every action stands up in court

Lake Protect · a weekly watch, a legal check, a field visit, a sealed case file

<!--
Reprise the commercial: Telangana can see its lakes. Lake Protect turns each new change into a dated,
checked, field-verified case with a named officer and a deadline, sealed so it holds up in court.
Pause for questions; use the appendix.
-->

---

### Appendix

## Detection rules, and what is live today

| Rule | What it watches | Status |
|---|---|---|
| R01 Water spread | Context only: water loss alone never alerts | <span class="tag built">Built</span> |
| R02/R03 Building in FTL or buffer | 10 m screen with radar; sub-metre confirm | <span class="tag built">Built</span> <span class="tag pilot">Pilot</span> |
| R04 Soil fill or dumping | Water to bare soil at the lake edge | <span class="tag built">Built</span> |
| R05 Government parcel occupation | Surveyed agency land, from 2028 | <span class="tag later">Later</span> |
| R06 Vegetation clearing | Vegetation to bare soil, against last year | <span class="tag built">Built</span> |
| R07 Levelling or excavation volume | Drone or stereo height models | <span class="tag later">Later</span> |
| R08/R09 Nala, feeder and road | Sub-metre images for narrow channels | <span class="tag later">Later</span> |
| R10 Citizen report check | Match to an asset, recheck the latest look | <span class="tag pilot">Pilot</span> |

<!--
Rules are a versioned YAML file (detect-v1); its SHA-256 is recorded on every run, so any case can show
exactly which rules produced it.
-->

---

### Appendix

## Boundary status decides what an alert may do

| Cohort | Asset | Boundary | Alert may |
|---|---|---|---|
| A | Recovered land in State hands | Physically marked | Act: full officer path |
| B | Lake with final notification | Final notice | Act |
| C | Lake with preliminary notification | Preliminary | Act |
| D | Lake without notification | Derived | Verify: field check only |
| E | Surveyed agency land | Agency survey | Act, routed to the owning agency (2028) |
| F | Revenue land by survey number only | Survey number | Watch |

<div class="note">A live court matter moves any alert to a legal hold, whatever the cohort · the 99 real lakes today are cohort D</div>

<!--
Source: the shortlisted proposal. Cohorts A to D start in the 2027 pilot; E from 2028; F later.
-->

---

### Appendix

## What exists, what the pilot adds, what comes later

| Area | <span class="tag built">Built</span> | <span class="tag pilot">Pilot</span> | <span class="tag later">Later</span> |
|---|---|---|---|
| Detection | Sentinel-2 and radar on 99 real lakes | Blind backtest; sub-metre confirm | Deep learning on verified outcomes |
| Workflow | Legal check, state machine, escalation | Agreed deadlines with HYDRAA | Per-category policies |
| Field and evidence | Offline field app; sealed packs; verify tool | Counsel-reviewed certificate | Drone integration |
| Citizens | Signals table | WhatsApp and web intake, in English, Telugu and Urdu | — |
| Security | Role checks, hash-chained audit | State SSO, MFA, row-level security | Key management, high availability |

<!--
Proposal slide 26 lists the statewide registry, department security, S3 storage and the outbox as built;
they are designed, not built. This slide is the accurate version: use it if the jury asks.
-->
