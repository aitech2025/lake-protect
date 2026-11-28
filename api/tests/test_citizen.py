"""Citizen reports: every report opens an incident with a satellite review, worked in the regular flow
(CONTEXT.md 17.8; DECISIONS.md D-062, D-063, D-065).

GeoGuard takes reports in Telangana only. These tests use fictional reports and fixtures at a
Telangana test point (factories.TG_LON, TG_LAT) or at a real Hyderabad point, in the test database only.
The satellite review always waits for the screener; the tests post its answers.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import io
import json
import re

import pytest
from PIL import Image
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.citizen import sender, service, whatsapp
from app.clock import utcnow
from app.config import settings
from app.models import Alert, Asset, Candidate, CandidateAsset, CitizenMessage, CitizenReport, ImageryRequest, Notification, SatelliteReview, Signal
from app.notify import service as notify
from app.notify.channels import Result
from tests.factories import PNG_B64, TEST_LAT, TEST_LON, TG_LAT, TG_LON, auth, cover, decide, ingest, make_asset, make_user, offset, square

REF = r"^GGR-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$"
TOKEN = {"X-Pipeline-Token": "test-token"}
HYDERABAD = (78.4740, 17.3850)  # a fictional report at a real point, in the test database only


def jpeg_with_gps() -> bytes:
    img = Image.new("RGB", (64, 48), (90, 120, 60))
    exif = Image.Exif()
    exif[0x010F] = "TestCam"
    exif[0x8825] = {1: "N", 2: (17.0, 24.0, 0.0)}
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def post_report(client, *, lon=TG_LON, lat=TG_LAT, what="dumping", language="en", photos=(), token=None, **extra):
    data = {"language": language, "what": what, "lon": lon, "lat": lat, **extra}
    if token:
        data["phone_token"] = token
    files = [("photos", (f"p{i}.jpg", p, "image/jpeg")) for i, p in enumerate(photos)]
    return client.post("/citizen/reports", data={"data": json.dumps(data)}, files=files or None)


def report_of(db, ref: str) -> CitizenReport:
    return db.scalar(select(CitizenReport).where(CitizenReport.ref == ref))


def review_of(db, alert_id: int) -> SatelliteReview:
    return db.scalar(select(SatelliteReview).where(SatelliteReview.alert_id == alert_id, SatelliteReview.kind == "automatic"))


def change_found(today: dt.date, area: float = 1800) -> dict:
    return {
        "status": "done", "result": "change_found", "as_of": today.isoformat(), "before_date": (today - dt.timedelta(days=40)).isoformat(),
        "after_date": (today - dt.timedelta(days=3)).isoformat(),
        "scenes": [{"sensor": "sentinel-2-l2a", "scene_id": f"S2TEST_REVIEW_{area:.0f}", "acquired_at": f"{today - dt.timedelta(days=3)}T05:20:00Z",
                    "cloud_pct": 2.5, "licence_notice": "Contains modified Copernicus Sentinel data 2026"}],
        "before_png_b64": PNG_B64, "after_png_b64": PNG_B64,
        "change": {"change_type": "building", "area_sq_m": area, "first_changed_at": (today - dt.timedelta(days=20)).isoformat()},
    }


@pytest.fixture(autouse=True)
def _token(monkeypatch):
    monkeypatch.setattr(settings, "pipeline_token", "test-token")


@pytest.fixture()
def w(db):
    admin = make_user(db, "admin")
    senior = make_user(db, "senior_official")
    north = make_user(db, "district_officer")
    cover(db, north, "North")
    lake = make_asset(db, district="North", mandal="Mandal A", name="Test Cheruvu North", geometry=square(TG_LON, TG_LAT))
    return type("W", (), {"admin": admin, "senior": senior, "north": north, "lake": lake})


def test_a_report_opens_a_citizen_incident_waiting_for_its_satellite_review_and_officials_are_told(client, db, w):
    resp = post_report(client, language="te", description="Lorries at night", photos=[jpeg_with_gps()])
    assert resp.status_code == 201, resp.text
    view = resp.json()
    assert re.match(REF, view["ref"]) and view["status"] == "CHECKING"
    assert [e["kind"] for e in view["events"]] == ["received", "case_opened"]
    assert set(view["events"][0]["note"]) == {"en", "te"}  # no Urdu
    report = report_of(db, view["ref"])
    assert report.is_demo is False
    alert = db.get(Alert, report.alert_id)
    assert (alert.origin, alert.report_id, alert.state, report.placed_by) == ("citizen", report.id, "OPEN", "pin")
    cand = db.get(Candidate, alert.candidate_id)
    assert (cand.asset_id, cand.sensor_basis, cand.change_type) == (w.lake.id, "citizen_report", "soil_fill")
    assert 2500 < float(cand.area_sq_m) < 3000  # the reported spot: a 30 m circle
    rv = review_of(db, alert.id)
    assert (rv.status, rv.source) == ("pending", "sentinel-2")  # the screener answers it; there is no demo sensor
    # The area's official and the admin are told.
    notes = db.scalars(select(Notification).where(Notification.alert_id == alert.id, Notification.kind == "incident_opened")).all()
    assert {n.user_id for n in notes} == {w.north.id, w.senior.id} and all(n.needs_ack for n in notes)  # the admin only where no one covers it
    body = next(n.body for n in notes if n.user_id == w.north.id)
    assert "Reported by a citizen (web portal), reference " + view["ref"] in body and "reported by a citizen on" in body
    # The incident page carries the report and the pending review; never the reporter.
    detail = client.get(f"/alerts/{alert.id}", headers=auth(w.north)).json()
    assert detail["origin"] == "citizen" and detail["citizen"]["ref"] == view["ref"] and detail["citizen"]["description"] == "Lorries at night"
    assert detail["satellite_review"]["status"] == "pending" and "satellite review pending" in detail["summary"]
    assert "reporter_phone" not in json.dumps(detail)
    # The photo kept has no metadata left.
    from app.storage import store

    kept = Image.open(io.BytesIO(store.get_object(report.photos[0]["key"])))
    assert len(kept.getexif()) == 0
    assert db.scalar(select(Signal).where(Signal.ref == view["ref"])).linked_alert_id == alert.id


def test_outside_every_location_the_report_makes_a_reported_place_and_the_screeners_change_is_the_incidents(client, db, w):
    lon, lat = offset(TG_LON, TG_LAT, east_m=3000)
    view = post_report(client, lon=lon, lat=lat, what="dumping").json()
    report = report_of(db, view["ref"])
    alert = db.get(Alert, report.alert_id)
    place = db.get(Asset, db.get(Candidate, alert.candidate_id).asset_id)
    assert (place.type, place.monitored, place.cohort) == ("reported_place", False, "D_UNNOTIFIED")
    assert place.name == f"Reported place {view['ref']}"
    candidate_asset = db.get(CandidateAsset, report.candidate_asset_id)
    assert candidate_asset is not None
    assert candidate_asset.candidate_code == f"GGC-{view['ref']}"
    assert candidate_asset.status == "PENDING_VERIFICATION"
    assert candidate_asset.support_asset_id == place.id
    assert candidate_asset.detection_candidate_id == alert.candidate_id
    assert candidate_asset.incident_id == alert.id
    assert candidate_asset.provenance["verification"] == "unverified"
    # Internal support geometry must not leak into either registered-asset catalogue.
    assert place.id not in {f["id"] for f in client.get("/assets", headers=auth(w.admin)).json()["features"]}
    registry = client.get("/api/v1/platform/assets", headers=auth(w.admin)).json()["items"]
    assert all(row["category_code"] != "reported_place" for row in registry)
    refused = client.post("/api/v1/platform/assets", json={"asset_code": "TEST-REPORTED-PLACE", "display_name": "Reported place", "category_code": "reported_place"}, headers=auth(w.admin))
    assert refused.status_code == 422
    candidate_rows = client.get("/api/v1/platform/candidate-assets", headers=auth(w.admin)).json()["items"]
    assert any(row["id"] == str(candidate_asset.id) and row["source_report_ref"] == view["ref"] for row in candidate_rows)
    # A reported place is not on the weekly watch.
    assert place.id not in {a["id"] for a in client.get("/pipeline/watchlist", headers=TOKEN).json()["assets"]}
    rid = review_of(db, alert.id).id
    assert client.post(f"/pipeline/reviews/{rid}", json=change_found(dt.date.today()), headers=TOKEN).status_code == 200
    assert client.get(f"/citizen/reports/{view['ref']}").json()["events"][-1]["kind"] == "satellite_change_found"
    row = client.get(f"/alerts/{alert.id}", headers=auth(w.admin)).json()
    assert "the satellite shows a change of about" in row["summary"] and row["summary_te"]
    assert "satellite_change_seen" in row["candidate"]["flags"] and row["candidate"]["has_image_pair"]


def test_a_report_in_hyderabad_waits_for_the_screener_whose_result_is_passed_on(client, db):
    admin = make_user(db, "admin", is_demo=False)
    view = post_report(client, lon=HYDERABAD[0], lat=HYDERABAD[1], what="construction").json()
    assert [e["kind"] for e in view["events"]] == ["received", "case_opened"]
    report = report_of(db, view["ref"])
    alert = db.get(Alert, report.alert_id)
    place = db.get(Asset, db.get(Candidate, alert.candidate_id).asset_id)
    assert place.district == "Hyderabad" and "OpenStreetMap" in place.notes  # the pin's district, not the revenue record
    assert "satellite review pending" in client.get(f"/alerts/{alert.id}", headers=auth(admin)).json()["summary"]

    pending = client.get("/pipeline/reviews", headers=TOKEN).json()["reviews"]
    mine = next(p for p in pending if p["alert_id"] == alert.id)
    assert (mine["ref"], round(mine["lon"], 4)) == (view["ref"], HYDERABAD[0]) and "parcel" in mine["asset"]["boundaries"]
    bad = client.post(f"/pipeline/reviews/{mine['id']}", json={"status": "done", "result": "change_found"}, headers=TOKEN)
    assert bad.status_code == 422  # a change found needs the change
    body = change_found(dt.date.today())
    done = client.post(f"/pipeline/reviews/{mine['id']}", json=body, headers=TOKEN)
    assert done.status_code == 200 and done.json()["result"] == "change_found"
    assert client.post(f"/pipeline/reviews/{mine['id']}", json=body, headers=TOKEN).status_code == 409
    assert client.get(f"/citizen/reports/{view['ref']}").json()["events"][-1]["kind"] == "satellite_change_found"
    told = db.scalars(select(Notification).where(Notification.alert_id == alert.id, Notification.kind == "satellite_review")).all()
    assert [n.user_id for n in told] == [admin.id] and "a change is visible" in told[0].subject
    cand = db.get(Candidate, alert.candidate_id)
    assert cand.after_chip and len(cand.observation_ids) == 1


def test_a_review_the_screener_cannot_finish_fails_after_three_tries(client, db):
    view = post_report(client, lon=HYDERABAD[0], lat=HYDERABAD[1]).json()
    rid = db.scalar(select(SatelliteReview.id).join(Alert, Alert.id == SatelliteReview.alert_id).join(CitizenReport, CitizenReport.id == Alert.report_id)
                    .where(CitizenReport.ref == view["ref"]))
    for _ in range(3):
        out = client.post(f"/pipeline/reviews/{rid}", json={"status": "failed", "detail": "STAC search timed out"}, headers=TOKEN).json()
    assert out == {"id": rid, "status": "failed", "attempts": 3}
    assert rid not in {p["id"] for p in client.get("/pipeline/reviews", headers=TOKEN).json()["reviews"]}


def test_the_regular_flow_is_passed_on_to_the_citizen(client, db, w):
    view = post_report(client).json()
    report = report_of(db, view["ref"])
    aid = report.alert_id
    assert client.post(f"/alerts/{aid}/reviews", json={"outcome": "needs_site_visit", "note": "Too small for 10 m pixels"}, headers=auth(w.north)).status_code == 201
    assert client.post(f"/alerts/{aid}/imagery-request", json={"provider": "commercial_archive"}, headers=auth(w.north)).status_code == 201
    assert db.scalar(select(ImageryRequest).where(ImageryRequest.alert_id == aid)) is not None
    kinds = [e["kind"] for e in client.get(f"/citizen/reports/{view['ref']}").json()["events"]]
    assert kinds[-2:] == ["under_review", "sharper_images"]
    # A department goes only with a dismissal. The district officer recommends; the senior official approves (D-067).
    rec = lambda body: client.post(f"/alerts/{aid}/recommendation", json=body, headers=auth(w.north))  # noqa: E731
    assert rec({"recommendation": "confirm", "note": "x", "citizen_department": "revenue"}).status_code == 422
    assert rec({"recommendation": "dismiss", "note": "x", "citizen_department": "nobody"}).status_code == 422
    assert rec({"recommendation": "dismiss", "note": "Patta land; sent to the Tahsildar", "citizen_department": "revenue"}).status_code == 201
    out = client.post(f"/alerts/{aid}/transitions", json={"to": "DISMISSED", "note": "Agreed"}, headers=auth(w.senior))
    assert out.status_code == 200, out.text
    public = client.get(f"/citizen/reports/{view['ref']}").json()
    assert (public["status"], public["closed_reason"]) == ("CLOSED", "passed_on")
    assert "Revenue Department" in public["events"][-1]["note"]["en"] and "రెవెన్యూ శాఖ" in public["events"][-1]["note"]["te"]
    assert "Patta land" not in json.dumps(public)  # the officers' notes stay inside
    assert client.post(f"/alerts/{aid}/transitions", json={"to": "CLOSED", "note": "Closed with the dismissal"}, headers=auth(w.senior)).status_code == 200


def test_a_report_by_an_open_incident_joins_it_and_a_second_report_follows_the_first(client, db, w):
    _, alert = ingest(db, w.lake, geometry=square(TG_LON, TG_LAT, side_m=60))
    first = post_report(client).json()
    assert [e["kind"] for e in first["events"]] == ["received", "linked_incident"]
    lon, lat = offset(TG_LON, TG_LAT, east_m=40)
    second = post_report(client, lon=lon, lat=lat, what="construction").json()
    assert [e["kind"] for e in second["events"]] == ["received", "duplicate"]
    r1, r2 = report_of(db, first["ref"]), report_of(db, second["ref"])
    assert r1.alert_id == r2.alert_id == alert.id and r2.duplicate_of == r1.id
    assert db.scalar(select(Alert).where(Alert.origin == "citizen")) is None  # no second incident
    assert all(not n.needs_ack for n in db.scalars(select(Notification).where(Notification.report_id == r1.id)))
    decide(db, alert, w.senior, to="CONFIRMED", at=utcnow())
    for ref in (first["ref"], second["ref"]):
        assert client.get(f"/citizen/reports/{ref}").json()["closed_reason"] == "incident_confirmed"


def test_words_that_name_a_location_place_the_report_and_others_wait_for_an_official(client, db, w):
    form = {"channel": "helpline_1070", "language": "te", "what": "construction",
            "location_text": "near the bund of Test Cheruvu North, by the temple"}
    out = client.post("/reports/intake", data={"data": json.dumps(form)}, headers=auth(w.north)).json()
    report = db.get(CitizenReport, out["id"])
    assert report.placed_by == "description" and report.alert_id and db.get(Candidate, db.get(Alert, report.alert_id).candidate_id).asset_id == w.lake.id
    assert "placed_from_description" in db.get(Candidate, db.get(Alert, report.alert_id).candidate_id).flags
    vague = client.post("/reports/intake", data={"data": json.dumps({**form, "location_text": "somewhere near the highway"})}, headers=auth(w.north)).json()
    r2 = db.get(CitizenReport, vague["id"])
    assert r2.alert_id is None and [e["kind"] for e in vague["events"]][-1] == "no_place"
    asks = {n.user_id: n for n in db.scalars(select(Notification).where(Notification.report_id == r2.id))}
    assert set(asks) == {w.senior.id, w.admin.id} and asks[w.senior.id].needs_ack  # no place yet: State-level
    assert client.post(f"/reports/{r2.id}/place", json={"lon": TG_LON, "lat": TG_LAT}, headers=auth(w.admin)).status_code == 403  # the admin takes no step
    assert client.post(f"/reports/{r2.id}/place", json={"lon": TEST_LON, "lat": TEST_LAT}, headers=auth(w.senior)).status_code == 422  # not Telangana
    lon, lat = offset(TG_LON, TG_LAT, east_m=2500)
    placed = client.post(f"/reports/{r2.id}/place", json={"lon": lon, "lat": lat}, headers=auth(w.senior)).json()
    assert placed["alert_id"] and placed["status"] == "CHECKING"
    db.refresh(asks[w.senior.id])
    assert asks[w.senior.id].acknowledged_at is not None
    assert client.post(f"/reports/{r2.id}/place", json={"lon": lon, "lat": lat}, headers=auth(w.senior)).status_code == 422


def test_reports_are_refused_outside_the_state_without_a_place_or_in_urdu(client, db, w):
    assert post_report(client, lon=72.8, lat=19.0).status_code == 422
    sea = post_report(client, lon=TEST_LON, lat=TEST_LAT)  # where the demo world was: no longer taken
    assert sea.status_code == 422 and "must be in Telangana" in sea.text
    assert post_report(client, what="theft").status_code == 422
    assert post_report(client, language="ur").status_code == 422
    assert client.post("/citizen/reports", data={"data": json.dumps({"what": "dumping"})}).status_code == 422
    assert client.post("/citizen/reports", data={"data": json.dumps({"dataset": "demo", "what": "dumping", "lon": TG_LON, "lat": TG_LAT})}).status_code == 422
    assert "At most 3" in post_report(client, photos=[jpeg_with_gps()] * 4).text


def test_updates_go_only_to_a_verified_phone(client, db, w, monkeypatch):
    held = client.post("/citizen/otp", json={"phone": "9876543210"})
    assert held.status_code == 409 and "not available yet" in held.text  # no SMS gateway yet
    assert client.post("/citizen/otp", json={"phone": "0000000001"}).status_code == 422  # not a mobile number
    sent: dict = {}

    def fake_sms(phone, template, values, is_demo):
        sent.update(values)
        return Result("sent", "test gateway", phone)

    with monkeypatch.context() as m:  # a stand-in gateway, for this request only
        m.setattr(sender, "sms_ready", lambda: True)
        m.setattr(sender, "send_sms", fake_sms)
        start = client.post("/citizen/otp", json={"phone": "9876543210"}).json()
    assert start["sent"] and sent["code"] not in json.dumps(start)  # the code goes only by SMS
    token = client.post("/citizen/otp/verify", json={"phone": "9876543210", "code": sent["code"]}).json()["token"]
    view = post_report(client, token=token, name="Test Citizen").json()
    report = report_of(db, view["ref"])
    assert (report.phone_verified_via, report.wants_updates) == ("otp", True)
    queued = db.scalars(select(CitizenMessage).where(CitizenMessage.report_id == report.id)).all()
    assert len(queued) == 1 and queued[0].text.startswith(f"GeoGuard {report.ref}: Being checked.")  # one update for the first steps
    assert notify.tick(db, utcnow())["citizen_messages"] == {"held": 1}
    aid = report.alert_id
    client.post(f"/alerts/{aid}/recommendation", json={"recommendation": "dismiss", "note": "Nothing there", "citizen_false_report": True},
                headers=auth(w.north))
    client.post(f"/alerts/{aid}/transitions", json={"to": "DISMISSED", "note": "Agreed"}, headers=auth(w.senior))
    db.refresh(report)
    assert report.false_report is True and report.status == "CLOSED"
    assert service.purge_contacts(db, utcnow() + dt.timedelta(days=91)) == 1
    db.refresh(report)
    assert report.reporter_phone is None and report.contact_purged_at is not None


def test_rate_limits(client, db, w):
    for i in range(service.PER_HOUR):
        assert post_report(client, lon=offset(TG_LON, TG_LAT, east_m=300 * i)[0]).status_code == 201
    assert post_report(client).status_code == 429


def test_the_whatsapp_conversation_makes_a_report_and_its_incident(client, db, w):
    number = "919000000002"  # a test number: the test gateway holds every reply

    def say(**msg):
        return whatsapp.handle(db, number, msg, at=utcnow())

    welcome = say(type="text", text="hi")[0]
    assert "1 English" in welcome and "2 తెలుగు" in welcome and "اردو" not in welcome
    assert "📎" in say(type="text", text="2")[0]
    assert say(type="location", latitude=TEST_LAT, longitude=TEST_LON)  # outside Telangana: asked again
    say(type="location", latitude=TG_LAT, longitude=TG_LON)
    say(type="text", text="2")
    png = io.BytesIO()
    Image.new("RGB", (20, 20), (1, 2, 3)).save(png, format="PNG")
    assert say(type="image", data=png.getvalue())[0] == "ఫోటో అందింది."
    say(type="text", text="A wall on the bund")
    done = say(type="text", text="YES")[0]
    ref = service.REF_RE.search(done).group(0)
    report = report_of(db, ref)
    assert (report.channel, report.language, report.phone_verified_via, report.is_demo) == ("whatsapp", "te", "whatsapp", False)
    assert db.get(Alert, report.alert_id).origin == "citizen"
    assert client.get("/reports/whatsapp-simulator", headers=auth(w.north)).status_code in (404, 422)  # the demo simulator is gone


def test_the_whatsapp_webhook_needs_the_states_agreement_and_a_signature(client, db, w, monkeypatch):
    payload = {"entry": [{"changes": [{"value": {"messages": [{"from": "919000000001", "type": "text", "text": {"body": "hi"}}]}}]}]}
    raw = json.dumps(payload).encode()
    assert client.post("/citizen/whatsapp/webhook", content=raw).status_code == 503
    monkeypatch.setenv("LP_WHATSAPP_APP_SECRET", "test-secret")
    assert client.post("/citizen/whatsapp/webhook", content=raw, headers={"x-hub-signature-256": "sha256=bad"}).status_code == 403
    sig = "sha256=" + hmac.new(b"test-secret", raw, hashlib.sha256).hexdigest()
    assert client.post("/citizen/whatsapp/webhook", content=raw, headers={"x-hub-signature-256": sig}).json() == {"handled": 1}
    assert whatsapp.close_idle(db, utcnow() + dt.timedelta(hours=25)) == 1


def test_the_weekly_screen_tells_the_citizen_when_it_looks_again(client, db, w):
    from app.models import AssetScreen, ScreenRun

    view = post_report(client).json()
    today = utcnow().date()
    run = ScreenRun(as_of=today, rule_version="t", rules_sha256="a" * 64, collection="test", started_at=utcnow(), finished_at=utcnow(),
                    assets_total=1, outcomes={}, is_demo=False)
    db.add(run)
    db.flush()
    db.add(AssetScreen(run_id=run.id, asset_id=w.lake.id, status="no_candidate", looks=1, candidates=0, legacy_changes=0, counts={},
                       week="2026-W48", changes=[], last_look=today))
    db.flush()
    assert service.on_screen_stored(db, run.id, utcnow()) == 1
    assert service.on_screen_stored(db, run.id, utcnow() + dt.timedelta(days=8)) == 0  # that look is already passed on
    assert client.get(f"/citizen/reports/{view['ref']}").json()["events"][-1]["kind"] == "satellite_checked"


def test_the_history_cannot_be_changed_and_the_planned_kind_cannot_be_added_by_hand(db, client, w):
    view = post_report(client).json()
    rid = report_of(db, view["ref"]).id
    with pytest.raises(DBAPIError, match="append-only"):
        with db.begin_nested():
            db.execute(text("DELETE FROM citizen_report_events WHERE report_id = :r"), {"r": rid})
    admin = make_user(db, "admin", is_demo=False)
    out = client.post("/assets", json={"type": "reported_place", "name": "x", "district": "x", "geometry": square(79.4, 18.6, side_m=200),
                                       "drawn": True, "status": "derived", "source_name": "x"}, headers=auth(admin))
    assert out.status_code == 422 and "made from citizens' reports" in out.text
    config = client.get("/citizen/config").json()
    assert config["languages"] == ["en", "te"] and "dataset" not in config
