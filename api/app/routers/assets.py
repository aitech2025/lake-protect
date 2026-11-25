"""Assets and boundary versions (section 9.5), and the locations the admin adds or stops watching (D-061).

- GET  /categories                    the kinds of land watched now and planned, with counts
- POST /assets                        admin: add a location with its first boundary
- POST /assets/outline-check          admin: area and overlap of an outline, before adding it
- POST /assets/{id}/monitoring        admin: stop or resume the weekly watch, with a reason
- GET  /assets/{id}/monitoring        who started or stopped the watch, when and why
"""
from __future__ import annotations

import datetime as dt
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import categories
from app.audit import chain
from app.clock import utcnow
from app.db import db_guard, get_db
from app.enums import BoundaryStatus, Role
from app.models import Asset, User
from app.rules import config as rules
from app.security import current_user, require_roles
from app.services import boundaries as bsvc
from app.services import locations as loc_svc
from app.services import weeks as weeks_svc
from app.storage import store

router = APIRouter(tags=["assets"])

_LIST_SQL = text(
    """
    SELECT a.id, a.asset_key, a.name, a.name_te, a.type::text AS type, a.cohort::text AS cohort,
           a.district, a.mandal, a.village, a.survey_numbers, a.area_acres, a.custodian_agency,
           a.has_cctv, a.baseline_date, a.is_demo, a.notes, a.monitored, a.added_at,
           (SELECT u.name FROM users u WHERE u.id = a.added_by) AS added_by,
           (SELECT m.at FROM monitoring_changes m WHERE m.asset_id = a.id ORDER BY m.at DESC, m.id DESC LIMIT 1) AS monitoring_changed_at,
           (SELECT m.reason FROM monitoring_changes m WHERE m.asset_id = a.id ORDER BY m.at DESC, m.id DESC LIMIT 1) AS monitoring_reason,
           b.id AS boundary_id, b.version AS boundary_version, b.kind::text AS boundary_kind,
           b.status::text AS boundary_status, b.source_name AS boundary_source,
           ST_AsGeoJSON(b.geom)::json AS geometry,
           sc.status AS screen_status, sc.looks AS screen_looks, sc.first_look AS screen_first_look,
           sc.last_look AS screen_last_look, sc.candidates AS screen_candidates, sc.as_of AS screened_as_of,
           sc.rule_version AS screen_rule_version
    FROM assets a
    LEFT JOIN LATERAL (
        SELECT bv.* FROM boundary_versions bv
        WHERE bv.asset_id = a.id AND bv.kind IN ('ftl', 'parcel')
          AND bv.valid_from <= CURRENT_DATE
          AND (bv.effective_valid_to IS NULL OR bv.effective_valid_to > CURRENT_DATE)
        ORDER BY bv.version DESC LIMIT 1
    ) b ON true
    LEFT JOIN LATERAL (
        SELECT s.status, s.looks, s.first_look, s.last_look, s.candidates, r.as_of, r.rule_version
        FROM asset_screens s JOIN screen_runs r ON r.id = s.run_id
        WHERE s.asset_id = a.id ORDER BY s.run_id DESC LIMIT 1
    ) sc ON true
    WHERE (CAST(:area_user AS bigint) IS NULL
           OR ST_Intersects(b.geom, (SELECT u.area_geom FROM users u WHERE u.id = CAST(:area_user AS bigint))))
      AND (CAST(:asset_id AS bigint) IS NULL OR a.id = CAST(:asset_id AS bigint))
      AND (CAST(:demo AS boolean) IS NULL OR a.is_demo = CAST(:demo AS boolean))
    ORDER BY a.is_demo DESC, a.name
    """
)


def _feature(row: dict) -> dict:
    props = {k: v for k, v in row.items() if k != "geometry"}
    props["mode"] = rules.mode_for_cohort(row["cohort"]).value
    props["category"] = categories.category_of(row["type"])
    props["boundary_confirmed"] = bool(row["boundary_status"]) and rules.is_confirmed_status(row["boundary_status"])
    props["area_acres"] = float(row["area_acres"]) if row["area_acres"] is not None else None
    return {"type": "Feature", "id": row["id"], "geometry": row["geometry"], "properties": props}


def _area_user(user: User) -> int | None:
    # Every role sees every asset since the roles were reduced to admin and viewer (D-057).
    return None


def _demo_flag(dataset: str | None) -> bool | None:
    return None if dataset is None else dataset == "demo"


@router.get("/assets")
def list_assets(dataset: Literal["demo", "real"] | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """`dataset` keeps real lakes and the fictional demo world apart (section 13, demo data rules)."""
    rows = db.execute(_LIST_SQL, {"area_user": _area_user(user), "asset_id": None, "demo": _demo_flag(dataset)}).mappings().all()
    chain.record(db, actor_id=user.id, action="view.assets", entity="asset", details={"count": len(rows)})
    db.commit()
    return {"type": "FeatureCollection", "features": [_feature(dict(r)) for r in rows]}


@router.get("/assets/{asset_id}")
def get_asset(asset_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    row = db.execute(_LIST_SQL, {"area_user": _area_user(user), "asset_id": asset_id, "demo": None}).mappings().first()
    if row is None:
        raise HTTPException(404, "Asset not found")
    chain.record(db, actor_id=user.id, action="view.asset", entity="asset", entity_id=asset_id)
    db.commit()
    return _feature(dict(row))


@router.get("/assets/{asset_id}/boundaries")
def list_boundaries(asset_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    if db.execute(_LIST_SQL, {"area_user": _area_user(user), "asset_id": asset_id, "demo": None}).first() is None:
        raise HTTPException(404, "Asset not found")
    versions = bsvc.all_versions(db, asset_id)
    current = {r["id"] for r in bsvc.current_boundary_set(db, asset_id).values()}
    features = []
    for v in versions:
        props = {k: val for k, val in v.items() if k != "geometry"}
        props["in_force"] = v["id"] in current
        props["area_sq_m"] = float(v["area_sq_m"])
        features.append({"type": "Feature", "id": v["id"], "geometry": v["geometry"], "properties": props})
    chain.record(db, actor_id=user.id, action="view.boundaries", entity="asset", entity_id=asset_id)
    db.commit()
    return {"type": "FeatureCollection", "asset_id": asset_id, "features": features}


@router.get("/categories")
def list_categories(dataset: Literal["demo", "real"] | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """The kinds of land GeoGuard watches now, and those planned (app/categories.yaml)."""
    return {"items": categories.as_list(loc_svc.counts_by_type(db, _demo_flag(dataset))), "limits": categories.limits(),
            "policy_cutoff_date": rules.policy_cutoff_date().isoformat()}


class OutlineIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    geometry: dict


@router.post("/assets/outline-check")
def outline_check(body: OutlineIn, user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> dict:
    """The outline's area, or why it cannot be watched, before the admin adds it."""
    try:
        out = loc_svc.check_outline(db, body.geometry)
    except loc_svc.LocationError as exc:
        return {"ok": False, "reason": str(exc), "asset_id": getattr(exc, "asset_id", None)}
    return {"ok": True, **{k: v for k, v in out.items() if k != "nearest"}}


class LocationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str
    name: str
    name_te: str | None = None
    district: str
    mandal: str | None = None
    village: str | None = None
    survey_numbers: list[str] = []
    custodian_agency: str | None = None
    baseline_date: dt.date | None = None
    notes: str | None = None
    geometry: dict
    drawn: bool
    status: BoundaryStatus
    source_name: str
    source_url: str | None = None
    source_date: dt.date | None = None
    notification_ref: str | None = None


@router.post("/assets", status_code=201)
def add_location(body: LocationIn, user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> dict:
    """A new location to watch, real data only. The next weekly screen includes it."""
    with db_guard(db):
        try:
            with db.begin_nested():  # a refusal leaves nothing behind
                asset = loc_svc.add_location(db, user, **body.model_dump(exclude={"status"}), status=body.status.value, at=utcnow())
        except loc_svc.LocationError as exc:
            detail = {"message": str(exc), "asset_id": exc.asset_id} if isinstance(exc, loc_svc.SamePlace) else str(exc)
            raise HTTPException(exc.status_code, detail) from exc
        db.commit()
    row = db.execute(_LIST_SQL, {"area_user": None, "asset_id": asset.id, "demo": None}).mappings().first()
    return _feature(dict(row))


class MonitoringIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    monitored: bool
    reason: str


@router.post("/assets/{asset_id}/monitoring")
def set_monitoring(asset_id: int, body: MonitoringIn, user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> dict:
    """Stop or resume the weekly watch. Nothing is deleted, and open incidents stay open."""
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(404, "Asset not found")
    with db_guard(db):
        try:
            with db.begin_nested():
                out = loc_svc.set_monitoring(db, user, asset, monitored=body.monitored, reason=body.reason, at=utcnow())
        except loc_svc.LocationError as exc:
            raise HTTPException(exc.status_code, str(exc)) from exc
        db.commit()
    return out


@router.get("/assets/{asset_id}/monitoring")
def monitoring_history(asset_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    if db.get(Asset, asset_id) is None:
        raise HTTPException(404, "Asset not found")
    items = loc_svc.history(db, asset_id)
    chain.record(db, actor_id=user.id, action="view.monitoring", entity="asset", entity_id=asset_id, details={"count": len(items)})
    db.commit()
    return {"asset_id": asset_id, "items": items}


class BoundaryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["ftl", "parcel"]
    status: BoundaryStatus
    geometry: dict
    source_name: str
    source_url: str | None = None
    source_date: dt.date | None = None
    notification_ref: str | None = None
    certified_by: str | None = None
    valid_from: dt.date | None = None


@router.post("/assets/{asset_id}/boundaries", status_code=201)
def add_boundary(
    asset_id: int,
    body: BoundaryIn,
    user: User = Depends(require_roles(Role.admin)),
    db: Session = Depends(get_db),
) -> dict:
    """New version, never an update."""
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(404, "Asset not found")
    if not body.source_name.strip():
        raise HTTPException(422, "Every boundary needs its source")
    with db_guard(db):
        try:
            rows = bsvc.add_version(db, asset, actor_id=user.id, **body.model_dump(mode="python") | {"status": body.status.value})
        except bsvc.BoundaryError as exc:
            raise HTTPException(422, str(exc)) from exc
        db.commit()
    return {
        "asset_id": asset_id,
        "cohort": asset.cohort,
        "version": rows[0].version,
        "boundaries": [{"id": r.id, "kind": r.kind, "version": r.version, "status": r.status, "sha256": r.sha256} for r in rows],
    }


@router.get("/assets/{asset_id}/weeks")
def asset_weeks(asset_id: int, limit: int = Query(26, ge=1, le=260), user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """The asset week by week: seen or not, the week's image, and what changed (D-057)."""
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(404, "Asset not found")
    items = weeks_svc.weeks_for_asset(db, asset_id, limit)
    chain.record(db, actor_id=user.id, action="view.asset_weeks", entity="asset", entity_id=asset_id, details={"weeks": len(items)})
    db.commit()
    return {"asset_id": asset_id, "asset_key": asset.asset_key, "is_demo": asset.is_demo, "items": items}


@router.get("/assets/{asset_id}/weeks/{screen_id}/image")
def asset_week_image(asset_id: int, screen_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    key = weeks_svc.image_key(db, asset_id, screen_id)
    if not key or store.head_object(key) is None:
        raise HTTPException(404, "No image for this week")
    chain.record(db, actor_id=user.id, action="view.week_image", entity="asset", entity_id=asset_id, details={"screen_id": screen_id})
    db.commit()
    return Response(store.get_object(key), media_type="image/png", headers={"Cache-Control": "private, max-age=86400"})
