"""Asset creation engine: source snapshots, import runs, source links and land parcels.

Government data arrives as files (an officer's drop, or the fictional samples) or, once a
data-sharing agreement exists, from an official API. Every file received is a snapshot with its
hash. Every run is recorded with what it did to each record. Each asset keeps the IDs other
departments use for it. Survey-number parcels carry land category and extent, never owner names:
the table has no column for them (CONTEXT.md 17.10).

Boundaries gain the snapshot they came from and their positional accuracy in metres
(docs/asset-load.md section 3).

All four new tables are append-only.

Revision ID: 0005
Revises: 0004
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

BOUNDARY_VERSIONS_VIEW = r"""
CREATE VIEW boundary_versions AS
SELECT b.*,
       n.id AS superseded_by_id,
       COALESCE(b.valid_to, n.valid_from) AS effective_valid_to
FROM boundaries b
LEFT JOIN LATERAL (
    SELECT x.id, x.valid_from FROM boundaries x WHERE x.supersedes_id = b.id ORDER BY x.version LIMIT 1
) n ON true;
"""

SQL = r"""
CREATE TABLE source_snapshots (
    id               bigserial PRIMARY KEY,
    connector        text        NOT NULL,
    agency           text        NOT NULL,
    dataset          text        NOT NULL,
    transport        text        NOT NULL CHECK (transport IN ('file_drop', 'api', 'sample')),
    file_name        text        NOT NULL,
    content_type     text        NOT NULL,
    received_sha256  varchar(64) NOT NULL,
    sha256           varchar(64) NOT NULL,
    byte_size        bigint      NOT NULL CHECK (byte_size >= 0),
    storage_key      text        NOT NULL,
    source_date      date        NOT NULL,
    reference        text,
    agreement_ref    text,
    licence_note     text        NOT NULL,
    is_sample        boolean     NOT NULL,
    stripped_fields  text[]      NOT NULL DEFAULT '{}',
    record_count     integer     NOT NULL DEFAULT 0,
    received_at      timestamptz NOT NULL DEFAULT now(),
    received_by      bigint REFERENCES users(id),
    CHECK ((transport = 'sample') = is_sample),
    CHECK (transport <> 'api' OR agreement_ref IS NOT NULL),
    UNIQUE (connector, dataset, received_sha256)
);

CREATE TABLE import_runs (
    id            bigserial PRIMARY KEY,
    connector     text        NOT NULL,
    transport     text        NOT NULL CHECK (transport IN ('file_drop', 'api', 'sample')),
    is_sample     boolean     NOT NULL,
    started_at    timestamptz NOT NULL,
    finished_at   timestamptz NOT NULL,
    actor_id      bigint REFERENCES users(id),
    snapshot_ids  bigint[]    NOT NULL DEFAULT '{}',
    counts        jsonb       NOT NULL DEFAULT '{}'::jsonb,
    items         jsonb       NOT NULL DEFAULT '[]'::jsonb,
    CHECK (finished_at >= started_at)
);

CREATE TABLE asset_source_links (
    id           bigserial PRIMARY KEY,
    asset_id     bigint      NOT NULL REFERENCES assets(id),
    connector    text        NOT NULL,
    external_id  text        NOT NULL,
    snapshot_id  bigint      NOT NULL REFERENCES source_snapshots(id),
    matched_by   text        NOT NULL CHECK (matched_by IN ('created', 'crosswalk', 'spatial')),
    linked_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (connector, external_id)
);
CREATE INDEX asset_source_links_asset ON asset_source_links (asset_id);

CREATE TABLE land_parcels (
    id                     bigserial PRIMARY KEY,
    snapshot_id            bigint  NOT NULL REFERENCES source_snapshots(id),
    district               text    NOT NULL,
    mandal                 text    NOT NULL,
    village                text    NOT NULL,
    survey_no              text    NOT NULL,
    sub_division           text    NOT NULL DEFAULT '',
    bhudhaar               text,
    land_category          text    NOT NULL CHECK (land_category IN (
                               'government', 'tank', 'shikam', 'assigned', 'patta', 'inam',
                               'endowment', 'wakf', 'forest', 'unknown')),
    recorded_category      text,
    extent_acres           numeric(12, 4),
    positional_accuracy_m  numeric(8, 2) CHECK (positional_accuracy_m > 0),
    geom                   geometry(MultiPolygon, 4326) NOT NULL,
    is_sample              boolean NOT NULL,
    UNIQUE (snapshot_id, district, mandal, village, survey_no, sub_division)
);
CREATE INDEX land_parcels_geom ON land_parcels USING gist (geom);

-- The parcels in force for a village are those of the newest snapshot that covers it.
CREATE VIEW land_parcels_current AS
SELECT p.*
FROM land_parcels p
JOIN (SELECT district, mandal, village, max(snapshot_id) AS snapshot_id
      FROM land_parcels GROUP BY district, mandal, village) latest
  USING (district, mandal, village, snapshot_id);

DROP VIEW boundary_versions;
ALTER TABLE boundaries
    ADD COLUMN source_snapshot_id bigint REFERENCES source_snapshots(id),
    ADD COLUMN positional_accuracy_m numeric(8, 2) CHECK (positional_accuracy_m > 0);
""" + BOUNDARY_VERSIONS_VIEW + r"""
CREATE TRIGGER source_snapshots_append_only BEFORE UPDATE OR DELETE ON source_snapshots
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER source_snapshots_no_truncate BEFORE TRUNCATE ON source_snapshots
    FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER import_runs_append_only BEFORE UPDATE OR DELETE ON import_runs
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER import_runs_no_truncate BEFORE TRUNCATE ON import_runs
    FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER asset_source_links_append_only BEFORE UPDATE OR DELETE ON asset_source_links
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER asset_source_links_no_truncate BEFORE TRUNCATE ON asset_source_links
    FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER land_parcels_append_only BEFORE UPDATE OR DELETE ON land_parcels
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER land_parcels_no_truncate BEFORE TRUNCATE ON land_parcels
    FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();
"""

DOWN = r"""
DROP VIEW land_parcels_current;
DROP TABLE land_parcels;
DROP TABLE asset_source_links;
DROP TABLE import_runs;
DROP VIEW boundary_versions;
ALTER TABLE boundaries DROP COLUMN source_snapshot_id, DROP COLUMN positional_accuracy_m;
""" + BOUNDARY_VERSIONS_VIEW + r"""
DROP TABLE source_snapshots;
"""


def run_raw(sql: str) -> None:
    with op.get_bind().connection.dbapi_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    run_raw(SQL)


def downgrade() -> None:
    run_raw(DOWN)
