"""Give authorized auditors complete read access to the global audit chain.
Revision ID: 0009
Revises: 0008
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE FUNCTION lp_is_auditor() RETURNS boolean LANGUAGE sql STABLE AS $$
      SELECT COALESCE(NULLIF(current_setting('lp.is_auditor', true), '')::boolean, false)
    $$;

    -- The audit chain is global: filtering rows for auditors would create false
    -- verification failures because prev_hash links include events from other departments.
    CREATE POLICY legacy_audit_log_auditor_read ON audit_log FOR SELECT
      USING (lp_is_auditor());

    -- The closure-sample audit screen joins the global chain to alerts.
    -- Auditors receive read-only statewide visibility; writes remain role-gated.
    CREATE POLICY legacy_alerts_auditor_read ON alerts FOR SELECT
      USING (lp_is_auditor());
    """)


def downgrade():
    op.execute("""
    DROP POLICY IF EXISTS legacy_alerts_auditor_read ON alerts;
    DROP POLICY IF EXISTS legacy_audit_log_auditor_read ON audit_log;
    DROP FUNCTION IF EXISTS lp_is_auditor();
    """)
