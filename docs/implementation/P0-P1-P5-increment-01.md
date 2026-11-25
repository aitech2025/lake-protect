# P0/P1/P5 implementation increment

Branch: `feat/p0-p1-p5-geospatial-integrations`

This is an additive increment. It preserves the existing FastAPI/PostGIS case-management plane, the citizen web application, and existing ingestion/processing-run APIs.

## P0 — detection and backtest foundations

- STAC scene discovery and suitability decisions for Sentinel collections.
- Sentinel-2 MNDWI spectral baseline and COG water masks.
- Sentinel-1 VV threshold screening accepts calibrated, terrain-corrected dB inputs only; it does not run orbit correction or SNAP preprocessing.
- Temporal comparison of two MNDWI masks produces water-loss and water-gain COGs plus GeoJSON polygons, with geodesic area filtering.
- GeoJSON case/detection scorer reports one-to-one spatial matches, precision, recall and F1. Ground-truth cases must include `area_acres`, `event_date` and an explicit `public_action_date` key (use null if no action date is known). Detections must include `detected_at`.
- The scorer is a first evaluation utility, not yet a statistically governed blind-test harness. It does not prove model accuracy or satisfy a 30-case acceptance gate.

## P1 — executable Sentinel-2 water workflow

- Dedicated geospatial dependencies and worker image remain separate from the transactional API.
- `lp-geo run-water` searches STAC, evaluates suitability, registers scene metadata through `/api/v1/ingestion/scenes`, creates and updates a processing run through `/api/v1/ingestion/processing-runs`, calculates MNDWI masks, selects a temporally distinct pair with at least 50% footprint overlap, compares water masks, and writes derived artefacts to S3-compatible object storage.
- Scene and run metadata use the existing ingestion schema; no duplicate scene or processing-run database was introduced.
- COG layout is checked; outputs are SHA-256 hashed and uploaded with hash metadata.
- The processing-run output manifest records scene IDs, acquisition dates, S3 object URIs, checksums, areas and method disclaimers.

Example environment (inject credentials through the runtime secret manager, not source control):

```bash
export LP_API_BASE_URL=https://lake-protect-api.example.gov
export LP_PIPELINE_TOKEN='replace-with-pipeline-service-token'
export LP_GEO_S3_BUCKET='approved-derived-imagery-bucket'
export LP_GEO_S3_ENDPOINT_URL='https://s3-compatible-endpoint.example' # omit if using AWS S3
export LP_GEO_S3_REGION=ap-south-1
export LP_GEO_S3_ACCESS_KEY_ID='inject-at-runtime'
export LP_GEO_S3_SECRET_ACCESS_KEY='inject-at-runtime'

cd pipeline
pip install -e '.[geo,dev]'
lp-geo run-water \
  --collections sentinel-2-l2a \
  --bbox 78.2,17.2,78.7,17.6 \
  --start 2025-01-01 --end 2025-03-01 \
  --max-cloud-pct 35 \
  --license-label 'confirm-provider-licence-before-use'
```

The example bbox and licence label are placeholders. Use an approved AOI, verify the provider/product licence, and confirm that the API service token and bucket policy are provisioned. The runner currently uses the STAC provider's accessible asset URLs; it does not implement CDSE account-based acquisition or provider tasking.

### P1 remaining

- Sentinel-1 ingestion and SNAP processing workflow.
- Persistent scheduling, backfill controls, rate limiting and resumable downloads.
- Production STAC API/pgSTAC and tile serving.
- Per-asset boundary clipping, lake-specific baseline selection and season-aware change rules.
- Integration against the target government's object store, API and IAM environment.

## P5 — WhatsApp inbound foundations (citizen web retained)

- Meta WhatsApp Cloud webhook GET verification uses the documented `hub.mode`, `hub.verify_token` and `hub.challenge` query parameter names.
- Signed POST payloads are verified using `X-Hub-Signature-256` HMAC-SHA256 before database writes.
- Text, location and media references are normalised; sender references are hashed.
- Inbound messages are persisted idempotently as unverified `signals` records using the existing table and transaction advisory locks.
- Keyword category hints are non-authoritative. Reports do not automatically create enforcement cases or legal findings.
- API tests cover Meta verification, invalid signatures and duplicate message handling.

Configure `LP_WHATSAPP_VERIFY_TOKEN` and `LP_WHATSAPP_APP_SECRET` in the runtime secret manager. Configure the Meta webhook subscription for the deployed HTTPS endpoint.

### P5 remaining

- Authenticated media download, content-type/size validation, malware scanning and immutable original storage.
- Outbound WhatsApp template messages.
- Social listening through authorised APIs/licensed providers and source-specific terms.
- Officer contact registry, departmental/jurisdiction routing, delivery receipts, retries and SLA escalation.
- Privacy notices, consent/retention rules and operational governance for each channel.

## Evidence and model guardrails

- MNDWI/SAR outputs and temporal water polygons are screening products. They are not proof of FTL encroachment, ownership or illegality.
- Water spread is not equivalent to the legally notified FTL polygon. Seasonal hydrology, image quality and acquisition timing matter.
- A two-date mask comparison is meaningful only when scenes are seasonally and spatially comparable. The pair selector uses acquisition-time gap and footprint overlap; it is an initial baseline, not a lake-specific seasonal reference policy. Comparisons are withheld when sufficient overlap is unavailable.
- Sentinel-1 thresholding is not a substitute for calibration, terrain correction, speckle filtering or orbit processing.
- MNDWI does not detect buildings or soil filling. High-resolution construction/fill models remain separate work.
- Backtest metrics require independently adjudicated cases, consistent geometry CRS, reliable event/action dates and a held-out blind cohort.
- All operational decisions remain with authorised officers; model outputs are review signals only.

## Verification status

Unit tests have been added for scene suitability, temporal water comparison, backtest timing, Meta signature verification and inbound idempotency. CI is configured to install the geospatial extra. The repository CI and target Docker/GDAL/S3 environment have not been executed in this session. Do not merge until PR checks pass and a controlled integration test is run with approved imagery and storage.
