"""Full alert lifecycle, timers, escalation and re-checks (sections 6.5 and 6.6)."""
import datetime as dt

import pytest
from sqlalchemy import select

from app.models import AuditLog, OfficerRecord
from app.workflow import escalation
from app.workflow import state_machine as sm
from app.workflow import timers
from tests.factories import Team, add_pack_row, auth, field_check, ingest, make_asset, record_checklist, square

T0 = dt.datetime(2025, 10, 6, 6, tzinfo=dt.timezone.utc)  # October: outside the monsoon


def at(days: float) -> dt.datetime:
    return T0 + dt.timedelta(days=days)


def test_full_path_to_officer_and_post_action_watch(db):
    team = Team(db, area=square(side_m=5000))
    asset = make_asset(db, cohort="A_RECOVERED")
    _, alert = ingest(db, asset, at=T0, first_changed=dt.date(2025, 9, 25), last_clear=dt.date(2025, 9, 15))
    assert alert.state == "TRIAGE" and alert.due_at == at(3)
    assert alert.code.startswith("DEMO-2025-")
    sm.transition(db, alert, "CONFIRMED", actor=team.analyst, data={"image_pair_reviewed": True}, at=at(1))
    assert alert.due_at is None
    sm.transition(db, alert, "ASSIGNED", actor=team.nodal, data={"owner_user_id": team.field.id}, at=at(1))
    assert alert.owner_user_id == team.field.id and alert.due_at == at(8)  # 7 days in a dry month

    result = field_check(db, alert, team.field, at=at(4))
    assert result["distance_warning"] is False and alert.state == "FIELD_CONFIRMED"
    add_pack_row(db, alert, team.nodal)
    record_checklist(db, alert, team.nodal)
    sm.transition(db, alert, "PACK_READY", actor=team.legal, at=at(5))
    sm.transition(db, alert, "WITH_OFFICER", actor=team.nodal, at=at(6))
    assert alert.due_at == at(36)
    rec = OfficerRecord(alert_id=alert.id, officer_id=team.legal.id, notice_ref="TEST/NOTICE/1", notice_date=dt.date(2025, 10, 14), created_at=at(9))
    db.add(rec)
    db.flush()
    out = sm.transition(db, alert, "ACTION_RECORDED", actor=team.legal, data={"officer_record_id": rec.id}, at=at(9))
    assert out["auto"] == ["POST_ACTION_WATCH"] and alert.state == "POST_ACTION_WATCH"

    path = [e.details["to"] for e in db.scalars(select(AuditLog).where(AuditLog.entity == "alert", AuditLog.entity_id == str(alert.id), AuditLog.action == "alert.transition").order_by(AuditLog.id))]
    assert path == ["TRIAGE", "CONFIRMED", "ASSIGNED", "FIELD_CONFIRMED", "PACK_READY", "WITH_OFFICER", "ACTION_RECORDED", "POST_ACTION_WATCH"]


def test_confirm_needs_the_image_pair(db):
    team = Team(db)
    _, alert = ingest(db, make_asset(db), at=T0, chips=False)
    with pytest.raises(sm.Refused, match="image pair"):
        sm.transition(db, alert, "CONFIRMED", actor=team.analyst, data={"image_pair_reviewed": True})


def test_field_confirmation_needs_photo_and_gps(db):
    team = Team(db)
    asset = make_asset(db)
    _, alert = ingest(db, asset, at=T0)
    sm.transition(db, alert, "CONFIRMED", actor=team.analyst, data={"image_pair_reviewed": True}, at=at(1))
    sm.transition(db, alert, "ASSIGNED", actor=team.nodal, data={"owner_user_id": team.field.id}, at=at(1))
    out = field_check(db, alert, team.field, photos=0, at=at(2))
    assert "geotagged photo" in out["step_refused"] and alert.state == "ASSIGNED"


def test_only_the_assigned_officer_can_submit(db):
    from app.services.field import FieldRefused

    team = Team(db)
    asset = make_asset(db)
    _, alert = ingest(db, asset, at=T0)
    sm.transition(db, alert, "CONFIRMED", actor=team.analyst, data={"image_pair_reviewed": True}, at=at(1))
    sm.transition(db, alert, "ASSIGNED", actor=team.nodal, data={"owner_user_id": team.field.id}, at=at(1))
    with pytest.raises(FieldRefused):
        field_check(db, alert, team.field2, at=at(2))


def test_distance_over_50_m_warns_but_does_not_block(db):
    team = Team(db)
    asset = make_asset(db)
    _, alert = ingest(db, asset, at=T0)
    sm.transition(db, alert, "CONFIRMED", actor=team.analyst, data={"image_pair_reviewed": True}, at=at(1))
    sm.transition(db, alert, "ASSIGNED", actor=team.nodal, data={"owner_user_id": team.field.id}, at=at(1))
    out = field_check(db, alert, team.field, near=False, at=at(2))
    assert out["distance_warning"] is True and out["distance_m"] > 300 and alert.state == "FIELD_CONFIRMED"


def test_cannot_access_keeps_the_timer_running(db):
    team = Team(db)
    asset = make_asset(db)
    _, alert = ingest(db, asset, at=T0)
    sm.transition(db, alert, "CONFIRMED", actor=team.analyst, data={"image_pair_reviewed": True}, at=at(1))
    sm.transition(db, alert, "ASSIGNED", actor=team.nodal, data={"owner_user_id": team.field.id}, at=at(1))
    due = alert.due_at
    field_check(db, alert, team.field, outcome="cannot_access", at=at(3))
    assert alert.state == "ASSIGNED" and alert.due_at == due


def test_monsoon_assignment_gets_14_days():
    july = dt.datetime(2025, 7, 1, tzinfo=dt.timezone.utc)
    assert timers.due_for("ASSIGNED", july) == july + dt.timedelta(days=14)
    assert timers.due_for("ASSIGNED", T0) == T0 + dt.timedelta(days=7)


def test_missed_timer_escalates_once_and_is_never_reset(db):
    team = Team(db)
    _, alert = ingest(db, make_asset(db), at=T0)
    assert escalation.run(db, now=at(2)) == []
    first = escalation.run(db, now=at(4))
    assert [m["notify"] for m in first] == ["reviewer"] and alert.escalation_level == 1
    assert escalation.run(db, now=at(5)) == []  # recorded once
    sm.transition(db, alert, "CONFIRMED", actor=team.analyst, data={"image_pair_reviewed": True}, at=at(6))
    assert alert.escalation_level == 1  # moving on does not reset it


def test_miss_found_on_transition_is_still_recorded(db):
    team = Team(db)
    _, alert = ingest(db, make_asset(db), at=T0)
    sm.transition(db, alert, "CONFIRMED", actor=team.analyst, data={"image_pair_reviewed": True}, at=at(5))
    misses = db.scalars(select(AuditLog).where(AuditLog.action == "timer.missed", AuditLog.entity_id == str(alert.id))).all()
    assert len(misses) == 1 and misses[0].details["detected"] == "on_transition" and alert.escalation_level == 1


def test_persisting_change_reopens_a_closed_alert(db):
    team = Team(db)
    asset = make_asset(db)
    _, alert = ingest(db, asset, at=T0)
    sm.transition(db, alert, "CLOSED_NOT_REAL", actor=team.analyst, reason="Looks like shadow", data={"reason_code": "shadow"}, at=at(1))
    sm.transition(db, alert, "CLOSED_NOT_REAL", actor=team.reviewer, at=at(1))
    assert alert.state == "CLOSED_NOT_REAL"
    out, same = ingest(db, asset, at=at(14), geometry=square(side_m=70), first_changed=dt.date(2025, 10, 12), last_clear=dt.date(2025, 10, 8))
    assert out["outcome"] == "reopened" and same.id == alert.id
    assert alert.state == "TRIAGE" and alert.reopened_count == 1


def test_change_on_an_open_alert_is_recorded_not_duplicated(db):
    asset = make_asset(db)
    _, alert = ingest(db, asset, at=T0)
    out, same = ingest(db, asset, at=at(7), first_changed=dt.date(2025, 10, 6), last_clear=dt.date(2025, 10, 1))
    assert out["outcome"] == "recorded_on_open_alert" and same.id == alert.id


def test_allowed_actions_follow_role_and_guards(db, client):
    team = Team(db)
    _, alert = ingest(db, make_asset(db), at=T0)
    analyst = {a["to"]: a for a in client.get(f"/alerts/{alert.id}", headers=auth(team.analyst)).json()["allowed_actions"]}
    assert set(analyst) == {"CONFIRMED", "CLOSED_NOT_REAL"} and analyst["CONFIRMED"]["enabled"]
    assert client.get(f"/alerts/{alert.id}", headers=auth(team.nodal)).json()["allowed_actions"] == []


def test_detail_carries_the_statement_and_legal_panel(db, client):
    team = Team(db)
    _, alert = ingest(db, make_asset(db), at=T0)
    body = client.get(f"/alerts/{alert.id}", headers=auth(team.analyst)).json()
    assert body["statement"] == "Imagery shows physical change. It does not establish title or legality."
    assert body["legal_check"]["zone"] == "inside_ftl" and body["boundary"]["confirmed"] is True
    assert body["candidate"]["last_clear_at"] == "2025-06-01" and body["is_demo"] is True


def test_field_officer_sees_only_their_own_alerts(db, client):
    team = Team(db)
    asset = make_asset(db)
    _, mine = ingest(db, asset, at=T0)
    _, other = ingest(db, make_asset(db), at=T0)
    sm.transition(db, mine, "CONFIRMED", actor=team.analyst, data={"image_pair_reviewed": True}, at=at(1))
    sm.transition(db, mine, "ASSIGNED", actor=team.nodal, data={"owner_user_id": team.field.id}, at=at(1))
    ids = [a["id"] for a in client.get("/alerts", headers=auth(team.field)).json()["items"]]
    assert ids == [mine.id]
    assert client.get(f"/alerts/{other.id}", headers=auth(team.field)).status_code == 404


def test_pipeline_ingest_needs_its_token(db, client, monkeypatch):
    from app.config import settings
    from tests.factories import candidate_in

    monkeypatch.setattr(settings, "pipeline_token", "test-token")
    payload = candidate_in(make_asset(db)).model_dump(mode="json")
    assert client.post("/candidates", json=payload).status_code == 401
    resp = client.post("/candidates", json=payload, headers={"X-Pipeline-Token": "test-token"})
    assert resp.status_code == 201 and resp.json()["state"] == "TRIAGE"


def test_imagery_request_is_recorded_not_ordered(db, client):
    team = Team(db)
    _, alert = ingest(db, make_asset(db), at=T0)
    resp = client.post(f"/alerts/{alert.id}/imagery-request", json={"provider": "commercial_archive"}, headers=auth(team.analyst))
    assert resp.status_code == 201 and resp.json()["status"] == "recorded" and resp.json()["est_cost_usd"] > 0


def test_priority_override_needs_a_reason_and_is_logged(db, client):
    team = Team(db)
    _, alert = ingest(db, make_asset(db), at=T0)
    assert client.post(f"/alerts/{alert.id}/priority-override", json={"score": 90, "reason": ""}, headers=auth(team.nodal)).status_code == 422
    assert client.post(f"/alerts/{alert.id}/priority-override", json={"score": 90, "reason": "CCTV report"}, headers=auth(team.nodal)).status_code == 200
    assert db.scalar(select(AuditLog).where(AuditLog.action == "priority.override")).details["reason"] == "CCTV report"


def test_closure_sample_is_repeatable(db, client):
    team = Team(db)
    for _ in range(3):
        _, a = ingest(db, make_asset(db), at=T0)
        sm.transition(db, a, "CLOSED_NOT_REAL", actor=team.analyst, reason="r", data={"reason_code": "x"}, at=at(1))
        sm.transition(db, a, "CLOSED_NOT_REAL", actor=team.reviewer, at=at(1))
    one = client.get("/audit/closure-sample?month=2025-10&n=2", headers=auth(team.auditor)).json()
    two = client.get("/audit/closure-sample?month=2025-10&n=2", headers=auth(team.auditor)).json()
    assert one["closures_in_month"] == 3 and one["sample"] == two["sample"] and len(one["sample"]) == 2
