"""The detection pipeline's side of the API (pipeline token, DECISIONS.md D-023).

- GET  /pipeline/watchlist   real assets with the boundary set in force, for `lp screen`
- POST /pipeline/runs        a screening run and, for every asset, its week: coverage, the week's
                             image and what changed (DECISIONS.md D-057)
- POST /pipeline/basemap     a zip of Sentinel-2 base-map tiles (`lp basemap`)

And the desk's read side:
- GET  /screening/runs       recent runs with their outcomes
"""
from __future__ import annotations

import datetime as dt
import io
import json
import re
import zipfile
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.db import db_guard, get_db
from app.models import Asset, AssetScreen, ScreenRun, User
from app.routers.candidates import pipeline_token
from app.security import current_user
from app.services import boundaries as bsvc
from app.services import weeks as weeks_svc
from app.storage import store

router = APIRouter(tags=["pipeline"])

Status = Literal["not_observed", "no_usable_look", "failed", "no_candidate", "candidate_found"]


@router.get("/pipeline/watchlist", dependencies=[Depends(pipeline_token)])
def watchlist(db: Session = Depends(get_db)) -> dict:
    """Every real asset with a boundary in force today. Demo assets are never screened."""
    out = []
    for asset in db.scalars(select(Asset).where(Asset.is_demo.is_(False)).order_by(Asset.id)):
        bset = bsvc.current_boundary_set(db, asset.id)
        if not bsvc.primary_of(bset):
            continue
        out.append(
            {
                "id": asset.id,
                "asset_key": asset.asset_key,
                "name": asset.name,
                "cohort": asset.cohort,
                "baseline_date": asset.baseline_date.isoformat(),
                "boundaries": {k: {"version": b["version"], "status": b["status"], "geometry": b["geometry"]} for k, b in bset.items()},
            }
        )
    return {"assets": out, "count": len(out)}


class ChangeIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    candidate_id: int
    alert_id: int | None = None
    outcome: str | None = None


class AssetScreenIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    asset_id: int
    status: Status
    looks: int = Field(ge=0)
    first_look: dt.date | None = None
    last_look: dt.date | None = None
    candidates: int = 0
    legacy_changes: int = 0
    counts: dict = {}
    # The week's image of the asset: its clearest latest look, boundary drawn (PNG, base64).
    image_png_b64: str | None = None
    image_date: dt.date | None = None
    image_scene_id: str | None = None
    # The changes this screen sent for the asset, with what ingest did with each.
    changes: list[ChangeIn] = []


class RunIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    as_of: dt.date
    rule_version: str
    rules_sha256: str = Field(min_length=64, max_length=64)
    collection: str
    started_at: dt.datetime
    finished_at: dt.datetime
    outcomes: dict = {}
    assets: list[AssetScreenIn]


@router.post("/pipeline/runs", status_code=201, dependencies=[Depends(pipeline_token)])
def record_run(body: RunIn, db: Session = Depends(get_db)) -> dict:
    if body.as_of > dt.date.today():
        raise HTTPException(422, "A run cannot be dated in the future")
    if any(a.last_look and a.last_look > body.as_of for a in body.assets):
        raise HTTPException(422, "A look acquired after the run's as_of date is not allowed (invariant 10)")
    if any(a.image_date and a.image_date > body.as_of for a in body.assets):
        raise HTTPException(422, "A weekly image acquired after the run's as_of date is not allowed (invariant 10)")
    known = set(db.scalars(select(Asset.id).where(Asset.is_demo.is_(False))))
    unknown = sorted({a.asset_id for a in body.assets} - known)
    if unknown:
        raise HTTPException(422, f"Not real watched assets: {unknown}")
    with db_guard(db):
        run = ScreenRun(
            as_of=body.as_of,
            rule_version=body.rule_version,
            rules_sha256=body.rules_sha256,
            collection=body.collection,
            started_at=body.started_at,
            finished_at=body.finished_at,
            assets_total=len(body.assets),
            outcomes=body.outcomes,
        )
        db.add(run)
        db.flush()
        week = weeks_svc.iso_week(body.as_of)
        for a in body.assets:
            asset = db.get(Asset, a.asset_id)
            try:
                image = weeks_svc.store_image(asset, body.as_of, a.image_png_b64)
                if a.changes:
                    changes = weeks_svc.change_entries(db, asset.id, [c.model_dump() for c in a.changes])
                elif a.status == "candidate_found":
                    changes = weeks_svc.changes_since(db, asset.id, body.started_at)
                else:
                    changes = []
            except ValueError as exc:
                db.rollback()
                raise HTTPException(422, f"Asset {a.asset_id}: {exc}") from exc
            fields = a.model_dump(exclude={"image_png_b64", "changes"})
            db.add(AssetScreen(run_id=run.id, week=week, image_key=image, changes=changes, **fields))
        statuses: dict[str, int] = {}
        for a in body.assets:
            statuses[a.status] = statuses.get(a.status, 0) + 1
        chain.record(
            db,
            actor_id=None,
            action="screen.run",
            entity="screen_run",
            entity_id=run.id,
            details={"as_of": body.as_of.isoformat(), "rule_version": body.rule_version, "rules_sha256": body.rules_sha256, "coverage": statuses, "outcomes": body.outcomes},
        )
        db.commit()
    return {"run_id": run.id, "assets": len(body.assets), "coverage": statuses}


_TILE = re.compile(r"^(\d{1,2})/(\d{1,7})/(\d{1,7})\.(jpg|png)$")


@router.post("/pipeline/basemap", status_code=201, dependencies=[Depends(pipeline_token)])
async def upload_basemap(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    """Replace the Sentinel-2 base map with the tiles in a zip (z/x/y.jpg plus meta.json)."""
    data = await file.read()
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise HTTPException(422, "Not a zip file") from exc
    names = zf.namelist()
    if "meta.json" not in names:
        raise HTTPException(422, "meta.json is missing")
    meta = json.loads(zf.read("meta.json"))
    tiles = 0
    for name in names:
        if name == "meta.json" or name.endswith("/"):
            continue
        if not _TILE.match(name):
            raise HTTPException(422, f"Unexpected file in the zip: {name}")
        store.put_object(f"tiles/s2/{name}", zf.read(name))
        tiles += 1
    store.put_object("tiles/s2/meta.json", json.dumps(meta).encode())
    chain.record(db, actor_id=None, action="basemap.uploaded", entity="basemap", entity_id="s2", details={"tiles": tiles, **{k: meta.get(k) for k in ("scenes", "bounds", "minzoom", "maxzoom")}})
    db.commit()
    return {"tiles": tiles}


@router.get("/screening/runs")
def list_runs(limit: int = 10, dataset: Literal["demo", "real"] = "real", user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.execute(
        text(
            """
            SELECT r.id, r.as_of, r.rule_version, r.rules_sha256, r.collection, r.started_at, r.finished_at,
                   r.assets_total, r.outcomes,
                   (SELECT jsonb_object_agg(status, n) FROM (SELECT status, count(*) AS n FROM asset_screens s
                     WHERE s.run_id = r.id GROUP BY status) x) AS coverage,
                   (SELECT sum(looks) FROM asset_screens s WHERE s.run_id = r.id) AS looks
            FROM screen_runs r WHERE r.is_demo = :demo ORDER BY r.as_of DESC, r.id DESC LIMIT :n
            """
        ),
        {"n": max(1, min(limit, 100)), "demo": dataset == "demo"},
    ).mappings().all()
    chain.record(db, actor_id=user.id, action="view.screening_runs", entity="screen_run", details={"count": len(rows)})
    db.commit()
    return {"items": [dict(r) for r in rows]}
