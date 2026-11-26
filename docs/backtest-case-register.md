# M3 blind-backtest case register

`data/cases.template.geojson` is intentionally empty. The PRD starter list in CONTEXT.md section 13 and `data/case_lake_search.yml` are discovery hints, not verified ground truth. Do not convert a name match or a press headline into a verified event polygon.

## One GeoJSON Feature per event

Use a Polygon or MultiPolygon in EPSG:4326. The geometry must represent the affected event footprint, not the entire lake outline.

Required `properties`:

| Field | Meaning |
|---|---|
| `case_id` | Stable, unique event identifier |
| `event_type` | Observed event class (for example soil_fill, clearing, levelling, building) |
| `event_date` | Exact first-change/event date, YYYY-MM-DD |
| `event_date_precision` | Must be `exact` for primary scoring; broader windows are excluded |
| `public_action_date` | First public action date, YYYY-MM-DD; use explicit null if unknown (then excluded from the primary before-action score) |
| `area_acres` | Independently sourced affected area; do not calculate from degree-based GeoJSON geometry |
| `area_source` | How the area was independently established |
| `source_url` | Public source URL supporting the event |
| `source_title` | Source title/publication |
| `geometry_source` | Provenance of the event footprint (for example dated imagery/manual tracing) |
| `geometry_status` | Must be `verified` for primary scoring; approximate/unverified cases are excluded |
| `geometry_crs` | Must be `EPSG:4326` |

Do not add owner names, claimant names, phone numbers, Aadhaar or other personal identifiers.

## Eligibility rules

A case can enter the primary Gate 1 denominator only if all of the following are true:

- event date is on/after 1 January 2018;
- event date is exact;
- public-action date is known and not before the event date;
- independently sourced affected area is strictly greater than 0.25 acre;
- event footprint is a valid, verified Polygon/MultiPolygon;
- source and geometry provenance are recorded.

Cases that do not meet the rules remain in the register with an explicit exclusion reason. A missing action date is not treated as if the event had no public action. A broad date range is not silently converted into an exact date.

## Validate

From the pipeline package environment:

```bash
lp-geo validate-cases data/cases.template.geojson --output reports/m3/case-validation.json
```

A structurally invalid manifest exits non-zero. A valid manifest may still have zero eligible cases; the report must show the actual denominator. This validator does not independently verify the cited source — a human evidence review is still required.

## Blind-test integrity

- Freeze the detection rule file and record the commit/tag before scoring.
- Keep tuning lakes out of the scored set.
- Disclose that Durgam Cheruvu was viewed once before tuning (DECISIONS.md D-042).
- Run the scored set once per frozen rule version.
- No imagery acquired after a replay's `as_of` date may enter that replay.
- High-resolution imagery may be used for manual false-flag inspection only, never as a pipeline input or evidence-pack input.


## Discovery register and evidence lanes

The research inventory is `data/case-register.csv`. It currently contains 27 named leads, not 27 verified cases. Each row separates the date anchor in a press report from the actual event date and public-action date. `source_review_status` means the cited article was located; it does not mean the facts, boundary or event footprint have been independently verified.

The `case_role` and `primary_score_status` columns separate these lanes:

- `encroachment_candidate`: a lead that may become primary ground truth after event date, action date, exact location and affected footprint are independently established.
- `exposed_candidate_disclose`: Durgam Cheruvu. D-042 records one pre-tuning smoke test; do not describe it as a fully blind case.
- `historical_trend`: government-reported 2014–2023 change ranges. These can be used for a separate detection-only comparison, not for lead-time scoring.
- `authorized_restoration_control`: known or reported restoration activity. Use to test authorised-work suppression and change-type handling, not as an encroachment-positive case.
- `boundary_uncertainty_control`: Bhagirathamma and Tautanikunta. Keep out of positive ground truth and use to test the legal/boundary hold path.
- `identity_unresolved`: do not trace or score until the exact waterbody is identified.

### Source review notes

- The SANDRP Hyderabad lakes review contains case-specific narratives for Nalla Cheruvu, Durgam Cheruvu, Bum-Rukn-ud-Daula, Bathukamma Kunta, Komati Kunta, Suram Cheruvu, Kothakunta and Mella Cheruvu. It reports enforcement/restoration dates in several cases, but these are not necessarily the date the underlying land change began.
- The NewsMeter reference is retained as a discovery lead for Sunnam Cheruvu, Mallampet Cheruvu and Dundigal Kotwa; the article and exact waterbody identities still need independent review.
- The NewsMinute report summarises a Telangana government study of tank encroachment from 2014–2023. Its date range is too broad for lead-time scoring; obtain the underlying government report and spatial annexures.
- The Deccan Chronicle report on Mushkin Cheruvu distinguishes the 52.2-acre FTL area fenced from the 34.21-acre alleged attempted encroachment. Do not use the fenced FTL area as the event footprint.
- The Ramanthapur lead is based on a secondary report and requires confirmation from HYDRAA or municipal records before use.

### Evidence hierarchy

1. Dated official action records, court orders and certified departmental maps.
2. Official historical imagery or imagery provider scene metadata, with licence and acquisition timestamps.
3. Independently traced event footprints with reviewer, method, CRS and source record.
4. Reputable reporting as a discovery pointer only.
5. OSM name matches as identity hints only; never as proof of lake identity or legal boundary.

Ask HYDRAA/TGRAC for the original 171-tank study, its spatial annexures, the fuller list of 30 candidate events, and dated enforcement/restoration records. Do not manufacture the missing cases to fill the target of 30.
