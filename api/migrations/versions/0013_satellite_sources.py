"""Satellite image sources the admin maintains (DECISIONS.md D-066).

One row per source, for one of three purposes:
- `screen_optical`: the weekly screen and citizens' satellite looks (Sentinel-2). One is on at a time.
- `screen_radar`: the radar check for built-up (Sentinel-1). At most one is on; with none, the screen
  runs without radar and says so.
- `sharper`: sharper paid images an official may ask for, with the price used for the estimate.

The detection thresholds stay in the versioned rule file (pipeline/lake_protect/detect_rules.yaml).
The pipeline reads the sources that are on, and records the settings it used in the run's rules hash.

Seeded with the sources the app used until now: the figures are CONTEXT.md section 8.1's.

Revision ID: 0013
Revises: 0012
"""
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

UP = r"""
CREATE TABLE satellite_sources (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    key text NOT NULL UNIQUE CHECK (key ~ '^[a-z0-9][a-z0-9_-]{2,40}$'),
    name text NOT NULL CHECK (length(name) BETWEEN 2 AND 120),
    provider text NOT NULL CHECK (length(provider) BETWEEN 2 AND 200),
    purpose text NOT NULL CHECK (purpose IN ('screen_optical', 'screen_radar', 'sharper')),
    resolution_m numeric(8, 2) NOT NULL CHECK (resolution_m > 0 AND resolution_m <= 1000),
    revisit_days numeric(6, 1) CHECK (revisit_days IS NULL OR (revisit_days > 0 AND revisit_days <= 365)),
    stac_url text CHECK (stac_url IS NULL OR stac_url ~ '^https://'),
    collection text,
    max_scene_cloud_pct numeric(5, 1) CHECK (max_scene_cloud_pct IS NULL OR (max_scene_cloud_pct >= 0 AND max_scene_cloud_pct <= 100)),
    price_usd_per_sq_km numeric(10, 2) CHECK (price_usd_per_sq_km IS NULL OR price_usd_per_sq_km >= 0),
    min_order_sq_km numeric(10, 2) CHECK (min_order_sq_km IS NULL OR min_order_sq_km >= 0),
    licence_notice text CHECK (licence_notice IS NULL OR length(licence_notice) <= 300),
    notes text CHECK (notes IS NULL OR length(notes) <= 1000),
    active boolean NOT NULL DEFAULT true,
    added_by bigint REFERENCES users(id),
    added_at timestamptz NOT NULL DEFAULT now(),
    updated_by bigint REFERENCES users(id),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (purpose = 'sharper' OR (stac_url IS NOT NULL AND collection IS NOT NULL)),
    CHECK (purpose <> 'screen_optical' OR max_scene_cloud_pct IS NOT NULL),
    CHECK (purpose = 'sharper' OR (price_usd_per_sq_km IS NULL AND min_order_sq_km IS NULL))
);
-- One source on at a time for each screening purpose.
CREATE UNIQUE INDEX satellite_sources_one_on ON satellite_sources (purpose) WHERE active AND purpose <> 'sharper';

INSERT INTO satellite_sources (key, name, provider, purpose, resolution_m, revisit_days, stac_url, collection, max_scene_cloud_pct,
                               price_usd_per_sq_km, min_order_sq_km, licence_notice, notes) VALUES
('sentinel-2-l2a', 'Sentinel-2 L2A', 'ESA Copernicus, through Element 84 Earth Search', 'screen_optical', 10, 5,
 'https://earth-search.aws.element84.com/v1', 'sentinel-2-c1-l2a', 70, NULL, NULL,
 'Contains modified Copernicus Sentinel data {year}',
 'Free. Cloud-optimised GeoTIFF over public HTTPS. 20 m for SWIR and the scene class (CONTEXT.md 8.1).'),
('sentinel-1-rtc', 'Sentinel-1 RTC (radar)', 'ESA Copernicus, through Microsoft Planetary Computer', 'screen_radar', 10, 6,
 'https://planetarycomputer.microsoft.com/api/stac/v1', 'sentinel-1-rtc', NULL, NULL, NULL,
 'Contains modified Copernicus Sentinel data {year}',
 'Free. Terrain-corrected gamma0; confirms built-up through cloud. 6-day repeat with 1C and 1D (CONTEXT.md 8.1).'),
('isro_nrsc', 'ISRO high-resolution', 'NRSC (Bhoonidhi)', 'sharper', 5, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
 'Finer than 5 m. Free to government bodies, priced for private firms (Indian Space Policy 2023). Order routing not confirmed.'),
('commercial_archive', 'Commercial archive, 30 to 50 cm', 'Commercial reseller', 'sharper', 0.5, NULL, NULL, NULL, NULL, 26, NULL, NULL,
 'Reseller guide figures, upper end: $17 to $26 per sq km (CONTEXT.md 8.1). A planning estimate, not a quote.'),
('commercial_tasking', 'Commercial new capture, 30 to 50 cm', 'Commercial reseller', 'sharper', 0.5, NULL, NULL, NULL, NULL, 55, NULL, NULL,
 'Reseller guide figures, upper end: $25 to $55 per sq km (CONTEXT.md 8.1). A planning estimate, not a quote.');
"""

DOWN = r"""
DROP TABLE satellite_sources;
"""


def run_raw(sql: str) -> None:
    with op.get_bind().connection.dbapi_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    run_raw(UP)


def downgrade() -> None:
    run_raw(DOWN)
