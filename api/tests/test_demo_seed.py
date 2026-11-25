"""The demo seed (D-057): every incident path is present, every asset has documents and eight
weekly records with images, and every row is fictional and marked."""
import datetime as dt

import pytest
from sqlalchemy import func, select, text

from app.audit import chain
from app.models import (
    Alert,
    Asset,
    AssetDocument,
    AssetScreen,
    AuthorisedWork,
    Candidate,
    CourtCase,
    IncidentReview,
    Observation,
    Permit,
    ScreenRun,
    User,
)
from app.models import Notification, NotificationDelivery
from app.seed import demo
from app.services import dashboard
from app.seed.demo_render import TileRenderer, render_chip, render_week
from app.seed.demo_world import World
from tests.factories import auth

SEED_DAY = dt.date(2026, 11, 6)


def test_seeded_demo(db, client, isolated_storage):
    """Every check on one seeded demo: seeding takes seconds, so it is done once."""
    seeded = demo.Seeder(db, SEED_DAY).run()
    _incident_paths(db, seeded)
    _users(db)
    _documents(db, seeded, isolated_storage)
    _weeks(db, seeded, isolated_storage)
    _weekly_record_names_the_change(db, client)
    _fictional(db)
    _open_sea(db)
    _notifications(db, seeded, isolated_storage)
    _dashboard(db)
    _citizen_reports(db, seeded)
    assert chain.verify(db)["ok"] is True
    _chips(db, isolated_storage)


def _citizen_reports(db, seeded):
    """Every channel and every way a report ends (D-062), all fictional."""
    assert seeded["citizen_reports"] == {
        "r-full-path": "CLOSED/incident_confirmed", "r-not-real": "CLOSED/incident_dismissed", "r-outside": "CLOSED/passed_on",
        "r-kunta": "CLOSED/no_change_seen", "r-parcel-a": "CHECKING", "r-headline": "CHECKING", "r-headline-whatsapp": "CHECKING",
    }
    rows = db.execute(text("SELECT channel, reporter_phone, is_demo, duplicate_of IS NOT NULL AS dup FROM citizen_reports")).all()
    assert {r[0] for r in rows} == {"web", "whatsapp", "helpline_1070", "praja_vani"} and all(r[2] for r in rows)
    assert all(p is None or p.startswith("+910000") for _, p, _, _ in rows) and sum(r[3] for r in rows) == 1
    kinds = db.scalars(text("SELECT e.kind FROM citizen_report_events e JOIN citizen_reports r ON r.id = e.report_id ORDER BY e.id")).all()
    assert {"change_found", "duplicate", "check_not_visible", "closed_passed_on", "closed_incident_confirmed", "satellite_checked"} <= set(kinds)


def _incident_paths(db, seeded):
    s = seeded["incidents"]
    assert s["headline"] == "OPEN"
    assert s["building"] == "UNDER_REVIEW"
    assert s["full_path"] == "CLOSED/confirmed"
    assert s["awaiting_boundary"] == "CONFIRMED/confirmed"
    assert s["false_alarm"] == "DISMISSED/dismissed"
    assert s["not_real"] == "CLOSED/dismissed"
    assert s["court_hold"] == "OPEN"
    assert s["watch_list"] == "OPEN"
    assert s["authorised_work"] == "CLOSED/auto"
    assert s["legacy"] == "CLOSED/auto"
    assert s["out_of_scope"] == "CLOSED/auto"
    assert s["levelling"] == "OPEN"
    assert s["reopened"] == "OPEN"

    reopened = db.scalar(select(Alert).where(Alert.related_alert_id.is_not(None)))
    assert reopened is not None and db.get(Alert, reopened.related_alert_id).resolution == "dismissed"
    types = set(db.scalars(text("SELECT DISTINCT change_type::text FROM candidates")))
    assert {"building", "soil_fill", "levelling", "clearing"} <= types
    assert db.scalar(select(func.count()).select_from(IncidentReview)) >= 10


def _users(db):
    users = {u.username: u.role for u in db.scalars(select(User))}
    assert users == {"demo.admin": "admin", "demo.viewer1": "viewer", "demo.viewer2": "viewer"}


def _documents(db, seeded, isolated_storage):
    counts = dict(db.execute(text("SELECT asset_id, count(*) FROM asset_documents GROUP BY asset_id")).all())
    assert len(counts) == seeded["assets"] and min(counts.values()) >= 1
    for doc in db.scalars(select(AssetDocument).where(AssetDocument.file_key.is_not(None))):
        data = isolated_storage.get_object(doc.file_key)
        assert data.startswith(b"%PDF") and b"DEMO DATA" in data
    kinds = set(db.scalars(text("SELECT DISTINCT doc_type FROM asset_documents")))
    assert {"recovery_order", "notification", "land_record", "survey_map", "court_order"} <= kinds


def _weeks(db, seeded, isolated_storage):
    assert db.scalar(select(func.count()).select_from(ScreenRun).where(ScreenRun.is_demo.is_(True))) == demo.WEEKS
    assert seeded["weekly_records"] == demo.WEEKS * seeded["assets"]
    rows = db.scalars(select(AssetScreen)).all()
    assert all(r.week and r.week.startswith("2026-W") for r in rows)
    with_image = [r for r in rows if r.image_key]
    assert len(with_image) == len(rows) - len(demo.CLOUDY_ASSETS)
    assert all(isolated_storage.get_object(r.image_key).startswith(b"\x89PNG") for r in with_image[:5])
    cloudy = [r for r in rows if r.status == "no_usable_look"]
    assert len(cloudy) == len(demo.CLOUDY_ASSETS) and all(not r.changes for r in cloudy)


def _weekly_record_names_the_change(db, client):
    admin = db.scalar(select(User).where(User.username == "demo.admin"))
    asset = db.scalar(select(Asset).where(Asset.asset_key == "demo-cheruvu-1"))
    weeks = client.get(f"/assets/{asset.id}/weeks", headers=auth(admin)).json()["items"]
    assert len(weeks) == demo.WEEKS
    latest = weeks[0]
    assert latest["changed"] and latest["status_label"] == "Change found"
    change = latest["changes"][0]
    assert change["change_label"] == "Land fill" and change["alert_code"].startswith("DEMO-") and change["alert_state"] == "OPEN"
    assert all(not w["changed"] and w["status_label"] == "No change seen" for w in weeks[1:])
    image = client.get(f"/assets/{asset.id}/weeks/{latest['screen_id']}/image", headers=auth(admin))
    assert image.status_code == 200 and image.content.startswith(b"\x89PNG")

    # An incident still open shows as continuing in the weeks after it was found.
    building = db.scalar(select(Asset).where(Asset.asset_key == "demo-cheruvu-4"))
    bweeks = client.get(f"/assets/{building.id}/weeks", headers=auth(admin)).json()["items"]
    assert bweeks[0]["changes"][0]["continues"] is True and bweeks[0]["changes"][0]["change_label"] == "Construction"


def _fictional(db):
    assert all(a.is_demo and a.name.startswith("Demo ") for a in db.scalars(select(Asset)))
    assert all(a.is_demo for a in db.scalars(select(Alert)))
    assert all(d.is_demo for d in db.scalars(select(AssetDocument)))
    assert all(o.is_demo and "Not satellite data" in o.licence_notice for o in db.scalars(select(Observation)))
    for model in (Permit, AuthorisedWork, CourtCase):
        assert all(r.is_demo for r in db.scalars(select(model)))
    assert all(u.is_demo and u.name.startswith("Demo ") for u in db.scalars(select(User)))
    assert all(s.startswith("D-") for a in db.scalars(select(Asset)) for s in a.survey_numbers)


def _notes(db, username: str, kind: str, asset_key: str) -> list[Notification]:
    return db.scalars(text(
        """SELECT n.id FROM notifications n JOIN users u ON u.id = n.user_id JOIN alerts al ON al.id = n.alert_id
           JOIN candidates c ON c.id = al.candidate_id JOIN assets a ON a.id = c.asset_id
           WHERE u.username = :u AND n.kind = :k AND a.asset_key = :a ORDER BY n.id"""), {"u": username, "k": kind, "a": asset_key}).all()


def _notifications(db, seeded, isolated_storage):
    """D-059: each open incident told its area's official and the admin; follow-ups ran each morning."""
    assert seeded["digests"] == 3 and seeded["notifications"] > 20
    # The headline, found two days ago in the north, is still unacknowledged: a reminder, and the admin told.
    assert len(_notes(db, "demo.viewer2", "incident_opened", "demo-cheruvu-1")) == 1
    assert _notes(db, "demo.viewer1", "incident_opened", "demo-cheruvu-1") == []
    assert len(_notes(db, "demo.viewer2", "reminder", "demo-cheruvu-1")) == 1
    assert len(_notes(db, "demo.admin", "not_acknowledged", "demo-cheruvu-1")) == 1
    # Reviewed within a day in the south: acknowledged by the review, no reminder.
    built = db.get(Notification, _notes(db, "demo.viewer1", "incident_opened", "demo-cheruvu-4")[0])
    assert built.ack_via == "review" and _notes(db, "demo.viewer1", "reminder", "demo-cheruvu-4") == []
    # A decision tells the area's official and the reviewer.
    assert _notes(db, "demo.viewer2", "incident_decided", "demo-cheruvu-2") and _notes(db, "demo.viewer1", "incident_decided", "demo-cheruvu-2")
    # Changes closed at once by the legal check told no one.
    assert _notes(db, "demo.admin", "incident_opened", "demo-cheruvu-3") == []
    # Channels: emails in the local outbox; SMS and WhatsApp held, as no gateway exists.
    latest = dict(db.execute(text(
        """SELECT d.channel || ':' || d.status, count(*) FROM (
             SELECT DISTINCT ON (notification_id, channel) channel, status FROM notification_deliveries
             ORDER BY notification_id, channel, id DESC) d GROUP BY 1""")).all())
    assert latest.get("email:sent", 0) > 10 and latest.get("sms:held", 0) > 0 and latest.get("whatsapp:held", 0) > 0
    assert not {k for k in latest if k.endswith(":queued")}
    sent = db.scalar(select(NotificationDelivery).where(NotificationDelivery.status == "sent", NotificationDelivery.channel == "email"))
    key = sent.detail.split(": ", 1)[1]
    assert isolated_storage.get_object(key).startswith(b"From: GeoGuard")
    assert all(n.is_demo for n in db.scalars(select(Notification)))


def _dashboard(db):
    viewer = db.scalar(select(User).where(User.username == "demo.viewer2"))
    out = dashboard.overview(db, viewer, is_demo=True)
    assert [c["name"] for c in out["children"]] == ["Demo North District", "Demo South District"]
    assert out["figures"]["assets"] == 20 and out["week"] is not None
    north = dashboard.overview(db, viewer, is_demo=True, district="Demo North District", mandal="Demo Mandal 1")
    assert [c["name"] for c in north["children"]] == ["Demo Village 1", "Demo Village 2"]


def _open_sea(db):
    # The demo box sits around 81.5 E, 14.5 N; the nearest coast is about 150 km west of it.
    outside = db.scalar(text("SELECT count(*) FROM candidates WHERE NOT ST_Within(geom, ST_MakeEnvelope(81.4, 14.4, 81.6, 14.6, 4326))"))
    assert outside == 0
    outside_b = db.scalar(text("SELECT count(*) FROM boundaries WHERE NOT ST_Within(geom, ST_MakeEnvelope(81.4, 14.4, 81.6, 14.6, 4326))"))
    assert outside_b == 0


def _chips(db, isolated_storage):
    for cand in db.scalars(select(Candidate)):
        for key in (cand.before_chip, cand.after_chip):
            head = isolated_storage.head_object(key)
            assert head is not None and head["size"] > 2000


def test_images_are_png_and_differ(db):
    world = World.load()
    sc = next(s for s in world.spec["scenarios"] if s["key"] == "headline")
    before = render_chip(world, sc, when=dt.date(2026, 10, 18), after=False)
    after = render_chip(world, sc, when=dt.date(2026, 10, 23), after=True)
    assert before.startswith(b"\x89PNG") and after.startswith(b"\x89PNG") and before != after
    quiet = render_week(world, "demo-cheruvu-1", when=dt.date(2026, 10, 18), week="2026-W42", changes=[])
    changed = render_week(world, "demo-cheruvu-1", when=dt.date(2026, 10, 18), week="2026-W42", changes=[(sc, 1.0)])
    assert quiet.startswith(b"\x89PNG") and quiet != changed


def test_tile_renderer_draws_a_tile():
    data = TileRenderer(World.load()).render(15, 23801, 15094)
    assert data.startswith(b"\x89PNG")
