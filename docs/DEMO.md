# Ten-minute presentation of GeoGuard (CONTEXT.md section 14)

Say once at the start: "GeoGuard is the platform you shortlisted as Lake Protect. It now covers
government land too, with endowment and forest land next."

For senior officials. Plain words throughout. **Everything on screen is real data** (DECISIONS.md
D-065):
- 99 real lakes;
- real Sentinel-2 images;
- real changes found by the screen from space.

Outlines are from OpenStreetMap, so every real incident is flagged "boundary not confirmed". The
fictional demo world was removed. The sign-in accounts are role accounts, not people.

**No accuracy figure exists yet.** The blind backtest (Gate 1, section 8.6) has not been run.
- Never call a real change an encroachment.
- Never suggest the detection has been shown to work.

Say: "The screen runs on real images today. How often it is right is being measured on past cases
before anyone relies on it."

## Before the meeting

```powershell
docker compose up -d --build                                              # once, with internet
docker compose exec -e LP_ALLOW_RESET=true api python -m app.seed.reset   # real lakes + role accounts
$env:LP_PIPELINE_TOKEN = "<value from .env>"
C:\lp-cache\venv\Scripts\lp replay reports\screen\2026-11-22             # the real incidents, no internet
```

**What needs internet:**
- **The desk:** nothing. Map tiles, image pairs, fonts and the app are all local.
- **Satellite reviews and looks** of citizens' reports: these need the `reviewer` service
  (`docker compose --profile screen up -d reviewer`). Without internet they stay "waiting for the
  satellite review". Say so if asked.
- **The newest scenes:** to refresh the real screen, run `lp screen` the day before.

Open http://localhost:8180 in Chrome or Edge. **After the meeting, reset and replay again:** the
steps taken during the presentation are records.

## The script

| # | Screen and clicks | Say |
|---|---|---|
| 1 | Sign in as **Admin**. The **Overview** groups the 99 lakes by district and mandal; click **Medchal–Malkajgiri**. Then open **Locations**. Point at the blue strip: date of the screen, locations watched, clear looks, locations seen clearly. | "These are 99 real lakes up to the ORR, on real satellite images from the European Copernicus programme, screened on this laptop. Where a lake was not seen clearly, the system says so; it never claims a lake is untouched." |
| 2 | Open **Incidents**. Open the incident at **Kapra lake** (or the highest-priority one). Read its first line, then point at the two images and "When the change happened". | "A real change: vegetation in the lake bed, then bare ground, first seen on this date, with the last clear image before it." |
| 3 | Same screen: **Images used** (Sentinel-2 scenes and dates), **What the system checked**, and the "boundary not confirmed" flag. | "HYDRAA started restoring Kapra lake in June 2026. This is why a works register is checked: your own works must not raise an alarm. And because this outline comes from OpenStreetMap, not an official FTL, the incident is flagged. Share the boundary files and the works register, and this same change is judged against them, or closes itself." |
| 4 | **Locations**: point at **Endowment land** and **Forest land** (planned; open one to show what it needs). **Add a location**, **Government land**, draw four corners on the map, **Finish outline**: the area appears. Name it, give the district, **Start watching**. Then **Stop watching** with a reason, and point at **Started and stopped**. | "The admin adds any public land to the weekly watch in a minute. A drawn outline is for watching only; a notified one needs its reference. Nothing is ever deleted: stopping is recorded, with who and why." |
| 5 | Sign out; sign in as **Official 2** (Medchal–Malkajgiri and Sangareddy). Open **Inbox**: the incidents in their districts, "Email: sent, WhatsApp: held". Open the Kapra lake incident: **Your review**, "Needs a site visit", a note, **Record review**. | "Each official is told about their own area, and must acknowledge. No reply in a day: a reminder. Two days: the admin is told. Their review and note are kept." |
| 6 | Sign in as **Admin**. **Officials**: who covers which district, how each is told, the delivery log. Back on the Kapra lake incident: **Dismiss**, note "HYDRAA restoration works", then **Close** with a note. | "The admin decides, with a reason, and the officials of the area are told. Here the change is the State's own restoration, so it is dismissed, and that reason is on record." |
| 7 | Open the public portal (**Citizen reports**, **Open the public portal**). Drop the pin on **Mallampet Cheruvu**, choose "Soil or debris", add a line, **Send report**: the reference. | "Citizens report on the web, on WhatsApp once the State connects it, or through 1070 and Praja Vani. They get a reference at once. A report never makes a finding: it asks officials to look." |
| 8 | On the desk: **Citizen reports**, the new reference, **Open incident**. In the officials' panel: **Acknowledge**, add a note, pick a date two months back and **Look on this date**, then **Look now** (with internet, tick the two looks to compare them side by side). **Attach the legal records**, **Request a sharper image** (it waits for the admin). | "Any official can acknowledge it, compare satellite looks by date, and pull the legal records at the spot, with what is not connected yet listed plainly. The admin approves anything that costs money." |
| 9 | As the admin: approve the sharper image, then **Decline** (or **Approve**) with a note, and **Close**. On the portal, **Check a report**, paste the reference, choose **తెలుగు**. | "The citizen sees each step in their language: being reviewed, sharper images asked for, the outcome. Never the officials' notes, never who reported." |
| 10 | **Audit**, **Check the log**. Then **Monthly page**, **Print one page**. | "Nothing closes quietly. Every step is logged and chained. This is the one page you see each month." |
| 11 | Sign out, sign in as **Official 1**: the desk opens in Telugu. | "Officials work in Telugu." |

## What to say if asked

- **"Are these real satellite images?"** Yes: Sentinel-2 at 10 m, with the scene name and date under
  every image, and Sentinel-1 radar to confirm built-up.
- **"How accurate is it?"** Not known yet. The blind backtest on past public cases answers that, and
  the result will be shown whatever it is. What we can say: on five tuning lakes, every change it
  raised was at the two lakes where HYDRAA reported works in 2026, and it raised nothing at the
  other three (reports/m2-tuning/README.md).
- **"Can it see a shed or a wall?"** No. Sentinel-2 cannot reliably see anything under about 10 by
  10 metres. Those need sharper images on a cue, or a field visit, which the design provides.
- **"Is the certificate ready to file?"** No. It is a template marked "Draft for counsel review"
  until counsel settles the wording and who signs Part B.
- **"Who uses it?"** Four personas (D-067): a district officer reviews incidents in their districts
  and sends a field officer, who reports from the place with photos and GPS; the district officer
  recommends, and a senior official approves and closes. The admin maintains the application and
  takes no step on an incident. Legal action happens outside the system.
- **"Who are these accounts?"** Role accounts, not people. Real officials' accounts come with the
  State's sign-in (not built yet).
- **"Where are the Telugu screens checked?"** The Telugu text is a draft for a native speaker to review.
