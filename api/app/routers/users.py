"""Officials and the admin: contact details, channels and areas (DECISIONS.md D-059). Admin only.

- GET /users                 every active account, with its areas, channels and contact details
- PATCH /users/{id}          change email, phone or channels
- PUT /users/{id}/areas      replace the districts or mandals an official covers

Contact details are personal data: only the admin sees them, and the audit log records that they
changed, never their values.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.audit import chain
from app.clock import utcnow
from app.db import db_guard, get_db
from app.enums import Channel, Role
from app.models import OfficialArea, User
from app.notify import routing, service
from app.security import require_roles

router = APIRouter(tags=["users"])

EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
PHONE = r"^\+[1-9][0-9]{7,14}$"
CHANNEL_ORDER = [c.value for c in Channel]


def _out(db: Session, u: User) -> dict:
    return {
        "id": u.id, "username": u.username, "name": u.name, "role": u.role, "language": u.language, "is_demo": u.is_demo,
        "email": u.email, "phone": u.phone, "channels": list(u.channels or []), "areas": routing.areas_of(db, u.id),
        "unacknowledged": service.unacknowledged_count(db, u),
    }


@router.get("/users")
def list_users(role: str | None = None, user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> list[dict]:
    q = select(User).where(User.is_active.is_(True)).order_by(User.role, User.name)
    if role:
        q = q.where(User.role == role)
    out = [_out(db, u) for u in db.scalars(q)]
    chain.record(db, actor_id=user.id, action="view.users", entity="user", details={"count": len(out)})
    db.commit()
    return out


class ContactIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str | None = Field(default=None, pattern=EMAIL, max_length=200)
    phone: str | None = Field(default=None, pattern=PHONE)
    channels: list[Channel] | None = None
    clear: list[str] = []  # fields to empty: "email", "phone"

    @field_validator("channels")
    @classmethod
    def in_app_always(cls, v):
        if v is not None and Channel.in_app not in v:
            raise ValueError("The in-app inbox is always on")
        return v


def _target(db: Session, user_id: int) -> User:
    u = db.get(User, user_id)
    if u is None or not u.is_active:
        raise HTTPException(404, "User not found")
    return u


@router.patch("/users/{user_id}")
def update_contact(user_id: int, body: ContactIn, user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> dict:
    target = _target(db, user_id)
    if set(body.clear) - {"email", "phone"}:
        raise HTTPException(422, "Only email and phone can be cleared")
    changed = []
    for field in ("email", "phone"):
        value = None if field in body.clear else getattr(body, field)
        if value is None and field not in body.clear:
            continue
        if getattr(target, field) != value:
            setattr(target, field, value)
            changed.append(field)
    if body.channels is not None:
        wanted = sorted({c.value for c in body.channels}, key=CHANNEL_ORDER.index)
        if list(target.channels or []) != wanted:
            target.channels = wanted
            changed.append("channels")
    with db_guard(db):
        if changed:
            chain.record(db, actor_id=user.id, action="user.contact_changed", entity="user", entity_id=target.id,
                         details={"fields": changed, "channels": list(target.channels)})
        db.commit()
    return _out(db, target)


class AreaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    district: str = Field(min_length=1, max_length=120)
    mandal: str | None = Field(default=None, min_length=1, max_length=120)


class AreasIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    areas: list[AreaIn] = Field(max_length=50)


@router.put("/users/{user_id}/areas")
def set_areas(user_id: int, body: AreasIn, user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> dict:
    target = _target(db, user_id)
    if target.role != Role.viewer.value:
        raise HTTPException(422, "Areas are for officials: the admin is told about every incident")
    wanted, seen = [], set()
    for a in body.areas:
        key = (a.district.strip().lower(), (a.mandal or "").strip().lower())
        if key not in seen:
            seen.add(key)
            wanted.append({"district": a.district.strip(), "mandal": a.mandal.strip() if a.mandal else None})
    before = routing.areas_of(db, target.id)
    now = utcnow()
    with db_guard(db):
        db.execute(delete(OfficialArea).where(OfficialArea.user_id == target.id))
        for a in wanted:
            db.add(OfficialArea(user_id=target.id, district=a["district"], mandal=a["mandal"], added_by=user.id, added_at=now))
        db.flush()
        chain.record(db, actor_id=user.id, action="user.areas_changed", entity="user", entity_id=target.id,
                     details={"from": before, "to": wanted}, at=now)
        db.commit()
    return _out(db, target)
