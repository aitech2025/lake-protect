"""M8: officer record, the escalation worker, and the monthly page."""
import contextlib
import datetime as dt
import io

import pytest
from pypdf import PdfReader

from app.bulletin import render, stats
from app.workflow import state_machine as sm
from tests.factories import Team, add_pack_row, auth, field_check, ingest, make_asset, record_checklist

UTC = dt.timezone.utc


def t(month: int, day: int, hour: int = 6) -> dt.datetime:
    return dt.datetime(2025, month, day, hour, tzinfo=UTC)


def confirm_assign(db, team, alert, when):
    sm.transition(db, alert, "CONFIRMED", actor=team.analyst, data={"image_pair_reviewed": True}, at=when)
    sm.transition(db, alert, "ASSIGNED", actor=team.nodal, data={"owner_user_id": team.field.id}, at=when + dt.timedelta(hours=1))


@pytest.fixture()
def scenario(db):
    team = Team(db)
    a1 = ingest(db, make_asset(db), at=t(10, 2), first_changed=dt.date(2025, 9, 20), last_clear=dt.date(2025, 9, 10))[1]
    a2 = ingest(db, make_asset(db), at=t(10, 3), first_changed=dt.date(2025, 9, 21), last_clear=dt.date(2025, 9, 11))[1]
    confirm_assign(db, team, a2, t(10, 4))
    field_check(db, a2, team.field, at=t(10, 6))
    a3 = ingest(db, make_asset(db), at=t(10, 5), first_changed=dt.date(2025, 9, 22), last_clear=dt.date(2025, 9, 12))[1]
    confirm_assign(db, team, a3, t(10, 28))
    legacy = ingest(db, make_asset(db, baseline=dt.date(2025, 9, 30)), at=t(10, 7), first_changed=dt.date(2025, 9, 23), last_clear=dt.date(2025, 9, 13))[1]
    sep = ingest(db, make_asset(db), at=t(9, 10), first_changed=dt.date(2025, 8, 20), last_clear=dt.date(2025, 8, 10))[1]
    sm.transition(db, sep, "CONFIRMED", actor=team.analyst, data={"image_pair_reviewed": True}, at=t(9, 11))
    assert (a1.state, a2.state, a3.state, legacy.state, sep.state) == ("TRIAGE", "FIELD_CONFIRMED", "ASSIGNED", "CLOSED_LEGACY", "CONFIRMED")
    return team, {"a1": a1, "a2": a2, "a3": a3, "legacy": legacy, "sep": sep}


def test_overdue_list_and_counts_for_a_closed_month(db, scenario):
    _, a = scenario
    out = stats.bulletin(db, "2025-10", demo=True, now=t(11, 20))
    assert out["complete_month"] is True
    assert out["counts"] == {"watched": 5, "new_alerts": 3, "verified": 1, "action_taken": 0, "overdue": 2}
    assert [(o["code"], o["state"], o["responsible"]) for o in out["overdue"]] == [
        (a["a1"].code, "TRIAGE", "Analyst desk"),  # due 5 Oct, 26 days late at month end
        (a["a2"].code, "FIELD_CONFIRMED", "Nodal officer (case file)"),  # due 13 Oct
    ]
    assert out["overdue"][0]["days_overdue"] == 26
    # a3 was assigned on 28 Oct with 7 days, so it was not overdue at the end of October.
    assert a["a3"].code not in [o["code"] for o in out["overdue"]]
    assert out["last_month"] == {"month": "2025-09", "counts": {"watched": 5, "new_alerts": 1, "verified": 0, "action_taken": 0, "overdue": 0}}


def test_current_month_is_worked_out_as_of_now(db, scenario):
    team, a = scenario
    out = stats.compute(db, "2025-11", demo=True, now=t(11, 20))
    assert out["complete_month"] is False
    assert {o["code"]: o["responsible"] for o in out["overdue"]} == {
        a["a1"].code: "Analyst desk",
        a["a2"].code: "Nodal officer (case file)",
        a["a3"].code: team.field.name,  # due 4 Nov
    }
    assert out["counts"]["new_alerts"] == 0


def test_monthly_pdf_is_one_page_even_with_many_overdue(db, scenario):
    for _ in range(12):
        ingest(db, make_asset(db), at=t(10, 9), first_changed=dt.date(2025, 9, 25), last_clear=dt.date(2025, 9, 15))
    out = stats.bulletin(db, "2025-10", demo=True, now=t(11, 20))
    assert out["counts"]["overdue"] == 14
    pdf = render.render_pdf(out, render.map_svg(db, out, demo=True))
    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) == 1
    text = " ".join(reader.pages[0].extract_text().split())
    assert "Monthly page: October 2025" in text and "Demo data" in text and "and 6 more" in text


def test_bulletin_api_roles_and_pdf(db, client, scenario):
    team, _ = scenario
    assert client.get("/bulletins/2025-10", headers=auth(team.field)).status_code == 403
    body = client.get("/bulletins/2025-10", headers=auth(team.senior)).json()
    assert body["map_svg"].startswith("<svg") and body["counts"]["new_alerts"] == 3
    pdf = client.get("/bulletins/2025-10/pdf", headers=auth(team.senior))
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert client.get("/bulletins", headers=auth(team.senior)).json()[0]["month"] == "2025-10"
    assert client.get("/bulletins/2025-13", headers=auth(team.senior)).status_code == 422


def _with_officer(db, team):
    alert = ingest(db, make_asset(db), at=t(10, 2), first_changed=dt.date(2025, 9, 20), last_clear=dt.date(2025, 9, 10))[1]
    confirm_assign(db, team, alert, t(10, 3))
    field_check(db, alert, team.field, at=t(10, 5))
    add_pack_row(db, alert, team.nodal)
    record_checklist(db, alert, team.nodal)
    sm.transition(db, alert, "PACK_READY", actor=team.nodal, at=t(10, 6))
    sm.transition(db, alert, "WITH_OFFICER", actor=team.nodal, at=t(10, 7))
    return alert


def test_officer_record_and_action(db, client):
    team = Team(db)
    alert = _with_officer(db, team)
    body = {"notice_ref": "TEST/NOTICE/1", "notice_date": "2025-10-10", "order_ref": "TEST/ORDER/1", "order_date": "2025-10-20", "record_action": True}
    assert client.post(f"/alerts/{alert.id}/officer-record", json=body, headers=auth(team.analyst)).status_code == 403
    assert client.post(f"/alerts/{alert.id}/officer-record", json={"action_summary": "x"}, headers=auth(team.legal)).status_code == 422
    resp = client.post(f"/alerts/{alert.id}/officer-record", json=body, headers=auth(team.legal))
    assert resp.status_code == 201 and resp.json()["state"] == "POST_ACTION_WATCH"
    detail = client.get(f"/alerts/{alert.id}", headers=auth(team.legal)).json()
    assert detail["officer_records"][0]["order_ref"] == "TEST/ORDER/1"
    assert client.post(f"/alerts/{alert.id}/officer-record", json=body, headers=auth(team.legal)).status_code == 409


def test_worker_tick_escalates_missed_timers(db, monkeypatch):
    from app import worker

    ingest(db, make_asset(db), at=t(10, 2), first_changed=dt.date(2025, 9, 20), last_clear=dt.date(2025, 9, 10))

    @contextlib.contextmanager
    def session():
        yield db

    monkeypatch.setattr(worker, "SessionLocal", session)
    first = worker.tick()
    assert [m["notify"] for m in first] == ["reviewer"]
    assert worker.tick() == []  # recorded once, never reset
