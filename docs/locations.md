# Locations: what GeoGuard watches, and how the admin adds or removes one (M14)

Built 25 November 2026 (DECISIONS.md D-061). The owner asked for three things:
- rename the platform **GeoGuard**;
- watch government land as well as lakes, with endowment and forest land to come;
- let the admin add and remove a location to monitor.

## 1. The name

The desk, sign-in, page titles, emails, SMS templates, the monthly page, evidence packs and the docs
now say **GeoGuard**. Some code names stay as they were until after the jury, so nothing in a running
setup breaks:
- the `lake_protect` Python package and the `lp` command;
- the `LP_` settings;
- the Docker project, images and volumes (`lakeprotect`);
- the repository folder.

Evidence packs sealed before the rename still say "Lake Protect API" inside, and they still verify:
the name is part of what was sealed.

**A note on the name.** GeoComply sells a product called GeoGuard (VPN and proxy detection, for
streaming and gaming). The owner chose the name knowing this. Check the trademark before any
public launch.

## 2. Kinds of land

`api/app/categories.yaml` lists every kind of land GeoGuard knows. Each kind has:
- its asset types;
- its custodians;
- where its boundary comes from;
- the changes that matter;
- the kind of boundary it has.

| Kind | Status | Types | Boundary kind |
|---|---|---|---|
| Lakes and water bodies | Watched now | Lake or tank (cheruvu, kunta) | Full tank level (FTL), with a buffer and the 100 m watch ring |
| Government land | Watched now | Revenue land (survey number), agency land (surveyed), recovered land | Parcel, with the 100 m watch ring and no buffer |
| Endowment land | Planned | Endowment land | Parcel |
| Forest land | Planned | Forest land | Parcel |
| Places reported by citizens | Made from reports (D-063) | Place reported by a citizen | A 50 m circle around the pin; not watched until the admin starts it; cannot be added by hand |

The two planned types are already in the database (migration 0008). The desk shows them, greyed
out, with what each still needs. The API refuses to add a location of a planned kind. To switch one
on:
1. Set `status: live` in `categories.yaml`. No migration is needed.
2. Do everything on its `needs` list:
   - **Endowment land:** the Endowments Department's land register by survey number, a connector
     for it, leased and licensed land (so lawful use is not flagged), and the department's
     officials with their areas.
   - **Forest land:** notified forest block boundaries, detection rules tuned for dry deciduous
     forest (leaf fall looks like clearing), approved diversions and felling permissions, a
     connector, and the department's officials.

Detection is the same for every kind: land-cover change from Sentinel-2, with radar for built-up.
The legal check and incidents also work the same way. The kind decides:
- how the boundary is drawn (a lake gets a buffer);
- the label on every screen;
- the "by kind of land" line on the overview.

## 3. Adding a location (admin)

**Where:** Locations, then **Add a location**. A location is always added to the real data and must
lie inside Telangana. Demo data is never screened.

**Steps:**
1. Pick the kind of land and the type.
2. Give a name, in English and optionally in Telugu.
3. Give the district, which is needed so the right officials are told (D-059). The mandal, village,
   survey numbers and custodian are optional.
4. Give the **baseline date**. Changes first seen on or before it are recorded as older changes and
   never open an incident. It defaults to the policy cut-off of 19 Jul 2024.
5. Give the **outline**, either way:
   - **Draw it** on the Sentinel-2 base map. Click each corner, then Finish. The base map covers
     Hyderabad.
   - **Upload a file**: GeoJSON or KML (Google Earth), longitude and latitude. Use this anywhere in
     the State.
6. Say where the outline comes from, then **Start watching**.

**Checks, made before anything is stored:**
- **A drawn outline is for watching only.** Its status is "derived" (estimated, cohort D), so its
  changes go to the watch list and never lead to field action (CONTEXT.md rule 2).
- **Allowed statuses for an uploaded outline:**

  | Kind | Statuses |
  |---|---|
  | Lake | physically marked, final notification, preliminary notification, derived |
  | Land | physically marked, surveyed by the agency, survey number only, derived |

  A confirmed status needs the reference of the notification, order or survey.
- **Size:** at least 2,000 sq m and at most 50 sq km. Sentinel-2 sees 10 m pixels, and the smallest
  change it reports is 1,000 sq m.
- **The same place is not added twice.** If the outline overlaps a watched location by half or more
  (intersection over union), it is refused. The desk links to that location, where a new boundary
  version is the right step.
- **Area check:** the form shows the outline's area in sq m and acres as soon as it is drawn or
  uploaded.

**What happens on adding:**
1. The location becomes an asset with boundary version 1. Its buffer (lakes only) and watch ring
   are derived as for any record.
2. The asset key is `loc-<name>`, and the location records who added it and when.
3. A "watching started" row is logged.
4. It goes into `/pipeline/watchlist`, so the next `lp screen` includes it.
5. The audit log records `location.added`.

## 4. Removing a location: stop watching

Nothing about a location is ever deleted. Boundaries are append-only in the database, and the
location's weekly records, incidents, documents and evidence packs are the record of what happened.
"Remove" is therefore **Stop watching**, with a reason.

When a location stops being watched:
- the next weekly screen leaves it out;
- it is not counted as watched on the overview, in the weekly digest or on the monthly page from
  that day;
- its open incidents stay open and still need a decision. The desk says how many before you stop;
- the Locations list hides it unless "Show locations no longer watched" is ticked. The overview
  still lists it while it has incidents.

**Watch again** reverses it, also with a reason. It needs a boundary in force.

Every start and stop is a row in `monitoring_changes`. The row records who, when and why, and it is
append-only. The database lets `assets.monitored` change only through such a row. The audit log
records `location.watch_stopped` and `location.watch_resumed`.

## 5. Files

| Part | File |
|---|---|
| Kinds of land, limits | `api/app/categories.yaml`, `api/app/categories.py` |
| Migration: planned types, `monitored`, `monitoring_changes`, guards | `api/migrations/versions/0008_locations.py` |
| Adding, checks, stopping and resuming | `api/app/services/locations.py` |
| API | `api/app/routers/assets.py` |
| Watched only | `routers/pipeline.py`, `services/dashboard.py`, `notify/digest.py`, `bulletin/stats.py` |
| Desk | `web/src/desk/AddLocation.tsx`, `web/src/desk/Assets.tsx` (kinds, filter, the watch panel), drawing in `web/src/components/MapView.tsx` |
| Tests | `api/tests/test_locations.py` (21), `api/tests/test_dashboard.py`, `e2e/tests/m14-locations.spec.ts` |

**API.**
- `GET /categories`
- Admin only:
  - `POST /assets`;
  - `POST /assets/outline-check`;
  - `POST /assets/{id}/monitoring`.
- `GET /assets/{id}/monitoring`

## 6. Not built yet

- Editing a location's name, area or custodian after it is added. A new boundary version already
  works (`POST /assets/{id}/boundaries`).
- Shapefile upload. Convert it to GeoJSON or KML first.
- A base map outside Hyderabad for drawing. `lp basemap` can make one for a wider area.
- Filtering the overview and the incident list by kind of land.
