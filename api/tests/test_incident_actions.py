"""What officers do on an incident a citizen reported (DECISIONS.md D-064, D-067): the district officer of
the area and the senior official act; the admin maintains the application and takes no step.

Fictional reports and fixtures at a Telangana test point (factories.TG_LON, TG_LAT) or a real
Hyderabad point, in the test database only. The tests post the screener's answers to satellite looks.
"""
from __future__ import annotations

import datetime as dt
import json

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.clock import utcnow
from app.config import settings
from app.models import Alert, Asset, Candidate, CitizenReport, CourtCase, Notification, SatelliteReview
from tests.factories import PNG_B64, TG_LAT, TG_LON, auth, cover, ingest, make_asset, make_user, offset, square

TOKEN = {"X-Pipeline-Token": "test-token"}


def report(client, db, *, lon=TG_LON, lat=TG_LAT, what="dumping") -> Alert:
    data = {"language": "te", "what": what, "lon": lon, "lat": lat, "description": "Soil dumped at night"}
    resp = client.post("/citizen/reports", data={"data": json.dumps(data)})
    assert resp.status_code == 201, resp.text
    r = db.scalar(select(CitizenReport).where(CitizenReport.ref == resp.json()["ref"]))
    return db.get(Alert, r.alert_id)


def public(client, db, alert: Alert) -> dict:
    ref = db.get(CitizenReport, alert.report_id).ref
    return client.get(f"/citizen/reports/{ref}").json()


@pytest.fixture(autouse=True)
def _token(monkeypatch):
    monkeypatch.setattr(settings, "pipeline_token", "test-token")


@pytest.fixture()
def w(db):
    admin = make_user(db, "admin")
    senior = make_user(db, "senior_official")
    north = make_user(db, "district_officer")
    other = make_user(db, "district_officer")  # another district's officer
    cover(db, north, "North")
    cover(db, other, "South")
    lake = make_asset(db, district="North", mandal="Mandal A", name="Test Cheruvu North", geometry=square(TG_LON, TG_LAT))
    return type("W", (), {"admin": admin, "senior": senior, "north": north, "other": other, "lake": lake})


def test_officials_acknowledge_and_add_notes_and_the_first_acknowledgement_starts_the_review(client, db, w):
    alert = report(client, db)
    assert alert.state == "OPEN"
    out = client.post(f"/alerts/{alert.id}/acknowledge", json={"note": "Seen. Checking the images."}, headers=auth(w.north))
    assert out.status_code == 201 and out.json()["state"] == "UNDER_REVIEW"
    assert client.post(f"/alerts/{alert.id}/acknowledge", json={}, headers=auth(w.north)).status_code == 409  # once each
    assert client.post(f"/alerts/{alert.id}/acknowledge", json={}, headers=auth(w.admin)).status_code == 403  # the admin takes no step
    assert client.post(f"/alerts/{alert.id}/acknowledge", json={}, headers=auth(w.senior)).status_code == 201
    assert public(client, db, alert)["events"][-1]["kind"] == "under_review"
    mine = db.scalar(select(Notification).where(Notification.alert_id == alert.id, Notification.user_id == w.north.id, Notification.kind == "incident_opened"))
    assert mine.acknowledged_at is not None
    assert client.post(f"/alerts/{alert.id}/notes", json={"text": "Lorry tracks on the bund in the photo."}, headers=auth(w.north)).status_code == 201
    assert client.post(f"/alerts/{alert.id}/notes", json={"text": "Asked the AE to look on Friday."}, headers=auth(w.senior)).status_code == 201
    assert client.post(f"/alerts/{alert.id}/notes", json={"text": "  "}, headers=auth(w.senior)).status_code == 422
    assert client.post(f"/alerts/{alert.id}/notes", json={"text": "x"}, headers=auth(w.admin)).status_code == 403
    assert client.get(f"/alerts/{alert.id}", headers=auth(w.other)).status_code == 403  # another district
    detail = client.get(f"/alerts/{alert.id}", headers=auth(w.admin)).json()
    assert [(n["kind"], n["author"]) for n in detail["notes"]] == [
        ("acknowledged", w.north.name), ("acknowledged", w.senior.name), ("note", w.north.name), ("note", w.senior.name)]
    assert detail["officer"]["acknowledged_by"] == [w.north.name, w.senior.name] and not detail["officer"]["acknowledged_by_me"]
    assert "Lorry tracks" not in json.dumps(public(client, db, alert))  # notes stay inside
    with pytest.raises(DBAPIError, match="append-only"):
        with db.begin_nested():
            db.execute(text("UPDATE incident_notes SET text = 'x' WHERE alert_id = :a"), {"a": alert.id})


def answer(client, review_id: int, result: str, as_of: str, after_date: str) -> dict:
    """The screener's answer to a review or a look (lp review-reports)."""
    body = {"status": "done", "result": result, "as_of": as_of, "after_date": after_date, "after_png_b64": PNG_B64,
            "scenes": [{"sensor": "sentinel-2-l2a", "scene_id": f"S2TEST_{review_id}", "acquired_at": f"{after_date}T05:20:00Z"}]}
    if result == "change_found":
        body.update(before_date=as_of, before_png_b64=PNG_B64,
                    change={"change_type": "soil_fill", "area_sq_m": 2400, "first_changed_at": after_date})
    out = client.post(f"/pipeline/reviews/{review_id}", json=body, headers=TOKEN)
    assert out.status_code == 200, out.text
    return out.json()


def test_satellite_looks_latest_and_by_date_compare_without_replacing_the_evidence(client, db, w):
    alert = report(client, db)
    first = db.scalar(select(SatelliteReview).where(SatelliteReview.alert_id == alert.id, SatelliteReview.kind == "automatic"))
    today, past = dt.date.today(), dt.date.today() - dt.timedelta(days=60)
    answer(client, first.id, "change_found", (today - dt.timedelta(days=30)).isoformat(), (today - dt.timedelta(days=2)).isoformat())
    cand = db.get(Candidate, alert.candidate_id)
    db.refresh(cand)
    evidence = (cand.before_chip, cand.after_chip)
    latest = client.post(f"/alerts/{alert.id}/satellite-looks", json={}, headers=auth(w.north)).json()
    earlier = client.post(f"/alerts/{alert.id}/satellite-looks", json={"date": past.isoformat()}, headers=auth(w.senior)).json()
    assert latest["status"] == earlier["status"] == "pending"  # the screener answers each look
    items = {r["id"]: r for r in client.get("/pipeline/reviews", headers=TOKEN).json()["reviews"]}
    assert (items[latest["id"]]["look_date"], items[earlier["id"]]["look_date"]) == (None, past.isoformat())
    answer(client, latest["id"], "change_found", today.isoformat(), (today - dt.timedelta(days=2)).isoformat())
    answer(client, earlier["id"], "no_change", past.isoformat(), (past - dt.timedelta(days=3)).isoformat())
    looks = client.get(f"/alerts/{alert.id}", headers=auth(w.north)).json()["looks"]
    assert [x["kind"] for x in looks] == ["automatic", "requested", "requested"] and looks[2]["look_date"] == past.isoformat()
    assert [x["result"] for x in looks] == ["change_found", "change_found", "no_change"]  # before the change: compare the two
    assert looks[2]["after_date"] == (past - dt.timedelta(days=3)).isoformat() and looks[1]["requested_by"] == w.north.name
    img = client.get(f"/alerts/{alert.id}/looks/{earlier['id']}/after", headers=auth(w.north))
    assert img.status_code == 200 and img.content.startswith(b"\x89PNG")
    db.refresh(cand)
    assert (cand.before_chip, cand.after_chip) == evidence  # the incident's own images stay as they were
    assert client.post(f"/alerts/{alert.id}/satellite-looks", json={"date": "2015-06-01"}, headers=auth(w.north)).status_code == 422
    future = (dt.date.today() + dt.timedelta(days=2)).isoformat()
    assert client.post(f"/alerts/{alert.id}/satellite-looks", json={"date": future}, headers=auth(w.north)).status_code == 422
    far_lake = make_asset(db, district="North", geometry=square(*offset(TG_LON, TG_LAT, east_m=5000)))
    _, satellite = ingest(db, far_lake, geometry=square(*offset(TG_LON, TG_LAT, east_m=5000), side_m=60))
    assert client.post(f"/alerts/{satellite.id}/satellite-looks", json={}, headers=auth(w.north)).status_code == 422


def test_a_real_look_waits_for_the_screener_and_comes_back_to_whoever_asked(client, db):
    official = make_user(db, "senior_official", is_demo=False)
    alert = report(client, db, lon=78.4740, lat=17.3850)
    asked = client.post(f"/alerts/{alert.id}/satellite-looks", json={"date": "2025-01-15"}, headers=auth(official)).json()
    assert asked["status"] == "pending"
    items = {r["id"]: r for r in client.get("/pipeline/reviews", headers=TOKEN).json()["reviews"]}
    assert items[asked["id"]]["kind"] == "requested" and items[asked["id"]]["look_date"] == "2025-01-15"
    body = {"status": "done", "result": "no_change", "as_of": "2025-01-15", "after_date": "2025-01-12", "after_png_b64": PNG_B64,
            "scenes": [{"sensor": "sentinel-2-l2a", "scene_id": "S2TEST_LOOK", "acquired_at": "2025-01-12T05:20:00Z"}]}
    assert client.post(f"/pipeline/reviews/{asked['id']}", json=body, headers=TOKEN).json()["result"] == "no_change"
    told = db.scalars(select(Notification).where(Notification.alert_id == alert.id, Notification.kind == "satellite_review")).all()
    assert [n.user_id for n in told] == [official.id]


def test_a_sharper_image_a_district_officer_asks_for_waits_for_the_senior_official(client, db, w):
    alert = report(client, db)
    req = client.post(f"/alerts/{alert.id}/imagery-request", json={"provider": "commercial_tasking", "note": "Need to see the posts"},
                      headers=auth(w.north)).json()
    assert req["status"] == "requested" and req["est_cost_usd"] > 0
    url = f"/alerts/{alert.id}/imagery-requests/{req['id']}/decision"
    assert client.post(url, json={"approve": True}, headers=auth(w.north)).status_code == 403
    assert client.post(url, json={"approve": True}, headers=auth(w.admin)).status_code == 403
    assert client.post(url, json={"approve": True, "note": "Within budget"}, headers=auth(w.senior)).json()["status"] == "approved"
    assert client.post(url, json={"approve": False}, headers=auth(w.senior)).status_code == 409
    own = client.post(f"/alerts/{alert.id}/imagery-request", json={"provider": "isro_nrsc"}, headers=auth(w.senior)).json()
    assert own["status"] == "approved"
    detail = client.get(f"/alerts/{alert.id}", headers=auth(w.north)).json()
    first = detail["imagery_requests"][0]
    assert (first["requested_by"], first["decided_by"], first["decision_note"], first["note"]) == (w.north.name, w.senior.name, "Within budget", "Need to see the posts")
    assert public(client, db, alert)["events"][-1]["kind"] == "sharper_images"
    far_lake = make_asset(db, district="North", geometry=square(*offset(TG_LON, TG_LAT, east_m=5000)))
    _, satellite = ingest(db, far_lake, geometry=square(*offset(TG_LON, TG_LAT, east_m=5000), side_m=60))
    assert client.post(f"/alerts/{satellite.id}/imagery-request", json={"provider": "isro_nrsc"}, headers=auth(w.north)).status_code == 201
    assert client.post(f"/alerts/{satellite.id}/imagery-request", json={"provider": "isro_nrsc"}, headers=auth(w.admin)).status_code == 403


def test_legal_records_and_documents_are_attached_to_the_incident(client, db, w):
    alert = report(client, db)
    db.add(CourtCase(court="Test High Court", case_no="WP 1/2026", status="pending", asset_id=w.lake.id, survey_numbers=[],
                     next_hearing=dt.date(2026, 12, 10), is_demo=False))
    db.flush()
    doc = client.post(f"/alerts/{alert.id}/documents", data={"doc_type": "government_order", "title": "Test stop-work notice",
                                                            "reference": "TEST/SWN/2026/7", "issued_on": "2026-11-20"},
                      headers=auth(w.north))
    assert doc.status_code == 201, doc.text
    assert doc.json()["alert_id"] == alert.id
    snap = client.post(f"/alerts/{alert.id}/legal-records", headers=auth(w.north)).json()["records"]
    assert snap["place"]["name"] == "Test Cheruvu North" and snap["boundary"]["status"]
    assert [d["reference"] for d in snap["documents"]] == ["TEST/SWN/2026/7"]
    assert [(k["case_no"], k["status"]) for k in snap["court_cases"]] == [("WP 1/2026", "pending")]
    assert snap["legal_check"]["verdict"] and any("22A" in x for x in snap["not_connected"])
    assert client.post(f"/alerts/{alert.id}/legal-records", headers=auth(w.admin)).status_code == 403
    client.post(f"/alerts/{alert.id}/legal-records", headers=auth(w.senior))
    detail = client.get(f"/alerts/{alert.id}", headers=auth(w.north)).json()
    assert detail["legal_records"]["snapshots"] == 2 and detail["legal_records"]["by"] == w.senior.name
    assert [d["title"] for d in detail["documents_attached"]] == ["Test stop-work notice"]
    # The document is the location's too.
    assert any(d["reference"] == "TEST/SWN/2026/7" for d in client.get(f"/assets/{w.lake.id}/documents", headers=auth(w.admin)).json()["items"])
    with pytest.raises(DBAPIError, match="append-only"):
        with db.begin_nested():
            db.execute(text("DELETE FROM incident_legal_records WHERE alert_id = :a"), {"a": alert.id})


def test_the_district_officer_recommends_and_the_senior_official_approves_then_closes(client, db, w):
    approved = report(client, db)
    rec = client.post(f"/alerts/{approved.id}/recommendation", json={"recommendation": "confirm", "note": "Fill confirmed on the look of today"},
                      headers=auth(w.north))
    assert rec.status_code == 201 and rec.json()["state"] == "RECOMMENDED"
    asked = db.scalars(select(Notification.user_id).where(Notification.alert_id == approved.id, Notification.kind == "recommended")).all()
    assert asked == [w.senior.id]
    ok = client.post(f"/alerts/{approved.id}/transitions", json={"to": "CONFIRMED", "note": "Approved"}, headers=auth(w.senior))
    assert ok.status_code == 200 and ok.json()["state"] == "CONFIRMED"
    told = db.scalars(select(Notification.user_id).where(Notification.alert_id == approved.id, Notification.kind == "incident_decided")).all()
    assert w.north.id in told
    assert public(client, db, approved)["closed_reason"] == "incident_confirmed"
    assert client.post(f"/alerts/{approved.id}/transitions", json={"to": "CLOSED", "note": ""}, headers=auth(w.senior)).status_code == 422
    assert client.post(f"/alerts/{approved.id}/transitions", json={"to": "CLOSED", "note": "Sent to Irrigation"}, headers=auth(w.north)).status_code == 403
    assert client.post(f"/alerts/{approved.id}/transitions", json={"to": "CLOSED", "note": "Sent to Irrigation"}, headers=auth(w.senior)).json()["state"] == "CLOSED"

    # A dismissal passed to a department is set in the recommendation and applied on approval.
    again = report(client, db)
    assert again.id != approved.id
    client.post(f"/alerts/{again.id}/recommendation", json={"recommendation": "dismiss", "note": "Patta land", "citizen_department": "revenue",
                                                          "citizen_false_report": True}, headers=auth(w.north))
    out = client.post(f"/alerts/{again.id}/transitions", json={"to": "DISMISSED", "note": "Agreed"}, headers=auth(w.senior))
    assert out.json()["state"] == "DISMISSED"
    view = public(client, db, again)
    assert view["closed_reason"] == "passed_on" and "Revenue" in view["events"][-1]["note"]["en"]
    assert db.get(CitizenReport, again.report_id).false_report is True

    # Where no district officer covers the place, the senior official decides in one step.
    lon, lat = offset(TG_LON, TG_LAT, east_m=3000)
    elsewhere = report(client, db, lon=lon, lat=lat)
    out = client.post(f"/alerts/{elsewhere.id}/transitions", json={"to": "DISMISSED", "note": "Not a change", "citizen_department": "irrigation"},
                      headers=auth(w.senior))
    assert out.json()["state"] == "DISMISSED"
    assert client.post(f"/alerts/{elsewhere.id}/transitions", json={"to": "CLOSED", "note": "x"}, headers=auth(w.admin)).status_code == 403


def test_the_place_goes_on_the_weekly_watch(client, db):
    official = make_user(db, "senior_official", is_demo=False)
    alert = report(client, db, lon=78.4740, lat=17.3850)
    place = db.get(Asset, db.get(Candidate, alert.candidate_id).asset_id)
    assert place.monitored is False
    assert client.post(f"/alerts/{alert.id}/watch", json={"reason": " "}, headers=auth(official)).status_code == 422
    out = client.post(f"/alerts/{alert.id}/watch", json={"reason": "Government land next to the lake; watch it weekly",
                                                         "name": "Government land by Test Lake"}, headers=auth(official)).json()
    assert out == {"asset_id": place.id, "name": "Government land by Test Lake", "monitored": True}
    assert place.id in {a["id"] for a in client.get("/pipeline/watchlist", headers=TOKEN).json()["assets"]}
    assert client.post(f"/alerts/{alert.id}/watch", json={"reason": "again"}, headers=auth(official)).status_code == 409
    assert public(client, db, alert)["events"][-1]["kind"] == "added_to_watch"
    hist = client.get(f"/assets/{place.id}/monitoring", headers=auth(official)).json()["items"]
    assert hist[0]["monitored"] is True and hist[0]["actor"] == official.name
