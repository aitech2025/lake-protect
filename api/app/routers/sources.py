"""Government sources and the asset creation engine (docs/asset-engine.md).

GET  /sources                   each connector, its data contract and whether files are waiting
POST /sources/{name}/runs       run the engine; a dry run by default (admin only)
GET  /sources/runs              recent applied runs, with what they did to each record
GET  /assets/{id}/register      where an asset's record came from, and the survey numbers it touches
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.db import db_guard, get_db
from app.enums import Role
from app.models import Asset, ImportRun, User
from app.security import require_roles
from app.sources import engine
from app.sources.base import AgreementRequired, NotConfigured, SourceError
from app.sources.connectors import CONNECTORS
from app.sources.transports import SampleTransport

router = APIRouter(tags=["sources"])

READ_ROLES = (Role.admin, Role.viewer)
RUN_ROLES = (Role.admin,)
REGISTER_ROLES = (Role.admin, Role.viewer)


def _run_summary(run: ImportRun | None, with_items: bool = False) -> dict | None:
    if run is None:
        return None
    out = {
        "id": run.id, "connector": run.connector, "transport": run.transport, "is_sample": run.is_sample,
        "started_at": run.started_at, "finished_at": run.finished_at, "actor_id": run.actor_id,
        "snapshot_ids": run.snapshot_ids, "counts": run.counts,
    }
    if with_items:
        out["items"] = run.items
    return out


@router.get("/sources")
def list_sources(user: User = Depends(require_roles(*READ_ROLES)), db: Session = Depends(get_db)) -> dict:
    cfg = engine.settings()
    items = []
    for c in CONNECTORS.values():
        api = engine.transport_for(c.name, "api")
        drop = engine.transport_for(c.name, "file_drop")
        last = db.scalar(select(ImportRun).where(ImportRun.connector == c.name).order_by(ImportRun.id.desc()).limit(1))
        items.append(c.describe() | {
            "agreement_ref": api.agreement_ref,
            "api_configured": api.configured,
            "drop_folder": f"{cfg['drop_root']}/{c.name}",
            "files_waiting": drop.waiting(c),
            "sample_available": bool(SampleTransport(c.name).waiting(c)),
            "last_run": _run_summary(last),
        })
    chain.record(db, actor_id=user.id, action="view.sources", entity="source", details={"count": len(items)})
    db.commit()
    return {"items": items}


class RunIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transport: Literal["file_drop", "sample", "api"] = "sample"
    dry_run: bool = True


@router.post("/sources/{name}/runs")
def start_run(name: str, body: RunIn, user: User = Depends(require_roles(*RUN_ROLES)), db: Session = Depends(get_db)) -> dict:
    if name not in CONNECTORS:
        raise HTTPException(404, "Unknown source")
    if body.transport == "sample" and not body.dry_run:
        # GeoGuard holds real data only (D-065): the fictional sample registers are previews.
        raise HTTPException(422, "The sample register is a preview only: GeoGuard holds real data only")
    with db_guard(db):
        try:
            return engine.run(db, name, transport=body.transport, dry_run=body.dry_run, actor_id=user.id)
        except (AgreementRequired, NotConfigured) as exc:
            db.rollback()
            raise HTTPException(409, str(exc)) from exc
        except SourceError as exc:
            db.rollback()
            raise HTTPException(422, str(exc)) from exc


@router.get("/sources/runs")
def list_runs(limit: int = Query(20, ge=1, le=100), user: User = Depends(require_roles(*READ_ROLES)),
              db: Session = Depends(get_db)) -> dict:
    runs = db.scalars(select(ImportRun).order_by(ImportRun.id.desc()).limit(limit)).all()
    chain.record(db, actor_id=user.id, action="view.import_runs", entity="import_run", details={"count": len(runs)})
    db.commit()
    return {"items": [_run_summary(r, with_items=True) for r in runs]}


_LINKS_SQL = text(
    """
    SELECT l.connector, regexp_replace(l.external_id, '^sample:', '') AS external_id, l.matched_by, l.linked_at,
           s.agency, s.file_name, s.source_date, s.sha256, s.transport
    FROM asset_source_links l JOIN source_snapshots s ON s.id = l.snapshot_id
    WHERE l.asset_id = :a ORDER BY l.id
    """
)

_PRIMARY_SOURCE_SQL = text(
    """
    SELECT b.id AS boundary_id, b.version, b.kind::text AS kind, b.status::text AS status, b.source_name,
           b.positional_accuracy_m, s.connector, s.agency, s.file_name, s.sha256, s.source_date, s.reference
    FROM boundaries b LEFT JOIN source_snapshots s ON s.id = b.source_snapshot_id
    WHERE b.asset_id = :a AND b.kind IN ('ftl', 'parcel') ORDER BY b.version DESC LIMIT 1
    """
)

# Parcels of the newest snapshot per village that overlap the asset's newest boundary set.
_PARCELS_SQL = text(
    """
    WITH v AS (SELECT max(version) AS v FROM boundaries WHERE asset_id = :a),
    z AS (SELECT b.kind::text AS kind, ST_Transform(b.geom, 32644) AS m
          FROM boundaries b, v WHERE b.asset_id = :a AND b.version = v.v),
    prim AS (SELECT ST_Union(m) AS m FROM z WHERE kind IN ('ftl', 'parcel')),
    buf AS (SELECT ST_Union(m) AS m FROM z WHERE kind = 'buffer'),
    allz AS (SELECT ST_Union(m) AS m FROM z)
    SELECT p.district, p.mandal, p.village, p.survey_no, p.sub_division, p.bhudhaar, p.land_category,
           p.recorded_category, p.extent_acres, p.positional_accuracy_m,
           round(ST_Area(ST_Intersection(ST_Transform(p.geom, 32644), prim.m))::numeric, 1) AS in_boundary_sq_m,
           round(COALESCE(ST_Area(ST_Intersection(ST_Transform(p.geom, 32644), buf.m)), 0)::numeric, 1) AS in_buffer_sq_m
    FROM land_parcels_current p, allz, prim, buf
    WHERE p.is_sample = :demo
      AND ST_Intersects(ST_Transform(p.geom, 32644), allz.m)
      AND NOT ST_Touches(ST_Transform(p.geom, 32644), allz.m)
    ORDER BY p.village, p.survey_no, p.sub_division
    """
)


@router.get("/assets/{asset_id}/register")
def asset_register(asset_id: int, user: User = Depends(require_roles(*REGISTER_ROLES)), db: Session = Depends(get_db)) -> dict:
    """The asset's place in the boundary register: sources, crosswalk IDs and survey-number parcels.

    Parcels carry land category and extent only. No owner name is held anywhere (CONTEXT.md 17.10).
    """
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(404, "Asset not found")
    links = [dict(r) for r in db.execute(_LINKS_SQL, {"a": asset_id}).mappings()]
    primary = db.execute(_PRIMARY_SOURCE_SQL, {"a": asset_id}).mappings().first()
    parcels = []
    core_sq_m = 0.0
    for r in db.execute(_PARCELS_SQL, {"a": asset_id, "demo": asset.is_demo}).mappings():
        p = dict(r)
        p["in_boundary_sq_m"] = float(p["in_boundary_sq_m"] or 0)
        p["in_buffer_sq_m"] = float(p["in_buffer_sq_m"] or 0)
        p["zone"] = "inside" if p["in_boundary_sq_m"] > 0 else "buffer" if p["in_buffer_sq_m"] > 0 else "watch_ring"
        p["core"] = p["land_category"] in ("tank", "shikam") and p["in_boundary_sq_m"] > 0
        if p["core"]:
            core_sq_m += p["in_boundary_sq_m"]
        parcels.append(p)
    categories: dict[str, int] = {}
    for p in parcels:
        categories[p["land_category"]] = categories.get(p["land_category"], 0) + 1
    chain.record(db, actor_id=user.id, action="view.asset_register", entity="asset", entity_id=asset_id)
    db.commit()
    return {
        "asset_id": asset_id,
        "asset_key": asset.asset_key,
        "is_demo": asset.is_demo,
        "boundary_source": dict(primary) if primary else None,
        "links": links,
        "parcels": parcels,
        "parcel_categories": categories,
        "core_area_sq_m": round(core_sq_m, 1),
    }
