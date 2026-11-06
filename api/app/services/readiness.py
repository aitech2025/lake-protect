"""Case-readiness checklist (section 6.7): yes, no or not applicable, with evidence and who checked it."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import chain
from app.clock import as_utc
from app.models import Alert, ReadinessItem, User
from app.workflow.state_machine import READINESS_KEYS


def record(db: Session, alert: Alert, user: User, item_key: str, status: str, evidence_ref: str | None, at: dt.datetime | None = None) -> ReadinessItem:
    if item_key not in READINESS_KEYS:
        raise ValueError(f"Unknown checklist item {item_key}")
    at = as_utc(at)
    item = db.scalar(select(ReadinessItem).where(ReadinessItem.alert_id == alert.id, ReadinessItem.item_key == item_key))
    before = None if item is None else {"status": item.status, "evidence_ref": item.evidence_ref, "checked_by": item.checked_by}
    if item is None:
        item = ReadinessItem(alert_id=alert.id, item_key=item_key, status=status, evidence_ref=evidence_ref, checked_by=user.id, checked_at=at)
        db.add(item)
    else:
        item.status, item.evidence_ref, item.checked_by, item.checked_at = status, evidence_ref, user.id, at
    db.flush()
    chain.record(db, actor_id=user.id, action="readiness.recorded", entity="alert", entity_id=alert.id,
                 details={"item_key": item_key, "before": before, "after": {"status": status, "evidence_ref": evidence_ref}}, at=at)
    return item
