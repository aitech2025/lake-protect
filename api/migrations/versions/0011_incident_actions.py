"""What officials do on a citizen's incident (DECISIONS.md D-064).

- `incident_notes`: acknowledgements and notes by officials or the admin. Append-only; one
  acknowledgement per person per incident.
- `satellite_reviews`: an incident may now have several looks. The first is 'automatic' (the review
  when the report arrives). Officials may request more, for the latest image or a past date
  (`look_date`), to compare.
- `imagery_requests`: a request for a sharper paid image is 'requested' by an official, then
  'approved' or 'declined' by the admin, with a note. Nothing is ordered in the prototype.
- `incident_legal_records`: snapshots of the legal records at the incident's place (land records,
  boundary and its notification, legal documents, court cases, permits and works, the legal
  check), attached by an official. Append-only: a new snapshot never replaces an earlier one.
- `asset_documents.alert_id`: a legal document attached to an incident is also the location's.

Revision ID: 0011
Revises: 0010
"""
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

UP = r"""
CREATE TABLE incident_notes (
    id         bigserial PRIMARY KEY,
    alert_id   bigint      NOT NULL REFERENCES alerts(id),
    author_id  bigint      NOT NULL REFERENCES users(id),
    kind       text        NOT NULL CHECK (kind IN ('note', 'acknowledged')),
    text       text        NOT NULL CHECK (length(btrim(text)) > 0 AND length(text) <= 2000),
    at         timestamptz NOT NULL,
    is_demo    boolean     NOT NULL DEFAULT false
);
CREATE INDEX incident_notes_alert ON incident_notes (alert_id, id);
CREATE UNIQUE INDEX incident_notes_ack_once ON incident_notes (alert_id, author_id) WHERE kind = 'acknowledged';
CREATE TRIGGER incident_notes_append_only BEFORE UPDATE OR DELETE ON incident_notes
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER incident_notes_no_truncate BEFORE TRUNCATE ON incident_notes
    FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();

ALTER TABLE satellite_reviews DROP CONSTRAINT satellite_reviews_alert_id_key;
ALTER TABLE satellite_reviews
    ADD COLUMN kind text NOT NULL DEFAULT 'automatic' CHECK (kind IN ('automatic', 'requested')),
    ADD COLUMN requested_by bigint REFERENCES users(id),
    ADD COLUMN look_date date,
    ADD CONSTRAINT satellite_reviews_requested_by CHECK ((kind = 'requested') = (requested_by IS NOT NULL));
CREATE UNIQUE INDEX satellite_reviews_one_automatic ON satellite_reviews (alert_id) WHERE kind = 'automatic';
CREATE INDEX satellite_reviews_alert ON satellite_reviews (alert_id, id);

ALTER TABLE imagery_requests
    ADD COLUMN note text,
    ADD COLUMN decided_by bigint REFERENCES users(id),
    ADD COLUMN decided_at timestamptz,
    ADD COLUMN decision_note text,
    ADD CONSTRAINT imagery_requests_status CHECK (status IN ('recorded', 'requested', 'approved', 'declined')),
    ADD CONSTRAINT imagery_requests_decided CHECK ((status IN ('approved', 'declined')) = (decided_by IS NOT NULL));

CREATE TABLE incident_legal_records (
    id           bigserial PRIMARY KEY,
    alert_id     bigint      NOT NULL REFERENCES alerts(id),
    attached_by  bigint      NOT NULL REFERENCES users(id),
    at           timestamptz NOT NULL,
    records      jsonb       NOT NULL,
    is_demo      boolean     NOT NULL DEFAULT false
);
CREATE INDEX incident_legal_records_alert ON incident_legal_records (alert_id, id);
CREATE TRIGGER incident_legal_records_append_only BEFORE UPDATE OR DELETE ON incident_legal_records
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();

ALTER TABLE asset_documents ADD COLUMN alert_id bigint REFERENCES alerts(id);
"""

DOWN = r"""
ALTER TABLE asset_documents DROP COLUMN alert_id;
DROP TABLE incident_legal_records;
ALTER TABLE imagery_requests
    DROP CONSTRAINT imagery_requests_decided, DROP CONSTRAINT imagery_requests_status,
    DROP COLUMN decision_note, DROP COLUMN decided_at, DROP COLUMN decided_by, DROP COLUMN note;
DELETE FROM satellite_reviews WHERE kind = 'requested';
DROP INDEX satellite_reviews_alert;
DROP INDEX satellite_reviews_one_automatic;
ALTER TABLE satellite_reviews DROP CONSTRAINT satellite_reviews_requested_by,
    DROP COLUMN look_date, DROP COLUMN requested_by, DROP COLUMN kind;
ALTER TABLE satellite_reviews ADD CONSTRAINT satellite_reviews_alert_id_key UNIQUE (alert_id);
DROP TABLE incident_notes;
"""


def run_raw(sql: str) -> None:
    with op.get_bind().connection.dbapi_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    run_raw(UP)


def downgrade() -> None:
    run_raw(DOWN)
