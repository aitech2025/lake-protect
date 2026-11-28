"""Records: permits, authorised works and court cases, with CSV import (section 9.1, 9.5)."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit import chain
from app.db import db_guard, get_db
from app.enums import Role
from app.models import User
from app.security import require_roles
from app.services import records as rec_svc
from app.workflow import incidents as lifecycle

router = APIRouter(prefix="/records", tags=["records"])

_TABLE = {"permits": "permits", "works": "authorised_works", "court-cases": "court_cases"}


@router.get("/{kind}")
def list_records(kind: str, user: User = Depends(require_roles(Role.admin, Role.senior_official)), db: Session = Depends(get_db)) -> dict:
    if kind not in _TABLE:
        raise HTTPException(404, "Unknown record kind")
    rows = db.execute(text(f"SELECT t.*, ST_AsGeoJSON(t.geom)::json AS geometry FROM {_TABLE[kind]} t ORDER BY t.id")).mappings().all()
    items = [{k: v for k, v in r.items() if k != "geom"} for r in rows]
    chain.record(db, actor_id=user.id, action="view.records", entity=kind, details={"count": len(items)})
    db.commit()
    return {"kind": kind, "items": items}


@router.post("/{kind}/import", status_code=201)
async def import_records(kind: str, file: UploadFile = File(...), user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> dict:
    content = await file.read()
    with db_guard(db):
        try:
            ids = rec_svc.parse_and_insert(db, kind, content)
        except rec_svc.ImportError_ as exc:
            db.rollback()
            raise HTTPException(422, str(exc)) from exc
        court = lifecycle.court_hits(db) if kind == "court-cases" else []
        chain.record(db, actor_id=user.id, action="records.imported", entity=kind, details={"ids": ids, "file": file.filename, "open_incidents_with_court_matter": court})
        db.commit()
    return {"kind": kind, "imported": len(ids), "ids": ids, "open_incidents_with_court_matter": court}
