"""Two roles, a simple incident lifecycle, weekly records per asset, and legal documents.

The owner's instruction of 24 Nov 2026 (DECISIONS.md D-057):

- Only two roles remain: `admin`, who runs the application, and `viewer`, the officials. Every
  other account becomes a viewer.
- An alert is now an incident: OPEN, then UNDER_REVIEW (a viewer records a review), then
  CONFIRMED or DISMISSED (the admin decides), then CLOSED. Changes the legal check rules out
  (outside the zones, before the baseline, authorised works) close at once with resolution
  `auto`. Existing alerts are mapped onto the new states; the old states stay in the legal-check
  table, where they are the check's verdict.
- Viewers' reviews are append-only rows.
- Every weekly screen records, per asset, the week, the image of that week and what changed.
- Levelling is a change type of its own.
- Every asset can carry legal documents, append-only, each with its file hash or its reference.

Revision ID: 0006
Revises: 0005
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

UP = r"""
-- Roles ---------------------------------------------------------------------------------------
ALTER TYPE role RENAME TO role_v1;
CREATE TYPE role AS ENUM ('admin', 'viewer');
ALTER TABLE users ALTER COLUMN role TYPE role
    USING (CASE WHEN role::text = 'admin' THEN 'admin' ELSE 'viewer' END)::role;
DROP TYPE role_v1;

-- Change types --------------------------------------------------------------------------------
ALTER TYPE change_type ADD VALUE IF NOT EXISTS 'levelling' AFTER 'clearing';

-- Incidents -----------------------------------------------------------------------------------
DROP TRIGGER alerts_state_guard ON alerts;
DROP FUNCTION lp_alert_state_guard();
DROP TRIGGER owner_claims_gate ON owner_claims;
DROP FUNCTION lp_owner_claim_gate();

ALTER TABLE alerts
    ADD COLUMN resolution text CHECK (resolution IN ('confirmed', 'dismissed', 'auto')),
    ADD COLUMN closed_at timestamptz,
    ADD COLUMN related_alert_id bigint REFERENCES alerts(id);

UPDATE alerts SET
    resolution = CASE
        WHEN state::text IN ('CONFIRMED', 'ASSIGNED', 'FIELD_CONFIRMED', 'AWAITING_BOUNDARY', 'PACK_READY',
                             'WITH_OFFICER', 'ACTION_RECORDED', 'POST_ACTION_WATCH', 'CLOSED_NO_ACTION') THEN 'confirmed'
        WHEN state::text IN ('CLOSED_NOT_REAL', 'CLOSED_FALSE_ALARM') THEN 'dismissed'
        WHEN state::text IN ('CLOSED_OUT_OF_SCOPE', 'CLOSED_LEGACY', 'CLOSED_AUTHORISED') THEN 'auto'
        END,
    closed_at = CASE
        WHEN state::text IN ('ACTION_RECORDED', 'POST_ACTION_WATCH', 'CLOSED_NO_ACTION', 'CLOSED_NOT_REAL',
                             'CLOSED_FALSE_ALARM', 'CLOSED_OUT_OF_SCOPE', 'CLOSED_LEGACY', 'CLOSED_AUTHORISED') THEN updated_at
        END;

CREATE TYPE incident_state AS ENUM ('OPEN', 'UNDER_REVIEW', 'CONFIRMED', 'DISMISSED', 'CLOSED');
ALTER TABLE alerts ALTER COLUMN state TYPE incident_state USING (CASE
    WHEN state::text IN ('CANDIDATE', 'TRIAGE', 'WATCH_LIST', 'HOLD_LEGAL') THEN 'OPEN'
    WHEN state::text IN ('CONFIRMED', 'ASSIGNED', 'FIELD_CONFIRMED', 'AWAITING_BOUNDARY', 'PACK_READY', 'WITH_OFFICER') THEN 'CONFIRMED'
    ELSE 'CLOSED' END)::incident_state;

-- IS NOT DISTINCT FROM, not '=': a CHECK that comes out NULL would let the row through.
ALTER TABLE alerts ADD CONSTRAINT alerts_state_resolution CHECK (
       (state IN ('OPEN', 'UNDER_REVIEW') AND resolution IS NULL AND closed_at IS NULL)
    OR (state = 'CONFIRMED' AND resolution IS NOT DISTINCT FROM 'confirmed' AND closed_at IS NULL)
    OR (state = 'DISMISSED' AND resolution IS NOT DISTINCT FROM 'dismissed' AND closed_at IS NULL)
    OR (state = 'CLOSED' AND resolution IS NOT NULL AND closed_at IS NOT NULL));

CREATE FUNCTION lp_alert_state_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.state <> 'OPEN' THEN
            RAISE EXCEPTION 'a new incident must start as OPEN, not %', NEW.state
                USING ERRCODE = 'check_violation';
        END IF;
        IF (SELECT change_type FROM candidates WHERE id = NEW.candidate_id) = 'water_loss' THEN
            RAISE EXCEPTION 'water loss alone never creates an incident'
                USING ERRCODE = 'check_violation';
        END IF;
    ELSIF NEW.state IS DISTINCT FROM OLD.state
          AND coalesce(current_setting('lp.state_machine', true), 'off') <> 'on' THEN
        RAISE EXCEPTION 'incident state changes only through the incident lifecycle (% to %)', OLD.state, NEW.state
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER alerts_state_guard BEFORE INSERT OR UPDATE ON alerts
    FOR EACH ROW EXECUTE FUNCTION lp_alert_state_guard();

-- Owner names only once the change is confirmed (invariant 4, database half).
CREATE FUNCTION lp_owner_claim_gate() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    s incident_state;
    r text;
BEGIN
    SELECT state, resolution INTO s, r FROM alerts WHERE id = NEW.alert_id;
    IF s IS NULL OR r IS DISTINCT FROM 'confirmed' THEN
        RAISE EXCEPTION 'owner claims are allowed only after the change is confirmed (incident % is %)',
            NEW.alert_id, s USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER owner_claims_gate BEFORE INSERT OR UPDATE ON owner_claims
    FOR EACH ROW EXECUTE FUNCTION lp_owner_claim_gate();

CREATE TABLE incident_reviews (
    id           bigserial PRIMARY KEY,
    alert_id     bigint      NOT NULL REFERENCES alerts(id),
    reviewer_id  bigint      NOT NULL REFERENCES users(id),
    outcome      text        NOT NULL CHECK (outcome IN ('real_change', 'not_real', 'needs_site_visit')),
    note         text        NOT NULL CHECK (length(btrim(note)) > 0),
    reviewed_at  timestamptz NOT NULL
);
CREATE INDEX incident_reviews_alert ON incident_reviews (alert_id);
CREATE TRIGGER incident_reviews_append_only BEFORE UPDATE OR DELETE ON incident_reviews
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER incident_reviews_no_truncate BEFORE TRUNCATE ON incident_reviews
    FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();

-- Weekly record per asset ---------------------------------------------------------------------
ALTER TABLE screen_runs ADD COLUMN is_demo boolean NOT NULL DEFAULT false;
ALTER TABLE asset_screens
    ADD COLUMN week text CHECK (week ~ '^[0-9]{4}-W[0-9]{2}$'),
    ADD COLUMN image_key text,
    ADD COLUMN image_date date,
    ADD COLUMN image_scene_id text,
    ADD COLUMN changes jsonb NOT NULL DEFAULT '[]'::jsonb;

-- Legal documents -------------------------------------------------------------------------------
CREATE TABLE asset_documents (
    id                  bigserial PRIMARY KEY,
    asset_id            bigint      NOT NULL REFERENCES assets(id),
    doc_type            text        NOT NULL CHECK (doc_type IN ('notification', 'survey_map', 'land_record',
                                        'government_order', 'court_order', 'recovery_order', 'other')),
    title               text        NOT NULL CHECK (length(btrim(title)) > 0),
    reference           text,
    issued_on           date,
    issued_by           text,
    file_key            text,
    file_name           text,
    content_type        text,
    sha256              varchar(64),
    byte_size           bigint,
    source_url          text,
    source_snapshot_id  bigint REFERENCES source_snapshots(id),
    supersedes_id       bigint REFERENCES asset_documents(id),
    added_by            bigint REFERENCES users(id),
    added_at            timestamptz NOT NULL DEFAULT now(),
    is_demo             boolean     NOT NULL DEFAULT false,
    CHECK (file_key IS NOT NULL OR reference IS NOT NULL OR source_url IS NOT NULL),
    CHECK ((file_key IS NULL) = (sha256 IS NULL))
);
CREATE INDEX asset_documents_asset ON asset_documents (asset_id);
CREATE TRIGGER asset_documents_append_only BEFORE UPDATE OR DELETE ON asset_documents
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER asset_documents_no_truncate BEFORE TRUNCATE ON asset_documents
    FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();
"""

DOWN = r"""
DROP TABLE asset_documents;
ALTER TABLE asset_screens DROP COLUMN week, DROP COLUMN image_key, DROP COLUMN image_date,
    DROP COLUMN image_scene_id, DROP COLUMN changes;
ALTER TABLE screen_runs DROP COLUMN is_demo;
DROP TABLE incident_reviews;

DROP TRIGGER owner_claims_gate ON owner_claims;
DROP FUNCTION lp_owner_claim_gate();
DROP TRIGGER alerts_state_guard ON alerts;
DROP FUNCTION lp_alert_state_guard();
ALTER TABLE alerts DROP CONSTRAINT alerts_state_resolution;
ALTER TABLE alerts ALTER COLUMN state TYPE alert_state USING (CASE
    WHEN state::text IN ('OPEN', 'UNDER_REVIEW') THEN 'TRIAGE'
    WHEN state::text = 'CONFIRMED' THEN 'CONFIRMED'
    WHEN state::text = 'DISMISSED' THEN 'CLOSED_NOT_REAL'
    WHEN resolution = 'confirmed' THEN 'ACTION_RECORDED'
    WHEN resolution = 'dismissed' THEN 'CLOSED_NOT_REAL'
    ELSE 'CLOSED_OUT_OF_SCOPE' END)::alert_state;
ALTER TABLE alerts DROP COLUMN resolution, DROP COLUMN closed_at, DROP COLUMN related_alert_id;
DROP TYPE incident_state;

CREATE FUNCTION lp_alert_state_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.state <> 'CANDIDATE' THEN
            RAISE EXCEPTION 'a new alert must start as CANDIDATE, not %', NEW.state
                USING ERRCODE = 'check_violation';
        END IF;
        IF (SELECT change_type FROM candidates WHERE id = NEW.candidate_id) = 'water_loss' THEN
            RAISE EXCEPTION 'water loss alone never creates an alert'
                USING ERRCODE = 'check_violation';
        END IF;
    ELSIF NEW.state IS DISTINCT FROM OLD.state
          AND coalesce(current_setting('lp.state_machine', true), 'off') <> 'on' THEN
        RAISE EXCEPTION 'alert state changes only through the state machine (% to %)', OLD.state, NEW.state
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER alerts_state_guard BEFORE INSERT OR UPDATE ON alerts
    FOR EACH ROW EXECUTE FUNCTION lp_alert_state_guard();

CREATE FUNCTION lp_owner_claim_gate() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    s alert_state;
BEGIN
    SELECT state INTO s FROM alerts WHERE id = NEW.alert_id;
    IF s IS NULL OR s NOT IN ('FIELD_CONFIRMED','AWAITING_BOUNDARY','PACK_READY','WITH_OFFICER',
                              'ACTION_RECORDED','CLOSED_NO_ACTION','POST_ACTION_WATCH') THEN
        RAISE EXCEPTION 'owner claims are allowed only after FIELD_CONFIRMED (alert % is %)',
            NEW.alert_id, s USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER owner_claims_gate BEFORE INSERT OR UPDATE ON owner_claims
    FOR EACH ROW EXECUTE FUNCTION lp_owner_claim_gate();

-- 'levelling' stays in change_type: PostgreSQL cannot drop an enum value. Earlier code never uses it.
ALTER TYPE role RENAME TO role_v2;
CREATE TYPE role AS ENUM ('analyst','reviewer','field_officer','nodal_officer','legal_officer',
                          'senior_officer','auditor','admin');
ALTER TABLE users ALTER COLUMN role TYPE role
    USING (CASE WHEN role::text = 'admin' THEN 'admin' ELSE 'analyst' END)::role;
DROP TYPE role_v2;
"""


def run_raw(sql: str) -> None:
    with op.get_bind().connection.dbapi_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    run_raw(UP)


def downgrade() -> None:
    run_raw(DOWN)
