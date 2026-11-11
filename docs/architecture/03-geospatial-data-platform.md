# 03 — Geospatial Data Platform

## 1. Source tiers
**Routine screening:** Sentinel-2 optical imagery for water/vegetation/built-up context; Sentinel-1 SAR for cloud-independent complementary observations; suitable open elevation/hydrography/land-cover layers.

**Targeted investigation:** NRSC/ISRO products, approved state geospatial datasets, commercial archive/tasking imagery and authorised aerial/drone surveys subject to data access, licensing, budget and permissions.

Use broad-area lower-cost screening followed by targeted higher-resolution review. Sentinel-2 at 10 m is not reliable for every small structure, wall or individual building. Never promise structure-level detection without appropriate resolution and validation.

## 2. Scene catalogue
Adopt STAC metadata; use a STAC API or pgSTAC when collection size and query patterns justify it. Record provider/collection, stable item ID, sensor/platform, acquisition time, footprint, CRS, resolution, cloud/quality, bands/assets, licence, provider/object URI, checksum, ingestion time and processing state.

Catalogue presence does not imply image suitability. Validate coverage, cloud/shadow, haze, temporal spacing, SAR noise/geometry and seasonal context.

## 3. Storage
Use S3-compatible object storage (approved cloud or MinIO). Store source imagery, derived products, COGs, image chips, field photos and evidence packs outside transactional Postgres. Keep metadata in STAC and relational records. Apply hot/warm/archive lifecycle policies. Never expire objects under case retention or legal hold.

Suggested object key layout: source/provider/collection/year/month/scene; derived/pipeline/tile/date; candidates/run/candidate; evidence/case/object; exports/department/export.

## 4. Ingestion workflow
Discover → validate metadata/coverage/licence → register scene → download or register remote asset → checksum/deduplicate → preprocess → create COG/derived products → water/built-up/land-cover analysis → create change geometries → intersect assets/parcels/boundaries → temporal deduplication → risk triage → human review.

Each stage is restartable and idempotent. Persist status, attempts, errors, timestamps, input/output IDs and correlation ID. Retry transient failures with backoff. Quarantine invalid/licence-incompatible assets. A failed stage must never create a false “no change” result.

Broker-neutral event names: SCENE_DISCOVERED, SCENE_VALIDATED, SCENE_REGISTERED, PREPROCESSING_COMPLETED, OBSERVATION_CREATED, CHANGE_DETECTION_COMPLETED, SPATIAL_INTERSECTION_COMPLETED, RISK_ASSESSMENT_COMPLETED, ALERT_CANDIDATE_CREATED, FIELD_VERIFICATION_REQUESTED and VERIFICATION_COMPLETED. Events carry IDs, schema version, correlation ID, run/source reference, geographic scope and timestamps; never send raster bytes through the broker.

## 5. GIS processing
Use GDAL for conversion/reprojection/mosaics/COGs; Rasterio for windowed Python access; ESA SNAP where required for Sentinel-1; GeoPandas/Shapely for vector processing; PostGIS for indexed spatial joins; GeoServer for OGC services when required; MapLibre for browser maps.

Operations include reprojection/grid alignment, optical cloud/shadow masking, SAR calibration/terrain correction as appropriate, seasonal water normalisation, mosaicking, windowed clipping, COG generation, geometry repair and spatial overlay. Do not load full large scenes into memory unnecessarily.

## 6. Geographic tiling and matching
Use a stable geographic tiling scheme. Process a scene/tile once, then intersect candidate geometries against all relevant assets and parcels with GiST-indexed PostGIS. Store source candidate geometry separately from clipped/intersection geometries. Preserve overlap area, spatial relation, source IDs and boundary version. Deduplicate detections across neighbouring tiles and overlapping scenes.

An intersection does not prove encroachment. Possible causes include authorised works, seasonal change, existing structures, georegistration error, boundary dispute or model error.

## 7. Temporal correctness
Store last clear observation, first changed observation, subsequent persistence observations, sensor/quality and imagery gaps. A date bracket bounds the event; it is not an exact start date. Distinguish seasonal water spread from permanent filling/land conversion using multi-season history, hydrological context and field verification. Persistence thresholds are configurable by asset type and model version.

## 8. Map delivery
Use vector tiles for asset/boundary/alert polygons and COG range requests or raster tile services for imagery. Cache by layer/version/time. Apply role/jurisdiction filtering before serving protected features. Limit bounding-box queries and exports. Keep map delivery independent from raster processing.

## 9. Operational metrics
Track asset boundary quality, authoritative-vs-derived boundary share, imagery coverage, cloud/quality rejection, ingestion lag, provider errors, processing time, spatial match latency, duplicate rate, before/after adequacy and review turnaround. Expose distinct states: not observed, no usable scene, processing failed, processed with no candidate, candidate found.

## 10. Integrations
Each provider/department adapter defines auth, rate limits, retries, schema mapping, licence, incremental cursor, timestamp semantics, reconciliation and failure owner. Do not label an integration live until access, schema, data rights, refresh SLA and operational owner are confirmed.