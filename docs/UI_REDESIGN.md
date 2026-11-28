# GeoGuard desk and portal: survey-sheet design system

**Date:** 28 November 2026
**Replaces:** the Civic Slate refresh of 26 November 2026 (three stacked override layers in `styles.css`).
**Scope:** presentation layer of `web/` only. No API, database, workflow, role or decision change.

## Direction

- **Product.** A Telangana government desk where officials review weekly Sentinel-2 evidence of
  physical change at lakes and government land, and a public page where citizens report a place.
- **Character.** Exact, accountable, unhurried. Evidence, not accusation.
- **World.** Survey sheets and satellite passes: graphite paper, survey-ink blue, the revenue map's
  boundary lines.
- **Where the colour goes.** The satellite imagery itself: the overview map with status pins, the
  before/after chips on an incident, the Sentinel-2 mosaic on the sign-in page. Chrome stays neutral.
- **Signature.** Line style encodes certainty everywhere a boundary or a source appears: solid is
  confirmed or authoritative, dashed is preliminary or derived, dotted is estimated or unverified.
  It is used by the boundary seal, the map, the sign-in legend, the registry's source authority and
  the brand mark (a water body inside its dashed full-tank-level line).

## Tokens (`web/src/styles.css`, section 1)

| Role | Light | Dark |
|---|---|---|
| App background / surface / raised | `#f1f2ef` / `#ffffff` / `#eceeea` | `#0d1110` / `#141918` / `#212826` |
| Text primary / secondary / muted | `#18211d` / `#4a5550` / `#66706b` | `#e8ecea` / `#aab3ae` / `#8a948f` |
| Accent (survey ink) | `#1d4f91` | `#8fb3e8` |
| Status ink: open / review / ok / info | `#a8342b` / `#8a5300` / `#22684a` / `#1d4f91` | toned equivalents |

- Hairlines are the text colour at 9–17% opacity. Shadows are neutral and small.
- Type: IBM Plex Sans (400/500/600) for the interface, IBM Plex Mono for codes, hashes, weeks and
  coordinates, Noto Sans Telugu for Telugu. All self-hosted; no external font request (offline desk).
- Radii: 6 controls and tags, 8 buttons and inputs, 12 panels and tables, 14 the workspace frame.
- Motion: one easing curve `cubic-bezier(0.22, 1, 0.36, 1)`; 140 ms for feedback, 220–320 ms for
  entrances. Everything respects `prefers-reduced-motion`; Motion runs under
  `MotionConfig reducedMotion="user"`.
- Theme: light, dark or match device, from the account menu (stored per browser as `lp.theme`).
  Map and imagery colours are data colours and do not change with the theme; the monthly map keeps
  the colours the server draws with, and its legend uses exactly those values.

## Shell

- Sidebar (252 px) on the app background; the workspace is one raised panel holding the top bar
  and the page. Collapsible to a 68 px icon rail (kept per browser as `lp-nav-collapsed`).
- Tablets (761–900 px) always get the icon rail; phones get a sheet from the left with a scrim.
- Sidebar foot: status of the latest weekly screen (date, locations seen clearly, rule version),
  from `/screening/runs`.
- Top bar: section and page, search, inbox with unacknowledged count, language, account menu
  (theme and sign out).
- Search is a combobox (pattern adapted from a 21st.dev command palette): locations, incidents,
  citizen reports and pages the person can open; arrow keys, Enter, Escape, Ctrl K. A source that
  fails is named and can be retried on its own.
- Pages are code-split by route; sign-in does not load the map library.

## Components (`web/src/components`)

`Segmented` (toggles or tabs with a sliding thumb), `Drawer` (side sheet with focus trap and
Escape), `GlobalSearch`, `BrandMark`, `EmptyState`, skeleton `PageState`. Existing `BoundarySeal`,
`StatePill`, `AuthImage`, `MapView` (now follows its container's size and hides crowded labels
until hover) are kept. Icons are lucide line icons at 16–18 px.

## Pages added for API features that had no screen

- **Registry** (`/registry`, both roles; changes admin-only, enforced by the API): registered public
  assets from `/api/v1/platform/assets` with source authority, footprint and responsible departments;
  reported places (`/candidate-assets`) clearly labelled as unverified, with their review priority
  score when one exists; departments, with admin forms to add a department, grant or revoke a
  person's access, add a registered asset and record a responsible department.
- **System status** (`/system`, admin): the `/readiness` checklist (never presented as a production
  certification), detection model versions with evaluations, approve and promote (with
  confirmation, API rules unchanged), an evaluation form, and pipeline processing runs.

## Known limits

- `/api/v1/platform/candidates/{id}/predictions` returns 500 on a database without the
  `candidate_predictions` table; the page shows the score as unavailable.
- The department API has no member listing, so access can be granted and revoked but not listed.
- nginx serves `/assets/` as static files, so refreshing an Asset 360 page (`/assets/<id>`) returns
  404 in the container build. The route needs a separate static prefix or an nginx rule; not changed
  here because it is infrastructure.
