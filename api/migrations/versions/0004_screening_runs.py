"""Screening runs and per-asset coverage (the weekly screen from space).

Every run of `lp screen` is recorded with its rule version and the hash of its rule file, and
every asset gets one coverage row per run: not observed, no usable look, failed, screened with
no candidate, or candidate found. The system never says "no encroachment" where no valid look
exists. Both tables are append-only.

Revision ID: 0004
Revises: 0003
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

SQL = r"""
CREATE TABLE screen_runs (
    id            bigserial PRIMARY KEY,
    as_of         date        NOT NULL,
    rule_version  text        NOT NULL,
    rules_sha256  varchar(64) NOT NULL,
    collection    text        NOT NULL,
    started_at    timestamptz NOT NULL,
    finished_at   timestamptz NOT NULL,
    received_at   timestamptz NOT NULL DEFAULT now(),
    assets_total  integer     NOT NULL,
    outcomes      jsonb       NOT NULL DEFAULT '{}'::jsonb,
    CHECK (finished_at >= started_at)
);

CREATE TABLE asset_screens (
    id              bigserial PRIMARY KEY,
    run_id          bigint  NOT NULL REFERENCES screen_runs(id),
    asset_id        bigint  NOT NULL REFERENCES assets(id),
    status          text    NOT NULL CHECK (status IN ('not_observed', 'no_usable_look', 'failed', 'no_candidate', 'candidate_found')),
    looks           integer NOT NULL CHECK (looks >= 0),
    first_look      date,
    last_look       date,
    candidates      integer NOT NULL DEFAULT 0,
    legacy_changes  integer NOT NULL DEFAULT 0,
    counts          jsonb   NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (run_id, asset_id)
);
CREATE INDEX asset_screens_latest ON asset_screens (asset_id, run_id DESC);

CREATE TRIGGER screen_runs_append_only BEFORE UPDATE OR DELETE ON screen_runs
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER screen_runs_no_truncate BEFORE TRUNCATE ON screen_runs
    FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER asset_screens_append_only BEFORE UPDATE OR DELETE ON asset_screens
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER asset_screens_no_truncate BEFORE TRUNCATE ON asset_screens
    FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();
"""


def upgrade() -> None:
    op.execute(SQL)


def downgrade() -> None:
    op.execute("DROP TABLE asset_screens; DROP TABLE screen_runs;")
