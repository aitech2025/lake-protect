# Ten-minute demo (CONTEXT.md section 14)

For senior officials. Plain words throughout. **Everything on screen is demo data**: fictional
places, people and records in a fictional world. Nothing shown is a finding.

**No detection result exists yet.** The blind backtest (Gate 1, section 8.6) has not been run, so do
not open with a result and do not suggest the detection has been shown to work. Say: "This shows how
the loop works. Whether the satellite screening finds real changes is being tested separately, on
past cases, before anyone relies on it."

## Before the meeting

```powershell
docker compose up -d --build                                   # once, with internet
docker compose exec -e LP_ALLOW_RESET=true api python -m app.seed.reset   # fresh demo, dated today
```

The laptop then needs no internet: the map tiles, image pairs, fonts and app are all local.
Open http://localhost:8180 in Chrome or Edge. For the phone view, open a second window at the same
address and use the browser's device toolbar (a narrow phone width).

## The script

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

- **"Are these real satellite images?"** No. They are drawn for the demo at the same 10 m detail as
  the free Sentinel-2 data, and every image is marked "synthetic". The real pipeline is next.
- **"How accurate is it?"** Not known yet. The blind backtest on past public cases answers that, and
  the result will be shown whatever it is.
- **"Is the certificate ready to file?"** No. It is a template marked "Draft for counsel review"
  until counsel settles the wording and who signs Part B.
- **"Can it work on our officers' phones?"** Yes, as a web app with no app store. Real phones need the
  system served over HTTPS, which the laptop demo does not set up.
- **"Where are the Telugu screens checked?"** The Telugu text is a draft for a native speaker to review.
