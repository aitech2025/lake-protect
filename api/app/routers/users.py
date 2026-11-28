"""Officials and the admin: roles, contact details, channels and areas (DECISIONS.md D-059, D-067). Admin only.

- GET /users                 every active account, with its role, areas, channels and contact details
- PATCH /users/{id}          change email, phone, channels, or the role (persona)
- PUT /users/{id}/areas      replace the districts or mandals a district or field officer covers

Contact details are personal data: only the admin sees them, and the audit log records that they
changed, never their values.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.clock import utcnow
from app.db import db_guard, get_db
from app.enums import Channel, Role
from app.models import OfficialArea, User
from app.notify import routing, service
from app.security import require_roles

router = APIRouter(tags=["users"])

# Personas whose work is limited to areas (D-067).
AREA_ROLES = (Role.district_officer.value, Role.field_officer.value)
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
    role: Role | None = None
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
    role_change = None
    if body.role is not None and body.role.value != target.role:
        if target.id == user.id:
            raise HTTPException(422, "You cannot change your own role")
        if target.role == Role.admin.value and len(routing.admins(db)) <= 1:
            raise HTTPException(422, "Keep at least one admin")
        open_visits = db.scalar(text(
            "SELECT count(*) FROM alerts al WHERE al.state IN ('FIELD_VISIT') AND (SELECT ia.field_officer_id FROM incident_assignments ia "
            "WHERE ia.alert_id = al.id ORDER BY ia.id DESC LIMIT 1) = :u"), {"u": target.id})
        if target.role == Role.field_officer.value and open_visits:
            raise HTTPException(422, f"{target.name} has {open_visits} open field visit(s): reassign them first")
        role_change = {"from": target.role, "to": body.role.value}
        target.role = body.role.value
        if body.role.value not in AREA_ROLES:
            db.execute(delete(OfficialArea).where(OfficialArea.user_id == target.id))
        changed.append("role")
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
        if role_change:
            chain.record(db, actor_id=user.id, action="user.role_changed", entity="user", entity_id=target.id, details=role_change)
        if set(changed) - {"role"}:
            chain.record(db, actor_id=user.id, action="user.contact_changed", entity="user", entity_id=target.id,
                         details={"fields": [c for c in changed if c != "role"], "channels": list(target.channels)})
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
    if target.role not in AREA_ROLES:
        raise HTTPException(422, "Areas are for district and field officers: the admin and senior officials see the whole State")
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
