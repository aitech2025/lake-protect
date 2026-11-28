# GeoGuard frontend redesign plan

## Scope and constraints

Redesign the React presentation layer while preserving every route, API call, route parameter,
query-backed filter, form payload, loading/error state, MapLibre interaction, localization, and
existing role check. Do not change API contracts, backend rules, authentication/session logic, or
database behavior. The current project role model remains admin and viewer.

Design direction: an institutional geospatial operations console with ink navy navigation,
restrained teal actions, neutral map-paper workspace surfaces, compact readable tables, and
high-contrast semantic state colors. Use map canvases as actual product content, never static
illustrations in place of working maps.

## Route and feature preservation matrix

The application declares 21 route entries. The matrix groups `/report/track` and its reference
variant in one row because they share one page component; both route patterns remain registered.

| Route | Existing data/API | Existing actions and interactions to preserve |
|---|---|---|
| /login | GET /auth/demo-users; login handled by the auth provider | Select demo user, sign in, switch language, pending/error states |
| /report | GET /citizen/config, /citizen/otp, /citizen/otp/verify, POST /citizen/reports | Public citizen report form, location pinning, GPS, photos, OTP, report acknowledgement |
| /report/track, /report/track/:ref | GET /citizen/reports/{ref} | Track by reference, show current incident status and response |
| /dashboard | GET /dashboard with URL-backed geographic filters | State → district → mandal → village → asset drill-down, KPI links, weekly trend |
| /map | GET /assets | MapLibre asset boundaries/pins; click an asset to open Asset 360 |
| /inbox | GET /notifications, GET /notifications/count, POST /notifications/{id}/ack | Pending/all filter, acknowledge one/all, live badge refresh |
| /officials | GET /users, /areas, /notifications/deliveries; notification run/digest and user/area updates | Admin user management, jurisdiction assignments, delivery/outbox actions |
| /alerts | GET /alerts, GET /assets, /screening/runs | Incident state/type/cohort/geography filters, URL-linked filters, map pins and incident links |
| /alerts/:id | GET /alerts/{id}, reviews, transitions, imagery request, evidence pack, citizen reports | Review, attributable state transitions, sharp-imagery request, evidence generation/download, related citizen reports |
| /reports | GET /reports, POST /reports/intake | Status filters, map, manual intake, evidence/location submission |
| /reports/:id | GET /reports/{id}, POST /reports/{id}/place | Review citizen report, resolve location on map, accept/decline/request details, existing workflow links |
| /assets | GET /assets, /categories, /reports, asset monitoring/boundary/register endpoints | Lakes/lands/citizen tabs, district filtering, add location, boundary versions, monitoring controls, asset selection |
| /assets/:id | Asset, boundaries, weeks/images, incidents, documents, inspections, audit endpoints | Asset 360 tabs; map/boundary provenance, weekly imagery, linked cases, legal documents, inspection evidence, audit |
| /records | GET /records/{kind}, /assets, import endpoint | Legal/asset record tabs, asset association, document import and validation |
| /sources | GET /sources, /sources/runs, POST /sources/{name}/runs | Configure/preview source runs and inspect run results |
| /satellites | Satellite source CRUD/history endpoints | Manage active imagery sources and review configuration history |
| /monthly | GET /bulletins/{month} | Month selection, visual summary, print |
| /audit | GET /audit, /audit/closure-sample, /audit/verify | Audit filtering/view, closure sample, chain verification |
| /whatsapp-test | Citizen config and simulator endpoint | Admin-only opt-in conversation simulator, map pin, reset/replies |
| /citizen-operations | GET /citizen/operations and existing action endpoints | Intake/review operations and channel status |

## Existing shared UI and dependencies

- App.tsx owns the route table; Layout.tsx owns protected navigation and notification count.
- auth.tsx owns session token, current user, logout, and role behavior. Keep it unchanged.
- MapView.tsx owns MapLibre, local Sentinel-2 tiles, boundary certainty styles, incident changes,
  marker click handlers, and drawing. Preserve spatial data/layers and interaction contracts; only
  presentation styles may change.
- Bits.tsx, PageState.tsx, and labels.ts are shared controls, state labels, and loading/error patterns.
  Refactor presentation without removing their data semantics.
- English and Telugu messages live in i18n/en.json and te.json.
- Page-specific styles live in styles.css, dashboard.css, monthly.css, portal.css, and
  whatsapp-test.css.

## Implementation sequence

1. Add shared design tokens and accessible baseline controls, table, status, panel, and empty/error
   treatments.
2. Replace the protected-app shell with a responsive collapsible navigation rail, contextual
   topbar, route breadcrumb, user menu, notification entry, language switch, and mobile navigation.
3. Apply the shared system to command centre, map/explorer, asset registry/Asset 360, incident and
   citizen workflows, records, sources, satellite settings, reports, admin, audit, and monthly
   views. Keep page data hooks and submit handlers intact.
4. Give the public portal and authentication pages a matching but separately composed entry shell.
5. Add focused UI regression coverage for routes, role-hidden navigation, forms, and map pin
   navigation; run the existing frontend build and end-to-end suite.

## Accessibility and responsive checks

Keep semantic headings, native form labels, visible focus indicators, keyboard-operable navigation,
text/icon alternatives for status, reduced-motion support, contrast checks, and non-color state
labels. Check desktop, tablet, and narrow mobile widths. Ensure map controls and contextual panels
remain reachable when the sidebar collapses or becomes a mobile drawer.

## Completion record — 27 November 2026

- Applied the redesign across the protected desk, authentication, public citizen portal, map, asset
  registry and Asset 360, incidents, reports, records, administration, satellite settings, audit,
  and monthly bulletin. The route table, API contracts, auth provider, role checks, and backend were
  left intact.
- Reworked the shared shell and responsive navigation, centralized visual tokens and control
  styles, updated English and Telugu strings, and aligned login/public pages with the same visual
  system. MapLibre remains the live map implementation; asset pins are keyboard-operable buttons
  and navigate to the selected Asset 360 record.
- Improved page-level error headings, filter semantics, global search failure/retry behavior,
  keyboard focus for long notification content, and contrast on report states and dashboard
  summaries.
- Added browser coverage for viewer/admin navigation, global search retry, asset search and details,
  map pin navigation, public report tracking and error states, desktop/tablet/mobile overflow, and
  route rendering. Automated axe checks cover all 21 route entries at 1440, 768, and 390 pixels
  against WCAG 2.1 AA tags.
- Verification: the Docker production web build succeeded and all 12 Playwright tests passed on a
  reset, isolated QA Compose stack seeded with the 99 real lake assets and a replayed weekly screen.
  `git diff --check` reported no whitespace errors. The web build still reports the existing
  large JavaScript chunk warning (about 1.72 MB minified); this does not block the build.
- The m14 and m15 browser checks were updated for the current Asset 360 route and candidate-asset
  lifecycle. Unknown citizen locations remain incident candidates until official verification;
  the UI test no longer treats a candidate as a registered asset that can be removed from the
  registry.
