# Initial asset load: building the boundary register

Proposal, 24 November 2026. Written in answer to the owner's plan:

> First map each government lake's boundaries (core, FTL and buffer zone) from Bhu Bharati, CCLA and revenue records (cadastral or survey-number maps). Once the boundaries are loaded and clear, use them as the system of record. Then compare satellite images weekly against a baseline date (not yet final) and alert officials.

This document covers:

1. what the register holds for each lake;
2. how private land-record apps get survey-number maps, and which part of their method we copy;
3. the load pipeline;
4. the baseline date;
5. what the weekly comparison does;
6. phases and effort;
7. the data request to send the government;
8. risks.

It builds on the design that already exists, so nothing here replaces it:

- cohorts and modes: CONTEXT.md §6.1;
- append-only boundary versions: §7 and D-011;
- boundary sources: §8.2;
- the survey-number file: §17.4.

Facts from web sources are marked with a link. Estimates are marked as estimates.

## 1. What the register holds for each lake

One lake, four nested zones, and the survey-number parcels that cross them.

| Layer | What it is | Authoritative source | Fallback until official files arrive (status `derived`, watch only) |
|---|---|---|---|
| **Lake record** | Lake ID; names in English and Telugu; district, mandal and village; custodian; cohort; baseline date | HMDA Lake Protection Committee (LPC) lake list; Irrigation tank ID from the minor irrigation census; HYDRAA's list | OpenStreetMap name and outline (today's 99 lakes) |
| **Core (lake bed)** | Survey numbers recorded as the tank itself (cheruvu, kunta) or as government shikam land. Title is clearest here | Village cadastral map, joined to the land category in the Sethwar, the 1954-55 Khasra Pahani and the current Record of Rights (Bhu Bharati) | Water seen in most clear looks over many years (JRC occurrence) |
| **FTL** | The full tank level line, as surveyed by Irrigation and notified by the LPC. It can include private (patta) land that floods when the tank is full: that land stays private, but nothing may be built on it | LPC final notification (preliminary if that is all there is), with Irrigation's FTL survey sheets | Contour at the surplus-weir crest level on an elevation model, or the largest water extent in wet years. HYDRAA itself is reported to [use satellite images against rainfall records from 1973 to 2024](https://newsmeter.in/regional/telangana/hydraa-to-use-satellite-imagery-to-conserve-govt-lands-determine-lake-ftls-741168) |
| **Buffer** | 30 m from the FTL for lakes of 10 ha or more; 9 m for smaller lakes, kuntas and shikam land (G.O. Ms. No. 168 of 2012, CONTEXT.md §4) | **Computed** from the FTL, never traced by hand. It is stored as a derived row pointing to its FTL row (D-010) | Computed from the derived FTL |
| **Watch ring** | 100 m beyond the buffer, for early warning | Computed | Computed |
| **Survey-number parcels** | Each parcel that touches any zone: polygon, survey and sub-division number, land category, extent and Bhudhaar number. **No owner names** (§17.10) | Survey, Settlement and Land Records (SS&LR) village maps through CCLA and Bhu Bharati | None. Parcels are never invented |

The layers map onto the alert classes that already exist:

- a change in the core is on government land (`GOVT_LAND`);
- a change on patta land inside the FTL or buffer is restricted but private (`RESTRICTED_PRIVATE`);
- a change on a parcel with a live court case is `DISPUTED`.

That is why the register needs the land category of each survey number, not just a line on a map.

## 2. How private apps get survey-number maps

**What they say they do.**

- **Landeed** sells Telangana village maps, survey sketches and record searches. For village maps it says it [sources the map from the District Survey and Land Records office through the Bhu Bharati and Dharani back end](https://web.landeed.com/products/telangana/certified-village-map). It also [offers a look-up from an address or landmark to a survey number](https://web.landeed.com/products/telangana/find-my-survey).
- **Telangana LandGrid** is an [independent app by Tech Avenue Labs](https://yourstory.com/companies/telangana-landgrid), not affiliated with the Government of Telangana. It shows survey numbers and boundaries on satellite maps for villages across the State.
- **1acre** shows a similar [survey-number layer for Telangana](https://1acre.in/map-layers/telangana/survey-numbers-telangana).

None of them publishes its method. Each warns, directly or in its guides, that its maps do not prove ownership.

**The likely method.** This is our inference from what they offer, not their disclosure:

1. **Gather village maps.** Sources are portal map views, certified copies from the Tahsildar or MeeSeva, and scans of old village maps (Tippon, Sethwar).
2. **Pin each scanned sheet onto satellite images.** Each sheet is georeferenced using points that can be seen on both, such as tank bunds, road junctions, temples and wells. The plot lines are then traced.
3. **Key each plot** by district, mandal, village and survey number. Join the public Record of Rights (pahani) to each plot by that key.
4. **Answer look-ups.** "Which survey number is this point in?" is a point-in-polygon query. Certified copies are fetched by people, which is why Landeed quotes weeks for some products.

**The State already holds the base layer.** The State's own records suggest most of this work is done:

- A State document reports about [10,480 of 10,890 village maps digitised and georeferenced](https://cdnbbsr.s3waas.gov.in/s3d69116f8b0140cdeb1f99a4d5096ffe4/uploads/2024/10/20241004416936919.pdf). Its date and scope are unclear, so treat this as unverified until SS&LR confirms it.
- [413 villages have no village map or Sethwar](https://www.siasat.com/survey-to-be-conducted-in-413-telangana-villages-without-naksha-3224058/), and are being surveyed afresh.
- A [first-phase re-survey of 2,240 villages](https://www.siasat.com/telangana-to-launch-statewide-land-re-survey-in-2240-villages-3492416/) (70 in each of 32 districts, excluding Hyderabad) uses DGPS and QGIS and uploads to Bhu Bharati.
- Every survey number is to get a [Bhudhaar number](https://www.deccanchronicle.com/amp/southern-states/telangana/tg-govt-to-launch-distribution-of-bhudhar-cards-after-dasara-ponguleti-1996766). Revenue, survey and registration data are being [combined into one record built with NIC](https://www.thehansindia.com/telangana/in-a-first-tg-to-roll-land-survey-and-reg-info-into-a-single-page-minister-1028377).
- HYDRAA has an agreement with NRSC to [combine toposheets, cadastral maps, revenue records, Survey of India tank surveys from the 1970s and NRSC images](https://newsmeter.in/hyderabad/hydraa-national-remote-sensing-centre-team-up-to-digitise-land-records-around-orr-for-transparency-746748) around the ORR.

**What we copy, and what we do not.**

| | Private apps | GeoGuard |
|---|---|---|
| Pipeline | Gather, georeference, key by survey number, join records, point-in-polygon | **Same pipeline** |
| Source | Portal views, certified copies, old scans | **The State's own files**, under a data-sharing order, because the State is our client |
| Who signs it | Nobody: no certificate | Irrigation signs the FTL; the Tahsildar and Mandal Surveyor sign the survey numbers |
| Owner names | Shown to buyers | Withheld until field confirmation, then shown only to named roles (§17.10) |
| Use in court | None | Certified, versioned and hashed, so it can go in the evidence pack |

**Do not scrape portals and do not buy app data.** Bulk scraping of Bhu Bharati may breach its terms and would undermine a vendor working for the State. Buying an app's maps gives a boundary that no court will accept. App maps may be used only as a cross-check, and only with a licence.

## 3. The load pipeline

Each lake goes through eight steps once. After that it changes only by new versions.

| # | Step | What happens | Output | Built today? |
|---|---|---|---|---|
| 1 | **List the lakes** | Merge the LPC list, the Irrigation tank IDs and HYDRAA's list into one lake ID, keeping a crosswalk to each department's ID | `assets` rows, one per lake | **Template (M11)**: department IDs kept per asset; match by ID, cited ID or overlap |
| 2 | **Collect the files** | Request the official files (section 7). Record each file's source, date and SHA-256 when it arrives | Source library | **Template (M11)**: snapshots hashed and stored; file drop and samples; API needs an agreement |
| 3 | **Georeference scans** | Only for files that arrive as scans or PDFs. Use QGIS, the State's own tool, with at least 8 control points spread over the sheet. Record the RMS error in metres; reject a sheet above the agreed limit | Georeferenced sheet and its error | Done in QGIS before the drop; the engine stores the error and refuses over 25 m |
| 4 | **Trace and check** | Trace the FTL line and the survey-number polygons. Snap shared edges and check for gaps and overlaps. Compare each traced area with the extent in the records, and flag a difference over 10% | FTL and parcel polygons | **Template (M11)**: validity, location, error and the 10% extent check; no gap or overlap check yet |
| 5 | **Join the records** | Join by survey number: land category, extent, Bhudhaar number, any Section 22A entry and court cases. No owner names | Survey-number file (§17.4) | **Template (M11)**: land category, extent and Bhudhaar per parcel; no 22A or court join yet |
| 6 | **Reconcile** | Compare the notified FTL with the cadastral lake bed, the largest historical water extent and the OSM outline. Measure overlap and the largest offset; differences go to the boundary desk | Agreement report per lake | **Template (M11)**: never downgraded; same-status disagreement reported as a conflict, with overlap and offset |
| 7 | **Certify** | The analyst prepares it and a second person checks it (maker and checker). The Irrigation engineer certifies the FTL; the Tahsildar and Mandal Surveyor certify the survey numbers. The nodal officer publishes | `certified_by`, `boundary_status` | Fields exist; workflow not built |
| 8 | **Publish** | Insert a new boundary version: append-only, hashed, never overwritten. Compute the buffer and ring. The cohort follows from the status (`cohort_by_boundary_status`), and any open alert is checked again (D-021). Freeze the reference image (section 4) | Lake is ready to watch | **Yes**, apart from the reference image |

**Keep in sync.** Each month, pull:

- new LPC notifications;
- mutations and new Bhudhaar numbers in the lake's villages;
- re-surveyed villages;
- court cases.

Any change becomes a new version. When two sources disagree, both are shown and neither is overwritten (§17.4).

**Proposed rule: an edge band.** This is new and not built.

- **Why.** A 9 m buffer is narrower than one 10 m Sentinel-2 pixel. Old village maps can be off by more than that after georeferencing.
- **Rule.** Store each boundary's positional accuracy in metres. A candidate that touches a zone only within *accuracy + 10 m* of the zone's line gets the flag `near_edge`. It then needs a sharper image or a joint survey before anyone acts on it.

**Effort.** These are estimates, to be measured in the demonstration:

- about 2 to 4 hours for a lake whose files arrive as scans (steps 3 to 6);
- under an hour for a lake whose vectors arrive clean;
- 20 lakes from scans, the demonstration: about one to two person-weeks;
- 100 lakes, the pilot: one GIS analyst and one reviewer for about two months, unless vectors arrive.

## 4. The baseline date: three dates, each with one job

| Date | Job | Recommendation |
|---|---|---|
| **Policy cut-off** | Decides what counts as new. Change first seen on or before it is recorded but never alerted (rule 3, `CLOSED_LEGACY`) | **19 July 2024**, the prototype's current value (D-039). It matches HYDRAA's public position that it acts on structures built after July 2024 and will not demolish occupied homes (CONTEXT.md §4). One State-wide date is simplest to defend. Allow a per-lake override only with a logged reason, for example a later final notification. **HYDRAA and counsel must confirm it in writing**, which is why it is still open |
| **Reference image** | Frozen proof of what stood there at the cut-off | New. Per lake: a cloud-free Sentinel-2 composite from the 2024 dry season (February to May; July is monsoon), a Sentinel-1 radar composite around the cut-off, and, for priority lakes, an archived sub-metre image near the cut-off. Hash each one and attach it to every alert |
| **Historical record** | Rebuilds lost boundaries and tells the story of loss | 1954-55 Khasra Pahani and Sethwar entries; 1970s Survey of India toposheets and tank surveys; NRSC images from 1975. Used to draw and defend boundaries, **never to raise an alert** |

The Telangana High Court treats the 1954-55 Khasra Pahani as a basic record of rights, and the Sethwar as a basic settlement record. Two judgments found in a search say so ([2025](https://www.latestlaws.com/judgements/telangana-high-court/2025/march/2025-latest-caselaw-2855-tel) and [2025](https://www.latestlaws.com/judgements/telangana-high-court/2025/april/2025-latest-caselaw-5119-tel)); counsel should read them in full. This is why the core layer starts from those records.

## 5. What runs every week

Most of this already runs on the 99 real lakes:

1. **New looks arrive** for every lake: Sentinel-2 optical, and Sentinel-1 radar through cloud. *Built.*
2. **Each pixel is compared with the year before.** The old state must have been established, and the new state must be new: D-042 and D-050. This dates the change with a bracket: last clear look, first changed look. *Built.*
3. **The change is placed in a zone** (core, FTL, buffer, ring or outside) of the boundary version in force that day (D-016). *Built.*
4. **New: compare with the frozen reference image.** This catches slow change that builds up over many weeks and never looks new from one week to the next. It also gives the officer a "not there on the cut-off date" picture.
5. **The legal check runs.** It checks the cut-off, permits, authorised works, the court register and the cohort mode. Only then is anyone alerted. *Built.*

Water loss alone never alerts, because season and drought shrink lakes too.

## 6. Phases

| Phase | Lakes | Boundary source | Boundary status reached |
|---|---|---|---|
| Prototype (now) | 99 | OpenStreetMap | `derived`: watch only |
| Demonstration, January to March 2027 | About 20 recovered assets | HYDRAA's files for land already recovered; scans georeferenced by us; certification tried for real | `physically_marked` or `final_notification`: full officer path |
| Paid pilot, April to September 2027 | 100 lakes and 10 parcels | Official vectors under a data-sharing order; boundary desk staffed | Mostly B; C and D stay at verify or watch |
| Core urban region, from October 2027 | All HMDA lakes, final notices first | Same, at scale | B first |
| Statewide, later | About 46,531 tanks (2014 census) | Irrigation inventory and re-surveyed villages as they reach Bhu Bharati | Grows with the State's own survey |

**A by-product for the State.** 2,577 of HMDA's 3,342 lakes have no final FTL notice (765 do).

- For each of them, the register holds:
  - a derived outline;
  - its historical water extents;
  - the survey numbers it touches;
  - its reconciliation report.
- Together that is a ready-made starting file for the LPC's notification work.
- **Frame this as support, not as a promise to notify lakes.** Notification remains the LPC's job.

## 7. The data request to send through HYDRAA

| From | Data | Format asked for |
|---|---|---|
| HMDA LPC and HYDRAA | Lake list with IDs. Final and preliminary FTL notifications with their maps. FTL and buffer layers from HYDRAA-Raksha | GeoPackage or shapefile; notification PDFs |
| Irrigation and CAD | FTL survey sheets. Tank memoirs with FTL and weir crest levels. Minor irrigation census tank IDs | CAD or GIS files; scans if nothing else exists |
| CCLA and SS&LR (Bhu Bharati, NIC) | Village cadastral vectors for every village a lake touches. A Record of Rights extract: survey and sub-division number, land category, extent, Bhudhaar number, **no names**. Sethwar and Khasra Pahani entries for those survey numbers | GeoPackage or shapefile with a data dictionary; CSV; scans |
| Registration and Stamps | Section 22A entries for those villages | CSV |
| NRSC and TGRAC (through HYDRAA's agreement) | Historical images, elevation models, the high-water analysis from 1973 to 2024, the 1970s tank surveys | GeoTIFF; GIS files |
| Municipal bodies and HMDA | Building permissions and authorised works in the FTL, buffer and ring | CSV with coordinates |
| Courts (CCMS) | Cases on those survey numbers and lakes | CSV |

Terms to offer:

- the data is used only for the State's lake watch;
- it is stored in India;
- owner names are withheld until field confirmation;
- every view is logged;
- all copies are deleted or returned at contract end.

## 8. Risks

| Risk | Answer |
|---|---|
| The FTL notice, village map and ground disagree | Keep both versions and never overwrite either. The boundary desk escalates; the alert waits at `AWAITING_BOUNDARY` (§6.5) |
| Old maps are misaligned | Store positional accuracy and apply the edge band (section 3). Sub-metre images or a joint survey decide near the line |
| Files are slow to arrive | Derived outlines keep the watch running in watch-only mode. The stop condition stands: no official boundary access by March 2027 means we stop |
| Personal data | No owner names in the register. The Digital Personal Data Protection Act 2023 applies to any that arrive later |
| A boundary is challenged in court | Every version carries its source, date, certifier and hash, and the alert names the version it used (§6.2) |
