"""Notifications to officials (DECISIONS.md D-059): routing by area, acknowledgement, follow-up,
channels, the weekly digest, and the admin's pages."""
from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.config import settings
from app.models import AssetScreen, AuditLog, Notification, NotificationDelivery, ScreenRun
from app.notify import channels, messages, service
from app.services import alert_view
from tests.factories import auth, cover, decide, ingest, make_asset, make_user, review

T0 = dt.datetime(2025, 6, 20, 6, tzinfo=dt.timezone.utc)
H = dt.timedelta(hours=1)


@pytest.fixture()
def w(db):
    admin = make_user(db, "admin", email="admin@geoguard.invalid")
    north = make_user(db, "viewer", email="north@geoguard.invalid", phone="+910000000011", channels=["in_app", "email", "sms", "whatsapp"])
    south = make_user(db, "viewer", language="te")
    idle = make_user(db, "viewer")  # covers no area
    cover(db, north, "North")
    cover(db, south, "South", "Mandal B")
    return SimpleNamespace(
        admin=admin, north=north, south=south, idle=idle,
        a_north=make_asset(db, district="North", mandal="Mandal A", village="Village 1"),
        a_south_b=make_asset(db, district=" south", mandal="MANDAL B "),  # case and spaces do not matter
        a_south_c=make_asset(db, district="South", mandal="Mandal C"),
        a_nowhere=make_asset(db),
    )


def notes_for(db, alert_id: int, kind: str = "incident_opened") -> dict[int, Notification]:
    return {n.user_id: n for n in db.scalars(select(Notification).where(Notification.alert_id == alert_id, Notification.kind == kind))}


# Routing ----------------------------------------------------------------------------------------
def test_an_incident_notifies_the_officials_of_its_area_and_the_admin(db, w):
    _, a = ingest(db, w.a_north)
    got = notes_for(db, a.id)
    assert set(got) == {w.north.id, w.admin.id}
    n = got[w.north.id]
    assert n.needs_ack and n.acknowledged_at is None
    assert a.code in n.subject and "Land fill" in n.subject
    assert n.body.startswith("Land fill of about") and f"/alerts/{a.id}" in n.body
    assert n.payload["area"] == {"district": "North", "mandal": "Mandal A", "village": "Village 1"}
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "notify.incident_opened", AuditLog.entity_id == str(a.id)))
    assert set(audit.details["recipients"]) == {w.north.id, w.admin.id}


def test_a_mandal_area_matches_only_that_mandal(db, w):
    _, b = ingest(db, w.a_south_b)
    _, c = ingest(db, w.a_south_c)
    assert set(notes_for(db, b.id)) == {w.south.id, w.admin.id}
    assert set(notes_for(db, c.id)) == {w.admin.id}


def test_an_asset_with_no_area_reaches_the_admin_who_is_told_why(db, w):
    _, a = ingest(db, w.a_nowhere)
    got = notes_for(db, a.id)
    assert set(got) == {w.admin.id}
    assert got[w.admin.id].payload["unrouted"] is True
    assert "No official covers this area yet" in got[w.admin.id].body


def test_telugu_officials_get_telugu_messages_without_english_labels(db, w):
    _, a = ingest(db, w.a_south_b)
    n = notes_for(db, a.id)[w.south.id]
    assert "కొత్త సంఘటన" in n.subject and "మట్టి నింపడం" in n.subject
    assert "Land fill" not in n.body


def test_changes_closed_at_once_or_seen_again_notify_no_one(db, w):
    out, _ = ingest(db, w.a_north, first_changed=dt.date(2024, 12, 1), last_clear=dt.date(2024, 11, 25))
    assert out["outcome"] == "closed_by_legal_check"
    assert notes_for(db, out["alert_id"]) == {}
    first, a = ingest(db, w.a_north)
    again, _ = ingest(db, w.a_north, at=T0 + 7 * 24 * H)
    assert again["outcome"] == "recorded_on_open_incident" and again["alert_id"] == a.id
    assert db.scalar(text("SELECT count(*) FROM notifications WHERE alert_id = :a"), {"a": a.id}) == 2


def test_notifications_never_carry_owner_fields(db, w):
    _, a = ingest(db, w.a_north)
    for n in notes_for(db, a.id).values():
        keys = set(n.payload) | set(n.payload.get("area", {}))
        assert not {k for k in keys if any(w in k for w in ("owner", "claimant", "phone", "aadhaar"))}


# Acknowledgement --------------------------------------------------------------------------------
def test_a_review_acknowledges_and_a_decision_tells_the_area_and_reviewers(db, w):
    _, a = ingest(db, w.a_north)
    review(db, a, w.north)
    got = notes_for(db, a.id)
    assert got[w.north.id].ack_via == "review"
    assert got[w.admin.id].acknowledged_at is None
    review(db, a, w.south, outcome="needs_site_visit", at=T0 + 30 * H)  # an official from elsewhere may review too
    decide(db, a, w.admin, to="CONFIRMED")
    db.refresh(got[w.admin.id])
    assert got[w.admin.id].ack_via == "decision"
    decided = notes_for(db, a.id, "incident_decided")
    assert set(decided) == {w.north.id, w.south.id}
    assert not decided[w.north.id].needs_ack
    assert "confirmed as a real change" in decided[w.north.id].subject
    assert "Test decision" in decided[w.north.id].body


def test_the_database_keeps_notifications_and_allows_one_acknowledgement(db, w):
    _, a = ingest(db, w.a_north)
    n = notes_for(db, a.id)[w.north.id]
    for sql in ("UPDATE notifications SET subject = 'changed' WHERE id = :i", "DELETE FROM notifications WHERE id = :i"):
        with pytest.raises(DBAPIError):
            with db.begin_nested():
                db.execute(text(sql), {"i": n.id})
    service.acknowledge(db, n, w.north, T0 + H)
    with pytest.raises(DBAPIError):
        with db.begin_nested():
            db.execute(text("UPDATE notifications SET acknowledged_at = now(), ack_via = 'review' WHERE id = :i"), {"i": n.id})
    d = db.scalar(select(NotificationDelivery).where(NotificationDelivery.notification_id == n.id))
    with pytest.raises(DBAPIError):
        with db.begin_nested():
            db.execute(text("UPDATE notification_deliveries SET status = 'sent' WHERE id = :i"), {"i": d.id})


# Follow-up --------------------------------------------------------------------------------------
def test_a_reminder_after_24_hours_and_the_admin_told_after_48(db, w):
    _, a = ingest(db, w.a_north, at=T0)
    assert service.follow_up(db, T0 + 23 * H) == {"reminders": 0, "not_acknowledged": 0}
    assert service.follow_up(db, T0 + 25 * H) == {"reminders": 2, "not_acknowledged": 0}  # the official and the admin
    assert service.follow_up(db, T0 + 26 * H) == {"reminders": 0, "not_acknowledged": 0}  # once only
    assert service.follow_up(db, T0 + 49 * H) == {"reminders": 0, "not_acknowledged": 1}  # about the official only
    assert service.follow_up(db, T0 + 72 * H) == {"reminders": 0, "not_acknowledged": 0}
    told = notes_for(db, a.id, "not_acknowledged")[w.admin.id]
    assert w.north.name in told.subject and not told.needs_ack
    # Acknowledging from the inbox clears the reminder too.
    service.acknowledge(db, notes_for(db, a.id)[w.north.id], w.north, T0 + 73 * H)
    reminder = notes_for(db, a.id, "reminder")[w.north.id]
    db.refresh(reminder)
    assert reminder.ack_via == "inbox"


def test_no_follow_up_once_acknowledged_or_decided(db, w):
    _, a = ingest(db, w.a_north, at=T0)
    review(db, a, w.north, at=T0 + 2 * H)
    decide(db, a, w.admin, to="DISMISSED", at=T0 + 3 * H)
    assert service.follow_up(db, T0 + 50 * H) == {"reminders": 0, "not_acknowledged": 0}


# Channels and the outbox ------------------------------------------------------------------------
def test_email_goes_to_the_outbox_and_sms_and_whatsapp_are_held_without_a_gateway(db, w, isolated_storage):
    _, a = ingest(db, w.a_north)
    n = notes_for(db, a.id)[w.north.id]
    counts = service.send_pending(db, T0 + H)
    latest = {d["channel"]: d for d in service.deliveries_for(db, [n.id])[n.id]}
    assert latest["email"]["status"] == "sent" and latest["email"]["to_masked"] == "n***@geoguard.invalid"
    assert latest["sms"]["status"] == "held" and "No SMS gateway agreement" in latest["sms"]["detail"]
    assert latest["whatsapp"]["status"] == "held"
    assert latest["sms"]["to_masked"] == "+91******0011"
    eml = isolated_storage.get_object(channels.outbox_key(n, w.north)).decode()
    assert "Subject: [DEMO] New incident" in eml and "fictional" in eml
    assert counts["sent"] >= 1 and counts["held"] == 2
    # The admin has no phone and only email; the second official has no email address.
    _, b = ingest(db, w.a_south_b)
    south = service.deliveries_for(db, [notes_for(db, b.id)[w.south.id].id])
    assert [(d["channel"], d["status"]) for d in next(iter(south.values()))] == [("email", "skipped")]


def test_demo_data_never_leaves_the_machine_on_smtp(db, w, monkeypatch):
    monkeypatch.setattr(settings, "email_transport", "smtp")
    monkeypatch.setattr(settings, "smtp_host", "relay.invalid")
    _, a = ingest(db, w.a_north)
    n = notes_for(db, a.id)[w.north.id]
    service.send_pending(db, T0 + H)
    email = next(d for d in service.deliveries_for(db, [n.id])[n.id] if d["channel"] == "email")
    assert email["status"] == "skipped" and email["detail"] == channels.DEMO_STAYS


def test_a_failed_delivery_is_retried_three_times_at_most(db, w, monkeypatch):
    monkeypatch.setattr(channels, "send", lambda ch, note, user: channels.Result("failed", "Relay down", "x"))
    monkeypatch.setattr(w.north, "channels", ["in_app", "email"])
    _, a = ingest(db, w.a_north)
    n = notes_for(db, a.id)[w.north.id]
    for minutes, expect in ((1, 1), (2, 0), (8, 1), (14, 1), (20, 0)):
        got = service.send_pending(db, T0 + dt.timedelta(minutes=minutes)).get("failed", 0)
        assert got >= expect if expect else got == 0
    attempts = db.scalars(select(NotificationDelivery.attempt).where(NotificationDelivery.notification_id == n.id).order_by(NotificationDelivery.id)).all()
    assert attempts == [0, 1, 2, 3]


def test_a_set_up_sms_gateway_gets_the_registered_template(db, w, monkeypatch):
    sent = {}

    class Resp:
        status_code = 202

    def fake_post(url, json, headers, timeout):
        sent.update(url=url, json=json, headers=headers)
        return Resp()

    import httpx

    cfg = {**channels.config(), "sms": {**channels.config()["sms"], "agreement_ref": "TS-GW-1", "base_url": "https://gateway.invalid/send",
                                         "dlt_entity_id": "1101", "sender_id": "LKPRTC"}}
    cfg["sms"]["templates"] = {k: {**v, "dlt_template_id": f"T-{k}"} for k, v in cfg["sms"]["templates"].items()}
    monkeypatch.setattr(channels, "config", lambda: cfg)
    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setenv("LP_SMS_TOKEN", "secret")
    _, a = ingest(db, w.a_north)
    payload = messages.incident_payload(alert_view.row_for(db, a.id))
    real = service.create(db, w.north, "reminder", {**payload, "notified_at": T0.isoformat()}, at=T0, needs_ack=True, is_demo=False,
                          alert_id=a.id, about_id=notes_for(db, a.id)[w.north.id].id)
    result = channels.send("sms", real, w.north)
    assert result.status == "sent"
    assert sent["json"]["template_id"] == "T-reminder" and sent["json"]["sender"] == "LKPRTC"
    assert sent["json"]["text"].startswith(f"GeoGuard reminder: incident {a.code} at ")
    assert sent["headers"]["Authorization"] == "Bearer secret"
    assert channels.send("sms", notes_for(db, a.id)[w.north.id], w.north).detail == channels.DEMO_STAYS


def test_dlt_templates_are_filled_slot_by_slot():
    assert channels.render_dlt("A {#var#} B {#var#}", ["x", "y"], {"x": "1", "y": "z" * 40}) == "A 1 B " + "z" * 30
    with pytest.raises(ValueError):
        channels.render_dlt("A {#var#}", ["x", "y"], {})


# Weekly digest ----------------------------------------------------------------------------------
def _week(db, statuses: dict, as_of=dt.date(2025, 6, 18)):
    run = ScreenRun(as_of=as_of, rule_version="t", rules_sha256="a" * 64, collection="test", started_at=T0, finished_at=T0,
                    assets_total=len(statuses), outcomes={}, is_demo=True)
    db.add(run)
    db.flush()
    for asset, status in statuses.items():
        db.add(AssetScreen(run_id=run.id, asset_id=asset.id, status=status, looks=1, candidates=0, legacy_changes=0, counts={},
                           week="2025-W25", changes=[]))
    db.flush()


def test_the_weekly_digest_covers_each_officials_area_once(db, w):
    _, a = ingest(db, w.a_north)
    _week(db, {w.a_north: "candidate_found", w.a_south_b: "no_usable_look", w.a_south_c: "no_candidate", w.a_nowhere: "no_candidate"})
    out = service.send_digests(db, "2025-W25", is_demo=True, at=T0 + H)
    assert out["sent"] == 3  # two officials with areas, and the admin; not the official with none
    digests = {n.user_id: n for n in db.scalars(select(Notification).where(Notification.kind == "weekly_digest"))}
    north = digests[w.north.id].payload
    assert north["figures"] == {"watched": 1, "clear_look": 1, "no_clear_look": 0, "changed": 1, "new_incidents": 1,
                                "waiting_for_you": 1, "open_over_14_days": 0}
    assert north["areas"] == ["North"]
    south = digests[w.south.id].payload
    assert south["figures"]["watched"] == 1 and [x["asset_name"] for x in south["no_clear_look"]] == [w.a_south_b.name]
    assert "వారం 2025-W25" in digests[w.south.id].subject
    admin = digests[w.admin.id].payload
    assert admin["scope"] == "all" and admin["figures"]["watched"] == 4 and admin["figures"]["waiting_for_you"] == 0
    assert "Waiting for your decision: 0." in digests[w.admin.id].body
    assert service.send_digests(db, "2025-W25", is_demo=True, at=T0 + 2 * H)["sent"] == 0


# API --------------------------------------------------------------------------------------------
def test_the_inbox_shows_only_my_notifications_and_acknowledges_them(client, db, w):
    _, a = ingest(db, w.a_north)
    mine = client.get("/notifications?dataset=demo", headers=auth(w.north)).json()
    assert mine["unacknowledged"] == 1 and [i["alert_id"] for i in mine["items"]] == [a.id]
    assert client.get("/notifications?dataset=real", headers=auth(w.north)).json()["items"] == []
    nid = mine["items"][0]["id"]
    assert client.post(f"/notifications/{nid}/ack", headers=auth(w.south)).status_code == 404
    detail = client.get(f"/alerts/{a.id}", headers=auth(w.north)).json()
    assert [n["id"] for n in detail["my_notifications"]] == [nid]
    assert client.post(f"/notifications/{nid}/ack", headers=auth(w.north)).json()["acknowledged"] == 1
    assert client.post(f"/notifications/{nid}/ack", headers=auth(w.north)).json()["acknowledged"] == 0
    assert client.get("/notifications/count?dataset=demo", headers=auth(w.north)).json() == {"unacknowledged": 0}
    assert client.get(f"/alerts/{a.id}", headers=auth(w.north)).json()["my_notifications"] == []


def test_the_delivery_log_digests_and_runs_are_for_the_admin(client, db, w):
    ingest(db, w.a_north)
    for path, method in (("/notifications/deliveries", "get"), ("/notifications/channels", "get"), ("/notifications/run", "post")):
        assert getattr(client, method)(path, headers=auth(w.north)).status_code == 403
    assert client.post("/notifications/digests", json={"dataset": "demo"}, headers=auth(w.north)).status_code == 403
    assert client.post("/notifications/digests", json={"dataset": "real"}, headers=auth(w.admin)).status_code == 409
    ran = client.post("/notifications/run", headers=auth(w.admin)).json()
    assert ran["deliveries"].get("sent", 0) >= 1
    log = client.get("/notifications/deliveries?dataset=demo", headers=auth(w.admin)).json()
    assert {(i["channel"], i["status"]) for i in log["items"]} >= {("email", "sent"), ("sms", "held"), ("whatsapp", "held")}
    assert {c["channel"]: c["ready"] for c in log["channels"]} == {"email": True, "sms": False, "whatsapp": False}
    _week(db, {w.a_north: "no_candidate"})
    assert client.post("/notifications/digests", json={"dataset": "demo", "week": "2025-W25"}, headers=auth(w.admin)).json()["sent"] == 3


def test_the_admin_sets_contacts_channels_and_areas(client, db, w):
    assert client.get("/users", headers=auth(w.north)).status_code == 403
    users = {u["id"]: u for u in client.get("/users", headers=auth(w.admin)).json()}
    assert users[w.north.id]["areas"] == [{"district": "North", "mandal": None}]
    assert users[w.north.id]["email"] == "north@geoguard.invalid"
    for bad in ({"email": "not-an-email"}, {"phone": "98765"}, {"channels": ["email"]}, {"clear": ["name"]}):
        assert client.patch(f"/users/{w.idle.id}", json=bad, headers=auth(w.admin)).status_code == 422
    out = client.patch(f"/users/{w.idle.id}", json={"email": "idle@geoguard.invalid", "channels": ["whatsapp", "in_app"]}, headers=auth(w.admin)).json()
    assert out["channels"] == ["in_app", "whatsapp"]
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "user.contact_changed").order_by(AuditLog.id.desc()))
    assert audit.details["fields"] == ["email", "channels"] and "idle@" not in str(audit.details)
    out = client.put(f"/users/{w.idle.id}/areas", json={"areas": [{"district": "North"}, {"district": "north "}, {"district": "South", "mandal": "Mandal C"}]},
                     headers=auth(w.admin)).json()
    assert out["areas"] == [{"district": "North", "mandal": None}, {"district": "South", "mandal": "Mandal C"}]
    assert client.put(f"/users/{w.admin.id}/areas", json={"areas": []}, headers=auth(w.admin)).status_code == 422
    _, c = ingest(db, w.a_south_c)
    assert w.idle.id in notes_for(db, c.id)
    areas = client.get("/areas", headers=auth(w.admin)).json()["items"]
    assert {"district": "North", "dataset": "demo", "assets": 1, "mandals": [{"mandal": "Mandal A", "assets": 1}]} in areas


def test_a_request_to_acknowledge_lapses_once_the_incident_is_decided(client, db, w):
    _, a = ingest(db, w.a_north)
    assert client.get("/notifications/count?dataset=demo", headers=auth(w.north)).json() == {"unacknowledged": 1}
    decide(db, a, w.admin, to="DISMISSED")
    assert client.get("/notifications/count?dataset=demo", headers=auth(w.north)).json() == {"unacknowledged": 0}
    assert client.get("/notifications?dataset=demo&pending=true", headers=auth(w.north)).json()["items"] == []
    assert client.get(f"/alerts/{a.id}", headers=auth(w.north)).json()["my_notifications"] == []
    # It still counts as not acknowledged: the record is kept as it was.
    assert notes_for(db, a.id)[w.north.id].acknowledged_at is None
