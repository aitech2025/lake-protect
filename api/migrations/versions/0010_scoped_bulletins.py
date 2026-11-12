"""Scope saved monthly bulletins to their generating user.
Revision ID: 0010
Revises: 0009
"""
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE bulletins
      ADD COLUMN scope_user_id bigint REFERENCES users(id);

    -- A bulletin is calculated from the caller's department-visible records.
    -- Keep saved snapshots private to that user; auditors/admins can inspect all.
    CREATE POLICY legacy_bulletins_scope_read ON bulletins FOR SELECT
      USING (lp_is_auditor() OR scope_user_id = lp_current_user_id());

    CREATE POLICY legacy_bulletins_scope_insert ON bulletins FOR INSERT
      WITH CHECK (lp_is_auditor() OR scope_user_id = lp_current_user_id());

    CREATE INDEX ix_bulletins_scope_user ON bulletins(scope_user_id, generated_at DESC);
    """)


def downgrade():
    op.execute("""
    DROP POLICY IF EXISTS legacy_bulletins_scope_insert ON bulletins;
    DROP POLICY IF EXISTS legacy_bulletins_scope_read ON bulletins;
    DROP INDEX IF EXISTS ix_bulletins_scope_user;
    ALTER TABLE bulletins DROP COLUMN IF EXISTS scope_user_id;
    """)
