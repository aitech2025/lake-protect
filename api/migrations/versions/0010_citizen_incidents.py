"""Every citizen report opens an incident with a satellite review (DECISIONS.md D-063); no Urdu.

- `alerts.origin`: 'satellite' (the weekly screen) or 'citizen' (a report), and `alerts.report_id`
  for the report that opened it. A citizen incident is never closed by the legal check on its own:
  an official always reviews it.
- `sensor_basis` 'citizen_report': the candidate of a citizen incident is the reported spot, not a
  change the satellite measured. The satellite review is kept beside it.
- Asset type 'reported_place': a place outside every watched location, made from a report so the
  incident has a place and a boundary. It is not on the weekly watch until the admin starts it.
- `satellite_reviews`: one per citizen incident. Pending until the screener (real data) or the demo
  world (demo data) looks at the place; then the result, the dates and the before and after images.
- `citizen_reports.placed_by`: how the place was found: the citizen's pin, the place named in their
  words, or an official.
- Notification kind 'satellite_review': the result, to the people told about the incident.
- Languages: English and Telugu only. Urdu rows become English.

Revision ID: 0010
Revises: 0009
"""
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

UP = r"""
ALTER TYPE sensor_basis ADD VALUE IF NOT EXISTS 'citizen_report';
ALTER TYPE asset_type ADD VALUE IF NOT EXISTS 'reported_place';
ALTER TYPE notification_kind ADD VALUE IF NOT EXISTS 'satellite_review';

ALTER TABLE alerts
    ADD COLUMN origin text NOT NULL DEFAULT 'satellite' CHECK (origin IN ('satellite', 'citizen')),
    ADD COLUMN report_id bigint UNIQUE REFERENCES citizen_reports(id),
    ADD CONSTRAINT alerts_origin_report CHECK ((origin = 'citizen') = (report_id IS NOT NULL));

ALTER TABLE citizen_reports
    ADD COLUMN placed_by text CHECK (placed_by IN ('pin', 'description', 'official'));
UPDATE citizen_reports SET placed_by = 'pin' WHERE geom IS NOT NULL;

CREATE TABLE satellite_reviews (
    id            bigserial PRIMARY KEY,
    alert_id      bigint      NOT NULL UNIQUE REFERENCES alerts(id),
    status        text        NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'done', 'failed')),
    result        text        CHECK (result IN ('change_found', 'no_change', 'no_clear_look')),
    source        text        NOT NULL CHECK (source IN ('sentinel-2', 'demo-synthetic')),
    requested_at  timestamptz NOT NULL,
    done_at       timestamptz,
    as_of         date,
    before_date   date,
    after_date    date,
    scenes        jsonb       NOT NULL DEFAULT '[]'::jsonb,
    before_chip   text,
    after_chip    text,
    change_type   text,
    change_area_sq_m numeric(14, 2),
    first_changed_at date,
    detail        text,
    attempts      integer     NOT NULL DEFAULT 0,
    is_demo       boolean     NOT NULL DEFAULT false,
    CHECK ((status = 'done') = (result IS NOT NULL)),
    CHECK ((status = 'pending') = (done_at IS NULL))
);
CREATE INDEX satellite_reviews_pending ON satellite_reviews (requested_at) WHERE status = 'pending';

-- English and Telugu only. The public notes already written keep their Urdu text; it is not shown.
UPDATE citizen_reports SET language = 'en' WHERE language = 'ur';
UPDATE citizen_chats SET language = 'en' WHERE language = 'ur';
ALTER TABLE citizen_reports DROP CONSTRAINT citizen_reports_language_check;
ALTER TABLE citizen_reports ADD CONSTRAINT citizen_reports_language_check CHECK (language IN ('en', 'te'));
ALTER TABLE citizen_chats DROP CONSTRAINT citizen_chats_language_check;
ALTER TABLE citizen_chats ADD CONSTRAINT citizen_chats_language_check CHECK (language IN ('en', 'te'));
"""

# The enum values stay, unused, as earlier migrations left theirs. Citizen incidents go with the
# reports: the demo reset drops everything below anyway.
DOWN = r"""
ALTER TABLE citizen_chats DROP CONSTRAINT citizen_chats_language_check;
ALTER TABLE citizen_chats ADD CONSTRAINT citizen_chats_language_check CHECK (language IN ('en', 'te', 'ur'));
ALTER TABLE citizen_reports DROP CONSTRAINT citizen_reports_language_check;
ALTER TABLE citizen_reports ADD CONSTRAINT citizen_reports_language_check CHECK (language IN ('en', 'te', 'ur'));
DROP TABLE satellite_reviews;
ALTER TABLE citizen_reports DROP COLUMN placed_by;
ALTER TABLE alerts DROP CONSTRAINT alerts_origin_report, DROP COLUMN report_id, DROP COLUMN origin;
"""


def run_raw(sql: str) -> None:
    with op.get_bind().connection.dbapi_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    run_raw(UP)


def downgrade() -> None:
    run_raw(DOWN)
