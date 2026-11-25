"""One-time passwords: a phone gets updates only once its owner proves it (CONTEXT.md 17.8).

Only hashes are stored. A code lasts 10 minutes and allows five tries; a phone can ask for three
codes an hour. A verified phone gets a token that lasts 30 minutes, to attach to the report.

- The code goes by SMS. Until the State's SMS gateway and DLT template exist,
  the portal says updates by SMS are not available yet, and the citizen keeps the reference
  number to check the status.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.citizen import sender
from app.citizen.service import CitizenError, TooMany, _key, normalise_phone, source_hash
from app.models import CitizenOtp

CODE_TTL = dt.timedelta(minutes=10)
TOKEN_TTL = dt.timedelta(minutes=30)
PER_HOUR = 3
MAX_TRIES = 5


class NotAvailable(CitizenError):
    status_code = 409


def _code_hash(phone: str, code: str) -> str:
    return hmac.new(_key(), f"otp:{phone}:{code}".encode(), hashlib.sha256).hexdigest()


def start(db: Session, phone_raw: str, *, at: dt.datetime) -> dict:
    phone = normalise_phone(phone_raw)
    if phone is None:
        raise CitizenError("Give your mobile number")
    ph = source_hash(f"phone:{phone}")
    recent = db.scalar(select(func.count()).select_from(CitizenOtp).where(CitizenOtp.phone_hash == ph, CitizenOtp.created_at >= at - dt.timedelta(hours=1)))
    if (recent or 0) >= PER_HOUR:
        raise TooMany("Too many codes for this number. Please try again in an hour.")
    code = f"{secrets.randbelow(10**6):06d}"
    if not sender.sms_ready():
        raise NotAvailable("Updates by SMS are not available yet: the State's SMS gateway is not set up. "
                           "Keep your reference number to check the status on this site.")
    result = sender.send_sms(phone, "citizen_otp", {"code": code}, False)
    if result.status != "sent":
        raise NotAvailable(f"The code could not be sent: {result.detail}")
    db.add(CitizenOtp(phone_hash=ph, code_hash=_code_hash(phone, code), attempts=0, expires_at=at + CODE_TTL, is_demo=False, created_at=at))
    db.flush()
    out = {"sent": True, "to": sender.mask(phone), "expires_in": int(CODE_TTL.total_seconds())}
    return out


def verify(db: Session, phone_raw: str, code: str, at: dt.datetime) -> tuple[str | None, str | None]:
    """(token, None) when the code is right, else (None, why). Every try counts, right or wrong."""
    phone = normalise_phone(phone_raw)
    if phone is None:
        return None, "Give your mobile number"
    row = db.scalar(select(CitizenOtp).where(CitizenOtp.phone_hash == source_hash(f"phone:{phone}"), CitizenOtp.verified_at.is_(None),
                                             CitizenOtp.expires_at > at).order_by(CitizenOtp.id.desc()).limit(1))
    if row is None:
        return None, "The code has expired. Ask for a new one."
    if row.attempts >= MAX_TRIES:
        return None, "Too many tries. Ask for a new code."
    row.attempts += 1
    if not hmac.compare_digest(row.code_hash, _code_hash(phone, (code or "").strip())):
        db.flush()
        return None, "That code is not right."
    row.verified_at = at
    db.flush()
    return make_token(phone, at), None


def make_token(phone: str, at: dt.datetime) -> str:
    exp = int((at + TOKEN_TTL).timestamp())
    payload = f"{phone}|{exp}"
    sig = hmac.new(_key(), f"token:{payload}".encode(), hashlib.sha256).hexdigest()[:32]
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=") + "." + sig


def phone_from_token(token: str, at: dt.datetime) -> str:
    try:
        raw, sig = token.split(".", 1)
        payload = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode()
        phone, exp = payload.split("|")
    except (ValueError, UnicodeDecodeError) as exc:
        raise CitizenError("The phone check is not valid. Verify the number again.") from exc
    good = hmac.new(_key(), f"token:{payload}".encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(sig, good):
        raise CitizenError("The phone check is not valid. Verify the number again.")
    if int(exp) < at.timestamp():
        raise CitizenError("The phone check has expired. Verify the number again.")
    return phone
