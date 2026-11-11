"""Department-scoped row security, immutable triage provenance and ingest idempotency.
Revision ID: 0005
Revises: 0004
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE user_department_access (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id bigint NOT NULL REFERENCES users(id),
      department_id uuid NOT NULL REFERENCES departments(id),
      access_level text NOT NULL CHECK (access_level IN ('READ','CONTRIBUTE','MANAGE')),
      valid_from date NOT NULL DEFAULT CURRENT_DATE,
      valid_to date,
      granted_by bigint REFERENCES users(id),
      created_at timestamptz NOT NULL DEFAULT now(),
      CHECK (valid_to IS NULL OR valid_to >= valid_from),
      UNIQUE(user_id, department_id, valid_from)
    );
    CREATE INDEX ix_user_department_access_active
      ON user_department_access(user_id, department_id, valid_from, valid_to);

    CREATE TABLE candidate_predictions (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      candidate_id bigint NOT NULL REFERENCES candidates(id),
      score_type text NOT NULL CHECK (score_type IN ('REVIEW_PRIORITY','DETECTOR_CONFIDENCE','CALIBRATED_PROBABILITY')),
      score numeric(6,2) NOT NULL CHECK (score >= 0 AND score <= 100),
      model_name text NOT NULL,
      model_version text NOT NULL,
      feature_schema_version text NOT NULL,
      features jsonb NOT NULL,
      factors jsonb NOT NULL DEFAULT '{}'::jsonb,
      disclaimer text NOT NULL,
      generated_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE(candidate_id, model_name, model_version)
    );
    CREATE INDEX ix_candidate_predictions_candidate
      ON candidate_predictions(candidate_id, generated_at DESC);

    CREATE TABLE candidate_ingest_requests (
      idempotency_key char(64) PRIMARY KEY,
      payload_sha256 char(64) NOT NULL,
      candidate_id bigint NOT NULL REFERENCES candidates(id),
      response jsonb NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX ix_candidate_ingest_requests_candidate ON candidate_ingest_requests(candidate_id);

    CREATE FUNCTION lp_current_user_id() RETURNS bigint LANGUAGE sql STABLE AS $$
      SELECT NULLIF(current_setting('lp.user_id', true), '')::bigint
    $$;
    CREATE FUNCTION lp_is_platform_admin() RETURNS boolean LANGUAGE sql STABLE AS $$
      SELECT COALESCE(NULLIF(current_setting('lp.is_platform_admin', true), '')::boolean, false)
    $$;
    CREATE FUNCTION lp_is_pipeline_ingest() RETURNS boolean LANGUAGE sql STABLE AS $$
      SELECT COALESCE(NULLIF(current_setting('lp.pipeline_ingest', true), '')::boolean, false)
    $$;

    ALTER TABLE user_department_access ENABLE ROW LEVEL SECURITY;
    ALTER TABLE user_department_access FORCE ROW LEVEL SECURITY;
    CREATE POLICY user_department_access_read_self ON user_department_access FOR SELECT
      USING (lp_is_platform_admin() OR user_id = lp_current_user_id());
    CREATE POLICY user_department_access_admin_write ON user_department_access FOR ALL
      USING (lp_is_platform_admin()) WITH CHECK (lp_is_platform_admin());

    ALTER TABLE departments ENABLE ROW LEVEL SECURITY;
    ALTER TABLE departments FORCE ROW LEVEL SECURITY;
    CREATE POLICY departments_read_scope ON departments FOR SELECT
      USING (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM user_department_access uda
        WHERE uda.department_id = departments.id AND uda.user_id = lp_current_user_id()
          AND uda.valid_from <= CURRENT_DATE AND (uda.valid_to IS NULL OR uda.valid_to > CURRENT_DATE)
      ));
    CREATE POLICY departments_admin_write ON departments FOR ALL
      USING (lp_is_platform_admin()) WITH CHECK (lp_is_platform_admin());

    ALTER TABLE public_assets ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public_assets FORCE ROW LEVEL SECURITY;
    CREATE POLICY public_assets_read_scope ON public_assets FOR SELECT
      USING (lp_is_platform_admin() OR lp_is_pipeline_ingest() OR EXISTS (
        SELECT 1 FROM asset_responsibilities ar
        JOIN user_department_access uda ON uda.department_id = ar.department_id
        WHERE ar.asset_id = public_assets.id AND uda.user_id = lp_current_user_id()
          AND uda.valid_from <= CURRENT_DATE AND (uda.valid_to IS NULL OR uda.valid_to > CURRENT_DATE)
          AND ar.valid_from <= CURRENT_DATE AND (ar.valid_to IS NULL OR ar.valid_to > CURRENT_DATE)
      ));
    CREATE POLICY public_assets_admin_write ON public_assets FOR ALL
      USING (lp_is_platform_admin()) WITH CHECK (lp_is_platform_admin());

    ALTER TABLE asset_responsibilities ENABLE ROW LEVEL SECURITY;
    ALTER TABLE asset_responsibilities FORCE ROW LEVEL SECURITY;
    CREATE POLICY responsibilities_read_scope ON asset_responsibilities FOR SELECT
      USING (lp_is_platform_admin() OR lp_is_pipeline_ingest() OR EXISTS (
        SELECT 1 FROM user_department_access uda
        WHERE uda.department_id = asset_responsibilities.department_id AND uda.user_id = lp_current_user_id()
          AND uda.valid_from <= CURRENT_DATE AND (uda.valid_to IS NULL OR uda.valid_to > CURRENT_DATE)
      ));
    CREATE POLICY responsibilities_manage_scope ON asset_responsibilities FOR INSERT
      WITH CHECK (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM user_department_access uda
        WHERE uda.department_id = asset_responsibilities.department_id AND uda.user_id = lp_current_user_id()
          AND uda.access_level = 'MANAGE' AND uda.valid_from <= CURRENT_DATE
          AND (uda.valid_to IS NULL OR uda.valid_to > CURRENT_DATE)
      ));

    ALTER TABLE asset_parcels ENABLE ROW LEVEL SECURITY;
    ALTER TABLE asset_parcels FORCE ROW LEVEL SECURITY;
    CREATE POLICY asset_parcels_read_scope ON asset_parcels FOR SELECT
      USING (lp_is_platform_admin() OR EXISTS (SELECT 1 FROM public_assets pa WHERE pa.id = asset_parcels.asset_id));
    CREATE POLICY asset_parcels_admin_write ON asset_parcels FOR ALL
      USING (lp_is_platform_admin()) WITH CHECK (lp_is_platform_admin());

    ALTER TABLE asset_admin_links ENABLE ROW LEVEL SECURITY;
    ALTER TABLE asset_admin_links FORCE ROW LEVEL SECURITY;
    CREATE POLICY asset_admin_links_read_scope ON asset_admin_links FOR SELECT
      USING (lp_is_platform_admin() OR EXISTS (SELECT 1 FROM public_assets pa WHERE pa.id = asset_admin_links.asset_id));
    CREATE POLICY asset_admin_links_admin_write ON asset_admin_links FOR ALL
      USING (lp_is_platform_admin()) WITH CHECK (lp_is_platform_admin());

    ALTER TABLE land_parcels ENABLE ROW LEVEL SECURITY;
    ALTER TABLE land_parcels FORCE ROW LEVEL SECURITY;
    CREATE POLICY land_parcels_read_scope ON land_parcels FOR SELECT
      USING (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM asset_parcels ap WHERE ap.parcel_id = land_parcels.id
      ));
    CREATE POLICY land_parcels_admin_write ON land_parcels FOR ALL
      USING (lp_is_platform_admin()) WITH CHECK (lp_is_platform_admin());

    ALTER TABLE candidate_asset_links ENABLE ROW LEVEL SECURITY;
    ALTER TABLE candidate_asset_links FORCE ROW LEVEL SECURITY;
    CREATE POLICY candidate_asset_links_read_scope ON candidate_asset_links FOR SELECT
      USING (lp_is_platform_admin() OR lp_is_pipeline_ingest() OR EXISTS (
        SELECT 1 FROM public_assets pa WHERE pa.id = candidate_asset_links.platform_asset_id
      ));
    CREATE POLICY candidate_asset_links_pipeline_insert ON candidate_asset_links FOR INSERT
      WITH CHECK (lp_is_platform_admin() OR lp_is_pipeline_ingest());

    ALTER TABLE candidate_predictions ENABLE ROW LEVEL SECURITY;
    ALTER TABLE candidate_predictions FORCE ROW LEVEL SECURITY;
    CREATE POLICY candidate_predictions_read_scope ON candidate_predictions FOR SELECT
      USING (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM candidate_asset_links cal
        JOIN public_assets pa ON pa.id = cal.platform_asset_id
        WHERE cal.legacy_candidate_id = candidate_predictions.candidate_id
      ));
    CREATE POLICY candidate_predictions_pipeline_insert ON candidate_predictions FOR INSERT
      WITH CHECK (lp_is_platform_admin() OR lp_is_pipeline_ingest());

    ALTER TABLE candidate_ingest_requests ENABLE ROW LEVEL SECURITY;
    ALTER TABLE candidate_ingest_requests FORCE ROW LEVEL SECURITY;
    CREATE POLICY candidate_ingest_pipeline_access ON candidate_ingest_requests FOR ALL
      USING (lp_is_platform_admin() OR lp_is_pipeline_ingest())
      WITH CHECK (lp_is_platform_admin() OR lp_is_pipeline_ingest());

    ALTER TABLE ingestion_batches ENABLE ROW LEVEL SECURITY;
    ALTER TABLE ingestion_batches FORCE ROW LEVEL SECURITY;
    CREATE POLICY ingestion_batches_service_access ON ingestion_batches FOR ALL
      USING (lp_is_platform_admin() OR lp_is_pipeline_ingest())
      WITH CHECK (lp_is_platform_admin() OR lp_is_pipeline_ingest());

    ALTER TABLE source_records ENABLE ROW LEVEL SECURITY;
    ALTER TABLE source_records FORCE ROW LEVEL SECURITY;
    CREATE POLICY source_records_service_access ON source_records FOR ALL
      USING (lp_is_platform_admin() OR lp_is_pipeline_ingest())
      WITH CHECK (lp_is_platform_admin() OR lp_is_pipeline_ingest());

    ALTER TABLE satellite_scenes ENABLE ROW LEVEL SECURITY;
    ALTER TABLE satellite_scenes FORCE ROW LEVEL SECURITY;
    CREATE POLICY satellite_scenes_service_access ON satellite_scenes FOR ALL
      USING (lp_is_platform_admin() OR lp_is_pipeline_ingest())
      WITH CHECK (lp_is_platform_admin() OR lp_is_pipeline_ingest());

    ALTER TABLE processing_runs ENABLE ROW LEVEL SECURITY;
    ALTER TABLE processing_runs FORCE ROW LEVEL SECURITY;
    CREATE POLICY processing_runs_service_access ON processing_runs FOR ALL
      USING (lp_is_platform_admin() OR lp_is_pipeline_ingest())
      WITH CHECK (lp_is_platform_admin() OR lp_is_pipeline_ingest());

    ALTER TABLE ml_model_versions ENABLE ROW LEVEL SECURITY;
    ALTER TABLE ml_model_versions FORCE ROW LEVEL SECURITY;
    CREATE POLICY ml_model_versions_admin_access ON ml_model_versions FOR ALL
      USING (lp_is_platform_admin()) WITH CHECK (lp_is_platform_admin());

    ALTER TABLE ml_evaluations ENABLE ROW LEVEL SECURITY;
    ALTER TABLE ml_evaluations FORCE ROW LEVEL SECURITY;
    CREATE POLICY ml_evaluations_admin_access ON ml_evaluations FOR ALL
      USING (lp_is_platform_admin()) WITH CHECK (lp_is_platform_admin());

    ALTER TABLE outbox_events ENABLE ROW LEVEL SECURITY;
    ALTER TABLE outbox_events FORCE ROW LEVEL SECURITY;
    CREATE POLICY outbox_events_pipeline_insert ON outbox_events FOR INSERT
      WITH CHECK (lp_is_platform_admin() OR lp_is_pipeline_ingest());
    CREATE POLICY outbox_events_admin_manage ON outbox_events FOR ALL
      USING (lp_is_platform_admin()) WITH CHECK (lp_is_platform_admin());

    CREATE TRIGGER candidate_predictions_append_only BEFORE UPDATE OR DELETE ON candidate_predictions
      FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
    """)


def downgrade():
    op.execute("""
    DROP TRIGGER IF EXISTS candidate_predictions_append_only ON candidate_predictions;
    DROP TABLE IF EXISTS candidate_ingest_requests, candidate_predictions, user_department_access CASCADE;
    DROP FUNCTION IF EXISTS lp_is_pipeline_ingest();
    DROP FUNCTION IF EXISTS lp_is_platform_admin();
    DROP FUNCTION IF EXISTS lp_current_user_id();
    """)
