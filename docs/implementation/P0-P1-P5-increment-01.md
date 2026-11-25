# P0/P1/P5 implementation increment

Branch: `feat/p0-p1-p5-geospatial-integrations`

This increment is additive. It preserves the current FastAPI/PostGIS case-management plane and the citizen web app.

## Added in this increment

### P0 — detection and backtest foundations

- STAC search for Sentinel collections with acquisition date, cloud-cover, asset-availability and age suitability checks.
- Sentinel-2 MNDWI spectral baseline and binary water mask output.
- Sentinel-1 VV backscatter threshold screen. Inputs must already be calibrated, terrain-corrected dB products; this is not a SNAP preprocessing workflow.
- GeoJSON case/detection evaluator with area eligibility, temporal constraints before public action, one-to-one spatial matching, precision, recall and F1.
- CLI entry point: `lp-geo` with `search`, `mndwi`, `sar-water`, and `backtest` commands.

Example:

```bash
cd pipeline
pip install -e '.[geo,dev]'
lp-geo search --collections sentinel-2-l2a --bbox 78.2,17.2,78.7,17.6 --start 2025-01-01 --end 2025-02-01
lp-geo backtest data/ground-truth/cases.geojson data/outputs/detections.geojson --output reports/backtest.json
```

Ground-truth GeoJSON must use EPSG:4326 coordinates. Each case should include `area_acres`, `event_date`, and `public_action_date`; detections should include `detected_at`. This is an initial scoring utility, not yet a statistically governed blind-backtest runner. It does not establish the required 30-case gate or model accuracy.

### P1 — geospatial processing foundation

- Optional geospatial dependencies remain isolated from the transactional API.
- Dedicated `pipeline/Dockerfile.geo` image for raster workers.
- STAC scene suitability decisions are serialisable for later registration through the existing `/api/v1/ingestion/scenes` endpoint.
- COG output is verified via GDAL IMAGE_STRUCTURE metadata; a normal GeoTIFF is not silently accepted as a COG.

Not yet included: production scheduler, CDSE authenticated Sentinel-1 acquisition, object-store download/cache manager, scene tiling, STAC API server/pgSTAC deployment, TiTiler, end-to-end run registration, and retryable distributed processing. These need environment/provider decisions and integration tests against the current DB schema.

### P5 — citizen channel foundations (citizen web retained)

- FastAPI WhatsApp Cloud webhook verification endpoint and signed inbound POST using Meta's `X-Hub-Signature-256` HMAC-SHA256 contract.
- Normalisation of text, location and media-message payloads.
- Sender reference is hashed before leaving the adapter; raw sender identity is not included in the normalized event.
- Stable fingerprint for duplicate screening.\n- Idempotent inbound message persistence as an unverified `signals` record, serialised by provider message ID; no second case-management table.
- Multilingual keyword hints are explicitly non-authoritative and do not determine legality.

Not yet included: media download and malware scanning, outbound WhatsApp templates, social API connectors, officer registry, notification delivery and SLA escalation. Inbound reports are stored as unverified signals only; they do not automatically create or classify an enforcement case.

## Safety and evidence constraints

- Water masks and SAR threshold masks are screening layers only. Thresholds need local seasonal calibration and independent field reference.
- Sentinel-1 VV thresholding is not a substitute for radiometric calibration, terrain correction, speckle treatment or orbit processing.
- Spectral MNDWI is not a building or soil-fill detector. High-resolution building/fill detection remains a separate model/data work package.
- Backtest metrics are meaningful only after case labels, geometry CRS, dates and blind-test independence are reviewed.
- No automated legal conclusion, enforcement recommendation or owner identification is produced.

## Verification status

The new tests are added to the existing pipeline test suite and CI installs the `geo` extra. This change has not been executed in a local Docker/GDAL environment in this session. CI must pass before merging; inspect COG driver availability and Sentinel asset naming against real STAC items before operational use.
