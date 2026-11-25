"""Locations the admin adds by hand, and starting or stopping their weekly watch (DECISIONS.md D-061).

Adding a location creates an asset with its first boundary version, exactly as a government record
would (app/sources/engine.py), so the weekly screen picks it up from `/pipeline/watchlist`.

- **An outline drawn on the screen is for watching only.** Its status is "derived", so its changes
  go to the watch list and never lead to field action (CONTEXT.md rule 2).
- **A confirmed status needs its reference:** the notification, recovery order or survey that
  fixes the line.
- **Planned categories are refused** until they are switched on in app/categories.yaml.
- **The same place is not added twice.** An outline that overlaps a watched location by half or
  more (intersection over union) is refused: add a boundary version to that location instead.

Removing a location stops its weekly watch. Nothing is deleted: its boundaries, weekly records,
incidents, documents and evidence packs stay, open incidents still need a decision, and the watch
can be resumed. Every start and stop is a row in `monitoring_changes`, with who, when and why.
"""
from __future__ import annotations

import datetime as dt
import json
import re

from shapely.geometry import box
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import categories
from app.audit import chain
from app.models import Asset, MonitoringChange, User
from app.rules import config as rules
from app.services import boundaries as bsvc
from app.sources import engine

ACRE_SQ_M = 4046.86
STATUSES = {
    # Lakes: the CONTEXT.md cohorts A to D. Land: A, E, F and D.
    "ftl": ("physically_marked", "final_notification", "preliminary_notification", "derived"),
    "parcel": ("physically_marked", "surveyed_agency", "survey_number_only", "derived"),
}
OPEN_STATES = ("OPEN", "UNDER_REVIEW")


class LocationError(ValueError):
    status_code = 422


class SamePlace(LocationError):
    status_code = 409

    def __init__(self, message: str, asset_id: int):
        super().__init__(message)
        self.asset_id = asset_id


def _measure(db: Session, geometry: dict) -> float:
    return float(db.scalar(
        text("SELECT ST_Area(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326), 32644))"),
        {"g": json.dumps(geometry)},
    ))


def _same_place(db: Session, geometry: dict, exclude: int | None) -> dict | None:
    row = db.execute(text(
        """
        WITH g AS (SELECT ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326), 32644) AS m)
        SELECT a.id, a.name,
               ST_Area(ST_Intersection(ST_Transform(b.geom, 32644), g.m))
                 / NULLIF(ST_Area(ST_Union(ST_Transform(b.geom, 32644), g.m)), 0) AS iou
        FROM assets a
        JOIN LATERAL (SELECT bv.geom FROM boundaries bv
                      WHERE bv.asset_id = a.id AND bv.kind IN ('ftl', 'parcel')
                      ORDER BY bv.version DESC LIMIT 1) b ON true
        CROSS JOIN g
        WHERE a.is_demo = false AND a.monitored AND a.id <> coalesce(CAST(:x AS bigint), 0)
          AND ST_Intersects(b.geom, ST_Transform(g.m, 4326))
        ORDER BY iou DESC NULLS LAST LIMIT 1
        """
    ), {"g": json.dumps(geometry), "x": exclude}).mappings().first()
    return dict(row) if row and row["iou"] is not None else None


def check_outline(db: Session, geometry: dict, *, exclude: int | None = None) -> dict:
    """Why an outline cannot be watched (LocationError), or its area and nearest watched neighbour."""
    try:
        geom = bsvc.to_multipolygon(geometry)
    except bsvc.BoundaryError as exc:
        raise LocationError(str(exc)) from exc
    if not box(*engine.settings()["real_bbox"]).contains(geom):
        raise LocationError("The outline lies outside Telangana")
    area = _measure(db, geometry)
    lim = categories.limits()
    if area < lim["min_area_sq_m"]:
        raise LocationError(
            f"The outline covers {area:,.0f} sq m. Below {lim['min_area_sq_m']:,} sq m the 10 m satellite images cannot watch it usefully"
        )
    if area > lim["max_area_sq_km"] * 1_000_000:
        raise LocationError(f"The outline covers {area / 1e6:,.1f} sq km. Split it into locations of {lim['max_area_sq_km']} sq km or less")
    near = _same_place(db, geometry, exclude)
    if near and near["iou"] >= lim["same_place_iou"]:
        raise SamePlace(f"This is the same place as {near['name']}, which is already watched. Add a boundary version to it instead", near["id"])
    return {"area_sq_m": round(area, 1), "area_acres": round(area / ACRE_SQ_M, 3), "nearest": near}


def _key(db: Session, name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "location"
    key, n = f"loc-{base}", 1
    while db.scalar(select(Asset.id).where(Asset.asset_key == key)) is not None:
        n += 1
        key = f"loc-{base}-{n}"
    return key


def add_location(
    db: Session,
    admin: User,
    *,
    type: str,
    name: str,
    district: str,
    geometry: dict,
    status: str,
    source_name: str,
    drawn: bool,
    name_te: str | None = None,
    mandal: str | None = None,
    village: str | None = None,
    survey_numbers: list[str] | None = None,
    custodian_agency: str | None = None,
    baseline_date: dt.date | None = None,
    notes: str | None = None,
    source_url: str | None = None,
    source_date: dt.date | None = None,
    notification_ref: str | None = None,
    at: dt.datetime,
) -> Asset:
    try:
        category = categories.category_of(type)
    except categories.CategoryError as exc:
        raise LocationError(str(exc)) from exc
    cat = categories.get(category)
    if cat["status"] == "intake":
        raise LocationError(f"{cat['label']['en']} are made from citizens' reports, not added by hand")
    if cat["status"] != categories.LIVE:
        raise LocationError(f"{cat['label']['en']} is planned and not watched yet. Still needed: {'; '.join(cat.get('needs', []))}")
    name, district, source_name = (name or "").strip(), (district or "").strip(), (source_name or "").strip()
    if not name:
        raise LocationError("Give the location a name")
    if not district:
        raise LocationError("Give the district, so the right officials are told")
    if not source_name:
        raise LocationError("Say where the outline comes from")
    kind = cat["primary_kind"]
    if status not in STATUSES[kind]:
        raise LocationError(f"A {cat['one']['en'].lower()} boundary can be: {', '.join(STATUSES[kind])}")
    if drawn and status != "derived":
        raise LocationError("An outline drawn on the screen is for watching only: its status must be 'derived'")
    if rules.is_confirmed_status(status) and not (notification_ref or "").strip():
        raise LocationError("A confirmed boundary needs the reference of the notification, order or survey that fixes it")
    baseline = baseline_date or rules.policy_cutoff_date()
    if baseline > at.date():
        raise LocationError("The baseline date cannot be in the future")
    if source_date and source_date > at.date():
        raise LocationError("The source date cannot be in the future")
    measured = check_outline(db, geometry)

    asset = Asset(
        asset_key=_key(db, name),
        name=name,
        name_te=(name_te or "").strip() or None,
        type=type,
        cohort=rules.cohort_for_status(status).value,
        district=district,
        mandal=(mandal or "").strip() or None,
        village=(village or "").strip() or None,
        survey_numbers=[s.strip() for s in survey_numbers or [] if s.strip()],
        area_acres=measured["area_acres"],
        custodian_agency=(custodian_agency or "").strip() or None,
        baseline_date=baseline,
        is_demo=False,
        notes=(notes or "").strip() or None,
        added_by=admin.id,
        added_at=at,
    )
    db.add(asset)
    db.flush()
    try:
        bsvc.add_version(
            db, asset, kind=kind, status=status, geometry=geometry, source_name=source_name, source_url=source_url,
            source_date=source_date, notification_ref=(notification_ref or "").strip() or None,
            valid_from=min(source_date or at.date(), at.date()), actor_id=admin.id, at=at,
        )
    except bsvc.BoundaryError as exc:
        raise LocationError(str(exc)) from exc
    db.add(MonitoringChange(asset_id=asset.id, monitored=True, reason=f"Added by hand. Outline: {source_name}", actor_id=admin.id, at=at))
    db.flush()
    chain.record(
        db, actor_id=admin.id, action="location.added", entity="asset", entity_id=asset.id, at=at,
        details={"asset_key": asset.asset_key, "type": type, "category": category, "status": status, "drawn": drawn,
                 "area_sq_m": measured["area_sq_m"], "district": asset.district, "mandal": asset.mandal},
    )
    return asset


def open_incidents(db: Session, asset_id: int) -> int:
    return int(db.scalar(text(
        "SELECT count(*) FROM alerts al JOIN candidates c ON c.id = al.candidate_id WHERE c.asset_id = :a AND al.state::text = ANY(:s)"
    ), {"a": asset_id, "s": list(OPEN_STATES)}) or 0)


def set_monitoring(db: Session, admin: User, asset: Asset, *, monitored: bool, reason: str, at: dt.datetime) -> dict:
    reason = (reason or "").strip()
    if len(reason) < 5:
        raise LocationError("Give the reason, so the record shows why")
    if asset.monitored == monitored:
        raise LocationError("The location is already watched" if monitored else "The location is already not watched")
    if monitored and not bsvc.primary_of(bsvc.current_boundary_set(db, asset.id)):
        raise LocationError("The location has no boundary in force. Add one before watching it again")
    db.add(MonitoringChange(asset_id=asset.id, monitored=monitored, reason=reason, actor_id=admin.id, at=at))
    db.flush()
    db.refresh(asset)
    still_open = open_incidents(db, asset.id)
    chain.record(
        db, actor_id=admin.id, action="location.watch_resumed" if monitored else "location.watch_stopped",
        entity="asset", entity_id=asset.id, at=at, details={"reason": reason, "open_incidents": still_open},
    )
    return {"asset_id": asset.id, "monitored": asset.monitored, "open_incidents": still_open}


def history(db: Session, asset_id: int) -> list[dict]:
    rows = db.execute(text(
        """
        SELECT m.id, m.monitored, m.reason, m.at, u.name AS actor
        FROM monitoring_changes m LEFT JOIN users u ON u.id = m.actor_id
        WHERE m.asset_id = :a ORDER BY m.at DESC, m.id DESC
        """
    ), {"a": asset_id}).mappings().all()
    return [dict(r) for r in rows]


def counts_by_type(db: Session, is_demo: bool | None = None) -> dict[str, int]:
    rows = db.execute(text(
        "SELECT type::text AS t, count(*) AS n FROM assets WHERE monitored AND (CAST(:d AS boolean) IS NULL OR is_demo = CAST(:d AS boolean)) GROUP BY 1"
    ), {"d": is_demo}).all()
    return {r[0]: int(r[1]) for r in rows}
