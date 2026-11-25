"""M1: real assets load with their source and status, and are never demo data."""
import json

import pytest
from shapely.geometry import box, shape
from sqlalchemy import func, select

from app.config import settings
from app.models import Asset, Boundary
from app.seed import real_assets
from tests.factories import auth, make_user

ASSET_FILE = settings.data_dir / "assets.geojson"
ORR_BBOX = box(78.22, 17.20, 78.72, 17.62)


@pytest.fixture(scope="module")
def collection():
    return json.loads(ASSET_FILE.read_text(encoding="utf-8"))


def test_asset_file_has_real_sourced_features(collection):
    assert collection["type"] == "FeatureCollection"
    assert "OpenStreetMap" in collection["source"]["licence"]
    assert len(collection["features"]) > 0
    keys = set()
    for f in collection["features"]:
        p, b = f["properties"], f["properties"]["boundary"]
        assert p["asset_key"] not in keys
        keys.add(p["asset_key"])
        assert p["is_demo"] is False
        assert b["status"] == "derived" and p["cohort"] == "D_UNNOTIFIED"
        assert b["source_name"] and b["source_date"]
        assert b["source_url"].startswith("https://www.openstreetmap.org/")
        geom = shape(f["geometry"])
        assert geom.is_valid and not geom.is_empty
        assert ORR_BBOX.intersects(geom)


def test_real_assets_load_once_and_reload_unchanged(db, client, collection):
    n = len(collection["features"])
    assert real_assets.load(db, ASSET_FILE) == {"created": n, "new_versions": 0, "unchanged": 0}
    assert real_assets.load(db, ASSET_FILE) == {"created": 0, "new_versions": 0, "unchanged": n}

    keys = [f["properties"]["asset_key"] for f in collection["features"]]
    assets = db.scalars(select(Asset).where(Asset.asset_key.in_(keys))).all()
    assert len(assets) == n and not any(a.is_demo for a in assets)
    rows = db.scalar(select(func.count()).select_from(Boundary).where(Boundary.asset_id.in_([a.id for a in assets])))
    assert rows == 3 * n  # ftl, buffer and watch ring, version 1

    analyst = make_user(db, "viewer")
    listed = {
        f["properties"]["asset_key"]: f["properties"]
        for f in client.get("/assets", headers=auth(analyst)).json()["features"]
    }
    for key in keys:
        assert listed[key]["mode"] == "WATCH"
        assert listed[key]["boundary_status"] == "derived"
        assert listed[key]["boundary_confirmed"] is False
        assert "OpenStreetMap" in listed[key]["boundary_source"]


def test_every_real_lake_has_a_district_and_mandal_from_osm(collection):
    """D-060: placed by OpenStreetMap boundaries, and marked as not the revenue record."""
    assert "areas" in collection["source"]
    for f in collection["features"]:
        p = f["properties"]
        assert p["district"] and p["mandal"], p["asset_key"]
        assert "not the revenue record" in p["area_source"]


def test_a_changed_area_is_updated_and_logged(db, tmp_path, collection):
    from app.models import AuditLog

    real_assets.load(db, ASSET_FILE)
    changed = json.loads(json.dumps(collection))
    first = changed["features"][0]["properties"]
    first["mandal"] = "Another mandal"
    path = tmp_path / "assets.geojson"
    path.write_text(json.dumps(changed), encoding="utf-8")
    out = real_assets.load(db, path)
    assert out["area_changed"] == 1
    asset = db.scalar(select(Asset).where(Asset.asset_key == first["asset_key"]))
    assert asset.mandal == "Another mandal"
    log = db.scalar(select(AuditLog).where(AuditLog.action == "asset.area_changed"))
    assert log.details["to"]["mandal"] == "Another mandal"
