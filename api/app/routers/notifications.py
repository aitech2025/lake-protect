"""Notifications (DECISIONS.md D-059).

Everyone:
- GET  /notifications                 my inbox (newest first), for one dataset
- GET  /notifications/count           how many wait for my acknowledgement
- POST /notifications/{id}/ack        acknowledge one (and its reminders)

Admin:
- GET  /notifications/deliveries      the delivery log: every notification, every channel, its status
- GET  /notifications/channels        is each outside channel ready to send?
- POST /notifications/digests         send the weekly digest now
- POST /notifications/run             run follow-ups and the outbox now (the notifier does it every minute)
"""
from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.clock import utcnow
from app.db import db_guard, get_db
from app.enums import Role
from app.models import Notification, User
from app.notify import channels, service
from app.security import current_user, require_roles

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def inbox(
    pending: bool = False,
    alert_id: int | None = None,
    limit: int = 100,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    q = select(Notification).where(Notification.user_id == user.id)
    if pending:
        q = q.where(*service.pending_filter())
    if alert_id is not None:
        q = q.where(Notification.alert_id == alert_id)
    notes = db.scalars(q.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(max(1, min(limit, 500)))).all()
    deliveries = service.deliveries_for(db, [n.id for n in notes])
    chain.record(db, actor_id=user.id, action="view.notifications", entity="notification",
                 details={"pending": pending, "alert_id": alert_id, "count": len(notes)})
    db.commit()
    return {"items": [service.as_dict(n, deliveries.get(n.id)) for n in notes],
            "unacknowledged": service.unacknowledged_count(db, user)}


@router.get("/count")
def count(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return {"unacknowledged": service.unacknowledged_count(db, user)}


@router.post("/{notification_id}/ack")
def acknowledge(notification_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    note = db.get(Notification, notification_id)
    if note is None or note.user_id != user.id:
        raise HTTPException(404, "Notification not found")
    with db_guard(db):
        try:
            n = service.acknowledge(db, note, user, utcnow())
        except service.Refused as exc:
            raise HTTPException(exc.status, exc.message) from exc
        db.commit()
    return {"acknowledged": n, "acknowledged_at": note.acknowledged_at.isoformat() if note.acknowledged_at else None}


_LOG = text(
    """
    SELECT n.id, n.kind::text AS kind, n.subject, n.created_at, n.alert_id, n.week, n.acknowledged_at, n.ack_via, n.needs_ack,
           u.id AS user_id, u.name AS user_name, u.role::text AS user_role,
           d.channel, d.status, d.attempt, d.to_masked, d.detail, d.at AS delivery_at
    FROM notifications n JOIN users u ON u.id = n.user_id
    LEFT JOIN LATERAL (
        SELECT DISTINCT ON (channel) channel, status, attempt, to_masked, detail, at
        FROM notification_deliveries WHERE notification_id = n.id ORDER BY channel, id DESC) d ON true
    WHERE (CAST(:status AS text) IS NULL OR d.status = CAST(:status AS text))
      AND (CAST(:channel AS text) IS NULL OR d.channel = CAST(:channel AS text))
    ORDER BY n.created_at DESC, n.id DESC, d.channel
    LIMIT :n
    """
)


@router.get("/deliveries")
def delivery_log(
    status: str | None = None,
    channel: str | None = None,
    limit: int = 300,
    user: User = Depends(require_roles(Role.admin)),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.execute(_LOG, {"status": status, "channel": channel, "n": max(1, min(limit, 2000))}).mappings().all()
    totals = db.execute(text(
        """
        SELECT d.channel, d.status, count(*) AS n FROM (
            SELECT DISTINCT ON (nd.notification_id, nd.channel) nd.channel, nd.status
            FROM notification_deliveries nd
            ORDER BY nd.notification_id, nd.channel, nd.id DESC) d
        GROUP BY 1, 2 ORDER BY 1, 2
        """)).mappings().all()
    chain.record(db, actor_id=user.id, action="view.deliveries", entity="notification", details={"count": len(rows)})
    db.commit()
    return {"items": [dict(r) for r in rows], "totals": [dict(t) for t in totals], "channels": channels.status()}


@router.get("/channels")
def channel_status(user: User = Depends(require_roles(Role.admin))) -> dict:
    return {"channels": channels.status()}


class DigestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    week: str | None = Field(default=None, pattern=r"^[0-9]{4}-W[0-9]{2}$")


@router.post("/digests", status_code=201)
def send_digests(body: DigestIn, user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> dict:
    week = body.week or service.latest_week(db)
    if week is None:
        raise HTTPException(409, "No weekly screen has run yet")
    with db_guard(db):
        out = service.send_digests(db, week, utcnow())
        out["deliveries"] = service.send_pending(db, utcnow())
        chain.record(db, actor_id=user.id, action="notify.digest_requested", entity="notification", details={"week": week, "sent": out["sent"]})
        db.commit()
    return out


@router.post("/run")
def run_now(user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> dict:
    with db_guard(db):
        out = service.tick(db, utcnow())
        chain.record(db, actor_id=user.id, action="notify.run_requested", entity="notification", details={k: v for k, v in out.items() if k != "deliveries"})
        db.commit()
    return out
