"""Satellite image sources (DECISIONS.md D-066).

- GET    /satellites                 every source; officials read them to ask for a sharper image
- GET    /satellites/history         the latest changes, from the audit log
- POST   /satellites                 the admin adds a source
- PATCH  /satellites/{id}            the admin changes one, or turns it on or off
- DELETE /satellites/{id}?reason=    the admin deletes one, with a reason
- GET    /pipeline/satellites        what the weekly screen and the reviewer read (pipeline token)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.clock import utcnow
from app.db import get_db
from app.enums import Role
from app.models import SatelliteSource, User
from app.routers.candidates import pipeline_token
from app.security import current_user, require_roles
from app.services import satellites as svc

router = APIRouter(tags=["satellites"])


class SourceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str | None = None
    name: str | None = None
    provider: str | None = None
    purpose: str | None = None
    resolution_m: float | None = Field(default=None, gt=0, le=1000)
    revisit_days: float | None = None
    stac_url: str | None = None
    collection: str | None = None
    max_scene_cloud_pct: float | None = None
    price_usd_per_sq_km: float | None = None
    min_order_sq_km: float | None = None
    licence_notice: str | None = None
    notes: str | None = None
    active: bool | None = None


def _run(db: Session, fn):
    try:
        with db.begin_nested():
            out = fn()
    except svc.Refused as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    db.commit()
    return out


@router.get("/satellites")
def list_sources(purpose: str | None = None, active: bool | None = None, user: User = Depends(current_user),
                 db: Session = Depends(get_db)) -> dict:
    return {"items": svc.list_all(db, purpose, active), "purposes": list(svc.PURPOSES)}


@router.get("/satellites/history")
def history(user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> dict:
    return {"items": svc.history(db)}


@router.post("/satellites", status_code=201)
def add_source(body: SourceIn, user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> dict:
    values = body.model_dump(exclude_unset=True)
    s, off = _run(db, lambda: svc.create(db, user, values, utcnow()))
    return {**svc.as_dict(s, svc.user_names(db)), "switched_off": off}


@router.patch("/satellites/{source_id}")
def change_source(source_id: int, body: SourceIn, user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> dict:
    s = db.get(SatelliteSource, source_id)
    if s is None:
        raise HTTPException(404, "No such source")
    values = body.model_dump(exclude_unset=True)
    s, off = _run(db, lambda: svc.update(db, user, s, values, utcnow()))
    return {**svc.as_dict(s, svc.user_names(db)), "switched_off": off}


@router.delete("/satellites/{source_id}")
def delete_source(source_id: int, reason: str = Query(""), user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> dict:
    s = db.get(SatelliteSource, source_id)
    if s is None:
        raise HTTPException(404, "No such source")
    key = s.key
    _run(db, lambda: svc.delete(db, user, s, reason, utcnow()))
    return {"deleted": key}


@router.get("/pipeline/satellites", dependencies=[Depends(pipeline_token)])
def for_pipeline(db: Session = Depends(get_db)) -> dict:
    return svc.for_pipeline(db)
