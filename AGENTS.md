# GeoGuard project context

Read this before changing the code. The project was formerly called Lake Protect, so package names,
environment variables, Docker resources, local storage keys, and some docs still use `lake-protect`
or `LP_*`. Keep those identifiers stable unless a task explicitly calls for renaming them.

## What this project does

GeoGuard is a Telangana-focused prototype for monitoring lakes and government land. It connects a
weekly satellite screen to a reviewable incident workflow: show observed change, let officials
review it, retain the source records and boundary versions, route it to the relevant area, and
publish a monthly summary. A satellite observation is evidence of physical change, not a legal
finding. The system must not label a place illegal or recommend demolition.

The current app uses real lake locations and OpenStreetMap outlines. The owner removed the fictional
demo world and demo maps (D-065), but kept the demo role accounts for sign-in. There are currently
99 ORR-area lake assets. Their OSM boundaries are `derived`, so real detections stop at `WATCH_LIST`
until an official boundary is loaded. Do not imply that a real case has completed the field or legal
workflow. The scored blind backtest (M3) has not been run; there is no accuracy result to claim.

There are four personas (D-067): the **admin** maintains the application (people and their areas,
locations, sources, satellites, settings) and takes no step on an incident; the **senior official**
sees the State and gives the final approval and closes; the **district officer** sees only their
districts, reviews, sends field officers and recommends; the **field officer** sees only the
incidents assigned to them and submits field reports with photos and GPS. Who may see what is
enforced in `api/app/access.py`; who may take each step in `api/app/workflow/incidents.py`. The
public citizen report page is available without sign-in. English and Telugu are the supported
languages.

## Product and domain rules

- Officials make decisions. Imagery reports physical change only.
- Show boundary status and provenance wherever a boundary informs a case. Boundaries are versioned
  and append-only; never silently replace or downgrade one.
- Compare changes to the asset baseline. Old features are not new alerts.
- Keep detection owner-blind. Do not add claimant or owner personal data to detection results,
  ordinary screens, or evidence packs.
- Keep review and closure actions attributable and auditable. Follow the API state machine and its
  database guards; do not mutate incident state through a side path.
- Distinguish “not observed” or “no usable look” from “no change.”
- Government-source integrations are templates only until a data-sharing agreement exists. Do not
  add scraping or call a government system without an explicit decision.
- Satellite source settings are managed in the app; detection thresholds remain in the versioned
  pipeline rules file.

## Code map

| Area | Location | Notes |
|---|---|---|
| React desk and public portal | `web/src/` | Vite, TypeScript, React Router, MapLibre, i18next. Pages are grouped under `desk/`, `bulletin/`, and `portal/`. |
| Shared map | `web/src/components/MapView.tsx` | MapLibre layers, offline raster tiles, boundaries, and clickable pins. |
| Overview | `web/src/desk/Dashboard.tsx` and `dashboard.css` | State → district → mandal → village → asset drill-down; data from `/dashboard`. |
| WhatsApp test UI | `web/src/desk/WhatsAppTest.tsx` and `whatsapp-test.css` | Admin-only local conversation simulator; API flag is off by default and simulated records are isolated. |
| Locations | `web/src/desk/Assets.tsx` | Asset list, map, selected asset, boundary versions, and monitoring controls. |
| Monthly bulletin | `web/src/bulletin/Monthly.tsx` and `monthly.css` | Monthly figures, SVG map and legend. SVG colors are drawn in `api/app/bulletin/render.py`. |
| Translations | `web/src/i18n/en.json`, `te.json` | Add/update both locales for user-facing strings. |
| API | `api/app/` | FastAPI routers, services, rules, workflow, notifications, and seed logic. |
| Database | `api/migrations/versions/` | Alembic migrations; PostGIS is used for geometry. Preserve database invariants. |
| Satellite pipeline | `pipeline/lake_protect/` | `lp` CLI, screening, detection, replay, basemap, and evidence-pack verification. |
| Real lake registry | `data/assets.geojson` | OSM-derived registry; treat as input data and use its CLI workflow for regeneration. |
| Owner decisions | `DECISIONS.md` | D-055 onward records the current data, roles, notification, dashboard, citizen, real-data and satellite-source choices. |

## Local architecture

Docker Compose runs PostgreSQL/PostGIS, FastAPI, a notifier worker and an nginx-served web app. The
optional `screen` profile runs the satellite screener/reviewer and needs internet access. The desk
uses local tiles and can run offline after setup; screening and satellite review need internet.
Configuration is in `.env` (start from `.env.example`); never commit secrets. See `README.md` for
the current PowerShell setup and ports.

The web app calls the API under `/api`. `web/src/api.ts` owns the API base and auth helpers. API
business rules belong in services, not UI-only checks. Changes that alter persisted data or state
need the corresponding migration, audit behavior, and API validation.

## Documentation and conflict handling

Use these sources in this order when statements disagree:

1. The owner's latest request in the active conversation.
2. The latest applicable entry in `DECISIONS.md` (especially D-055 through D-066).
3. Current implementation and focused docs under `docs/`.
4. `README.md` for setup and the present-day product overview.
5. `CONTEXT.md` and older portions of `PROGRESS.md` as historical design context.

`CONTEXT.md` contains earlier scope and persona descriptions that were superseded: for example,
fictional demo data, more than two roles, and some unbuilt design-only features. Do not revive those
choices without a new owner decision. `PROGRESS.md` is a milestone history and may lag later
decisions; confirm current behavior in code and `DECISIONS.md`.

Focused references:

- `docs/weekly-processing.md` — weekly records, incidents and legal documents.
- `docs/locations.md` — kinds of land, admin-added locations and watch status.
- `docs/asset-engine.md` and `docs/asset-load.md` — source templates and boundary ingestion.
- `docs/downstream.md` — area-based notifications and overview behavior.
- `docs/citizen.md` — citizen report, review and status flow.
- `docs/DEMO.md` — presentation walkthrough; check its real-data assumptions before relying on it.
- `reports/m2-tuning/README.md` — detection tuning record; not a scored backtest.

## Recent UI request

On 25 Nov 2026, the overview map drill-down was clarified: a dot should open the specific monitored
location, and district/mandal views need direct navigation back to their parent. The monthly map
needs a clear color-keyed legend. Current implementation work is in `Dashboard.tsx`, `Assets.tsx`,
`Monthly.tsx`, their stylesheets, and both translation files. Preserve those interaction expectations
when extending these screens.

The admin-only WhatsApp intake simulator is opt-in with `LP_ENABLE_WHATSAPP_SIMULATOR=true`. It
creates records flagged `is_demo=true` and uses the actual WhatsApp conversation handler; keep its
reports/incidents out of live lists, official notifications, and monthly totals.

## Change workflow

- Read the relevant decision and focused doc before changing workflow or data behavior.
- Keep user-visible labels in both translation files; prefer plain English and clear Telugu.
- Preserve URL-backed drill-down filters so a level can be refreshed or shared.
- Avoid broad refactors for a focused UI request. Do not rewrite real-data files by hand.
- When reporting work, state what changed and whether it was exercised. Do not claim tests or builds
  passed unless they were run.
