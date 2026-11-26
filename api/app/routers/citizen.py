"""The public side of citizen reporting (CONTEXT.md 17.8; DECISIONS.md D-062). No sign-in.

- GET  /citizen/config              what can be reported, which update channels work, last 30 days' figures
- POST /citizen/reports             a report from the web portal (form data: `data` JSON and up to 3 photos)
- GET  /citizen/reports/{ref}       its status and history, by reference
- POST /citizen/otp                 a one-time password to verify a phone for updates
- POST /citizen/otp/verify          the code, for a token to attach to the report
- GET  /citizen/whatsapp/webhook    the WhatsApp Cloud API verification handshake
- POST /citizen/whatsapp/webhook    incoming WhatsApp messages, signed with the app secret
"""
from __future__ import annotations

import os
import time
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.citizen import otp, sender, service, texts, whatsapp
from app.clock import utcnow
from app.db import get_db
from app.enums import Role
from app.models import CitizenChat, CitizenReport, User
from app.security import require_roles

router = APIRouter(prefix="/citizen", tags=["citizen"])

_LOOKUPS: dict[str, list[float]] = {}
LOOKUPS_PER_MINUTE = 30


def source_of(request: Request) -> str:
    """A salted hash of the caller's address. The last X-Forwarded-For entry is the one nginx saw."""
    xff = request.headers.get("x-forwarded-for")
    ip = xff.split(",")[-1].strip() if xff else (request.client.host if request.client else "unknown")
    return service.source_hash(f"ip:{ip}")


def _limit_lookups(source: str) -> None:
    now = time.monotonic()
    recent = [t for t in _LOOKUPS.get(source, []) if now - t < 60]
    if len(recent) >= LOOKUPS_PER_MINUTE:
        raise HTTPException(429, "Too many lookups. Please wait a minute.")
    recent.append(now)
    _LOOKUPS[source] = recent


def _fail(exc: service.CitizenError) -> HTTPException:
    return HTTPException(exc.status_code, str(exc))


@router.get("/config")
def config(db: Session = Depends(get_db)) -> dict:
    return {
        "languages": list(texts.LANGS),
        "whats": [{"key": k, "label": texts.WHAT[k]} for k in texts.WHAT_ORDER],
        "updates": sender.status(),
        "whatsapp_simulator": settings.enable_whatsapp_simulator,
        "stats": service.stats(db),
        "limits": {"photos": service.MAX_PHOTOS, "photo_mb": service.MAX_PHOTO_BYTES // (1024 * 1024), "description": 1000},
        "helpline": "1070",
    }


class ReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Literal["en", "te"] = "en"
    what: str
    lon: float | None = Field(default=None, ge=-180, le=180)
    lat: float | None = Field(default=None, ge=-90, le=90)
    location_text: str | None = None
    description: str | None = None
    name: str | None = None
    phone_token: str | None = None


@router.post("/reports", status_code=201)
async def submit(request: Request, data: str = Form(...), photos: list[UploadFile] = File(default=[]), db: Session = Depends(get_db)) -> dict:
    try:
        body = ReportIn.model_validate_json(data)
    except ValidationError as exc:
        raise HTTPException(422, "The report form is not complete") from exc
    if body.lon is None or body.lat is None:
        raise HTTPException(422, "Mark the place on the map")
    now = utcnow()
    blobs = [await f.read(service.MAX_PHOTO_BYTES + 1) for f in photos[: service.MAX_PHOTOS + 1]]
    try:
        phone = otp.phone_from_token(body.phone_token, now) if body.phone_token else None
        with db.begin_nested():
            report = service.submit(
                db, channel="web", language=body.language, what=body.what, at=now, source=source_of(request),
                lon=body.lon, lat=body.lat, location_text=body.location_text, description=body.description, photos=blobs,
                reporter_name=body.name, phone=phone, phone_verified_via="otp" if phone else None, wants_updates=bool(phone),
            )
    except service.CitizenError as exc:
        raise _fail(exc) from exc
    db.commit()
    return service.public_view(db, report.ref)


@router.get("/reports/{ref}")
def status(ref: str, request: Request, db: Session = Depends(get_db)) -> dict:
    _limit_lookups(source_of(request))
    if not service.REF_RE.fullmatch(ref.strip().upper()):
        raise HTTPException(404, "No report has that reference")
    view = service.public_view(db, ref)
    if view is None:
        raise HTTPException(404, "No report has that reference")
    return view


class OtpIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone: str


@router.post("/otp")
def otp_start(body: OtpIn, db: Session = Depends(get_db)) -> dict:
    try:
        out = otp.start(db, body.phone, at=utcnow())
    except service.CitizenError as exc:
        raise _fail(exc) from exc
    db.commit()
    return out


class VerifyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone: str
    code: str


@router.post("/otp/verify")
def otp_verify(body: VerifyIn, db: Session = Depends(get_db)) -> dict:
    try:
        token, why = otp.verify(db, body.phone, body.code, utcnow())
    except service.CitizenError as exc:
        raise _fail(exc) from exc
    db.commit()  # a wrong try counts too
    if token is None:
        raise HTTPException(422, why)
    return {"token": token}


@router.get("/whatsapp/webhook")
def whatsapp_verify(mode: str = Query("", alias="hub.mode"), token: str = Query("", alias="hub.verify_token"),
                    challenge: str = Query("", alias="hub.challenge")) -> PlainTextResponse:
    expected = os.environ.get("LP_WHATSAPP_VERIFY_TOKEN")
    if not expected or mode != "subscribe" or token != expected:
        raise HTTPException(403, "WhatsApp intake is not set up, or the token is wrong")
    return PlainTextResponse(challenge)


@router.post("/whatsapp/webhook")
async def whatsapp_incoming(request: Request, db: Session = Depends(get_db)) -> dict:
    if not os.environ.get("LP_WHATSAPP_APP_SECRET"):
        raise HTTPException(503, "WhatsApp intake is not set up: it needs the State's WhatsApp Business agreement")
    raw = await request.body()
    if not whatsapp.signature_ok(raw, request.headers.get("x-hub-signature-256")):
        raise HTTPException(403, "The message is not signed with the app secret")
    import json

    handled = 0
    for wa_id, message in whatsapp.parse_webhook(json.loads(raw or b"{}")):
        whatsapp.handle(db, wa_id, message, at=utcnow())
        handled += 1
    db.commit()
    return {"handled": handled}


class WhatsAppSimulatorIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sender: str = Field(default="15550000000", pattern=r"^1555[0-9]{7,9}$")
    type: Literal["text", "location"]
    text: str | None = Field(default=None, max_length=1000)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    latitude: float | None = Field(default=None, ge=-90, le=90)


@router.post("/whatsapp/simulator")
def whatsapp_simulator(body: WhatsAppSimulatorIn, user: User = Depends(require_roles(Role.admin)),
                       db: Session = Depends(get_db)) -> dict:
    """Local-only WhatsApp test UI. Records are isolated with is_demo and never notify officials."""
    if not settings.enable_whatsapp_simulator:
        raise HTTPException(404, "The WhatsApp simulator is disabled")
    if body.type == "text":
        if body.text is None:
            raise HTTPException(422, "Enter a text message")
        message = {"type": "text", "text": body.text}
    else:
        if body.latitude is None or body.longitude is None:
            raise HTTPException(422, "Choose a location on the map")
        message = {"type": "location", "latitude": body.latitude, "longitude": body.longitude}
    replies = whatsapp.handle(db, body.sender, message, at=utcnow(), is_demo=True)
    chat = db.scalar(select(CitizenChat).where(
        CitizenChat.wa_hash == whatsapp.wa_hash(body.sender), CitizenChat.is_demo.is_(True)))
    report_out = None
    if chat and chat.report_id:
        report = db.get(CitizenReport, chat.report_id)
        if report:
            coords = db.execute(text("SELECT ST_X(geom), ST_Y(geom) FROM citizen_reports WHERE id = :id"), {"id": report.id}).one()
            report_out = {"id": report.id, "ref": report.ref, "alert_id": report.alert_id,
                          "longitude": coords[0], "latitude": coords[1], "what": report.what,
                          "description": report.description, "location_text": report.location_text}
    db.commit()
    return {"replies": replies, "state": chat.state if chat else "new", "report": report_out}
