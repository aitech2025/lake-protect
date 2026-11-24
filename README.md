# Lake Protect (working name)

Prototype of a monitoring loop for Telangana's lakes and government land. `CONTEXT.md` is the
source of truth. `PROGRESS.md` shows what is built and what comes next. `DECISIONS.md` records every
choice that departs from, or fills a gap in, `CONTEXT.md`.

Two worlds, never mixed on one screen (switch in the desk's side bar):

- **Hyderabad lakes (real data):** 99 lakes up to the ORR, outlines from OpenStreetMap, screened from
  Sentinel-2 (and Sentinel-1 radar for built-up) by `lp screen`. Real alerts stop at the watch list,
  because no official boundary is loaded yet (DECISIONS.md D-048).
- **Demo world (fictional):** the full loop to an officer, on invented places (`is_demo`, marked on
  every screen, image and PDF).

The scored blind backtest (M3) has not been run, so no accuracy figure exists yet.

## Run

```powershell
Copy-Item .env.example .env      # then set LP_DB_PASSWORD, LP_JWT_SECRET and LP_PIPELINE_TOKEN
docker compose up -d --build
docker compose exec -e LP_ALLOW_RESET=true api python -m app.seed.reset   # real assets + fresh demo
```

| Service | Address |
|---|---|
| Desk | http://localhost:8180 |
| API | http://localhost:8100/health (also under `/api` on the app's address) |
| Database | localhost:5544, bound to this machine only |

Two roles (DECISIONS.md D-057): **admin**, who runs the application and decides on incidents, and
**viewer**, the officials, who see everything and record reviews. The demo accounts are
`demo.admin`, `demo.viewer1` (Telugu) and `demo.viewer2`. How the weekly record, incidents and
legal documents work: [docs/weekly-processing.md](docs/weekly-processing.md).

The demo script is in [docs/DEMO.md](docs/DEMO.md). After the first build the laptop needs no
internet: tiles, image pairs, fonts and the app are all local.

## Real data: the screen from space

The pipeline runs on the host, in the venv outside OneDrive. It needs internet; the desk does not.

```powershell
$env:LP_CACHE_DIR = "C:\lp-cache"                       # imagery cache, never inside OneDrive
$env:LP_PIPELINE_TOKEN = "<same value as in .env>"
docker compose exec api python -m app.seed.real_assets   # load or update the 99 real lakes
C:\lp-cache\venv\Scripts\lp screen                       # weekly screen: watch list in, candidates and coverage out
C:\lp-cache\venv\Scripts\lp basemap --upload             # offline Sentinel-2 base map for the real-lake maps
C:\lp-cache\venv\Scripts\lp replay reports\screen\<date>  # after a demo reset: resend a saved screen, no internet
C:\lp-cache\venv\Scripts\lp detect --asset <asset_key>   # one or more lakes from data/assets.geojson, report only
```

Government sources (asset creation engine, `docs/asset-engine.md`). No data-sharing agreement exists yet, so they read files:

```powershell
docker compose exec api python -m app.sources list                                    # data contracts
docker compose exec api python -m app.sources run hmda_lpc --transport sample --items  # dry run
docker compose exec api python -m app.sources samples --apply                          # load all four fictional samples
```

Install once: `py -m venv C:\lp-cache\venv`, then `C:\lp-cache\venv\Scripts\pip install -e "pipeline[geo,osm,dev]" planetary-computer`.
Rules are in `pipeline/lake_protect/detect_rules.yaml`; the tuning record is `reports/m2-tuning/README.md`.

## Test

```powershell
docker compose exec api pytest                 # API: invariants, incidents, weeks, documents, packs, monthly page
C:\lp-cache\venv\Scripts\python -m pytest pipeline/tests -p no:cacheprovider
sh scripts/e2e.sh                              # browser tests on a fresh demo (Chromium in Docker)
```

To prove the demo runs with no internet, start the stack on an internal network and run the walkthrough:

```powershell
$env:COMPOSE_PATH_SEPARATOR=":"; $env:COMPOSE_FILE="docker-compose.yml:docker-compose.offline.yml"
docker compose down; docker compose up -d --wait db api web
sh scripts/e2e.sh m9-demo
Remove-Item Env:COMPOSE_FILE; docker compose -f docker-compose.yml -f docker-compose.offline.yml down; docker compose up -d
```

## Tools

- `lp verify-pack <zip> --manifest-sha256 <hash>`: recompute every hash in an evidence pack.
- `lp assets-osm`: rebuild `data/assets.geojson` from the saved OpenStreetMap response.
- `lp detect`, `lp screen`, `lp replay`, `lp basemap`: the detection pipeline (above).

Keep `node_modules`, virtual environments and the imagery cache outside this OneDrive folder. The
containers use named volumes, and the pipeline venv is at `C:\lp-cache\venv`.
