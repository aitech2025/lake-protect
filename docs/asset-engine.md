# Asset creation engine (M11)

Built 24 November 2026. It turns government records into assets and boundary versions, following the plan in `docs/asset-load.md`.

No data-sharing agreement exists yet, so this is a **template implementation**:
- every connector, rule and table is real;
- no government system is called;
- files arrive from an officer's drop folder or from fictional samples;
- the API transport refuses to run until an agreement is recorded.

## 1. The design compared with the code

| Design element (`asset-load.md`) | Before M11 | M11 adds | Still to build |
|---|---|---|---|
| **1. Lake list and department IDs** | 99 OpenStreetMap lakes, no department IDs | `asset_source_links`: each asset keeps the ID every source uses for it. Records match by their own ID, by another department's ID they cite, or by outline overlap | A tool for the boundary desk to merge or unlink assets |
| **2. Collect the files** | One GeoJSON file from OpenStreetMap | Four template connectors, each with a data contract. File drop and samples work; the official-API transport is a template | Real field names once agreements fix them; GeoPackage and shapefile reading |
| **3. Georeference scans** | None | Not done in the app: scans are georeferenced in QGIS before the drop. Each outline's positional error is stored, and outlines worse than 25 m are refused | A georeferencing checklist for the boundary desk |
| **4. Trace and check** | Geometry validity only | Validity, location (Telangana for real data, open sea for samples), positional error, and drawn area against recorded extent for parcels | Gap and overlap checks between neighbouring parcels |
| **5. Join the records** | Court register by CSV | Record of Rights joined to village parcels by survey number. Land category mapped from the recorded classification. Personal fields removed on arrival | Section 22A list; CCMS court cases |
| **6. Reconcile** | None | A boundary is never replaced by a weaker one. When two sources give the same status but different outlines, the current one is kept and a conflict is reported. Overlap, largest offset and area change are measured | A boundary-desk screen to resolve conflicts |
| **7. Certify** | `certified_by` field | Certification is carried from the source. A notified boundary must cite its notification reference and date, and a recovered parcel its order | Sign-off by Irrigation and Revenue, which needs the `revenue_officer` and `irrigation_officer` roles |
| **8. Publish** | Append-only versions; the cohort follows the status | The same, plus every boundary row records the file it came from and its positional error | Frozen reference image per asset |
| **Keep in sync** | Manual | Re-running the same files changes nothing; changed files add versions | Scheduled pulls once an API exists |
| **Core (lake bed)** | None | Tank and shikam parcels inside the boundary, with the lake-bed area, on the asset's register | A `core` boundary kind, used by the legal check for the government-land class |
| **Edge band** | None | Positional error stored on every boundary | The `near_edge` flag in the legal check |
| **Survey-number file** (CONTEXT.md 17.4) | Not built | For each asset: the survey numbers it touches, their Bhudhaar numbers, land category, extent and zone | Mutations, Section 22A entries and court cases by survey number |
| **No owner names** (17.10) | Detection is owner-blind | Personal columns are removed before a file is stored, and the parcels table has no column for a name | |

## 2. How a run works

```
transport ──► files ──► privacy filter ──► snapshot (hash, stored) ──► connector reads records
                                                                             │
   publish ◄── reconcile ◄── match to an asset ◄── validate ◄─────────────────┘
      │
      └─► new asset or new boundary version (append-only), links, parcels, survey numbers, run record, audit log
```

| Part | File |
|---|---|
| Types, data contracts, reading helpers | `api/app/sources/base.py` |
| The four connectors | `api/app/sources/connectors.py` |
| File drop, samples and the official-API template | `api/app/sources/transports.py` |
| Removing personal fields | `api/app/sources/privacy.py` |
| The engine | `api/app/sources/engine.py` |
| Settings: limits, areas, API blocks | `api/app/sources/sources.yaml` |
| Fictional samples and their generator | `api/app/sources/samples/` |
| Tables: snapshots, runs, links, parcels | `api/migrations/versions/0005_source_engine.py` |
| API | `api/app/routers/sources.py` |
| Desk page | `web/src/desk/Sources.tsx`; the register panel on `web/src/desk/Assets.tsx` |
| Command line | `python -m app.sources` |

**Status rules.**
- The Lake Protection Committee's notification is the only thing that gives a lake boundary a notified status.
- An Irrigation outline loads as `derived` (watch only).
- A HYDRAA recovered parcel is `physically_marked`, but only with its order reference and marking date.

**Never mixed.**
- Sample IDs are stored as `sample:<id>`, so a fictional record can never claim a real asset.
- Sample assets are demo assets: `is_demo`, with asset keys that start `sample-`.

**Dry run first.** A run is a preview unless it is applied. The preview runs every step inside a savepoint and rolls it back, so it shows exactly what loading would do.

## 3. Data contracts

Dates are `YYYY-MM-DD`. Geometry is WGS 84 Polygon or MultiPolygon. Lists inside a CSV cell are separated by `;`. `certified_by` names an office, never a person.

| Source | File | Required fields | Optional fields |
|---|---|---|---|
| HMDA Lake Protection Committee | `lakes.csv` | lake_id, lake_name, district, mandal, village, survey_numbers, area_ha, notification_status (final, preliminary or none) | lake_name_te, notification_ref, notification_date, notification_url, certified_by, positional_accuracy_m |
| | `ftl.geojson` | lake_id | positional_accuracy_m, method |
| Irrigation and CAD | `tanks.csv` | tank_id, tank_name, district, mandal, village | tank_name_te, hmda_lake_id, survey_numbers, ftl_level_m, weir_crest_m, surveyed_by |
| | `tank_outlines.geojson` (optional file) | tank_id | method, positional_accuracy_m, survey_date |
| CCLA, Survey Settlement and Land Records (Bhu Bharati) | `village_parcels.geojson` | district, mandal, village, survey_no | sub_division, positional_accuracy_m |
| | `ror_extract.csv` | district, mandal, village, survey_no, land_classification, extent_acres | sub_division, bhudhaar |
| HYDRAA | `ftl_layer.geojson` (optional file) | hmda_lake_id, lake_name, status | lake_ref, notification_ref, notification_date, positional_accuracy_m |
| | `recovered_parcels.geojson` (optional file) | parcel_ref, name, district, mandal, village, marked_on, order_ref | name_te, survey_numbers, recovered_on, positional_accuracy_m |

Each drop folder also needs a `manifest.yml`:

```yaml
source_date: 2026-12-01            # the date the department's data is as of
reference: "HMDA letter no. ..."   # the covering letter
agreement_ref: null                # once a data-sharing agreement exists
```

**Recorded classifications and the land category each maps to.**

| Recorded as | Land category |
|---|---|
| Sarkari, Government, Poramboke | government |
| Kunta, Cheruvu, Tank | tank |
| Shikam | shikam |
| Patta | patta |
| Assigned, Lavani patta | assigned |
| Inam | inam |
| Endowment, Devadaya | endowment |
| Wakf | wakf |
| Forest | forest |

Anything else loads as `unknown`, with a warning. Survey numbers are unique only within a village, which the register keeps in mind.

## 4. Running it

```bash
docker compose exec api python -m app.sources list                                    # the data contracts
docker compose exec api python -m app.sources run hmda_lpc --transport sample --items  # dry run, every record
docker compose exec api python -m app.sources samples --apply                          # all four samples, in order
docker compose cp ./my-drop/. api:/var/lp/storage/source-drops/hmda_lpc/               # an officer's files
docker compose exec api python -m app.sources run hmda_lpc --transport file_drop        # preview the drop
```

**API endpoints:**
- `GET /sources`;
- `POST /sources/{name}/runs` with `{"transport": "sample" | "file_drop" | "api", "dry_run": true}` (admin or nodal officer only);
- `GET /sources/runs`;
- `GET /assets/{id}/register`.

**On the desk:**
- The **Sources** page previews and loads each source. Admins and nodal officers can run loads; analysts, auditors and senior officers can view.
- On the **Assets** page, selecting an asset shows where its record came from and the survey numbers it touches.

The samples are not loaded into the development database. They sit about 15 km from the demo world, so loading them would widen the demo map. Load them when wanted with `samples --apply`; a demo reset removes them.

**What the samples show, in order (HMDA, Irrigation, HYDRAA, Bhu Bharati):**
1. Three lakes are created in cohorts B, C and D.
2. One lake is refused because it has no notification reference, and one waits because it has no outline.
3. An Irrigation outline does not replace a notified one.
4. A new Irrigation tank is created.
5. A tank that overlaps a lake but draws it differently is reported as a conflict.
6. An outline with 40 m error is refused.
7. HYDRAA's final notification moves lake B from cohort C to B as a new version.
8. A recovered parcel is created in cohort A.
9. 180 parcels load with the owner name and phone columns removed. Two extent mismatches and one unrecognised classification are reported, and the lakes' survey numbers are filled.

## 5. Switching on a real source

1. When the agreement is signed, set `agreement_ref`, `base_url` and `paths` in `sources.yaml`, and put the credential in `.env` under the named variable (for example `LP_SRC_HMDA_LPC_TOKEN`).
2. If the department's field names differ from the contract, change only that connector's mapping, and add a test with a small fixture.
3. Preview, read the conflicts and refusals with the boundary desk, then apply.

The API transport accepts only CSV and GeoJSON. It stops on an HTML page, because Lake Protect does not read portal pages.

## 6. Tests

- **API:** `api/tests/test_sources.py`, 16 tests. Together with the earlier suites, 284 API tests pass.
- **Browser:** `e2e/tests/m11-sources.spec.ts`, 2 tests. It uses previews only, so it runs without a database reset.
