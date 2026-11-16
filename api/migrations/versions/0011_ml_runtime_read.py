"""Allow pipeline inference to read only the deployed model version.
Revision ID: 0011
Revises: 0010
"""
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE INDEX ix_ml_model_versions_runtime
      ON ml_model_versions(task_type, status, approved_at DESC);
    CREATE UNIQUE INDEX uq_ml_one_production_model_per_task
      ON ml_model_versions(task_type) WHERE status='PRODUCTION';

    -- Pipeline credentials may read only a model explicitly promoted to PRODUCTION.
    -- Registry writes and evaluation records remain platform-admin only.
    CREATE POLICY ml_model_versions_pipeline_runtime_read
      ON ml_model_versions FOR SELECT
      USING (lp_is_pipeline_ingest() AND status = 'PRODUCTION');
    """)


def downgrade():
    op.execute("""
    DROP POLICY IF EXISTS ml_model_versions_pipeline_runtime_read ON ml_model_versions;
    DROP INDEX IF EXISTS uq_ml_one_production_model_per_task;
    DROP INDEX IF EXISTS ix_ml_model_versions_runtime;
    """)
