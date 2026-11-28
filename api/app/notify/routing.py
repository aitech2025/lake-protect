"""Who is notified about an asset's incidents (DECISIONS.md D-059, D-067).

An incident goes to every active district officer whose area holds its asset, and to every active
senior official. An area is a whole district, or one mandal within a district. Names match without
regard to case or surrounding spaces. Where no district officer covers the asset, the admin is told
too, so the gap can be fixed on the Officials page. Who may look is decided in app.access.
"""
from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.enums import Role
from app.models import Asset, OfficialArea, User

# Does official u cover the asset a? Used in every query that needs an official's assets.
COVERS = """EXISTS (
    SELECT 1 FROM official_areas oa
    WHERE oa.user_id = {user} AND lower(btrim(oa.district)) = lower(btrim({asset}.district))
      AND (oa.mandal IS NULL OR lower(btrim(oa.mandal)) = lower(btrim(coalesce({asset}.mandal, '')))))"""


def admins(db: Session) -> list[User]:
    return list(db.scalars(select(User).where(User.role == Role.admin.value, User.is_active.is_(True)).order_by(User.id)))


def seniors(db: Session) -> list[User]:
    return list(db.scalars(select(User).where(User.role == Role.senior_official.value, User.is_active.is_(True)).order_by(User.id)))


def officials_for(db: Session, asset: Asset, role: str = Role.district_officer.value) -> list[User]:
    """The active district officers (or field officers) whose area holds the asset."""
    if not (asset.district or "").strip():
        return []
    ids = db.scalars(
        text(f"SELECT u.id FROM users u, assets a WHERE a.id = :a AND u.is_active AND u.role = CAST(:role AS role) AND {COVERS.format(user='u.id', asset='a')} ORDER BY u.id"),
        {"a": asset.id, "role": role},
    ).all()
    return [db.get(User, i) for i in ids]


def areas_of(db: Session, user_id: int) -> list[dict]:
    rows = db.scalars(select(OfficialArea).where(OfficialArea.user_id == user_id).order_by(OfficialArea.district, OfficialArea.mandal.nulls_first()))
    return [{"district": r.district, "mandal": r.mandal} for r in rows]


def area_label(area: dict) -> str:
    return f"{area['mandal']} mandal, {area['district']}" if area.get("mandal") else area["district"]


def scope_sql(user: User, asset_alias: str = "a") -> str:
    """SQL condition: the assets this user hears about. The admin and senior officials hear about all of them."""
    if user.role in (Role.admin.value, Role.senior_official.value):
        return "TRUE"
    return COVERS.format(user=int(user.id), asset=asset_alias)
