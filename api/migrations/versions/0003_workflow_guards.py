"""Workflow guards in the database.

- Alert state changes only through the state machine, which sets lp.state_machine for the
  duration of one update (section 6.5: "No code path may change state except through it").
- A new alert starts as CANDIDATE, and never for a water-loss-only candidate (invariant 8).
- Alerts are never deleted. Legal checks, field checks and officer records are append-only.

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

SQL = r"""
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
CREATE TRIGGER alerts_no_delete BEFORE DELETE ON alerts
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();

CREATE TRIGGER legal_checks_append_only BEFORE UPDATE OR DELETE ON legal_checks
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER field_checks_append_only BEFORE UPDATE OR DELETE ON field_checks
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER officer_records_append_only BEFORE UPDATE OR DELETE ON officer_records
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
"""


def run_raw(sql: str) -> None:
    with op.get_bind().connection.dbapi_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    run_raw(SQL)


def downgrade() -> None:
    run_raw(
        """
        DROP TRIGGER IF EXISTS officer_records_append_only ON officer_records;
        DROP TRIGGER IF EXISTS field_checks_append_only ON field_checks;
        DROP TRIGGER IF EXISTS legal_checks_append_only ON legal_checks;
        DROP TRIGGER IF EXISTS alerts_no_delete ON alerts;
        DROP TRIGGER IF EXISTS alerts_state_guard ON alerts;
        DROP FUNCTION IF EXISTS lp_alert_state_guard;
        """
    )
