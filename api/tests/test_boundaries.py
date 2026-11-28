"""M1: boundary versions. Invariant 12 and "a superseded boundary stays retrievable"."""
import datetime as dt
import math

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.models import AuditLog, Boundary
from app.services import boundaries as bsvc
from tests.factories import auth, make_asset, make_user, square


def _area(db, boundary_id: int) -> float:
    return db.scalar(text("SELECT ST_Area(ST_Transform(geom, 32644)) FROM boundaries WHERE id = :i"), {"i": boundary_id})


@pytest.mark.parametrize("side_m,expected_width", [(450.0, 30), (200.0, 9)])
def test_first_version_derives_buffer_and_watch_ring(db, side_m, expected_width):
    asset = make_asset(db, cohort="B_FINAL", geometry=square(side_m=side_m))
    rows = {r["kind"]: r for r in bsvc.current_boundary_set(db, asset.id).values()}
    assert set(rows) == {"ftl", "buffer", "watch_ring"}
    assert {r["version"] for r in rows.values()} == {1}

    side = math.sqrt(_area(db, rows["ftl"]["id"]))
    w = expected_width
    buffer_expected = 4 * side * w + math.pi * w * w
    assert _area(db, rows["buffer"]["id"]) == pytest.approx(buffer_expected, rel=0.03)

    outer = w + 100
    ring_expected = (4 * side * outer + math.pi * outer**2) - buffer_expected
    assert _area(db, rows["watch_ring"]["id"]) == pytest.approx(ring_expected, rel=0.03)
    assert rows["buffer"]["derived_from_id"] == rows["ftl"]["id"]
    assert all(len(r["sha256"]) == 64 for r in rows.values())


def test_parcel_gets_watch_ring_and_no_buffer(db):
    asset = make_asset(db, cohort="A_RECOVERED", type="recovered_parcel", kind="parcel")
    assert set(bsvc.current_boundary_set(db, asset.id)) == {"parcel", "watch_ring"}


def test_superseded_boundary_stays_retrievable(db, client):
    asset = make_asset(db, cohort="D_UNNOTIFIED", valid_from=dt.date(2025, 1, 1))
    admin = make_user(db, "admin")
    resp = client.post(
        f"/assets/{asset.id}/boundaries",
        headers=auth(admin),
        json={
            "kind": "ftl",
            "status": "final_notification",
            "geometry": square(side_m=320),
            "source_name": "Test final notification",
            "notification_ref": "TEST/FINAL/1",
            "valid_from": "2026-01-01",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["version"] == 2
    assert resp.json()["cohort"] == "B_FINAL"

    features = client.get(f"/assets/{asset.id}/boundaries", headers=auth(admin)).json()["features"]
    by = {(f["properties"]["version"], f["properties"]["kind"]): f["properties"] for f in features}
    assert len(features) == 6
    old, new = by[(1, "ftl")], by[(2, "ftl")]
    assert old["status"] == "derived" and new["status"] == "final_notification"
    assert old["superseded_by_id"] == new["id"]
    assert new["supersedes_id"] == old["id"]
    assert old["effective_valid_to"] == "2026-01-01"
    assert old["valid_to"] is None  # never written back
    assert old["in_force"] is False and new["in_force"] is True

    # Point-in-time: the old version is the one in force before the new one starts.
    assert bsvc.primary_of(bsvc.boundary_set_at(db, asset.id, dt.date(2025, 6, 1)))["id"] == old["id"]
    assert bsvc.primary_of(bsvc.boundary_set_at(db, asset.id, dt.date(2026, 6, 1)))["id"] == new["id"]
    assert bsvc.boundary_set_at(db, asset.id, dt.date(2024, 6, 1)) == {}

    asset_view = client.get(f"/assets/{asset.id}", headers=auth(admin)).json()["properties"]
    assert asset_view["mode"] == "ACTION" and asset_view["boundary_version"] == 2


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE boundaries SET status = 'final_notification' WHERE id = :i",
        "UPDATE boundaries SET valid_to = '2030-01-01' WHERE id = :i",
        "UPDATE boundaries SET geom = ST_Multi(ST_Buffer(geom, 0.001)) WHERE id = :i",
        "DELETE FROM boundaries WHERE id = :i",
    ],
)
def test_invariant_12_boundary_rows_cannot_be_updated_or_deleted(db, statement):
    asset = make_asset(db)
    row = bsvc.primary_of(bsvc.current_boundary_set(db, asset.id))
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text(statement), {"i": row["id"]})
    db.rollback()


def test_invariant_12_orm_update_is_refused(db):
    asset = make_asset(db)
    row = db.scalar(select(Boundary).where(Boundary.asset_id == asset.id, Boundary.kind == "ftl"))
    row.status = "final_notification"
    with pytest.raises(DBAPIError, match="append-only"):
        db.flush()
    db.rollback()


def test_invariant_12_truncate_is_refused(db):
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text("TRUNCATE boundaries CASCADE"))
    db.rollback()


def test_insert_must_extend_the_newest_version(db):
    asset = make_asset(db)
    ftl = bsvc.primary_of(bsvc.current_boundary_set(db, asset.id))
    insert = text(
        "INSERT INTO boundaries (asset_id, version, kind, status, geom, source_name, valid_from, supersedes_id, sha256) "
        "SELECT asset_id, :v, kind, status, geom, 'x', valid_from, :sup, '' FROM boundaries WHERE id = :i"
    )
    # Each refused insert runs in its own savepoint, so the asset survives for the next one.
    with pytest.raises(DBAPIError, match="version"):
        with db.begin_nested():
            db.execute(insert, {"v": 5, "sup": ftl["id"], "i": ftl["id"]})
    with pytest.raises(DBAPIError, match="supersede"):
        with db.begin_nested():
            db.execute(insert, {"v": 2, "sup": None, "i": ftl["id"]})
    with pytest.raises(DBAPIError, match="duplicate key"):
        with db.begin_nested():
            db.execute(insert, {"v": 1, "sup": None, "i": ftl["id"]})
    assert db.scalar(text("SELECT count(*) FROM boundaries WHERE asset_id = :a"), {"a": asset.id}) == 3


def test_boundary_post_needs_admin_or_nodal_role(db, client):
    asset = make_asset(db)
    body = {"kind": "ftl", "status": "final_notification", "geometry": square(), "source_name": "x"}
    assert client.post(f"/assets/{asset.id}/boundaries", json=body).status_code == 401
    analyst = make_user(db, "senior_official")
    assert client.post(f"/assets/{asset.id}/boundaries", json=body, headers=auth(analyst)).status_code == 403


def test_boundary_post_rejects_invalid_geometry(db, client):
    asset = make_asset(db)
    admin = make_user(db, "admin")
    bowtie = {"type": "Polygon", "coordinates": [[[81.5, 14.5], [81.51, 14.51], [81.51, 14.5], [81.5, 14.51], [81.5, 14.5]]]}
    body = {"kind": "ftl", "status": "final_notification", "geometry": bowtie, "source_name": "x"}
    resp = client.post(f"/assets/{asset.id}/boundaries", json=body, headers=auth(admin))
    assert resp.status_code == 422


def test_boundary_post_is_audited(db, client):
    asset = make_asset(db)
    admin = make_user(db, "admin")
    body = {"kind": "ftl", "status": "final_notification", "geometry": square(side_m=310), "source_name": "Test"}
    assert client.post(f"/assets/{asset.id}/boundaries", json=body, headers=auth(admin)).status_code == 201
    row = db.scalar(
        select(AuditLog).where(AuditLog.action == "boundary.version_added", AuditLog.actor_id == admin.id)
    )
    assert row is not None and row.details["version"] == 2 and row.details["cohort_after"] == "B_FINAL"
