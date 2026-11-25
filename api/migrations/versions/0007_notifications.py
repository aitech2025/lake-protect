"""Notifications to officials by area, acknowledgements and the delivery log (DECISIONS.md D-059).

- Officials (and the admin) get a work email, a phone number and the channels they want: in the
  app always, then email, SMS and WhatsApp. Only the admin sees or changes these.
- `official_areas`: the districts, or mandals within a district, each official covers. An incident
  notifies the officials whose area holds its asset, and every admin.
- `notifications`: one row per person per event. A row is never deleted or edited; the only change
  allowed is its acknowledgement, once.
- `notification_deliveries`: every attempt on every outside channel, append-only. The latest row
  per notification and channel is its status: queued, sent, held (the channel is not set up),
  failed, or skipped (no address, or demo data that must not leave the machine).

Revision ID: 0007
Revises: 0006
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

UP = r"""
-- Contact details and channels ----------------------------------------------------------------
ALTER TABLE users
    ADD COLUMN email text CHECK (email IS NULL OR email ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
    ADD COLUMN phone text CHECK (phone IS NULL OR phone ~ '^\+[1-9][0-9]{7,14}$'),
    ADD COLUMN channels text[] NOT NULL DEFAULT '{in_app,email}'
        CHECK (channels <@ ARRAY['in_app', 'email', 'sms', 'whatsapp']::text[] AND 'in_app' = ANY(channels));

-- Areas each official covers ---------------------------------------------------------------------
CREATE TABLE official_areas (
    id        bigserial PRIMARY KEY,
    user_id   bigint      NOT NULL REFERENCES users(id),
    district  text        NOT NULL CHECK (length(btrim(district)) > 0),
    mandal    text        CHECK (mandal IS NULL OR length(btrim(mandal)) > 0),
    added_by  bigint      REFERENCES users(id),
    added_at  timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX official_areas_once ON official_areas (user_id, lower(district), lower(coalesce(mandal, '')));
CREATE INDEX assets_area ON assets (lower(district), lower(mandal));

-- Notifications ----------------------------------------------------------------------------------
CREATE TYPE notification_kind AS ENUM ('incident_opened', 'incident_decided', 'reminder', 'not_acknowledged', 'weekly_digest');

CREATE TABLE notifications (
    id               bigserial PRIMARY KEY,
    user_id          bigint            NOT NULL REFERENCES users(id),
    kind             notification_kind NOT NULL,
    alert_id         bigint            REFERENCES alerts(id),
    week             text              CHECK (week ~ '^[0-9]{4}-W[0-9]{2}$'),
    about_id         bigint            REFERENCES notifications(id),
    subject          text              NOT NULL CHECK (length(btrim(subject)) > 0),
    body             text              NOT NULL,
    payload          jsonb             NOT NULL DEFAULT '{}'::jsonb,
    needs_ack        boolean           NOT NULL,
    created_at       timestamptz       NOT NULL,
    acknowledged_at  timestamptz,
    ack_via          text              CHECK (ack_via IN ('inbox', 'review', 'decision')),
    is_demo          boolean           NOT NULL DEFAULT false,
    CHECK ((kind = 'weekly_digest') = (alert_id IS NULL)),
    CHECK ((kind = 'weekly_digest') = (week IS NOT NULL)),
    CHECK ((kind IN ('reminder', 'not_acknowledged')) = (about_id IS NOT NULL)),
    CHECK (acknowledged_at IS NULL OR needs_ack),
    CHECK ((acknowledged_at IS NULL) = (ack_via IS NULL)),
    CHECK (acknowledged_at IS NULL OR acknowledged_at >= created_at)
);
CREATE UNIQUE INDEX notifications_once_per_incident ON notifications (user_id, kind, alert_id)
    WHERE kind IN ('incident_opened', 'incident_decided');
CREATE UNIQUE INDEX notifications_once_per_follow_up ON notifications (user_id, kind, about_id)
    WHERE about_id IS NOT NULL;
CREATE UNIQUE INDEX notifications_once_per_week ON notifications (user_id, week, is_demo)
    WHERE kind = 'weekly_digest';
CREATE INDEX notifications_user ON notifications (user_id, created_at DESC);
CREATE INDEX notifications_alert ON notifications (alert_id) WHERE alert_id IS NOT NULL;

-- Kept for good: the only change allowed is the acknowledgement, once.
CREATE FUNCTION lp_notification_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER notifications_guard BEFORE UPDATE OR DELETE ON notifications
    FOR EACH ROW EXECUTE FUNCTION lp_notification_guard();
CREATE TRIGGER notifications_no_truncate BEFORE TRUNCATE ON notifications
    FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();

-- Delivery attempts ------------------------------------------------------------------------------
CREATE TABLE notification_deliveries (
    id               bigserial PRIMARY KEY,
    notification_id  bigint      NOT NULL REFERENCES notifications(id),
    channel          text        NOT NULL CHECK (channel IN ('email', 'sms', 'whatsapp')),
    status           text        NOT NULL CHECK (status IN ('queued', 'sent', 'held', 'failed', 'skipped')),
    attempt          integer     NOT NULL DEFAULT 0 CHECK (attempt >= 0),
    to_masked        text,
    detail           text,
    at               timestamptz NOT NULL
);
CREATE INDEX notification_deliveries_latest ON notification_deliveries (notification_id, channel, id DESC);
CREATE INDEX notification_deliveries_queued ON notification_deliveries (status, at) WHERE status IN ('queued', 'failed');
CREATE TRIGGER notification_deliveries_append_only BEFORE UPDATE OR DELETE ON notification_deliveries
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER notification_deliveries_no_truncate BEFORE TRUNCATE ON notification_deliveries
    FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();
"""

DOWN = r"""
DROP TABLE notification_deliveries;
DROP TABLE notifications;
DROP FUNCTION lp_notification_guard();
DROP TYPE notification_kind;
DROP INDEX assets_area;
DROP TABLE official_areas;
ALTER TABLE users DROP COLUMN email, DROP COLUMN phone, DROP COLUMN channels;
"""


def run_raw(sql: str) -> None:
    with op.get_bind().connection.dbapi_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    run_raw(UP)


def downgrade() -> None:
    run_raw(DOWN)
