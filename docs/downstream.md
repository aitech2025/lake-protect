# The downstream layer: notifications and the dashboard (M13)

Built 25 November 2026. It covers everything after an incident is created:
- who is told about it, and how;
- whether they acknowledged it;
- what happens when they do not;
- the weekly summary each official gets;
- the overview from State to lake.

The owner chose the scope (DECISIONS.md D-059 and D-060):
- notify officials by area;
- add a drill-down dashboard.

Not in this build: feeds to department systems, a weekly report page per district, and citizen reporting.

## 1. The three layers

```
DATA SOURCES (M11)          PROCESSOR (M12)                    DOWNSTREAM (M13)
government records    ──►   weekly screen of every asset  ──►  notify the area's officials
become assets and           change found: incident opened       inbox, email, SMS, WhatsApp
boundaries                  legal check, plain words            acknowledge, remind, tell the admin
                                                                weekly digest per official
                                                                overview: State > district > mandal
                                                                > village > lake > incident
```

## 2. Who is told

**Areas.** The admin gives each official one or more areas: a whole district, or one mandal within a district. Names match without regard to case or spaces.

| Event | Who is told | Acknowledgement |
|---|---|---|
| A new incident stays open | Officials whose area holds the asset, and every admin | Needed |
| The legal check closes a change at once (outside the zones, before the baseline, authorised works) | No one: it appears in the weekly digest | |
| A change is seen again on an open incident | No one: it appears in the weekly digest | |
| The admin confirms or dismisses an incident | The area's officials and every official who reviewed it | Not needed |
| 24 hours without acknowledgement, incident still open or under review | The same person again (a reminder, once) | Needed |
| 48 hours without acknowledgement from an official | Every admin, once | Not needed |
| A weekly screen is stored | Every official with an area, and every admin: the week's digest | Not needed |

- **No official covers the area.** The incident reaches the admin, and the message says so.
- **Seeing is not restricted.** Everyone can still open every incident and every area. Areas decide who is told, not who may look.

**Acknowledging.** There are three ways:
- the inbox's Acknowledge button;
- recording a review (an official);
- taking a step on the incident (the admin).

Acknowledging one notification about an incident also acknowledges its reminder.

**When a request lapses.** Once the incident is confirmed, dismissed or closed, the request drops out of the inbox count. It still counts as "not acknowledged within 24 hours" on the dashboard.

## 3. How they are told

| Channel | In this build | To switch it on |
|---|---|---|
| In the app | Always on. Every notification is in the person's inbox, with a count in the side bar | Nothing |
| Email | Written to the outbox folder in storage (`outbox/email/<date>/`), so nothing leaves the machine | Set `LP_EMAIL_TRANSPORT=smtp` and the `LP_SMTP_*` values for the State's mail relay |
| SMS | Template: every message is **held** | A gateway agreement, plus a sender header and template registered on a DLT platform (TRAI's commercial communication rules). Set them in `api/app/notify/channels.yaml` and the token in `.env` |
| WhatsApp | Template: every message is **held** | An agreement with a WhatsApp Business solution provider or the State's MeeSeva on WhatsApp channel, with approved templates. Set them in `channels.yaml` and `.env` |

**Rules.**
- Demo data never leaves the machine. It is skipped on SMTP, SMS and WhatsApp, even when they are set up.
- A held message is never sent later. Once a channel is set up, only new messages go out on it.
- A failed attempt is retried after 5 minutes, up to three attempts.
- SMS carries only the incident code, the asset, what changed and the link. Each value is cut to the 30 characters DLT allows.

Each delivery attempt is one append-only row, with a masked address (`d***@…`, `+91******0001`), its status and the reason. The admin's **Officials** page shows:
- whether each channel is ready;
- each person's contact details, channels and areas;
- the delivery log.

**What a message says.** Every message gives:
- the incident code;
- the asset and its village, mandal and district;
- the incident's plain sentence ("Land fill of about 4,474 sq m inside the boundary, first seen 11 Nov 2026");
- warnings for a court case or an unconfirmed boundary;
- a link to the desk.

It never names an owner or claimant. It never says whether a change is lawful, and never says what to do on the ground. Officials who chose Telugu get Telugu messages; the Telugu wording is a draft for review by a native speaker.

## 4. The weekly digest

After each weekly screen, every official gets one digest for their area, and the admin gets one for everything. It covers:
- the lakes and parcels watched;
- how many were seen clearly, and which had no clear look;
- each change found that week, with its incident, marked when it is a change seen again;
- new incidents;
- what waits for the reader: reviews for an official, decisions for the admin;
- incidents open for more than 14 days.

There is one digest per person, per week and per dataset. A second screen in the same week sends none. The admin can send it from the Officials page.

## 5. The overview (dashboard)

The **Overview** is now the home page for both roles. Levels:

**State > district > mandal > village > lake or parcel > incident.**

At every level:

| Figure | Counted as |
|---|---|
| Lakes and parcels watched | Assets in the area, and how many have a confirmed boundary |
| Seen clearly this week | The latest week's record says "No change seen" or "Change found" |
| With a change this week | The latest week's record says "Change found", including changes seen again |
| New incidents this week | Opened in the latest week, not closed at once by the legal check |
| Awaiting review / under review / confirmed | The incident's state |
| Waiting over 14 days | Open or under review for more than 14 whole days (the monthly page's rule) |
| Acknowledged within 24 hours | Officials' new-incident notifications in the last 30 days |

**Every underlined number opens the incidents behind it.** The incident list takes the same area and rule (`/alerts?district=…&mandal=…&state=OPEN`, `&waiting=true`, `&week=2026-W48`), and a test checks the counts agree.

**The page** also shows:
- a map of the area's lakes coloured by their status, each colour with a word in the legend;
- the last 8 weeks as two bar charts (assets with a change, new incidents), each with a table view;
- a row per district, mandal, village or lake.

A level that no asset in the area records is skipped. The real lakes have no village, so a mandal lists its lakes directly. Assets with no district appear as "Area not recorded". Officials get "My area" shortcuts.

**Where the real lakes' areas come from.** Government records carry district, mandal and village (M11's data contracts). The 99 OpenStreetMap lakes do not, so `lp assets-areas` places each lake in OpenStreetMap's district and mandal boundaries, by a point on its surface:
- all 99 are placed, in 5 districts and 27 mandals;
- the saved Overpass response is `data/sources/overpass_admin_orr.json`;
- each lake is marked `area_source: OpenStreetMap administrative boundaries (not the revenue record)`, and the overview says so.

## 6. Files

| Part | File |
|---|---|
| Tables: contacts and channels on users, `official_areas`, `notifications`, `notification_deliveries` | `api/migrations/versions/0007_notifications.py` |
| Routing by area | `api/app/notify/routing.py` |
| Events, acknowledgement, follow-up, digests, outbox | `api/app/notify/service.py` |
| Message text, English and Telugu | `api/app/notify/messages.py` |
| Email, SMS and WhatsApp | `api/app/notify/channels.py`, `channels.yaml` |
| The digest | `api/app/notify/digest.py` |
| The notifier (every minute) | `api/app/notify/__main__.py`; `notifier` service in `docker-compose.yml` |
| Overview figures | `api/app/services/dashboard.py` |
| API | `api/app/routers/notifications.py`, `dashboard.py`, `users.py` |
| Desk | `web/src/desk/Dashboard.tsx`, `Inbox.tsx`, `Officials.tsx`; the banner on the incident page |
| Real lakes' districts and mandals | `pipeline/lake_protect/osm_areas.py` (`lp assets-areas`) |

**API.**
- `GET /dashboard?dataset=&district=&mandal=&village=`
- `GET /notifications`, `/notifications/count`, `POST /notifications/{id}/ack`
- Admin only:
  - `GET /notifications/deliveries`, `/notifications/channels`;
  - `POST /notifications/digests`, `/notifications/run`;
  - `GET /users`, `PATCH /users/{id}`, `PUT /users/{id}/areas`, `GET /areas`.

**Safeguards.**
- A notification is never deleted or edited. The database allows only its acknowledgement, once.
- Delivery attempts are append-only.
- Contact details are seen only by the admin. The audit log records that they changed, never their values.
- Every view of the inbox, the dashboard and the delivery log is logged.

## 7. Running it

```powershell
docker compose up -d --remove-orphans                    # starts the notifier with the API
docker compose logs notifier                             # reminders, escalations, outbox runs
docker compose exec api python -m app.notify tick        # follow-ups and outbox, once
docker compose exec api python -m app.notify digest --dataset real
C:\lp-cache\venv\Scripts\lp assets-areas                 # districts and mandals for the real lakes
```

Emails written in file mode are in the storage volume: `docker compose exec api ls /var/lp/storage/outbox/email`.

## 8. Tests

- **API:**
  - `tests/test_notifications.py`: 20 tests on routing, wording, acknowledgement, lapsing, follow-up, channels, retries, the DLT template, digests and the admin routes;
  - `tests/test_dashboard.py`: 5 tests on each level, skipping a level, datasets, acknowledgement and the count check against the incident list;
  - additions to the demo seed, real asset and pipeline tests.

  308 passed in all, with a test that a failing digest never fails a stored run.
- **Pipeline:** `tests/test_osm_areas.py`; 29 passed.
- **Browser:** the walkthrough (`m9-demo`) now starts at the overview, drills down to a village, opens the incidents behind a number, checks the inbox, reviews (which acknowledges) and checks the admin's Officials page. With `m10-real` and `m11-sources`, 4 tests pass.

## 9. Not built yet

- **Feeds to department systems:** OGC API Features and GeoJSON for department GIS, and signed webhooks.
- **A weekly report page per district.**
- **Delivery receipts:** read receipts and delivery reports from SMS and WhatsApp gateways.
- **Further escalation:** after the admin, to a senior officer. There is no such role now (D-057).
- **Citizen reporting** (CONTEXT.md 17.8).
