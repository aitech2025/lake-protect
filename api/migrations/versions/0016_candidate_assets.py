"""Represent unknown citizen-reported locations as candidate assets, not registry assets.

Revision ID: 0016
Revises: 0015
"""
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE candidate_assets (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      candidate_code text NOT NULL UNIQUE,
      source_report_id bigint NOT NULL UNIQUE REFERENCES citizen_reports(id),
      support_asset_id bigint NOT NULL UNIQUE REFERENCES assets(id),
      detection_candidate_id bigint NOT NULL UNIQUE REFERENCES candidates(id),
      incident_id bigint NOT NULL UNIQUE REFERENCES alerts(id),
      display_name text NOT NULL,
      category_hint text NOT NULL,
      district text,
      mandal text,
      village text,
      footprint geometry(MultiPolygon,4326) NOT NULL,
      status text NOT NULL DEFAULT 'PENDING_VERIFICATION',
      provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
      is_demo boolean NOT NULL DEFAULT false,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX ix_candidate_assets_status_created ON candidate_assets(status, created_at DESC);
    CREATE INDEX ix_candidate_assets_footprint ON candidate_assets USING GIST(footprint);
    ALTER TABLE citizen_reports ADD COLUMN candidate_asset_id uuid REFERENCES candidate_assets(id);
    UPDATE public_assets SET lifecycle_status = 'UNDER_REVIEW' WHERE category_code = 'reported_place';
    """)


def downgrade():
    op.execute("""
    ALTER TABLE citizen_reports DROP COLUMN IF EXISTS candidate_asset_id;
    DROP TABLE IF EXISTS candidate_assets CASCADE;
    """)
