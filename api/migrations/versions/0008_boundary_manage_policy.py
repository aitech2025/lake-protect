"""Allow department MANAGE members to add immutable boundary versions.
Revision ID: 0008
Revises: 0007
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE POLICY legacy_boundaries_department_insert ON boundaries FOR INSERT
      WITH CHECK (EXISTS (
        SELECT 1
        FROM public_assets pa
        JOIN asset_responsibilities ar ON ar.asset_id = pa.id
        JOIN user_department_access uda ON uda.department_id = ar.department_id
        WHERE pa.legacy_asset_id = boundaries.asset_id
          AND uda.user_id = lp_current_user_id()
          AND uda.access_level = 'MANAGE'
          AND uda.valid_from <= CURRENT_DATE
          AND (uda.valid_to IS NULL OR uda.valid_to > CURRENT_DATE)
          AND ar.valid_from <= CURRENT_DATE
          AND (ar.valid_to IS NULL OR ar.valid_to > CURRENT_DATE)
      ));
    """)


def downgrade():
    op.execute("DROP POLICY IF EXISTS legacy_boundaries_department_insert ON boundaries;")
