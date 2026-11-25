# Ten-minute demo of GeoGuard (CONTEXT.md section 14)

Say once at the start: "GeoGuard is the platform you shortlisted as Lake Protect. It now covers
government land too, with endowment and forest land next."

For senior officials. Plain words throughout. The desk shows two worlds, switched in its side
bar, never mixed on one screen:

- **Telangana (real data):** 99 real lakes, real Sentinel-2 images, real changes found by the
  screen from space. Outlines are from OpenStreetMap, so every real incident is flagged "boundary
  not confirmed".
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
Open http://localhost:8180 in Chrome or Edge.

## Opening: real data (three minutes)

| # | Screen and clicks | Say |
|---|---|---|
| R1 | Sign in as **Admin**. In the side bar choose **Telangana (real data)**. The **Overview** groups the 99 lakes by district and mandal; click **Medchal–Malkajgiri**. Then open **Locations**. Point at the blue strip: date of the screen, locations watched, clear looks, locations seen clearly. | "These are 99 real lakes up to the ORR, on real satellite images from the European Copernicus programme, screened on this laptop. Where a lake was not seen clearly, the system says so; it never claims a lake is untouched." |
| R2 | Open **Incidents**. Open the incident at **Kapra lake** (or the highest-priority one). Read its first line, then point at the two images and "When the change happened". | "A real change: vegetation in the lake bed, then bare ground, first seen on this date, with the last clear image before it." |
| R3 | Same screen: **Images used** (Sentinel-2 scenes and dates), **What the system checked**, and the "boundary not confirmed" flag. | "HYDRAA started restoring Kapra lake in June 2026. This is why a works register is checked: your own works must not raise an alarm. And because this outline comes from OpenStreetMap, not an official FTL, the incident is flagged. Share the boundary files and the works register, and this same change is judged against them, or closes itself." |
| R3a | **Locations**: point at **Endowment land** and **Forest land** (planned; open one to show what it needs). **Add a location**, **Government land**, draw four corners on the map, **Finish outline**: the area appears. Name it, give the district, **Start watching**. Then **Stop watching** with a reason, and point at **Started and stopped**. | "The admin adds any public land to the weekly watch in a minute. A drawn outline is for watching only; a notified one needs its reference. Nothing is ever deleted: stopping is recorded, with who and why." |
| R4 | Switch the side bar to **Demo world (fictional)**. | "Now the full loop, on invented places, because real cases need your boundaries first." |

## The script (demo world)

| # | Screen and clicks | Say |
|---|---|---|
| 0 | Sign-in page. Point at the purple band. | "Everything you will see is demo data: invented places and records." |
| 1 | Sign in as **Official 2** (viewer). The desk opens on the **Overview**. Click **Demo North District**, then **Demo Mandal 1**. On **Demo Village 1**, click the number under **Awaiting review**. | "From the State down to a village: what was seen this week, what is open, what has waited too long. Every number opens the incidents behind it." |
| 1a | Open **Inbox** (the count in the side bar). Point at the new incident at Demo Cheruvu 1, its reminder, and "Email: sent, WhatsApp: held". | "Each official is told about their own area, and must acknowledge. No reply in a day: a reminder. Two days: the admin is told. SMS and WhatsApp switch on once the State's gateway exists." |
| 1b | Open **Locations**, click **Demo Cheruvu 1**: the **Week by week** strip and the **Legal documents**. | "Every lake, every week: seen clearly or not, the week's image, and what changed. Its notification and orders sit with it." |
| 2 | Open **Incidents**, then **Demo Cheruvu 1**. Read the first line aloud ("Land fill of about ... inside the boundary, first seen ..."). Point at the two images and the "When the change happened" strip. | "It says plainly what changed: construction, land fill, levelling or clearing. The same place on two dates." |
| 3 | Same screen: **What the system checked** and the boundary badge (solid line: confirmed). | "Before anyone looks, the system checks the boundary, permits, works and court cases." |
| 4 | Same screen: **Your review**: "A real change", a note, **Record review**. The incident moves to **Under review**, and the blue "You were notified" banner goes. | "The officials review it. Their note is kept, and the review counts as acknowledging." |
| 5 | Incidents list: **What changed: Levelling** (Demo Parcel C), then **Dismissed** (Demo Cheruvu 6), **Closed** (Demo Cheruvu 3, "Closed by the legal check"), and **Court case** on Demo Cheruvu 7. | "Restoration works close themselves. A court case is flagged for the legal team." |
| 5a | Sign in as **Admin**. Open **Officials**: who covers which district, how each is told, and the delivery log. | "The admin sets each official's area. Every message and its delivery is on record." |
| 5b | Open **Citizen reports**. Point at the report at **Demo Cheruvu 1** (Telugu, from the portal, with a photo) and the one from WhatsApp that follows it. Both joined the satellite incident already open there. Open it: what the citizen read at each step, and "updates go to a verified phone": the number itself is never shown. | "Citizens report on the web, on WhatsApp, or through 1070 and Praja Vani. They get a reference at once, and a note at each step in their language. A report never makes a finding: it asks officials to look." |
| 6 | Demo Cheruvu 1: **Confirm: a real change**, with a note. **Generate evidence pack**, **Open PDF**. | "The admin decides, with a reason. The officials of the area are told. The file is sealed so any change can be detected." |
| 7 | **Locations**, Demo Cheruvu 1, **Add a document**: a court order reference. | "Every legal paper for a lake stays with the lake." |
| 8 | **Audit**, **Check the log**. | "Nothing closes quietly. Every step is logged and chained." |
| 9 | **Monthly page**: new incidents, reviewed, confirmed, and those waiting over 14 days. **Print one page**. | "This is the one page you see each month." |
| 6a | **Citizen reports**, the Demo Cheruvu 1 report: now **Closed**, "officials confirmed a change". Click **Open the public portal**, **Check a report**, paste its reference, choose **తెలుగు**. | "The citizen who reported it is told, in their own language, without anyone naming who did it." |
| 6c | On the public portal (demo), drop the pin on the east edge of **Demo Kunta 7**, choose "Soil or debris", **Send report**. Then on the desk open **Citizen reports**, the new reference, **Open incident**: the satellite review says **A change is visible**, with before and after images. In the officials' panel: **Acknowledge** (the citizen now reads "an official is reviewing it"), add a note, pick a date two months back and **Look on this date**, then **Look now**; tick the two looks to compare them side by side (no change then, fill now). **Attach the legal records**, **Request a sharper image** (it waits for the admin), then **Approve** with a note. Sign in as the admin: approve the sharper image and **Close** with a note. | "Any report opens a case. The app finds the place and looks at the newest satellite images at once; here it found fill the weekly screen had not reached yet. Any official can acknowledge it, compare satellite looks by date, pull the legal records at the spot and decide, with a note at each step; the admin approves anything that costs money. The citizen sees each step." |
| 6b | **Citizen reports**, **WhatsApp (demo)**: send `hi`, `1`, share a location on the map, `2`, `SKIP`, `SKIP`, `NO`. | "The same report by WhatsApp, one question at a time. It goes live when the State connects its WhatsApp number." |
| 10 | Sign out, sign in as **Official 1**: the desk opens in Telugu. | "Officials work in Telugu." |

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
- **"Who uses it?"** Two roles: an admin who runs it and decides on each incident, and officials who
  see everything and record their reviews. Field visits and legal action happen outside the system.
- **"Where are the Telugu screens checked?"** The Telugu text is a draft for a native speaker to review.
