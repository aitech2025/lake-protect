"""The incident lifecycle (DECISIONS.md D-057, D-067).

OPEN -> UNDER_REVIEW (an officer's review, or they start one) -> FIELD_VISIT (a field officer is
assigned) -> FIELD_REPORTED (their report) -> RECOMMENDED (the district officer) -> CONFIRMED or
DISMISSED (the senior official approves) -> CLOSED (the senior official). A field visit is
optional, a report or a recommendation can be returned, and the admin takes no step. The legal
check closes some changes at once.
"""
import datetime as dt

import pytest
from geoalchemy2.elements import WKTElement
from shapely.geometry import shape
from sqlalchemy import func, select

from app.models import Alert, AuthorisedWork, CourtCase, IncidentReview
from app.workflow import incidents
from tests.factories import Team, auth, cover, decide, ingest, make_asset, make_user, rect, review, square

T0 = dt.datetime(2025, 6, 20, 6, tzinfo=dt.timezone.utc)


def at(days: float) -> dt.datetime:
    return T0 + dt.timedelta(days=days)


def wkt(geojson: dict) -> WKTElement:
    g = shape(geojson)
    return WKTElement(f"MULTIPOLYGON((({', '.join(f'{x} {y}' for x, y in g.exterior.coords)})))", srid=4326)


def field_report(client, alert, user, outcome="confirmed", findings="Fresh fill along the bund", photos=0):
    files = [("photos", (f"p{i}.png", _png(), "image/png")) for i in range(photos)]
    data = {"outcome": outcome, "findings": findings, "observed_at": "2025-06-21T05:00:00+00:00", "lat": "14.5", "lon": "81.5"}
    return client.post(f"/alerts/{alert.id}/field-report", data=data, files=files or None, headers=auth(user))


def _png() -> bytes:
    import base64

    return base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def test_a_change_opens_an_incident_that_says_what_changed(db, client):
    team = Team(db)
    out, alert = ingest(db, make_asset(db, geometry=square(side_m=450)), change_type="soil_fill", geometry=square(side_m=60))
    assert out["outcome"] == "created" and alert.state == "OPEN" and alert.resolution is None
    body = client.get(f"/alerts/{alert.id}", headers=auth(team.district)).json()
    assert body["change_label"] == "Land fill"
    assert body["summary"].startswith("Land fill of about 3,") and "sq m inside the boundary" in body["summary"]
    assert "first seen 10 Jun 2025" in body["summary"]


@pytest.mark.parametrize("change_type,label", [("building", "Construction"), ("soil_fill", "Land fill"),
                                               ("levelling", "Levelling"), ("clearing", "Clearing")])
def test_each_change_type_is_named_plainly(db, client, change_type, label):
    team = Team(db)
    _, alert = ingest(db, make_asset(db), change_type=change_type)
    items = client.get("/alerts", headers=auth(team.senior)).json()["items"]
    assert [i["change_label"] for i in items if i["id"] == alert.id] == [label]
    filtered = client.get(f"/alerts?change_type={change_type}", headers=auth(team.senior)).json()["items"]
    assert {i["id"] for i in filtered} == {alert.id}


def test_full_path_review_field_visit_recommend_approve_close(db, client):
    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    r = client.post(f"/alerts/{alert.id}/reviews", json={"outcome": "needs_site_visit", "note": "Check on site"}, headers=auth(team.district))
    assert r.status_code == 201 and r.json()["state"] == "UNDER_REVIEW"

    offered = client.get(f"/alerts/{alert.id}/field-officers", headers=auth(team.district)).json()["items"]
    assert [o["id"] for o in offered] == [team.field.id]
    assigned = client.post(f"/alerts/{alert.id}/assignments", json={"field_officer_id": team.field.id, "note": "Photograph the east bund"},
                           headers=auth(team.district))
    assert assigned.status_code == 201 and assigned.json()["state"] == "FIELD_VISIT"

    reported = field_report(client, alert, team.field, photos=2)
    assert reported.status_code == 201 and reported.json()["state"] == "FIELD_REPORTED"

    assert client.post(f"/alerts/{alert.id}/recommendation", json={"recommendation": "confirm", "note": ""}, headers=auth(team.district)).status_code == 422
    rec = client.post(f"/alerts/{alert.id}/recommendation", json={"recommendation": "confirm", "note": "Fill confirmed on site"},
                      headers=auth(team.district))
    assert rec.status_code == 201 and rec.json()["state"] == "RECOMMENDED"

    ok = client.post(f"/alerts/{alert.id}/transitions", json={"to": "CONFIRMED", "note": "Approved"}, headers=auth(team.senior))
    assert ok.status_code == 200 and ok.json()["resolution"] == "confirmed"
    closed = client.post(f"/alerts/{alert.id}/transitions", json={"to": "CLOSED", "note": "Passed to the revenue office"}, headers=auth(team.senior))
    assert closed.status_code == 200
    db.refresh(alert)
    assert (alert.state, alert.resolution) == ("CLOSED", "confirmed") and alert.closed_at is not None

    detail = client.get(f"/alerts/{alert.id}", headers=auth(team.senior)).json()
    assert [(f["field_officer"], f["outcome"], f["photos"]) for f in detail["field_reports"]] == [(team.field.name, "confirmed", 2)]
    assert detail["recommendation"]["recommendation"] == "confirm" and detail["recommendation"]["field_report_id"] == detail["field_reports"][0]["id"]
    steps = [t["details"].get("to") for t in detail["timeline"] if t["action"] == "alert.transition"]
    assert steps == ["UNDER_REVIEW", "FIELD_VISIT", "FIELD_REPORTED", "RECOMMENDED", "CONFIRMED", "CLOSED"]


def test_a_field_visit_is_optional(db):
    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    incidents.recommend(db, alert, team.district, "dismiss", "Cloud shadow on both images", at=at(1))
    assert alert.state == "RECOMMENDED"
    incidents.transition(db, alert, "DISMISSED", actor=team.senior, note="Agreed", at=at(2))
    incidents.transition(db, alert, "CLOSED", actor=team.senior, note="Done", at=at(3))
    assert (alert.state, alert.resolution) == ("CLOSED", "dismissed")


def test_a_returned_field_report_goes_back_to_the_same_field_officer(db, client):
    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    incidents.assign(db, alert, team.district, team.field.id, "Visit", at=at(1))
    assert field_report(client, alert, team.field).status_code == 201
    back = client.post(f"/alerts/{alert.id}/transitions", json={"to": "FIELD_VISIT", "note": "Add a photo from the north side"},
                       headers=auth(team.district))
    assert back.status_code == 200 and back.json()["state"] == "FIELD_VISIT"
    assert field_report(client, alert, team.field, findings="North side photographed").status_code == 201
    assert len(client.get(f"/alerts/{alert.id}", headers=auth(team.district)).json()["field_reports"]) == 2


def test_a_returned_recommendation_goes_back_to_review(db, client):
    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    incidents.recommend(db, alert, team.district, "confirm", "Real change", at=at(1))
    back = client.post(f"/alerts/{alert.id}/transitions", json={"to": "UNDER_REVIEW", "note": "Attach the survey sketch"}, headers=auth(team.senior))
    assert back.status_code == 200 and back.json()["state"] == "UNDER_REVIEW"
    notes = client.get("/notifications", headers=auth(team.district)).json()["items"]
    assert any(n["kind"] == "returned" and n["alert_id"] == alert.id for n in notes)


def test_the_senior_official_approves_only_what_was_recommended(db, client):
    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    incidents.recommend(db, alert, team.district, "confirm", "Real change", at=at(1))
    wrong = client.post(f"/alerts/{alert.id}/transitions", json={"to": "DISMISSED", "note": "No"}, headers=auth(team.senior))
    assert wrong.status_code == 409 and "recommendation was to confirm" in wrong.json()["detail"]


def test_each_persona_takes_only_its_own_steps(db, client):
    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    post = lambda path, body, who: client.post(f"/alerts/{alert.id}/{path}", json=body, headers=auth(who))  # noqa: E731
    # The admin maintains the application and takes no step on an incident.
    assert post("reviews", {"outcome": "real_change", "note": "x"}, team.admin).status_code == 403
    assert post("transitions", {"to": "UNDER_REVIEW", "note": "x"}, team.admin).status_code == 403
    assert post("assignments", {"field_officer_id": team.field.id, "note": "x"}, team.admin).status_code == 403
    # A field officer works only an incident assigned to them.
    assert client.get(f"/alerts/{alert.id}", headers=auth(team.field)).status_code == 403
    # Only the district officer recommends where one covers the place; the senior official cannot skip them.
    assert post("recommendation", {"recommendation": "confirm", "note": "x"}, team.senior).status_code == 403
    assert post("transitions", {"to": "CONFIRMED", "note": "x"}, team.senior).status_code == 403
    # Officers start the review.
    assert post("transitions", {"to": "UNDER_REVIEW", "note": "Starting"}, team.district).json()["state"] == "UNDER_REVIEW"
    # Only the assigned field officer reports.
    incidents.assign(db, alert, team.district, team.field.id, "Visit", at=at(1))
    other_field = make_user(db, "field_officer")
    cover(db, other_field, "Test District")
    assert field_report(client, alert, other_field).status_code == 403
    assert field_report(client, alert, team.district).status_code == 403


def test_where_no_district_officer_covers_the_place_the_senior_official_decides(db, client):
    team = Team(db)
    _, alert = ingest(db, make_asset(db, district="Elsewhere"))
    actions = client.get(f"/alerts/{alert.id}", headers=auth(team.senior)).json()["allowed_actions"]
    assert {a.get("to") for a in actions if a.get("direct")} == {"CONFIRMED", "DISMISSED"}
    ok = client.post(f"/alerts/{alert.id}/transitions", json={"to": "DISMISSED", "note": "Not a change"}, headers=auth(team.senior))
    assert ok.status_code == 200 and ok.json()["state"] == "DISMISSED"
    detail = client.get(f"/alerts/{alert.id}", headers=auth(team.senior)).json()
    assert any(t["details"].get("no_district_officer") for t in detail["timeline"] if t["action"] == "alert.transition")
    # A district officer of another district does not see it.
    assert client.get(f"/alerts/{alert.id}", headers=auth(team.district)).status_code == 403


def test_a_field_officer_is_assigned_only_where_they_cover(db):
    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    far = make_user(db, "field_officer")
    cover(db, far, "Elsewhere")
    with pytest.raises(incidents.Refused, match="does not cover"):
        incidents.assign(db, alert, team.district, far.id, "Visit", at=at(1))
    with pytest.raises(incidents.Refused, match="active field officer"):
        incidents.assign(db, alert, team.district, team.district2.id, "Visit", at=at(1))


def test_steps_must_follow_the_order(db):
    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    with pytest.raises(incidents.Refused, match="no step from OPEN to CLOSED"):
        incidents.transition(db, alert, "CLOSED", actor=team.senior, note="Too early")
    decide(db, alert, team.senior, "CONFIRMED")
    with pytest.raises(incidents.Refused, match="reviews are taken while it is open or under review"):
        review(db, alert, team.district)
    with pytest.raises(incidents.Refused, match="no step from CONFIRMED to DISMISSED"):
        incidents.transition(db, alert, "DISMISSED", actor=team.senior, note="Changed my mind")


def test_allowed_actions_follow_persona_and_state(db, client):
    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    actions = lambda who: [a["action"] + ":" + a.get("to", "") for a in client.get(f"/alerts/{alert.id}", headers=auth(who)).json()["allowed_actions"]]  # noqa: E731
    assert actions(team.district) == ["review:", "transition:UNDER_REVIEW", "assign:", "recommend:"]
    assert actions(team.senior) == ["review:", "transition:UNDER_REVIEW", "assign:"]
    assert actions(team.admin) == []
    incidents.assign(db, alert, team.district, team.field.id, "Visit", at=at(1))
    assert actions(team.field) == ["field_report:"]
    assert actions(team.district) == ["assign:", "transition:UNDER_REVIEW"]
    incidents.transition(db, alert, "UNDER_REVIEW", actor=team.district, note="Withdrawn", at=at(2))
    incidents.recommend(db, alert, team.district, "confirm", "Real", at=at(3))
    assert actions(team.senior) == ["transition:CONFIRMED", "transition:UNDER_REVIEW"]
    assert actions(team.district) == []


def test_legal_check_closes_changes_before_the_baseline_at_once(db, client):
    team = Team(db)
    out, alert = ingest(db, make_asset(db, baseline=dt.date(2025, 6, 15)), first_changed=dt.date(2025, 6, 10))
    assert out["outcome"] == "closed_by_legal_check"
    assert (alert.state, alert.resolution) == ("CLOSED", "auto")
    detail = client.get(f"/alerts/{alert.id}", headers=auth(team.district)).json()
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
    rows = {i["id"]: i for i in client.get("/alerts", headers=auth(team.district)).json()["items"]}
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
    decide(db, first, team.senior, "DISMISSED")
    incidents.transition(db, first, "CLOSED", actor=team.senior, note="Dismissed", at=at(3))
    out, second = ingest(db, asset, at=at(30), geometry=rect(-40, 40, -40, 40), first_changed=dt.date(2025, 7, 10), last_clear=dt.date(2025, 7, 1))
    assert out["outcome"] == "created" and second.id != first.id and second.related_alert_id == first.id
    detail = client.get(f"/alerts/{second.id}", headers=auth(team.district)).json()
    assert detail["related"]["code"] == first.code


def test_reviews_assignments_reports_and_recommendations_are_append_only(db, client):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    row = review(db, alert, team.district)
    incidents.assign(db, alert, team.district, team.field.id, "Visit", at=at(1))
    assert field_report(client, alert, team.field).status_code == 201
    incidents.recommend(db, alert, team.district, "confirm", "Real", at=at(3))
    for table in ("incident_reviews", "incident_assignments", "field_reports", "incident_recommendations"):
        with pytest.raises(DBAPIError, match="append-only"):
            with db.begin_nested():
                db.execute(text(f"DELETE FROM {table}"))
    assert db.scalar(select(func.count()).select_from(IncidentReview)) == 1 and row.id


def test_the_database_refuses_an_assignment_to_someone_who_is_not_a_field_officer(db):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    with pytest.raises(DBAPIError, match="only a field officer"):
        with db.begin_nested():
            db.execute(text("INSERT INTO incident_assignments (alert_id, field_officer_id, assigned_by, note, at) VALUES (:a, :u, :u, 'x', now())"),
                       {"a": alert.id, "u": team.district.id})


def test_imagery_request_is_for_the_officers_and_priority_override_for_the_admin(db, client):
    team = Team(db)
    _, alert = ingest(db, make_asset(db))
    assert client.post(f"/alerts/{alert.id}/imagery-request", json={"provider": "commercial_archive"}, headers=auth(team.admin)).status_code == 403
    r = client.post(f"/alerts/{alert.id}/imagery-request", json={"provider": "commercial_archive"}, headers=auth(team.district))
    assert r.status_code == 201 and r.json()["status"] == "requested" and "Recorded only" in r.json()["note"]
    mine = client.post(f"/alerts/{alert.id}/imagery-request", json={"provider": "commercial_archive"}, headers=auth(team.senior))
    assert mine.json()["status"] == "approved"
    assert client.post(f"/alerts/{alert.id}/priority-override", json={"score": 90, "reason": "Near a school"}, headers=auth(team.admin)).status_code == 200


def test_closure_sample_is_repeatable(db, client):
    team = Team(db)
    for n in range(4):
        _, alert = ingest(db, make_asset(db), at=at(n))
        decide(db, alert, team.senior, "DISMISSED", at=at(n + 1))
        incidents.transition(db, alert, "CLOSED", actor=team.senior, note="Done", at=at(n + 2))
    month = at(2).strftime("%Y-%m")
    one = client.get(f"/audit/closure-sample?month={month}&n=2", headers=auth(team.senior)).json()
    two = client.get(f"/audit/closure-sample?month={month}&n=2", headers=auth(team.admin)).json()
    assert one["sample"] == two["sample"] and len(one["sample"]) == 2
    assert {s["closed_as"] for s in one["sample"]} == {"dismissed"}
    assert client.get(f"/audit/closure-sample?month={month}&n=2", headers=auth(team.district)).status_code == 403
