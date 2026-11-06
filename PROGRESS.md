# Progress

Read this first at the start of every session, then continue from the first unfinished milestone.

**Build order (owner's instruction, see DECISIONS.md D-001):** M0, M1, M4, M5, M6, M7, M8, M9,
**stop and report**, M2, M3, report the backtest.

| Milestone | Status | Tests | Commit |
|---|---|---|---|
| M0 Scaffold | Done | 1 passed | M0 commit |
| M1 Assets and boundaries | Done | API 41 passed, pipeline 4 passed | M1 commit |
| M4 Workflow API | In progress | | |
| M5 Desk | Not started | | |
| M6 Field app | Not started | | |
| M7 Evidence pack | Not started | | |
| M8 Officer record, escalation, monthly page | Not started | | |
| M9 Demo | Not started | | |
| **Stop: report to owner** | | | |
| M2 Detection on Sentinel-2 | Not started | | |
| M3 Radar and scored backtest | Not started | | |

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

## Stubbed

- No demo users exist yet, so the API can only be called from tests. They are seeded in M4.

## Next

M4: workflow API.
