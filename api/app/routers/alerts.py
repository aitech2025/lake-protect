"""Alerts (section 9.5). Every state change goes through the state machine."""
from __future__ import annotations

import json
import math
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from datetime import date as _date

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.clock import utcnow
from app.db import db_guard, get_db
from app.enums import ReadinessStatus, Role
from app.models import Candidate, ImageryRequest, OwnerClaim, ReadinessItem, User
from app.security import current_user, require_roles
from app.services import alert_view
from app.services import field as field_svc
from app.storage import store
from app.workflow import state_machine as sm

router = APIRouter(prefix="/alerts", tags=["alerts"])

DESK_ROLES = [r.value for r in Role if r != Role.field_officer]


@router.get("")
def list_alerts(
    state: str | None = None,
    mode: str | None = None,
    cohort: str | None = None,
    overdue: bool | None = None,
    dataset: Literal["demo", "real"] | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    items = alert_view.list_alerts(db, user, state=state, mode=mode, cohort=cohort, overdue=overdue)
    if dataset is not None:
        items = [i for i in items if i["is_demo"] == (dataset == "demo")]
    chain.record(db, actor_id=user.id, action="view.alerts", entity="alert", details={"filters": {"state": state, "mode": mode, "cohort": cohort, "overdue": overdue, "dataset": dataset}, "count": len(items)})
    db.commit()
    return {"items": items, "count": len(items), "has_demo": any(i["is_demo"] for i in items)}


@router.get("/{alert_id}")
def get_alert(alert_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    alert = alert_view.get_visible(db, alert_id, user)
    out = alert_view.detail(db, alert, user)
    chain.record(db, actor_id=user.id, action="view.alert", entity="alert", entity_id=alert_id)
    db.commit()
    return out


@router.get("/{alert_id}/chips/{which}")
def get_chip(alert_id: int, which: Literal["before", "after"], user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    alert = alert_view.get_visible(db, alert_id, user)
    cand = db.get(Candidate, alert.candidate_id)
    key = cand.before_chip if which == "before" else cand.after_chip
    if not key or store.head_object(key) is None:
        raise HTTPException(404, "No image for this alert")
    chain.record(db, actor_id=user.id, action="view.chip", entity="alert", entity_id=alert_id, details={"which": which})
    db.commit()
    return Response(store.get_object(key), media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


class TransitionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    to: str
    reason: str | None = None
    data: dict = Field(default_factory=dict)


def _refusal(db: Session, exc: sm.Refused):
    db.rollback()
    return HTTPException(exc.status, exc.message)


@router.post("/{alert_id}/transitions")
def post_transition(alert_id: int, body: TransitionIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    alert = alert_view.get_visible(db, alert_id, user)
    with db_guard(db):
        try:
            result = sm.transition(db, alert, body.to, actor=user, reason=body.reason, data=body.data)
        except ValueError as exc:
            db.rollback()
            raise HTTPException(422, f"Unknown state {body.to}") from exc
        except sm.Refused as exc:
            raise _refusal(db, exc) from exc
        db.commit()
    return result


@router.post("/{alert_id}/field-checks")
async def post_field_check(
    alert_id: int,
    meta: str = Form(...),
    photos: list[UploadFile] = File(default=[]),
    user: User = Depends(require_roles(Role.field_officer)),
    db: Session = Depends(get_db),
) -> dict:
    """Idempotent: resending the same client_uuid returns the stored record."""
    alert = alert_view.get_visible(db, alert_id, user)
    try:
        parsed = field_svc.FieldCheckMeta.model_validate(json.loads(meta))
    except (ValidationError, json.JSONDecodeError) as exc:
        raise HTTPException(422, f"Bad field check metadata: {exc}") from exc
    blobs = [await p.read() for p in photos]
    with db_guard(db):
        try:
            result = field_svc.submit(db, alert, user, parsed, blobs)
        except field_svc.FieldRefused as exc:
            db.rollback()
            raise HTTPException(exc.status, exc.message) from exc
        db.commit()
    return result


class OwnerClaimIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_type: str
    claimant_name: str
    document_ref: str | None = None


@router.post("/{alert_id}/owner-claims", status_code=201)
def post_owner_claim(
    alert_id: int,
    body: OwnerClaimIn,
    user: User = Depends(require_roles(Role.field_officer, Role.nodal_officer, Role.legal_officer)),
    db: Session = Depends(get_db),
) -> dict:
    """Rule 4: owner names stay out until a field check confirms the change."""
    alert = alert_view.get_visible(db, alert_id, user)
    if alert.state not in sm.FIELD_CONFIRMED_OR_LATER:
        raise HTTPException(409, f"Owner claims are accepted only after field confirmation (alert is {alert.state})")
    with db_guard(db):
        now = utcnow()
        claim = OwnerClaim(alert_id=alert.id, claim_type=body.claim_type, claimant_name=body.claimant_name, document_ref=body.document_ref, entered_by=user.id, entered_at=now)
        db.add(claim)
        db.flush()
        reclassified = _reclassify_after_claim(db, alert, body.claim_type, now)
        chain.record(db, actor_id=user.id, action="owner_claim.added", entity="alert", entity_id=alert.id, details={"owner_claim_id": claim.id, "claim_type": body.claim_type, "alert_class": reclassified})
        db.commit()
    return {"id": claim.id, "alert_class": reclassified}


def _reclassify_after_claim(db: Session, alert, claim_type: str, now) -> str | None:
    """Section 6.3: a private title claim inside the FTL or buffer makes the class RESTRICTED_PRIVATE.

    Legal checks are append-only, so the new class is a new row that copies the latest one.
    """
    from app.models import Asset, Candidate, LegalCheck
    from app.rules import legal_check

    latest = db.scalar(select(LegalCheck).where(LegalCheck.candidate_id == alert.candidate_id).order_by(LegalCheck.id.desc()).limit(1))
    if latest is None or claim_type != "private_title":
        return latest.alert_class if latest else None
    asset = db.get(Asset, db.get(Candidate, alert.candidate_id).asset_id)
    new_class = legal_check.alert_class_for(asset, latest.matched_court_case_id, private_title_claim=True, zone=latest.zone).value
    if new_class == latest.alert_class:
        return new_class
    db.add(LegalCheck(
        candidate_id=latest.candidate_id, zone=latest.zone, boundary_status=latest.boundary_status, mode=latest.mode,
        alert_class=new_class, result=alert.state, matched_permit_id=latest.matched_permit_id, matched_work_id=latest.matched_work_id,
        matched_court_case_id=latest.matched_court_case_id, boundary_id=latest.boundary_id, boundary_version=latest.boundary_version,
        flags=sorted(set(latest.flags or []) | {"reclassified_after_title_claim"}), rule_version=latest.rule_version, checked_at=now,
    ))
    db.flush()
    return new_class


class ReadinessIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: ReadinessStatus
    evidence_ref: str | None = None


@router.put("/{alert_id}/readiness/{item_key}")
def put_readiness(
    alert_id: int,
    item_key: str,
    body: ReadinessIn,
    user: User = Depends(require_roles(Role.nodal_officer, Role.legal_officer)),
    db: Session = Depends(get_db),
) -> dict:
    from app.services import readiness

    if item_key not in sm.READINESS_KEYS:
        raise HTTPException(422, f"Unknown checklist item {item_key}")
    alert = alert_view.get_visible(db, alert_id, user)
    item = readiness.record(db, alert, user, item_key, body.status.value, body.evidence_ref)
    db.commit()
    return {"item_key": item_key, "status": item.status}


class ImageryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["isro_nrsc", "commercial_archive", "commercial_tasking"]
    note: str | None = None


# Reseller guide figures from CONTEXT.md section 8.1, upper end. Planning estimates, not quotes.
_USD_PER_SQ_KM = {"isro_nrsc": None, "commercial_archive": 26.0, "commercial_tasking": 55.0}


@router.post("/{alert_id}/imagery-request", status_code=201)
def post_imagery_request(
    alert_id: int,
    body: ImageryIn,
    user: User = Depends(require_roles(Role.analyst, Role.nodal_officer)),
    db: Session = Depends(get_db),
) -> dict:
    """Stub: records the request and its estimated cost. Nothing is ordered (section 3)."""
    alert = alert_view.get_visible(db, alert_id, user)
    area = db.scalar(
        text("SELECT ST_Area(ST_Transform(ST_Envelope(ST_Buffer(geom::geography, 250)::geometry), 32644)) / 1e6 FROM candidates WHERE id = :c"),
        {"c": alert.candidate_id},
    )
    rate = _USD_PER_SQ_KM[body.provider]
    req = ImageryRequest(alert_id=alert.id, provider=body.provider, area_sq_km=round(area, 3), est_cost_usd=None if rate is None else round(math.ceil(area * 100) / 100 * rate, 2), status="recorded", requested_by=user.id, created_at=utcnow())
    db.add(req)
    db.flush()
    chain.record(db, actor_id=user.id, action="imagery.requested", entity="alert", entity_id=alert.id, details={"imagery_request_id": req.id, "provider": body.provider, "area_sq_km": float(req.area_sq_km), "est_cost_usd": req.est_cost_usd and float(req.est_cost_usd), "note": body.note})
    db.commit()
    return {"id": req.id, "status": req.status, "area_sq_km": float(req.area_sq_km), "est_cost_usd": req.est_cost_usd and float(req.est_cost_usd), "note": "Recorded only. No imagery is ordered in the prototype."}


class OverrideIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: float = Field(ge=0, le=100)
    reason: str = Field(min_length=3)


@router.post("/{alert_id}/priority-override")
def post_priority_override(alert_id: int, body: OverrideIn, user: User = Depends(require_roles(Role.nodal_officer)), db: Session = Depends(get_db)) -> dict:
    """Section 6.4: manual overrides need a reason and are logged."""
    alert = alert_view.get_visible(db, alert_id, user)
    before = float(alert.priority_score) if alert.priority_score is not None else None
    alert.priority_factors = {**(alert.priority_factors or {}), "override": {"score": body.score, "reason": body.reason, "by": user.id, "at": utcnow().isoformat(), "previous": before}}
    alert.priority_score = body.score
    db.flush()
    chain.record(db, actor_id=user.id, action="priority.override", entity="alert", entity_id=alert.id, details={"before": before, "after": body.score, "reason": body.reason})
    db.commit()
    return {"priority_score": body.score}


# Evidence pack (section 9.3). Single-case downloads only, and every export is logged (section 10).
PACK_ROLES = (Role.nodal_officer, Role.legal_officer)
READ_PACK_ROLES = (Role.nodal_officer, Role.legal_officer, Role.senior_officer, Role.auditor, Role.admin, Role.analyst)


def _pack(db: Session, alert_id: int, version: int | None):
    from app.models import EvidencePack

    q = select(EvidencePack).where(EvidencePack.alert_id == alert_id)
    q = q.where(EvidencePack.version == version) if version else q.order_by(EvidencePack.version.desc()).limit(1)
    pack = db.scalar(q)
    if pack is None:
        raise HTTPException(404, "No evidence pack for this alert yet")
    return pack


@router.post("/{alert_id}/evidence-pack", status_code=201)
def post_evidence_pack(alert_id: int, user: User = Depends(require_roles(*PACK_ROLES)), db: Session = Depends(get_db)) -> dict:
    """Generate a new version. An earlier version is never overwritten."""
    from app.evidence import pack as pack_svc

    alert = alert_view.get_visible(db, alert_id, user)
    if alert.state not in sm.FIELD_CONFIRMED_OR_LATER:  # checked before any write
        raise HTTPException(409, f"A pack needs a field-confirmed change (alert is {alert.state})")
    with db_guard(db):
        try:
            pack = pack_svc.build(db, alert, user)
        except pack_svc.PackRefused as exc:
            db.rollback()
            raise HTTPException(409, str(exc)) from exc
        db.commit()
    return {"id": pack.id, "version": pack.version, "manifest_sha256": pack.manifest_sha256, "counsel_reviewed": pack.counsel_reviewed}


@router.get("/{alert_id}/evidence-pack")
def get_evidence_pack(alert_id: int, version: int | None = None, user: User = Depends(require_roles(*READ_PACK_ROLES)), db: Session = Depends(get_db)) -> Response:
    alert = alert_view.get_visible(db, alert_id, user)
    pack = _pack(db, alert.id, version)
    chain.record(db, actor_id=user.id, action="export.evidence_pack", entity="alert", entity_id=alert.id, details={"version": pack.version, "file": "zip"})
    db.commit()
    name = pack.zip_path.rsplit("/", 1)[-1]
    return Response(store.get_object(pack.zip_path), media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{name}"', "X-Manifest-SHA256": pack.manifest_sha256})


@router.get("/{alert_id}/evidence-pack/pdf")
def get_evidence_pdf(alert_id: int, version: int | None = None, user: User = Depends(require_roles(*READ_PACK_ROLES)), db: Session = Depends(get_db)) -> Response:
    alert = alert_view.get_visible(db, alert_id, user)
    pack = _pack(db, alert.id, version)
    chain.record(db, actor_id=user.id, action="export.evidence_pdf", entity="alert", entity_id=alert.id, details={"version": pack.version, "file": "pdf"})
    db.commit()
    return Response(store.get_object(pack.pdf_path), media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{alert.code}-v{pack.version}.pdf"'})


@router.get("/{alert_id}/evidence-pack/verify")
def verify_evidence_pack(alert_id: int, version: int | None = None, user: User = Depends(require_roles(*READ_PACK_ROLES)), db: Session = Depends(get_db)) -> dict:
    """Run the same check as `lp verify-pack`, against the manifest hash recorded when the pack was made."""
    from app.evidence.verify import verify

    alert = alert_view.get_visible(db, alert_id, user)
    pack = _pack(db, alert.id, version)
    result = verify(store.local_path(pack.zip_path), pack.manifest_sha256)
    chain.record(db, actor_id=user.id, action="view.evidence_verify", entity="alert", entity_id=alert.id, details={"version": pack.version, "ok": result["ok"]})
    db.commit()
    return {"version": pack.version, **result}


@router.get("/{alert_id}/field-checks/{check_id}/photos/{n}")
def get_field_photo(alert_id: int, check_id: int, n: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    from app.models import FieldCheck

    alert = alert_view.get_visible(db, alert_id, user)
    fc = db.get(FieldCheck, check_id)
    if fc is None or fc.alert_id != alert.id or not (1 <= n <= len(fc.photo_paths)):
        raise HTTPException(404, "No such photo")
    path = fc.photo_paths[n - 1]
    chain.record(db, actor_id=user.id, action="view.field_photo", entity="alert", entity_id=alert.id, details={"field_check_id": check_id, "photo": n})
    db.commit()
    return Response(store.get_object(path), media_type="image/png" if path.endswith(".png") else "image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


class OfficerRecordIn(BaseModel):
    """Validated before any write, so a refusal never needs a rollback."""

    model_config = ConfigDict(extra="forbid")
    notice_ref: str | None = None
    notice_date: _date | None = None
    hearing_date: _date | None = None
    order_ref: str | None = None
    order_date: _date | None = None
    action_date: _date | None = None
    action_summary: str | None = None
    record_action: bool = False

    @model_validator(mode="after")
    def needs_a_reference(self):
        if not any([self.notice_ref, self.order_ref, self.notice_date, self.hearing_date, self.order_date, self.action_date]):
            raise ValueError("Give at least one notice, hearing, order or action reference")
        return self


@router.post("/{alert_id}/officer-record", status_code=201)
def post_officer_record(alert_id: int, body: OfficerRecordIn, user: User = Depends(require_roles(Role.legal_officer, Role.senior_officer)), db: Session = Depends(get_db)) -> dict:
    """Section 9.1: notice, hearing, order and action references. The system suggests no outcome."""
    from app.services import officer

    alert = alert_view.get_visible(db, alert_id, user)
    if alert.state != "WITH_OFFICER":  # checked before any write
        raise HTTPException(409, f"Officer records are added while the alert is with the officer (alert is {alert.state})")
    with db_guard(db):
        try:
            result = officer.add(db, alert, user, body.model_dump(exclude={"record_action"}), record_action=body.record_action)
        except officer.OfficerRefused as exc:
            db.rollback()
            raise HTTPException(exc.status, exc.message) from exc
        except sm.Refused as exc:
            db.rollback()
            raise HTTPException(exc.status, exc.message) from exc
        db.commit()
    return result
