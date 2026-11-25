# Progress

Read this first at the start of every session, then continue from the first unfinished milestone.

**Build order (owner's instruction, see DECISIONS.md D-001):** M0, M1, M4, M5, M6, M7, M8, M9,
**stop and report**, M2, M3, report the backtest. On 23 Nov 2026 the owner restarted work for the
TISC 2026 jury round, due within a week, and asked for real data first (D-044): M2, then M10 (real
data in the app), then M3.

| Milestone | Status | Tests | Commit |
|---|---|---|---|
| M0 Scaffold | Done | 1 passed | 3d536f3 |
| M1 Assets and boundaries | Done | API 41 passed, pipeline 4 passed | 31b4513 |
| M4 Workflow API | Done | API 161 passed | be8e74a |
| M5 Desk | Done | API 197 passed, browser 5 passed | 3309202 |
| M6 Field app | Done | API 204 passed, browser 8 passed | b72f1fe |
| M7 Evidence pack | Done | API 217 passed, browser 10 passed | 3bd08bb |
| M8 Officer record, escalation, monthly page | Done | API 232 passed, browser 13 passed | 30a287f |
| M9 Demo | Done | API 235, pipeline 4, browser 14 passed | M9 commit |
| Stop: report to owner | Owner replied 23 Nov 2026 (D-044) | | |
| M2 Detection on Sentinel-2 | Done | Pipeline 25 passed | cf91bce |
| M10 Real data in the app | Done | API 249, pipeline 25, browser 15 passed | M10 commit |
| M3 Radar and scored backtest | Radar check for built-up done; backtest not started | | |
| M11 Asset creation engine (templates) | Done | API 284, browser 2 new (m11-sources) | 507d359 |
| M12 Weekly record, incidents, documents, two roles | Done | API 263, pipeline 27, browser 4 | 76c6593 |
| M13 Downstream: notifications by area, overview | Done | API 308, pipeline 29, browser 4 | b03bb99 |
| M14 GeoGuard: kinds of land, admin adds and stops watching locations | Done | API 334, pipeline 29, browser 5 | M14 commit |

## M0 Scaffold: done

Done-check run on 6 Nov 2026 from empty volumes (`docker compose down -v`, then `up --wait`):

- `GET /health` returned `{"status":"ok","postgis":"3.4 USE_GEOS=1 USE_PROJ=1 USE_STATS=1","migration":"0001"}`.
- Both services healthy. Host ports are bound to 127.0.0.1 only: database 5544, API 8100.
- `pytest`: 1 passed (health reports PostGIS and the head migration).
- `git check-ignore` covers `.env`, `node_modules`, `venv`, `.venv`, `cache`, `*.tif`, `chips`,
  `__pycache__`, `storage` and `data/demo/generated`.
- Fix made during the check: the database health check now tests TCP. The socket check passed
  during PostGIS's first-run init, so the API started too early and was refused.

## M1 Assets and boundaries: done

- Migration 0002 holds the whole section 7 data model with database guards: append-only
  `boundaries`, `audit_log` and `evidence_packs`; boundary version and supersession checks; the
  owner-claim gate (invariant 4, database half).
- Real assets: `lp assets-osm` builds `data/assets.geojson` from one saved Overpass response
  (DECISIONS.md D-012). `python -m app.seed.real_assets` loaded 11 lakes into the dev database,
  all `derived`, cohort D, mode WATCH. Reloading reports 11 unchanged.
- API: `POST /auth/login` (demo accounts only), `GET /assets`, `GET /assets/{id}`,
  `GET /assets/{id}/boundaries` (all versions, with `in_force`, `superseded_by_id` and
  `effective_valid_to`), `POST /assets/{id}/boundaries` (admin or nodal officer, always a new version).
- Tests: API 41 passed, pipeline 4 passed. They cover mode by cohort for all six cohorts,
  invariant 12 (UPDATE, DELETE, ORM update and TRUNCATE refused), superseded boundary
  retrievable by date, buffer widths 30 m and 9 m, role checks, and the audit chain catching an edit.
- On the dev database, `UPDATE boundaries ...` fails with "the table is append-only".

## M4 Workflow API: done

- Legal check (`app/rules/legal_check.py`): `decide` follows section 6.2 step by step, and `run`
  gathers zone, works, permits and court matters with PostGIS. Each result stores the rule version,
  the boundary version and the matched records.
- Priority (`app/rules/priority.py`): section 6.4 with every factor stored. Overrides need a reason
  and are logged.
- State machine (`app/workflow/state_machine.py`): one table of 24 rules covering section 6.5, plus
  E-004 and D-017. A database trigger refuses any state change made outside it.
- Timers and escalation (`timers.py`, `escalation.py`), with monsoon timing for field assignment.
- Re-check reopen (D-020) and court holds after import (E-004).
- API: `POST /candidates` (pipeline token), `GET /alerts` with filters, `GET /alerts/{id}` with
  allowed actions per role, `POST /alerts/{id}/transitions`, field checks (idempotent, photo hashes,
  server-side distance), owner claims, readiness items, imagery-request stub, priority override,
  records CSV import and list, `GET /audit`, `GET /audit/verify`, `GET /audit/closure-sample`.
- Tests: API 161 passed. Invariants 1 to 9 and 12 pass, plus a test that no module but the state
  machine assigns `state`. The invariant 11 wording scan already covers API strings, configuration
  and trigger messages, and will pick up web strings when they exist.

## M5 Desk: done

- Demo world (`data/demo/world.yml`): 20 fictional assets in open sea (D-015), 9 role accounts,
  fictional permit, restoration work and court case, and 18 alert scenarios. `app.seed.demo` runs
  every scenario through the real ingest and state machine in time order. Synthetic image chips
  and offline base-map tiles (2,039) are drawn from the same file (D-027).
- `python -m app.seed.reset` rebuilds a clean demo (D-030). `sh scripts/e2e.sh` resets, then runs
  browser tests.
- Web app (React, TypeScript, Vite, MapLibre, i18next), served by nginx on http://localhost:8180
  with the API under `/api`. Screens: login by demo role, alert queue (map and list, filters,
  open alerts first by priority), alert detail (boundary badge, before and after images with dates
  and sensor, dated bracket strip, map, legal check panel, actions for the role, history,
  checklist, the section 6.8 statement), assets with boundary versions, records with CSV import,
  and audit with log check and closure sample. English and Telugu.
- Done-check (browser, against a fresh demo): 5 passed. The analyst confirms the headline alert
  only after ticking that the image pair was compared. Closing as not real takes an analyst and a
  reviewer, and the analyst cannot sign twice. The nodal officer assigns to Demo Field Officer 1.
  The desk switches to Telugu.
- API tests: 197 passed. The wording scan (invariant 11) now covers every web source and both i18n files.

## M6 Field app: done

- A progressive web app at `/field`, in the same bundle. Workbox precaches the shell, code and fonts
  (40 files, 2.1 MB) and caches demo tiles on first use. "My alerts", alert details and image pairs
  are kept in IndexedDB. Captures (photos, GPS fix and accuracy, timestamps, outcome, stage, notes)
  queue in IndexedDB with a SHA-256 per photo and are sent on reconnect. Sending is idempotent by
  `client_uuid`, and the server refuses a photo whose hash changed. Device time and server time are
  both kept.
- Distance to the change is checked on the phone and again on the server. Beyond 50 m it warns and
  does not block. The section 9.2 note ("observation, not a survey"), marked as pending counsel, is
  on every alert. English and Telugu are switchable, and Demo Field Officer 1 defaults to Telugu.
- Demo-only switches for "no signal" and simulated position (D-031).
- Done-check (browser, in the same run as M5): 8 passed. The field officer opens the app in Telugu
  and switches to English. Offline, they reload the app, open the alert and see the image pair from
  the device, get a distance warning at 430 m, and save a visit that stays queued across another
  offline reload. The server is unchanged until the browser comes back online. Then the queue sends
  itself and the server shows `FIELD_CONFIRMED` with the photo, device time and server time.
- API tests: 204 passed, adding resend idempotency and the changed-photo refusal.

## M7 Evidence pack: done

- `app/evidence/pack.py` builds a zip holding the before and after chips, field photos, boundary and
  change GeoJSON, the legal check, checklist, full history (with audit hashes), a processing note,
  the section 63(4) certificate template, a WeasyPrint PDF, and `manifest.json` with the SHA-256 of
  every file. The PDF (5 pages for the demo case) covers the eight items of section 9.3 in order, with
  the demo band on every page.
- A pack is never overwritten: each one is a new version. Downloads are single-case and logged as
  exports.
- The desk has an editable checklist (nodal and legal officers), a case-file panel (generate, open the
  PDF, download the zip, check integrity) and field photo thumbnails.
- The demo seed now carries the full-path alert through the checklist, pack v1, `PACK_READY` and
  `WITH_OFFICER`, with the checklist gap logged.
- Done-check, run on a pack downloaded from the running API:
  ```
  lp verify-pack pack.zip --manifest-sha256 783d60d7…   -> PASS  every file matches its hash   (exit 0)
  (one checklist answer changed inside the zip)
  lp verify-pack tampered.zip --manifest-sha256 783d60d7… -> FAIL  changed: records/checklist.json (exit 1)
  ```
- Tests: API 217 passed. They include invariant 13 (statement present, draft mark present until
  counsel review and absent after), verify-pack catching a changed, missing, added or forged file,
  `lp` exit codes, versioning, and the export log. Browser: 10 passed.

## M8 Officer record, escalation, monthly page: done

- Officer record: `POST /alerts/{id}/officer-record` for the legal or senior officer, with notice,
  hearing, order and action fields, and an optional step to `ACTION_RECORDED` (which moves on to
  `POST_ACTION_WATCH`). The desk panel says "The system suggests no outcome. The officer decides."
- Worker container (`python -m app.worker`): records missed timers every 5 minutes (D-036).
- Monthly page: `GET /bulletins/{month}` and `/pdf`, worked out from the audit log (D-034, D-035).
  The desk screen at `/monthly`, which is the senior officer's home, has the five figures against
  last month, a map of every asset with new and overdue alerts marked, overdue alerts by who must act
  and the overdue list. Each PDF is stored with its figures in `bulletins`.
- The demo seed adds a completed path (notice, hearing, order, action recorded) on Demo Cheruvu 5.
- Done-check:
  - The overdue list is correct against known due dates in `test_monthly.py`: a closed month is
    replayed to its own end, and the current month runs to now.
  - The live demo month gave watched 20, new 2, seen on site 1, actions 1, overdue 4. The overdue
    list is Demo Kunta 2 (review, 52 days), Demo Cheruvu 9 (Demo Field Officer 2, 13 days),
    Demo Cheruvu 8 (2 days) and Demo Parcel B (reopened, 1 day).
  - The live PDF has 1 page (pypdf). Rendered, it fits one A4 page.
  - The browser test checks the screen's figures equal the API's, and that recording an officer
    action raises "actions" by 1 and lowers "overdue" by 1.
- Tests: API 232 passed, browser 13 passed.

## M9 Demo: done

- `docs/DEMO.md`: the ten-minute script from section 14, keyed to screens. It opens with "demo data"
  and says no detection result exists yet (D-001).
- `e2e/tests/m9-demo.spec.ts` walks all ten steps on one alert, Demo Cheruvu 1:
  1. map of watched assets;
  2. image pair and dated bracket;
  3. legal check panel;
  4. court hold, restoration work and watch list;
  5. analyst confirms and nodal officer assigns;
  6. phone, offline, in Telugu, then sync;
  7. checklist, evidence pack and integrity check;
  8. case file ready, sent to the officer, officer action recorded;
  9. audit log check;
  10. monthly page.
  Any request that tries to leave localhost fails the test.
- Done-check with no internet: `docker-compose.offline.yml` put every container on an internal
  network (`internal=true`). From inside, the API container could not reach Earth Search,
  OpenStreetMap tiles or Google Fonts (URLError), and the browser's network could not resolve
  outside names (EAI_AGAIN). The walkthrough passed in that mode: 1 passed (28.5 s), with no
  external request attempted. It also passes on the normal network.
- Fixes from reviewing the walkthrough screenshots: the audit screen now shows the "Demo data" band,
  and a map showing only pins stops at district zoom.
- Final runs: API 235 passed, pipeline 4 passed, browser 14 passed (13 milestone tests on one fresh
  demo, then the walkthrough on a second fresh demo).
- A fresh demo, dated today, is left in the database for the owner.

## M2 Detection on Sentinel-2: done

Real data, five tuning lakes outside the case list (D-045). The full record, with what each control
removed, is `reports/m2-tuning/README.md`.

- `pipeline/lake_protect/`: `stac` (Earth Search `sentinel-2-c1-l2a`, one look per acquisition
  date across the UTM 43/44 edge), `raster` (windowed COG reads onto a 10 m EPSG:32644 grid, cloud
  mask first, cached in `C:\lp-cache`; each scene file is opened once for every lake),
  `indices` (MNDWI, NDVI, NDBI, BSI and the section 8.4 classes), `change` (dated bracket and all
  controls), `chips` (true colour, same stretch, hard pixel edges, Copernicus notice), `radar`
  (Sentinel-1 RTC from Planetary Computer for built-up), `detect`, `screen`, `basemap`.
- Rules: `pipeline/lake_protect/detect_rules.yaml`, now `detect-v1` (D-052): section 8.4 plus
  novelty (D-042), established (D-050), one change per place (D-051), the drought control as read
  in D-040, and radar for built-up (D-049). Not frozen yet.
- `lp detect` produced candidates and before and after chips for the five tuning lakes
  (`reports/m2-tuning/run4`): 14 candidates, all at Kapra lake and Gangaram Cheruvu, the two where
  HYDRAA reported restoration works in 2026; none at Saroor Nagar, Peeran or Gopi Cheruvu. Radar
  refused both Sentinel-2 "building" candidates (0.4 and 1.6 dB against 3 dB).
- **No-look-ahead test passes (invariant 10):** the catalogue query ends at the end of the as_of
  day, later items are dropped if returned anyway, and the readers refuse a later scene before any
  pixel is read (`pipeline/tests/test_no_lookahead.py`). The API also refuses a screening run that
  reports a look after its as_of date.
- Disclosure for M3: Durgam Cheruvu, a scored case lake, was run once as a smoke test before
  tuning (D-042).
- Tests: pipeline 25 passed (no look-ahead, every control on synthetic stacks, merge, radar
  arithmetic, classes, OSM registry).

## M10 Real data in the app: done

- Registry: 99 real lakes up to the ORR from the saved OpenStreetMap response (D-038), baseline
  19 July 2024 (D-039), all `derived`, cohort D, watch only.
- Migration 0004: `screen_runs` and `asset_screens`, append-only. `GET /pipeline/watchlist`,
  `POST /pipeline/runs`, `POST /pipeline/basemap` (pipeline token), `GET /screening/runs`,
  `GET /tiles/s2/...`, and `dataset=real|demo` on `GET /alerts` and `GET /assets` (D-043).
- `lp screen` ran over all 99 lakes with scenes up to 22 Nov 2026 (`reports/screen/2026-11-22`):
  7,652 clear looks from March 2022 to November 2026; every lake seen clearly, the newest look at
  most 14 days old; 84 lakes with no candidate, 15 with candidates. 58 candidate changes (46
  clearing, 11 soil fill, 1 building confirmed by radar at +5.3 dB), all on the watch list
  (D-048); radar refused 25 Sentinel-2 building candidates. Fetch and detection took 28 minutes
  the first time; a rerun from cache takes minutes. One candidate was first refused for an area
  rounding error, now fixed (D-054); `lp replay` then put back all 58 after a demo reset.
  Kapra lake (10) and Gangaram Cheruvu (5) are where HYDRAA reported restoration works in 2026.
  No accuracy is claimed: that is M3's job.
- Base map: `lp basemap` built 707 tiles, zoom 9 to 14, from four clear scenes of 29 September to
  14 October 2026, and uploaded them (D-047). Real-lake maps work offline.
- Desk: one switch in the side bar, "Hyderabad lakes (real data)" or "Demo world (fictional)",
  for the queue, assets and monthly page; the latest screen in one line; each lake's coverage
  ("Last clear look ..."); an "Images used" panel on every alert with scene, date, sensor and flags.
- `lp replay reports/screen/<date>` puts a saved screen back after a demo reset, with no internet.
- Scheduled container: `docker compose --profile screen up -d screener` runs `lp screen` weekly.
- Tests: API 249 passed (watch list, runs and coverage, append-only, dataset split, base map
  upload, the area rounding case). Browser 15 passed on fresh demos: `m10-real` (switch, no demo
  record on the real side, Sentinel-2 tiles requested, 99 real lakes listed) with the M5 to M8
  suites, then the M9 walkthrough with no internet.

## M14 GeoGuard: kinds of land, and locations the admin adds or stops watching: done

Owner's request, 25 Nov 2026 (D-061). Design: `docs/locations.md`.

- **Name:** GeoGuard everywhere people see it. Code, Docker and `lp` names are kept until after the
  jury.
- **Kinds of land** (`api/app/categories.yaml`):
  - lakes and water bodies, and government land, are watched now;
  - endowment and forest land are planned, with what each needs. Their asset types are in
    migration 0008, and the API refuses them until they are switched on.
- **Adding a location** (admin):
  - drawn on the Sentinel-2 map (watch only) or uploaded as GeoJSON or KML;
  - checks for Telangana, size, the same place twice, status and reference;
  - the area is shown before saving;
  - the next weekly screen includes it.
- **Stopping the watch:**
  - with a reason, and reversible;
  - nothing is deleted, and open incidents stay;
  - logged in the append-only `monitoring_changes`, which is the only way the database lets
    `assets.monitored` change.
- **Watched only:** the pipeline watchlist, the overview figures, the weekly digest and the monthly
  page count only watched locations. The overview adds a "by kind of land" line.
- **Tests:**
  - API 334 passed, including `test_locations.py` (21) and a dashboard test;
  - pipeline 29 passed;
  - browser 5 passed, including the new `m14-locations`: draw and add, a duplicate refused from a
    file, stop watching.

  They ran on the preview stack.

## M13 Downstream: notifications by area and the overview: done

Owner's request, 25 Nov 2026 (D-059, D-060). Design: `docs/downstream.md`.

- **Migration 0007:**
  - contact details and channels on users;
  - `official_areas`;
  - `notifications`, kept for good: only the acknowledgement can be set, once;
  - `notification_deliveries`, append-only.

  The demo reset migrates down to 0001 and up again through it.
- **Notifications** (`api/app/notify/`):
  - routing by area;
  - English and Telugu messages;
  - acknowledgement in the inbox or by acting on the incident;
  - a reminder after 24 hours, and the admin told after 48;
  - the weekly digest after each stored screen;
  - email to a local outbox or SMTP; SMS and WhatsApp as held templates;
  - the `notifier` service, every minute.
- **Overview** (`api/app/services/dashboard.py`, `web/src/desk/Dashboard.tsx`):
  - State, district, mandal, village, lake;
  - figures that open the incident list with the same filters;
  - a map, an 8-week trend, and rows per area.

  It is now the home page.
- **Desk:**
  - Inbox, with a count in the side bar;
  - an acknowledgement banner on the incident page;
  - the admin's Officials page: channels, contacts, areas, delivery log, send digest.
- **Real lakes:** `lp assets-areas` placed all 99 in 5 districts and 27 mandals, from
  OpenStreetMap boundaries. The loader updates and logs a changed area. On the preview, the
  replayed screen of 22 Nov 2026 notified:
  - the official covering Medchal–Malkajgiri and Sangareddy of 43 incidents;
  - the official covering Ranga Reddy of 15;
  - the admin of all 58.
- **Demo:**
  - two fictional districts, four mandals and eight villages;
  - officials with areas, fictional contacts and channels;
  - the notifier's follow-up each simulated morning: 82 notifications and 3 digests.
- **Tests:** API 308 passed; pipeline 29 passed; browser 4 passed (`m9-demo` walkthrough with no
  internet, now from the overview through the inbox and the Officials page; `m10-real`;
  `m11-sources`). These ran on the preview stack (`docker compose -p lakeprotect-preview`); the
  dev database still needs the reset described in README.

## M12 Weekly record, incidents, legal documents, two roles: done

Owner's request, 24 Nov 2026 (D-057, D-058). Design: `docs/weekly-processing.md`.

- Migration 0006:
  - roles reduced to `admin` and `viewer`;
  - alerts become incidents (OPEN, UNDER_REVIEW, CONFIRMED, DISMISSED, CLOSED) with a
    resolution, and existing rows are mapped across;
  - `incident_reviews`;
  - `asset_screens` gains the week, the image and the changes;
  - `asset_documents`;
  - change type `levelling`.

  Migrating down to 0005 and up again works.
- API:
  - the incident lifecycle replaces the state machine;
  - viewers record reviews and the admin decides;
  - incidents say what changed in plain words;
  - endpoints for the weekly record, its images and documents;
  - the source engine tags documents;
  - the evidence pack holds reviews, decisions and documents;
  - the monthly page counts new, reviewed, confirmed and waiting.
- Removed: the field app, field checks, two-person closures, escalation timers, the worker,
  officer records and the readiness checklist.
- Pipeline (detect-v2):
  - levelling (`other>bare`) is a change type of its own;
  - a weekly image for every asset;
  - each change's incident is sent with the run;
  - `lp replay` resends images.

  On the preview stack, `lp screen` of Kapra lake and Saroor Nagar Lake drew both weekly images
  and linked Kapra's ten continuing changes to their open incidents.
- Demo: one admin and two viewers; 19 incidents across every state; fictional PDF documents on
  all 20 assets; eight weeks of weekly records with images (one cloudy week for two assets).
- Desk:
  - an incident list filtered by state and what changed;
  - an incident page with a review form for viewers and decision steps for the admin;
  - a week-by-week strip and legal documents on Assets;
  - the monthly page in the new figures;
  - Telugu drafts for all new strings.
- Tests: API 263 passed; pipeline 27 passed; browser 4 passed (`m9-demo` walkthrough with no
  internet, `m10-real`, `m11-sources`). These ran on a separate preview stack
  (`docker compose -p lakeprotect-preview`, ports 5545/8101/8181): the reset of the dev database
  was not run, because it wipes it. The dev database needs that reset, then `lp replay`, before
  the dev desk works (README).

## M11 Asset creation engine (templates): done

Owner's request, 24 Nov 2026: compare the solution with the code, then build the data source
layer that collects government records and creates assets, as templates because no data-sharing
agreement exists (D-056). Comparison and design: `docs/asset-engine.md`.

- Migration 0005: `source_snapshots`, `import_runs`, `asset_source_links`, `land_parcels` (all
  append-only) and the `land_parcels_current` view. Boundaries gain `source_snapshot_id` and
  `positional_accuracy_m`. Migrating down to 0001 and up again works.
- `app/sources`: four template connectors with data contracts (HMDA Lake Protection Committee,
  Irrigation and CAD, Bhu Bharati land records, HYDRAA); file-drop, sample and official-API
  transports (the API refuses without an agreement, and refuses HTML); a privacy filter that drops
  owner, phone and Aadhaar columns before a file is stored; the engine (validate, match, reconcile,
  publish, dry run by default).
- Fictional samples in open sea 15 km from the demo world, with every awkward case the engine must
  handle. Not loaded into the dev database (they would widen the demo map).
- API: `GET /sources`, `POST /sources/{name}/runs`, `GET /sources/runs`, `GET /assets/{id}/register`.
  CLI: `python -m app.sources list | run | samples`.
- Desk: a Sources page (preview and load; admin and nodal officer run, others view) and a register
  panel on Assets (source IDs, survey numbers touched, land category, lake-bed area). Telugu strings
  are drafts (D-028).
- Tests: API 284 passed (16 new). Browser `m11-sources` 2 passed, run on its own without a reset
  because it only previews; the full `scripts/e2e.sh` was not run, because it resets the dev database.

## Stop: report to owner (after M9)

The owner's order puts a stop here. M2 and M3 start when the owner replies.

**Needed for M2 and M3, so the owner can prepare now:**
- **Sentinel-1 access (M3):** a free Copernicus Data Space Ecosystem account, plus S3 keys from its
  S3 key manager, put in `.env` as `LP_CDSE_S3_ACCESS_KEY` and `LP_CDSE_S3_SECRET_KEY`. Sentinel-2
  (M2) needs no account.
- **JRC water history:** this needs Google Earth Engine, with a Cloud project and a service account.
  Without it, the seasonal control uses the previous two years of Sentinel data, as the owner's
  instructions allow.
- **Cases:** of the 21 starter names, 6 have an OpenStreetMap polygon and 3 of those are ambiguous.
  Each case must be confirmed from its source (location, date, area over 0.25 acre). Hand-traced
  boundaries from the owner are needed for the rest. Reaching 30 eligible cases is unlikely from the
  starter list alone, so M3 may be a partial result, not a Gate 1 pass.
- **Disk:** about 15 GB is free on C:. The geospatial Python packages and a windowed imagery cache
  fit, but full scenes are never downloaded.

## Stubbed

- Imagery requests are recorded with an estimate. Nothing is ordered (section 3).
- Signals (CCTV, Praja Vani) have a table but no endpoint. They are not in the demo script.
- Escalation "notify" is an audit event and an overdue flag. No email or SMS.
- The scheduled worker container that runs escalation comes in M8. The job itself exists and is tested.

- The weekly re-check from space is not scheduled until the pipeline exists (D-036).
- Telugu strings are drafts awaiting a native speaker's review (D-028).
- A real phone over the network needs HTTPS, which is not set up (D-032).

- The section 63(4) certificate is a template with counsel placeholders, marked draft (D-033).

## Questions for counsel (draft marks stay on until answered)

- Section 63(4) certificate wording, and who may sign Part B.
- How a field check works without being a "survey". The field app shows "This is an observation,
  not a survey. Do not enter private land." as pending legal review.
- Buffer widths in `rules/config.yaml` (section 4) before any real use.

## Next

M3, after the jury round: confirm the case list from sources (locations, dates, areas), hand-trace
the outlines OpenStreetMap lacks, step the screen weekly through 2017 to 2026 for each case, tag
the frozen rules in git, run the 30 cases once and write the section 8.6 report, with the Durgam
Cheruvu disclosure (D-042). Sentinel-1 needs no account (D-049); the Copernicus keys asked for
above are no longer needed.
