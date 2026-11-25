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
from sqlalchemy.orm import Session

from app.citizen import otp, sender, service, texts, whatsapp
from app.clock import utcnow
from app.db import get_db

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
def config(dataset: Literal["demo", "real"] = "real", db: Session = Depends(get_db)) -> dict:
    return {
        "dataset": dataset,
        "languages": list(texts.LANGS),
        "whats": [{"key": k, "label": texts.WHAT[k]} for k in texts.WHAT_ORDER],
        "updates": sender.status(),
        "stats": service.stats(db, dataset == "demo"),
        "limits": {"photos": service.MAX_PHOTOS, "photo_mb": service.MAX_PHOTO_BYTES // (1024 * 1024), "description": 1000},
        "helpline": "1070",
    }


class ReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset: Literal["demo", "real"] = "real"
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
                is_demo=body.dataset == "demo",
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
    dataset: Literal["demo", "real"] = "real"


@router.post("/otp")
def otp_start(body: OtpIn, db: Session = Depends(get_db)) -> dict:
    try:
        out = otp.start(db, body.phone, is_demo=body.dataset == "demo", at=utcnow())
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
        whatsapp.handle(db, wa_id, message, is_demo=False, at=utcnow())
        handled += 1
    db.commit()
    return {"handled": handled}
