# GeoGuard (formerly Lake Protect): Build Context

Single source for building the prototype. A developer or coding agent should be able to start from this file with no other context.

| | |
|---|---|
| **Status** | Prototype milestones M0, M1 and M4 to M9 are built on demo data; the backtest (M2, M3) is not. See `PROGRESS.md`. |
| **Last updated** | 7 November 2026: section 17 added (officials, personas, detection by stage, alert contents, escalation, due diligence, dashboard, citizen reporting) and the imagery and owner-blind decisions refined at the owner's request |
| **Name** | **GeoGuard**, chosen by the owner on 25 Nov 2026 (DECISIONS.md D-061). "Lake Protect" was the working name, and the name the TISC jury shortlisted. Code names keep it for now. |
| **Background** | [Feasibility and solution design](https://claude.ai/artifact/6SgGGK4e8Zf8gyzjbC13wD) and [pitch deck](https://claude.ai/artifact/ABdLPgjWa1t5Y7V855Kbsa). Both are private until the owner shares them. |

**How to use this file:** read sections 1 to 3, then build in the order given in section 12. Sections 6 to 10 are the specification. Section 15 lists what is already decided, so do not reopen it, and what is still unknown, so do not assume it.

---

## 1. Start here

**What it is.** A monitoring system for Telangana's lakes and government land. Satellite imagery screens every asset each week (free, ISRO or commercial imagery: the source is open, section 17.9). A rules engine checks the legal position of each change. Field teams verify what remains, and officers receive a complete case file.

**Why this shape.** HYDRAA, the Hyderabad agency that protects lakes and public land, already has satellite data from ISRO's National Remote Sensing Centre (NRSC), a lake-boundary portal and 900 CCTV cameras on 264 lakes. No public evidence was found of a recurring alert loop that reaches field teams and produces evidence that holds up in court. That loop is the product. Do not build a satellite-map viewer: the State already has one.

**The pitch in one line.** Not "we find more encroachments" but "your cases hold up".

**What to build first.** The blind backtest (section 8.6), then the demo application (section 9). The backtest comes first because it is the first gate in the plan, needs no government permission, and tells us whether the detection works before anyone sees a pitch.

### Six rules that override everything else

1. **Officers decide.** A satellite sees change, not illegality. The product reports verified facts. It never labels a change illegal and never recommends demolition.
2. **Boundary status is always visible.** Every alert shows how certain its boundary is. Only confirmed boundaries can lead to action.
3. **New change only.** Alert only on change after an asset's baseline date. Old structures are a separate policy problem, not an alert.
4. **Owner-blind detection.** Owner names stay out of the system until a field check confirms the change. The survey-number record (land category, Section 22A status, court cases, disputes) is shown with every alert; the personal names of owners and claimants are not (section 17.10).
5. **Nothing closes silently.** Every action is logged, closing needs two people, and missed deadlines escalate automatically.
6. **No invented results.** Demo data is labelled, uses fictional places, and never appears in a pitch as a finding.

---

## 2. Users

| Role | Who | What they need | Main surface |
|---|---|---|---|
| `analyst` | Vendor or desk staff | Review change candidates, confirm or reject them | Desk |
| `reviewer` | Second analyst | Co-sign closures | Desk |
| `field_officer` | HYDRAA Lake Protection Teams | One clear alert, exact location, simple capture, works offline, Telugu and English | Field app |
| `nodal_officer` | Named HYDRAA officer | Assign alerts, watch timers, clear the queue | Desk |
| `legal_officer` | HYDRAA legal team | Case-ready files, litigation register | Desk |
| `senior_officer` | Commissioner, Secretary | One page a month | Monthly page |
| `auditor` | Internal or external | Read the full log, re-check closures | Audit view |
| `admin` | Vendor | Users, assets, record imports | Desk |
| `revenue_officer` | Tahsildar with Mandal Surveyor | Confirm survey number, land category and title status; joint survey with notice | Desk (design only, not in the prototype) |
| `irrigation_officer` | Irrigation engineer (DEE or AEE) | Confirm the FTL and buffer position and the map version used | Desk (design only) |
| `citizen` | Resident, lake committee | Report a change by WhatsApp or web; get status updates | Portal or WhatsApp (design only) |

Section 17.2 maps every role to Telangana's officials. The audience for the demo is senior officials. They should grasp every screen at a glance, so favour pictures, maps and plain words over tables of numbers.

---

## 3. Prototype scope

### Deliverable A: blind backtest engine

A Python command-line pipeline. Given asset boundaries and a list of past cases, it runs forward through free satellite archives and reports whether each case would have been flagged before public action.

**Done when:** it produces a report scored against the first gate: at least 21 of 30 known events over 0.25 acre flagged before public action (section 8.6).

**Rough effort:** two people, four to six weeks, on free data and with no government permission.

### Deliverable B: demo application

A web app and field app showing the whole loop on about 20 recovered assets: detect, legal check, set priority, analyst review, route, field check, evidence pack, officer record, monthly page.

**Done when:** the 10-minute demo in section 14 runs end to end on one laptop, including offline field capture.

### Out of scope for the prototype

- Live government integrations (Bhu Bharati, BuildNow, HYDRAA portals, CCTV, command centre). Use CSV imports behind a clean interface.
- Ordering ISRO or paid imagery. Record the request and its estimated cost only.
- NISAR, until Sentinel-1 and Sentinel-2 work.
- Deep learning. Rules first (section 15).
- Drone data processing, statewide coverage, Revenue land workflows.
- The citizen reporting channel (section 17.8), the survey-number file from live land records (17.4), the full escalation matrix (17.5) and the drill-down dashboard (17.7). These are part of the solution design and the pitch, not of the current prototype build.
- Production security certification.
- Any real owner or personal data.

---

## 4. Domain primer

### Glossary

| Term | Meaning |
|---|---|
| **HYDRAA** | Hyderabad Disaster Response and Asset Protection Agency. Formed by G.O.Ms.No. 99 on 19 July 2024. Covers the area up to the Outer Ring Road. First customer. |
| **NRSC** | National Remote Sensing Centre, part of ISRO, based in Hyderabad. Signed an agreement with HYDRAA in April 2025 covering lake, canal, park and government land data. |
| **TGRAC** | Telangana Remote Sensing Applications Centre. Compared 920 water bodies across 2014 and 2023, and runs land mapping projects for state agencies. |
| **HMDA, LPC** | Hyderabad Metropolitan Development Authority and its Lake Protection Committee, which issue lake notifications. |
| **CCLA** | Chief Commissioner of Land Administration, head of the Revenue land system. |
| **ORR** | Outer Ring Road around Hyderabad. |
| **Core urban region** | About 2,053 sq km, split since February 2026 into GHMC, Cyberabad and Malkajgiri corporations. Also called CURE or TCUR. |
| **FTL** | Full Tank Level, the highest level a lake can reach. It defines the legal lake area. Certified by the Irrigation and Revenue departments. |
| **Buffer zone** | A protected strip around the FTL (widths below). |
| **Preliminary notification** | Draft boundary. Claims and objections may still be open. |
| **Final notification** | Settled boundary, after claims and objections close. |
| **Cheruvu, kunta, nala** | Lake, small tank, storm drain. |
| **Patta** | Private land title. |
| **Shikam** | Land in a lake bed, which may carry a private claim but has development limits. |
| **Survey number** | Revenue land parcel ID. One number can cover hundreds of acres. |
| **Section 22A list** | Prohibited-property list under the Registration Act. Marks whole survey numbers and is error-prone. Never treat it as truth. |
| **Bhu Bharati** | State land records portal, which replaced Dharani in 2025. |
| **BuildNow** | State building permission system, which replaced TG-bPASS in 2025. |
| **Praja Vani** | HYDRAA's weekly public grievance hearing. |
| **Lake Protection Teams** | HYDRAA field staff. |
| **Section 63(4) BSA** | Bharatiya Sakshya Adhiniyam, 2023. Electronic records need a certificate with the file's hash value (Part A) and an expert's certification (Part B). |
| **Units** | 1 acre = 40 guntas = 4,046.86 sq m. 1 lakh = 100,000. 1 crore = 10,000,000. |

### Buffer widths

Measured from the FTL or defined boundary ([Deccan Chronicle](https://www.deccanchronicle.com/southern-states/telangana/hydraa-demolitions-all-you-want-to-know-about-ftl-buffer-zone-1819329); G.O. Ms. No. 168 of 2012 per [Legal 500](https://www.legal500.com/intelligence/india/environment/ftl-buffer-zone-and-go111-area-demolitions-by-hydraa-%E2%80%93-legal-perspective)).

| Water body | Buffer |
|---|---|
| River | 50 m |
| Lake, tank or kunta of 10 ha or more | 30 m |
| Lake, tank or kunta under 10 ha, and shikam land | 9 m |
| Canal, vagu, nala or storm drain over 10 m wide | 9 m |
| Canal, vagu, nala or storm drain up to 10 m wide | 2 m |

Store these as configuration, not constants. Have counsel confirm them before any real use.

### What the courts and records teach

These facts drive the design:

- **Boundaries change and get contested.** In Boduppal, officials marked 48 houses as inside the FTL using revised proposals. HYDRAA ruled that the 2014 notification applied and had the marks removed ([Siasat](https://www.siasat.com/boduppal-residents-get-relief-as-hydraa-chief-removes-wrong-ftl-tags-3297141/amp/)). So boundaries must be versioned, never overwritten.
- **Courts test process.** Orders have turned on unclear boundaries, missing notice, pending disputes and joint surveys (section 6.7).
- **Timing is policy.** HYDRAA has said it acts on [structures built after July 2024](https://deccanchronicle.com/southern-states/telangana/illegal-buildings-constructed-in-ftl-from-july-2024-will-be-razed-hydraa-chief-1847531) and [will not demolish occupied homes](https://newsmeter.in/top-stories/occupied-houses-on-lake-ftl-wont-face-demolition-says-hydraa-chief-735519). So a dated bracket (last clear image, first changed image) is a core output, and catching soil fill early is the real value.
- **A permit does not settle it.** HYDRAA said under-construction structures with permissions issued after July 2024 [will be checked](https://deccanchronicle.com/southern-states/telangana/illegal-buildings-constructed-in-ftl-from-july-2024-will-be-razed-hydraa-chief-1847531). So a permit inside the FTL or buffer flags a conflict and does not auto-close.
- **Imagery supports but does not prove.** A Kerala ruling, as [reported](https://www.lawweb.in/2025/08/courts-reliance-on-google-maps-to.html), treated Google Earth images as supporting, not conclusive. Never put Google Earth screenshots in an evidence pack.
- **Lake restoration looks like encroachment from space.** HYDRAA is earth-moving at [20 lakes](https://www.deccanchronicle.com/southern-states/telangana/hydraa-protects-110-l-cr-worth-of-public-land-from-encroachments-1962508). Without a register of authorised works, these become false alerts.

---

## 5. Functional architecture

Read from the bottom up. Data comes in at the base, and people act at the top.

```text
PEOPLE    Senior officers  |  Legal team   |  Field teams  |  Nodal officer
                 ^                ^               ^ v             ^ v
ACT       [8 Monthly page] <- [7 Evidence] <- [6 Field   ] <- [5 Alert    ]
                                 pack           check           routing
                                                  :               ^
                     field results improve step 1 :               |
                                                  :               |
ANALYSE   [1 Detect    ] -> [2 Legal   ] -> [3 Set     ] -> [4 Analyst ]
            change            check           priority        review
                 ^                ^               ^
DATA      Satellite images  |  Legal records  |  Field signals

SAFEGUARDS ACROSS EVERY LAYER: access by role, every action logged,
deadlines escalate, State-owned data hosted in India
```

| # | Function | Input | Output | Prototype depth |
|---|---|---|---|---|
| 1 | Detect change | Sentinel scenes, boundaries, baseline | Candidates with geometry, type, dated bracket, confidence | Real pipeline |
| 2 | Legal check | Candidate, boundary versions, permits, works, court register | Zone, mode, alert class, next state | Real rules, seeded records |
| 3 | Set priority | Candidate and legal result | Score with stored factors, optional imagery request | Real score, imagery request is a stub |
| 4 | Analyst review | Before and after image pair | Confirm, or close as not real (two people) | Real screen |
| 5 | Alert routing | Confirmed alert | Named owner, due date, escalation | Real |
| 6 | Field check | Assigned alert | Geotagged photos, outcome | Real offline-capable app |
| 7 | Evidence pack | Everything above | PDF, zip, manifest of hashes, readiness checklist | Real, certificate marked draft |
| 8 | Monthly page | All alerts | One-page bulletin with map and overdue list | Real, from the database |

Inputs by group:

- **Satellite images:** free radar and optical data, then ISRO and paid imagery on a cue.
- **Legal records:** FTL maps, survey parcels, permits, authorised works, court case register.
- **Field signals:** CCTV alerts, Praja Vani complaints, citizen reports. These raise priority or open a check; they never create a finding alone.

Section 17 turns this into the solution architecture shown to officials: what comes in (imagery, government records, ground and citizen signals), the platform (detect, check the records, route and escalate, seal the evidence), and who acts (field teams, verifiers, officers, senior officials, citizens).

---

## 6. Business rules

### 6.1 Asset cohorts

Every asset belongs to one cohort, which sets what an alert may do.

| Cohort | Asset | `boundary_status` | Mode | Start |
|---|---|---|---|---|
| A | Recovered land, cleared and in state hands | `physically_marked` | `ACTION` | Prototype |
| B | Lake with final notification | `final_notification` | `ACTION` | Prototype |
| C | Lake with preliminary notification | `preliminary_notification` | `VERIFY` | Prototype |
| D | Lake without notification | `derived` | `WATCH` | Prototype |
| E | Surveyed agency land (endowments, housing, police, transport) | `surveyed_agency` | `ACTION`, sent to owning agency | 2028, model only |
| F | Revenue land known only by survey number | `survey_number_only` | `WATCH` | Later, model only |

- **`ACTION`:** full path to an officer.
- **`VERIFY`:** field check allowed. No officer path until the boundary is final.
- **`WATCH`:** logged and flagged to the boundary team. No field action.
- **Live court matter:** moves to `HOLD_LEGAL`, whatever the cohort.

Start with cohort A. The boundary is marked, the land is cleared, HYDRAA's own plan asks for [monitoring of retrieved assets](https://www.deccanchronicle.com/southern-states/telangana/hyderabads-shrinking-lakes-trigger-hydraa-action-plan-1944775), and an alert protects reported gains instead of opening a new fight.

### 6.2 Legal check

Runs automatically on every candidate, before any analyst time or paid imagery.

```python
def legal_check(candidate) -> str:
    asset = candidate.asset
    boundary = current_boundary(asset)          # newest version in force
    zone = locate(candidate.geom, boundary)     # inside_ftl, buffer, watch_ring, outside

    if zone == "outside":
        return "CLOSED_OUT_OF_SCOPE"
    if candidate.first_changed_at <= asset.baseline_date:
        return "CLOSED_LEGACY"                  # logged, never alerted
    if hits_authorised_work(candidate):         # for example HYDRAA restoration
        return "CLOSED_AUTHORISED"              # stores the reference

    permit = hits_valid_permit(candidate)
    if permit and zone == "watch_ring":
        return "CLOSED_AUTHORISED"
    if permit:
        candidate.flags.add("permit_conflict")  # never auto-close inside FTL or buffer

    if hits_court_register(candidate):
        return "HOLD_LEGAL"
    if MODE_BY_COHORT[asset.cohort] == "WATCH":
        return "WATCH_LIST"
    return "TRIAGE"
```

Every result stores `rule_version`, the boundary version used and the records it matched.

### 6.3 Alert class

Separate these because they follow different legal routes.

| `alert_class` | Meaning |
|---|---|
| `GOVT_LAND` | Change on recovered parcels or land recorded as government land |
| `RESTRICTED_PRIVATE` | Change inside FTL or buffer on land with a private title claim |
| `DISPUTED` | Court register hit |
| `UNKNOWN` | Land category not yet known. The default until records say otherwise |

Land category is not an owner name. Rule 4 still applies.

### 6.4 Priority score

Rule-based and owner-blind. Weights are starting values to tune. Store every factor on the alert. Manual overrides need a reason and are logged.

```text
score = 100 * (0.35*stage + 0.25*area + 0.20*growth + 0.20*cohort)

stage   soil_dumped, land_levelled, sheds_fences = 1.0   (still preventable)
        building_rises = 0.8
        occupied = 0.2
area    clip((log10(area_sq_m) - 3) / 2, 0, 1)           (1,000 sq m = 0; 100,000 sq m = 1)
growth  clip(area growth since previous observation, 0, 1)
cohort  A = 1.0, B = 0.9, C = 0.5
```

### 6.5 Alert lifecycle

| From | To | Actor | Guard and required data |
|---|---|---|---|
| none | `CANDIDATE` | Pipeline | Persistence rule passed, area at or above the minimum |
| `CANDIDATE` | `CLOSED_OUT_OF_SCOPE`, `CLOSED_LEGACY`, `CLOSED_AUTHORISED` | System | Reference stored |
| `CANDIDATE` | `HOLD_LEGAL` | System | Court register hit |
| `CANDIDATE` | `WATCH_LIST` | System | Cohort D or F |
| `CANDIDATE` | `TRIAGE` | System | Everything else |
| `HOLD_LEGAL` | `TRIAGE` | Legal officer | Reason and case status reference |
| `WATCH_LIST` | `TRIAGE` | Nodal officer | New boundary version with a confirmed status. Asset moves to the matching cohort |
| `TRIAGE` | `CLOSED_NOT_REAL` | Analyst and reviewer | Two different users, reason code. Label saved for tuning |
| `TRIAGE` | `CONFIRMED` | Analyst | Image pair reviewed |
| `CONFIRMED` | `ASSIGNED` | Nodal officer or auto-rule | Named field owner and due date |
| `ASSIGNED` | `ASSIGNED` | Field officer | Outcome `cannot_access`, with reason. Timer keeps running |
| `ASSIGNED` | `CLOSED_FALSE_ALARM` | Field officer and nodal officer | Two different users, reason |
| `ASSIGNED` | `FIELD_CONFIRMED` | Field officer | Geotagged photo, GPS fix, timestamp |
| `FIELD_CONFIRMED` | `AWAITING_BOUNDARY` | System | Cohort C |
| `AWAITING_BOUNDARY` | `FIELD_CONFIRMED` | Nodal officer | New boundary version with a final status. Asset moves to cohort B, so the alert does not loop back |
| `FIELD_CONFIRMED` | `PACK_READY` | Nodal or legal officer | Evidence pack generated, checklist recorded |
| `PACK_READY` | `WITH_OFFICER` | Nodal officer | Boundary confirmed. Checklist gaps need a logged reason and show as a banner |
| `WITH_OFFICER` | `ACTION_RECORDED` | Officer | Notice, hearing, order and action references as applicable |
| `WITH_OFFICER` | `CLOSED_NO_ACTION` | Officer and nodal officer | Two different users, reason |
| `ACTION_RECORDED` | `POST_ACTION_WATCH` | System | Land stays on weekly watch. New change creates a new candidate |
| any `CLOSED_*` from analyst, field or officer | `TRIAGE` | System | Re-check finds the change persisting or growing. Marked as reopened |

Implement this as one table-driven state machine. No code path may change state except through it. Each transition writes an audit event.

### 6.6 Timers and escalation

Proposed defaults, to agree with HYDRAA. Keep them configurable.

| State | Due in | On miss |
|---|---|---|
| `TRIAGE` | 3 days | Notify reviewer |
| `ASSIGNED` | 7 days, 14 in monsoon | Escalate to nodal officer |
| `FIELD_CONFIRMED` | 7 days | Escalate to legal officer |
| `WITH_OFFICER` | 30 days | Add to the overdue list on the monthly page |

Monsoon is June to September. Missed timers are never silently reset.

### 6.7 Case-readiness checklist

Each item records yes, no or not applicable, with an evidence reference and who checked it. The checklist informs officers. It does not replace their judgement.

| Key | Check | Why it exists |
|---|---|---|
| `boundary_confirmed` | Final notification or certified survey | High Court found [boundaries "were not clear"](https://thenewsminute.com/telangana/telangana-hc-raps-hydraa-again-for-hasty-evictions-questions-proof-of-violations) in Khajaguda |
| `joint_survey_done` | Joint boundary survey | A [2026 bench](https://www.etvbharat.com/en/state/telangana-hc-stays-single-bench-order-to-remove-ranganath-as-hydraa-commissioner-enn26090203364) wanted it before action on contested land |
| `survey_notice_given` | Survey carried out with prior notice | A 2024 order held surveys without notice vitiated, per [Legal 500](https://www.legal500.com/intelligence/india/environment/ftl-buffer-zone-and-go111-area-demolitions-by-hydraa-%E2%80%93-legal-perspective) |
| `no_live_court_matter` | No live dispute or undertaking | Same [2026 bench](https://www.etvbharat.com/en/state/telangana-hc-stays-single-bench-order-to-remove-ranganath-as-hydraa-commissioner-enn26090203364) |
| `title_permits_reviewed` | Title claims and local permissions reviewed | [2024 guidance](https://www.legal500.com/intelligence/india/environment/ftl-buffer-zone-and-go111-area-demolitions-by-hydraa-%E2%80%93-legal-perspective) requires weighing them |
| `notice_and_hearing` | Notice served and hearing held | [Kokapet order](https://www.telanganatribune.com/telangana-high-court-pulls-up-hydraa-over-kokapet-demolition-without-notice/), May 2026 |
| `construction_dated` | Dated bracket shown against the policy cut-off | [HYDRAA's July 2024 position](https://deccanchronicle.com/southern-states/telangana/illegal-buildings-constructed-in-ftl-from-july-2024-will-be-razed-hydraa-chief-1847531) |

`policy_cutoff_date` is configuration, default `2024-07-19` (HYDRAA's formation). HYDRAA's statements say only "July 2024", so confirm the exact date.

### 6.8 Wording

The interface shapes how officials read a case. Enforce this with a test over all English and Telugu strings.

| Use | Never use |
|---|---|
| change, candidate change | violation |
| verified change, field-confirmed | illegal, unauthorised (unless quoting an order) |
| case file, evidence pack | proof of encroachment |
| land category, title claim | encroacher, land grabber |
| action recorded, order reference | demolish, demolition (unless quoting an order) |

Every evidence pack and alert detail screen must carry: **"Imagery shows physical change. It does not establish title or legality."**

---

## 7. Data model

PostgreSQL with PostGIS. Store geometry in EPSG:4326 and calculate area in EPSG:32644.

### Enums

```text
cohort            A_RECOVERED, B_FINAL, C_PRELIM, D_UNNOTIFIED, E_AGENCY, F_REVENUE
asset_type        lake, recovered_parcel, agency_parcel, revenue_parcel
boundary_kind     ftl, buffer, parcel, watch_ring
boundary_status   physically_marked, final_notification, preliminary_notification,
                  derived, surveyed_agency, survey_number_only
zone              inside_ftl, buffer, watch_ring, outside
change_type       soil_fill, clearing, small_structure, building, water_loss, other
stage             soil_dumped, land_levelled, sheds_fences, building_rises, occupied
sensor_basis      optical_and_radar, optical_only, radar_only
alert_class       GOVT_LAND, RESTRICTED_PRIVATE, DISPUTED, UNKNOWN
mode              ACTION, VERIFY, WATCH
alert_state       see section 6.5
field_outcome     confirmed, false_alarm, cannot_access
role              see section 2
```

### Tables

```text
assets            id, name, name_te, type, cohort, district, mandal, village, survey_numbers[],
                  area_acres, custodian_agency, has_cctv, baseline_date, is_demo, notes

boundaries        id, asset_id, version, kind, status, geom, source_name, source_url, source_date,
                  notification_ref, certified_by, valid_from, valid_to, supersedes_id, sha256
                  (append-only: a change is a new version, never an update)

observations      id, sensor, scene_id, acquired_at, cloud_pct, stac_href, processing_version,
                  licence_notice, sha256

candidates        id, asset_id, boundary_id, geom, area_sq_m, change_type, stage_estimate,
                  last_clear_at, first_changed_at, observation_ids[], sensor_basis, confidence,
                  rule_version, flags[], before_chip, after_chip, created_at

legal_checks      id, candidate_id, zone, boundary_status, mode, alert_class, result,
                  matched_permit_id, matched_work_id, matched_court_case_id, rule_version, checked_at

alerts            id, code, candidate_id, state, priority_score, priority_factors(jsonb),
                  owner_user_id, due_at, escalation_level, reopened_count, is_demo, created_at, updated_at

permits           id, source, ref, geom, kind, valid_from, valid_to, is_demo
authorised_works  id, agency, description, ref, geom, starts_on, ends_on, is_demo
court_cases       id, court, case_no, status, asset_id, survey_numbers[], geom, next_hearing,
                  last_checked_at, is_demo

field_checks      id, alert_id, officer_id, observed_at, lat, lon, gps_accuracy_m,
                  distance_to_candidate_m, outcome, observed_stage, notes, photo_paths[],
                  photo_sha256[], device_time, synced_at

owner_claims      id, alert_id, claim_type, claimant_name, document_ref, entered_by, entered_at
                  (insert allowed only after FIELD_CONFIRMED; enforce in the database and API)

readiness_items   id, alert_id, item_key, status, evidence_ref, checked_by, checked_at

evidence_packs    id, alert_id, version, pdf_path, zip_path, manifest_sha256, generated_by,
                  generated_at, counsel_reviewed

officer_records   id, alert_id, officer_id, notice_ref, notice_date, hearing_date, order_ref,
                  order_date, action_date, action_summary

imagery_requests  id, alert_id, provider, area_sq_km, est_cost_usd, status, requested_by, approved_by

signals           id, kind, asset_id, geom, received_at, ref, linked_alert_id, is_demo

users             id, name, role, language, area_geom, is_active

audit_log         id, actor_id, action, entity, entity_id, details(jsonb), at, prev_hash, hash
                  (append-only hash chain: hash = sha256(prev_hash + canonical row). Also logs views and exports)

bulletins         id, month, stats(jsonb), pdf_path, generated_at
```

---

## 8. Detection pipeline

### 8.1 Data sources

Checked on 5 November 2026. Re-check endpoints before depending on them.

| Source | Use | Detail | Access |
|---|---|---|---|
| **Sentinel-2 L2A** | Optical screening | 10 m, 20 m for SWIR and scene class. 5-day revisit | [Earth Search STAC](https://earth-search.aws.element84.com/v1), collection `sentinel-2-c1-l2a`. Cloud-optimised GeoTIFF over public HTTPS. A test query returned a Hyderabad scene from 3 Nov 2026 |
| **Sentinel-1** | All-weather radar, main sensor June to September | IW 5 x 20 m. 6-day repeat with 1C and 1D | [Copernicus Data Space STAC](https://stac.dataspace.copernicus.eu/v1/), collection `sentinel-1-grd`, cloud-optimised GeoTIFF, free account. Or [Planetary Computer](https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-rtc) `sentinel-1-rtc`, 10 m terrain-corrected, account needed. Earth Search `sentinel-1-grd` is requester-pays, so avoid it |
| **Sentinel-1 monthly mosaics** | Quick radar baseline | 20 m and 40 m, monthly from 2020 | Copernicus Data Space, collection `sentinel-1-global-mosaics` |
| **JRC Global Surface Water** | Seasonal water history | 30 m, monthly, March 1984 to December 2021 | [Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_MonthlyHistory) `JRC/GSW1_4/MonthlyHistory` |
| **Open Buildings Temporal** | Built-up baseline | Annual, 2016 to 2023, covers India | [Google Research](https://sites.research.google/gr/open-buildings/temporal), Earth Engine `GOOGLE/Research/open-buildings-temporal/v1` |
| **NISAR L-band** | Later: second radar view through vegetation | 12-day repeat. HDF5. Public since 20 July 2026, provisional | [ASF](https://nisar-docs.asf.alaska.edu/access-overview/), `asf_search`, free Earthdata Login. Resolution and Hyderabad coverage not yet confirmed |
| **ISRO high-resolution** | Confirm priority cases, production only | Finer than 5 m. [Free to government bodies, priced for private firms](https://www.isro.gov.in/media_isro/pdf/IndianSpacePolicy2023.pdf) | Through NRSC. Order routing not confirmed |
| **Commercial 30 to 50 cm** | Fallback, production only | About [$17 to $26 per sq km archive, $25 to $55 tasking](https://geopera-website.pages.dev/blog/satellite-imagery-cost-guide), reseller guide figures | Stub only in the prototype |

These are the free sources the backtest and first pipeline use. The production imagery source is open: free, ISRO or commercial, chosen per phase (section 17.9).

**Licence notices to carry:**

- Sentinel derived output: `Contains modified Copernicus Sentinel data [Year]` ([legal notice](https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice)).
- JRC layers on published maps: `Source: EC JRC/Google`.
- Open Buildings: CC BY 4.0 or ODbL.
- Indian Space Policy 2023: disseminating imagery at 30 cm or finer needs IN-SPACe authorisation, and coarser data needs intimation. Default to 50 cm in anything shared.

### 8.2 Boundary sources

| Source | Status | How to use |
|---|---|---|
| [HMDA Lakes Portal](https://lakes.hmda.gov.in) | Responds, titled "HMDA-Lakes". A secondary source says it filters by district, mandal, village and lake, with FTL in blue and buffer in red. Bulk download not confirmed | View and digitise by hand for internal testing. Check terms first. Do not scrape |
| [HMDA notifications](https://hmda.gov.in/wp-content/uploads/2020/07/Preliminary-Notification-of-Lakes-Outside-ORR-under-6th-Phase.pdf) | Public PDFs. The ones found are preliminary | Use for `notification_ref` and status |
| [HYDRAA website](https://www.siasat.com/hydraa-launches-portal-to-check-ftl-before-buying-homes-3540671/) | Launched 11 September 2026. Links to the HMDA portal and Bhu Bharati. URL not confirmed | Reference. Ask for official files |
| [HYDRAA-Raksha](https://newsmeter.in/hydraa/nrsc-satellite-data-helping-hydraa-identify-lake-boundaries-prevent-encroachments-in-hyderabad-764543) | Launched March 2026 with FTL and buffer search up to the ORR | Ask for official files through the first meeting |
| JRC maximum water extent, or OpenStreetMap water | Free and quick | Status `derived`. Fine for a first backtest run, never for field action |

Every boundary stores its source, date and status. Official files should replace hand-digitised ones when the government shares them.

### 8.3 Area and grid

- **Approximate area up to the ORR:** bbox `[78.22, 17.20, 78.72, 17.62]` (west, south, east, north). This is an estimate, so replace it with the official boundary.
- **Working CRS:** EPSG:32644 (UTM 44N), 10 m grid.
- **Mixed zones:** Hyderabad sits near the 78°E zone edge, so scenes arrive from both UTM 43 (tile `43QHV`) and UTM 44. Reproject everything, and remove duplicate overlaps by acquisition date.
- **AOI per asset:** boundary polygon, its buffer and a 100 m watch ring.
- **Efficiency:** read windows from cloud-optimised GeoTIFFs only. Never download whole scenes. Cache outside OneDrive (section 11).

### 8.4 Method, version 0

Rules before machine learning, because they are easier to explain and labels are scarce.

**Sentinel-2.** Earth Search asset keys are `blue`, `green`, `red`, `nir`, `swir16`, `swir22`, `scl`. Apply the scale and offset in each item's raster metadata. Mask `scl` classes 0, 1, 3, 8, 9 and 10.

```text
MNDWI = (green - swir16) / (green + swir16)
NDVI  = (nir - red) / (nir + red)
NDBI  = (swir16 - nir) / (swir16 + nir)
BSI   = ((swir16 + red) - (nir + blue)) / ((swir16 + red) + (nir + blue))
```

**Sentinel-1.** Use VV and VH in dB. Reduce speckle with a multi-temporal median, not spatial smoothing that blurs small changes.

**Starting thresholds.** These are untested. Tune them on the tuning lakes only (section 8.6).

| Class | Rule |
|---|---|
| Water | MNDWI > 0, or VV below a per-scene Otsu threshold (fallback -15 dB) |
| Bare soil | BSI > 0.1 and NDVI < 0.2 |
| Vegetation | NDVI > 0.4 |
| Built | NDBI > 0 and VV at least 3 dB above baseline |

**Transitions that make a candidate.**

| Transition | `change_type` | Likely stage |
|---|---|---|
| Water to bare soil, at the lake edge | `soil_fill` | `soil_dumped` |
| Vegetation to bare soil | `clearing` | `land_levelled` |
| Bare soil or vegetation to built | `building` | `building_rises` |
| Water loss alone | `water_loss` | Never alerts on its own |

Small sheds, fences and walls are below what Sentinel can see. Sentinel-2 [cannot efficiently detect footprints under 10 x 10 m](https://www.iitis.pl/pl/bibcite/reference/16126). Those need high-resolution imagery or a field check, so do not claim to detect them.

**False-alarm controls, all required.**

1. **Persistence:** at least two independent observations, at least 5 days apart, with no reversal between them.
2. **Minimum area:** 1,000 sq m, about 0.25 acre or 10 Sentinel-2 pixels. Use 8-connected components.
3. **Seasonal control:** compare with the same calendar months in the previous two years, plus JRC history where it exists.
4. **Drought control:** require the lake's water anomaly to be at least 10 percentage points worse than the median of its 5 nearest lakes.
5. **Monsoon:** [cloud cover averages 79 to 89%](https://www.climate-zone.com/climate/in/hyderabad) from June to September. Accept radar-only candidates in those months, set `sensor_basis = radar_only`, lower the confidence and show "optical confirmation pending".
6. **Baseline:** ignore anything first changed on or before the asset's `baseline_date`.

**Dated bracket.** From each polygon's time series, record `last_clear_at` and `first_changed_at`. This is the single most useful field in the product.

**Output.** One GeoJSON feature per candidate with the fields in section 7, plus before and after image chips (PNG, true colour, same window, with the boundary drawn on top).

### 8.5 Command line

```text
lp fetch     --asset <id> --from 2017-01-01 --to 2026-11-01
lp detect    --asset <id> --as-of 2024-06-30
lp backtest  --cases data/cases.csv --assets data/assets.geojson --freeze rules-v0
lp report    --run <id>
```

### 8.6 Blind backtest protocol

This is Gate 1. Protect its honesty, because the result will be shown to officials.

1. **Tune separately.** Tune thresholds on at least 5 lakes that are not among the 30 scored cases.
2. **Freeze.** Tag rules and thresholds in git before the scored run. Run the scored set once. A re-run after changes needs a new tag and must be reported as such.
3. **No look-ahead.** Step weekly. At each `as_of` date use only scenes acquired on or before it. A test must prove this.
4. **Scoring window.** Use cases after 2017, when Sentinel-1 and Sentinel-2 are both dense.
5. **Flagged means:** a candidate intersects the event area with an alert date before the public action date.
6. **Eligible events:** over 0.25 acre, with a known location and a date. Log ineligible cases and leave them out of the score.
7. **Check false flags by hand:** sample them against high-resolution history. Use that history only to check results, never as a pipeline input, and never in an evidence pack.

**Report must show:**

- Events flagged, against the pass mark of 21 of 30.
- Median lead time in days before public action.
- False flags per lake per year.
- Results split by sensor and season.
- An image chip pair for every case, flagged or missed.
- The rule version and a list of ineligible cases.

**Decision after the run:**

| Result | Decision |
|---|---|
| 21 or more of 30 | Gate 1 passed. Move on to the demo with this result |
| 15 to 20 | Study misses, tune on separate lakes, freeze a new version and report both runs |
| Under 15, or reviewers buried in false flags | Stop and rethink. This is a stop condition in the plan |

---

## 9. Application

### 9.1 Screens

| Screen | Who | Must show |
|---|---|---|
| **Alert queue** | Analyst, nodal, legal | Map and list together. Filters by state, mode, cohort and overdue. Sort by priority |
| **Alert detail** | Analyst, nodal, legal | Boundary with status badge, candidate polygon, before and after images with dates and sensor, dated bracket, legal check panel, timeline, actions allowed for this role, the rule 6.8 statement |
| **Assets** | Admin, nodal | Cohort, boundary versions with source, baseline date |
| **Records** | Admin, legal | Permits, authorised works and court cases, with CSV import |
| **Evidence pack** | Nodal, legal | Checklist, preview, download |
| **Officer record** | Officer | Notice, hearing, order and action fields. No suggested outcome |
| **Monthly page** | Senior officer | See 9.4 |
| **Audit view** | Auditor | Full log, chain check result, random closure sample |
| **Field app** | Field officer | See 9.2 |

Use large map-first layouts. Show a visible `Demo data` badge whenever `is_demo` records are on screen.

### 9.2 Field app

A progressive web app, so no app store is needed.

- **List:** "My alerts", sorted by due date.
- **Alert:** small map, exact location, link to open in a maps app, before and after images, plain instruction.
- **Capture:** photos, GPS fix and accuracy, timestamp, outcome, observed stage, notes.
- **Offline:** queue everything in IndexedDB and sync when back online. Keep both device time and server time.
- **Location check:** warn if the officer is more than 50 m from the candidate. Warn, do not block.
- **Language:** English and Telugu, switchable. Have Telugu strings reviewed by a native speaker. Bundle a Noto Sans Telugu font.
- **On-screen note, pending counsel:** "This is an observation, not a survey. Do not enter private land." Surveys without notice have been held vitiated, so counsel must settle how field checks work.

### 9.3 Evidence pack

A PDF for reading, and a zip for integrity.

**Contents:**

1. Asset ID, boundary source, status and notification link.
2. Dated image pair with sensor, capture time, resolution, licence, last clear date and first changed date.
3. Processing note with software version, rule version and steps applied.
4. SHA-256 hash of every original and derived file, and a `manifest.json` listing them.
5. Field record with officer, geotag, timestamp and photographs.
6. Case-readiness checklist.
7. Section 63(4) certificate template, Part A and Part B, marked **Draft for counsel review** until `counsel_reviewed = true`.
8. The statement from section 6.8.

Provide `lp verify-pack <zip>` to recompute every hash. Regenerating a pack creates a new version and never overwrites the old one.

### 9.4 Monthly page

One printable page for senior officers.

- **Map:** every lake and parcel, with new alerts marked.
- **Counts:** lakes watched, new alerts, verified, action taken, overdue.
- **Who:** overdue alerts by officer.
- **Trend:** this month against last month.

Everything comes from the database with no hand edits. The original idea was monthly alerts. The design is weekly screening with a monthly page, because a month can separate soil fill from a foundation.

### 9.5 API sketch

```text
POST /auth/login                          demo users only
GET  /assets                  GET /assets/{id}/boundaries
POST /assets/{id}/boundaries              new version, never an update
POST /records/{permits|works|court-cases}/import
POST /candidates                          pipeline ingest, runs legal check and priority
GET  /alerts?state=&mode=&cohort=&overdue=
GET  /alerts/{id}
POST /alerts/{id}/transitions             {to, reason, data}, enforced by the state machine
POST /alerts/{id}/field-checks            idempotent, accepts offline sync
POST /alerts/{id}/owner-claims            rejected before FIELD_CONFIRMED
PUT  /alerts/{id}/readiness/{item_key}
POST /alerts/{id}/evidence-pack           GET to download
POST /alerts/{id}/officer-record
POST /alerts/{id}/imagery-request         stub
GET  /bulletins/{month}
GET  /audit?entity=&actor=                GET /audit/verify
```

Enforce role and area checks on the server. Never rely on hiding buttons.

---

## 10. Safeguards and security

| Requirement | How to enforce it | Prototype |
|---|---|---|
| Access by role and area | Server-side checks. Field officers see only their area | Yes |
| Owner-blind detection | No owner fields on candidates or alerts. `owner_claims` insert blocked before `FIELD_CONFIRMED` | Yes |
| Every action logged | Append-only `audit_log` with hash chain, including views and exports | Yes |
| Two-person closure | Transition guard requires two different users | Yes |
| Automatic escalation | Scheduled job on due dates | Yes |
| Re-check from space | Weekly job reopens closed alerts if change persists or grows. Monthly random sample of closures | Yes |
| Bulk export off | Single-case downloads only. Every export logged | Yes |
| Rule neutrality | Same rules for all. Overrides need a reason | Yes |
| State owns all data | Contract term. Keep the data portable | Design for it |
| Hosting in India | State Data Centre or a government-approved cloud region. So no cloud-only services | Design for it |
| Security audit | Expect a third-party audit. Requirement not yet confirmed | Later |
| Personal data | Treat owner names and photos as personal data under the Digital Personal Data Protection Act, 2023. Minimise them | Design for it |
| Vendor conduct | Staff conflict declarations. Contract bars selling alert data, because early notice is valuable to land brokers and could enable extortion | Later |

---

## 11. Stack and layout

These are defaults, chosen to stay portable to a government data centre. Change one only for a real reason.

| Part | Choice |
|---|---|
| Pipeline | Python, `pystac-client`, `odc-stac`, `rioxarray`, `rasterio`, `scikit-image`, `geopandas`, `shapely`, `typer`, `pytest` |
| API | FastAPI, SQLAlchemy, GeoAlchemy2, Alembic |
| Database | PostgreSQL with PostGIS, in Docker |
| Web and field app | React, TypeScript, Vite, MapLibre GL, `i18next`, PWA with Workbox and IndexedDB |
| PDF | WeasyPrint, with a Noto Sans Telugu font bundled |
| File storage | Local disk behind an S3-style interface, so MinIO or a state store can replace it |
| Jobs | One scheduled worker container |
| Run | `docker compose up` on one machine |

**This machine, checked 5 November 2026:** Windows 11, git 2.49, Docker 29.7, Node 24.18, npm 11.14, Python 3.13.9 through the `py` launcher. PostgreSQL and GDAL are not installed, so run them in Docker or use `rasterio` wheels. The folder is not yet a git repository.

**OneDrive warning:** this folder is inside OneDrive. Keep `node_modules`, virtual environments and the imagery cache outside it, or set `LP_CACHE_DIR` to a local path such as `C:\lp-cache`. Syncing them will be slow and can corrupt files.

```text
lake-protect/
  CONTEXT.md
  README.md
  docker-compose.yml
  .gitignore                  cache, chips, .env, node_modules, venv
  data/
    cases.csv                 backtest cases (section 13)
    assets.geojson            real assets with source and status
    demo/                     fictional seed data
  pipeline/
    lake_protect/             aoi, stac, indices, classify, persistence, candidates, backtest, cli
    tests/
  api/
    app/
      rules/                  legal_check, priority, config
      workflow/               state_machine, timers, escalation
      evidence/               pack, manifest, verify
      bulletin/
      audit/
      routers/
    migrations/
    tests/
  web/
    src/
      desk/  field/  bulletin/  i18n/
  reports/                    backtest output
```

---

## 12. Build order

Each milestone must pass its check before the next starts. Stop after M3 and report the result to the owner.

| # | Milestone | Done when |
|---|---|---|
| M0 | Scaffold | `git init`, Compose brings up the database and API, migrations run, `.gitignore` covers caches |
| M1 | Assets and boundaries | Load real assets. A superseded boundary stays retrievable. Mode-by-cohort tests pass |
| M2 | Detection on Sentinel-2 | `lp detect` produces candidates and image chips for 5 tuning lakes. No-look-ahead test passes |
| M3 | Radar, then scored backtest | Sentinel-1 added, monsoon logic in, rules frozen, 30 cases run once, report written. **Gate 1 decision** |
| M4 | Workflow API | State machine, legal check, priority and audit chain in place. All invariant tests pass |
| M5 | Desk | Analyst can confirm or close from a real image pair. Nodal officer can assign |
| M6 | Field app | Capture works offline, syncs on reconnect, distance warning works, language toggle works |
| M7 | Evidence pack | PDF and zip generated. `lp verify-pack` passes and fails correctly when a file changes. Draft mark shows |
| M8 | Officer record, escalation, monthly page | Overdue list is correct. One-page PDF prints cleanly |
| M9 | Demo | Section 14 runs start to finish on one laptop with no internet, using cached base-map tiles and image chips |

### Invariant tests, all required

1. A court register hit never reaches field assignment.
2. A cohort D or F alert never reaches field assignment.
3. A cohort C alert never reaches `WITH_OFFICER` before its boundary is final.
4. An owner claim before `FIELD_CONFIRMED` is rejected by both API and database.
5. A closure by one person is rejected.
6. Change on or before `baseline_date` never gets past `CLOSED_LEGACY`.
7. A permit inside FTL or buffer never auto-closes an alert.
8. Water loss alone never creates an alert.
9. Editing any audit row makes `GET /audit/verify` fail.
10. The backtest reads no scene acquired after `as_of`.
11. No English or Telugu string uses a banned word from section 6.8.
12. Boundary rows can only be inserted, never updated.
13. A pack shows the title statement, and shows the draft mark until counsel review.

---

## 13. Seed data

### Backtest starter cases for `data/cases.csv`

Taken from press reports. Confirm each location and date before scoring, and drop any you cannot confirm. This is a working list and is not 30 eligible cases yet. Use it internally only: several involve contested facts, and these names must not be published as a list of encroachments.

**Columns:** `case_id, name, district, event_type, event_area_acres, public_action_date, source_url, eligible, notes`

| Case | What is reported | Date anchor | Source |
|---|---|---|---|
| Nalla Cheruvu | 12 acres reclaimed | September 2024 | [SANDRP](https://sandrp.in/2026/02/17/hyderabad-lakes-2025-degradation-continues-amid-hydraa-efforts/) |
| Durgam Cheruvu | 5 acres cleared. Lake shrank from about 160 to 116 acres | 30 December 2025 | SANDRP |
| Bum-Rukn-ud-Daula | 11 to 13 of 17.5 acres recovered | To find | SANDRP |
| Bathukamma Kunta | 16.13 acres originally, 5.15 remaining | To find | SANDRP |
| Thammidikunta, Pedda Cheruvu | Part of HYDRAA's first six revived lakes | To find | SANDRP |
| Sunnam Cheruvu, Mallampet Cheruvu, Dundigal Kotwa pond | Under-construction buildings removed | Before 8 September 2024 | [NewsMeter](https://newsmeter.in/top-stories/occupied-houses-on-lake-ftl-wont-face-demolition-says-hydraa-chief-735519) |
| Komati Kunta | High Court ruling on structures inside FTL | February 2025 | SANDRP |
| Mushkin Cheruvu | 52.2 acres protected | Before June 2026 | [The Week](https://www.theweek.in/news/biz-tech/2026/06/06/hyderabad-asset-protection-financial-district.html) |
| Bhagirathamma and Tautanikunta tanks, Khajaguda | About 10 acres. Court said boundaries "were not clear" | 31 December 2024 | [The News Minute](https://thenewsminute.com/telangana/telangana-hc-raps-hydraa-again-for-hasty-evictions-questions-proof-of-violations). Keep out of the score; use to test the unconfirmed-boundary path |
| Puppalaguda tank | 9.25 acres, untouched to fully encroached | Change 2014 to 2023, reported October 2024 | [The News Minute](https://thenewsminute.com/telangana/telangana-171-natural-water-tanks-encroached-in-past-10-years-says-govt-report) |
| Budwel tank | 6.39 acres | As above | As above |
| Pedda Amberpet tank | 9.48 of 12.09 acres | As above | As above |
| Devaryamjal tank | 9.19 of 22.24 acres | As above | As above |
| Pupplagunda tank | 19.59 acres, partial to full | As above | As above |
| Boduppal tank | 17.03 acres | As above | As above |
| Thumkunta tank | 10.14 acres | As above | As above |
| Miyapur water body | 54.83% of 8.67 acres | As above | As above |

Cases with only a 2014 to 2023 window test whether the change was seen, not lead time. Report them separately. TGRAC's fuller list of 171 changed tanks would be the best source for more cases, so ask for it.

### Demo assets, real monitoring targets

| Group | Examples | Source |
|---|---|---|
| Recovered lakes | HYDRAA's 20 lakes in two phases | [Deccan Chronicle](https://www.deccanchronicle.com/southern-states/telangana/hydraa-protects-110-l-cr-worth-of-public-land-from-encroachments-1962508) |
| Recovered parcels | Ailapur, Ameenpur (about 861 acres), Puppalaguda (198 acres), Quthbullapur (about 300 acres) | Deccan Chronicle, [The Week](https://www.theweek.in/magazine/theweek/statescan/2026/04/25/telanganas-urban-revival-hydraa-reshapes-hyderabad-through-lake-restoration-land-protection.html) |

Check for live court matters before using any real parcel on screen. Show real places only with real pipeline output.

### Demo data rules

- Synthetic alerts use **fictional places**, such as "Demo Cheruvu 1", and made-up survey numbers.
- **Never attach an invented alert, person or violation to a real lake, parcel or name.**
- Every synthetic row has `is_demo = true` and shows a `Demo data` badge.
- Seed at least one alert for each path: full path to officer, not real, false alarm, court hold, watch list, authorised work, permit conflict, overdue, reopened.
- Demo users are fictional role accounts, one per role.

---

## 14. Demo script

Ten minutes, for senior officials. Plain words throughout. Say "demo data" at the start.

| # | Show | Say |
|---|---|---|
| 1 | Map of watched assets | "Every lake and recovered parcel, screened weekly, on free satellite data." |
| 2 | New alert at Demo Cheruvu 1, before and after images | "The same place on two dates. Last clear on one date, first changed on another." |
| 3 | Legal check panel | "Before anyone is sent out, the system checks the boundary, permits, works and court cases." |
| 4 | Other alerts: court hold, restoration work, watch list | "These stop here. A court case goes to the legal team. Your own restoration work does not raise an alarm." |
| 5 | Analyst confirms, nodal officer assigns | "A person reviews it, and a named officer owns it with a deadline." |
| 6 | Phone, offline, in Telugu | "The field team sees one clear alert, even without signal." |
| 7 | Evidence pack and checklist | "The file an officer needs, sealed so any change can be detected." |
| 8 | Officer record screen | "The system stops here. An officer makes every legal decision." |
| 9 | Audit view | "Nothing closes quietly. Two people, every step logged." |
| 10 | Monthly page | "This is the one page you see each month." |

If the backtest has been run, open with its real result.

---

## 15. Decisions and open questions

### Already decided

| Decision | Reason |
|---|---|
| Start with recovered land | Clearest boundary, least dispute, asked for in HYDRAA's own plan |
| Weekly screening with a monthly page | Free data arrives every 5 to 6 days, and a month can separate soil fill from a foundation |
| Tiered imagery: a frequent screening layer, sharper images only on a cue. The provider of each layer (free, ISRO or commercial) is open and chosen per phase. *Changed 7 November 2026 from "free data first" at the owner's request (section 17.9)* | Blanket monthly 50 cm imagery of Telangana would cost over ₹300 crore a year, so sharp images stay targeted whoever supplies them |
| Legal check before analyst and paid imagery | Saves money and keeps blocked cases out of the field |
| Rules before deep learning | Easier to defend in court, and labels are scarce |
| Officers decide, product supplies facts | Courts test process, and the State holds legal authority |
| Owner-blind detection: names withheld until a field check; land category, court cases and disputes shown on every alert. *Refined 7 November 2026 (section 17.10)* | Limits targeting and personal data exposure, while officers see the legal position of the land |
| Annual fee per asset, never per alert or per acre recovered | Other pricing rewards false alarms and would look bad in court |
| Portable stack | Must be able to move to a government data centre |

### Open questions

| Question | Who answers | Until then |
|---|---|---|
| Does any vendor, NRSC or HYDRAA already run or plan recurring alerts? | HYDRAA, NRSC, TGRAC | Build the backtest anyway. Stop if an equal system is live or funded |
| Can we get official boundary files, and may a vendor use them? | HYDRAA, HMDA | Hand-digitise for internal use |
| How many lakes have final notification today? Last count found: 765 of 3,342, January 2025 | HMDA | Treat status per lake as unknown until checked |
| Can NRSC supply confirmation imagery on time, and may a vendor process ISRO data supplied free to HYDRAA? | NRSC | Keep the stub |
| What are the real field team capacity and timer limits? | HYDRAA | Use section 6.6 defaults |
| How must field checks work without being a "survey"? What wording should the certificate use? Who can sign Part B? | Land-law counsel | Draft marks stay on |
| Which hosting and security audit rules apply? | ITE&C, TGTS | Keep the stack portable |
| What is the exact policy cut-off date? | HYDRAA | `2024-07-19`, configurable |
| Do geospatial rules limit imagery over sensitive sites around Hyderabad? Not verified | Counsel, NRSC | Show only asset windows, not area-wide imagery |
| NISAR resolution and coverage over Hyderabad? | Check ASF | Leave NISAR out |
| Final product name? | Owner | Decided: GeoGuard (D-061) |

---

## 16. Plan and key facts

### Plan

| Phase | When (target) | Scope | Gate to pass | Indicative cost to Government |
|---|---|---|---|---|
| Blind backtest | By December 2026 | 30 public cases on free data | At least 21 of 30 flagged before public action | None |
| Free demonstration | January to March 2027 | About 20 recovered assets | HYDRAA names an officer, shares boundaries and agrees targets | None |
| Paid pilot | April to September 2027 | 100 lakes and 10 parcels through one monsoon | See targets below | ₹40 to ₹60 lakh |
| Core urban region | From October 2027 | 900-plus lakes and recovered assets | Renewal funded, one surveyed land agency signs | ₹4.5 to ₹9.5 crore a year |

**Pilot targets**, proposals to agree with HYDRAA, not measured results:

- Field-confirmed precision of at least 70% by month 6.
- Median 14 days from first detectable change to field check in dry months, and 30 days in the monsoon.
- At least 60% of confirmed cases caught before a permanent structure.
- Every alert has a named owner and a closure reason.
- At least 90% of evidence packs accepted by HYDRAA's legal team without rework.

**Stop conditions:** backtest under 15 of 30 (50%), an equivalent system already live or funded, no official boundary access by the end of March 2027, no named officer owning field action, field-confirmed precision under 50% at pilot month 4, or no funded renewal by December 2027.

Prices and costs are planning estimates, not quotes.

### Key facts

As reported, mostly in the press. HYDRAA's figures are agency claims that vary by date and report. Check before quoting.

| Fact | Source |
|---|---|
| Hyderabad lost 61% of its lake area, 1979 to 2024 (NRSC). HYDRAA warns the rest could vanish within 15 years | [Deccan Chronicle](https://www.deccanchronicle.com/southern-states/telangana/hyderabads-shrinking-lakes-trigger-hydraa-action-plan-1944775), [NewsMeter](https://newsmeter.in/hydraa/nrsc-satellite-data-helping-hydraa-identify-lake-boundaries-prevent-encroachments-in-hyderabad-764543) |
| 2,435 acres protected, valued at ₹1.10 lakh crore by HYDRAA (June 2026): 1,804 acres government land, 449 acres lake land | [Deccan Chronicle](https://www.deccanchronicle.com/southern-states/telangana/hydraa-protects-110-l-cr-worth-of-public-land-from-encroachments-1962508) |
| 900 CCTV cameras on 264 lakes, with alerts to Lake Protection Teams (May 2026) | [Siasat](https://www.siasat.com/hydraa-launches-cctv-surveillance-system-to-curb-lake-encroachments-3469341/) |
| 920 water bodies mapped up to the ORR by TGRAC (2014 and 2023) | [The South First](https://thesouthfirst.com/telangana/491-out-of-920-hyderabad-lakes-tanks-encroached-in-20-years-telangana-government-wants-to-reclaim-it) |
| 171 water bodies worsened over about ten years, around 17 a year. Expect low alert volumes, so precision matters most | [The News Minute](https://thenewsminute.com/telangana/telangana-171-natural-water-tanks-encroached-in-past-10-years-says-govt-report) |
| 14,061 structures around 134 lakes, with 250 of 400 objections in litigation (2022 report) | [The News Minute](https://www.thenewsminute.com/telangana/134-lakes-14061-encroachments-state-hyderabad-lakes-170335) |
| 765 of 3,342 HMDA lakes had final notification (January 2025) | [The Hans India](https://www.thehansindia.com/telangana/final-notification-for-765-lakes-issued-hmda-to-hc-934405) |
| 13.82 lakh acres of government land per revenue records (August 2025) | [Deccan Chronicle](https://deccanchronicle.com/southern-states/telangana/government-holds-1382-lakh-acres-across-the-state-as-per-revenue-records-1899654) |
| Section 22A: one upload flagged Survey No. 403 in full, though 2 of its 1,280 acres are restricted | [Siasat](https://www.siasat.com/explained-telanganas-section-22a-land-list-and-who-it-affects-3530652/) |
| Section 63(4) upheld, including hash value and expert part (May 2026) | [LiveLaw](https://www.livelaw.in/top-stories/supreme-court-rejects-challenge-to-s634-bsa-mandating-hash-value-disclosure-for-electronic-evidence-535950) |
| Precedents: BLUIS in Odisha, with [about 768 alerts by November 2021](https://odishabytes.com/national-e-governance-awards-bluis-odisha-wins-gold-for-excellence-in-adopting-emerging-technologies/). Defence Estates tool, with [1,133 changes in 62 cantonments](https://dgde.gov.in/?p=10295). Madhya Pradesh [forest alerts](https://apacnewsnetwork.com/2025/04/mp-govt-launches-indias-first-ai-based-real-time-forest-alert-system/). None publishes verified precision in the reports found, so publishing ours would set us apart | As linked |

The full source list is in the [feasibility document](https://claude.ai/artifact/6SgGGK4e8Zf8gyzjbC13wD). This file is not legal advice.

---

## 17. Solution design for Telangana (added 7 November 2026)

Researched on 7 November 2026 from public reports, court filings and government notices. Titles and procedures are as reported and must be confirmed with HYDRAA, the Revenue Department and HMDA before they are relied on. Sources are listed in 17.12. Sections 17.4 to 17.8 describe the solution as pitched; 17.11 says what the prototype already has.

### 17.1 Who protects lakes and public land today

| Body | Posts | Part they play |
|---|---|---|
| Government of Telangana | Chief Minister; Chief Secretary; Principal Secretary, Municipal Administration and Urban Development (MA&UD) | HYDRAA's Commissioner reports directly to the Chief Minister. The Chief Secretary has reviewed HYDRAA's powers and staffing. HYDRAA, HMDA and the municipal corporations sit under MA&UD. |
| Revenue Department | Chief Commissioner of Land Administration (CCLA) | Heads revenue administration, including Survey, Settlement and Land Records (SS&LR), and runs Bhu Bharati and Grama Palana Officer recruitment. |
| District | District Collector; Additional Collector (Revenue) | Revenue administration of the district. The Collector certifies cadastral maps for FTL notifications. |
| Revenue division | Revenue Divisional Officer (RDO) | Certifies cadastral maps with the Tahsildar. Telangana has about 74 revenue divisions. |
| Mandal | Tahsildar; Mandal Surveyor (SS&LR) | Survey numbers and land records. Prepares lake records for the Lake Protection Committee; joint inspections with Irrigation. |
| Village | Grama Palana Officer (GPO) | 10,954 posts created in March 2025, one per revenue village, to restore village revenue work after VROs were abolished. In April 2026 many qualified candidates still awaited appointment. |
| HYDRAA | Commissioner; Additional Commissioners; Asset Protection, Disaster Management and Logistical Support wings | Protects lakes, nalas, parks and government land up to the ORR (now the core urban region). 169 deputation posts, four of them Additional Commissioners, were reported. 900 CCTV cameras on 264 lakes; guards in shifts at some lakes; a dedicated police station at Buddha Bhavan led by an Assistant Commissioner of Police (order of January 2025); weekly Praja Vani hearings; the 1070 helpline and a WhatsApp number for encroachment reports. |
| HMDA | Metropolitan Commissioner; Lake Protection Committee (LPC) | The LPC was formed by G.O.Ms.No.157, MA&UD, 6 April 2010, and issues preliminary and final FTL notifications. It was chaired by the Metropolitan Commissioner; recent reports name the HYDRAA Commissioner as its chairman. Confirm the current chair. |
| Irrigation and CAD Department | Executive, Deputy Executive and Assistant Executive Engineers | Survey the FTL in the field and certify FTL maps. |
| Municipal corporations | Commissioners; town planning | Building permissions through BuildNow. |
| Registration and Stamps | Sub-Registrars | The Section 22A prohibited-properties list, searchable by district, mandal, village and survey number. It is known to mark whole survey numbers when only part is restricted. |
| Police | Local police stations; HYDRAA police station | Register FIRs on complaints from HYDRAA, Irrigation or Revenue. |
| Courts and litigation | Telangana High Court; Court Case Monitoring System (CCMS) | CCMS, launched in February 2026 and piloted in the Home, Revenue and Higher Education departments, tracks government litigation and links to the High Court's case information. On 14 April 2026 the High Court restrained HYDRAA's demolitions until it files written standard operating procedures, and said action without prior notice is not permissible. |
| Maps and coordination | TGRAC; NRSC; Telangana Integrated Command and Control Centre (TGICCC) | TGRAC and NRSC supply maps and imagery. TGICCC coordinates HYDRAA with other agencies in emergencies. |

**How an FTL is fixed, as reported.** Irrigation surveys the lake and drafts FTL maps. Revenue survey numbers are superimposed and the cadastral map is certified by the Tahsildar, RDO and Collector. The LPC issues a preliminary notification, hears objections and then issues a final notification. The High Court has been told that no statute prescribes this procedure, which is one reason boundaries are contested.

**Scale beyond Hyderabad.** The 2014 minor irrigation census counted about 46,531 tanks and related structures across Telangana. HMDA's area alone has over 3,000 lakes (section 16).

### 17.2 Personas

Each persona maps to a system role (section 2). `revenue_officer`, `irrigation_officer` and `citizen` are design only; the prototype has the original eight roles.

| Persona | Example posts | System role | Sees | Does | Hears about an alert when |
|---|---|---|---|---|---|
| **State overseer** | Chief Secretary; Principal Secretary, MA&UD; CCLA | `senior_officer` | State dashboard and monthly page | Reviews performance across agencies and districts; acts on level 4 escalations | Monthly, and at level 4 |
| **Agency head** | HYDRAA Commissioner; District Collector outside HYDRAA's area | `senior_officer`, and the deciding officer where the law gives them the power | Dashboard of their own area; escalations | Directs or takes the action decision | At level 3, or when a court-sensitive case arises |
| **Nodal officer** | HYDRAA Additional Commissioner (Asset Protection); Additional Collector (Revenue) | `nodal_officer` | Queue, map, deadlines | Assigns each alert to a named field officer and verifiers; sends case files to the officer | When an alert is confirmed, and at levels 1 and 2 |
| **Revenue verifier** | Tahsildar with the Mandal Surveyor | `revenue_officer` | The survey-number file | Confirms the survey number, land category and title status; holds the joint survey with prior notice | When a change in their mandal is field-confirmed |
| **Irrigation verifier** | Deputy or Assistant Executive Engineer, Irrigation | `irrigation_officer` | Boundary versions | Confirms where the change sits against the FTL and buffer, and which map version applies | When a change at a lake is field-confirmed |
| **Field officer** | HYDRAA Lake Protection Team member; GPO outside HYDRAA's area | `field_officer` | One alert, its map and its images | Visits and records photos, position and outcome, even offline | When assigned |
| **Analyst and reviewer** | Vendor or HYDRAA desk staff | `analyst`, `reviewer` | Before and after images | Confirms a change, or closes it as not real with a second person | When a candidate passes the legal check |
| **Legal officer** | HYDRAA legal cell; liaison with the Government Pleader | `legal_officer` | Court register and case files | Holds court cases; prepares the case file and notices | On a court register hit, or when a case file is due |
| **Auditor** | Internal audit or vigilance | `auditor` | The full log | Re-checks a random sample of closures | Monthly |
| **Citizen** | Resident or lake committee member | `citizen` | Their own reports only | Reports a change; gets status updates | Never; they receive updates on their own reports |

**Who decides.** The "officer" of section 6.5 is whoever holds the legal power for that land and action: in HYDRAA's area, its Commissioner or an officer he authorises; elsewhere the Collector or RDO under revenue law, or a municipal commissioner for building permissions. Counsel must confirm this (section 15).

### 17.3 Detecting each stage of encroachment

The five stages on the deck's "easiest to stop early" slide, and what imagery shows at each. The rules are those of section 8.4 and are the same whichever provider supplies the images; thresholds are tuned per sensor.

**Imagery tiers.**
- **Screen:** every asset, at least weekly, with multispectral optical images (3 to 10 m) and radar. Radar sees through monsoon cloud.
- **Confirm:** sub-metre images on priority cases only: commercial tasking at about 0.3 to 0.5 m, or ISRO Cartosat-3 (about 0.28 m panchromatic) through NRSC.
- **Verify:** the field team, CCTV and drones.

| Stage | What happens on the ground | What the images show | Rule (section 8.4) | Tier |
|---|---|---|---|---|
| Soil dumped | Earth or debris dumped at the edge of, or into, the water | Water or vegetation turns to bright bare soil: the water index falls and the bare-soil index rises; radar texture changes | Water to bare soil at the lake edge: `soil_fill`, stage `soil_dumped` | Screen |
| Land levelled | Plants cleared, ground flattened, plots pegged | A uniform bare patch where vegetation was; the pegs and plot lines need sub-metre images | Vegetation to bare soil: `clearing`, stage `land_levelled` | Screen, then confirm |
| Sheds and fences | Sheds, compound walls, fencing | Often smaller than one 10 m pixel, so medium-resolution images cannot see them reliably | Not claimed from medium resolution | Confirm or field |
| Building rises | Columns, slabs and walls go up | Radar return rises sharply as walls and ground form corner reflections; the interferometric coherence pattern changes; the built-up index rises | Bare soil or vegetation to built: `building`, stage `building_rises` | Screen; confirm the footprint |
| Family moves in | The building is occupied | Stable built-up surface; little new to detect | The dated bracket shows when it was built; change before the baseline is `CLOSED_LEGACY` (rule 3) | Record only |

Water loss alone never alerts (section 8.4). Every alert names the sensor that saw the change and the dates of both images.

### 17.4 What every alert carries: the survey-number file

| Block | Contents | Source in production | In the prototype |
|---|---|---|---|
| Identity | Alert code, asset, cohort, mode, priority and its factors, state, owner, due date | System | Built |
| Location | Coordinates; village, mandal, district, municipality and ward; nearest road; a map with the FTL, buffer and watch ring; a link to a maps app | System and boundary layers | Coordinates and map built; administrative units come from the asset record |
| Survey numbers | Every survey or sub-division number the change overlaps, with the area of overlap; the 14-digit Bhudhaar number where issued; land category (government, assigned, patta, inam, endowment, wakf, shikam); extent; a Record of Rights summary; recent mutations and pending applications | Bhu Bharati; SS&LR cadastral maps | Not built |
| Prohibitions | Section 22A entry and its clause, with a warning that the list marks whole survey numbers and may be wrong | Registration and Stamps | Not built |
| Boundary | Status and version, notification references, who certified it | LPC, Irrigation, HYDRAA Raksha | Built |
| Court and police | Cases on the survey numbers or the asset: court, case number, status, next hearing, interim orders or stays; FIRs | CCMS, eCourts, police | Court register built (CSV import); CCMS and eCourts links not built |
| Permits and works | Building permissions, layout approvals, authorised works | BuildNow and departments | Built (CSV import) |
| History | Earlier alerts, closures, actions and title claims | System | Built |
| Evidence | Before and after images, dated bracket, sensor, area, stage, confidence | System | Built |
| Signals | Linked citizen reports, CCTV alerts, Praja Vani complaints | System | Table only |
| People | Names of owners and claimants | Bhu Bharati and the field record | Only after field confirmation, to authorised roles (17.10) |

Every item shows its source and the date it was read. When two records disagree, both are shown side by side and neither is overwritten.

### 17.5 Who gets the alert, and the escalation matrix

**Routing.** An alert goes to the nodal officer of the body that holds the asset: HYDRAA inside its area, the District Collector's nodal officer elsewhere, and the owning agency for cohort E. Once the change is field-confirmed, the Tahsildar of the mandal and the Irrigation engineer of the division are added as verifiers.

Proposed deadlines, to agree with HYDRAA and the Revenue Department. They extend section 6.6 and stay configurable.

| Step | Goes to | Deadline | If missed, level 1 | Level 2 | Level 3 |
|---|---|---|---|---|---|
| Review the image pair | Analyst; a reviewer co-signs any closure | 3 days | Reviewer | Nodal officer | |
| Assign a field officer | Nodal officer | 1 working day | Additional Commissioner or Additional Collector | Commissioner or Collector | State dashboard |
| Check on site | Field officer | 7 days; 48 hours if the priority score is 80 or more, or soil is dumped inside the FTL of a cohort A or B asset; 14 days in the monsoon | Nodal officer | Additional Commissioner or Additional Collector | Commissioner or Collector |
| Confirm the survey number and FTL position | Tahsildar; Irrigation engineer | 7 days from field confirmation | RDO; Executive Engineer | Collector; Superintending Engineer | State dashboard |
| Prepare the case file | Legal officer with the nodal officer | 7 days | Head of the legal cell | Commissioner or Collector | State dashboard |
| Record the officer's decision | Deciding officer | 30 days | Commissioner or Collector | State dashboard | |

- **Level 4** is the State dashboard's overdue list, seen by the State overseer.
- **A court register hit** goes straight to the legal officer, with no field visit (invariant 1).
- **A linked citizen report** sends the reporter a status update at each step.
- **Channels:** in-app inbox, SMS, WhatsApp through a State-approved channel, and a daily email digest. Each notification needs an acknowledgement. If it is not acknowledged within 24 hours it is repeated and escalated.

### 17.6 Due diligence: four gates

| Gate | When | Checks |
|---|---|---|
| A. Before anyone moves (automatic) | When a candidate arrives | Section 6.2 (boundary version and status, baseline date, authorised works, permits, court register), plus land category and Section 22A, duplicates and earlier closures, and the seasonal and drought controls |
| B. Before the field visit | Analyst review | Two-image review; sharper images requested if needed; a field brief listing the survey numbers, access and the "observation, not a survey" note (section 9.2) |
| C. Before the officer decides | Case file | Geotagged photos on site; survey number and title status confirmed by Revenue; FTL position confirmed by Irrigation; joint survey held with prior notice; notice served and hearing held; no live court matter; evidence pack verified; checklist (section 6.7) recorded, with any gap logged |
| D. Before anything closes | Closure | Two different people; a reason code; a weekly re-check from space that reopens a closed alert if the change persists |

The April 2026 High Court order asked HYDRAA for written procedures and prior notice. These gates are such a procedure, enforced and logged by the software. Counsel must confirm the wording and the order of steps.

### 17.7 Central dashboard and drill-down

- **Levels:** State, then agency or district, then mandal, municipality or zone, then village or ward, then lake or parcel, then survey number, then alert.
- **At every level:** a map shaded by open and overdue alerts; the five monthly figures (section 9.4); the share of deadlines met; overdue alerts by officer; boundary coverage (the share of assets with a final or marked boundary); citizen reports received and closed; and the trend against last month.
- **Scope by role and area:** the State sees everything, a Commissioner or Collector sees their own area, and a Tahsildar sees their own mandal.
- **Every number opens the cases behind it.** Every view is logged, and there is no bulk export (section 10).
- **Monthly page:** the printable summary of the same view (section 9.4). Summary tiles can be fed to TGICCC if the State wants them on its video wall.

### 17.8 Citizen reporting by web portal and WhatsApp

**Channels.** A web portal (map pin, photo, short description) and a WhatsApp chatbot. The chatbot could use HYDRAA's existing WhatsApp number or the MeeSeva on WhatsApp platform the State launched in November 2025; the choice is for the State. Calls to the 1070 helpline and Praja Vani complaints are entered by staff into the same intake.

**Flow.**
1. The citizen sends a photo, a location (a pin or shared location) and a short description. A name and phone number are optional; a phone number is verified by one-time password if the citizen wants updates.
2. The citizen gets a reference number at once.
3. The system matches the location to an asset and survey number and merges duplicate reports.
4. The report becomes a signal (the `signals` table, section 7). It raises the priority of a matching alert, or opens a satellite re-check and a field check.
5. The citizen gets a status update at each step: received, checked, closed with a reason. They never see officer names, owner names or evidence.

**Rules.**
- A report never creates a finding on its own (section 5).
- The reporter's identity is protected and kept to a minimum, under the Digital Personal Data Protection Act, 2023.
- Accused persons are never shown publicly.
- Rate limits and the one-time password guard against abuse; repeated false reports are flagged.
- The channel works in English, Telugu and Urdu.
- A report about a place the system does not watch is passed to the right department.

### 17.9 Imagery sourcing (changed 7 November 2026)

At the owner's request the imagery source is no longer fixed as "free data first". The tiers in 17.3 stay. Each tier may use free (Copernicus Sentinel), ISRO (through NRSC) or commercial imagery, chosen per phase on cost, revisit and resolution. Section 8.1 remains the reference for the free sources the backtest uses. The cost figures in section 16 assume free screening, so they must be revised if commercial screening is chosen. The pitch deck no longer presents the solution as built on free data.

### 17.10 Owner-blind detection, refined (changed 7 November 2026)

The owner asked that ownership, disputes and court cases around a survey number be visible to officers. Applied:
- Every alert shows the land category, the type of record, the Section 22A entry, court cases, disputes and mutation activity, to the desk and officer roles.
- The personal names of owners and claimants appear only after field confirmation, only to the nodal, revenue and legal roles, and every view is logged.
- Detection and the priority score stay owner-blind.

Reason: if names were visible as soon as a change was detected, an alert could be used to target or extort the people named (section 10, vendor conduct).

### 17.11 What the prototype has, and what this section adds

| Feature | In the prototype (M0 to M9) | Added by this section |
|---|---|---|
| Legal check, priority, state machine, two-person closure, audit chain | Built | |
| Alert with boundary, legal check, images and dated bracket | Built | Survey-number file from Bhu Bharati, the Section 22A list and CCMS (17.4) |
| Timers and escalation (section 6.6) | Built | The full matrix, a verification step, a 48-hour urgent timer, and the notification channels (17.5) |
| Case-readiness checklist and evidence pack | Built | Revenue and Irrigation verification steps (17.6, gate C) |
| Monthly page | Built | Drill-down dashboard from State to survey number (17.7) |
| Field app, offline, in English and Telugu | Built | GPO as a field user outside HYDRAA's area |
| Citizen reporting | `signals` table only | Portal, WhatsApp intake and status updates (17.8) |
| Roles | Eight | `revenue_officer`, `irrigation_officer`, `citizen` (17.2) |

### 17.12 Sources for this section

- HYDRAA structure and staffing: [Telangana Today](https://telanganatoday.com/all-you-need-to-know-about-hydraa-organisation-function-and-responsibilities), [The News Minute](https://thenewsminute.com/telangana/hyderabad-hydra-to-get-four-additional-commissioners-among-169-officers), [Deccan Chronicle](https://www.deccanchronicle.com/amp/southern-states/telangana/hydraa-to-get-more-powers-and-staff-for-protecting-lakes-and-govt-properties-1819933), [Wikipedia](https://en.wikipedia.org/wiki/HYDRAA)
- HYDRAA police station: [Deccan Chronicle](https://deccanchronicle.com/southern-states/telangana/hydraa-gets-dedicated-police-station-1852599)
- HYDRAA helpline 1070 and WhatsApp reporting: [NewsMeter](https://newsmeter.in/hyderabad/hyderabad-can-now-dial-1070-to-report-encroachments-flood-related-emergencies-754408), [Siasat](https://www.siasat.com/hydraa-introduces-phone-number-to-report-lake-encroachments-3238098), [Deccan Chronicle](https://www.deccanchronicle.com/southern-states/telangana/hydraa-launches-toll-free-number-to-raise-complaints-1901231)
- Lake guards per lake: [Hyderabad News Hunt](https://hyderabadnewshunt.com/hyderabad-lakes-cctv-monitoring-185-water-bodies-hydraa)
- Lake Protection Committee: [HMDA](https://www.hmda.gov.in/lake-protection-committee/), [NGT filing OA 71 of 2023](https://www.greentribunal.gov.in/sites/default/files/news_updates/OA%20No.%2071%20of%202023%20Report%20of%20R-2.pdf), [Siasat on the chair](https://www.siasat.com/hyderabad-durgam-cheruvus-ftl-to-be-fixed-in-4-months-says-hydraa-commissioner-3162831/amp/)
- FTL procedure: [Deccan Chronicle on the High Court](https://deccanchronicle.com/southern-states/telangana/telangana-hc-directs-state-to-clarify-procedures-for-setting-lake-ftl-1824865), [NGT filing](https://www.greentribunal.gov.in/sites/default/files/news_updates/16321_2.pdf)
- High Court order of April 2026 on SOPs and notice: [Siasat, 14 April 2026](https://www.siasat.com/no-sops-no-demolitions-hc-restrains-hydraa-flags-lack-of-notice-and-due-process-3452589/)
- Revenue hierarchy: [CAG audit report](https://cag.gov.in/webroot/uploads/download_audit_report/2020/Chapter-VI-0605b2d7259e7d3.27393891.pdf), [revenue divisions](https://en.wikipedia.org/wiki/List_of_revenue_divisions_in_Telangana)
- Grama Palana Officers: [Deccan Chronicle](https://deccanchronicle.com/southern-states/telangana/telangana-govt-sanctions-creation-of-10954-village-level-officer-posts-1868381), [Telangana Today](https://telanganatoday.com/vros-vras-qualified-in-gpo-test-wait-for-appointment-orders)
- Bhu Bharati and Bhudhaar: [The News Minute](https://www.thenewsminute.com/telangana/how-is-bhu-bharati-telanganas-new-land-records-system-different-from-dharani), [The Week](https://www.theweek.in/news/india/2026/04/22/bhudhaar-card-can-telanganas-unique-id-get-rid-of-land-disputes-for-good.html)
- Section 22A list: [ThePrint](https://theprint.in/india/telanganas-section-22a-mess-how-thousands-of-acres-of-private-property-landed-up-in-prohibited-list/3018683/), [The South First](https://thesouthfirst.com/telangana/section-22a-row-intensifies-in-telangana-cm-revanth-assures-protection-of-property-owners-rights/)
- Court Case Monitoring System: [The Week](https://www.theweek.in/news/india/2026/02/10/telangana-rolls-out-court-case-monitoring-system-to-strengthen-coordination-between-govt-and-courts.html)
- MeeSeva on WhatsApp: [Deccan Chronicle](https://www.deccanchronicle.com/southern-states/telangana/meeseva-on-whatsapp-launched-1918037), [NewsMeter](https://newsmeter.in/nation/telangana-unveils-new-meeseva-expansion-offers-580-services-from-38-departments-via-whatsapp-758427)
- TGICCC: [Wikipedia](https://en.wikipedia.org/wiki/Telangana_Integrated_Command_and_Control_Centre), [Telangana Today](https://telanganatoday.com/monsoon-preparedness-meeting-held-at-tgiccc-in-hyderabad)
- Tanks in Telangana: [Mission Kakatiya](https://en.wikipedia.org/wiki/Mission_Kakatiya)
- Radar change detection for urban building change: Che and Gamba, 2020, Sentinel-1 amplitude and coherence time series ([summary](https://www.bohrium.com/paper-details/bi-and-three-dimensional-urban-change-detection-using-sentinel-1-sar-temporal-series/812671251611910146-2681)); false alarms of coherence change detection in dense urban areas ([Manzoni et al., 2020](https://doaj.org/article/efc4f458c7b749ab84427c192aa0d30b))
- High-resolution imagery: [PlanetScope and SkySat (NASA Earthdata)](https://www.earthdata.nasa.gov/about/csda/vendor-planet?page=9), [Cartosat-3 (NRSC brochure)](https://www.nrsc.gov.in/sites/default/files/pdf/training/C3_BROCHURE_JAN2021_modified.pdf)
