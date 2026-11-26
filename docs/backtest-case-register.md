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
