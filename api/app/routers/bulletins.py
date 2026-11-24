"""GET /bulletins/{month}: the monthly page (section 9.4), from the database only."""
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import chain
from app.bulletin import render, stats
from app.clock import utcnow
from app.db import get_db
from app.enums import Role
from app.models import Bulletin, User
from app.security import require_roles
from app.storage import store

router = APIRouter(prefix="/bulletins", tags=["bulletins"])
READERS = (Role.admin, Role.viewer)


def _check(month: str) -> None:
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise HTTPException(422, "Month must be YYYY-MM")


@router.get("/{month}")
def get_bulletin(month: str, dataset: Literal["demo", "real"] = "demo", user: User = Depends(require_roles(*READERS)), db: Session = Depends(get_db)) -> dict:
    _check(month)
    out = stats.bulletin(db, month, demo=dataset == "demo")
    out["map_svg"] = render.map_svg(db, out, demo=dataset == "demo")
    chain.record(db, actor_id=user.id, action="view.bulletin", entity="bulletin", entity_id=month, details={"dataset": dataset})
    db.commit()
    return out


@router.get("/{month}/pdf")
def get_bulletin_pdf(month: str, dataset: Literal["demo", "real"] = "demo", user: User = Depends(require_roles(*READERS)), db: Session = Depends(get_db)) -> Response:
    """Builds the one-page PDF from the current records and keeps a copy with its figures."""
    _check(month)
    out = stats.bulletin(db, month, demo=dataset == "demo")
    pdf = render.render_pdf(out, render.map_svg(db, out, demo=dataset == "demo"))
    now = utcnow()
    key = store.put_object(f"bulletins/{dataset}/{month}/{now.strftime('%Y%m%dT%H%M%S')}.pdf", pdf)
    row = Bulletin(month=month, stats={k: v for k, v in out.items() if k != "new_alert_points"}, pdf_path=key, generated_at=now)
    db.add(row)
    db.flush()
    chain.record(db, actor_id=user.id, action="export.bulletin_pdf", entity="bulletin", entity_id=month, details={"dataset": dataset, "bulletin_id": row.id})
    db.commit()
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="lake-protect-{month}.pdf"'})


@router.get("")
def list_bulletins(user: User = Depends(require_roles(*READERS)), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Bulletin).order_by(Bulletin.generated_at.desc()).limit(24))
    return [{"id": b.id, "month": b.month, "generated_at": b.generated_at.isoformat(), "counts": b.stats.get("counts")} for b in rows]
