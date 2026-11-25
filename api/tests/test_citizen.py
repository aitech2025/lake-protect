"""Citizen reports: portal, WhatsApp and staff intake, and updates back (CONTEXT.md 17.8; DECISIONS.md D-062).

Everything here is fictional and in the open-sea demo world, except the webhook test, which uses
a fictional pin inside Telangana.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import io
import json

import pytest
from PIL import Image
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.citizen import service, whatsapp
from app.clock import utcnow
from app.models import AssetScreen, AuditLog, CitizenMessage, CitizenReport, Notification, ScreenRun, Signal
from app.notify import service as notify
from tests.factories import TEST_LAT, TEST_LON, auth, cover, decide, ingest, make_asset, make_user, offset

REF = r"^GGR-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$"


def jpeg_with_gps() -> bytes:
    img = Image.new("RGB", (64, 48), (90, 120, 60))
    exif = Image.Exif()
    exif[0x010F] = "TestCam"  # Make
    exif[0x8825] = {1: "N", 2: (17.0, 24.0, 0.0)}  # GPS
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def post_report(client, *, lon=TEST_LON, lat=TEST_LAT, what="dumping", language="en", photos=(), token=None, dataset="demo", **extra):
    data = {"dataset": dataset, "language": language, "what": what, "lon": lon, "lat": lat, **extra}
    if token:
        data["phone_token"] = token
    files = [("photos", (f"p{i}.jpg", p, "image/jpeg")) for i, p in enumerate(photos)]
    return client.post("/citizen/reports", data={"data": json.dumps(data)}, files=files or None)


@pytest.fixture()
def w(db):
    admin = make_user(db, "admin")
    north = make_user(db, "viewer")
    cover(db, north, "North")
    lake = make_asset(db, district="North", mandal="Mandal A", name="Test Cheruvu North")
    return type("W", (), {"admin": admin, "north": north, "lake": lake})


def test_a_portal_report_is_placed_routed_and_tracked_by_reference(client, db, w):
    resp = post_report(client, language="te", description="Lorries at night", photos=[jpeg_with_gps()])
    assert resp.status_code == 201, resp.text
    view = resp.json()
    assert view["status"] == "CHECKING" and view["place"]["en"] == "Test Cheruvu North"
    assert [e["kind"] for e in view["events"]] == ["received", "routed_area"]
    assert view["events"][0]["note"]["te"].endswith(f"{view['ref']}.") and view["events"][0]["note"]["ur"]
    import re

    assert re.match(REF, view["ref"])
    # The public view carries no photo, contact, officer or internal note.
    public = client.get(f"/citizen/reports/{view['ref'].lower()}").json()
    assert not {"photos", "reporter_phone", "internal_note", "actor", "asset_id"} & set(public) and "internal_note" not in public["events"][0]
    report = db.scalar(select(CitizenReport).where(CitizenReport.ref == view["ref"]))
    assert (report.asset_id, report.zone, report.channel, report.wants_updates) == (w.lake.id, "inside", "web", False)
    # The official of the area and the admin are told, and must acknowledge.
    notes = db.scalars(select(Notification).where(Notification.report_id == report.id)).all()
    assert {n.user_id for n in notes} == {w.north.id, w.admin.id} and all(n.needs_ack for n in notes)
    assert "Lorries at night" in next(n.body for n in notes if n.user_id == w.north.id)
    assert db.scalar(select(Signal).where(Signal.ref == view["ref"])).asset_id == w.lake.id
    # The photo kept has no metadata left.
    from app.storage import store

    kept = Image.open(io.BytesIO(store.get_object(report.photos[0]["key"])))
    assert len(kept.getexif()) == 0 and kept.size == (64, 48)
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "citizen.report_received")).all()[-1]
    assert "Lorries" not in json.dumps(entry.details)  # the audit log holds no free text from citizens


def test_reports_are_refused_outside_the_state_or_without_a_place(client, db, w):
    assert post_report(client, lon=72.8, lat=19.0).status_code == 422  # Mumbai
    assert "demo world" in post_report(client, lon=78.47, lat=17.41).text  # real place, demo form
    assert post_report(client, what="theft").status_code == 422
    resp = client.post("/citizen/reports", data={"data": json.dumps({"dataset": "demo", "what": "dumping"})})
    assert resp.status_code == 422 and "map" in resp.text
    too_many = post_report(client, photos=[jpeg_with_gps()] * 4)
    assert too_many.status_code == 422 and "At most 3" in too_many.text
    assert client.post("/citizen/reports", data={"data": "{"}).status_code == 422


def test_a_report_next_to_an_incident_follows_it_and_closes_with_its_decision(client, db, w):
    _, alert = ingest(db, w.lake)
    first = post_report(client).json()
    assert [e["kind"] for e in first["events"]] == ["received", "linked_incident"]
    lon, lat = offset(TEST_LON, TEST_LAT, east_m=40)
    second = post_report(client, lon=lon, lat=lat, what="construction").json()
    assert [e["kind"] for e in second["events"]] == ["received", "duplicate"]
    r1, r2 = (db.scalar(select(CitizenReport).where(CitizenReport.ref == x["ref"])) for x in (first, second))
    assert r2.duplicate_of == r1.id and r1.alert_id == alert.id
    # On an incident: officials are told, without needing to acknowledge; the duplicate tells no one.
    assert all(not n.needs_ack for n in db.scalars(select(Notification).where(Notification.report_id == r1.id)))
    assert db.scalar(select(Notification).where(Notification.report_id == r2.id)) is None

    decide(db, alert, w.admin, to="CONFIRMED")
    for ref in (first["ref"], second["ref"]):
        view = client.get(f"/citizen/reports/{ref}").json()
        assert (view["status"], view["closed_reason"]) == ("CLOSED", "incident_confirmed")
        assert view["events"][-1]["note"]["en"].startswith("Closed: officials confirmed a change")


def test_an_incident_found_later_picks_up_the_open_reports(client, db, w):
    view = post_report(client).json()
    _, alert = ingest(db, w.lake, at=utcnow())
    report = db.scalar(select(CitizenReport).where(CitizenReport.ref == view["ref"]))
    assert report.alert_id == alert.id
    assert client.get(f"/citizen/reports/{view['ref']}").json()["events"][-1]["kind"] == "change_found"
    decide(db, alert, w.admin, to="DISMISSED", at=utcnow() + dt.timedelta(minutes=10))
    assert client.get(f"/citizen/reports/{view['ref']}").json()["closed_reason"] == "incident_dismissed"


def test_officials_check_the_admin_closes_and_unanswered_reports_are_followed_up(client, db, w):
    other = make_user(db, "viewer")
    cover(db, other, "North")
    report_id = db.scalar(select(CitizenReport.id).where(CitizenReport.ref == post_report(client).json()["ref"]))
    url = f"/reports/{report_id}"
    out = client.post(f"{url}/check", json={"outcome": "not_visible", "note": "Looked at the 22 Nov image"}, headers=auth(w.north)).json()
    assert out["events"][-1]["kind"] == "check_not_visible" and out["events"][-1]["internal_note"] == "Looked at the 22 Nov image"
    assert out["events"][-1]["actor"] == w.north.name
    north_note = db.scalar(select(Notification).where(Notification.report_id == report_id, Notification.user_id == w.north.id))
    assert north_note.ack_via == "report_check"
    # The other official has not acknowledged: reminded after 24 hours, the admin told after 48.
    later = utcnow() + dt.timedelta(hours=49)
    assert notify.follow_up(db, later) == {"reminders": 2, "not_acknowledged": 1}  # the admin's own note is reminded too
    reminder = db.scalar(select(Notification).where(Notification.user_id == other.id, Notification.kind == "reminder"))
    assert reminder.report_id == report_id and reminder.subject.startswith("Reminder: citizen report")
    assert notify.unacknowledged_count(db, other) == 2

    assert client.post(f"{url}/close", json={"reason": "no_change_seen", "note": "x"}, headers=auth(w.north)).status_code == 403
    bad = client.post(f"{url}/close", json={"reason": "passed_on", "note": "Not ours"}, headers=auth(w.admin))
    assert bad.status_code == 422 and "department" in bad.text
    done = client.post(f"{url}/close", json={"reason": "passed_on", "department": "revenue", "note": "Patta land"}, headers=auth(w.admin)).json()
    assert done["status"] == "CLOSED" and "Revenue Department" in done["events"][-1]["note"]["en"]
    assert "రెవెన్యూ శాఖ" in done["events"][-1]["note"]["te"] and "محکمہ مال" in done["events"][-1]["note"]["ur"]
    assert notify.unacknowledged_count(db, other) == 0  # the request lapses once the report is closed
    again = client.post(f"{url}/check", json={"outcome": "visible", "note": "x"}, headers=auth(w.north))
    assert again.status_code == 422 and "closed" in again.text


def test_a_place_not_watched_is_placed_on_a_location_the_admin_adds(client, db, w):
    lon, lat = offset(TEST_LON, TEST_LAT, east_m=3000)
    view = post_report(client, lon=lon, lat=lat).json()
    assert [e["kind"] for e in view["events"]] == ["received", "not_watched"] and view["status"] == "RECEIVED"
    report = db.scalar(select(CitizenReport).where(CitizenReport.ref == view["ref"]))
    notes = db.scalars(select(Notification).where(Notification.report_id == report.id)).all()
    assert [n.user_id for n in notes] == [w.admin.id] and "not on the watch list" in notes[0].body
    from tests.factories import square

    new = make_asset(db, geometry=square(lon, lat, side_m=200), district="North", name="Test Parcel Added")
    new.added_at = utcnow()
    db.flush()
    out = client.post(f"/reports/{report.id}/link", json={"asset_id": new.id}, headers=auth(w.admin)).json()
    assert out["status"] == "CHECKING" and out["zone"] == "inside" and out["events"][-1]["kind"] == "added_to_watch"
    assert "Test Parcel Added" in out["events"][-1]["note"]["en"]
    assert db.scalar(select(Signal.asset_id).where(Signal.ref == view["ref"])) == new.id


def test_the_weekly_screen_tells_the_citizen_once_when_the_place_was_seen_clearly(client, db, w):
    view = post_report(client).json()
    report = db.scalar(select(CitizenReport).where(CitizenReport.ref == view["ref"]))
    today = utcnow().date()

    def run(status: str) -> int:
        r = ScreenRun(as_of=today, rule_version="t", rules_sha256="a" * 64, collection="test", started_at=utcnow(), finished_at=utcnow(),
                      assets_total=1, outcomes={}, is_demo=True)
        db.add(r)
        db.flush()
        db.add(AssetScreen(run_id=r.id, asset_id=w.lake.id, status=status, looks=1, candidates=0, legacy_changes=0, counts={},
                           week="2026-W48", changes=[], last_look=today))
        db.flush()
        return service.on_screen_stored(db, r.id, utcnow())

    assert run("no_usable_look") == 0
    assert run("no_candidate") == 1
    assert run("no_candidate") == 0  # the same look is not reported twice
    events = client.get(f"/citizen/reports/{report.ref}").json()["events"]
    assert events[-1]["kind"] == "satellite_checked" and "no change large enough" in events[-1]["note"]["en"]


def test_updates_go_only_to_a_verified_phone_and_demo_messages_stay_here(client, db, w):
    assert client.post("/citizen/otp", json={"phone": "9876543210", "dataset": "demo"}).status_code == 422  # real number in the demo
    real = client.post("/citizen/otp", json={"phone": "9876543210", "dataset": "real"})
    assert real.status_code == 409 and "not available yet" in real.text  # no SMS gateway
    start = client.post("/citizen/otp", json={"phone": "0000000001", "dataset": "demo"}).json()
    assert start["to"].startswith("+91") and len(start["demo_code"]) == 6 and start["sent"] is False
    wrong = client.post("/citizen/otp/verify", json={"phone": "0000000001", "code": "999999" if start["demo_code"] != "999999" else "111111"})
    assert wrong.status_code == 422 and "not right" in wrong.text
    token = client.post("/citizen/otp/verify", json={"phone": "+910000000001", "code": start["demo_code"]}).json()["token"]
    assert post_report(client, token=token + "x").status_code == 422
    view = post_report(client, token=token, name="Test Citizen").json()
    report = db.scalar(select(CitizenReport).where(CitizenReport.ref == view["ref"]))
    assert (report.reporter_phone, report.phone_verified_via, report.wants_updates) == ("+910000000001", "otp", True)
    queued = db.scalars(select(CitizenMessage).where(CitizenMessage.report_id == report.id)).all()
    assert len(queued) == 1 and queued[0].channel == "sms" and queued[0].status == "queued"
    assert queued[0].text.startswith(f"GeoGuard {report.ref}: Being checked.") and queued[0].to_masked == "+91******0001"
    out = notify.tick(db, utcnow())
    assert out["citizen_messages"] == {"held": 1}  # no SMS gateway: held, never sent later
    # Officials see only that updates go to a verified phone, never the number or name.
    desk = client.get(f"/reports/{report.id}", headers=auth(w.north)).json()
    assert desk["phone_masked"] == "+91******0001" and desk["has_name"] is True
    assert "0000000001" not in json.dumps({k: v for k, v in desk.items() if k not in ("phone_masked", "messages")})
    # 90 days after closing, the name and number go; the report and its history stay.
    client.post(f"/reports/{report.id}/close", json={"reason": "no_change_seen", "note": "Checked"}, headers=auth(w.admin))
    assert service.purge_contacts(db, utcnow() + dt.timedelta(days=91)) == 1
    db.refresh(report)
    assert report.reporter_phone is None and report.reporter_name is None and report.contact_purged_at is not None
    assert len(client.get(f"/citizen/reports/{report.ref}").json()["events"]) == 3


def test_rate_limits_and_repeated_false_reports(client, db, w):
    refs = [post_report(client).json()["ref"] for _ in range(service.PER_HOUR)]
    blocked = post_report(client)
    assert blocked.status_code == 429
    # The first report is closed as false twice over (its duplicates follow it); the next is flagged.
    root = db.scalar(select(CitizenReport).where(CitizenReport.ref == refs[0]))
    client.post(f"/reports/{root.id}/close", json={"reason": "not_enough", "note": "Nothing there", "false_report": True}, headers=auth(w.admin))
    other = db.scalar(select(CitizenReport).where(CitizenReport.ref == refs[1]))
    assert other.duplicate_of == root.id and other.status == "CLOSED"
    db.execute(text("UPDATE citizen_reports SET false_report = true, created_at = created_at - interval '2 hours' WHERE id IN (:a, :b)"),
               {"a": root.id, "b": other.id})
    db.execute(text("UPDATE citizen_reports SET created_at = created_at - interval '2 hours'"))
    flagged = post_report(client, lon=offset(TEST_LON, TEST_LAT, east_m=2000)[0]).json()
    assert db.scalar(select(CitizenReport.flags).where(CitizenReport.ref == flagged["ref"])) == ["repeat_false_reports"]


def test_staff_enter_a_helpline_call(client, db, w):
    form = {"channel": "helpline_1070", "source_ref": "1070-TEST-1", "language": "te", "what": "construction", "dataset": "demo",
            "lon": TEST_LON, "lat": TEST_LAT, "description": "Caller says a wall is going up", "caller_phone": "0000000002",
            "wants_updates": True}
    out = client.post("/reports/intake", data={"data": json.dumps(form)}, headers=auth(w.north)).json()
    assert (out["channel"], out["source_ref"], out["updates"], out["phone_masked"]) == ("helpline_1070", "1070-TEST-1", True, "+91******0002")
    assert out["events"][0]["actor"] == w.north.name
    report = db.get(CitizenReport, out["id"])
    assert (report.entered_by, report.phone_verified_via) == (w.north.id, "staff")
    # Citizens cannot use the staff channels.
    assert post_report(client, channel="helpline_1070").status_code == 422


def test_the_whatsapp_conversation_makes_a_report(client, db, w):
    def say(**msg):
        r = client.post("/reports/whatsapp-simulator", json=msg, headers=auth(w.north))
        assert r.status_code == 200, r.text
        return r.json()["replies"]

    assert "1 English" in say(type="text", text="hi")[0]
    assert "📎" in say(type="text", text="2")[0]  # Telugu from here on
    assert say(type="location", latitude=17.41, longitude=78.47)[0].startswith("ఆ పిన్ తెలంగాణ బయట")  # real place in the demo
    menu = say(type="location", latitude=TEST_LAT, longitude=TEST_LON)[0]
    assert "1 మట్టి" in menu and "5 ఇంకేదైనా" in menu
    assert "క్షమించండి" in say(type="text", text="9")[0]
    say(type="text", text="2")
    png = io.BytesIO()
    Image.new("RGB", (20, 20), (1, 2, 3)).save(png, format="PNG")
    assert say(type="image", photo_b64=base64.b64encode(png.getvalue()).decode())[0] == "ఫోటో అందింది."
    say(type="text", text="A wall on the bund")
    done = say(type="text", text="YES")[0]
    ref = service.REF_RE.search(done).group(0)
    report = db.scalar(select(CitizenReport).where(CitizenReport.ref == ref))
    assert (report.channel, report.language, report.what, report.phone_verified_via) == ("whatsapp", "te", "construction", "whatsapp")
    assert report.reporter_phone == f"+910000{w.north.id:06d}" and len(report.photos) == 1 and report.asset_id == w.lake.id
    assert say(type="text", text=ref.lower())[0].startswith(f"సమాచారం {ref}: పరిశీలనలో ఉంది")
    chat = client.get("/reports/whatsapp-simulator", headers=auth(w.north)).json()
    assert chat["state"] == "done" and all(m["status"] in ("received", "held") for m in chat["messages"])


def test_the_whatsapp_webhook_needs_the_states_agreement_and_a_signature(client, db, w, monkeypatch):
    payload = {"entry": [{"changes": [{"value": {"messages": [{"from": "919000000001", "type": "text", "text": {"body": "hi"}}]}}]}]}
    raw = json.dumps(payload).encode()
    assert client.post("/citizen/whatsapp/webhook", content=raw).status_code == 503
    monkeypatch.setenv("LP_WHATSAPP_APP_SECRET", "test-secret")
    assert client.post("/citizen/whatsapp/webhook", content=raw, headers={"x-hub-signature-256": "sha256=bad"}).status_code == 403
    sig = "sha256=" + hmac.new(b"test-secret", raw, hashlib.sha256).hexdigest()
    assert client.post("/citizen/whatsapp/webhook", content=raw, headers={"x-hub-signature-256": sig}).json() == {"handled": 1}
    reply = db.scalars(select(CitizenMessage).where(CitizenMessage.direction == "out", CitizenMessage.is_demo.is_(False))).all()[-1]
    assert reply.status == "held" and "agreement" in reply.detail
    monkeypatch.setenv("LP_WHATSAPP_VERIFY_TOKEN", "verify-me")
    ok = client.get("/citizen/whatsapp/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "42"})
    assert ok.text == "42"
    assert client.get("/citizen/whatsapp/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "no", "hub.challenge": "42"}).status_code == 403
    assert whatsapp.close_idle(db, utcnow() + dt.timedelta(hours=25)) == 1


def test_the_history_and_messages_cannot_be_changed(db, client, w):
    view = post_report(client).json()
    rid = db.scalar(select(CitizenReport.id).where(CitizenReport.ref == view["ref"]))
    for sql in ("UPDATE citizen_report_events SET internal_note = 'x' WHERE report_id = :r", "DELETE FROM citizen_report_events WHERE report_id = :r"):
        with pytest.raises(DBAPIError, match="append-only"):
            with db.begin_nested():
                db.execute(text(sql), {"r": rid})
    stats = client.get("/citizen/config?dataset=demo").json()
    assert stats["stats"]["received"] >= 1 and stats["updates"] == {"sms_updates": False, "whatsapp": False}
    assert [x["key"] for x in stats["whats"]] == ["dumping", "construction", "fencing", "clearing", "other"]
