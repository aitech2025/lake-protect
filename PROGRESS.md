# Progress

Read this first at the start of every session, then continue from the first unfinished milestone.

**Build order (owner's instruction, see DECISIONS.md D-001):** M0, M1, M4, M5, M6, M7, M8, M9,
**stop and report**, M2, M3, report the backtest.

| Milestone | Status | Tests | Commit |
|---|---|---|---|
| M0 Scaffold | Done | 1 passed | M0 commit |
| M1 Assets and boundaries | In progress | | |
| M4 Workflow API | Not started | | |
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

## Stubbed

Nothing yet.

## Next

M1: assets and boundaries.
