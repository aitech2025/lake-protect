# Decisions

Choices that change, or fill a gap in, `CONTEXT.md`. `CONTEXT.md` itself is not edited.

## Owner instructions that override CONTEXT.md

### D-001: Build order changed by the owner (5 Nov 2026)
`CONTEXT.md` section 12 orders M0 to M9 and stops after M3. The owner's instruction is: M0, M1,
then M4 to M9 on demo data with demo image pairs, then M2 and M3, with the stop moved from after
M3 to after M9, and the backtest reported at the end.

**Reading applied:** build M0, M1, M4 to M9, stop and report, then build M2 and M3 and report the
backtest as section 8.6 requires.

**Conflict inside the instruction:** its "when to stop" list still says not to start M4 until the
owner replies "Continue to M4". M4 now comes before M3, so that line cannot apply. The goal line
wins. The section 8.6 report and the "partial result, not a Gate 1 pass" wording still apply at M3.

**Consequence to keep in view:** section 1 puts the backtest first because it shows whether
detection works before anyone sees a pitch. Under this order the demo exists before there is any
detection result, so section 14's "open with its real result" cannot be used yet, and the demo
must not imply that detection has been shown to work.

## Errors and gaps found in CONTEXT.md

### E-001: `boundaries` is append-only but has `valid_to` (section 7, invariant 12)
An append-only row cannot have `valid_to` filled in when a later version supersedes it.
**Applied:** `valid_to` is set only at insert, for a boundary known to expire. The end of a
superseded version is derived by the `boundary_versions` view (`superseded_by_id`,
`effective_valid_to`), and `supersedes_id` is checked by a trigger. No row is ever updated.

### E-002: The priority score has no cohort factor for D, E or F (section 6.4)
Section 6.4 gives A = 1.0, B = 0.9, C = 0.5 only. **Applied (config, `rules-v0`):** D = 0.0 and
F = 0.0, because watch-only alerts never reach review unless the asset moves cohort, at which point
the score uses the new cohort. E = 0.9, the same as B, because E is also ACTION mode on a surveyed
boundary. These are placeholders to agree with HYDRAA, not derived values.

### E-003: "Officer" in section 6.5 is not a role in section 2
`WITH_OFFICER` to `ACTION_RECORDED` and `CLOSED_NO_ACTION` name "Officer", which is not one of the
eight roles. **Applied:** `legal_officer` and `senior_officer` act as the officer. For
`CLOSED_NO_ACTION` the officer signs first and a `nodal_officer` co-signs.

### E-004: A live court matter found after the candidate stage has no route to `HOLD_LEGAL`
Section 6.1 says a live court matter moves an alert to `HOLD_LEGAL` "whatever the cohort", but
section 6.5 only has `CANDIDATE` to `HOLD_LEGAL`. **Applied:** a system step from any open state
to `HOLD_LEGAL`, run straight after a court register import. Assignment also re-checks the
register, so invariant 1 holds even if a case is added some other way.

### E-005: The `zone` enum has no value for the inside of a parcel
Cohort A parcels have a parcel boundary, not an FTL. **Applied:** the inside of a parcel is
reported as `inside_ftl`. The alert screen labels it by boundary kind.

## Gaps filled (no change to CONTEXT.md)

### D-010: Additions to the section 7 schema
- `users.username`, `users.is_demo`: login key, and only demo accounts can log in.
- `assets.asset_key`: stable external key (for example `osm-way-28131043`).
- `observations.is_demo`: synthetic demo images are never presented as Sentinel scenes.
- `boundaries.derived_from_id`, `created_at`: links a derived buffer or ring to its source row.
- `candidates.area_growth`: input to the priority score's growth factor.
- `legal_checks.boundary_id`, `boundary_version`, `flags`: section 6.2 says every result stores
  the boundary version used.
- `closure_requests`: holds the first signature of a two-person closure (section 6.5).
- `field_checks.client_uuid`: makes offline sync idempotent (section 9.5).

### D-011: A boundary version is a set
Version numbers count per asset. One version holds the defined boundary (FTL or parcel), a buffer
derived from it at the configured width (FTL only), and a watch ring 100 m beyond. All three are
stored rows with their own hash, so a later change to the configured widths cannot silently move
an existing zone. `sha256` is the SHA-256 of the stored geometry (PostGIS EWKB).

### D-012: Real assets come from OpenStreetMap, status `derived`
One Overpass query over the approximate ORR box. The response is saved in
`data/sources/overpass_water_orr.json` (with retrieval time and query) so the asset file can be
rebuilt offline. No government portal was queried.

**Result on 6 Nov 2026:** 163 named water bodies. 11 polygons match 6 of the 21 section 13 names:
- Durgam Cheruvu, Sunnam Cheruvu and Miyapur Cheruvu ("Miyapur water body") match one polygon each.
- Nalla Cheruvu (2), Pedda Cheruvu (4) and Mallampet Cheruvu (2) match several, and are left
  ambiguous rather than guessed.
- 15 names have no OSM polygon. Their geometry is not invented; they need hand-traced boundaries.

A name match does not confirm that a polygon is the lake in a press report. That is checked against
the source in M3. The recovered parcels in section 13 (Ailapur, Ameenpur, Puppalaguda, Quthbullapur)
have no public geometry and are not loaded.

### D-014: `baseline_date` of a real asset is its enrolment date
`baseline_date` is required. For a real asset it is the date its boundary was retrieved, so only
change after enrolment can alert (rule 3). The backtest sets its own per-case baseline and does not
read this value.

### D-015: Demo and test places are in open sea
Every fictional asset, test fixture and demo alert sits around 81.5 E, 14.5 N, in the Bay of Bengal
about 150 km offshore and inside UTM zone 44N. No invented alert can then coincide with a real lake,
parcel or person (section 13), and areas in EPSG:32644 still work. The demo base map is drawn from
the demo data, so the sea is never shown.

### D-016: How a candidate's zone is located
A candidate is in the most restrictive zone whose interior it overlaps: FTL or parcel, then buffer,
then watch ring. Touching a zone's edge does not count. The rule is applied against the boundary
version in force on the check date, and that version is stored.

### D-017: Release from legal hold
`HOLD_LEGAL` to `TRIAGE` needs the court register to show no live matter, plus a reason and a case
status reference. A watch-only asset is released to `WATCH_LIST`, because section 6.5 has no other
route that keeps it out of the field.

### D-018: Two-person closures
The first signature is stored in `closure_requests`. The second must come from a different user with
the co-signing role: analyst then reviewer (`CLOSED_NOT_REAL`), field officer then nodal officer
(`CLOSED_FALSE_ALARM`), officer then nodal officer (`CLOSED_NO_ACTION`). A database check forbids the
same person resolving their own request. Any other step on the alert supersedes an open request.

### D-019: What counts as a court register hit
A court case with a live status (`pending`, `interim_order`, `stay` or `undertaking`, configurable)
whose footprint intersects the candidate, or which names the asset with no footprint, or which shares
a survey number with the asset.

### D-020: Re-check from space
A new candidate that overlaps an alert closed by people (`CLOSED_NOT_REAL`, `CLOSED_FALSE_ALARM`,
`CLOSED_NO_ACTION`), and covers at least 90% of its area, reopens it to `TRIAGE`. Alerts closed by
the system (legacy, out of scope, authorised) never reopen. A new change on an alert that is still
open is recorded on that alert, not duplicated.

### D-021: Leaving the watch list
"A new boundary version with a confirmed status" is read as: a boundary version newer than the one
the legal check used, whose status's cohort is not watch-only. So a new preliminary notification
moves a cohort D lake to C (VERIFY), which allows a field check but no officer step.

### D-022: Owner claims
Accepted in `FIELD_CONFIRMED` and every later state. Claimant names are personal data, so only the
legal and nodal officers see them. A `private_title` claim inside the FTL or buffer changes the class
to `RESTRICTED_PRIVATE` by appending a legal check row.

### D-023: Pipeline ingest
"Pipeline" is not a role, so `POST /candidates` takes a shared secret (`LP_PIPELINE_TOKEN` in `.env`)
instead of a login. Ingest also refuses a candidate whose observations were acquired after its ingest
time, which backs up invariant 10.

### D-024: Missed timers and notification
A miss is recorded once per timer, by the scheduled job or, if the alert moves first, by the
transition itself. `escalation_level` only goes up. "Notify" means an audit event plus the overdue
flag in the queue for the named role. The prototype sends no email or SMS.

### D-025: Imagery request estimate
The stub records an area (candidate envelope plus 250 m) and a cost at the upper end of the section
8.1 reseller figures: $26 per sq km archive and $55 tasking. ISRO's cost is left blank. Nothing is
ordered.

### D-026: More append-only tables
`legal_checks`, `field_checks` and `officer_records` are append-only, and `alerts` cannot be
deleted. Corrections are new rows.

### D-027: Demo images are synthetic and look no sharper than Sentinel
Demo "before" and "after" chips are drawn from the fictional world file at 10 m per pixel and
enlarged with hard pixel edges, so the demo never suggests a resolution that free data cannot give.
Each chip carries "Demo data, synthetic image, not satellite data", and its observation row says the
same instead of a Copernicus licence notice. Field photos are labelled drawings.

### D-028: Telugu strings are drafts
`web/src/i18n/te.json` was drafted without a native speaker. It carries a `_review` note and must be
reviewed before any real use (section 9.2). The wording test checks Telugu stems for the banned words.

### D-029: Browser tests run in a Chromium-only container
The all-browser Playwright image is about 2 GB and this machine has about 16 GB free. The e2e image
installs Chromium only. Chromium treats `http://web` as a secure origin inside Docker, so the service
worker and geolocation behave as they do on localhost.

### D-030: Demo reset rebuilds the schema
Append-only tables cannot be emptied, by design. `python -m app.seed.reset` (guarded by
`LP_ALLOW_RESET=true`) migrates down to revision 0001, which keeps PostGIS, migrates up, reloads the
real assets and reseeds the demo relative to today's date.

### D-031: Two demo-only switches in the field app
On one laptop, airplane mode does not cut `localhost`, and the demo sites are fictional points in
the sea, so a real GPS fix is always far away. For demo users only, the field app shows:
- "Demo: no signal", which pauses sending so captures queue on the device;
- "Demo: position", which offers "at the site" or "200 m away" as simulated fixes.
A simulated fix is written into the field record's notes as "[Demo: simulated position]". Real
offline behaviour (service worker, IndexedDB queue, sync on reconnect) does not depend on these
switches and is tested with the browser's own offline mode.

### D-032: The field app needs HTTPS on a real phone
Service workers and GPS work only on a secure origin. `localhost` counts as one, so the demo works on
the laptop itself, and the browser tests reach the app as `http://localhost` from inside the web
container's network. Using a real phone over the network would need an HTTPS certificate. None is
set up in the prototype.

### D-033: Evidence pack details
- `counsel_reviewed` comes from server configuration (`LP_COUNSEL_REVIEWED_TEMPLATE`, default false).
  No screen or API call can set it. Until counsel signs off, every pack carries "Draft for counsel
  review" on the cover and on the certificate.
- The certificate is structure only: Part A lists the files and their SHA-256 hashes, and Part B has
  the expert's fields. The statements are "[Wording to be supplied by counsel]". No legal wording
  was invented. **Open legal question, for counsel (section 15):** the certificate wording, who may
  sign Part B, and how field checks avoid being a "survey".
- Field photos are hashed again when a pack is built. A photo that no longer matches its arrival
  hash stops the pack.
- Claimant names are left out of the pack (personal data). The pack lists the claim types only.
- `lp verify-pack` lives in the pipeline package and uses the standard library only. It was written
  apart from the pack builder, so the check does not share the builder's assumptions. Given the
  manifest hash recorded in the database, it also catches a manifest rewritten to match an edited file.
- The PDF cannot contain its own hash. `manifest.json` lists the PDF's hash, and the database and
  audit log hold the manifest's hash.

### D-034: How the monthly figures are counted
Section 9.4 names the figures but not their rules. Applied:
- **Watched:** assets with a boundary in force by the end of the month.
- **New alerts:** alerts created in the month, not counting ones the legal check closed straight
  away (outside the boundary, before the baseline, or authorised).
- **Seen on site:** alerts that moved from field assignment to `FIELD_CONFIRMED` in the month.
- **Officer actions recorded:** alerts that reached `ACTION_RECORDED` in the month.
- **Overdue:** alerts in a timed state past their due date at the end of the month, or now for the
  current month.

Every figure is worked out by replaying the audit log up to the cut-off, so last month's page shows
last month's position. Real lakes and demo assets are never mixed on one page.

### D-035: "Overdue by officer" when nobody owns the alert
Only field assignment names an owner. For the other timed states the page names who must act: review
is the "Analyst desk", a field-confirmed case awaiting its file is the "Nodal officer (case file)",
and a case with the officer is the "Officer".

### D-036: The worker does escalation only, for now
The worker container runs the escalation job every 5 minutes. The weekly re-check from space needs
the detection pipeline (M2 and M3), so it is not scheduled yet. The reopen logic it would feed
already exists and is tested at ingest (D-020).

## Defaults changed
