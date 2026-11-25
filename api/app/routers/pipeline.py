"""The detection pipeline's side of the API (pipeline token, DECISIONS.md D-023).

- GET  /pipeline/watchlist   real assets being watched, with the boundary set in force, for `lp screen`
- POST /pipeline/runs        a screening run and, for every asset, its week: coverage, the week's
                             image and what changed (DECISIONS.md D-057). Then the weekly digest
                             goes to every official and the admin (D-059).
- POST /pipeline/basemap     a zip of Sentinel-2 base-map tiles (`lp basemap`)
- GET  /pipeline/reviews     citizen incidents waiting for their satellite review (`lp review-reports`, D-063)
- POST /pipeline/reviews/{id}  the review's result: what the newest images show at the reported place

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
from app.citizen import service as citizen
from app.clock import utcnow
from app.db import db_guard, get_db
from app.models import Asset, AssetScreen, ScreenRun, User
from app.notify import service as notify
from app.routers.candidates import pipeline_token
from app.security import current_user
from app.services import boundaries as bsvc
from app.services import weeks as weeks_svc
from app.storage import store

router = APIRouter(tags=["pipeline"])

Status = Literal["not_observed", "no_usable_look", "failed", "no_candidate", "candidate_found"]


@router.get("/pipeline/watchlist", dependencies=[Depends(pipeline_token)])
def watchlist(db: Session = Depends(get_db)) -> dict:
    """Every real asset being watched, with a boundary in force today. Demo assets are never screened,
    and a location whose watch the admin stopped is left out (D-061)."""
    out = []
    for asset in db.scalars(select(Asset).where(Asset.is_demo.is_(False), Asset.monitored.is_(True)).order_by(Asset.id)):
        bset = bsvc.current_boundary_set(db, asset.id)
        if not bsvc.primary_of(bset):
            continue
        out.append(
            {
                "id": asset.id,
                "asset_key": asset.asset_key,
                "name": asset.name,
                "cohort": asset.cohort,
                "type": asset.type,
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
    # After the run is safely stored: the week's digest, once per person per week. It never fails the
    # run, or the pipeline would send the run again; the admin can send it from the Officials page.
    try:
        digests = notify.send_digests(db, week, at=utcnow())["sent"]
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        digests = 0
        chain.record(db, actor_id=None, action="notify.digest_failed", entity="screen_run", entity_id=run.id,
                     details={"week": week, "error": type(exc).__name__})
        db.commit()
    # Citizens whose reported place was seen clearly, with no change, are told (D-062). Best effort too.
    try:
        checked = citizen.on_screen_stored(db, run.id, utcnow())
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        checked = 0
        chain.record(db, actor_id=None, action="citizen.screen_update_failed", entity="screen_run", entity_id=run.id,
                     details={"error": type(exc).__name__})
        db.commit()
    return {"run_id": run.id, "assets": len(body.assets), "coverage": statuses, "digests": digests, "citizen_reports_checked": checked}


@router.get("/pipeline/reviews", dependencies=[Depends(pipeline_token)])
def pending_reviews(db: Session = Depends(get_db)) -> dict:
    """Real citizen incidents waiting for a satellite look: the place, its location and boundaries."""
    from app.citizen import incident
    from app.models import Alert, Candidate, CitizenReport

    out = []
    for rv in incident.pending(db):
        alert = db.get(Alert, rv.alert_id)
        cand = db.get(Candidate, alert.candidate_id)
        asset = db.get(Asset, cand.asset_id)
        report = db.get(CitizenReport, alert.report_id)
        lon, lat = db.execute(text("SELECT ST_X(geom), ST_Y(geom) FROM citizen_reports WHERE id = :i"), {"i": report.id}).one()
        bset = bsvc.current_boundary_set(db, asset.id)
        out.append({
            "id": rv.id, "alert_id": alert.id, "code": alert.code, "ref": report.ref, "lon": lon, "lat": lat,
            "reported_at": report.created_at.isoformat(), "attempts": rv.attempts, "kind": rv.kind,
            "look_date": rv.look_date.isoformat() if rv.look_date else None,
            "asset": {"id": asset.id, "asset_key": asset.asset_key, "name": asset.name, "baseline_date": asset.baseline_date.isoformat(),
                      "boundaries": {k: {"version": b["version"], "status": b["status"], "geometry": b["geometry"]} for k, b in bset.items()}},
        })
    return {"reviews": out, "count": len(out)}


class SceneIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    sensor: str
    scene_id: str
    acquired_at: dt.datetime
    cloud_pct: float | None = None
    stac_href: str | None = None
    licence_notice: str | None = None


class ChangeSeenIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    change_type: str
    area_sq_m: float = Field(gt=0)
    first_changed_at: dt.date


class ReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["done", "failed"]
    result: Literal["change_found", "no_change", "no_clear_look"] | None = None
    as_of: dt.date | None = None
    before_date: dt.date | None = None
    after_date: dt.date | None = None
    scenes: list[SceneIn] = []
    before_png_b64: str | None = None
    after_png_b64: str | None = None
    change: ChangeSeenIn | None = None
    detail: str | None = None


@router.post("/pipeline/reviews/{review_id}", dependencies=[Depends(pipeline_token)])
def post_review(review_id: int, body: ReviewIn, db: Session = Depends(get_db)) -> dict:
    from app.citizen import incident
    from app.models import SatelliteReview

    rv = db.get(SatelliteReview, review_id)
    if rv is None or rv.is_demo:
        raise HTTPException(404, "No such review")
    if rv.status != "pending":
        raise HTTPException(409, f"The review is already {rv.status}")
    if body.status == "failed":
        incident.failed(db, rv, body.detail or "The screener could not finish", utcnow())
        db.commit()
        return {"id": rv.id, "status": rv.status, "attempts": rv.attempts}
    if body.result is None or (body.result == "change_found") != (body.change is not None):
        raise HTTPException(422, "A finished review needs its result, and a change exactly when one was found")
    if any(d and d > dt.date.today() for d in (body.as_of, body.before_date, body.after_date)):
        raise HTTPException(422, "A review cannot use images acquired in the future")
    try:
        result = {
            "result": body.result, "as_of": body.as_of, "before_date": body.before_date, "after_date": body.after_date,
            "scenes": [s.model_dump() for s in body.scenes], "detail": body.detail,
            "before_png": incident.decode(body.before_png_b64), "after_png": incident.decode(body.after_png_b64),
            "change": body.change.model_dump() if body.change else None,
        }
        with db_guard(db):
            incident.record(db, rv, result, utcnow())
            db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    return {"id": rv.id, "status": rv.status, "result": rv.result}


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
