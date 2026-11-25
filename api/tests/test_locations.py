"""Locations the admin adds and stops watching, and the land categories (DECISIONS.md D-061)."""
from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app import categories
from app.config import settings
from app.enums import AssetType
from app.models import Asset, AuditLog, MonitoringChange
from tests.factories import auth, ingest, make_asset, make_user, square

TOKEN = {"X-Pipeline-Token": "test-token"}
# A fictional square in rural Telangana. The outline must lie in the State; no real record is here
# in the test database.
IN_STATE = (79.40, 18.60)


@pytest.fixture(autouse=True)
def _token(monkeypatch):
    monkeypatch.setattr(settings, "pipeline_token", "test-token")


def body(**kw) -> dict:
    out = {
        "type": "revenue_parcel",
        "name": "Test Government Land 1",
        "district": "Test District",
        "mandal": "Test Mandal",
        "geometry": square(*IN_STATE, side_m=200),
        "drawn": True,
        "status": "derived",
        "source_name": "Drawn by the admin on the satellite base map",
        "survey_numbers": ["101", " 102/A "],
    }
    out.update(kw)
    return out


def test_every_asset_type_has_one_category_and_planned_ones_say_what_they_need(client, db):
    viewer = make_user(db, "viewer")
    items = {c["name"]: c for c in client.get("/categories", headers=auth(viewer)).json()["items"]}
    assert {k: v["status"] for k, v in items.items()} == {
        "water_body": "live", "government_land": "live", "endowment_land": "planned", "forest_land": "planned",
        "citizen_reported": "intake"}  # places made from citizens' reports (D-063)
    assert {t["type"] for c in items.values() for t in c["types"]} == set(AssetType.__members__)
    assert items["forest_land"]["needs"] and items["endowment_land"]["needs"]
    assert items["government_land"]["label"]["te"] == "ప్రభుత్వ భూమి"
    assert categories.primary_kind("lake") == "ftl" and categories.primary_kind("agency_parcel") == "parcel"


def test_the_admin_adds_a_drawn_parcel_and_the_next_screen_watches_it(client, db):
    admin = make_user(db, "admin", is_demo=False)
    resp = client.post("/assets", json=body(), headers=auth(admin))
    assert resp.status_code == 201, resp.text
    p = resp.json()["properties"]
    assert (p["category"], p["type"], p["monitored"], p["is_demo"]) == ("government_land", "revenue_parcel", True, False)
    # Drawn on the screen: for watching only (cohort D, mode WATCH), never for field action.
    assert (p["cohort"], p["mode"], p["boundary_status"], p["boundary_kind"]) == ("D_UNNOTIFIED", "WATCH", "derived", "parcel")
    assert p["survey_numbers"] == ["101", "102/A"] and p["added_by"] == admin.name
    assert p["asset_key"] == "loc-test-government-land-1"
    assert 9 < p["area_acres"] < 11  # 200 m x 200 m = 4 ha = 9.9 acres

    kinds = {f["properties"]["kind"] for f in client.get(f"/assets/{p['id']}/boundaries", headers=auth(admin)).json()["features"]}
    assert kinds == {"parcel", "watch_ring"}  # land has no buffer; only lakes do

    watch = client.get("/pipeline/watchlist", headers=TOKEN).json()["assets"]
    mine = [a for a in watch if a["id"] == p["id"]]
    assert mine and mine[0]["type"] == "revenue_parcel" and set(mine[0]["boundaries"]) == {"parcel", "watch_ring"}

    hist = client.get(f"/assets/{p['id']}/monitoring", headers=auth(admin)).json()["items"]
    assert len(hist) == 1 and hist[0]["monitored"] and hist[0]["actor"] == admin.name
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "location.added")).all()[-1]
    assert entry.details["category"] == "government_land" and entry.details["drawn"] is True


def test_a_lake_gets_its_buffer_and_a_confirmed_boundary_its_reference(client, db):
    admin = make_user(db, "admin", is_demo=False)
    resp = client.post("/assets", json=body(type="lake", name="Test Cheruvu", drawn=False, status="final_notification",
                                            notification_ref="Test LPC notification 1", source_name="Test FTL file"), headers=auth(admin))
    assert resp.status_code == 201, resp.text
    p = resp.json()["properties"]
    assert (p["category"], p["cohort"], p["mode"], p["boundary_kind"]) == ("water_body", "B_FINAL", "ACTION", "ftl")
    kinds = {f["properties"]["kind"] for f in client.get(f"/assets/{p['id']}/boundaries", headers=auth(admin)).json()["features"]}
    assert kinds == {"ftl", "buffer", "watch_ring"}


@pytest.mark.parametrize(
    ("change", "code", "says"),
    [
        ({"type": "forest_land"}, 422, "planned and not watched yet"),
        ({"type": "endowment_land"}, 422, "Endowments Department"),
        ({"type": "temple"}, 422, "Unknown asset type"),
        ({"status": "surveyed_agency"}, 422, "drawn on the screen is for watching only"),
        ({"drawn": False, "status": "surveyed_agency"}, 422, "needs the reference"),
        ({"type": "lake", "drawn": False, "status": "surveyed_agency", "notification_ref": "X"}, 422, "boundary can be"),
        ({"geometry": square(81.5, 14.5, side_m=200)}, 422, "outside Telangana"),
        ({"geometry": square(*IN_STATE, side_m=30)}, 422, "cannot watch it usefully"),
        ({"geometry": square(*IN_STATE, side_m=8000)}, 422, "Split it"),
        ({"geometry": {"type": "Point", "coordinates": list(IN_STATE)}}, 422, "Polygon or MultiPolygon"),
        ({"baseline_date": "2999-01-01"}, 422, "future"),
        ({"name": "  "}, 422, "name"),
        ({"district": ""}, 422, "district"),
        ({"source_name": " "}, 422, "outline comes from"),
    ],
)
def test_what_cannot_be_added(client, db, change, code, says):
    admin = make_user(db, "admin", is_demo=False)
    resp = client.post("/assets", json=body(**change), headers=auth(admin))
    assert resp.status_code == code, resp.text
    assert says in resp.text
    assert db.scalar(select(Asset).where(Asset.asset_key.like("loc-%"))) is None


def test_only_the_admin_adds_and_the_same_place_is_not_added_twice(client, db):
    admin, viewer = make_user(db, "admin", is_demo=False), make_user(db, "viewer", is_demo=False)
    assert client.post("/assets", json=body(), headers=auth(viewer)).status_code == 403
    first = client.post("/assets", json=body(), headers=auth(admin)).json()
    again = client.post("/assets", json=body(name="Same place", geometry=square(IN_STATE[0] + 0.0002, IN_STATE[1], side_m=200)), headers=auth(admin))
    assert again.status_code == 409 and again.json()["detail"]["asset_id"] == first["id"]
    check = client.post("/assets/outline-check", json={"geometry": square(*IN_STATE, side_m=200)}, headers=auth(admin)).json()
    assert check["ok"] is False and check["asset_id"] == first["id"]
    # Next door is fine; the check gives the area first.
    beside = square(IN_STATE[0] + 0.01, IN_STATE[1], side_m=100)
    assert client.post("/assets/outline-check", json={"geometry": beside}, headers=auth(admin)).json() == {"ok": True, "area_sq_m": pytest.approx(10000, rel=0.02), "area_acres": pytest.approx(2.47, rel=0.02)}
    assert client.post("/assets", json=body(name="Beside", geometry=beside), headers=auth(admin)).status_code == 201
    # A second location with the same name gets its own key.
    other = client.post("/assets", json=body(geometry=square(IN_STATE[0] - 0.01, IN_STATE[1], side_m=100)), headers=auth(admin)).json()
    assert other["properties"]["asset_key"] == "loc-test-government-land-1-2"


def test_stopping_the_watch_keeps_everything_and_can_be_undone(client, db):
    admin, viewer = make_user(db, "admin"), make_user(db, "viewer")
    asset = make_asset(db, district="North")
    _, alert = ingest(db, asset)
    url = f"/assets/{asset.id}/monitoring"
    assert client.post(url, json={"monitored": False, "reason": "Handed over"}, headers=auth(viewer)).status_code == 403
    assert client.post(url, json={"monitored": False, "reason": "no"}, headers=auth(admin)).status_code == 422

    out = client.post(url, json={"monitored": False, "reason": "Handed over to the agency, which fenced it"}, headers=auth(admin)).json()
    assert out == {"asset_id": asset.id, "monitored": False, "open_incidents": 1}
    p = client.get(f"/assets/{asset.id}", headers=auth(viewer)).json()["properties"]
    assert p["monitored"] is False and p["monitoring_reason"] == "Handed over to the agency, which fenced it"
    # Nothing is lost: the incident and the boundary are still there.
    assert client.get(f"/alerts/{alert.id}", headers=auth(viewer)).status_code == 200
    assert client.get(f"/assets/{asset.id}/boundaries", headers=auth(viewer)).json()["features"]
    again = client.post(url, json={"monitored": False, "reason": "Handed over again"}, headers=auth(admin))
    assert again.status_code == 422 and "already not watched" in again.text

    assert client.post(url, json={"monitored": True, "reason": "The agency asked us to watch it again"}, headers=auth(admin)).json()["monitored"] is True
    hist = client.get(url, headers=auth(viewer)).json()["items"]
    assert [h["monitored"] for h in hist] == [True, False]
    actions = db.scalars(select(AuditLog.action).where(AuditLog.entity == "asset", AuditLog.entity_id == str(asset.id))).all()
    assert "location.watch_stopped" in actions and "location.watch_resumed" in actions


def test_a_stopped_location_leaves_the_watchlist(client, db):
    admin = make_user(db, "admin", is_demo=False)
    p = client.post("/assets", json=body(), headers=auth(admin)).json()
    client.post(f"/assets/{p['id']}/monitoring", json={"monitored": False, "reason": "Added by mistake"}, headers=auth(admin))
    assert p["id"] not in {a["id"] for a in client.get("/pipeline/watchlist", headers=TOKEN).json()["assets"]}
    items = {c["name"]: c for c in client.get("/categories?dataset=real", headers=auth(admin)).json()["items"]}
    assert items["government_land"]["watched"] == 0


def test_the_database_allows_watching_to_change_only_through_the_log(db):
    asset = make_asset(db)
    with pytest.raises(DBAPIError, match="changes only through monitoring_changes"):
        with db.begin_nested():
            db.execute(text("UPDATE assets SET monitored = false WHERE id = :a"), {"a": asset.id})
    db.add(MonitoringChange(asset_id=asset.id, monitored=False, reason="Test stop"))
    db.flush()
    assert db.scalar(text("SELECT monitored FROM assets WHERE id = :a"), {"a": asset.id}) is False
    for sql in ("UPDATE monitoring_changes SET reason = 'edited' WHERE asset_id = :a", "DELETE FROM monitoring_changes WHERE asset_id = :a"):
        with pytest.raises(DBAPIError, match="append-only"):
            with db.begin_nested():
                db.execute(text(sql), {"a": asset.id})
    with pytest.raises(DBAPIError):
        with db.begin_nested():
            db.add(MonitoringChange(asset_id=asset.id, monitored=True, reason="  "))
            db.flush()
