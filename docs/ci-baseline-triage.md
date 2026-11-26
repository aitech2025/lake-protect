# API/PostGIS CI baseline triage

**Date:** 26 November 2026  
**Branch under repair:** `feature/p0-ci-triage`  
**Canonical branch at triage start:** `feature/consolidated`  
**Scope:** the 40 API/PostGIS failures in the canonical CI run; this document does not waive or suppress tests.

## Evidence

The exact same 40 test names and failure signatures occur in both runs:

- [Canonical validation run 45765808663](https://github.com/aitech2025/lake-protect/actions/runs/45765808663) — API/PostGIS: 347 passed, 40 failed.
- [Canonical run 45766083814](https://github.com/aitech2025/lake-protect/actions/runs/45766083814) — API/PostGIS: 347 passed, 40 failed.

The PostGIS service started, migrations ran, and 347 tests completed successfully. No service-startup, dependency-installation or database-connection failure is visible in the job log. The same failures repeat deterministically, so the evidence does not point to a transient CI/environment problem.

## Failure classification

| Failure group | Count | Classification | Finding / action |
|---|---:|---|---|
| `test_boundaries.py`, `test_dashboard.py`, `test_lifecycle.py`, `test_locations.py`, `test_monthly.py`, `test_notifications.py`, `test_rules_mode.py`, plus the citizen incident-link test | 38 | Test-fixture / product-contract mismatch | `api/tests/factories.py` created ordinary test assets and users with `is_demo=True` by default. Since D-057/D-065, production list, dashboard, monthly and notification paths intentionally isolate demo records. API tests were therefore exercising hidden demo records while asserting real-record behavior. Change ordinary test fixture defaults to `is_demo=False`; make tests that specifically exercise demo isolation opt in explicitly. |
| `test_sources.py::test_hydraa_upgrades_a_preliminary_lake_and_adds_recovered_land` | 1 | Obsolete test expectation | Connector sample assets are intentionally marked demo (D-056) and the real-asset API excludes them. The test incorrectly expected those samples to appear in `GET /assets`. Keep the product isolation rule and assert that imported samples remain hidden from the real-asset listing while their import/database results remain verifiable. |
| `test_citizen.py::test_the_whatsapp_conversation_makes_a_report_and_its_incident` | 1 | Product defect | Confirmed `NameError: name 'is_demo' is not defined` in `api/app/citizen/whatsapp.py::_step`. `handle()` already receives the demo flag but did not pass it to `_step()`; the submit path then referenced an undefined variable. Pass the flag through explicitly. |

### Interpretation

- The 38 fixture-related failures are not evidence that the production endpoints should expose demo data. The tests must create ordinary non-demo records when validating ordinary API behavior.
- The source-sample test must not weaken demo isolation to satisfy its old assertion.
- The WhatsApp NameError is a genuine runtime defect and is fixed in this branch by threading the existing `is_demo` argument into the conversation step.
- No CI/environment failure has been established from the available logs.
- These are classifications from log evidence and source inspection. The repair is not considered validated until the API/PostGIS suite is rerun.

## Reproducible CI commands

The canonical workflow is `.github/workflows/ci.yml`. It uses Python 3.13, Node.js 22 and PostGIS `postgis/postgis:16-3.4`.

| Job | Install / run commands | Current canonical result |
|---|---|---|
| API + PostGIS | `pip install -r api/requirements.txt`; `pip install -e pipeline`; from `api/`, run `pytest -q` | 347 passed / 40 failed |
| Pipeline | From `pipeline/`, run `pip install -e ".[dev,osm,ml,geo]"`; then `pytest -q` | 77 passed |
| Web | From `web/`, run `npm ci`; then `npm run build` | Passed |

The API job requires a reachable PostGIS 16 / PostgreSQL 16 test service and the same environment used in CI:

- `LP_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/lakeprotect`
- `LP_TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/lakeprotect_test`
- `LP_JWT_SECRET` and `LP_PIPELINE_TOKEN` set to non-production test values
- `LP_DB_POOL_SIZE=3`, `LP_DB_MAX_OVERFLOW=2`
- `LP_DATA_DIR` and `LP_REPO_DIR` pointing to the checkout

The test harness recreates the database named by `LP_TEST_DATABASE_URL` and migrates it to head. Never point that variable at a developer or production database.

## Repair validation result — 26 November 2026

The repair is validated on PR #21's latest full CI run:

- [Run #275](https://github.com/aitech2025/lake-protect/actions/runs/45776369043), commit `99c36fb6fcf3421c46331922d17d278cb736f624`.
- API/PostGIS: **387 passed, 0 failed** (one warning).
- Pipeline: **77 passed**.
- Web type-check/build: **passed**.
- All three jobs completed successfully. No test was skipped or marked xfail to obtain this result.
- An intermediate run after the first fixture correction left two tests failing: the evidence-pack fixture still expected demo data without explicitly creating a demo asset, and the pipeline rejection test still created a real asset while calling it demo. Both tests now declare demo intent explicitly; the production demo-isolation behavior remains unchanged.
- The evidence-pack demo banner was also moved into normal printable page flow so PDF text extraction and readers can see it.

CI now writes compact test totals and failing test names to each pytest job summary and uploads API/PostGIS and pipeline JUnit XML reports as workflow artifacts, including on failed test runs.

## Repair validation criteria

1. Run the full API/PostGIS suite; do not mark P0.3 complete based only on fixture inspection.
2. Preserve explicit demo-isolation coverage: demo notifications must not be sent through SMTP, and imported sample records must not appear in real-asset APIs.
3. Confirm the WhatsApp conversation path passes with `is_demo=False`, and retain coverage for an explicitly demo conversation if that path is supported.
4. Confirm pipeline and web jobs remain green.
5. Record the new run URL and exact pass/fail counts in `docs/IMPLEMENTATION_PLAN.md`. Any remaining failures must be classified individually; do not suppress them or lower assertions to manufacture a green build.
