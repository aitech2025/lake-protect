"""Durable outbox dispatch leases and worker-scoped RLS.
Revision ID: 0006
Revises: 0005
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE outbox_events
      ADD COLUMN next_attempt_at timestamptz,
      ADD COLUMN claimed_by uuid,
      ADD COLUMN claimed_at timestamptz,
      ADD COLUMN dead_lettered_at timestamptz;

    CREATE INDEX ix_outbox_dispatch
      ON outbox_events(COALESCE(next_attempt_at, occurred_at), occurred_at)
      WHERE published_at IS NULL AND dead_lettered_at IS NULL;

    CREATE FUNCTION lp_is_outbox_worker() RETURNS boolean LANGUAGE sql STABLE AS $$
      SELECT COALESCE(NULLIF(current_setting('lp.outbox_worker', true), '')::boolean, false)
    $$;

    CREATE POLICY outbox_events_worker_read ON outbox_events FOR SELECT
      USING (lp_is_outbox_worker());
    CREATE POLICY outbox_events_worker_update ON outbox_events FOR UPDATE
      USING (lp_is_outbox_worker()) WITH CHECK (lp_is_outbox_worker());
    """)


def downgrade():
    op.execute("""
    DROP POLICY IF EXISTS outbox_events_worker_update ON outbox_events;
    DROP POLICY IF EXISTS outbox_events_worker_read ON outbox_events;
    DROP FUNCTION IF EXISTS lp_is_outbox_worker();
    DROP INDEX IF EXISTS ix_outbox_dispatch;
    ALTER TABLE outbox_events
      DROP COLUMN IF EXISTS dead_lettered_at,
      DROP COLUMN IF EXISTS claimed_at,
      DROP COLUMN IF EXISTS claimed_by,
      DROP COLUMN IF EXISTS next_attempt_at;
    """)
