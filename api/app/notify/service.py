"""Notifications to officials (DECISIONS.md D-059): what is sent, to whom, and when.

Events, called inside the same transaction as the change that causes them:
- incident_opened: a new incident that stays open. Its area's officials and every admin are told,
  and each must acknowledge it. Changes the legal check closes at once, and changes seen again on
  an open incident, notify no one: they appear in the weekly digest.
- incident_decided: the admin confirmed or dismissed an incident. The area's officials and every
  official who reviewed it are told. No acknowledgement is needed.
- acknowledgement: in the inbox, or by acting on the incident (a review, or the admin's step).
- citizen_report (D-062): a citizen's report in the area. Its area's officials and every admin are
  told; it needs acknowledgement unless it already sits on an incident. Recording a check on the
  report, or closing it, acknowledges it. Outside channels carry it by email only.

Follow-up, run by the notifier every minute (`python -m app.notify run`):
- 24 hours without an acknowledgement while the incident is still open or under review: a
  reminder to the same person, once.
- 48 hours without one from an official: every admin is told, once.

Outside channels never block the event: a notification queues one delivery per channel the person
wants, and the outbox sends them on the next run (app.notify.channels).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.clock import as_utc
from app.enums import Role
from app.models import Alert, Asset, Candidate, CitizenReport, IncidentReview, Notification, NotificationDelivery, User
from app.notify import channels, digest, messages, routing
from app.services import alert_view

REMIND_AFTER = dt.timedelta(hours=24)
ESCALATE_AFTER = dt.timedelta(hours=48)
MAX_ATTEMPTS = 3
RETRY_AFTER = dt.timedelta(minutes=5)
OUTSIDE = ("email", "sms", "whatsapp")


class Refused(Exception):
    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.message = message
        self.status = status


# Creating ---------------------------------------------------------------------------------------
def _queue(db: Session, note: Notification, user: User, at: dt.datetime) -> None:
    for channel in OUTSIDE:
        if channel not in (user.channels or []) or not channels.carries(channel, note.kind):
            continue
        if note.report_id and channel != "email":
            continue  # the SMS and WhatsApp templates are worded for incidents
        addr = channels.address(channel, user)
        masked = channels.mask_email(addr) if channel == "email" else channels.mask_phone(addr)
        if not addr:
            db.add(NotificationDelivery(notification_id=note.id, channel=channel, status="skipped", attempt=0, to_masked=None,
                                        detail="No email address on file" if channel == "email" else "No phone number on file", at=at))
        else:
            db.add(NotificationDelivery(notification_id=note.id, channel=channel, status="queued", attempt=0, to_masked=masked, at=at))


def create(db: Session, user: User, kind: str, payload: dict, *, at: dt.datetime, needs_ack: bool, is_demo: bool,
           alert_id: int | None = None, week: str | None = None, about_id: int | None = None, report_id: int | None = None) -> Notification:
    msg = messages.compose(kind, user.language, payload)
    note = Notification(user_id=user.id, kind=kind, alert_id=alert_id, report_id=report_id, week=week, about_id=about_id, subject=msg.subject,
                        body=msg.body, payload=payload, needs_ack=needs_ack, created_at=at, is_demo=is_demo)
    db.add(note)
    db.flush()
    _queue(db, note, user, at)
    return note


def _already(db: Session, user_id: int, kind: str, *, alert_id: int | None = None, about_id: int | None = None) -> bool:
    q = select(Notification.id).where(Notification.user_id == user_id, Notification.kind == kind)
    if alert_id is not None:
        q = q.where(Notification.alert_id == alert_id)
    if about_id is not None:
        q = q.where(Notification.about_id == about_id)
    return db.scalar(q.limit(1)) is not None


def _asset_of(db: Session, alert: Alert) -> Asset:
    return db.get(Asset, db.get(Candidate, alert.candidate_id).asset_id)


def incident_opened(db: Session, alert: Alert, at: dt.datetime | None = None) -> list[Notification]:
    at = as_utc(at)
    asset = _asset_of(db, alert)
    officials = routing.officials_for(db, asset)
    base = messages.incident_payload(alert_view.row_for(db, alert.id))
    out = []
    for user in officials + routing.admins(db):
        if _already(db, user.id, "incident_opened", alert_id=alert.id):
            continue
        payload = {**base, "unrouted": not officials} if user.role == Role.admin.value else base
        out.append(create(db, user, "incident_opened", payload, at=at, needs_ack=True, is_demo=alert.is_demo, alert_id=alert.id))
    chain.record(db, actor_id=None, action="notify.incident_opened", entity="alert", entity_id=alert.id,
                 details={"recipients": [n.user_id for n in out], "officials": len(officials), "area": base["area"]}, at=at)
    return out


def incident_decided(db: Session, alert: Alert, actor: User, note_text: str | None, at: dt.datetime | None = None) -> list[Notification]:
    at = as_utc(at)
    asset = _asset_of(db, alert)
    reviewers = db.scalars(select(User).join(IncidentReview, IncidentReview.reviewer_id == User.id)
                           .where(IncidentReview.alert_id == alert.id, User.is_active.is_(True)).distinct()).all()
    # An official's decision on a citizen's incident also goes to every admin (D-064).
    admins = routing.admins(db) if actor.role != Role.admin.value else []
    people = {u.id: u for u in [*routing.officials_for(db, asset), *reviewers, *admins] if u.id != actor.id}
    payload = {**messages.incident_payload(alert_view.row_for(db, alert.id)), "decision": alert.state, "note": note_text}
    out = [create(db, u, "incident_decided", payload, at=at, needs_ack=False, is_demo=alert.is_demo, alert_id=alert.id)
           for u in people.values() if not _already(db, u.id, "incident_decided", alert_id=alert.id)]
    if out:
        chain.record(db, actor_id=None, action="notify.incident_decided", entity="alert", entity_id=alert.id,
                     details={"recipients": [n.user_id for n in out], "decision": alert.state}, at=at)
    return out


# Acknowledging ----------------------------------------------------------------------------------
def satellite_review(db: Session, alert: Alert, at: dt.datetime | None = None, only: int | None = None) -> list[Notification]:
    """A citizen incident's satellite review is back (D-063): the people told about the incident hear the
    result. A look an official asked for goes to that official only (`only`, D-064)."""
    at = as_utc(at)
    asset = _asset_of(db, alert)
    base = messages.incident_payload(alert_view.row_for(db, alert.id))
    people = {u.id: u for u in routing.officials_for(db, asset) + routing.admins(db)}
    if only is not None:
        people = {only: db.get(User, only)}
    return [create(db, u, "satellite_review", base, at=at, needs_ack=False, is_demo=alert.is_demo, alert_id=alert.id) for u in people.values()]


def citizen_report(db: Session, report: CitizenReport, at: dt.datetime | None = None) -> list[Notification]:
    """A citizen's report: the area's officials and every admin. Duplicates of a report tell no one again."""
    from app.citizen import texts

    at = as_utc(at)
    asset = db.get(Asset, report.asset_id) if report.asset_id else None
    officials = routing.officials_for(db, asset) if asset else []
    alert = db.get(Alert, report.alert_id) if report.alert_id else None
    payload = {
        "report": True, "report_id": report.id, "code": report.ref,
        "asset_name": asset.name if asset else texts.PLACE_UNWATCHED["en"],
        "asset_name_te": (asset.name_te or asset.name) if asset else texts.PLACE_UNWATCHED["te"],
        "area": {"district": asset.district, "mandal": asset.mandal, "village": asset.village} if asset else None,
        "what": report.what, "what_label": texts.WHAT[report.what]["en"], "what_te": texts.WHAT[report.what]["te"],
        "description": (report.description or "")[:300], "channel": report.channel, "opened_at": report.created_at.isoformat(),
        "link": messages.link(f"/reports/{report.id}"), "incident_code": alert.code if alert else None,
        "not_watched": asset is None, "no_place": report.geom is None, "repeat_false": "repeat_false_reports" in (report.flags or []),
        "unrouted": not officials,
    }
    people = {u.id: u for u in officials + routing.admins(db)}
    out = []
    for user in people.values():
        if db.scalar(select(Notification.id).where(Notification.user_id == user.id, Notification.report_id == report.id,
                                                   Notification.about_id.is_(None))):
            continue
        out.append(create(db, user, "citizen_report", payload, at=at, needs_ack=report.alert_id is None, is_demo=report.is_demo,
                          report_id=report.id))
    return out


def _ack(db: Session, notes: list[Notification], user: User, at: dt.datetime, via: str, alert_id: int | None) -> int:
    for n in notes:
        n.acknowledged_at = max(at, n.created_at)
        n.ack_via = via
    db.flush()
    if notes:
        chain.record(db, actor_id=user.id, action="notification.acknowledged", entity="alert" if alert_id else "notification",
                     entity_id=alert_id or notes[0].id, details={"notifications": [n.id for n in notes], "via": via}, at=at)
    return len(notes)


def _open_for(db: Session, user_id: int, alert_id: int) -> list[Notification]:
    return list(db.scalars(select(Notification).where(
        Notification.user_id == user_id, Notification.alert_id == alert_id, Notification.needs_ack.is_(True),
        Notification.acknowledged_at.is_(None)).order_by(Notification.id)))


def acknowledge(db: Session, note: Notification, user: User, at: dt.datetime | None = None) -> int:
    """From the inbox. Acknowledging one notification about an incident acknowledges the reminders too."""
    at = as_utc(at)
    if note.user_id != user.id:
        raise Refused("Not your notification", 404)
    if not note.needs_ack:
        raise Refused("This notification needs no acknowledgement", 422)
    if note.acknowledged_at is not None:
        return 0
    if note.alert_id:
        notes = _open_for(db, user.id, note.alert_id)
    elif note.report_id:
        notes = _open_for_report(db, user.id, note.report_id)
    else:
        notes = [note]
    return _ack(db, notes, user, at, "inbox", note.alert_id)


def _open_for_report(db: Session, user_id: int, report_id: int) -> list[Notification]:
    return list(db.scalars(select(Notification).where(
        Notification.user_id == user_id, Notification.report_id == report_id, Notification.needs_ack.is_(True),
        Notification.acknowledged_at.is_(None)).order_by(Notification.id)))


def acknowledge_for_report(db: Session, user: User, report: CitizenReport, via: str, at: dt.datetime | None = None) -> int:
    """Recording a check on a citizen's report, or closing it, acknowledges what this person was sent about it."""
    return _ack(db, _open_for_report(db, user.id, report.id), user, as_utc(at), via, None)


def acknowledge_for_alert(db: Session, user: User, alert: Alert, via: str, at: dt.datetime | None = None) -> int:
    """Acting on the incident (a review, or the admin's step) acknowledges what this person was sent about it."""
    return _ack(db, _open_for(db, user.id, alert.id), user, as_utc(at), via, alert.id)


# Follow-up --------------------------------------------------------------------------------------
_UNACKED = text(
    """
    SELECT n.id FROM notifications n JOIN users u ON u.id = n.user_id
    LEFT JOIN alerts al ON al.id = n.alert_id LEFT JOIN citizen_reports cr ON cr.id = n.report_id
    WHERE n.kind::text IN ('incident_opened', 'citizen_report') AND n.needs_ack AND n.acknowledged_at IS NULL
      AND n.created_at <= :before AND u.is_active
      AND ((n.kind::text = 'incident_opened' AND al.state IN ('OPEN', 'UNDER_REVIEW'))
           OR (n.kind::text = 'citizen_report' AND cr.status <> 'CLOSED'))
    ORDER BY n.id
    """
)


def follow_up(db: Session, now: dt.datetime | None = None) -> dict:
    now = as_utc(now)
    reminders = escalations = 0
    for nid in db.scalars(_UNACKED, {"before": now - REMIND_AFTER}).all():
        note = db.get(Notification, nid)
        if _already(db, note.user_id, "reminder", about_id=note.id):
            continue
        user = db.get(User, note.user_id)
        payload = {**note.payload, "notified_at": note.created_at.isoformat()}
        create(db, user, "reminder", payload, at=now, needs_ack=True, is_demo=note.is_demo, alert_id=note.alert_id, about_id=note.id,
               report_id=note.report_id)
        reminders += 1
    for nid in db.scalars(_UNACKED, {"before": now - ESCALATE_AFTER}).all():
        note = db.get(Notification, nid)
        official = db.get(User, note.user_id)
        if official.role != Role.viewer.value:
            continue
        payload = {**note.payload, "notified_at": note.created_at.isoformat(), "official_name": official.name, "official_id": official.id}
        for admin in routing.admins(db):
            if _already(db, admin.id, "not_acknowledged", about_id=note.id):
                continue
            create(db, admin, "not_acknowledged", payload, at=now, needs_ack=False, is_demo=note.is_demo, alert_id=note.alert_id, about_id=note.id,
                   report_id=note.report_id)
            escalations += 1
    if reminders or escalations:
        chain.record(db, actor_id=None, action="notify.follow_up", entity="notification",
                     details={"reminders": reminders, "not_acknowledged": escalations}, at=now)
    return {"reminders": reminders, "not_acknowledged": escalations}


# Weekly digest ----------------------------------------------------------------------------------
def send_digests(db: Session, week: str, at: dt.datetime | None = None) -> dict:
    """One digest per person per week. Officials with no area get none."""
    at = as_utc(at)
    sent, skipped = [], 0
    users = db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.id)).all()
    for user in users:
        if db.scalar(select(Notification.id).where(Notification.user_id == user.id, Notification.kind == "weekly_digest",
                                                   Notification.week == week).limit(1)):
            skipped += 1
            continue
        payload = digest.build(db, user, week, at)
        if payload is None:
            skipped += 1
            continue
        sent.append(create(db, user, "weekly_digest", payload, at=at, needs_ack=False, is_demo=False, week=week).user_id)
    if sent:
        chain.record(db, actor_id=None, action="notify.weekly_digest", entity="notification",
                     details={"week": week, "recipients": sent}, at=at)
    return {"week": week, "sent": len(sent), "skipped": skipped}


def latest_week(db: Session) -> str | None:
    """The ISO week of the latest weekly screen."""
    return db.scalar(text(
        "SELECT coalesce(s.week, to_char(r.as_of, 'IYYY-\"W\"IW')) FROM asset_screens s JOIN screen_runs r ON r.id = s.run_id "
        "ORDER BY r.as_of DESC, s.id DESC LIMIT 1"))


# Outbox -----------------------------------------------------------------------------------------
_PENDING = text(
    """
    SELECT d.id FROM (
        SELECT DISTINCT ON (notification_id, channel) id, status, attempt, at
        FROM notification_deliveries ORDER BY notification_id, channel, id DESC
    ) d
    WHERE d.status = 'queued' OR (d.status = 'failed' AND d.attempt < :max AND d.at <= :retry_before)
    ORDER BY d.id
    LIMIT :n
    """
)


def send_pending(db: Session, now: dt.datetime | None = None, limit: int = 200) -> dict:
    now = as_utc(now)
    counts: dict[str, int] = {}
    for did in db.scalars(_PENDING, {"max": MAX_ATTEMPTS, "retry_before": now - RETRY_AFTER, "n": limit}).all():
        last = db.get(NotificationDelivery, did)
        note = db.get(Notification, last.notification_id)
        user = db.get(User, note.user_id)
        result = channels.send(last.channel, note, user)
        db.add(NotificationDelivery(notification_id=note.id, channel=last.channel, status=result.status, attempt=last.attempt + 1,
                                    to_masked=result.to_masked, detail=result.detail, at=now))
        counts[result.status] = counts.get(result.status, 0) + 1
    db.flush()
    return counts


def tick(db: Session, now: dt.datetime | None = None) -> dict:
    from app.citizen import sender as citizen_sender
    from app.citizen import service as citizen
    from app.citizen import whatsapp

    now = as_utc(now)
    out = follow_up(db, now)
    out["deliveries"] = send_pending(db, now)
    out["citizen_messages"] = citizen_sender.send_pending(db, now)
    out["chats_closed"] = whatsapp.close_idle(db, now)
    out["contacts_removed"] = citizen.purge_contacts(db, now)
    return out


# Reading ----------------------------------------------------------------------------------------
_LATEST = text(
    """
    SELECT DISTINCT ON (notification_id, channel) notification_id, channel, status, attempt, to_masked, detail, at
    FROM notification_deliveries WHERE notification_id = ANY(:ids) ORDER BY notification_id, channel, id DESC
    """
)


def deliveries_for(db: Session, ids: list[int]) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    for r in db.execute(_LATEST, {"ids": ids or [0]}).mappings():
        out.setdefault(r["notification_id"], []).append({k: (v.isoformat() if isinstance(v, dt.datetime) else v) for k, v in r.items() if k != "notification_id"})
    return out


def as_dict(note: Notification, deliveries: list[dict] | None = None) -> dict:
    return {
        "id": note.id, "kind": note.kind, "alert_id": note.alert_id, "report_id": note.report_id, "week": note.week, "about_id": note.about_id,
        "subject": note.subject, "body": note.body, "payload": note.payload, "needs_ack": note.needs_ack,
        "created_at": note.created_at.isoformat(), "acknowledged_at": note.acknowledged_at.isoformat() if note.acknowledged_at else None,
        "ack_via": note.ack_via, "is_demo": note.is_demo, "deliveries": deliveries or [],
    }


def pending_filter():
    """Waiting for acknowledgement: not acknowledged, and its incident still open or under review, or its
    citizen report not closed. Once decided or closed the request lapses; it still counts as late."""
    return (
        Notification.needs_ack.is_(True),
        Notification.acknowledged_at.is_(None),
        or_(Notification.alert_id.in_(select(Alert.id).where(Alert.state.in_(("OPEN", "UNDER_REVIEW")))),
            Notification.report_id.in_(select(CitizenReport.id).where(CitizenReport.status != "CLOSED"))),
    )


def unacknowledged_count(db: Session, user: User) -> int:
    q = select(func.count()).select_from(Notification).where(Notification.user_id == user.id, *pending_filter())
    return int(db.scalar(q) or 0)
