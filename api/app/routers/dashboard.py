"""The drill-down dashboard (DECISIONS.md D-060).

- GET /dashboard   figures for one level (state, district, mandal or village), the next level's
                   rows, an eight-week trend and map pins. Every signed-in user sees every area.
- GET /areas       the districts and mandals that hold assets, for the admin's area picker.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.audit import chain
from app.clock import utcnow
from app.db import get_db
from app.enums import Role
from app.models import User
from app.security import current_user, require_roles
from app.services import dashboard

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def get_dashboard(
    dataset: Literal["demo", "real"] = "demo",
    district: str | None = None,
    mandal: str | None = None,
    village: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    if (mandal is not None and district is None) or (village is not None and mandal is None):
        raise HTTPException(422, "Give the area from the top: a mandal needs its district, a village its mandal")
    out = dashboard.overview(db, user, is_demo=dataset == "demo", district=district, mandal=mandal, village=village, now=utcnow())
    chain.record(db, actor_id=user.id, action="view.dashboard", entity="dashboard", details={"dataset": dataset, **out["filters"]})
    db.commit()
    return out


@router.get("/areas")
def get_areas(user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> dict:
    return {"items": dashboard.known_areas(db)}
