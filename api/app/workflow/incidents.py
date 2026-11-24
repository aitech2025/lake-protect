"""Incident lifecycle (DECISIONS.md D-057). Replaces the 24-rule state machine of section 6.5.

    OPEN ──(a viewer records a review, or the admin starts one)──► UNDER_REVIEW
    UNDER_REVIEW ──(admin, with a note)──► CONFIRMED  or  DISMISSED
    CONFIRMED / DISMISSED ──(admin, with a note)──► CLOSED
    OPEN ──(system, from the legal check)──► CLOSED, resolution "auto"

`transition` is the only code that changes `alert.state`. It switches on `lp.state_machine` for
the one UPDATE; a database trigger refuses every other state change, and a check constraint keeps
the resolution consistent with the state. Every step and every review writes an audit event.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.clock import as_utc
from app.enums import AlertState, IncidentState as S, Resolution, ReviewOutcome, Role
from app.models import Alert, IncidentReview, User
from app.rules import legal_check

SYSTEM = "system"
OPEN_STATES = frozenset({S.OPEN.value, S.UNDER_REVIEW.value, S.CONFIRMED.value})
REVIEWABLE = frozenset({S.OPEN.value, S.UNDER_REVIEW.value})

# (from, to) -> who may take the step, and its label.
STEPS: dict[tuple[str, str], tuple[str, str]] = {
    (S.OPEN.value, S.UNDER_REVIEW.value): (Role.admin.value, "Start review"),
    (S.UNDER_REVIEW.value, S.CONFIRMED.value): (Role.admin.value, "Confirm: a real change"),
    (S.UNDER_REVIEW.value, S.DISMISSED.value): (Role.admin.value, "Dismiss: not a real change"),
    (S.CONFIRMED.value, S.CLOSED.value): (Role.admin.value, "Close"),
    (S.DISMISSED.value, S.CLOSED.value): (Role.admin.value, "Close"),
    (S.OPEN.value, S.CLOSED.value): (SYSTEM, "Closed by the legal check"),
}

# The legal check's verdicts that close a change at once, and why.
AUTO_CLOSE = {
    AlertState.CLOSED_OUT_OF_SCOPE.value: "Outside the lake boundary, buffer and watch ring",
    AlertState.CLOSED_LEGACY.value: "First changed on or before the baseline date: recorded, not an incident",
    AlertState.CLOSED_AUTHORISED.value: "Matches authorised works or a permit",
}


class Refused(Exception):
    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.message = message
        self.status = status


def _set_state(db: Session, alert: Alert, to: str, at: dt.datetime, resolution: str | None) -> None:
    db.execute(text("SELECT set_config('lp.state_machine', 'on', true)"))
    alert.state = to
    alert.updated_at = at
    if to == S.CONFIRMED.value:
        alert.resolution = Resolution.confirmed.value
    elif to == S.DISMISSED.value:
        alert.resolution = Resolution.dismissed.value
    elif to == S.CLOSED.value:
        alert.resolution = resolution or alert.resolution
        alert.closed_at = at
    db.flush()
    db.execute(text("SELECT set_config('lp.state_machine', 'off', true)"))


def transition(
    db: Session,
    alert: Alert,
    to: str,
    *,
    actor: User | None,
    note: str | None,
    at: dt.datetime | None = None,
    resolution: str | None = None,
    details: dict | None = None,
) -> dict:
    """One step of the lifecycle. Admin steps need a note; system steps come from the legal check."""
    at = as_utc(at)
    try:
        to = S(to).value
    except ValueError as exc:
        raise Refused(f"Unknown state {to}", 422) from exc
    step = STEPS.get((alert.state, to))
    if step is None:
        raise Refused(f"There is no step from {alert.state} to {to}")
    who, label = step
    role = actor.role if actor else SYSTEM
    # A viewer's first review moves an incident to UNDER_REVIEW through review(), never directly.
    if role != who and not (to == S.UNDER_REVIEW.value and details and details.get("by_review")):
        raise Refused(f"Only the {who} can take this step ({label})", 403)
    if actor is not None and not (note and note.strip()):
        raise Refused("A note is required", 422)
    frm = alert.state
    _set_state(db, alert, to, at, resolution)
    chain.record(
        db,
        actor_id=actor.id if actor else None,
        action="alert.transition",
        entity="alert",
        entity_id=alert.id,
        details={"from": frm, "to": to, "role": role, "step": label, "note": note, "resolution": alert.resolution, **(details or {})},
        at=at,
    )
    return {"status": "applied", "from": frm, "state": alert.state, "resolution": alert.resolution}


def auto_close(db: Session, alert: Alert, verdict: str, at: dt.datetime | None = None) -> dict:
    return transition(db, alert, S.CLOSED.value, actor=None, note=AUTO_CLOSE[verdict], at=at,
                      resolution=Resolution.auto.value, details={"legal_check": verdict})


def review(db: Session, alert: Alert, user: User, outcome: str, note: str, at: dt.datetime | None = None) -> IncidentReview:
    """A viewer's review. The first one moves the incident from OPEN to UNDER_REVIEW."""
    at = as_utc(at)
    if user.role != Role.viewer.value:
        raise Refused("Reviews are recorded by viewers (the officials); the admin decides", 403)
    if alert.state not in REVIEWABLE:
        raise Refused(f"This incident is {alert.state}; reviews are taken while it is open or under review")
    try:
        outcome = ReviewOutcome(outcome).value
    except ValueError as exc:
        raise Refused(f"Unknown review outcome {outcome}", 422) from exc
    if not (note and note.strip()):
        raise Refused("A note is required", 422)
    row = IncidentReview(alert_id=alert.id, reviewer_id=user.id, outcome=outcome, note=note.strip(), reviewed_at=at)
    db.add(row)
    db.flush()
    chain.record(db, actor_id=user.id, action="incident.reviewed", entity="alert", entity_id=alert.id,
                 details={"review_id": row.id, "outcome": outcome, "note": row.note}, at=at)
    if alert.state == S.OPEN.value:
        transition(db, alert, S.UNDER_REVIEW.value, actor=user, note="First review recorded", at=at,
                   details={"by_review": True, "review_id": row.id})
    return row


def allowed_actions(db: Session, alert: Alert, user: User) -> list[dict]:
    """What this user can do next. The server still checks every step."""
    out = []
    if user.role == Role.viewer.value:
        reviewed = db.scalar(select(IncidentReview.id).where(IncidentReview.alert_id == alert.id, IncidentReview.reviewer_id == user.id).limit(1))
        if alert.state in REVIEWABLE:
            out.append({"action": "review", "label": "Record your review", "already_reviewed": reviewed is not None})
        return out
    if user.role == Role.admin.value:
        for (frm, to), (who, label) in STEPS.items():
            if frm == alert.state and who == Role.admin.value:
                out.append({"action": "transition", "to": to, "label": label})
        if alert.resolution == Resolution.confirmed.value:
            out.append({"action": "evidence_pack", "label": "Generate the evidence pack"})
    return out


def court_hits(db: Session) -> list[int]:
    """Open incidents whose change now meets a live court matter (after a court register import)."""
    hits = []
    for alert in db.scalars(select(Alert).where(Alert.state.in_(sorted(OPEN_STATES)))).all():
        if legal_check.live_court_case(db, alert.candidate_id) is not None:
            hits.append(alert.id)
    return hits
