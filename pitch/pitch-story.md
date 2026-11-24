# Lake Protect: executive deck, story and design brief

Prepared 24 November 2026 for the TISC 2026 jury round. Redesigned the same day as a visual deck: real satellite imagery, real app screenshots, icons and diagrams in place of text tables.

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

## Slides

| # | Section | Headline | Visual |
|---|---|---|---|
| 1 | Title | A weekly satellite watch that reaches the field, and cases that hold up | Full-bleed Sentinel-2 mosaic of Hyderabad |
| 2 | Problem | Hyderabad has lost 61% of its lake area, and the watch has not kept up | 61% with a 10-drop pictograph; four stat cards |
| 3 | 1 | Encroachment takes six forms, and each leaves a different trace | Six icon cards, each tagged with the sensor that catches it |
| 4 | 1 | Act while the change is still reversible | Five-stage timeline with icons; the alert window bracketed |
| 5 | 1 | Screen every lake weekly, sharpen only where it matters | Three tiers with pixel-size pictograms; index colour key |
| 6 | 1 | Every alert dates the change | Real Sentinel-2 before and after pair, 70 days apart |
| 7 | 2 | One core decides what deserves an officer's time | Channels in, core flow, portals out, with icons |
| 8 | 2 | Officers get the picture, the dates and what was checked | Real desk screenshot (Kapra lake) and the Telugu field app on a phone |
| 9 | 3 | A legal check runs before anyone moves | Decision ladder with coloured outcomes; boundary-status key |
| 10 | 3 | Six rules no one can switch off | Six icon cards, each with how it is enforced in code |
| 11 | 3 | Controls cut 124,203 changed pixels to 58 candidates | Funnel bars (log scale) from the real screen |
| 12 | 4 | Optical, radar and sub-metre imagery, each with one job | Four sensor cards with resolution and source |
| 13 | 4 | An open, portable stack the State can host and own | Four layers marked Built; Pilot and Later cards |
| 14 | 4 | Already screening 99 real Hyderabad lakes | Six metrics beside the 99 lakes drawn on the mosaic |
| 15 | Next | Each phase must earn the next | Four-phase timeline with gates and costs; pilot targets; stop conditions |
| 16 | Close | Recovered land stays recovered, and every action stands up in court | Lakes mosaic; four-step icon chain |
| A1–A4 | Appendix | Detection rules; boundary status; built, pilot and later; monthly page | Icon lists and the monthly-page screenshot |

About 9 minutes in total, plus time for a live demo.

## Where the images come from

All imagery is the project's own. There is no stock photography.

- **Satellite backgrounds** (`img/hero-hyderabad.jpg`, `img/lakes-wide.jpg`, `img/lakes-tall.jpg`) are stitched from the app's offline Sentinel-2 base map (zoom 14, clear scenes from 29 September to 14 October 2026). The 99 lake outlines come from `data/assets.geojson` (OpenStreetMap). Each slide carries "Contains modified Copernicus Sentinel data 2026" and "© OpenStreetMap contributors".
- **Before and after pair** (`img/candidate-*.png`) is a real candidate chip from the 22 November screen. It is labelled as a candidate whose cause is not verified.
- **App screenshots** (`img/app-*.jpg`) were captured from the running prototype, read-only:
  - the analyst desk on the real Kapra lake alert;
  - the field app in Telugu on the demo world;
  - the monthly page on the demo world.

  The demo screens show the app's own purple "Demo data" band, and the slides label them as demo data.
- **Icons** are Lucide (ISC licence). **Fonts** are Manrope and Inter (SIL Open Font Licence). Both are embedded in `theme.css`, so the deck renders with no internet.

## How to rebuild

Run these in a scratch folder outside OneDrive:

```bash
npm install @marp-team/marp-cli@4.5.1 lucide-static@0.460.0 @fontsource/inter@5.1.0 @fontsource/manrope@5.1.0
```

Then, from the project root:

```bash
# 1. Only if the imagery or screenshots change
py -I pitch/build/mosaic.py C:/lp-cache/basemap/s2_2026-11-22.zip data/assets.geojson <work dir>
py -I pitch/build/deck_images.py <work dir> <screenshot dir>
# 2. Theme: inlines fonts and the icons the deck uses
py -I pitch/build/build_theme.py <scratch>/node_modules
# 3. PDF (use Chrome: Edge hung on this machine)
cd pitch && marp --no-stdin --theme ./theme.css --html --allow-local-files --browser chrome --pdf pitch-deck.md -o Lake-Protect-TISC-2026.pdf
```

Edit `build/theme.src.css`, never `theme.css`. Icons are written as `<i class="ic ic-NAME"></i>` with Lucide names; the theme build fails if a name does not exist.

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
| 61% lost; 15 years; 920 water bodies; 264 lakes under CCTV; 656 with no routine watch | Proposal; CONTEXT.md §16 |
| 765 of 3,342 lakes (23%) with a final notice | Proposal |
| 99 lakes, 7,652 looks, 14 days, 58 candidates, 25 refused by radar, 28 min | PROGRESS.md (M10) and `summary.json` |
| 124,203 → 102,758 → 8,750 pixels → 83 patches → 58 | Sums of `px_changed_any`, `px_alerting_type`, `px_kept`, `candidates` and `candidates_dropped_radar` in `summary.json` |
| 249 API tests and 15 browser tests | PROGRESS.md (M10) |
| Phases, gates, costs and pilot targets | Proposal (indicative estimates; targets, not results) |
