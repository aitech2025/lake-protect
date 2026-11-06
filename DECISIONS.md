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

## Defaults changed
