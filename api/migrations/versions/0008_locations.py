"""Locations the admin adds and stops watching, and the land categories to come (DECISIONS.md D-061).

- Two asset types for the planned categories: endowment land and forest land. They are listed in
  app/categories.yaml as planned, and the API refuses them until a category is switched to live.
- `assets.monitored`: whether the weekly screen watches the asset. It changes only through a row
  in `monitoring_changes`, which records who, when and why, and is append-only. Nothing about an
  asset is ever deleted: boundaries, weekly records, incidents and documents stay.
- `assets.added_by`, `assets.added_at`: set when the admin adds a location by hand.

Revision ID: 0008
Revises: 0007
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

UP = r"""
ALTER TYPE asset_type ADD VALUE IF NOT EXISTS 'endowment_land';
ALTER TYPE asset_type ADD VALUE IF NOT EXISTS 'forest_land';

ALTER TABLE assets
    ADD COLUMN monitored boolean NOT NULL DEFAULT true,
    ADD COLUMN added_by  bigint REFERENCES users(id),
    ADD COLUMN added_at  timestamptz;

CREATE TABLE monitoring_changes (
    id        bigserial PRIMARY KEY,
    asset_id  bigint      NOT NULL REFERENCES assets(id),
    monitored boolean     NOT NULL,
    reason    text        NOT NULL CHECK (length(btrim(reason)) >= 5),
    actor_id  bigint      REFERENCES users(id),
    at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX monitoring_changes_asset ON monitoring_changes (asset_id, at DESC, id DESC);
CREATE TRIGGER monitoring_changes_append_only BEFORE UPDATE OR DELETE ON monitoring_changes
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER monitoring_changes_no_truncate BEFORE TRUNCATE ON monitoring_changes
    FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();

-- A logged change is applied to the asset ...
CREATE FUNCTION lp_monitoring_apply() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    UPDATE assets SET monitored = NEW.monitored WHERE id = NEW.asset_id;
    RETURN NEW;
END $$;
CREATE TRIGGER monitoring_changes_apply AFTER INSERT ON monitoring_changes
    FOR EACH ROW EXECUTE FUNCTION lp_monitoring_apply();

-- ... and is the only way to change it.
CREATE FUNCTION lp_monitored_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.monitored IS DISTINCT FROM OLD.monitored AND pg_trigger_depth() < 2 THEN
        RAISE EXCEPTION 'Whether an asset is watched changes only through monitoring_changes'
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER assets_monitored_guard BEFORE UPDATE OF monitored ON assets
    FOR EACH ROW EXECUTE FUNCTION lp_monitored_guard();
"""

# The two asset type values stay, unused, as migration 0006 left 'levelling': Postgres cannot drop
# an enum value, and the full reset drops the type in 0002.
DOWN = r"""
DROP TRIGGER assets_monitored_guard ON assets;
DROP FUNCTION lp_monitored_guard();
DROP TABLE monitoring_changes;
DROP FUNCTION lp_monitoring_apply();
ALTER TABLE assets DROP COLUMN monitored, DROP COLUMN added_by, DROP COLUMN added_at;
"""


def run_raw(sql: str) -> None:
    with op.get_bind().connection.dbapi_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    run_raw(UP)


def downgrade() -> None:
    run_raw(DOWN)
