"""Citizen reports: the portal, WhatsApp and staff intake, and updates back to the citizen (DECISIONS.md D-062).

- `citizen_reports`: one report, with the place, what was seen, photos (metadata removed), the
  matched location and incident, and its status (RECEIVED, CHECKING, CLOSED with a reason). The
  reporter's name and phone are optional, kept only if they want updates, and removed 90 days after
  the report closes. `source_hash` is a salted hash of the network address or phone, used only for
  rate limits and to spot repeated false reports.
- `citizen_report_events`: every step, with the public note the citizen sees and the officials'
  internal note. Append-only.
- `citizen_messages`: every message to a citizen by SMS or WhatsApp, with its status. Append-only;
  the address is stored masked.
- `citizen_otps`: one-time passwords that verify a phone before updates go to it. Only hashes.
- `citizen_chats`: the state of a WhatsApp conversation. The number is kept while the chat is
  open and removed after 24 hours without a message.
- `notifications`: a new kind, `citizen_report`, tells the area's officials and the admin about a
  report. Its reminders point to the report instead of an incident.
- Every report is also a row in `signals` (CONTEXT.md section 7), kind `citizen_report`.

Revision ID: 0009
Revises: 0008
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

UP = r"""
CREATE TABLE citizen_reports (
    id                 bigserial PRIMARY KEY,
    ref                text        NOT NULL UNIQUE CHECK (ref ~ '^GGR-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$'),
    channel            text        NOT NULL CHECK (channel IN ('web', 'whatsapp', 'helpline_1070', 'praja_vani', 'walk_in')),
    language           text        NOT NULL DEFAULT 'en' CHECK (language IN ('en', 'te', 'ur')),
    what               text        NOT NULL CHECK (what IN ('dumping', 'construction', 'fencing', 'clearing', 'other')),
    description        text        CHECK (description IS NULL OR length(description) <= 1000),
    geom               geometry(Point, 4326),
    location_text      text        CHECK (location_text IS NULL OR length(location_text) <= 300),
    photos             jsonb       NOT NULL DEFAULT '[]'::jsonb,
    reporter_name      text        CHECK (reporter_name IS NULL OR length(reporter_name) <= 120),
    reporter_phone     text        CHECK (reporter_phone IS NULL OR reporter_phone ~ '^\+[1-9][0-9]{7,14}$'),
    phone_verified_via text        CHECK (phone_verified_via IN ('otp', 'whatsapp', 'staff')),
    wants_updates      boolean     NOT NULL DEFAULT false,
    source_ref         text,
    entered_by         bigint      REFERENCES users(id),
    asset_id           bigint      REFERENCES assets(id),
    zone               text        CHECK (zone IN ('inside', 'buffer', 'watch_ring', 'outside')),
    alert_id           bigint      REFERENCES alerts(id),
    duplicate_of       bigint      REFERENCES citizen_reports(id),
    status             text        NOT NULL DEFAULT 'RECEIVED' CHECK (status IN ('RECEIVED', 'CHECKING', 'CLOSED')),
    closed_reason      text        CHECK (closed_reason IN ('incident_confirmed', 'incident_dismissed', 'no_change_seen',
                                        'authorised', 'passed_on', 'not_enough', 'duplicate_closed')),
    false_report       boolean     NOT NULL DEFAULT false,
    flags              text[]      NOT NULL DEFAULT '{}',
    source_hash        text        NOT NULL,
    contact_purged_at  timestamptz,
    is_demo            boolean     NOT NULL DEFAULT false,
    created_at         timestamptz NOT NULL,
    updated_at         timestamptz NOT NULL,
    CHECK ((status = 'CLOSED') = (closed_reason IS NOT NULL)),
    CHECK (reporter_phone IS NULL OR (wants_updates AND phone_verified_via IS NOT NULL)),
    CHECK (geom IS NOT NULL OR location_text IS NOT NULL),
    CHECK (duplicate_of IS NULL OR duplicate_of <> id),
    CHECK ((channel IN ('helpline_1070', 'praja_vani', 'walk_in')) = (entered_by IS NOT NULL))
);
CREATE INDEX citizen_reports_geom ON citizen_reports USING gist (geom);
CREATE INDEX citizen_reports_open ON citizen_reports (status, created_at DESC);
CREATE INDEX citizen_reports_asset ON citizen_reports (asset_id) WHERE asset_id IS NOT NULL;
CREATE INDEX citizen_reports_alert ON citizen_reports (alert_id) WHERE alert_id IS NOT NULL;
CREATE INDEX citizen_reports_source ON citizen_reports (source_hash, created_at DESC);

CREATE TABLE citizen_report_events (
    id             bigserial PRIMARY KEY,
    report_id      bigint      NOT NULL REFERENCES citizen_reports(id),
    kind           text        NOT NULL,
    status         text        NOT NULL CHECK (status IN ('RECEIVED', 'CHECKING', 'CLOSED')),
    public_note    jsonb       NOT NULL,
    internal_note  text,
    actor_id       bigint      REFERENCES users(id),
    at             timestamptz NOT NULL
);
CREATE INDEX citizen_report_events_report ON citizen_report_events (report_id, at, id);
CREATE TRIGGER citizen_report_events_append_only BEFORE UPDATE OR DELETE ON citizen_report_events
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER citizen_report_events_no_truncate BEFORE TRUNCATE ON citizen_report_events
    FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();

CREATE TABLE citizen_chats (
    id          bigserial PRIMARY KEY,
    wa_hash     text        NOT NULL,
    wa_id       text,
    language    text        CHECK (language IN ('en', 'te', 'ur')),
    state       text        NOT NULL,
    draft       jsonb       NOT NULL DEFAULT '{}'::jsonb,
    report_id   bigint      REFERENCES citizen_reports(id),
    is_demo     boolean     NOT NULL DEFAULT false,
    updated_at  timestamptz NOT NULL
);
CREATE UNIQUE INDEX citizen_chats_once ON citizen_chats (wa_hash, is_demo);

CREATE TABLE citizen_messages (
    id          bigserial PRIMARY KEY,
    report_id   bigint      REFERENCES citizen_reports(id),
    chat_id     bigint      REFERENCES citizen_chats(id),
    direction   text        NOT NULL CHECK (direction IN ('in', 'out')),
    channel     text        NOT NULL CHECK (channel IN ('sms', 'whatsapp')),
    kind        text        NOT NULL,
    language    text        NOT NULL,
    to_masked   text,
    text        text        NOT NULL,
    status      text        NOT NULL CHECK (status IN ('received', 'queued', 'sent', 'held', 'skipped', 'failed')),
    attempt     integer     NOT NULL DEFAULT 0,
    retry_of    bigint      REFERENCES citizen_messages(id),
    detail      text,
    is_demo     boolean     NOT NULL DEFAULT false,
    at          timestamptz NOT NULL,
    CHECK (report_id IS NOT NULL OR chat_id IS NOT NULL)
);
CREATE UNIQUE INDEX citizen_messages_one_retry ON citizen_messages (retry_of) WHERE retry_of IS NOT NULL;
CREATE INDEX citizen_messages_report ON citizen_messages (report_id, id);
CREATE INDEX citizen_messages_chat ON citizen_messages (chat_id, id);
CREATE INDEX citizen_messages_queued ON citizen_messages (status, at) WHERE status IN ('queued', 'failed');
CREATE TRIGGER citizen_messages_append_only BEFORE UPDATE OR DELETE ON citizen_messages
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();

CREATE TABLE citizen_otps (
    id           bigserial PRIMARY KEY,
    phone_hash   text        NOT NULL,
    code_hash    text        NOT NULL,
    attempts     integer     NOT NULL DEFAULT 0,
    expires_at   timestamptz NOT NULL,
    verified_at  timestamptz,
    is_demo      boolean     NOT NULL DEFAULT false,
    created_at   timestamptz NOT NULL
);
CREATE INDEX citizen_otps_phone ON citizen_otps (phone_hash, created_at DESC);

-- Notifications about a citizen report --------------------------------------------------------
ALTER TYPE notification_kind ADD VALUE IF NOT EXISTS 'citizen_report';
ALTER TABLE notifications ADD COLUMN report_id bigint REFERENCES citizen_reports(id);
DO $$
DECLARE c record;
BEGIN
    FOR c IN SELECT conname FROM pg_constraint
             WHERE conrelid = 'notifications'::regclass AND contype = 'c'
               AND (pg_get_constraintdef(oid) LIKE '%alert_id IS NULL%' OR pg_get_constraintdef(oid) LIKE '%about_id IS NOT NULL%')
    LOOP
        EXECUTE format('ALTER TABLE notifications DROP CONSTRAINT %I', c.conname);
    END LOOP;
END $$;
-- kind::text, because a new enum value cannot be used in the transaction that adds it.
ALTER TABLE notifications
    ADD CONSTRAINT notifications_digest_alone CHECK (kind::text <> 'weekly_digest' OR (alert_id IS NULL AND report_id IS NULL)),
    ADD CONSTRAINT notifications_incident_has_alert CHECK (kind::text NOT IN ('incident_opened', 'incident_decided') OR (alert_id IS NOT NULL AND report_id IS NULL)),
    ADD CONSTRAINT notifications_report_has_report CHECK (kind::text <> 'citizen_report' OR (report_id IS NOT NULL AND alert_id IS NULL)),
    ADD CONSTRAINT notifications_follow_up_about CHECK ((kind::text IN ('reminder', 'not_acknowledged')) = (about_id IS NOT NULL)),
    ADD CONSTRAINT notifications_follow_up_one CHECK (kind::text NOT IN ('reminder', 'not_acknowledged') OR ((alert_id IS NULL) <> (report_id IS NULL)));
-- One citizen_report notification per person and report (its reminders carry about_id).
CREATE UNIQUE INDEX notifications_once_per_report ON notifications (user_id, report_id) WHERE report_id IS NOT NULL AND about_id IS NULL;
CREATE INDEX notifications_report ON notifications (report_id) WHERE report_id IS NOT NULL;

CREATE OR REPLACE FUNCTION lp_notification_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'notifications are kept: notification % cannot be deleted', OLD.id
            USING ERRCODE = 'restrict_violation';
    END IF;
    IF OLD.acknowledged_at IS NOT NULL THEN
        RAISE EXCEPTION 'notification % is already acknowledged', OLD.id
            USING ERRCODE = 'restrict_violation';
    END IF;
    IF (NEW.id, NEW.user_id, NEW.kind, NEW.alert_id, NEW.report_id, NEW.week, NEW.about_id, NEW.subject, NEW.body,
        NEW.payload, NEW.needs_ack, NEW.created_at, NEW.is_demo)
       IS DISTINCT FROM
       (OLD.id, OLD.user_id, OLD.kind, OLD.alert_id, OLD.report_id, OLD.week, OLD.about_id, OLD.subject, OLD.body,
        OLD.payload, OLD.needs_ack, OLD.created_at, OLD.is_demo) THEN
        RAISE EXCEPTION 'only the acknowledgement of notification % can change', OLD.id
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END $$;
ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_ack_via_check;
ALTER TABLE notifications ADD CONSTRAINT notifications_ack_via_check CHECK (ack_via IN ('inbox', 'review', 'decision', 'report_check'));
"""

# Going down removes what only 0009 can hold: notifications about citizen reports and their
# delivery rows. Both tables are guarded, so the guards are lifted for that one delete.
DOWN = r"""
ALTER TABLE notification_deliveries DISABLE TRIGGER notification_deliveries_append_only;
DELETE FROM notification_deliveries WHERE notification_id IN (SELECT id FROM notifications WHERE report_id IS NOT NULL);
ALTER TABLE notification_deliveries ENABLE TRIGGER notification_deliveries_append_only;
ALTER TABLE notifications DISABLE TRIGGER notifications_guard;
DELETE FROM notifications WHERE report_id IS NOT NULL;
ALTER TABLE notifications ENABLE TRIGGER notifications_guard;
ALTER TABLE notifications DROP CONSTRAINT notifications_ack_via_check;
ALTER TABLE notifications ADD CONSTRAINT notifications_ack_via_check CHECK (ack_via IN ('inbox', 'review', 'decision'));
DROP INDEX notifications_once_per_report;
DROP INDEX notifications_report;
ALTER TABLE notifications
    DROP CONSTRAINT notifications_digest_alone, DROP CONSTRAINT notifications_incident_has_alert,
    DROP CONSTRAINT notifications_report_has_report, DROP CONSTRAINT notifications_follow_up_about,
    DROP CONSTRAINT notifications_follow_up_one;
ALTER TABLE notifications
    ADD CHECK ((kind = 'weekly_digest') = (alert_id IS NULL)),
    ADD CHECK ((kind IN ('reminder', 'not_acknowledged')) = (about_id IS NOT NULL));
ALTER TABLE notifications DROP COLUMN report_id;
CREATE OR REPLACE FUNCTION lp_notification_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'notifications are kept: notification % cannot be deleted', OLD.id
            USING ERRCODE = 'restrict_violation';
    END IF;
    IF OLD.acknowledged_at IS NOT NULL THEN
        RAISE EXCEPTION 'notification % is already acknowledged', OLD.id
            USING ERRCODE = 'restrict_violation';
    END IF;
    IF (NEW.id, NEW.user_id, NEW.kind, NEW.alert_id, NEW.week, NEW.about_id, NEW.subject, NEW.body,
        NEW.payload, NEW.needs_ack, NEW.created_at, NEW.is_demo)
       IS DISTINCT FROM
       (OLD.id, OLD.user_id, OLD.kind, OLD.alert_id, OLD.week, OLD.about_id, OLD.subject, OLD.body,
        OLD.payload, OLD.needs_ack, OLD.created_at, OLD.is_demo) THEN
        RAISE EXCEPTION 'only the acknowledgement of notification % can change', OLD.id
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END $$;
DELETE FROM signals WHERE kind = 'citizen_report';
DROP TABLE citizen_otps;
DROP TABLE citizen_messages;
DROP TABLE citizen_chats;
DROP TABLE citizen_report_events;
DROP TABLE citizen_reports;
"""
# The 'citizen_report' notification kind stays in the enum, unused, as 0006 and 0008 left theirs.


def run_raw(sql: str) -> None:
    with op.get_bind().connection.dbapi_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    run_raw(UP)


def downgrade() -> None:
    run_raw(DOWN)
