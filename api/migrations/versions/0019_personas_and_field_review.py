"""Four personas, district scope, field visits and two-step approval (DECISIONS.md D-067).

- Roles: `admin`, `senior_official`, `district_officer`, `field_officer`. A `viewer` with an area
  becomes a district officer, any other viewer a senior official. The two demo viewers are renamed
  demo.district1 and demo.district2; the new role accounts come from data/accounts.yml.
- Incident states gain FIELD_VISIT (a field officer is assigned), FIELD_REPORTED (their report is
  in) and RECOMMENDED (a district officer's recommendation waits for the senior official). None of
  them has a resolution. The state still changes only through the lifecycle.
- `incident_assignments`, `field_reports`, `incident_recommendations`: append-only. Their guards:
  only a field officer can be assigned, only the assigned field officer reports while the visit is
  open, and a senior official can only approve what was recommended.
- Notification kinds for the new steps: an assignment, a field report, a recommendation, a return.

Revision ID: 0019
Revises: 0018
"""
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

UP = r"""
-- Roles -----------------------------------------------------------------------------------------
-- The new role is worked out first: a column type change cannot look at another table.
ALTER TABLE users ADD COLUMN role_next text;
UPDATE users SET role_next = CASE
    WHEN role::text = 'admin' THEN 'admin'
    WHEN EXISTS (SELECT 1 FROM official_areas oa WHERE oa.user_id = users.id) THEN 'district_officer'
    ELSE 'senior_official' END;
ALTER TYPE role RENAME TO role_v2;
CREATE TYPE role AS ENUM ('admin', 'senior_official', 'district_officer', 'field_officer');
ALTER TABLE users ALTER COLUMN role TYPE role USING role_next::role;
ALTER TABLE users DROP COLUMN role_next;
DROP TYPE role_v2;
UPDATE users SET username = 'demo.district1', name = 'Demo District Officer 1'
    WHERE is_demo AND username = 'demo.viewer1' AND NOT EXISTS (SELECT 1 FROM users WHERE username = 'demo.district1');
UPDATE users SET username = 'demo.district2', name = 'Demo District Officer 2'
    WHERE is_demo AND username = 'demo.viewer2' AND NOT EXISTS (SELECT 1 FROM users WHERE username = 'demo.district2');

-- Incident states -------------------------------------------------------------------------------
ALTER TABLE alerts DROP CONSTRAINT alerts_state_resolution;
ALTER TYPE incident_state RENAME TO incident_state_v1;
CREATE TYPE incident_state AS ENUM ('OPEN', 'UNDER_REVIEW', 'FIELD_VISIT', 'FIELD_REPORTED', 'RECOMMENDED',
                                    'CONFIRMED', 'DISMISSED', 'CLOSED');
ALTER TABLE alerts ALTER COLUMN state TYPE incident_state USING state::text::incident_state;
DROP TYPE incident_state_v1;
ALTER TABLE alerts ADD CONSTRAINT alerts_state_resolution CHECK (
       (state IN ('OPEN', 'UNDER_REVIEW', 'FIELD_VISIT', 'FIELD_REPORTED', 'RECOMMENDED') AND resolution IS NULL AND closed_at IS NULL)
    OR (state = 'CONFIRMED' AND resolution IS NOT DISTINCT FROM 'confirmed' AND closed_at IS NULL)
    OR (state = 'DISMISSED' AND resolution IS NOT DISTINCT FROM 'dismissed' AND closed_at IS NULL)
    OR (state = 'CLOSED' AND resolution IS NOT NULL AND closed_at IS NOT NULL));

-- Assignments -----------------------------------------------------------------------------------
CREATE TABLE incident_assignments (
    id                bigserial PRIMARY KEY,
    alert_id          bigint      NOT NULL REFERENCES alerts(id),
    field_officer_id  bigint      NOT NULL REFERENCES users(id),
    assigned_by       bigint      NOT NULL REFERENCES users(id),
    note              text        NOT NULL CHECK (length(btrim(note)) > 0),
    at                timestamptz NOT NULL,
    is_demo           boolean     NOT NULL DEFAULT false
);
CREATE INDEX incident_assignments_alert ON incident_assignments (alert_id, id DESC);
CREATE INDEX incident_assignments_officer ON incident_assignments (field_officer_id, alert_id);

CREATE FUNCTION lp_assignment_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (SELECT role FROM users WHERE id = NEW.field_officer_id) IS DISTINCT FROM 'field_officer' THEN
        RAISE EXCEPTION 'only a field officer can be assigned a field visit (user %)', NEW.field_officer_id
            USING ERRCODE = 'check_violation';
    END IF;
    IF (SELECT state FROM alerts WHERE id = NEW.alert_id) NOT IN ('OPEN', 'UNDER_REVIEW', 'FIELD_VISIT', 'FIELD_REPORTED') THEN
        RAISE EXCEPTION 'incident % is not open for a field visit', NEW.alert_id USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER incident_assignments_guard BEFORE INSERT ON incident_assignments
    FOR EACH ROW EXECUTE FUNCTION lp_assignment_guard();
CREATE TRIGGER incident_assignments_append_only BEFORE UPDATE OR DELETE ON incident_assignments
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER incident_assignments_no_truncate BEFORE TRUNCATE ON incident_assignments
    FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();

-- Field reports ---------------------------------------------------------------------------------
CREATE TABLE field_reports (
    id                bigserial PRIMARY KEY,
    alert_id          bigint      NOT NULL REFERENCES alerts(id),
    assignment_id     bigint      NOT NULL REFERENCES incident_assignments(id),
    field_officer_id  bigint      NOT NULL REFERENCES users(id),
    inspection_id     bigint      NOT NULL REFERENCES asset_inspections(id),
    outcome           text        NOT NULL CHECK (outcome IN ('confirmed', 'false_alarm', 'cannot_access')),
    findings          text        NOT NULL CHECK (length(btrim(findings)) > 0),
    submitted_at      timestamptz NOT NULL,
    is_demo           boolean     NOT NULL DEFAULT false
);
CREATE INDEX field_reports_alert ON field_reports (alert_id, id);

CREATE FUNCTION lp_field_report_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    latest incident_assignments;
BEGIN
    SELECT * INTO latest FROM incident_assignments WHERE alert_id = NEW.alert_id ORDER BY id DESC LIMIT 1;
    IF latest.id IS DISTINCT FROM NEW.assignment_id OR latest.field_officer_id IS DISTINCT FROM NEW.field_officer_id THEN
        RAISE EXCEPTION 'only the field officer currently assigned can report on incident %', NEW.alert_id
            USING ERRCODE = 'check_violation';
    END IF;
    IF (SELECT state FROM alerts WHERE id = NEW.alert_id) IS DISTINCT FROM 'FIELD_VISIT' THEN
        RAISE EXCEPTION 'incident % has no field visit open', NEW.alert_id USING ERRCODE = 'check_violation';
    END IF;
    IF (SELECT alert_id FROM asset_inspections WHERE id = NEW.inspection_id) IS DISTINCT FROM NEW.alert_id THEN
        RAISE EXCEPTION 'the inspection is not of incident %', NEW.alert_id USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER field_reports_guard BEFORE INSERT ON field_reports
    FOR EACH ROW EXECUTE FUNCTION lp_field_report_guard();
CREATE TRIGGER field_reports_append_only BEFORE UPDATE OR DELETE ON field_reports
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER field_reports_no_truncate BEFORE TRUNCATE ON field_reports
    FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();

-- Recommendations -------------------------------------------------------------------------------
CREATE TABLE incident_recommendations (
    id                    bigserial PRIMARY KEY,
    alert_id              bigint      NOT NULL REFERENCES alerts(id),
    recommended_by        bigint      NOT NULL REFERENCES users(id),
    recommendation        text        NOT NULL CHECK (recommendation IN ('confirm', 'dismiss')),
    note                  text        NOT NULL CHECK (length(btrim(note)) > 0),
    field_report_id       bigint      REFERENCES field_reports(id),
    citizen_department    text,
    citizen_false_report  boolean     NOT NULL DEFAULT false,
    at                    timestamptz NOT NULL,
    is_demo               boolean     NOT NULL DEFAULT false,
    CHECK (recommendation = 'dismiss' OR (citizen_department IS NULL AND NOT citizen_false_report))
);
CREATE INDEX incident_recommendations_alert ON incident_recommendations (alert_id, id DESC);

CREATE FUNCTION lp_recommendation_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (SELECT role FROM users WHERE id = NEW.recommended_by) NOT IN ('district_officer', 'senior_official') THEN
        RAISE EXCEPTION 'a recommendation is made by a district officer' USING ERRCODE = 'check_violation';
    END IF;
    IF (SELECT state FROM alerts WHERE id = NEW.alert_id) NOT IN ('UNDER_REVIEW', 'FIELD_REPORTED') THEN
        RAISE EXCEPTION 'incident % is not under review', NEW.alert_id USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER incident_recommendations_guard BEFORE INSERT ON incident_recommendations
    FOR EACH ROW EXECUTE FUNCTION lp_recommendation_guard();
CREATE TRIGGER incident_recommendations_append_only BEFORE UPDATE OR DELETE ON incident_recommendations
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER incident_recommendations_no_truncate BEFORE TRUNCATE ON incident_recommendations
    FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();

-- A recommended incident is decided only as recommended.
CREATE FUNCTION lp_alert_recommendation_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    rec text;
BEGIN
    IF OLD.state = 'RECOMMENDED' AND NEW.state IN ('CONFIRMED', 'DISMISSED') THEN
        SELECT recommendation INTO rec FROM incident_recommendations WHERE alert_id = NEW.id ORDER BY id DESC LIMIT 1;
        IF (NEW.state = 'CONFIRMED') IS DISTINCT FROM (rec = 'confirm') THEN
            RAISE EXCEPTION 'incident % was recommended to %, not %', NEW.id, rec, NEW.state
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER alerts_recommendation_guard BEFORE UPDATE OF state ON alerts
    FOR EACH ROW EXECUTE FUNCTION lp_alert_recommendation_guard();

-- Notifications ---------------------------------------------------------------------------------
ALTER TYPE notification_kind ADD VALUE IF NOT EXISTS 'incident_assigned';
ALTER TYPE notification_kind ADD VALUE IF NOT EXISTS 'field_reported';
ALTER TYPE notification_kind ADD VALUE IF NOT EXISTS 'recommended';
ALTER TYPE notification_kind ADD VALUE IF NOT EXISTS 'returned';
"""

# Going down removes what only 0019 can hold. The guarded tables are lifted for that one delete;
# the added notification kinds stay in the type, unused, as 0009 and 0010 leave theirs.
DOWN = r"""
ALTER TABLE notification_deliveries DISABLE TRIGGER notification_deliveries_append_only;
DELETE FROM notification_deliveries WHERE notification_id IN (
    SELECT id FROM notifications WHERE kind::text IN ('incident_assigned', 'field_reported', 'recommended', 'returned'));
ALTER TABLE notification_deliveries ENABLE TRIGGER notification_deliveries_append_only;
ALTER TABLE notifications DISABLE TRIGGER notifications_guard;
DELETE FROM notifications WHERE kind::text IN ('incident_assigned', 'field_reported', 'recommended', 'returned');
ALTER TABLE notifications ENABLE TRIGGER notifications_guard;

DROP TRIGGER alerts_recommendation_guard ON alerts;
DROP FUNCTION lp_alert_recommendation_guard();
DROP TABLE incident_recommendations;
DROP FUNCTION lp_recommendation_guard();
DROP TABLE field_reports;
DROP FUNCTION lp_field_report_guard();
DROP TABLE incident_assignments;
DROP FUNCTION lp_assignment_guard();

ALTER TABLE alerts DROP CONSTRAINT alerts_state_resolution;
ALTER TYPE incident_state RENAME TO incident_state_v2;
CREATE TYPE incident_state AS ENUM ('OPEN', 'UNDER_REVIEW', 'CONFIRMED', 'DISMISSED', 'CLOSED');
ALTER TABLE alerts ALTER COLUMN state TYPE incident_state USING (CASE
    WHEN state::text IN ('FIELD_VISIT', 'FIELD_REPORTED', 'RECOMMENDED') THEN 'UNDER_REVIEW'
    ELSE state::text END)::incident_state;
DROP TYPE incident_state_v2;
ALTER TABLE alerts ADD CONSTRAINT alerts_state_resolution CHECK (
       (state IN ('OPEN', 'UNDER_REVIEW') AND resolution IS NULL AND closed_at IS NULL)
    OR (state = 'CONFIRMED' AND resolution IS NOT DISTINCT FROM 'confirmed' AND closed_at IS NULL)
    OR (state = 'DISMISSED' AND resolution IS NOT DISTINCT FROM 'dismissed' AND closed_at IS NULL)
    OR (state = 'CLOSED' AND resolution IS NOT NULL AND closed_at IS NOT NULL));

UPDATE users SET username = 'demo.viewer1', name = 'Demo Official 1' WHERE is_demo AND username = 'demo.district1';
UPDATE users SET username = 'demo.viewer2', name = 'Demo Official 2' WHERE is_demo AND username = 'demo.district2';
ALTER TYPE role RENAME TO role_v3;
CREATE TYPE role AS ENUM ('admin', 'viewer');
ALTER TABLE users ALTER COLUMN role TYPE role
    USING (CASE WHEN role::text = 'admin' THEN 'admin' ELSE 'viewer' END)::role;
DROP TYPE role_v3;
"""


def run_raw(sql: str) -> None:
    with op.get_bind().connection.dbapi_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    run_raw(UP)


def downgrade() -> None:
    run_raw(DOWN)
