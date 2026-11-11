"""Additive statewide registry, provenance, geospatial processing and ML governance foundation.
Revision ID: 0004
Revises: 0003
"""
from alembic import op
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
    CREATE TABLE departments (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), code text NOT NULL UNIQUE,
      name text NOT NULL, parent_id uuid REFERENCES departments(id),
      is_active boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE administrative_units (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), code text NOT NULL, name text NOT NULL,
      unit_type text NOT NULL CHECK (unit_type IN ('STATE','DISTRICT','MANDAL','ULB','VILLAGE','WARD')),
      parent_id uuid REFERENCES administrative_units(id), valid_from date NOT NULL, valid_to date,
      recorded_at timestamptz NOT NULL DEFAULT now(), source_record_ref text,
      CHECK (valid_to IS NULL OR valid_to > valid_from), UNIQUE(code, unit_type, valid_from)
    );
    CREATE INDEX ix_admin_units_parent ON administrative_units(parent_id);
    CREATE TABLE public_assets (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), asset_code text NOT NULL UNIQUE,
      display_name text NOT NULL, category_code text NOT NULL,
      lifecycle_status text NOT NULL DEFAULT 'ACTIVE' CHECK (lifecycle_status IN ('ACTIVE','INACTIVE','TRANSFERRED','RETIRED','UNDER_REVIEW')),
      legacy_asset_id bigint UNIQUE REFERENCES assets(id), baseline_date date,
      centroid geometry(Point,4326), footprint geometry(MultiPolygon,4326),
      source_authority text NOT NULL DEFAULT 'UNVERIFIED'
        CHECK (source_authority IN ('AUTHORITATIVE','CERTIFIED','DERIVED','EXTERNAL','FIELD','MODEL','UNVERIFIED')),
      source_record_ref text, created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX ix_public_assets_category ON public_assets(category_code,lifecycle_status);
    CREATE INDEX ix_public_assets_footprint ON public_assets USING GIST(footprint);
    CREATE TABLE land_parcels (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), state_code text NOT NULL DEFAULT 'TS',
      district_code text, mandal_code text, village_code text, survey_number text NOT NULL,
      subdivision_number text, land_classification text,
      source_authority text NOT NULL DEFAULT 'UNVERIFIED'
        CHECK (source_authority IN ('AUTHORITATIVE','CERTIFIED','DERIVED','EXTERNAL','FIELD','MODEL','UNVERIFIED')),
      source_record_ref text, valid_from date NOT NULL, valid_to date, recorded_at timestamptz NOT NULL DEFAULT now(),
      footprint geometry(MultiPolygon,4326), CHECK (valid_to IS NULL OR valid_to > valid_from)
    );
    CREATE INDEX ix_land_parcels_survey ON land_parcels(district_code,mandal_code,village_code,survey_number,subdivision_number);
    CREATE INDEX ix_land_parcels_geom ON land_parcels USING GIST(footprint);
    CREATE TABLE asset_parcels (
      asset_id uuid NOT NULL REFERENCES public_assets(id), parcel_id uuid NOT NULL REFERENCES land_parcels(id),
      overlap_area_sq_m numeric(16,2), relation_type text NOT NULL DEFAULT 'INTERSECTS',
      valid_from date NOT NULL, valid_to date, PRIMARY KEY(asset_id,parcel_id,valid_from),
      CHECK (valid_to IS NULL OR valid_to > valid_from)
    );
    CREATE INDEX ix_asset_parcels_parcel ON asset_parcels(parcel_id);
    CREATE TABLE asset_admin_links (
      asset_id uuid NOT NULL REFERENCES public_assets(id),
      administrative_unit_id uuid NOT NULL REFERENCES administrative_units(id),
      valid_from date NOT NULL, valid_to date,
      PRIMARY KEY(asset_id,administrative_unit_id,valid_from),
      CHECK (valid_to IS NULL OR valid_to > valid_from)
    );
    CREATE INDEX ix_asset_admin_unit ON asset_admin_links(administrative_unit_id);
    CREATE TABLE asset_responsibilities (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), asset_id uuid NOT NULL REFERENCES public_assets(id),
      department_id uuid NOT NULL REFERENCES departments(id),
      relationship_type text NOT NULL CHECK (relationship_type IN ('OWNER','CUSTODIAN','POSSESSOR','JURISDICTION','OPERATIONAL','ENFORCEMENT','DATA_STEWARD')),
      valid_from date NOT NULL, valid_to date, source_authority text NOT NULL,
      source_record_ref text NOT NULL, recorded_at timestamptz NOT NULL DEFAULT now(),
      CHECK (valid_to IS NULL OR valid_to > valid_from)
    );
    CREATE INDEX ix_asset_responsibilities_asset ON asset_responsibilities(asset_id,relationship_type,valid_from);
    CREATE INDEX ix_asset_responsibilities_department ON asset_responsibilities(department_id,relationship_type);
    CREATE TABLE ingestion_batches (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source_system text NOT NULL,
      source_authority text NOT NULL, schema_version text NOT NULL, mapping_version text NOT NULL,
      status text NOT NULL CHECK (status IN ('RECEIVED','VALIDATING','ACCEPTED','PARTIAL','REJECTED','FAILED')),
      source_uri text, checksum_sha256 char(64), records_received integer NOT NULL DEFAULT 0,
      records_accepted integer NOT NULL DEFAULT 0, records_rejected integer NOT NULL DEFAULT 0,
      error_summary jsonb NOT NULL DEFAULT '{}'::jsonb, started_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz
    );
    CREATE TABLE source_records (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), batch_id uuid REFERENCES ingestion_batches(id),
      source_system text NOT NULL, source_record_id text NOT NULL, authority_class text NOT NULL
        CHECK (authority_class IN ('AUTHORITATIVE','CERTIFIED','DERIVED','EXTERNAL','FIELD','MODEL','UNVERIFIED')),
      source_uri text, source_version text, source_effective_at timestamptz,
      retrieved_at timestamptz NOT NULL DEFAULT now(), checksum_sha256 char(64),
      validation_status text NOT NULL DEFAULT 'PENDING'
        CHECK (validation_status IN ('PENDING','VALID','INVALID','CONFLICT','QUARANTINED')),
      payload jsonb NOT NULL DEFAULT '{}'::jsonb, UNIQUE(source_system,source_record_id,source_version)
    );
    CREATE INDEX ix_source_records_batch ON source_records(batch_id,validation_status);
    CREATE TABLE satellite_scenes (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), provider text NOT NULL, collection_id text NOT NULL,
      item_id text NOT NULL, platform text, instrument text, acquired_at timestamptz NOT NULL,
      footprint geometry(Polygon,4326) NOT NULL, cloud_cover numeric(5,2), gsd_m numeric(10,3),
      license text NOT NULL, stac_item jsonb NOT NULL, object_uri text, checksum_sha256 char(64),
      suitability_status text NOT NULL DEFAULT 'PENDING'
        CHECK (suitability_status IN ('PENDING','SUITABLE','UNSUITABLE','PARTIAL')),
      ingested_at timestamptz NOT NULL DEFAULT now(), UNIQUE(provider,collection_id,item_id)
    );
    CREATE INDEX ix_satellite_scenes_acquired ON satellite_scenes(acquired_at DESC);
    CREATE INDEX ix_satellite_scenes_footprint ON satellite_scenes USING GIST(footprint);
    CREATE TABLE processing_runs (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), pipeline_name text NOT NULL,
      pipeline_version text NOT NULL, config_hash char(64) NOT NULL,
      status text NOT NULL CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','PARTIAL','FAILED','CANCELLED')),
      input_manifest jsonb NOT NULL, output_manifest jsonb NOT NULL DEFAULT '{}'::jsonb,
      geographic_scope geometry(Geometry,4326), correlation_id uuid NOT NULL DEFAULT gen_random_uuid(),
      attempt integer NOT NULL DEFAULT 0, started_at timestamptz, finished_at timestamptz,
      error_code text, error_detail text, created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX ix_processing_runs_status ON processing_runs(status,created_at);
    CREATE INDEX ix_processing_runs_scope ON processing_runs USING GIST(geographic_scope);
    CREATE TABLE candidate_asset_links (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), legacy_candidate_id bigint REFERENCES candidates(id),
      platform_asset_id uuid NOT NULL REFERENCES public_assets(id), parcel_id uuid REFERENCES land_parcels(id),
      boundary_id bigint REFERENCES boundaries(id), processing_run_id uuid REFERENCES processing_runs(id),
      spatial_relation text NOT NULL, overlap_area_sq_m numeric(16,2), matched_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE(legacy_candidate_id,platform_asset_id,parcel_id,boundary_id)
    );
    CREATE INDEX ix_candidate_asset_links_asset ON candidate_asset_links(platform_asset_id,matched_at DESC);
    CREATE TABLE ml_model_versions (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), model_name text NOT NULL, model_version text NOT NULL,
      task_type text NOT NULL, framework text, artifact_uri text, artifact_sha256 char(64),
      feature_schema_version text NOT NULL, training_dataset_ref text, validation_report_uri text,
      model_card jsonb NOT NULL DEFAULT '{}'::jsonb,
      status text NOT NULL CHECK (status IN ('REGISTERED','VALIDATING','APPROVED','SHADOW','PRODUCTION','RETIRED','REJECTED')),
      approved_by text, approved_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE(model_name,model_version)
    );
    CREATE TABLE ml_evaluations (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), model_version_id uuid NOT NULL REFERENCES ml_model_versions(id),
      evaluation_type text NOT NULL CHECK (evaluation_type IN ('BACKTEST','VALIDATION','SHADOW','DRIFT','PRODUCTION')),
      dataset_ref text NOT NULL, metrics jsonb NOT NULL, slice_metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
      evaluated_at timestamptz NOT NULL DEFAULT now(), evaluator text NOT NULL, passed boolean NOT NULL, notes text
    );
    CREATE INDEX ix_ml_evaluations_model ON ml_evaluations(model_version_id,evaluated_at DESC);
    CREATE TABLE outbox_events (
      id bigserial PRIMARY KEY, event_id uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
      event_type text NOT NULL, schema_version text NOT NULL DEFAULT '1.0',
      aggregate_type text NOT NULL, aggregate_id text NOT NULL, correlation_id uuid NOT NULL,
      payload jsonb NOT NULL, occurred_at timestamptz NOT NULL DEFAULT now(),
      published_at timestamptz, publish_attempts integer NOT NULL DEFAULT 0, last_error text
    );
    CREATE INDEX ix_outbox_unpublished ON outbox_events(occurred_at) WHERE published_at IS NULL;

    INSERT INTO public_assets(asset_code,display_name,category_code,legacy_asset_id,baseline_date,source_authority,source_record_ref)
    SELECT 'LEGACY-' || id::text,name,type::text,id,baseline_date,'DERIVED','legacy:assets:' || id::text
    FROM assets ON CONFLICT (legacy_asset_id) DO NOTHING;
    """)

def downgrade():
    op.execute("""
    DROP TABLE IF EXISTS outbox_events,ml_evaluations,ml_model_versions,candidate_asset_links,
      processing_runs,satellite_scenes,source_records,ingestion_batches,asset_responsibilities,
      asset_admin_links,asset_parcels,land_parcels,public_assets,administrative_units,departments CASCADE;
    """)
