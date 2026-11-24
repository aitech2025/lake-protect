# Lake Protect: executive deck, story and design brief

Prepared 24 November 2026 for the TISC 2026 jury round.

The deck follows the four sections the owner asked for. It is a jury deck, not a fundraising deck, so it has no team, market-size or raise slides. The facts come from these sources, not from a founder interview:

- the shortlisted proposal;
- `CONTEXT.md`;
- `PROGRESS.md`;
- the real screen of 22 November 2026 (`reports/screen/2026-11-22`).

## 30-second commercial

Hyderabad has lost 61% of its lake area since 1979. Telangana can already see its lakes from space; what it lacks is a loop that turns each new change into a dated, checked case that an officer owns and a court accepts. Lake Protect works in four steps:

1. It screens every lake weekly from satellite.
2. It runs a legal check before anyone is sent out.
3. It sends a field officer with a Telugu app that works offline.
4. It seals the result in a hash-verified evidence pack.

It already screens 99 real Hyderabad lakes. The next step is a blind backtest on 30 public cases.

## Headlines

The headlines alone should tell the story.

| # | Section | Headline | Class |
|---|---|---|---|
| 1 | Title | Lake Protect: a weekly satellite watch that reaches the field, and cases that hold up | lead |
| 2 | Why | 61% of Hyderabad's lake area lost between 1979 and 2024 | big-number |
| 3 | 1 | Encroachment takes six forms, and each leaves a different trace | table |
| 4 | 1 | Screen every lake weekly, sharpen only where it matters | steps |
| 5 | 1 | Every alert dates the change: last clear image, first changed image | real image pair |
| 6 | 2 | One core decides what deserves an officer's time | architecture diagram |
| 7 | 3 | A legal check runs before anyone moves | table |
| 8 | 3 | Six rules no one can switch off | grid |
| 9 | 3 | Controls cut 124,203 changed pixels to 58 candidates | metrics + list |
| 10 | 4 | Optical, radar and sub-metre imagery, each with one job | table |
| 11 | 4 | An open, portable stack the State can host and own | grid |
| 12 | 4 | Already screening 99 real Hyderabad lakes | metrics |
| 13 | Next | Each phase must earn the next | steps |
| 14 | Close | Recovered land stays recovered, and every action stands up in court | lead |
| A1 | Appendix | Detection rules, and what is live today | table |
| A2 | Appendix | Boundary status decides what an alert may do | table |
| A3 | Appendix | What exists, what the pilot adds, what comes later | table |

## Timing

About 8 minutes in total, plus time for a live demo:

- slides 1–2: 30 seconds;
- section 1: 2 minutes;
- section 2: 1.5 minutes;
- section 3: 2 minutes;
- section 4: 1.5 minutes;
- close: 30 seconds.

## Design notes

- Each content slide carries a small section label (for example "1 · Encroachment and how we detect it") instead of a separate divider slide. This keeps the deck short.
- Slides 3, 7 and 10 are reference tables and go over the 30-word guideline. That is deliberate: the owner asked for these details. Everything else stays near 30 words.
- Slide 5 uses a real Sentinel-2 pair from the prototype's own screen. It is labelled as a candidate whose cause is not verified, and the lake is named only in the speaker notes.
- Speaker notes are in the Marp source as HTML comments. They hold the sources, the caveats and the numbers not shown on the slides.

## Owner's architecture sketch and the improvements made

The owner's layout is kept: channels on the left, core processing in the middle, portals on the right. These changes were made:

1. **Government records added as a channel.** Without FTL notices, permits, authorised works, court cases and survey numbers, the legal check cannot run.
2. **Ground signals added as a channel.** HYDRAA's 900 CCTV cameras and lake guards feed the same intake. Calls to 1070 and Praja Vani complaints enter through the web app.
3. **"Mobile app" is the officer field app.** It works offline in Telugu, both bringing photos in and taking tasks out. Citizens report through WhatsApp and the web, with nothing to install.
4. **The legal check and the evidence seal are highlighted in the core.** Nothing is routed to a field team before the legal check, and every case ends in a sealed pack.
5. **Three outputs added beside the two portals:** the evidence pack, the leadership monthly page and notifications.
6. **The citizen portal shows status only.** It never shows the person accused or any owner names.
7. **A feedback loop.** Field outcomes tune detection, and only verified outcomes ever count as truth.

## Checks before sending

Every number on the slides was checked against its source:

| Figure | Source |
|---|---|
| 61% lost; 15 years | Proposal; CONTEXT.md §16 |
| 765 of 3,342 lakes (23%) with a final notice | Proposal |
| 99 lakes, 7,652 looks, 14 days, 58 candidates, 25 refused by radar, 28 min | PROGRESS.md (M10) and `summary.json` |
| 124,203 changed pixels | Sum of `px_changed_any` in `summary.json` |
| 249 API tests and 15 browser tests | PROGRESS.md (M10) |
| Phases, gates and costs | Proposal (indicative estimates) |
