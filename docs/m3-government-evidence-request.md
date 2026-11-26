# M3 government evidence request checklist

## Purpose

Request source material needed to build an independently reviewable historical ground-truth set for GeoGuard's M3 backtest. The current 27-row register is a discovery inventory only. It is not a list of verified encroachments and must not be circulated as such.

## Requested from TGRAC

1. The original government study/report that identified 171 encroached natural water tanks.
2. The full machine-readable tank list and all spatial annexures used in that study.
3. The exact comparison dates and definitions behind the reported 2014, 2023 and 2024 encroachment figures.
4. Original map layers or georeferenced maps for the before/after periods, including CRS, scale, source and preparation date.
5. Any official change polygons, affected-area calculations and methodology notes.
6. A separate list of at least 30 post-2017 historical change events with exact event dates, if available.
7. Five or more suitable tuning lakes that are not in the final scored case set.

## Requested from HYDRAA

For each relevant enforcement, restoration or protection action:

- Case/reference number and waterbody/asset identifier.
- Village, mandal, district and official lake/tank name.
- Date the physical change was first observed, if known.
- Date of first official complaint or inspection.
- Date of first public/official action, notice or enforcement.
- Date and footprint of demolition, soil removal, fencing or restoration work.
- Affected event footprint polygon, or source map from which it can be independently traced.
- Area measurement and its method; distinguish event footprint from total FTL extent and total area fenced.
- Original dated photographs and metadata, where releasable.
- Whether the work was authorised restoration, maintenance, a permitted project, or alleged unauthorised change.
- Current case status and whether any court order, stay or boundary dispute affects interpretation.

## Requested from HMDA, Irrigation and Revenue departments

- Official asset identifiers and aliases for each waterbody.
- FTL and buffer boundary versions, source records, survey date and CRS.
- Final notification status and notification reference/date.
- Village and survey-level boundary references, where legally shareable.
- Boundary dispute, overlap or pending litigation status.
- Any superseded boundary versions; do not overwrite history.

## Minimum case evidence contract

A case is a primary M3 candidate only when the evidence package can establish:

| Field | Required evidence |
|---|---|
| Asset identity | Unambiguous official waterbody/asset ID and location |
| Event date | Exact date the physical change first occurred or can be bounded to a single observation interval under the agreed protocol |
| Public-action date | Exact first public/official action date; must not be confused with event date |
| Event type | Soil fill, levelling, clearing, building or another defined change class |
| Event geometry | Polygon/MultiPolygon of the affected change footprint, not the whole lake or FTL |
| Area | Independently supported affected area, strictly greater than 0.25 acre |
| Provenance | Source record, source custodian, acquisition date, method, CRS and reviewer |
| Legal context | Boundary status, authorised-work status and court/permit flags |

The backtest protocol currently requires an exact event date for primary lead-time scoring. If an agency can only provide a date interval, retain the case in a separate detection-only lane until the scoring protocol explicitly defines interval handling. Do not invent a midpoint.

## Evidence handling and safeguards

- Request only records the department is authorised to share.
- Do not request or store landowner names, phone numbers, Aadhaar, PAN or other personal identifiers in the model-training or scoring case manifest.
- Keep identity and boundary uncertainty explicit. Do not infer illegality from imagery or a press report.
- Keep court matters and disputed boundaries out of positive encroachment ground truth; use them as workflow-control cases.
- Preserve original files read-only and record SHA-256, source, receipt date and custodian in the evidence log.
- Do not place restricted government maps, personal data or high-resolution imagery in the public Git repository. Store references and hashes; keep the source files in an approved controlled store.
- Separate the scored set from at least five tuning lakes. Disclose the Durgam Cheruvu pre-tuning smoke-test exposure recorded in D-042.

## Suggested response format

A department may provide GeoPackage, Shapefile, GeoJSON, CSV plus georeferenced map, PDF order/inspection record, or original imagery metadata. For every spatial file, include CRS and the date/version to which the geometry applies.

A case may remain in the inventory when some fields are unavailable, but it must not be promoted to the primary scored manifest until the full evidence contract is satisfied.
