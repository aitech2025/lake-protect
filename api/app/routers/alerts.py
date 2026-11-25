"""Incidents (DECISIONS.md D-057). Kept at /alerts so links and audit entries stay stable.

Every signed-in user can read every incident. Viewers record reviews; the admin moves an incident
through its lifecycle. Every state change goes through app.workflow.incidents.

On an incident a citizen reported (D-064), officials and the admin alike can:
- acknowledge it, and add notes;
- request satellite looks (latest or by date), and sharper images (the admin approves them);
- attach legal records and documents;
- approve, decline or close it, with notes;
- put its place on the weekly watch.
"""
from __future__ import annotations

import datetime as dt
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import chain
from app.citizen import actions
from app.clock import utcnow
from app.db import db_guard, get_db
from app.enums import ReviewOutcome, Role
from app.models import Candidate, EvidencePack, User
from app.security import current_user, require_roles
from app.services import alert_view, imagery
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
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Every incident, open first and then by priority. The area filters and `waiting` (open or under review
    for more than 14 days) and `week` (new incidents of an ISO week) are what the dashboard's numbers
    open (D-060)."""
    items = alert_view.list_alerts(db, state=state, change_type=change_type, cohort=cohort, asset_id=asset_id,
                                   district=district, mandal=mandal, village=village, waiting=waiting,
                                   new_in_week=week, now=utcnow())
    filters = {"state": state, "change_type": change_type, "cohort": cohort, "asset_id": asset_id, "district": district,
               "mandal": mandal, "village": village, "waiting": waiting, "week": week}
    chain.record(db, actor_id=user.id, action="view.alerts", entity="alert",
                 details={"filters": {k: v for k, v in filters.items() if v not in (None, False)}, "count": len(items)})
    db.commit()
    return {"items": items, "count": len(items)}


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
def post_review(alert_id: int, body: ReviewIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """A viewer's review: real change, not real, or needs a site visit, with a note. On a citizen's
    incident the admin may review too (D-064)."""
    alert = alert_view.get_visible(db, alert_id)
    with db_guard(db):
        row = _act(db, lambda: lifecycle.review(db, alert, user, body.outcome.value, body.note))
    return {"id": row.id, "state": alert.state}


class TransitionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    to: str
    note: str | None = None
    citizen_department: str | None = None  # dismissing a citizen's report: the department it was passed to (D-063)
    citizen_false_report: bool = False  # dismissing: the report was false; repeated false reports flag their source


@router.post("/{alert_id}/transitions")
def post_transition(alert_id: int, body: TransitionIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """The admin's steps; on a citizen's incident an official's too (D-064). The lifecycle checks who may."""
    alert = alert_view.get_visible(db, alert_id)
    with db_guard(db):
        return _act(db, lambda: lifecycle.transition(db, alert, body.to, actor=user, note=body.note, department=body.citizen_department or None,
                                                     false_report=body.citizen_false_report))


class ImageryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str | None = None  # a sharper-image source that is on (Satellites, D-066); none: the first one on
    note: str | None = None


@router.post("/{alert_id}/imagery-request", status_code=201)
def post_imagery_request(alert_id: int, body: ImageryIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Stub: records a request for a sharper image and its estimated cost. Nothing is ordered. Officials
    may ask on a citizen's incident; the admin approves (D-064)."""
    alert = alert_view.get_visible(db, alert_id)
    if user.role != Role.admin.value and alert.origin != "citizen":
        raise HTTPException(403, "Officials request sharper images on incidents a citizen reported")
    from app.services import satellites

    try:
        with db.begin_nested():
            req = imagery.request(db, alert, user, body.provider, body.note, utcnow())
    except satellites.Refused as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    db.commit()
    return {"id": req.id, "provider": req.provider, "status": req.status, "area_sq_km": float(req.area_sq_km), "est_cost_usd": req.est_cost_usd and float(req.est_cost_usd),
            "note": "Recorded only. No imagery is ordered in the prototype."}


# What officials and the admin do on a citizen's incident (D-064) --------------------------------
def _act(db: Session, fn):
    """Run one step in a savepoint: a refusal leaves nothing behind and keeps the session usable."""
    try:
        with db.begin_nested():
            out = fn()
    except lifecycle.Refused as exc:
        raise HTTPException(exc.status, exc.message) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return out


class AckIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: str | None = None


@router.post("/{alert_id}/acknowledge", status_code=201)
def post_acknowledge(alert_id: int, body: AckIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """I have seen this citizen's incident. The first acknowledgement starts its review."""
    alert = alert_view.get_visible(db, alert_id)
    row = _act(db, lambda: actions.acknowledge(db, alert, user, body.note, utcnow()))
    return {"id": row.id, "state": alert.state}


class NoteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str


@router.post("/{alert_id}/notes", status_code=201)
def post_note(alert_id: int, body: NoteIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """A note for the record, by an official or the admin. Kept for good; never shown to citizens."""
    alert = alert_view.get_visible(db, alert_id)
    row = _act(db, lambda: actions.add_note(db, alert, user, body.text, utcnow()))
    return {"id": row.id}


class LookIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: dt.date | None = None  # none: the latest clear image


@router.post("/{alert_id}/satellite-looks", status_code=201)
def post_look(alert_id: int, body: LookIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """A satellite look at the reported place: the latest, or the newest clear image on or before a date."""
    from app.citizen import incident

    alert = alert_view.get_visible(db, alert_id)

    def run():
        actions.require_citizen(alert)
        return incident.request_look(db, alert, user, body.date, utcnow())

    rv = _act(db, run)
    return {"id": rv.id, "status": rv.status, "result": rv.result}


@router.get("/{alert_id}/looks/{review_id}/{which}")
def get_look_image(alert_id: int, review_id: int, which: Literal["before", "after"], user: User = Depends(current_user),
                   db: Session = Depends(get_db)) -> Response:
    from app.models import SatelliteReview

    rv = db.get(SatelliteReview, review_id)
    if rv is None or rv.alert_id != alert_id:
        raise HTTPException(404, "No such look")
    key = rv.before_chip if which == "before" else rv.after_chip
    if not key or store.head_object(key) is None:
        raise HTTPException(404, "No image for this look")
    chain.record(db, actor_id=user.id, action="view.look", entity="alert", entity_id=alert_id, details={"review_id": review_id, "which": which})
    db.commit()
    return Response(store.get_object(key), media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


class ImageryDecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approve: bool
    note: str | None = None


@router.post("/{alert_id}/imagery-requests/{request_id}/decision")
def post_imagery_decision(alert_id: int, request_id: int, body: ImageryDecisionIn, user: User = Depends(require_roles(Role.admin)),
                          db: Session = Depends(get_db)) -> dict:
    """The admin approves or declines an official's request for a sharper image. Nothing is ordered."""
    from app.models import ImageryRequest

    req = db.get(ImageryRequest, request_id)
    if req is None or req.alert_id != alert_id:
        raise HTTPException(404, "No such request")
    _act(db, lambda: actions.decide_imagery(db, req, user, body.approve, body.note, utcnow()))
    return {"id": req.id, "status": req.status}


@router.post("/{alert_id}/legal-records", status_code=201)
def post_legal_records(alert_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Attach the legal records at the place as they stand now: a dated snapshot, kept beside earlier ones."""
    alert = alert_view.get_visible(db, alert_id)
    row = _act(db, lambda: actions.attach_legal(db, alert, user, utcnow()))
    return {"id": row.id, "at": row.at.isoformat(), "records": row.records}


@router.post("/{alert_id}/documents", status_code=201)
async def post_document(
    alert_id: int,
    doc_type: str = Form(...),
    title: str = Form(...),
    reference: str | None = Form(None),
    issued_on: str | None = Form(None),
    issued_by: str | None = Form(None),
    file: UploadFile | None = File(None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """A legal document for the incident (a notice, an order, a survey sketch): a file or a reference.
    It is kept on the location too, so the next incident there sees it."""
    from app.services import documents as doc_svc

    alert = alert_view.get_visible(db, alert_id)
    if user.role != Role.admin.value and alert.origin != "citizen":
        raise HTTPException(403, "Officials attach documents to incidents a citizen reported; the admin to any")
    try:
        issued = dt.date.fromisoformat(issued_on) if issued_on else None
    except ValueError as exc:
        raise HTTPException(422, "issued_on must be YYYY-MM-DD") from exc
    content = await file.read() if file is not None and file.filename else None
    try:
        with db.begin_nested():
            row = actions.attach_document(db, alert, user, utcnow(), doc_type=doc_type, title=title, reference=reference, issued_on=issued,
                                          issued_by=issued_by, content=content, file_name=file.filename if content else None,
                                          content_type=file.content_type if content else None)
    except doc_svc.DocumentRefused as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return doc_svc.as_dict(row, set())


class DecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approve", "decline", "close"]
    note: str
    citizen_department: str | None = None
    citizen_false_report: bool = False


@router.post("/{alert_id}/decision")
def post_decision(alert_id: int, body: DecisionIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Approve (a real change), decline (not a change that needs action), or close, with a note."""
    alert = alert_view.get_visible(db, alert_id)
    return _act(db, lambda: actions.decide(db, alert, user, body.decision, body.note, utcnow(),
                                           department=body.citizen_department or None, false_report=body.citizen_false_report))


class WatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str
    name: str | None = None


@router.post("/{alert_id}/watch")
def post_watch(alert_id: int, body: WatchIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Add the incident's place to the weekly watch, so every screen from now on looks at it."""
    alert = alert_view.get_visible(db, alert_id)
    asset = _act(db, lambda: actions.watch_place(db, alert, user, body.reason, body.name, utcnow()))
    return {"asset_id": asset.id, "name": asset.name, "monitored": asset.monitored}


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
