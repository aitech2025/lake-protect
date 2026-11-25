"""Satellite image sources, maintained by the admin (DECISIONS.md D-066)."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from app.config import settings
from app.models import AuditLog, CitizenReport, ImageryRequest
from tests.factories import TG_LAT, TG_LON, auth, make_user

TOKEN = {"X-Pipeline-Token": "test-token"}
PLANET = {"key": "test-tasking-30cm", "name": "Test tasking, 30 cm", "provider": "Test reseller", "purpose": "sharper",
          "resolution_m": 0.3, "price_usd_per_sq_km": 40, "min_order_sq_km": 25, "notes": "Fictional source for the test"}


@pytest.fixture(autouse=True)
def _token(monkeypatch):
    monkeypatch.setattr(settings, "pipeline_token", "test-token")


@pytest.fixture()
def people(db):
    return type("P", (), {"admin": make_user(db, "admin"), "official": make_user(db, "viewer")})


def by_key(client, user) -> dict:
    return {s["key"]: s for s in client.get("/satellites", headers=auth(user)).json()["items"]}


def test_the_sources_the_app_used_are_seeded_and_everyone_can_read_them(client, people):
    sources = by_key(client, people.official)
    assert {k: (s["purpose"], s["active"]) for k, s in sources.items()} == {
        "sentinel-2-l2a": ("screen_optical", True), "sentinel-1-rtc": ("screen_radar", True), "isro_nrsc": ("sharper", True),
        "commercial_archive": ("sharper", True), "commercial_tasking": ("sharper", True)}
    s2 = sources["sentinel-2-l2a"]
    assert (s2["stac_url"], s2["collection"], s2["max_scene_cloud_pct"], s2["resolution_m"]) == (
        "https://earth-search.aws.element84.com/v1", "sentinel-2-c1-l2a", 70, 10)
    assert sources["commercial_archive"]["price_usd_per_sq_km"] == 26 and sources["isro_nrsc"]["price_usd_per_sq_km"] is None
    assert client.get("/pipeline/satellites", headers=TOKEN).json()["screen_optical"]["collection"] == "sentinel-2-c1-l2a"
    assert client.get("/pipeline/satellites").status_code in (401, 403)


def test_the_admin_adds_changes_and_deletes_a_source_and_every_step_is_logged(client, db, people):
    assert client.post("/satellites", json=PLANET, headers=auth(people.official)).status_code == 403
    added = client.post("/satellites", json=PLANET, headers=auth(people.admin))
    assert added.status_code == 201, added.text
    sid = added.json()["id"]
    assert client.post("/satellites", json=PLANET, headers=auth(people.admin)).status_code == 409  # the key is taken
    changed = client.patch(f"/satellites/{sid}", json={"price_usd_per_sq_km": 35, "notes": "New price list"}, headers=auth(people.admin)).json()
    assert changed["price_usd_per_sq_km"] == 35 and changed["updated_by"] == people.admin.name
    assert client.patch(f"/satellites/{sid}", json={"key": "renamed"}, headers=auth(people.admin)).status_code == 422
    assert client.patch(f"/satellites/{sid}", json={"purpose": "screen_radar"}, headers=auth(people.admin)).status_code == 422
    log = db.scalar(select(AuditLog).where(AuditLog.action == "satellite_source.changed", AuditLog.entity_id == str(sid)))
    assert log.details["before"]["price_usd_per_sq_km"] == 40 and log.details["after"]["price_usd_per_sq_km"] == 35
    assert client.delete(f"/satellites/{sid}?reason=x", headers=auth(people.admin)).status_code == 422  # a reason is needed
    assert client.delete(f"/satellites/{sid}?reason=Contract ended", headers=auth(people.admin)).json() == {"deleted": PLANET["key"]}
    assert PLANET["key"] not in by_key(client, people.admin)
    gone = db.scalar(select(AuditLog).where(AuditLog.action == "satellite_source.deleted", AuditLog.entity_id == str(sid)))
    assert gone.details["reason"] == "Contract ended" and gone.details["before"]["name"] == PLANET["name"]
    actions = [h["action"] for h in client.get("/satellites/history", headers=auth(people.admin)).json()["items"]]
    assert actions[:3] == ["satellite_source.deleted", "satellite_source.changed", "satellite_source.added"]


def test_values_are_checked_for_the_purpose(client, people):
    base = {"key": "test-optical", "name": "Test optical", "provider": "Test", "purpose": "screen_optical", "resolution_m": 10}
    for bad, why in (
        ({}, "catalogue address"),
        ({"stac_url": "http://plain.example/v1", "collection": "c1"}, "catalogue address"),
        ({"stac_url": "https://stac.example/v1"}, "collection"),
        ({"stac_url": "https://stac.example/v1", "collection": "c1"}, "cloud limit"),
        ({"stac_url": "https://stac.example/v1", "collection": "c1", "max_scene_cloud_pct": 120}, "cloud limit"),
    ):
        out = client.post("/satellites", json={**base, **bad}, headers=auth(people.admin))
        assert out.status_code == 422 and why in out.text, (bad, out.text)
    assert client.post("/satellites", json={**base, "key": "Bad Key!"}, headers=auth(people.admin)).status_code == 422
    assert client.post("/satellites", json={**PLANET, "price_usd_per_sq_km": -1}, headers=auth(people.admin)).status_code == 422
    assert client.post("/satellites", json={**base, "purpose": "drone"}, headers=auth(people.admin)).status_code == 422


def test_one_screening_source_is_on_and_the_screen_always_has_an_optical_one(client, db, people):
    s2 = by_key(client, people.admin)["sentinel-2-l2a"]
    refused = client.patch(f"/satellites/{s2['id']}", json={"active": False}, headers=auth(people.admin))
    assert refused.status_code == 409 and "Turn another optical source on first" in refused.text
    assert client.delete(f"/satellites/{s2['id']}?reason=Not needed", headers=auth(people.admin)).status_code == 409
    other = {"key": "test-optical", "name": "Test optical mirror", "provider": "Test mirror", "purpose": "screen_optical", "resolution_m": 10,
             "stac_url": "https://stac.example/v1", "collection": "sentinel-2-c1-l2a", "max_scene_cloud_pct": 50}
    added = client.post("/satellites", json=other, headers=auth(people.admin)).json()
    assert added["active"] and added["switched_off"] == ["Sentinel-2 L2A"]  # one optical source screens at a time
    seen = client.get("/pipeline/satellites", headers=TOKEN).json()
    assert (seen["screen_optical"]["key"], seen["screen_optical"]["max_scene_cloud_pct"]) == ("test-optical", 50)
    back = client.patch(f"/satellites/{s2['id']}", json={"active": True}, headers=auth(people.admin)).json()
    assert back["active"] and back["switched_off"] == ["Test optical mirror"]
    # The radar check may be off: the screen then runs without it.
    radar = by_key(client, people.admin)["sentinel-1-rtc"]
    assert client.patch(f"/satellites/{radar['id']}", json={"active": False}, headers=auth(people.admin)).json()["active"] is False
    assert client.get("/pipeline/satellites", headers=TOKEN).json()["screen_radar"] is None


def test_a_sharper_image_is_priced_from_its_source_and_a_source_that_is_off_is_refused(client, db, people):
    admin = make_user(db, "admin", is_demo=False)
    data = {"language": "en", "what": "dumping", "lon": TG_LON, "lat": TG_LAT}
    ref = client.post("/citizen/reports", data={"data": json.dumps(data)}).json()["ref"]
    aid = db.scalar(select(CitizenReport).where(CitizenReport.ref == ref)).alert_id
    added = client.post("/satellites", json=PLANET, headers=auth(admin)).json()
    out = client.post(f"/alerts/{aid}/imagery-request", json={"provider": PLANET["key"]}, headers=auth(admin)).json()
    assert out["provider"] == PLANET["key"] and out["est_cost_usd"] == 25 * 40  # the smallest order, 25 sq km
    first_on = client.post(f"/alerts/{aid}/imagery-request", json={}, headers=auth(admin)).json()
    assert first_on["provider"] == "isro_nrsc" and first_on["est_cost_usd"] is None  # price on request
    detail = client.get(f"/alerts/{aid}", headers=auth(admin)).json()
    assert detail["imagery_requests"][0]["provider_name"] == PLANET["name"]
    client.patch(f"/satellites/{added['id']}", json={"active": False}, headers=auth(admin))
    off = client.post(f"/alerts/{aid}/imagery-request", json={"provider": PLANET["key"]}, headers=auth(admin))
    assert off.status_code == 422 and "is on" in off.text
    client.delete(f"/satellites/{added['id']}?reason=Test over", headers=auth(admin))
    kept = db.scalar(select(ImageryRequest).where(ImageryRequest.alert_id == aid, ImageryRequest.provider == PLANET["key"]))
    assert kept is not None  # a deleted source's requests keep its key
    assert client.get(f"/alerts/{aid}", headers=auth(admin)).json()["imagery_requests"][0]["provider_name"] == PLANET["key"]
