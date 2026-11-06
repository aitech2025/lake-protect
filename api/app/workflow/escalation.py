"""Escalation on missed timers (CONTEXT.md section 6.6).

A miss is recorded once per timer (same state and due date), raises escalation_level, and is
never reset. A miss found when the alert moves on, before the scheduled job ran, is still recorded.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.clock import as_utc
from app.enums import AlertState
from app.models import Alert
from app.workflow import timers


def _due_key(alert: Alert) -> str:
    return alert.due_at.astimezone(dt.timezone.utc).isoformat()


def already_recorded(db: Session, alert: Alert) -> bool:
    return bool(
        db.scalar(
            text(
                """
                SELECT EXISTS (SELECT 1 FROM audit_log WHERE entity = 'alert' AND entity_id = :id
                    AND action = 'timer.missed' AND details->>'state' = :state AND details->>'due_at' = :due)
                """
            ),
            {"id": str(alert.id), "state": alert.state, "due": _due_key(alert)},
        )
    )


def record_miss(db: Session, alert: Alert, *, at: dt.datetime, detected: str) -> dict:
    alert.escalation_level = (alert.escalation_level or 0) + 1
    db.flush()
    details = {
        "state": alert.state,
        "due_at": _due_key(alert),
        "notify": timers.ON_MISS[AlertState(alert.state)],
        "escalation_level": alert.escalation_level,
        "detected": detected,
    }
    chain.record(db, actor_id=None, action="timer.missed", entity="alert", entity_id=alert.id, details=details, at=at)
    return {"alert_id": alert.id, **details}


def run(db: Session, now: dt.datetime | None = None) -> list[dict]:
    """The scheduled job: record every missed timer not yet recorded."""
    now = as_utc(now)
    timed = [s.value for s in timers.TIMED_STATES]
    overdue = db.scalars(select(Alert).where(Alert.state.in_(timed), Alert.due_at < now).order_by(Alert.id)).all()
    return [record_miss(db, a, at=now, detected="scheduled") for a in overdue if not already_recorded(db, a)]
