"""The incident lifecycle (DECISIONS.md D-057): two roles, viewers review, the admin decides.

OPEN -> UNDER_REVIEW (a viewer's review, or the admin starts one) -> CONFIRMED or DISMISSED
(admin, with a note) -> CLOSED (admin, with a note). The legal check closes some changes at once.
"""
import datetime as dt

import pytest
from geoalchemy2.elements import WKTElement
from shapely.geometry import shape
from sqlalchemy import func, select

from app.models import Alert, AuthorisedWork, CourtCase, IncidentReview
from app.workflow import incidents
from tests.factories import Team, auth, decide, ingest, make_asset, rect, review, square

T0 = dt.datetime(2025, 6, 20, 6, tzinfo=dt.timezone.utc)


def at(days: float) -> dt.datetime:
    return T0 + dt.timedelta(days=days)


def wkt(geojson: dict) -> WKTElement:
    g = shape(geojson)
    return WKTElement(f"MULTIPOLYGON((({', '.join(f'{x} {y}' for x, y in g.exterior.coords)})))", srid=4326)


def test_a_change_opens_an_incident_that_says_what_changed(db, client):
    team = Team(db)
    out, alert = ingest(db, make_asset(db, geometry=square(side_m=450)), change_type="soil_fill", geometry=square(side_m=60))
    assert out["outcome"] == "created" and alert.state == "OPEN" and alert.resolution is None
    body = client.get(f"/alerts/{alert.id}", headers=auth(team.viewer)).json()
    assert body["change_label"] == "Land fill"
    assert body["summary"].startswith("Land fill of about 3,") and "sq m inside the boundary" in body["summary"]
    assert "first seen 10 Jun 2025" in body["summary"]


@pytest.mark.parametrize("change_type,label", [("building", "Construction"), ("soil_fill", "Land fill"),
                                               ("levelling", "Levelling"), ("clearing", "Clearing")])
def test_each_change_type_is_named_plainly(db, client, change_type, label):
    team = Team(db)
    _, alert = ingest(db, make_asset(db), change_type=change_type)
    items = client.get("/alerts", headers=auth(team.admin)).json()["items"]
    assert [i["change_label"] for i in items if i["id"] == alert.id] == [label]
    filtered = client.get(f"/alerts?change_type={change_type}", headers=auth(team.admin)).json()["items"]
    assert {i["id"] for i in filtered} == {alert.id}


def test_full_path_review_confirm_close(db, client):
    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    r = client.post(f"/alerts/{alert.id}/reviews", json={"outcome": "real_change", "note": "Fresh soil on both images"}, headers=auth(team.viewer))
    assert r.status_code == 201 and r.json()["state"] == "UNDER_REVIEW"
    r2 = client.post(f"/alerts/{alert.id}/reviews", json={"outcome": "needs_site_visit", "note": "Check on site"}, headers=auth(team.viewer2))
    assert r2.status_code == 201 and r2.json()["state"] == "UNDER_REVIEW"

    assert client.post(f"/alerts/{alert.id}/transitions", json={"to": "CONFIRMED"}, headers=auth(team.admin)).status_code == 422
    ok = client.post(f"/alerts/{alert.id}/transitions", json={"to": "CONFIRMED", "note": "Real change"}, headers=auth(team.admin))
    assert ok.status_code == 200 and ok.json()["resolution"] == "confirmed"
    closed = client.post(f"/alerts/{alert.id}/transitions", json={"to": "CLOSED", "note": "Fill removed"}, headers=auth(team.admin))
    assert closed.status_code == 200
    db.refresh(alert)
    assert (alert.state, alert.resolution) == ("CLOSED", "confirmed") and alert.closed_at is not None

    detail = client.get(f"/alerts/{alert.id}", headers=auth(team.viewer)).json()
    assert [(r["outcome"], r["reviewer"]) for r in detail["reviews"]] == [("real_change", team.viewer.name), ("needs_site_visit", team.viewer2.name)]
    steps = [t["details"].get("to") for t in detail["timeline"] if t["action"] == "alert.transition"]
    assert steps == ["UNDER_REVIEW", "CONFIRMED", "CLOSED"]


def test_dismiss_then_close(db):
    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    review(db, alert, team.viewer, "not_real", "Cloud shadow")
    incidents.transition(db, alert, "DISMISSED", actor=team.admin, note="Cloud shadow", at=at(2))
    assert (alert.state, alert.resolution) == ("DISMISSED", "dismissed")
    incidents.transition(db, alert, "CLOSED", actor=team.admin, note="Done", at=at(3))
    assert (alert.state, alert.resolution) == ("CLOSED", "dismissed")


def test_roles_are_kept_apart(db, client):
    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    # The admin decides but does not review; a viewer reviews but does not decide.
    assert client.post(f"/alerts/{alert.id}/reviews", json={"outcome": "real_change", "note": "x"}, headers=auth(team.admin)).status_code == 403
    assert client.post(f"/alerts/{alert.id}/transitions", json={"to": "UNDER_REVIEW", "note": "x"}, headers=auth(team.viewer)).status_code == 403
    # The admin may start a review when no viewer has.
    started = client.post(f"/alerts/{alert.id}/transitions", json={"to": "UNDER_REVIEW", "note": "Starting"}, headers=auth(team.admin))
    assert started.status_code == 200 and started.json()["state"] == "UNDER_REVIEW"


def test_steps_must_follow_the_order(db):
    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    with pytest.raises(incidents.Refused, match="no step from OPEN to CONFIRMED"):
        incidents.transition(db, alert, "CONFIRMED", actor=team.admin, note="Too early")
    decide(db, alert, team.admin, "CONFIRMED")
    with pytest.raises(incidents.Refused, match="reviews are taken while it is open or under review"):
        review(db, alert, team.viewer)
    with pytest.raises(incidents.Refused, match="no step from CONFIRMED to DISMISSED"):
        incidents.transition(db, alert, "DISMISSED", actor=team.admin, note="Changed my mind")


def test_allowed_actions_follow_role_and_state(db, client):
    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    viewer = client.get(f"/alerts/{alert.id}", headers=auth(team.viewer)).json()["allowed_actions"]
    assert viewer == [{"action": "review", "label": "Record your review", "already_reviewed": False}]
    review(db, alert, team.viewer)
    admin = client.get(f"/alerts/{alert.id}", headers=auth(team.admin)).json()["allowed_actions"]
    assert [a["to"] for a in admin] == ["CONFIRMED", "DISMISSED"]
    again = client.get(f"/alerts/{alert.id}", headers=auth(team.viewer)).json()["allowed_actions"]
    assert again[0]["already_reviewed"] is True


def test_legal_check_closes_changes_before_the_baseline_at_once(db, client):
    team = Team(db)
    out, alert = ingest(db, make_asset(db, baseline=dt.date(2025, 6, 15)), first_changed=dt.date(2025, 6, 10))
    assert out["outcome"] == "closed_by_legal_check"
    assert (alert.state, alert.resolution) == ("CLOSED", "auto")
    detail = client.get(f"/alerts/{alert.id}", headers=auth(team.viewer)).json()
    assert detail["legal_check"]["verdict"] == "CLOSED_LEGACY"
    assert "before the baseline" in detail["legal_check"]["auto_close_reason"]
    assert detail["allowed_actions"] == []


def test_legal_check_closes_authorised_works_at_once(db):
    asset = make_asset(db, geometry=square(side_m=450))
    db.add(AuthorisedWork(agency="Test agency", description="Restoration", ref="TEST-W", geom=wkt(square(side_m=60)), starts_on=dt.date(2025, 5, 1), is_demo=True))
    db.flush()
    _, alert = ingest(db, asset, geometry=square(side_m=40))
    assert (alert.state, alert.resolution) == ("CLOSED", "auto")


def test_court_matter_and_unconfirmed_boundary_stay_open_and_flagged(db, client):
    team = Team(db)
    asset = make_asset(db, cohort="B_FINAL")
    db.add(CourtCase(court="Test court", case_no="TEST-1", status="pending", asset_id=asset.id, is_demo=True))
    db.flush()
    _, held = ingest(db, asset)
    _, watched = ingest(db, make_asset(db, cohort="D_UNNOTIFIED"))
    rows = {i["id"]: i for i in client.get("/alerts", headers=auth(team.viewer)).json()["items"]}
    assert held.state == "OPEN" and rows[held.id]["court_matter"] is True
    assert watched.state == "OPEN" and rows[watched.id]["boundary_confirmed"] is False


def test_the_same_change_again_is_recorded_not_duplicated(db):
    asset = make_asset(db)
    _, first = ingest(db, asset, at=T0)
    out, again = ingest(db, asset, at=at(7))
    assert out["outcome"] == "recorded_on_open_incident" and again.id == first.id
    assert db.scalar(select(func.count()).select_from(Alert)) == 1


def test_a_change_seen_again_after_dismissal_opens_a_linked_incident(db, client):
    team = Team(db)
    asset = make_asset(db)
    _, first = ingest(db, asset, at=T0)
    decide(db, first, team.admin, "DISMISSED")
    incidents.transition(db, first, "CLOSED", actor=team.admin, note="Dismissed", at=at(3))
    out, second = ingest(db, asset, at=at(30), geometry=rect(-40, 40, -40, 40), first_changed=dt.date(2025, 7, 10), last_clear=dt.date(2025, 7, 1))
    assert out["outcome"] == "created" and second.id != first.id and second.related_alert_id == first.id
    detail = client.get(f"/alerts/{second.id}", headers=auth(team.viewer)).json()
    assert detail["related"]["code"] == first.code


def test_reviews_are_append_only(db):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    row = review(db, alert, team.viewer)
    with pytest.raises(DBAPIError, match="append-only"):
        with db.begin_nested():
            db.execute(text("UPDATE incident_reviews SET note = 'changed' WHERE id = :i"), {"i": row.id})
    assert db.scalar(select(func.count()).select_from(IncidentReview)) == 1


def test_imagery_request_and_priority_override_are_admin_only(db, client):
    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    assert client.post(f"/alerts/{alert.id}/imagery-request", json={"provider": "commercial_archive"}, headers=auth(team.viewer)).status_code == 403
    r = client.post(f"/alerts/{alert.id}/imagery-request", json={"provider": "commercial_archive"}, headers=auth(team.admin))
    assert r.status_code == 201 and "Recorded only" in r.json()["note"]
    assert client.post(f"/alerts/{alert.id}/priority-override", json={"score": 90, "reason": "Near a school"}, headers=auth(team.admin)).status_code == 200


def test_closure_sample_is_repeatable(db, client):
    team = Team(db)
    for n in range(4):
        _, alert = ingest(db, make_asset(db), at=at(n))
        decide(db, alert, team.admin, "DISMISSED", at=at(n + 1))
        incidents.transition(db, alert, "CLOSED", actor=team.admin, note="Done", at=at(n + 2))
    month = at(2).strftime("%Y-%m")
    one = client.get(f"/audit/closure-sample?month={month}&n=2", headers=auth(team.viewer)).json()
    two = client.get(f"/audit/closure-sample?month={month}&n=2", headers=auth(team.admin)).json()
    assert one["sample"] == two["sample"] and len(one["sample"]) == 2
    assert {s["closed_as"] for s in one["sample"]} == {"dismissed"}
