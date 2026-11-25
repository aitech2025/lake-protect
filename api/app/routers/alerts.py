"""Incidents (DECISIONS.md D-057). Kept at /alerts so links and audit entries stay stable.

Every signed-in user can read every incident. Viewers record reviews; the admin moves an incident
through its lifecycle. Every state change goes through app.workflow.incidents.
"""
from __future__ import annotations

import math
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.clock import utcnow
from app.db import db_guard, get_db
from app.enums import ReviewOutcome, Role
from app.models import Candidate, EvidencePack, ImageryRequest, User
from app.security import current_user, require_roles
from app.services import alert_view
from app.storage import store
from app.workflow import incidents as lifecycle

router = APIRouter(prefix="/alerts", tags=["incidents"])


@router.get("")
def list_alerts(
    state: str | None = None,
    change_type: str | None = None,
    cohort: str | None = None,
    asset_id: int | None = None,
    district: str | None = None,
    mandal: str | None = None,
    village: str | None = None,
    waiting: bool = False,
    week: str | None = None,
    dataset: Literal["demo", "real"] | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Every incident, open first and then by priority. The area filters and `waiting` (open or under review
    for more than 14 days) and `week` (new incidents of an ISO week) are what the dashboard's numbers
    open (D-060)."""
    items = alert_view.list_alerts(db, state=state, change_type=change_type, cohort=cohort, asset_id=asset_id,
                                   district=district, mandal=mandal, village=village, waiting=waiting,
                                   new_in_week=week, now=utcnow())
    if dataset is not None:
        items = [i for i in items if i["is_demo"] == (dataset == "demo")]
    filters = {"state": state, "change_type": change_type, "cohort": cohort, "asset_id": asset_id, "district": district,
               "mandal": mandal, "village": village, "waiting": waiting, "week": week, "dataset": dataset}
    chain.record(db, actor_id=user.id, action="view.alerts", entity="alert",
                 details={"filters": {k: v for k, v in filters.items() if v not in (None, False)}, "count": len(items)})
    db.commit()
    return {"items": items, "count": len(items), "has_demo": any(i["is_demo"] for i in items)}


@router.get("/{alert_id}")
def get_alert(alert_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    alert = alert_view.get_visible(db, alert_id)
    out = alert_view.detail(db, alert, user)
    chain.record(db, actor_id=user.id, action="view.alert", entity="alert", entity_id=alert_id)
    db.commit()
    return out


@router.get("/{alert_id}/chips/{which}")
def get_chip(alert_id: int, which: Literal["before", "after"], user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    alert = alert_view.get_visible(db, alert_id)
    cand = db.get(Candidate, alert.candidate_id)
    key = cand.before_chip if which == "before" else cand.after_chip
    if not key or store.head_object(key) is None:
        raise HTTPException(404, "No image for this incident")
    chain.record(db, actor_id=user.id, action="view.chip", entity="alert", entity_id=alert_id, details={"which": which})
    db.commit()
    return Response(store.get_object(key), media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


class ReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome: ReviewOutcome
    note: str = Field(min_length=1)


@router.post("/{alert_id}/reviews", status_code=201)
def post_review(alert_id: int, body: ReviewIn, user: User = Depends(require_roles(Role.viewer)), db: Session = Depends(get_db)) -> dict:
    """A viewer's review: real change, not real, or needs a site visit, with a note."""
    alert = alert_view.get_visible(db, alert_id)
    with db_guard(db):
        try:
            row = lifecycle.review(db, alert, user, body.outcome.value, body.note)
        except lifecycle.Refused as exc:
            db.rollback()
            raise HTTPException(exc.status, exc.message) from exc
        db.commit()
    return {"id": row.id, "state": alert.state}


class TransitionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    to: str
    note: str | None = None


@router.post("/{alert_id}/transitions")
def post_transition(alert_id: int, body: TransitionIn, user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> dict:
    alert = alert_view.get_visible(db, alert_id)
    with db_guard(db):
        try:
            result = lifecycle.transition(db, alert, body.to, actor=user, note=body.note)
        except lifecycle.Refused as exc:
            db.rollback()
            raise HTTPException(exc.status, exc.message) from exc
        db.commit()
    return result


class ImageryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["isro_nrsc", "commercial_archive", "commercial_tasking"]
    note: str | None = None


# Reseller guide figures from CONTEXT.md section 8.1, upper end. Planning estimates, not quotes.
_USD_PER_SQ_KM = {"isro_nrsc": None, "commercial_archive": 26.0, "commercial_tasking": 55.0}


@router.post("/{alert_id}/imagery-request", status_code=201)
def post_imagery_request(alert_id: int, body: ImageryIn, user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> dict:
    """Stub: records a request for a sharper image and its estimated cost. Nothing is ordered."""
    alert = alert_view.get_visible(db, alert_id)
    area = db.scalar(
        text("SELECT ST_Area(ST_Transform(ST_Envelope(ST_Buffer(geom::geography, 250)::geometry), 32644)) / 1e6 FROM candidates WHERE id = :c"),
        {"c": alert.candidate_id},
    )
    rate = _USD_PER_SQ_KM[body.provider]
    req = ImageryRequest(alert_id=alert.id, provider=body.provider, area_sq_km=round(area, 3),
                         est_cost_usd=None if rate is None else round(math.ceil(area * 100) / 100 * rate, 2),
                         status="recorded", requested_by=user.id, created_at=utcnow())
    db.add(req)
    db.flush()
    chain.record(db, actor_id=user.id, action="imagery.requested", entity="alert", entity_id=alert.id,
                 details={"imagery_request_id": req.id, "provider": body.provider, "area_sq_km": float(req.area_sq_km),
                          "est_cost_usd": req.est_cost_usd and float(req.est_cost_usd), "note": body.note})
    db.commit()
    return {"id": req.id, "status": req.status, "area_sq_km": float(req.area_sq_km), "est_cost_usd": req.est_cost_usd and float(req.est_cost_usd),
            "note": "Recorded only. No imagery is ordered in the prototype."}


class OverrideIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: float = Field(ge=0, le=100)
    reason: str = Field(min_length=3)


@router.post("/{alert_id}/priority-override")
def post_priority_override(alert_id: int, body: OverrideIn, user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> dict:
    """Manual overrides need a reason and are logged."""
    alert = alert_view.get_visible(db, alert_id)
    before = float(alert.priority_score) if alert.priority_score is not None else None
    alert.priority_factors = {**(alert.priority_factors or {}), "override": {"score": body.score, "reason": body.reason, "by": user.id, "at": utcnow().isoformat(), "previous": before}}
    alert.priority_score = body.score
    db.flush()
    chain.record(db, actor_id=user.id, action="priority.override", entity="alert", entity_id=alert.id, details={"before": before, "after": body.score, "reason": body.reason})
    db.commit()
    return {"priority_score": body.score}


# Evidence pack (section 9.3). Single-case downloads only, and every export is logged (section 10).

def _pack(db: Session, alert_id: int, version: int | None) -> EvidencePack:
    q = select(EvidencePack).where(EvidencePack.alert_id == alert_id)
    q = q.where(EvidencePack.version == version) if version else q.order_by(EvidencePack.version.desc()).limit(1)
    pack = db.scalar(q)
    if pack is None:
        raise HTTPException(404, "No evidence pack for this incident yet")
    return pack


@router.post("/{alert_id}/evidence-pack", status_code=201)
def post_evidence_pack(alert_id: int, user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> dict:
    """Generate a new version for a confirmed change. An earlier version is never overwritten."""
    from app.evidence import pack as pack_svc

    alert = alert_view.get_visible(db, alert_id)
    if alert.resolution != "confirmed":  # checked before any write
        raise HTTPException(409, f"A pack is made for a confirmed change (incident is {alert.state})")
    with db_guard(db):
        try:
            pack = pack_svc.build(db, alert, user)
        except pack_svc.PackRefused as exc:
            db.rollback()
            raise HTTPException(409, str(exc)) from exc
        db.commit()
    return {"id": pack.id, "version": pack.version, "manifest_sha256": pack.manifest_sha256, "counsel_reviewed": pack.counsel_reviewed}


@router.get("/{alert_id}/evidence-pack")
def get_evidence_pack(alert_id: int, version: int | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    alert = alert_view.get_visible(db, alert_id)
    pack = _pack(db, alert.id, version)
    chain.record(db, actor_id=user.id, action="export.evidence_pack", entity="alert", entity_id=alert.id, details={"version": pack.version, "file": "zip"})
    db.commit()
    name = pack.zip_path.rsplit("/", 1)[-1]
    return Response(store.get_object(pack.zip_path), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{name}"', "X-Manifest-SHA256": pack.manifest_sha256})


@router.get("/{alert_id}/evidence-pack/pdf")
def get_evidence_pdf(alert_id: int, version: int | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    alert = alert_view.get_visible(db, alert_id)
    pack = _pack(db, alert.id, version)
    chain.record(db, actor_id=user.id, action="export.evidence_pdf", entity="alert", entity_id=alert.id, details={"version": pack.version, "file": "pdf"})
    db.commit()
    return Response(store.get_object(pack.pdf_path), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{alert.code}-v{pack.version}.pdf"'})


@router.get("/{alert_id}/evidence-pack/verify")
def verify_evidence_pack(alert_id: int, version: int | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Run the same check as `lp verify-pack`, against the manifest hash recorded when the pack was made."""
    from app.evidence.verify import verify

    alert = alert_view.get_visible(db, alert_id)
    pack = _pack(db, alert.id, version)
    result = verify(store.local_path(pack.zip_path), pack.manifest_sha256)
    chain.record(db, actor_id=user.id, action="view.evidence_verify", entity="alert", entity_id=alert.id, details={"version": pack.version, "ok": result["ok"]})
    db.commit()
    return {"version": pack.version, **result}
