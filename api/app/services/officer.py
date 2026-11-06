"""Officer record (section 9.1): notice, hearing, order and action references. No suggested outcome."""
from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.audit import chain
from app.clock import as_utc
from app.models import Alert, OfficerRecord, User
from app.workflow import state_machine as sm

DATE_FIELDS = ("notice_date", "hearing_date", "order_date", "action_date")
REF_FIELDS = ("notice_ref", "order_ref")


class OfficerRefused(Exception):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.message = message
        self.status = status


def add(db: Session, alert: Alert, user: User, fields: dict, *, record_action: bool = False, at: dt.datetime | None = None) -> dict:
    at = as_utc(at)
    if alert.state != "WITH_OFFICER":
        raise OfficerRefused(f"Officer records are added while the alert is with the officer (alert is {alert.state})", 409)
    try:
        dates = {k: (v if isinstance(v, dt.date) else dt.date.fromisoformat(v)) if v else None for k, v in fields.items() if k in DATE_FIELDS}
    except ValueError as exc:
        raise OfficerRefused(f"Dates must be YYYY-MM-DD: {exc}") from exc
    if not any(fields.get(k) for k in (*REF_FIELDS, *DATE_FIELDS)):
        raise OfficerRefused("Give at least one notice, hearing, order or action reference")
    rec = OfficerRecord(alert_id=alert.id, officer_id=user.id, notice_ref=fields.get("notice_ref"), order_ref=fields.get("order_ref"),
                        action_summary=fields.get("action_summary"), created_at=at, **dates)
    db.add(rec)
    db.flush()
    chain.record(db, actor_id=user.id, action="officer_record.added", entity="alert", entity_id=alert.id,
                 details={"officer_record_id": rec.id, **{k: str(v) for k, v in fields.items() if v}}, at=at)
    result = {"id": rec.id, "state": alert.state}
    if record_action:
        step = sm.transition(db, alert, "ACTION_RECORDED", actor=user, data={"officer_record_id": rec.id}, at=at)
        result.update(state=alert.state, transition=step)
    return result
