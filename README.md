# GeoGuard

Formerly Lake Protect, the name the TISC 2026 jury shortlisted. The code, the `lp` command, the `LP_`
settings and the Docker project keep the old name for now (DECISIONS.md D-061).

Prototype of a monitoring loop for Telangana's lakes and government land, with endowment and forest
land planned. `CONTEXT.md` is the
source of truth. `PROGRESS.md` shows what is built and what comes next. `DECISIONS.md` records every
choice that departs from, or fills a gap in, `CONTEXT.md`.

**Real data only** (DECISIONS.md D-065): 99 lakes up to the ORR, outlines from OpenStreetMap,
screened from Sentinel-2 (and Sentinel-1 radar for built-up) by `lp screen`, plus the locations the
admin adds and the places citizens report. Real incidents stop at the watch list, because no
official boundary is loaded yet (DECISIONS.md D-048). The fictional demo world and its drawn map
were removed at the owner's request; only the role accounts were kept.

The scored blind backtest (M3) has not been run, so no accuracy figure exists yet.

## Run

```powershell
Copy-Item .env.example .env      # then set LP_DB_PASSWORD, LP_JWT_SECRET and LP_PIPELINE_TOKEN
docker compose up -d --build
docker compose exec -e LP_ALLOW_RESET=true api python -m app.seed.reset   # real lakes + the role accounts
C:\lp-cache\venv\Scripts\lp replay reports\screen\2026-11-22                # the real incidents, no internet
```

| Service | Address |
|---|---|
| Desk | http://localhost:8180 |
| Citizen portal | http://localhost:8180/report |
| API | http://localhost:8100/health (also under `/api` on the app's address) |
| Database | localhost:5544, bound to this machine only |
| Notifier | Reminders, escalations to the admin and the email outbox, every minute (`docker compose logs notifier`) |

Two roles (DECISIONS.md D-057): **admin**, who runs the application and decides on incidents, and
**viewer**, the officials, who see everything and record reviews. The role accounts are
`demo.admin`, `demo.viewer1` (Telugu; Hyderabad, Ranga Reddy) and `demo.viewer2` (Medchal–Malkajgiri,
Sangareddy), listed in `data/accounts.yml`; they sign in with one click. How the weekly record, incidents and
legal documents work: [docs/weekly-processing.md](docs/weekly-processing.md).

The desk opens on the **Overview**, which drills down from State to district, mandal, village and
lake. Each official is notified about incidents in their own area:
- in the **Inbox**, where they acknowledge;
- by email;
- by SMS and WhatsApp, as templates held until a gateway exists.

The `notifier` service sends reminders after 24 hours and tells the admin after 48. The admin
manages areas and channels on the **Officials** page. Design: [docs/downstream.md](docs/downstream.md).

**Locations.** The admin adds a location on the **Locations** page, by drawing it on the satellite
map or uploading a GeoJSON or KML file. The next weekly screen includes it. Removing a location means
**Stop watching**, with a reason: nothing is deleted, and it can be watched again. The kinds of land
watched now and planned are listed in `api/app/categories.yaml`. Design:
[docs/locations.md](docs/locations.md).

**Satellites.** The admin keeps the satellite image sources on the **Satellites** page (D-066):
- **The weekly screen's optical source** (Sentinel-2 today) and the radar check (Sentinel-1);
- **sharper paid images,** with the price per sq km used for estimates.

The admin adds, changes, turns on or off and deletes them, and every change is logged. `lp screen`
and `lp review-reports` read the sources that are on at the start of each run. Detection
thresholds stay in `pipeline/lake_protect/detect_rules.yaml`.

**Citizens.**
- **How they report:**
  - on the public portal at `/report`, with no sign-in, in English or Telugu;
  - on WhatsApp, once the State's channel exists;
  - through staff, who enter 1070 calls and Praja Vani petitions on **Citizen reports**.
- **What happens to a report:**
  - the app finds the place;
  - it opens an incident, or joins one already open nearby;
  - it reviews the place with satellite imagery;
  - it tells the area's officials.

  The satellite review waits for the `reviewer` service:
  `docker compose --profile screen up -d reviewer`, which needs internet.
- **What officials do** (both roles, D-064): acknowledge, add notes, compare satellite looks by
  date, attach the legal records, ask for a sharper image (the admin approves), approve or decline
  and close, each with a note, and put a reported place on the weekly watch.
- **How citizens hear back:** each report gets a reference. Its status page `/report/track/<ref>`
  shows every step in their language, and SMS or WhatsApp updates start once a gateway is set up.
- **Design:** [docs/citizen.md](docs/citizen.md).

The presentation script is in [docs/DEMO.md](docs/DEMO.md). After the first build the desk needs no
internet: tiles, image pairs, fonts and the app are all local. Satellite reviews and looks need it.

## Real data: the screen from space

The pipeline runs on the host, in the venv outside OneDrive. It needs internet; the desk does not.

```powershell
$env:LP_CACHE_DIR = "C:\lp-cache"                       # imagery cache, never inside OneDrive
$env:LP_PIPELINE_TOKEN = "<same value as in .env>"
docker compose exec api python -m app.seed.real_assets   # load or update the 99 real lakes
C:\lp-cache\venv\Scripts\lp screen                       # weekly screen: watch list in, candidates and coverage out
C:\lp-cache\venv\Scripts\lp basemap --upload             # offline Sentinel-2 base map for the real-lake maps
C:\lp-cache\venv\Scripts\lp replay reports\screen\<date>  # after a reset: resend a saved screen, no internet
C:\lp-cache\venv\Scripts\lp detect --asset <asset_key>   # one or more lakes from data/assets.geojson, report only
C:\lp-cache\venv\Scripts\lp assets-areas                 # district and mandal of each real lake (OpenStreetMap boundaries)
```

Government sources (asset creation engine, `docs/asset-engine.md`). No data-sharing agreement exists yet, so they read files:

```powershell
docker compose exec api python -m app.sources list                                    # data contracts
docker compose exec api python -m app.sources run hmda_lpc --transport sample --items  # dry run
docker compose exec api python -m app.sources samples                                  # preview the four fictional samples (never loaded)
```

Install once: `py -m venv C:\lp-cache\venv`, then `C:\lp-cache\venv\Scripts\pip install -e "pipeline[geo,osm,dev]" planetary-computer`.
Rules are in `pipeline/lake_protect/detect_rules.yaml`; the tuning record is `reports/m2-tuning/README.md`.

## Test

```powershell
docker compose exec api pytest                 # API: invariants, incidents, weeks, documents, notifications, overview
C:\lp-cache\venv\Scripts\python -m pytest pipeline/tests -p no:cacheprovider
sh scripts/e2e.sh                              # browser tests after a reset and a replay (Chromium in Docker)
```

The browser tests write test records (reports, decisions): run them on a separate stack, such as
`docker compose -p lakeprotect-preview`, and reset it afterwards.

To prove the desk runs with no internet, start the stack on an internal network and run the walkthrough:

```powershell
$env:COMPOSE_PATH_SEPARATOR=":"; $env:COMPOSE_FILE="docker-compose.yml:docker-compose.offline.yml"
docker compose down; docker compose up -d --wait db api notifier web
sh scripts/e2e.sh m9-desk
Remove-Item Env:COMPOSE_FILE; docker compose -f docker-compose.yml -f docker-compose.offline.yml down; docker compose up -d
```

## Tools

- `lp verify-pack <zip> --manifest-sha256 <hash>`: recompute every hash in an evidence pack.
- `lp assets-osm`: rebuild `data/assets.geojson` from the saved OpenStreetMap response.
- `lp detect`, `lp screen`, `lp replay`, `lp basemap`: the detection pipeline (above).

Keep `node_modules`, virtual environments and the imagery cache outside this OneDrive folder. The
containers use named volumes, and the pipeline venv is at `C:\lp-cache\venv`.
