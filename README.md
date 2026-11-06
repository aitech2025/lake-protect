# Lake Protect (working name)

Prototype of a monitoring loop for Telangana's lakes and government land. `CONTEXT.md` is the
source of truth. `PROGRESS.md` shows what is built and what comes next. `DECISIONS.md` records every
choice that departs from, or fills a gap in, `CONTEXT.md`.

**Everything in the demo is fictional** (`is_demo`, marked on every screen, image and PDF). No
detection result exists yet: the blind backtest (M2, M3) is still to come.

## Run

```powershell
Copy-Item .env.example .env      # then set LP_DB_PASSWORD, LP_JWT_SECRET and LP_PIPELINE_TOKEN
docker compose up -d --build
docker compose exec -e LP_ALLOW_RESET=true api python -m app.seed.reset   # real assets + fresh demo
```

| Service | Address |
|---|---|
| Desk and field app | http://localhost:8180 (field app at `/field`) |
| API | http://localhost:8100/health (also under `/api` on the app's address) |
| Database | localhost:5544, bound to this machine only |
| Worker | Escalation job every 5 minutes (`docker compose logs worker`) |

The demo script is in [docs/DEMO.md](docs/DEMO.md). After the first build the laptop needs no
internet: tiles, image pairs, fonts and the app are all local.

## Test

```powershell
docker compose exec api pytest                 # API: invariants, workflow, packs, monthly page
C:\lp-cache\venv\Scripts\python -m pytest pipeline/tests -p no:cacheprovider
sh scripts/e2e.sh                              # browser tests on a fresh demo (Chromium in Docker)
```

To prove the demo runs with no internet, start the stack on an internal network and run the walkthrough:

```powershell
$env:COMPOSE_PATH_SEPARATOR=":"; $env:COMPOSE_FILE="docker-compose.yml:docker-compose.offline.yml"
docker compose down; docker compose up -d --wait db api worker web
sh scripts/e2e.sh m9-demo
Remove-Item Env:COMPOSE_FILE; docker compose -f docker-compose.yml -f docker-compose.offline.yml down; docker compose up -d
```

## Tools

- `lp verify-pack <zip> --manifest-sha256 <hash>`: recompute every hash in an evidence pack.
- `lp assets-osm`: rebuild `data/assets.geojson` from the saved OpenStreetMap response.

Keep `node_modules`, virtual environments and the imagery cache outside this OneDrive folder. The
containers use named volumes, and the pipeline venv is at `C:\lp-cache\venv`.
