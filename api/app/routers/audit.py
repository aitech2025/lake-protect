"""Audit view (section 9.1): the full log, the chain check, and a random sample of closures."""
import random

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit import chain
from app.db import get_db
from app.enums import Role
from app.models import User
from app.security import require_roles

router = APIRouter(prefix="/audit", tags=["audit"])
READERS = (Role.auditor, Role.admin)


@router.get("")
def list_audit(
    entity: str | None = None,
    entity_id: str | None = None,
    actor: int | None = None,
    include_views: bool = False,
    limit: int = 200,
    user: User = Depends(require_roles(*READERS)),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.execute(
        text(
            """
            SELECT l.id, l.actor_id, coalesce(u.name, 'System') AS actor, coalesce(u.role::text, 'system') AS actor_role,
                   l.action, l.entity, l.entity_id, l.details, l.at, l.prev_hash, l.hash
            FROM audit_log l LEFT JOIN users u ON u.id = l.actor_id
            WHERE (CAST(:entity AS text) IS NULL OR l.entity = :entity)
              AND (CAST(:eid AS text) IS NULL OR l.entity_id = :eid)
              AND (CAST(:actor AS bigint) IS NULL OR l.actor_id = :actor)
              AND (:views OR l.action NOT LIKE 'view.%')
            ORDER BY l.id DESC LIMIT :limit
            """
        ),
        {"entity": entity, "eid": entity_id, "actor": actor, "views": include_views, "limit": min(limit, 1000)},
    ).mappings().all()
    chain.record(db, actor_id=user.id, action="view.audit", entity="audit_log", details={"entity": entity, "entity_id": entity_id, "actor": actor})
    db.commit()
    return {"items": [dict(r) for r in rows]}


@router.get("/verify")
def verify(user: User = Depends(require_roles(*READERS)), db: Session = Depends(get_db)) -> dict:
    result = chain.verify(db)
    chain.record(db, actor_id=user.id, action="view.audit_verify", entity="audit_log", details={"ok": result["ok"], "rows_checked": result["rows_checked"]})
    db.commit()
    return result


@router.get("/closure-sample")
def closure_sample(month: str, n: int = 5, user: User = Depends(require_roles(*READERS)), db: Session = Depends(get_db)) -> dict:
    """Section 10: a monthly random sample of closures to re-check. Seeded by month, so it is repeatable."""
    rows = db.execute(
        text(
            """
            SELECT DISTINCT ON (l.entity_id) l.entity_id::bigint AS alert_id, a.code, l.details->>'to' AS closed_as, l.at
            FROM audit_log l JOIN alerts a ON a.id = l.entity_id::bigint
            WHERE l.entity = 'alert' AND l.action = 'alert.transition' AND l.details->>'to' LIKE 'CLOSED_%'
              AND to_char(l.at, 'YYYY-MM') = :month
            ORDER BY l.entity_id, l.id DESC
            """
        ),
        {"month": month},
    ).mappings().all()
    pool = [dict(r) for r in rows]
    sample = random.Random(month).sample(pool, min(n, len(pool)))
    chain.record(db, actor_id=user.id, action="view.closure_sample", entity="audit_log", details={"month": month, "sampled": [s["alert_id"] for s in sample]})
    db.commit()
    return {"month": month, "closures_in_month": len(pool), "sample": sample}
