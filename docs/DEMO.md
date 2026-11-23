# Ten-minute demo (CONTEXT.md section 14)

For senior officials. Plain words throughout. The desk shows two worlds, switched in its side
bar, never mixed on one screen:

- **Hyderabad lakes (real data):** 99 real lakes, real Sentinel-2 images, real changes found by the
  screen from space. Outlines are from OpenStreetMap, so every real alert stops at the watch list.
- **Demo world (fictional):** invented places and records, used to show the full loop to an officer.

**No accuracy figure exists yet.** The blind backtest (Gate 1, section 8.6) has not been run. Never
call a real change an encroachment, and never suggest the detection has been shown to work. Say:
"The screen runs on real images today. How often it is right is being measured on past cases
before anyone relies on it."

## Before the meeting

```powershell
docker compose up -d --build                                   # once, with internet
docker compose exec -e LP_ALLOW_RESET=true api python -m app.seed.reset   # fresh demo, dated today
```

Then put the real screen back, because the reset rebuilds the database (no internet needed):

```powershell
$env:LP_PIPELINE_TOKEN = "<value from .env>"
C:\lp-cache\venv\Scripts\lp replay reports\screen\2026-11-22
```

The laptop then needs no internet: the map tiles (demo and Sentinel-2), image pairs, fonts and app
are all local. To refresh the real screen with the newest scenes, run `lp screen` the day before,
with internet.
Open http://localhost:8180 in Chrome or Edge. For the phone view, open a second window at the same
address and use the browser's device toolbar (a narrow phone width).

## Opening: real data (three minutes)

| # | Screen and clicks | Say |
|---|---|---|
| R1 | Sign in as **Admin**. In the side bar choose **Hyderabad lakes (real data)**. Open **Assets**. Point at the blue strip: date of the screen, lakes watched, clear looks, lakes seen clearly. | "These are 99 real lakes up to the ORR, on real satellite images from the European Copernicus programme, screened on this laptop. Where a lake was not seen clearly, the system says so; it never claims a lake is untouched." |
| R2 | Open **Alerts**. Open the alert at **Kapra lake** (or the highest-priority one). Point at the two images and "When the change happened". | "A real change: vegetation in the lake bed, then bare ground, first seen on this date, with the last clear image before it." |
| R3 | Same screen: **Images used** (Sentinel-2 scenes and dates) and **What the system checked** (boundary estimated, watch only). | "HYDRAA started restoring Kapra lake in June 2026. This is why a works register is checked before anyone moves: your own works must not raise an alarm. And because this outline comes from OpenStreetMap, not an official FTL, the system will not send anyone. Share the boundary files and the works register, and this same alert becomes actionable or closes itself." |
| R4 | Switch the side bar to **Demo world (fictional)**. | "Now the full loop, on invented places, because real cases need your boundaries first." |

## The script (demo world)

| # | Screen and clicks | Say |
|---|---|---|
| 0 | Sign-in page. Point at the purple band. | "Everything you will see is demo data: invented places and records." |
| 1 | Sign in as **Admin** (or Nodal officer). Open **Assets**: the map of 20 lakes and parcels. | "Every lake and recovered parcel, screened weekly, on free satellite data." |
| 2 | Sign out, sign in as **Analyst**. Open **Demo Cheruvu 1** from the alert list. Point at the two images and the "When the change happened" strip. | "The same place on two dates. Last clear on one date, first changed on another." |
| 3 | Same screen: the **What the system checked** panel and the boundary badge (solid line: confirmed). | "Before anyone is sent out, the system checks the boundary, permits, works and court cases." |
| 4 | Alert list, filters: **With legal** (Demo Cheruvu 7, court case), **Closed** (Demo Cheruvu 3, restoration work), **Watch list** (Demo Kunta 5). | "These stop here. A court case goes to the legal team. Your own restoration work does not raise an alarm." |
| 5 | Back on Demo Cheruvu 1: **Confirm the change**, tick "I compared the before and after images", Confirm. Sign in as **Nodal officer**, **Assign to a field officer**: Demo Field Officer 1. | "A person reviews it, and a named officer owns it with a deadline." |
| 6 | Phone window: sign in as **Field officer 1** (opens in Telugu). Tick **Demo: no signal**. Open the alert, add a photo, "Demo: position, at the site", Get my position, "The change is there", Save. Show "1 visit waiting to send". Untick no signal: it sends itself. | "The field team sees one clear alert, even without signal." |
| 7 | Desk, **Legal officer**: Demo Cheruvu 1, fill the **case-readiness checklist**, **Generate evidence pack**, **Open PDF**, **Check integrity**. | "The file an officer needs, sealed so any change can be detected." |
| 8 | **Nodal officer**: Mark the case file ready, Send to the officer. **Legal officer**: Officer record, fill the notice and order references, **Save and record the action**. | "The system stops here. An officer makes every legal decision." |
| 9 | **Auditor**: Audit, **Check the log**. | "Nothing closes quietly. Two people, every step logged." |
| 10 | **Senior officer**: lands on the Monthly page. **Print one page**. | "This is the one page you see each month." |

## What to say if asked

- **"Are these real satellite images?"** On the real-data side, yes: Sentinel-2 at 10 m, with the
  scene name and date under every image, and Sentinel-1 radar to confirm built-up. On the demo
  side, no: they are drawn at the same 10 m detail and marked "synthetic".
- **"How accurate is it?"** Not known yet. The blind backtest on past public cases answers that, and
  the result will be shown whatever it is. What we can say: on five tuning lakes, every change it
  raised was at the two lakes where HYDRAA reported works in 2026, and it raised nothing at the
  other three (reports/m2-tuning/README.md).
- **"Can it see a shed or a wall?"** No. Sentinel-2 cannot reliably see anything under about 10 by
  10 metres. Those need sharper images on a cue, or a field visit, which the design provides.
- **"Is the certificate ready to file?"** No. It is a template marked "Draft for counsel review"
  until counsel settles the wording and who signs Part B.
- **"Can it work on our officers' phones?"** Yes, as a web app with no app store. Real phones need the
  system served over HTTPS, which the laptop demo does not set up.
- **"Where are the Telugu screens checked?"** The Telugu text is a draft for a native speaker to review.
