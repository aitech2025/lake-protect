# 01 — Statewide Platform Architecture

## 1. Product definition
Lake Protect should evolve into a Telangana Public Asset Protection Platform: a geospatial intelligence and operational case-management system for lakes, tanks, reservoirs, canals, drainage channels, government land and other notified public assets.

It is not simply a satellite viewer, lake inventory or automated encroachment-verdict engine. It connects:
1. What asset is protected? A stable registry of assets, parcels, custodians, boundaries and legal references.
2. What changed, where and when? Time-stamped satellite, aerial, field and authorised signal observations.
3. What does the change intersect? Applicable versioned boundaries, parcels, notifications, permits, works, disputes and court references.
4. Who acts next? Analyst review, department routing, field verification, legal scrutiny, official decision, escalation and reporting.

The first operational deployment can remain lake-focused and HYDRAA-oriented. The architecture must not make HYDRAA the only agency, lakes the only asset type or Hyderabad the only geography.

## 2. Design principles
- Geospatial-first: every asset, parcel, observation, candidate and boundary has validated spatial identity and CRS.
- Evidence-first: each alert is reconstructable from source observations, processing metadata, boundary/rule versions and human decisions.
- Human-in-the-loop: model output is a screening signal, not a legal conclusion.
- Multi-department: responsibility is configured by jurisdiction, asset category, statutory role and effective date.
- Temporal correctness: preserve valid-time and recorded-time history.
- Interoperability: use versioned APIs and open geospatial formats.
- Graceful degradation: asset, alert, case and evidence access continues during imagery/ML outages.
- Portable and open: target approved government hosting while avoiding unnecessary proprietary lock-in.

## 3. System context
Inputs: approved satellite scenes, government asset/parcel records, legal notifications, permits and authorised works, field observations, approved aerial data and permitted citizen signals.

Processing: ingestion and validation; asset registry and boundary versioning; raster/vector analysis; change detection; spatial intersection; transparent triage; human review.

Outputs: candidate queue, department assignment, field task, legal case file, officer decision record, audit trail, coverage dashboard and monthly reports.

## 4. Logical architecture
| Layer | Responsibilities | Recommended technology |
|---|---|---|
| Experience | State/department dashboards, GIS, Asset 360, case desk, field app | React/TypeScript, MapLibre GL JS, responsive PWA |
| Application | Identity, registry, parcels, boundaries, alerts, cases, evidence, analytics | FastAPI modular application |
| Geospatial | Spatial query, raster/vector processing, tiles and intersections | PostGIS, GDAL, Rasterio, GeoPandas, Shapely, GeoServer as needed |
| Intelligence | Water, built-up, land-cover change and risk triage | Python workers; PyTorch, scikit-learn, XGBoost as validated |
| Data | Transactional records, imagery catalogue, object storage, cache, events | PostgreSQL/PostGIS, STAC/pgSTAC, S3-compatible storage, Redis |
| Integration | Satellite providers and approved departmental feeds | Adapter interfaces, scheduled sync, reconciliation |
| Operations | Deployment, security, telemetry, backup and DR | Docker; Kubernetes for production scale; CI/CD and IaC |

## 5. Deployment topology
Run stateless API instances behind a load balancer. Keep PostgreSQL/PostGIS as the system of record. Store large raster and evidence objects in S3-compatible storage. Run raster and ML workers separately from transactional APIs. Use a scheduler/orchestrator for ingestion and recurring jobs. Serve maps through cacheable vector/raster tiles, not large API payloads.

A modular monolith is the right starting point for transactional domains. Extract raster ingestion and inference first because they have distinct resource profiles. Do not start with dozens of microservices.

## 6. Geographic processing
A satellite scene may cover many lakes and parcels. Discover and ingest it once, preprocess by scene/tile, run relevant products, store candidate geometries, and intersect those results with all relevant assets using indexed PostGIS queries. Deduplicate across overlapping scenes and tiles. This is the primary statewide scaling optimisation.

## 7. Asset coverage
Design the registry to support lakes/tanks (FTL, buffer, catchment, feeder channels), reservoirs/dams/canals, government land classifications, forest blocks, endowment and Wakf properties, parks/open spaces, nalas/drainage, municipal/road/institutional land and approved industrial/infrastructure parcels. Category-specific legal rules remain separate.

## 8. Illustrative scale envelope
| Dimension | Pilot | Regional | Statewide planning envelope |
|---|---:|---:|---:|
| Assets | 100–500 | 2,000–10,000 | 10,000–50,000+ |
| Registered users | 20–50 | 200–500 | 1,000–5,000 |
| Concurrent users | 10–20 | 50–100 | 200–500 |
| Raster/object storage | 1–5 TB | 10–30 TB | 50–200 TB+ |

These are planning ranges, not measured requirements. Actual sizing depends on area, resolution, revisit, scene count, derived products, retention and map traffic. Benchmark before procurement.

## 9. Degradation states
The UI must distinguish no change detected, no suitable imagery, observation completed, processing failed, not onboarded/not monitored and candidate found. Never display “no encroachment” when no valid observation exists.

## 10. Rollout
1. Foundation: asset registry, administrative hierarchy, parcels, boundaries, identity, audit and GIS.
2. Intelligence: satellite catalogue, ingestion, COG storage, detection, spatial matching and provenance.
3. Operations: analyst review, routing, field verification, case workflow, evidence and escalation.
4. Hardening: security, HA/DR, load tests, model monitoring and integrations.
5. Expansion: districts, departments and asset categories in controlled waves.

HYDRAA may be an operational partner in its notified jurisdiction. Elsewhere, route to the competent custodian and authority only after legal and administrative verification.