"""Citizen reports on the desk (CONTEXT.md 17.8; DECISIONS.md D-062).

- GET  /reports                       reports, newest first, with filters
- POST /reports/intake                staff enter a 1070 call, a Praja Vani petition or a visit
- GET  /reports/whatsapp-simulator    the demo WhatsApp conversation of the signed-in user
- POST /reports/whatsapp-simulator    send a demo WhatsApp message
- GET  /reports/{id}                  one report: history, messages to the citizen, duplicates
- GET  /reports/{id}/photos/{n}       a photo (metadata already removed)
- POST /reports/{id}/place            an official puts a report with no place on the map

Each placed report belongs to an incident (D-063): officials work it there, in the regular flow.

Officials never see a citizen's number or name: only whether updates go to a verified phone.
"""
from __future__ import annotations

import base64
import binascii
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import chain
from app.citizen import service, whatsapp
from app.clock import utcnow
from app.db import get_db
from app.models import CitizenChat, CitizenMessage, CitizenReport, User
from app.security import current_user
from app.storage import store

router = APIRouter(prefix="/reports", tags=["citizen reports"])


def _get(db: Session, report_id: int) -> CitizenReport:
    report = db.get(CitizenReport, report_id)
    if report is None:
        raise HTTPException(404, "Report not found")
    return report


def _fail(exc: service.CitizenError) -> HTTPException:
    return HTTPException(exc.status_code, str(exc))


@router.get("")
def list_reports(dataset: Literal["demo", "real"] | None = None, status: str | None = None, channel: str | None = None,
                 asset_id: int | None = None, alert_id: int | None = None, limit: int = Query(200, ge=1, le=500),
                 user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    q = select(CitizenReport)
    if dataset is not None:
        q = q.where(CitizenReport.is_demo.is_(dataset == "demo"))
    if status == "open":
        q = q.where(CitizenReport.status != "CLOSED")
    elif status:
        q = q.where(CitizenReport.status == status)
    if channel:
        q = q.where(CitizenReport.channel == channel)
    if asset_id:
        q = q.where(CitizenReport.asset_id == asset_id)
    if alert_id:
        q = q.where(CitizenReport.alert_id == alert_id)
    rows = list(db.scalars(q.order_by(CitizenReport.created_at.desc(), CitizenReport.id.desc()).limit(limit)))
    chain.record(db, actor_id=user.id, action="view.citizen_reports", entity="citizen_report", details={"count": len(rows)})
    db.commit()
    return {"items": [service.desk_row(db, r) for r in rows]}


class IntakeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset: Literal["demo", "real"] = "real"
    channel: Literal["helpline_1070", "praja_vani", "walk_in"]
    source_ref: str | None = None
    language: Literal["en", "te"] = "te"
    what: str
    lon: float | None = Field(default=None, ge=-180, le=180)
    lat: float | None = Field(default=None, ge=-90, le=90)
    location_text: str | None = None
    description: str | None = None
    caller_phone: str | None = None
    wants_updates: bool = False


@router.post("/intake", status_code=201)
async def intake(data: str = Form(...), photos: list[UploadFile] = File(default=[]), user: User = Depends(current_user),
                 db: Session = Depends(get_db)) -> dict:
    """Staff type in what a caller or visitor said. The caller's number is kept only for updates."""
    try:
        body = IntakeIn.model_validate_json(data)
    except ValidationError as exc:
        raise HTTPException(422, "The form is not complete") from exc
    blobs = [await f.read(service.MAX_PHOTO_BYTES + 1) for f in photos[: service.MAX_PHOTOS + 1]]
    try:
        phone = service.normalise_phone(body.caller_phone) if body.wants_updates else None
        with db.begin_nested():
            report = service.submit(
                db, channel=body.channel, language=body.language, what=body.what, at=utcnow(), source=service.source_hash(f"staff:{user.id}"),
                lon=body.lon, lat=body.lat, location_text=body.location_text, description=body.description, photos=blobs,
                phone=phone, phone_verified_via="staff" if phone else None, wants_updates=bool(phone), source_ref=body.source_ref,
                entered_by=user, is_demo=body.dataset == "demo",
            )
    except service.CitizenError as exc:
        raise _fail(exc) from exc
    db.commit()
    return {**service.desk_row(db, report), "events": service.events_of(db, report.id, internal=True)}


def _sim_number(user: User) -> str:
    """A fictional WhatsApp number per desk user: +91 0000 …, which no real mobile can have."""
    return f"910000{user.id:06d}"


def _chat_view(db: Session, user: User) -> dict:
    chat = db.scalar(select(CitizenChat).where(CitizenChat.wa_hash == whatsapp.wa_hash(_sim_number(user)), CitizenChat.is_demo.is_(True)))
    if chat is None:
        return {"number": "+" + _sim_number(user), "state": "new", "messages": []}
    rows = db.scalars(select(CitizenMessage).where(CitizenMessage.chat_id == chat.id).order_by(CitizenMessage.id))
    msgs = [{"id": m.id, "direction": m.direction, "text": m.text, "status": m.status, "detail": m.detail, "at": m.at.isoformat()} for m in rows]
    if chat.report_id:
        # Later updates on the report go to the same number, like a real WhatsApp thread.
        updates = list(db.scalars(select(CitizenMessage).where(CitizenMessage.report_id == chat.report_id, CitizenMessage.kind == "update")
                                  .order_by(CitizenMessage.id)))
        retried = {m.retry_of for m in updates if m.retry_of}
        for m in (u for u in updates if u.id not in retried):  # each update once, at its latest attempt
            msgs.append({"id": m.id, "direction": "out", "text": m.text, "status": m.status, "detail": m.detail, "at": m.at.isoformat()})
        msgs.sort(key=lambda x: (x["at"], x["id"]))
    return {"number": "+" + _sim_number(user), "state": chat.state, "report_id": chat.report_id, "messages": msgs}


@router.get("/whatsapp-simulator")
def simulator_view(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return _chat_view(db, user)


class SimIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["text", "location", "image"]
    text: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    photo_b64: str | None = None


@router.post("/whatsapp-simulator")
def simulator_send(body: SimIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Demo only: the same conversation a citizen has on WhatsApp, with a fictional number."""
    message: dict = {"type": body.type}
    if body.type == "text":
        message["text"] = body.text or ""
    elif body.type == "location":
        if body.latitude is None or body.longitude is None:
            raise HTTPException(422, "A location needs latitude and longitude")
        message.update(latitude=body.latitude, longitude=body.longitude)
    else:
        try:
            message["data"] = base64.b64decode(body.photo_b64 or "", validate=True) or None
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(422, "The photo is not valid base64") from exc
    replies = whatsapp.handle(db, _sim_number(user), message, is_demo=True, at=utcnow())
    db.commit()
    return {"replies": replies, **_chat_view(db, user)}


@router.get("/{report_id}")
def get_report(report_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    report = _get(db, report_id)
    dups = db.scalars(select(CitizenReport).where(CitizenReport.duplicate_of == report.id).order_by(CitizenReport.id))
    out = {
        **service.desk_row(db, report),
        "events": service.events_of(db, report.id, internal=True),
        "messages": service.messages_of(db, report.id),
        "duplicate_list": [{"id": d.id, "ref": d.ref, "channel": d.channel, "created_at": d.created_at.isoformat(), "status": d.status} for d in dups],
        "photo_list": [{"n": i + 1, "width": p.get("width"), "height": p.get("height")} for i, p in enumerate(report.photos or [])],
    }
    chain.record(db, actor_id=user.id, action="view.citizen_report", entity="citizen_report", entity_id=report.id)
    db.commit()
    return out


@router.get("/{report_id}/photos/{n}")
def photo(report_id: int, n: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    report = _get(db, report_id)
    photos = report.photos or []
    if not 1 <= n <= len(photos) or store.head_object(photos[n - 1]["key"]) is None:
        raise HTTPException(404, "No such photo")
    chain.record(db, actor_id=user.id, action="view.citizen_photo", entity="citizen_report", entity_id=report.id, details={"n": n})
    db.commit()
    return Response(store.get_object(photos[n - 1]["key"]), media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


class PlaceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)


@router.post("/{report_id}/place")
def place(report_id: int, body: PlaceIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """A report with no place: an official puts it on the map. Its incident and satellite review follow (D-063)."""
    report = _get(db, report_id)
    try:
        with db.begin_nested():
            service.place_by_official(db, report, user, body.lon, body.lat, utcnow())
    except service.CitizenError as exc:
        raise _fail(exc) from exc
    db.commit()
    return get_report(report_id, user, db)
