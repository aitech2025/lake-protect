"""The monthly page (section 9.4) with incidents (D-057): new, reviewed, confirmed, and waiting
more than 14 days for a decision, worked out as at the end of each month."""
import datetime as dt
import io

import pytest
from pypdf import PdfReader

from app.bulletin import render, stats
from app.workflow import incidents
from tests.factories import Team, auth, decide, ingest, make_asset, review

UTC = dt.timezone.utc


def t(month: int, day: int, hour: int = 6) -> dt.datetime:
    return dt.datetime(2025, month, day, hour, tzinfo=UTC)


@pytest.fixture()
def scenario(db):
    team = Team(db)
    a1 = ingest(db, make_asset(db), at=t(10, 2), first_changed=dt.date(2025, 9, 20), last_clear=dt.date(2025, 9, 10))[1]
    a2 = ingest(db, make_asset(db), at=t(10, 3), first_changed=dt.date(2025, 9, 21), last_clear=dt.date(2025, 9, 11))[1]
    review(db, a2, team.viewer, at=t(10, 4))
    incidents.transition(db, a2, "CONFIRMED", actor=team.admin, note="Real", at=t(10, 6))
    a3 = ingest(db, make_asset(db), at=t(10, 25), first_changed=dt.date(2025, 10, 10), last_clear=dt.date(2025, 10, 1))[1]
    legacy = ingest(db, make_asset(db, baseline=dt.date(2025, 9, 30)), at=t(10, 7), first_changed=dt.date(2025, 9, 23), last_clear=dt.date(2025, 9, 13))[1]
    sep = ingest(db, make_asset(db), at=t(9, 10), first_changed=dt.date(2025, 8, 20), last_clear=dt.date(2025, 8, 10))[1]
    review(db, sep, team.viewer2, "not_real", "Shadow", at=t(9, 11))
    decide(db, sep, team.admin, "DISMISSED", at=t(9, 12))
    incidents.transition(db, sep, "CLOSED", actor=team.admin, note="Done", at=t(9, 13))
    assert (a1.state, a2.state, a3.state, legacy.state, sep.state) == ("OPEN", "CONFIRMED", "OPEN", "CLOSED", "CLOSED")
    return team, {"a1": a1, "a2": a2, "a3": a3, "legacy": legacy, "sep": sep}


def test_counts_and_waiting_list_for_a_closed_month(db, scenario):
    _, a = scenario
    out = stats.bulletin(db, "2025-10", now=t(11, 20))
    assert out["complete_month"] is True
    assert out["counts"] == {"watched": 5, "new_alerts": 3, "reviewed": 1, "confirmed": 1, "waiting": 1}
    assert [(w["code"], w["state"], w["days_waiting"]) for w in out["waiting"]] == [(a["a1"].code, "OPEN", 29)]
    assert out["change_types"] == {"soil_fill": 3}
    assert out["last_month"] == {"month": "2025-09", "counts": {"watched": 5, "new_alerts": 1, "reviewed": 1, "confirmed": 0, "waiting": 0}}


def test_current_month_is_worked_out_as_of_now(db, scenario):
    _, a = scenario
    out = stats.compute(db, "2025-11", now=t(11, 20))
    assert out["complete_month"] is False
    assert {w["code"] for w in out["waiting"]} == {a["a1"].code, a["a3"].code}
    assert out["counts"]["new_alerts"] == 0


def test_monthly_pdf_is_one_page_even_with_many_waiting(db, scenario):
    for _ in range(12):
        ingest(db, make_asset(db), at=t(10, 9), first_changed=dt.date(2025, 9, 25), last_clear=dt.date(2025, 9, 15))
    out = stats.bulletin(db, "2025-10", now=t(11, 20))
    assert out["counts"]["waiting"] == 13
    pdf = render.render_pdf(out, render.map_svg(db, out))
    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) == 1
    text = " ".join(reader.pages[0].extract_text().split())
    assert "Monthly page: October 2025" in text and "Demo data" not in text and "and 5 more" in text and "Land fill" in text


def test_bulletin_api_for_both_roles(db, client, scenario):
    team, _ = scenario
    assert client.get("/bulletins/2025-10").status_code == 401
    body = client.get("/bulletins/2025-10", headers=auth(team.viewer)).json()
    assert body["map_svg"].startswith("<svg") and body["counts"]["new_alerts"] == 3
    pdf = client.get("/bulletins/2025-10/pdf", headers=auth(team.admin))
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert client.get("/bulletins", headers=auth(team.viewer)).json()[0]["month"] == "2025-10"
    assert client.get("/bulletins/2025-13", headers=auth(team.viewer)).status_code == 422
