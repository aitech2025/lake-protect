"""Append-only field inspection records attached to registered assets.

Revision ID: 0018
Revises: 0017
"""
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE asset_inspections (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        asset_id bigint NOT NULL REFERENCES assets(id) ON DELETE RESTRICT,
        alert_id bigint REFERENCES alerts(id) ON DELETE RESTRICT,
        inspector_id bigint NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
        observed_at timestamptz NOT NULL,
        lat double precision CHECK (lat BETWEEN -90 AND 90),
        lon double precision CHECK (lon BETWEEN -180 AND 180),
        outcome field_outcome NOT NULL,
        notes text NOT NULL CHECK (length(btrim(notes)) > 0),
        photo_paths text[] NOT NULL DEFAULT '{}',
        photo_sha256 text[] NOT NULL DEFAULT '{}',
        created_at timestamptz NOT NULL DEFAULT now(),
        CHECK (cardinality(photo_paths) = cardinality(photo_sha256))
    );
    CREATE INDEX ix_asset_inspections_asset ON asset_inspections(asset_id, observed_at DESC, id DESC);
    CREATE TRIGGER asset_inspections_append_only BEFORE UPDATE OR DELETE ON asset_inspections
        FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
    CREATE TRIGGER asset_inspections_no_truncate BEFORE TRUNCATE ON asset_inspections
        FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();
    """)


def downgrade() -> None:
    op.execute("""
    DROP TRIGGER IF EXISTS asset_inspections_no_truncate ON asset_inspections;
    DROP TRIGGER IF EXISTS asset_inspections_append_only ON asset_inspections;
    DROP TABLE IF EXISTS asset_inspections;
    """)
