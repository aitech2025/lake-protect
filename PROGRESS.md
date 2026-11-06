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
| M6 Field app | Done | API 204 passed, browser 8 passed | M6 commit |
| M7 Evidence pack | Done | API 217 passed, browser 10 passed | M7 commit |
| M8 Officer record, escalation, monthly page | Done | API 232 passed, browser 13 passed | M8 commit |
| M9 Demo | In progress | | |
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

M9: demo. Section 14 end to end on one laptop with no internet, using cached tiles and image chips.
