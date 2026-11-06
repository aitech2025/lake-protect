"""Invariant tests from CONTEXT.md section 12. Each test name carries its invariant number.

Invariants 10 (backtest look-ahead), 11 (wording) and 13 (evidence pack) are tested where their
code lives: pipeline/tests, test_wording.py and test_evidence_pack.py.
"""
import datetime as dt
import io

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.enums import AlertState, Role
from app.models import Alert, Candidate, CourtCase, OwnerClaim, Permit
from app.services import boundaries as bsvc
from app.services import ingest as ingest_svc
from app.workflow import state_machine as sm
from tests.factories import (
    Team,
    add_pack_row,
    auth,
    candidate_in,
    field_check,
    ingest,
    make_asset,
    rect,
    record_checklist,
    square,
)

T0 = dt.datetime(2025, 6, 20, 6, tzinfo=dt.timezone.utc)


def at(days: float) -> dt.datetime:
    return T0 + dt.timedelta(days=days)


def to_confirmed(db, team, asset):
    _, alert = ingest(db, asset, at=T0)
    assert alert.state == "TRIAGE"
    sm.transition(db, alert, "CONFIRMED", actor=team.analyst, data={"image_pair_reviewed": True}, at=at(1))
    return alert


def to_assigned(db, team, asset):
    alert = to_confirmed(db, team, asset)
    sm.transition(db, alert, "ASSIGNED", actor=team.nodal, data={"owner_user_id": team.field.id}, at=at(2))
    return alert


def refused(fn, *args, **kwargs) -> sm.Refused:
    with pytest.raises(sm.Refused) as exc:
        fn(*args, **kwargs)
    return exc.value


def every_rule_into(dst: str):
    return [r for r in sm.TABLE if r.dst == dst]


# 1 ------------------------------------------------------------------------------------------

def test_invariant_1_every_route_into_assignment_checks_the_court_register():
    assert every_rule_into("ASSIGNED")
    for rule in every_rule_into("ASSIGNED"):
        if rule.src == {"ASSIGNED"}:
            continue  # cannot_access keeps an existing assignment; it is not a new one
        assert sm.no_live_court in rule.pre


def test_invariant_1_court_hit_at_ingest_is_held_and_cannot_be_assigned(db):
    team = Team(db)
    asset = make_asset(db, cohort="A_RECOVERED")
    db.add(CourtCase(court="Test court", case_no="T-1", status="pending", asset_id=asset.id, is_demo=True))
    db.flush()
    _, alert = ingest(db, asset, at=T0)
    assert alert.state == "HOLD_LEGAL"
    refused(sm.transition, db, alert, "ASSIGNED", actor=team.nodal, data={"owner_user_id": team.field.id})
    exc = refused(sm.transition, db, alert, "TRIAGE", actor=team.legal, reason="Try release", data={"case_status_ref": "x"})
    assert "live matter" in exc.message
    assert alert.state == "HOLD_LEGAL"


def test_invariant_1_court_case_added_later_blocks_assignment_even_without_the_import_hook(db):
    team = Team(db)
    asset = make_asset(db, cohort="A_RECOVERED")
    alert = to_confirmed(db, team, asset)
    db.add(CourtCase(court="Test court", case_no="T-2", status="stay", asset_id=asset.id, is_demo=True))
    db.flush()
    exc = refused(sm.transition, db, alert, "ASSIGNED", actor=team.nodal, data={"owner_user_id": team.field.id}, at=at(2))
    assert "court" in exc.message and alert.state == "CONFIRMED"


def test_invariant_1_court_import_puts_open_alerts_on_hold(db, client):
    team = Team(db)
    asset = make_asset(db, cohort="A_RECOVERED")
    alert = to_assigned(db, team, asset)
    csv = f"court,case_no,status,asset_key\nTest court,T-3,pending,{asset.asset_key}\n"
    resp = client.post("/records/court-cases/import", headers=auth(team.legal), files={"file": ("cases.csv", io.BytesIO(csv.encode()), "text/csv")})
    assert resp.status_code == 201, resp.text
    assert alert.id in resp.json()["alerts_put_on_hold"]
    db.refresh(alert)
    assert alert.state == "HOLD_LEGAL"


def test_invariant_1_release_after_the_matter_closes_restarts_review(db):
    team = Team(db)
    asset = make_asset(db, cohort="A_RECOVERED")
    case = CourtCase(court="Test court", case_no="T-4", status="pending", asset_id=asset.id, is_demo=True)
    db.add(case)
    db.flush()
    _, alert = ingest(db, asset, at=T0)
    case.status = "disposed"
    db.flush()
    sm.transition(db, alert, "TRIAGE", actor=team.legal, reason="Matter disposed", data={"case_status_ref": "Order T-4 disposed"}, at=at(1))
    assert alert.state == "TRIAGE"


# 2 ------------------------------------------------------------------------------------------

def test_invariant_2_every_route_into_assignment_refuses_watch_mode():
    for rule in every_rule_into("ASSIGNED"):
        if rule.src == {"ASSIGNED"}:
            continue
        assert any(g.__name__ == "mode_not_WATCH" for g in rule.pre)


@pytest.mark.parametrize("cohort", ["D_UNNOTIFIED", "F_REVENUE"])
def test_invariant_2_watch_cohorts_stop_at_the_watch_list(db, cohort):
    team = Team(db)
    asset = make_asset(db, cohort=cohort)
    _, alert = ingest(db, asset, at=T0)
    assert alert.state == "WATCH_LIST"
    for role_user in (team.nodal, team.analyst, team.admin):
        for target in ("ASSIGNED", "CONFIRMED", "TRIAGE"):
            refused(sm.transition, db, alert, target, actor=role_user, data={"owner_user_id": team.field.id, "image_pair_reviewed": True})
    assert alert.state == "WATCH_LIST"


def test_invariant_2_asset_downgraded_to_watch_cannot_be_assigned(db):
    team = Team(db)
    asset = make_asset(db, cohort="C_PRELIM")
    alert = to_confirmed(db, team, asset)
    bsvc.add_version(db, asset, kind="ftl", status="derived", geometry=square(side_m=305), source_name="Test downgrade", valid_from=dt.date(2025, 6, 1))
    assert asset.cohort == "D_UNNOTIFIED"
    exc = refused(sm.transition, db, alert, "ASSIGNED", actor=team.nodal, data={"owner_user_id": team.field.id}, at=at(2))
    assert "watch" in exc.message.lower()


def test_invariant_2_court_release_of_a_watch_asset_returns_to_the_watch_list(db):
    team = Team(db)
    asset = make_asset(db, cohort="D_UNNOTIFIED")
    case = CourtCase(court="Test court", case_no="T-5", status="pending", asset_id=asset.id, is_demo=True)
    db.add(case)
    db.flush()
    _, alert = ingest(db, asset, at=T0)
    assert alert.state == "HOLD_LEGAL"
    case.status = "disposed"
    db.flush()
    refused(sm.transition, db, alert, "TRIAGE", actor=team.legal, reason="r", data={"case_status_ref": "x"})
    sm.transition(db, alert, "WATCH_LIST", actor=team.legal, reason="Matter disposed", data={"case_status_ref": "x"}, at=at(1))
    assert alert.state == "WATCH_LIST"


def test_invariant_2_watch_list_moves_on_only_after_a_confirmed_boundary(db):
    team = Team(db)
    asset = make_asset(db, cohort="D_UNNOTIFIED")
    _, alert = ingest(db, asset, at=T0)
    bsvc.add_version(db, asset, kind="ftl", status="final_notification", geometry=square(side_m=305), source_name="Test final", valid_from=dt.date(2025, 6, 1))
    sm.transition(db, alert, "TRIAGE", actor=team.nodal, at=at(1))
    assert alert.state == "TRIAGE" and asset.cohort == "B_FINAL"


# 3 ------------------------------------------------------------------------------------------

def test_invariant_3_cohort_c_waits_for_a_final_boundary_before_the_officer(db):
    team = Team(db)
    asset = make_asset(db, cohort="C_PRELIM")
    alert = to_assigned(db, team, asset)
    field_check(db, alert, team.field, at=at(3))
    assert alert.state == "AWAITING_BOUNDARY"  # automatic, cohort C

    add_pack_row(db, alert, team.nodal)
    record_checklist(db, alert, team.nodal)
    for target in ("PACK_READY", "WITH_OFFICER"):
        refused(sm.transition, db, alert, target, actor=team.nodal, data={"gap_reason": "x"})
    exc = refused(sm.transition, db, alert, "FIELD_CONFIRMED", actor=team.nodal, at=at(4))
    assert "not confirmed" in exc.message

    bsvc.add_version(db, asset, kind="ftl", status="final_notification", geometry=square(side_m=300), source_name="Test final", valid_from=dt.date(2025, 6, 1))
    sm.transition(db, alert, "FIELD_CONFIRMED", actor=team.nodal, at=at(5))
    assert alert.state == "FIELD_CONFIRMED" and asset.cohort == "B_FINAL"  # no loop back
    sm.transition(db, alert, "PACK_READY", actor=team.nodal, at=at(5))
    sm.transition(db, alert, "WITH_OFFICER", actor=team.nodal, at=at(6))
    assert alert.state == "WITH_OFFICER"


def test_invariant_3_boundary_that_stops_being_final_blocks_the_officer_step(db):
    team = Team(db)
    asset = make_asset(db, cohort="B_FINAL")
    alert = to_assigned(db, team, asset)
    field_check(db, alert, team.field, at=at(3))
    add_pack_row(db, alert, team.nodal)
    record_checklist(db, alert, team.nodal)
    sm.transition(db, alert, "PACK_READY", actor=team.nodal, at=at(4))
    bsvc.add_version(db, asset, kind="ftl", status="preliminary_notification", geometry=square(side_m=301), source_name="Test revised", valid_from=dt.date(2025, 6, 1))
    exc = refused(sm.transition, db, alert, "WITH_OFFICER", actor=team.nodal, at=at(5))
    assert "not confirmed" in exc.message and alert.state == "PACK_READY"


# 4 ------------------------------------------------------------------------------------------

def test_invariant_4_owner_claim_before_field_confirmation_is_rejected_by_api_and_database(db, client):
    team = Team(db)
    asset = make_asset(db, cohort="A_RECOVERED")
    alert = to_assigned(db, team, asset)
    body = {"claim_type": "private_title", "claimant_name": "Test Claimant", "document_ref": "TEST-DOC"}

    resp = client.post(f"/alerts/{alert.id}/owner-claims", json=body, headers=auth(team.nodal))
    assert resp.status_code == 409

    with pytest.raises(DBAPIError, match="only after FIELD_CONFIRMED"):
        with db.begin_nested():
            db.add(OwnerClaim(alert_id=alert.id, claim_type="private_title", claimant_name="Test Claimant", entered_by=team.nodal.id, entered_at=at(2)))
            db.flush()
    assert db.scalar(select(func.count()).select_from(OwnerClaim)) == 0

    field_check(db, alert, team.field, at=at(3))
    assert alert.state == "FIELD_CONFIRMED"
    resp = client.post(f"/alerts/{alert.id}/owner-claims", json=body, headers=auth(team.nodal))
    assert resp.status_code == 201
    # Cohort A is government land, so a title claim does not change the class.
    assert resp.json()["alert_class"] == "GOVT_LAND"


def test_private_title_claim_inside_ftl_reclassifies_after_field_confirmation(db, client):
    team = Team(db)
    asset = make_asset(db, cohort="B_FINAL")
    alert = to_assigned(db, team, asset)
    field_check(db, alert, team.field, at=at(3))
    body = {"claim_type": "private_title", "claimant_name": "Test Claimant"}
    assert client.post(f"/alerts/{alert.id}/owner-claims", json=body, headers=auth(team.legal)).json()["alert_class"] == "RESTRICTED_PRIVATE"
    detail = client.get(f"/alerts/{alert.id}", headers=auth(team.analyst)).json()
    assert detail["legal_check"]["alert_class"] == "RESTRICTED_PRIVATE"
    assert detail["owner_claims"][0]["claimant_name"] is None  # personal data hidden from the analyst


def test_invariant_4_candidates_and_alerts_carry_no_owner_fields(db):
    for model in (Candidate, Alert):
        cols = {c.name for c in model.__table__.columns}
        assert not {c for c in cols if "owner_name" in c or "claimant" in c or "encroach" in c}
    payload = candidate_in(make_asset(db)).model_dump()
    payload["owner_name"] = "Someone"
    with pytest.raises(ValueError):
        ingest_svc.CandidateIn.model_validate(payload)


# 5 ------------------------------------------------------------------------------------------

def _closure_setup(db, team, closure):
    asset = make_asset(db, cohort="A_RECOVERED")
    if closure == "CLOSED_NOT_REAL":
        _, alert = ingest(db, asset, at=T0)
        return alert, team.analyst, team.reviewer, {"reason_code": "cloud_shadow"}
    if closure == "CLOSED_FALSE_ALARM":
        return to_assigned(db, team, asset), team.field, team.nodal, {}
    alert = to_assigned(db, team, asset)
    field_check(db, alert, team.field, at=at(3))
    add_pack_row(db, alert, team.nodal)
    record_checklist(db, alert, team.nodal)
    sm.transition(db, alert, "PACK_READY", actor=team.nodal, at=at(4))
    sm.transition(db, alert, "WITH_OFFICER", actor=team.nodal, at=at(5))
    return alert, team.legal, team.nodal, {}


@pytest.mark.parametrize("closure", ["CLOSED_NOT_REAL", "CLOSED_FALSE_ALARM", "CLOSED_NO_ACTION"])
def test_invariant_5_closure_by_one_person_is_rejected(db, client, closure):
    team = Team(db)
    alert, first, second, data = _closure_setup(db, team, closure)
    state_before = alert.state
    body = {"to": closure, "reason": "Test reason", "data": data}

    r1 = client.post(f"/alerts/{alert.id}/transitions", json=body, headers=auth(first))
    assert r1.status_code == 200 and r1.json()["status"] == "awaiting_second_signature"
    r2 = client.post(f"/alerts/{alert.id}/transitions", json=body, headers=auth(first))
    assert r2.status_code == 409 and "two different people" in r2.json()["detail"]
    db.refresh(alert)
    assert alert.state == state_before

    r3 = client.post(f"/alerts/{alert.id}/transitions", json={"to": closure}, headers=auth(second))
    assert r3.status_code == 200 and r3.json()["state"] == closure


def test_invariant_5_second_signature_needs_the_right_role(db):
    team = Team(db)
    alert, first, _, data = _closure_setup(db, team, "CLOSED_NOT_REAL")
    sm.transition(db, alert, "CLOSED_NOT_REAL", actor=first, reason="r", data=data, at=at(1))
    other_analyst = Team(db).analyst
    exc = refused(sm.transition, db, alert, "CLOSED_NOT_REAL", actor=other_analyst, at=at(1))
    assert exc.status == 403 and alert.state == "TRIAGE"


def test_invariant_5_database_refuses_a_self_cosigned_closure(db):
    team = Team(db)
    alert, first, _, data = _closure_setup(db, team, "CLOSED_NOT_REAL")
    out = sm.transition(db, alert, "CLOSED_NOT_REAL", actor=first, reason="r", data=data, at=at(1))
    with pytest.raises(DBAPIError):
        with db.begin_nested():
            db.execute(text("UPDATE closure_requests SET resolved_by = requested_by, resolution = 'cosigned' WHERE id = :i"), {"i": out["closure_request_id"]})


# 6 ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("first_changed", [dt.date(2025, 1, 1), dt.date(2024, 11, 3)])
def test_invariant_6_change_on_or_before_baseline_never_gets_past_closed_legacy(db, first_changed):
    team = Team(db)
    asset = make_asset(db, cohort="A_RECOVERED", baseline=dt.date(2025, 1, 1))
    _, alert = ingest(db, asset, at=T0, first_changed=first_changed, last_clear=first_changed - dt.timedelta(days=10))
    assert alert.state == "CLOSED_LEGACY"
    actors = [None, *vars(team).values()]
    for target in AlertState:
        for actor in actors:
            with pytest.raises(sm.Refused):
                sm.transition(db, alert, target.value, actor=actor, reason="r", data={"recheck_candidate_id": alert.candidate_id})
    # A later re-check of the same footprint does not reopen it.
    ingest(db, asset, at=at(30), first_changed=dt.date(2025, 7, 1), last_clear=dt.date(2025, 6, 25))
    db.refresh(alert)
    assert alert.state == "CLOSED_LEGACY" and alert.reopened_count == 0


# 7 ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("zone,geometry", [("inside_ftl", square(side_m=60)), ("buffer", rect(230, 250, -50, 50))])
def test_invariant_7_permit_inside_ftl_or_buffer_never_auto_closes(db, zone, geometry):
    asset = make_asset(db, cohort="B_FINAL", geometry=square(side_m=450))
    db.add(Permit(source="Test", ref="TEST-PERMIT", kind="building", geom=WKTElement("MULTIPOLYGON(((81.4 14.4, 81.6 14.4, 81.6 14.6, 81.4 14.6, 81.4 14.4)))", srid=4326), valid_from=dt.date(2025, 1, 1), is_demo=True))
    db.flush()
    out, alert = ingest(db, asset, geometry=geometry)
    assert out["legal_check"]["zone"] == zone
    assert alert.state == "TRIAGE"
    assert "permit_conflict" in out["legal_check"]["flags"]
    assert not [r for r in sm.TABLE if r.actors == {sm.SYSTEM} and "TRIAGE" in r.src and r.dst.startswith("CLOSED")]


def test_invariant_7_control_permit_in_watch_ring_does_close(db):
    asset = make_asset(db, cohort="B_FINAL", geometry=square(side_m=450))
    db.add(Permit(source="Test", ref="TEST-PERMIT", kind="building", geom=WKTElement("MULTIPOLYGON(((81.4 14.4, 81.6 14.4, 81.6 14.6, 81.4 14.6, 81.4 14.4)))", srid=4326), valid_from=dt.date(2025, 1, 1), is_demo=True))
    db.flush()
    out, alert = ingest(db, asset, geometry=rect(270, 310, -20, 20))
    assert out["legal_check"]["zone"] == "watch_ring" and alert.state == "CLOSED_AUTHORISED"


# 8 ------------------------------------------------------------------------------------------

def test_invariant_8_water_loss_alone_never_creates_an_alert(db, client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "pipeline_token", "test-token")
    asset = make_asset(db)
    before = db.scalar(select(func.count()).select_from(Alert))
    payload = candidate_in(asset, change_type="water_loss").model_dump(mode="json")
    resp = client.post("/candidates", json=payload, headers={"X-Pipeline-Token": "test-token"})
    assert resp.status_code == 422 and "Water loss" in resp.json()["detail"]
    with pytest.raises(ingest_svc.IngestRefused):
        ingest_svc.ingest(db, candidate_in(asset, change_type="water_loss"))
    assert db.scalar(select(func.count()).select_from(Alert)) == before


def test_invariant_8_database_refuses_an_alert_for_water_loss(db):
    asset = make_asset(db)
    primary = bsvc.primary_of(bsvc.current_boundary_set(db, asset.id))
    cand = Candidate(asset_id=asset.id, boundary_id=primary["id"], geom=WKTElement("MULTIPOLYGON(((81.5 14.5, 81.501 14.5, 81.501 14.501, 81.5 14.5)))", srid=4326),
                     area_sq_m=5000, change_type="water_loss", first_changed_at=dt.date(2025, 6, 1), sensor_basis="optical_only", confidence=0.5, rule_version="t", created_at=T0)
    db.add(cand)
    db.flush()
    with pytest.raises(DBAPIError, match="water loss"):
        with db.begin_nested():
            db.add(Alert(code="X-1", candidate_id=cand.id, state="CANDIDATE", created_at=T0, updated_at=T0))
            db.flush()


# 9 ------------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "tamper",
    [
        "UPDATE audit_log SET details = '{\"tampered\": true}' WHERE id = :i",
        "UPDATE audit_log SET at = at + interval '1 second' WHERE id = :i",
        "UPDATE audit_log SET actor_id = NULL WHERE id = :i",
        "DELETE FROM audit_log WHERE id = :i",
    ],
)
def test_invariant_9_editing_any_audit_row_makes_verify_fail(db, client, tamper):
    team = Team(db)
    asset = make_asset(db)
    _, alert = ingest(db, asset, at=T0)
    sm.transition(db, alert, "CONFIRMED", actor=team.analyst, data={"image_pair_reviewed": True}, at=at(1))
    ok = client.get("/audit/verify", headers=auth(team.auditor)).json()
    assert ok["ok"] is True and ok["rows_checked"] > 3

    target = db.scalar(text("SELECT id FROM audit_log WHERE action = 'alert.transition' AND actor_id IS NOT NULL ORDER BY id LIMIT 1"))
    db.execute(text("SET LOCAL session_replication_role = replica"))  # a superuser switching triggers off
    db.execute(text(tamper), {"i": target})
    db.execute(text("SET LOCAL session_replication_role = origin"))
    db.expire_all()
    bad = client.get("/audit/verify", headers=auth(team.auditor)).json()
    assert bad["ok"] is False


# Section 6.5: no code path may change state except through the state machine -----------------

def test_state_changes_outside_the_state_machine_are_refused_by_the_database(db):
    asset = make_asset(db)
    _, alert = ingest(db, asset, at=T0)
    with pytest.raises(DBAPIError, match="only through the state machine"):
        with db.begin_nested():
            db.execute(text("UPDATE alerts SET state = 'WITH_OFFICER' WHERE id = :i"), {"i": alert.id})


def test_no_other_module_assigns_alert_state():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app"
    offenders = []
    for path in root.rglob("*.py"):
        if path.name == "state_machine.py":
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if ".state =" in stripped and "alert" in stripped.lower():
                offenders.append(f"{path.name}:{n}: {stripped}")
    assert offenders == []
