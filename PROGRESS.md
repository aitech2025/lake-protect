# Progress

Read this first at the start of every session, then continue from the first unfinished milestone.

**Build order (owner's instruction, see DECISIONS.md D-001):** M0, M1, M4, M5, M6, M7, M8, M9,
**stop and report**, M2, M3, report the backtest.

| Milestone | Status | Tests | Commit |
|---|---|---|---|
| M0 Scaffold | Done | 1 passed | M0 commit |
| M1 Assets and boundaries | Done | API 41 passed, pipeline 4 passed | M1 commit |
| M4 Workflow API | Done | API 161 passed | M4 commit |
| M5 Desk | Done | API 197 passed, browser 5 passed | M5 commit |
| M6 Field app | In progress | | |
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

## Stubbed

- Imagery requests are recorded with an estimate. Nothing is ordered (section 3).
- Signals (CCTV, Praja Vani) have a table but no endpoint. They are not in the demo script.
- Escalation "notify" is an audit event and an overdue flag. No email or SMS.
- The scheduled worker container that runs escalation comes in M8. The job itself exists and is tested.

- The Monthly page and Field app routes show a placeholder until M8 and M6.
- Telugu strings are drafts awaiting a native speaker's review (D-028).

## Next

M6: field app (PWA). Offline capture queued in IndexedDB, sync on reconnect, distance warning,
language toggle.
