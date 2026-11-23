"""The pipeline's side of the API: watch list, screening runs with coverage, the base map, and the
real/demo split on the desk's lists (DECISIONS.md D-043)."""
import datetime as dt
import io
import json
import zipfile

import pytest
from sqlalchemy import text

from app.config import settings
from tests.factories import auth, make_asset, make_user

TOKEN = {"X-Pipeline-Token": "test-token"}
SHA = "a" * 64


@pytest.fixture(autouse=True)
def pipeline_on(monkeypatch):
    monkeypatch.setattr(settings, "pipeline_token", "test-token")


def _real(db, **kw):
    """A non-demo asset for these tests. It still sits in open sea, like every test asset."""
    asset = make_asset(db, cohort="D_UNNOTIFIED", **kw)
    asset.is_demo = False
    db.flush()
    return asset


def _run(asset_ids, **over):
    body = {
        "as_of": "2026-11-20",
        "rule_version": "detect-v0",
        "rules_sha256": SHA,
        "collection": "sentinel-2-c1-l2a",
        "started_at": "2026-11-20T10:00:00+00:00",
        "finished_at": "2026-11-20T10:05:00+00:00",
        "outcomes": {"created": 1},
        "assets": [
            {"asset_id": i, "status": "no_candidate", "looks": 40, "first_look": "2023-01-10", "last_look": "2026-11-13", "candidates": 0, "counts": {"looks": 40}}
            for i in asset_ids
        ],
    }
    body.update(over)
    return body


def test_watchlist_needs_the_pipeline_token(client):
    assert client.get("/pipeline/watchlist").status_code == 401
    assert client.get("/pipeline/watchlist", headers={"X-Pipeline-Token": "wrong"}).status_code == 401


def test_watchlist_lists_real_assets_only_with_boundary_set(client, db):
    real = _real(db, baseline=dt.date(2024, 7, 19))
    demo = make_asset(db)
    body = client.get("/pipeline/watchlist", headers=TOKEN).json()
    keys = {a["asset_key"] for a in body["assets"]}
    assert real.asset_key in keys and demo.asset_key not in keys
    mine = next(a for a in body["assets"] if a["asset_key"] == real.asset_key)
    assert mine["baseline_date"] == "2024-07-19"
    assert set(mine["boundaries"]) == {"ftl", "buffer", "watch_ring"}
    assert mine["boundaries"]["ftl"]["status"] == "derived"


def test_run_is_recorded_with_coverage_and_shown_on_assets(client, db):
    real = _real(db)
    resp = client.post("/pipeline/runs", json=_run([real.id]), headers=TOKEN)
    assert resp.status_code == 201, resp.text
    assert resp.json()["coverage"] == {"no_candidate": 1}
    analyst = make_user(db, "analyst")
    feats = client.get("/assets?dataset=real", headers=auth(analyst)).json()["features"]
    mine = next(f for f in feats if f["id"] == real.id)["properties"]
    assert mine["screen_status"] == "no_candidate"
    assert mine["screen_last_look"] == "2026-11-13" and mine["screen_looks"] == 40
    runs = client.get("/screening/runs", headers=auth(analyst)).json()["items"]
    assert runs[0]["coverage"] == {"no_candidate": 1} and runs[0]["looks"] == 40
    audit = db.execute(text("SELECT details FROM audit_log WHERE action = 'screen.run' ORDER BY id DESC LIMIT 1")).scalar_one()
    assert audit["rules_sha256"] == SHA


def test_run_refuses_a_look_after_as_of(client, db):
    """Invariant 10 at the API: a run cannot report a look acquired after its own as_of date."""
    real = _real(db)
    body = _run([real.id])
    body["assets"][0]["last_look"] = "2026-11-21"
    assert client.post("/pipeline/runs", json=body, headers=TOKEN).status_code == 422


def test_run_refuses_demo_or_unknown_assets(client, db):
    demo = make_asset(db)
    assert client.post("/pipeline/runs", json=_run([demo.id]), headers=TOKEN).status_code == 422
    assert client.post("/pipeline/runs", json=_run([987654321]), headers=TOKEN).status_code == 422


def test_screening_tables_are_append_only(client, db):
    real = _real(db)
    run_id = client.post("/pipeline/runs", json=_run([real.id]), headers=TOKEN).json()["run_id"]
    from sqlalchemy.exc import DBAPIError

    for sql in ("UPDATE screen_runs SET rule_version = 'x' WHERE id = :i", "UPDATE asset_screens SET status = 'candidate_found' WHERE run_id = :i", "DELETE FROM asset_screens WHERE run_id = :i"):
        with pytest.raises(DBAPIError, match="append-only"):
            with db.begin_nested():
                db.execute(text(sql), {"i": run_id})


def test_dataset_filter_keeps_real_and_demo_apart(client, db):
    real = _real(db)
    demo = make_asset(db)
    analyst = make_user(db, "analyst")
    real_ids = {f["id"] for f in client.get("/assets?dataset=real", headers=auth(analyst)).json()["features"]}
    demo_ids = {f["id"] for f in client.get("/assets?dataset=demo", headers=auth(analyst)).json()["features"]}
    assert real.id in real_ids and real.id not in demo_ids
    assert demo.id in demo_ids and demo.id not in real_ids
    for item in client.get("/alerts?dataset=real", headers=auth(analyst)).json()["items"]:
        assert item["is_demo"] is False


def _zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_basemap_upload_serves_tiles_and_refuses_other_files(client, db):
    meta = json.dumps({"bounds": [78.2, 17.2, 78.7, 17.6], "minzoom": 9, "maxzoom": 14, "scenes": []}).encode()
    ok = _zip({"meta.json": meta, "14/11745/7480.jpg": b"\xff\xd8jpegdata"})
    resp = client.post("/pipeline/basemap", files={"file": ("s2.zip", ok, "application/zip")}, headers=TOKEN)
    assert resp.status_code == 201 and resp.json()["tiles"] == 1
    assert client.get("/tiles/s2/14/11745/7480.jpg").content == b"\xff\xd8jpegdata"
    assert client.get("/tiles/s2/meta.json").json()["maxzoom"] == 14
    blank = client.get("/tiles/s2/14/1/1.jpg")
    assert blank.status_code == 200 and blank.headers["content-type"] == "image/jpeg"
    bad = _zip({"meta.json": meta, "../escape.jpg": b"x"})
    assert client.post("/pipeline/basemap", files={"file": ("s2.zip", bad, "application/zip")}, headers=TOKEN).status_code == 422
    assert client.post("/pipeline/basemap", files={"file": ("s2.zip", ok, "application/zip")}).status_code == 401


def test_ten_pixels_on_the_pipeline_grid_meet_the_minimum_area(db):
    """A 1,000 sq m candidate drawn on the 10 m UTM grid must not be refused for losing a fraction
    of a square metre in the lon/lat round trip (it happened on the first real screen)."""
    from app.services import ingest as ingest_svc
    from tests.factories import TEST_LAT, TEST_LON, candidate_in

    asset = make_asset(db, geometry=None)
    x, y = db.execute(text("SELECT ST_X(p), ST_Y(p) FROM ST_Transform(ST_SetSRID(ST_Point(:lon, :lat), 4326), 32644) AS p"), {"lon": TEST_LON, "lat": TEST_LAT}).one()
    x, y = round(x / 10) * 10, round(y / 10) * 10
    # 10 pixels, 999.99999999 sq m: exactly as the first real screen sent one
    strip = json.loads(db.scalar(text("SELECT ST_AsGeoJSON(ST_Transform(ST_MakeEnvelope(:x, :y, :x + 100, :y + 9.999999999, 32644), 4326), 15)"), {"x": x, "y": y}))
    out = ingest_svc.ingest(db, candidate_in(asset, geometry=strip), at=dt.datetime(2025, 6, 20, 6, tzinfo=dt.timezone.utc))
    assert out["outcome"] in {"created", "closed_by_legal_check"}
