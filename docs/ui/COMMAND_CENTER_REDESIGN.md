# GeoGuard command-centre UI redesign

## Design intent

The web application now uses a map-first, tactical geospatial command design system. Dark Command is the default; Light Audit is available from the shared top bar and persists as a local preference. The map remains the full-bleed workspace while the layer drawer and asset inspector float above it.

## Main workspace

- Shared top command bar: GeoGuard identity, jurisdiction context, global search, service status, theme/language controls and signed-in officer.
- Left HUD: official/cadastral boundaries, lake FTL/buffer, AI screening overlays, incident pins, imagery mode placeholders, severity summaries and priority alert feed.
- Centre: MapLibre operational map, asset category filters, detection-date filter, legend, zoom, measurement, pitch and swipe comparison controls.
- Right inspector: selected asset/case reference, operational state, changed area, priority score, change class, first-observed date, sensor basis, location, officer and links into the existing case/asset workflows.

## Existing pages

The shared navigation, page surfaces, typography, form controls, tables, status pills, queue/map presentation and responsive shell have been moved to the same dark/light design tokens. Existing case-management, legal record, evidence-pack, audit, monthly report, login, and citizen/field workflows retain their API contracts and role permissions.

## Data and evidence honesty

- The overview consumes existing `/assets` and `/alerts` APIs; it does not manufacture asset records.
- Demo records remain marked by the existing DemoBand.
- A priority score is not presented as AI confidence.
- The baseline/latest swipe currently compares boundary-only and latest detection-overlay map layers. It is not a historical satellite raster comparison. Historical raster pairing requires an imagery timeline API and licensed imagery URLs.
- The date selector filters recorded detection events, not satellite acquisition passes. A true pass-date selector requires scene acquisition metadata to be exposed by the API.
- The 3D control changes map pitch; a DEM/terrain source is not yet connected.
- Distance measurement is a geodesic map estimate and is not a cadastral survey measurement.
- SAR and hybrid imagery choices are visibly disabled until those providers and render pipelines are integrated.
- Asset boundary and AI screening overlays are visual decision support. They are not a legal finding or an automated enforcement decision.

## Build validation

The GitHub Actions workflow includes a dedicated `web-build` job that runs `npm ci` and `npm run build` (TypeScript plus Vite). API/PostGIS and pipeline tests remain in the same workflow.
