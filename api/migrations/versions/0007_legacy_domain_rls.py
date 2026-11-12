"""Apply department-scope RLS to the original lake workflow tables.
Revision ID: 0007
Revises: 0006
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    -- Legacy lake pilot records now inherit department access from their canonical
    -- public_assets identity and effective-dated responsibility assignments.
    ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
    ALTER TABLE assets FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_assets_scope_read ON assets FOR SELECT
      USING (lp_is_platform_admin() OR lp_is_pipeline_ingest() OR EXISTS (
        SELECT 1 FROM public_assets pa WHERE pa.legacy_asset_id = assets.id
      ));
    CREATE POLICY legacy_assets_admin_write ON assets FOR ALL
      USING (lp_is_platform_admin()) WITH CHECK (lp_is_platform_admin());

    ALTER TABLE boundaries ENABLE ROW LEVEL SECURITY;
    ALTER TABLE boundaries FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_boundaries_scope_read ON boundaries FOR SELECT
      USING (lp_is_platform_admin() OR lp_is_pipeline_ingest() OR EXISTS (
        SELECT 1 FROM assets a WHERE a.id = boundaries.asset_id
      ));
    CREATE POLICY legacy_boundaries_admin_write ON boundaries FOR ALL
      USING (lp_is_platform_admin()) WITH CHECK (lp_is_platform_admin());

    ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;
    ALTER TABLE candidates FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_candidates_scope_read ON candidates FOR SELECT
      USING (lp_is_platform_admin() OR lp_is_pipeline_ingest() OR EXISTS (
        SELECT 1 FROM assets a WHERE a.id = candidates.asset_id
      ));
    CREATE POLICY legacy_candidates_pipeline_insert ON candidates FOR INSERT
      WITH CHECK (lp_is_platform_admin() OR lp_is_pipeline_ingest());

    ALTER TABLE observations ENABLE ROW LEVEL SECURITY;
    ALTER TABLE observations FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_observations_scope_read ON observations FOR SELECT
      USING (lp_is_platform_admin() OR lp_is_pipeline_ingest() OR EXISTS (
        SELECT 1 FROM candidates c
        WHERE c.observation_ids @> ARRAY[observations.id]::bigint[]
      ));
    CREATE POLICY legacy_observations_pipeline_insert ON observations FOR INSERT
      WITH CHECK (lp_is_platform_admin() OR lp_is_pipeline_ingest());

    ALTER TABLE legal_checks ENABLE ROW LEVEL SECURITY;
    ALTER TABLE legal_checks FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_legal_checks_scope_read ON legal_checks FOR SELECT
      USING (lp_is_platform_admin() OR lp_is_pipeline_ingest() OR EXISTS (
        SELECT 1 FROM candidates c WHERE c.id = legal_checks.candidate_id
      ));
    CREATE POLICY legacy_legal_checks_pipeline_insert ON legal_checks FOR INSERT
      WITH CHECK (lp_is_platform_admin() OR lp_is_pipeline_ingest());

    ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
    ALTER TABLE alerts FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_alerts_scope_access ON alerts FOR ALL
      USING (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM candidates c WHERE c.id = alerts.candidate_id
      ))
      WITH CHECK (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM candidates c WHERE c.id = alerts.candidate_id
      ));
    CREATE POLICY legacy_alerts_pipeline_insert ON alerts FOR INSERT
      WITH CHECK (lp_is_platform_admin() OR lp_is_pipeline_ingest());

    ALTER TABLE permits ENABLE ROW LEVEL SECURITY;
    ALTER TABLE permits FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_permits_scope_read ON permits FOR SELECT
      USING (lp_is_platform_admin() OR lp_is_pipeline_ingest() OR EXISTS (
        SELECT 1 FROM legal_checks lc WHERE lc.matched_permit_id = permits.id
      ));
    CREATE POLICY legacy_permits_admin_write ON permits FOR ALL
      USING (lp_is_platform_admin()) WITH CHECK (lp_is_platform_admin());

    ALTER TABLE authorised_works ENABLE ROW LEVEL SECURITY;
    ALTER TABLE authorised_works FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_authorised_works_scope_read ON authorised_works FOR SELECT
      USING (lp_is_platform_admin() OR lp_is_pipeline_ingest() OR EXISTS (
        SELECT 1 FROM legal_checks lc WHERE lc.matched_work_id = authorised_works.id
      ));
    CREATE POLICY legacy_authorised_works_admin_write ON authorised_works FOR ALL
      USING (lp_is_platform_admin()) WITH CHECK (lp_is_platform_admin());

    ALTER TABLE court_cases ENABLE ROW LEVEL SECURITY;
    ALTER TABLE court_cases FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_court_cases_scope_read ON court_cases FOR SELECT
      USING (lp_is_platform_admin() OR lp_is_pipeline_ingest()
        OR (court_cases.asset_id IS NOT NULL AND EXISTS (
          SELECT 1 FROM assets a WHERE a.id = court_cases.asset_id
        ))
        OR EXISTS (SELECT 1 FROM legal_checks lc WHERE lc.matched_court_case_id = court_cases.id));
    CREATE POLICY legacy_court_cases_admin_write ON court_cases FOR ALL
      USING (lp_is_platform_admin()) WITH CHECK (lp_is_platform_admin());

    ALTER TABLE closure_requests ENABLE ROW LEVEL SECURITY;
    ALTER TABLE closure_requests FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_closure_requests_scope_access ON closure_requests FOR ALL
      USING (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM alerts a WHERE a.id = closure_requests.alert_id
      ))
      WITH CHECK (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM alerts a WHERE a.id = closure_requests.alert_id
      ));

    ALTER TABLE field_checks ENABLE ROW LEVEL SECURITY;
    ALTER TABLE field_checks FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_field_checks_scope_access ON field_checks FOR ALL
      USING (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM alerts a WHERE a.id = field_checks.alert_id
      ))
      WITH CHECK (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM alerts a WHERE a.id = field_checks.alert_id
      ));

    ALTER TABLE owner_claims ENABLE ROW LEVEL SECURITY;
    ALTER TABLE owner_claims FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_owner_claims_scope_access ON owner_claims FOR ALL
      USING (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM alerts a WHERE a.id = owner_claims.alert_id
      ))
      WITH CHECK (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM alerts a WHERE a.id = owner_claims.alert_id
      ));

    ALTER TABLE readiness_items ENABLE ROW LEVEL SECURITY;
    ALTER TABLE readiness_items FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_readiness_scope_access ON readiness_items FOR ALL
      USING (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM alerts a WHERE a.id = readiness_items.alert_id
      ))
      WITH CHECK (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM alerts a WHERE a.id = readiness_items.alert_id
      ));

    ALTER TABLE evidence_packs ENABLE ROW LEVEL SECURITY;
    ALTER TABLE evidence_packs FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_evidence_packs_scope_read ON evidence_packs FOR SELECT
      USING (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM alerts a WHERE a.id = evidence_packs.alert_id
      ));
    CREATE POLICY legacy_evidence_packs_insert ON evidence_packs FOR INSERT
      WITH CHECK (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM alerts a WHERE a.id = evidence_packs.alert_id
      ));

    ALTER TABLE officer_records ENABLE ROW LEVEL SECURITY;
    ALTER TABLE officer_records FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_officer_records_scope_access ON officer_records FOR ALL
      USING (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM alerts a WHERE a.id = officer_records.alert_id
      ))
      WITH CHECK (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM alerts a WHERE a.id = officer_records.alert_id
      ));

    ALTER TABLE imagery_requests ENABLE ROW LEVEL SECURITY;
    ALTER TABLE imagery_requests FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_imagery_requests_scope_access ON imagery_requests FOR ALL
      USING (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM alerts a WHERE a.id = imagery_requests.alert_id
      ))
      WITH CHECK (lp_is_platform_admin() OR EXISTS (
        SELECT 1 FROM alerts a WHERE a.id = imagery_requests.alert_id
      ));

    ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
    ALTER TABLE signals FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_signals_scope_access ON signals FOR ALL
      USING (lp_is_platform_admin() OR lp_is_pipeline_ingest()
        OR (signals.asset_id IS NOT NULL AND EXISTS (
          SELECT 1 FROM assets a WHERE a.id = signals.asset_id
        ))
        OR (signals.linked_alert_id IS NOT NULL AND EXISTS (
          SELECT 1 FROM alerts a WHERE a.id = signals.linked_alert_id
        )))
      WITH CHECK (lp_is_platform_admin() OR lp_is_pipeline_ingest()
        OR (signals.asset_id IS NOT NULL AND EXISTS (
          SELECT 1 FROM assets a WHERE a.id = signals.asset_id
        ))
        OR (signals.linked_alert_id IS NOT NULL AND EXISTS (
          SELECT 1 FROM alerts a WHERE a.id = signals.linked_alert_id
        )));

    ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
    ALTER TABLE audit_log FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_audit_log_scope_read ON audit_log FOR SELECT
      USING (lp_is_platform_admin() OR actor_id = lp_current_user_id()
        OR (entity = 'alert' AND EXISTS (
          SELECT 1 FROM alerts a WHERE a.id::text = audit_log.entity_id
        ))
        OR (entity = 'candidate' AND EXISTS (
          SELECT 1 FROM candidates c WHERE c.id::text = audit_log.entity_id
        ))
        OR (entity = 'public_asset' AND EXISTS (
          SELECT 1 FROM public_assets pa WHERE pa.id::text = audit_log.entity_id
        )));
    CREATE POLICY legacy_audit_log_scoped_insert ON audit_log FOR INSERT
      WITH CHECK (lp_is_platform_admin() OR lp_is_pipeline_ingest()
        OR actor_id = lp_current_user_id());

    ALTER TABLE bulletins ENABLE ROW LEVEL SECURITY;
    ALTER TABLE bulletins FORCE ROW LEVEL SECURITY;
    CREATE POLICY legacy_bulletins_admin_only ON bulletins FOR ALL
      USING (lp_is_platform_admin()) WITH CHECK (lp_is_platform_admin());

    -- RLS joins must stay index-backed as the registry grows.
    CREATE INDEX IF NOT EXISTS ix_boundaries_asset_id ON boundaries(asset_id);
    CREATE INDEX IF NOT EXISTS ix_candidates_asset_id ON candidates(asset_id);
    CREATE INDEX IF NOT EXISTS ix_alerts_candidate_id ON alerts(candidate_id);
    CREATE INDEX IF NOT EXISTS ix_legal_checks_candidate_id ON legal_checks(candidate_id);
    CREATE INDEX IF NOT EXISTS ix_field_checks_alert_id ON field_checks(alert_id);
    CREATE INDEX IF NOT EXISTS ix_owner_claims_alert_id ON owner_claims(alert_id);
    CREATE INDEX IF NOT EXISTS ix_readiness_items_alert_id ON readiness_items(alert_id);
    CREATE INDEX IF NOT EXISTS ix_evidence_packs_alert_id ON evidence_packs(alert_id);
    CREATE INDEX IF NOT EXISTS ix_officer_records_alert_id ON officer_records(alert_id);
    CREATE INDEX IF NOT EXISTS ix_imagery_requests_alert_id ON imagery_requests(alert_id);
    """)


def downgrade():
    op.execute("""
    DROP POLICY IF EXISTS legacy_bulletins_admin_only ON bulletins;
    DROP POLICY IF EXISTS legacy_audit_log_scoped_insert ON audit_log;
    DROP POLICY IF EXISTS legacy_audit_log_scope_read ON audit_log;
    DROP POLICY IF EXISTS legacy_signals_scope_access ON signals;
    DROP POLICY IF EXISTS legacy_imagery_requests_scope_access ON imagery_requests;
    DROP POLICY IF EXISTS legacy_officer_records_scope_access ON officer_records;
    DROP POLICY IF EXISTS legacy_evidence_packs_insert ON evidence_packs;
    DROP POLICY IF EXISTS legacy_evidence_packs_scope_read ON evidence_packs;
    DROP POLICY IF EXISTS legacy_readiness_scope_access ON readiness_items;
    DROP POLICY IF EXISTS legacy_owner_claims_scope_access ON owner_claims;
    DROP POLICY IF EXISTS legacy_field_checks_scope_access ON field_checks;
    DROP POLICY IF EXISTS legacy_closure_requests_scope_access ON closure_requests;
    DROP POLICY IF EXISTS legacy_court_cases_admin_write ON court_cases;
    DROP POLICY IF EXISTS legacy_court_cases_scope_read ON court_cases;
    DROP POLICY IF EXISTS legacy_authorised_works_admin_write ON authorised_works;
    DROP POLICY IF EXISTS legacy_authorised_works_scope_read ON authorised_works;
    DROP POLICY IF EXISTS legacy_permits_admin_write ON permits;
    DROP POLICY IF EXISTS legacy_permits_scope_read ON permits;
    DROP POLICY IF EXISTS legacy_alerts_pipeline_insert ON alerts;
    DROP POLICY IF EXISTS legacy_alerts_scope_access ON alerts;
    DROP POLICY IF EXISTS legacy_legal_checks_pipeline_insert ON legal_checks;
    DROP POLICY IF EXISTS legacy_legal_checks_scope_read ON legal_checks;
    DROP POLICY IF EXISTS legacy_observations_pipeline_insert ON observations;
    DROP POLICY IF EXISTS legacy_observations_scope_read ON observations;
    DROP POLICY IF EXISTS legacy_candidates_pipeline_insert ON candidates;
    DROP POLICY IF EXISTS legacy_candidates_scope_read ON candidates;
    DROP POLICY IF EXISTS legacy_boundaries_admin_write ON boundaries;
    DROP POLICY IF EXISTS legacy_boundaries_scope_read ON boundaries;
    DROP POLICY IF EXISTS legacy_assets_admin_write ON assets;
    DROP POLICY IF EXISTS legacy_assets_scope_read ON assets;
    ALTER TABLE bulletins NO FORCE ROW LEVEL SECURITY; ALTER TABLE bulletins DISABLE ROW LEVEL SECURITY;
    ALTER TABLE audit_log NO FORCE ROW LEVEL SECURITY; ALTER TABLE audit_log DISABLE ROW LEVEL SECURITY;
    ALTER TABLE signals NO FORCE ROW LEVEL SECURITY; ALTER TABLE signals DISABLE ROW LEVEL SECURITY;
    ALTER TABLE imagery_requests NO FORCE ROW LEVEL SECURITY; ALTER TABLE imagery_requests DISABLE ROW LEVEL SECURITY;
    ALTER TABLE officer_records NO FORCE ROW LEVEL SECURITY; ALTER TABLE officer_records DISABLE ROW LEVEL SECURITY;
    ALTER TABLE evidence_packs NO FORCE ROW LEVEL SECURITY; ALTER TABLE evidence_packs DISABLE ROW LEVEL SECURITY;
    ALTER TABLE readiness_items NO FORCE ROW LEVEL SECURITY; ALTER TABLE readiness_items DISABLE ROW LEVEL SECURITY;
    ALTER TABLE owner_claims NO FORCE ROW LEVEL SECURITY; ALTER TABLE owner_claims DISABLE ROW LEVEL SECURITY;
    ALTER TABLE field_checks NO FORCE ROW LEVEL SECURITY; ALTER TABLE field_checks DISABLE ROW LEVEL SECURITY;
    ALTER TABLE closure_requests NO FORCE ROW LEVEL SECURITY; ALTER TABLE closure_requests DISABLE ROW LEVEL SECURITY;
    ALTER TABLE court_cases NO FORCE ROW LEVEL SECURITY; ALTER TABLE court_cases DISABLE ROW LEVEL SECURITY;
    ALTER TABLE authorised_works NO FORCE ROW LEVEL SECURITY; ALTER TABLE authorised_works DISABLE ROW LEVEL SECURITY;
    ALTER TABLE permits NO FORCE ROW LEVEL SECURITY; ALTER TABLE permits DISABLE ROW LEVEL SECURITY;
    ALTER TABLE alerts NO FORCE ROW LEVEL SECURITY; ALTER TABLE alerts DISABLE ROW LEVEL SECURITY;
    ALTER TABLE legal_checks NO FORCE ROW LEVEL SECURITY; ALTER TABLE legal_checks DISABLE ROW LEVEL SECURITY;
    ALTER TABLE observations NO FORCE ROW LEVEL SECURITY; ALTER TABLE observations DISABLE ROW LEVEL SECURITY;
    ALTER TABLE candidates NO FORCE ROW LEVEL SECURITY; ALTER TABLE candidates DISABLE ROW LEVEL SECURITY;
    ALTER TABLE boundaries NO FORCE ROW LEVEL SECURITY; ALTER TABLE boundaries DISABLE ROW LEVEL SECURITY;
    ALTER TABLE assets NO FORCE ROW LEVEL SECURITY; ALTER TABLE assets DISABLE ROW LEVEL SECURITY;
    DROP INDEX IF EXISTS ix_imagery_requests_alert_id;
    DROP INDEX IF EXISTS ix_officer_records_alert_id;
    DROP INDEX IF EXISTS ix_evidence_packs_alert_id;
    DROP INDEX IF EXISTS ix_readiness_items_alert_id;
    DROP INDEX IF EXISTS ix_owner_claims_alert_id;
    DROP INDEX IF EXISTS ix_field_checks_alert_id;
    DROP INDEX IF EXISTS ix_legal_checks_candidate_id;
    DROP INDEX IF EXISTS ix_alerts_candidate_id;
    DROP INDEX IF EXISTS ix_candidates_asset_id;
    DROP INDEX IF EXISTS ix_boundaries_asset_id;
    """)
