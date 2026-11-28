"""Incident lifecycle (DECISIONS.md D-057, D-067).

    OPEN ──(start the review)──► UNDER_REVIEW ──(assign a field officer)──► FIELD_VISIT
    FIELD_VISIT ──(the field officer reports)──► FIELD_REPORTED
    FIELD_REPORTED ──(return it)──► FIELD_VISIT
    UNDER_REVIEW / FIELD_REPORTED ──(the district officer recommends)──► RECOMMENDED
    RECOMMENDED ──(the senior official approves)──► CONFIRMED or DISMISSED, as recommended
    RECOMMENDED ──(the senior official returns it)──► UNDER_REVIEW
    CONFIRMED / DISMISSED ──(the senior official closes)──► CLOSED
    OPEN ──(system, from the legal check)──► CLOSED, resolution "auto"

Who: the district officer whose area holds the asset, and the senior official, start reviews and
assign or withdraw field visits; only the assigned field officer reports; only the district
officer returns a report or recommends; only the senior official approves, returns and closes. The
admin takes no step. Where no district officer covers the place, the senior official takes the
district steps and decides in one step (the audit entry says so). A field visit is optional.

`_step` is the only code that changes `alert.state`. It switches on `lp.state_machine` for the one
UPDATE; a database trigger refuses every other state change, a check constraint keeps the
resolution consistent with the state, and another trigger refuses a decision that differs from the
recommendation. Every step, review, assignment, report and recommendation writes an audit event.

Notifications (D-059, D-067): acting on an incident acknowledges what that person was sent about
it. Assignments, reports, recommendations, returns and decisions tell the people who act next.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import access
from app.audit import chain
from app.clock import as_utc
from app.enums import AlertState, IncidentState as S, Resolution, ReviewOutcome, Role
from app.models import Alert, FieldReport, IncidentAssignment, IncidentRecommendation, IncidentReview, User
from app.rules import legal_check

SYSTEM = "system"
DO, SO, FO = Role.district_officer.value, Role.senior_official.value, Role.field_officer.value
# Not decided yet: "waiting" counts these, and notifications about them still need acknowledging.
UNDECIDED = frozenset({S.OPEN.value, S.UNDER_REVIEW.value, S.FIELD_VISIT.value, S.FIELD_REPORTED.value, S.RECOMMENDED.value})
OPEN_STATES = UNDECIDED | {S.CONFIRMED.value}
# An official's review (an opinion with a note) is recorded while these hold.
REVIEWABLE = frozenset({S.OPEN.value, S.UNDER_REVIEW.value})
ASSIGNABLE = frozenset({S.OPEN.value, S.UNDER_REVIEW.value, S.FIELD_VISIT.value, S.FIELD_REPORTED.value})
RECOMMENDABLE = frozenset({S.OPEN.value, S.UNDER_REVIEW.value, S.FIELD_REPORTED.value})

# The legal check's verdicts that close a change at once, and why.
AUTO_CLOSE = {
    AlertState.CLOSED_OUT_OF_SCOPE.value: "Outside the boundary, buffer and watch ring",
    AlertState.CLOSED_LEGACY.value: "First changed on or before the baseline date: recorded, not an incident",
    AlertState.CLOSED_AUTHORISED.value: "Matches authorised works or a permit",
}

LABEL = {
    "start": "Start the review",
    "assign": "Assign a field officer",
    "reassign": "Assign another field officer",
    "withdraw": "Withdraw the field visit",
    "report": "Submit the field report",
    "return_report": "Return the field report to the field officer",
    "recommend": "Recommend a decision",
    "approve_confirm": "Approve: confirm as a real change",
    "approve_dismiss": "Approve: dismiss as not a real change",
    "return_recommendation": "Return to the district officer",
    "decide_confirm": "Confirm: a real change",
    "decide_dismiss": "Dismiss: not a real change",
    "close": "Close",
}


class Refused(Exception):
    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.message = message
        self.status = status


# Who is acting ----------------------------------------------------------------------------------
class Actor:
    """What this person may do on this incident, worked out once."""

    def __init__(self, db: Session, alert: Alert, user: User):
        self.user = user
        self.asset = access.asset_of(db, alert)
        self.senior = user.role == SO
        self.district = user.role == DO and access.covers(db, user, self.asset)
        self.uncovered = access.uncovered(db, self.asset)
        latest = current_assignment(db, alert.id)
        self.assigned = user.role == FO and latest is not None and latest.field_officer_id == user.id
        # The district officer's steps: theirs, or the senior official's where no district officer covers the place.
        self.district_steps = self.district or (self.senior and self.uncovered)
        self.officer = self.district or self.senior


def _need(ok: bool, message: str) -> None:
    if not ok:
        raise Refused(message, 403)


def _note(note: str | None, what: str = "A note") -> str:
    note = (note or "").strip()
    if not note:
        raise Refused(f"{what} is required", 422)
    if len(note) > 4000:
        raise Refused("Keep the note under 4,000 characters", 422)
    return note


def current_assignment(db: Session, alert_id: int) -> IncidentAssignment | None:
    return db.scalar(select(IncidentAssignment).where(IncidentAssignment.alert_id == alert_id).order_by(IncidentAssignment.id.desc()).limit(1))


def latest_recommendation(db: Session, alert_id: int) -> IncidentRecommendation | None:
    return db.scalar(select(IncidentRecommendation).where(IncidentRecommendation.alert_id == alert_id)
                     .order_by(IncidentRecommendation.id.desc()).limit(1))


def latest_field_report(db: Session, alert_id: int) -> FieldReport | None:
    return db.scalar(select(FieldReport).where(FieldReport.alert_id == alert_id).order_by(FieldReport.id.desc()).limit(1))


# The one place the state changes -----------------------------------------------------------------
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


def _step(db: Session, alert: Alert, to: str, *, actor: User | None, note: str, label: str, at: dt.datetime,
          resolution: str | None = None, details: dict | None = None, department: str | None = None, false_report: bool = False,
          ack_via: str = "decision") -> dict:
    frm = alert.state
    _set_state(db, alert, to, at, resolution)
    chain.record(
        db,
        actor_id=actor.id if actor else None,
        action="alert.transition",
        entity="alert",
        entity_id=alert.id,
        details={"from": frm, "to": to, "role": actor.role if actor else SYSTEM, "step": label, "note": note,
                 "resolution": alert.resolution, **(details or {})},
        at=at,
    )
    from app.citizen import service as citizen
    from app.notify import service as notify

    if actor is not None:
        notify.acknowledge_for_alert(db, actor, alert, ack_via, at)
    if to in (S.CONFIRMED.value, S.DISMISSED.value) and actor is not None:
        notify.incident_decided(db, alert, actor, note, at)
        citizen.on_incident_decided(db, alert, to, at, department, false_report)  # their reports close with the decision (D-062, D-063)
    if to == S.UNDER_REVIEW.value and frm == S.OPEN.value:
        citizen.on_review_started(db, alert, at)  # citizens are told an official is reviewing it (D-063)
    return {"status": "applied", "from": frm, "state": alert.state, "resolution": alert.resolution}


def _start_if_open(db: Session, alert: Alert, user: User, at: dt.datetime, why: str) -> None:
    if alert.state == S.OPEN.value:
        _step(db, alert, S.UNDER_REVIEW.value, actor=user, note=f"{why} by {user.name}", label=LABEL["start"], at=at,
              details={"implicit": True})


def _validate_citizen_outcome(alert: Alert, to_dismiss: bool, department: str | None, false_report: bool) -> None:
    if department is not None:
        from app.citizen import texts as ctexts

        if not to_dismiss or department not in ctexts.DEPARTMENTS:
            raise Refused(f"A department goes with a dismissal, one of: {', '.join(ctexts.DEPARTMENTS)}", 422)
    if false_report and not to_dismiss:
        raise Refused("Only a dismissal can mark the citizen's report as false", 422)


# Steps ------------------------------------------------------------------------------------------
def transition(db: Session, alert: Alert, to: str, *, actor: User | None, note: str | None, at: dt.datetime | None = None,
               resolution: str | None = None, details: dict | None = None, department: str | None = None, false_report: bool = False) -> dict:
    """The plain steps: start, withdraw a visit, return a report, approve, return a recommendation,
    decide where no district officer covers the place, and close. Assignments, field reports and
    recommendations carry their own data and have their own functions below."""
    at = as_utc(at)
    try:
        to = S(to).value
    except ValueError as exc:
        raise Refused(f"Unknown state {to}", 422) from exc
    frm = alert.state
    if actor is None:
        if (frm, to) != (S.OPEN.value, S.CLOSED.value):
            raise Refused(f"There is no system step from {frm} to {to}")
        return _step(db, alert, to, actor=None, note=note or "", label="Closed by the legal check", at=at, resolution=resolution,
                     details=details)
    who = Actor(db, alert, actor)
    note = _note(note)
    extra = dict(details or {})
    if (frm, to) == (S.OPEN.value, S.UNDER_REVIEW.value):
        _need(who.officer, "The district officer of the area or a senior official starts the review")
        label = LABEL["start"]
    elif (frm, to) == (S.FIELD_VISIT.value, S.UNDER_REVIEW.value):
        _need(who.officer, "The district officer of the area or a senior official withdraws a field visit")
        label = LABEL["withdraw"]
    elif (frm, to) == (S.FIELD_REPORTED.value, S.FIELD_VISIT.value):
        _need(who.district_steps, "The district officer of the area returns a field report")
        label = LABEL["return_report"]
    elif frm == S.RECOMMENDED.value and to in (S.CONFIRMED.value, S.DISMISSED.value):
        _need(who.senior, "Only a senior official gives the final approval")
        rec = latest_recommendation(db, alert.id)
        wanted = S.CONFIRMED.value if rec and rec.recommendation == "confirm" else S.DISMISSED.value
        if to != wanted:
            raise Refused(f"The recommendation was to {rec.recommendation if rec else 'decide'}: approve it, or return it to the district officer")
        label = LABEL["approve_confirm" if to == S.CONFIRMED.value else "approve_dismiss"]
        department, false_report = rec.citizen_department, rec.citizen_false_report
        extra["recommendation_id"] = rec.id
    elif (frm, to) == (S.RECOMMENDED.value, S.UNDER_REVIEW.value):
        _need(who.senior, "Only a senior official returns a recommendation")
        label = LABEL["return_recommendation"]
    elif frm in (S.OPEN.value, S.UNDER_REVIEW.value, S.FIELD_REPORTED.value) and to in (S.CONFIRMED.value, S.DISMISSED.value):
        _need(who.senior and who.uncovered,
              "A decision needs the district officer's recommendation first" if who.senior else "Only a senior official decides")
        _validate_citizen_outcome(alert, to == S.DISMISSED.value, department, false_report)
        _start_if_open(db, alert, actor, at, "Review started")
        label = LABEL["decide_confirm" if to == S.CONFIRMED.value else "decide_dismiss"]
        extra["no_district_officer"] = True
    elif frm in (S.CONFIRMED.value, S.DISMISSED.value) and to == S.CLOSED.value:
        _need(who.senior, "Only a senior official closes an incident")
        label = LABEL["close"]
    else:
        raise Refused(f"There is no step from {frm} to {to}")
    out = _step(db, alert, to, actor=actor, note=note, label=label, at=at, details=extra, department=department, false_report=false_report)
    from app.notify import service as notify

    if label == LABEL["return_report"]:
        cur = current_assignment(db, alert.id)
        notify.returned(db, alert, [db.get(User, cur.field_officer_id)] if cur else [], actor, "field_report", note, at)
    elif label == LABEL["return_recommendation"]:
        rec = latest_recommendation(db, alert.id)
        notify.returned(db, alert, [db.get(User, rec.recommended_by)] if rec else [], actor, "recommendation", note, at)
    return out


def assign(db: Session, alert: Alert, user: User, field_officer_id: int, note: str, at: dt.datetime | None = None) -> IncidentAssignment:
    """Send a field officer to the place. From an open, reviewed or reported incident, or to replace the one on a visit."""
    at = as_utc(at)
    who = Actor(db, alert, user)
    _need(who.officer, "The district officer of the area or a senior official assigns a field visit")
    if alert.state not in ASSIGNABLE:
        raise Refused(f"This incident is {alert.state}; a field visit is assigned before a recommendation")
    note = _note(note)
    officer = db.get(User, field_officer_id)
    if officer is None or not officer.is_active or officer.role != FO:
        raise Refused("Choose an active field officer", 422)
    if not _field_officer_covers(db, officer, who.asset):
        raise Refused(f"{officer.name} does not cover {who.asset.district or 'this place'}", 422)
    cur = current_assignment(db, alert.id)
    if alert.state == S.FIELD_VISIT.value and cur is not None and cur.field_officer_id == officer.id:
        raise Refused(f"{officer.name} is already on this field visit")
    _start_if_open(db, alert, user, at, "Review started")
    row = IncidentAssignment(alert_id=alert.id, field_officer_id=officer.id, assigned_by=user.id, note=note, at=at, is_demo=alert.is_demo)
    db.add(row)
    db.flush()
    chain.record(db, actor_id=user.id, action="incident.assigned", entity="alert", entity_id=alert.id, at=at,
                 details={"assignment_id": row.id, "field_officer_id": officer.id, "field_officer": officer.name, "note": note,
                          "replaces": cur.field_officer_id if cur and alert.state == S.FIELD_VISIT.value else None})
    if alert.state != S.FIELD_VISIT.value:
        _step(db, alert, S.FIELD_VISIT.value, actor=user, note=note, label=LABEL["assign"], at=at,
              details={"assignment_id": row.id, "field_officer": officer.name})
    else:
        from app.notify import service as notify

        notify.acknowledge_for_alert(db, user, alert, "decision", at)
    from app.notify import service as notify

    notify.assigned(db, alert, officer, user, note, at)
    return row


def _field_officer_covers(db: Session, officer: User, asset) -> bool:
    from app.notify.routing import COVERS

    if not (asset.district or "").strip():
        return False
    return bool(db.scalar(text(f"SELECT {COVERS.format(user=int(officer.id), asset='a')} FROM assets a WHERE a.id = :a"), {"a": asset.id}))


def field_officers_for(db: Session, alert: Alert) -> list[dict]:
    """The field officers who may be sent to this incident's place, with what they have open."""
    from app.notify import routing

    asset = access.asset_of(db, alert)
    out = []
    for u in routing.officials_for(db, asset, Role.field_officer.value):
        busy = db.scalar(text(
            "SELECT count(*) FROM alerts al WHERE al.state = 'FIELD_VISIT' AND (SELECT ia.field_officer_id FROM incident_assignments ia "
            "WHERE ia.alert_id = al.id ORDER BY ia.id DESC LIMIT 1) = :u"), {"u": u.id})
        out.append({"id": u.id, "name": u.name, "areas": [routing.area_label(a) for a in routing.areas_of(db, u.id)], "open_visits": int(busy or 0)})
    return out


def submit_field_report(db: Session, alert: Alert, user: User, *, outcome: str, findings: str, observed_at: dt.datetime,
                        lat: float | None, lon: float | None, photos: list[bytes], at: dt.datetime | None = None) -> FieldReport:
    """The assigned field officer's report: the visit (GPS, photos) and what they found."""
    from app.services import inspections

    at = as_utc(at)
    who = Actor(db, alert, user)
    _need(who.assigned, "Only the field officer assigned to this incident submits its field report")
    if alert.state != S.FIELD_VISIT.value:
        raise Refused(f"This incident is {alert.state}; there is no field visit open")
    findings = _note(findings, "Your findings")
    if observed_at > at + dt.timedelta(minutes=5):
        raise Refused("The visit cannot be in the future", 422)
    try:
        visit = inspections.record(db, who.asset, user, outcome=outcome, notes=findings, observed_at=observed_at, lat=lat, lon=lon,
                                   photos=photos, alert_id=alert.id)
    except inspections.InspectionRefused as exc:
        raise Refused(str(exc), 422) from exc
    cur = current_assignment(db, alert.id)
    row = FieldReport(alert_id=alert.id, assignment_id=cur.id, field_officer_id=user.id, inspection_id=visit.id, outcome=outcome,
                      findings=findings, submitted_at=at, is_demo=alert.is_demo)
    db.add(row)
    db.flush()
    chain.record(db, actor_id=user.id, action="incident.field_reported", entity="alert", entity_id=alert.id, at=at,
                 details={"field_report_id": row.id, "inspection_id": visit.id, "outcome": outcome, "photos": len(visit.photo_paths),
                          "gps": lat is not None})
    _step(db, alert, S.FIELD_REPORTED.value, actor=user, note=findings, label=LABEL["report"], at=at, details={"field_report_id": row.id})
    from app.notify import service as notify

    notify.field_reported(db, alert, user, outcome, findings, at)
    return row


def recommend(db: Session, alert: Alert, user: User, recommendation: str, note: str, at: dt.datetime | None = None, *,
              department: str | None = None, false_report: bool = False) -> IncidentRecommendation:
    """The district officer's recommendation, for the senior official's final approval."""
    at = as_utc(at)
    who = Actor(db, alert, user)
    _need(who.district, "The district officer of the area recommends a decision" if not who.senior or not who.uncovered
          else "No district officer covers this place: decide it directly")
    if recommendation not in ("confirm", "dismiss"):
        raise Refused("The recommendation is confirm or dismiss", 422)
    if alert.state not in RECOMMENDABLE:
        raise Refused(f"This incident is {alert.state}; it cannot be recommended now")
    note = _note(note)
    _validate_citizen_outcome(alert, recommendation == "dismiss", department, false_report)
    _start_if_open(db, alert, user, at, "Review started")
    report = latest_field_report(db, alert.id) if alert.state == S.FIELD_REPORTED.value else None
    row = IncidentRecommendation(alert_id=alert.id, recommended_by=user.id, recommendation=recommendation, note=note,
                                 field_report_id=report.id if report else None, citizen_department=department,
                                 citizen_false_report=bool(false_report), at=at, is_demo=alert.is_demo)
    db.add(row)
    db.flush()
    chain.record(db, actor_id=user.id, action="incident.recommended", entity="alert", entity_id=alert.id, at=at,
                 details={"recommendation_id": row.id, "recommendation": recommendation, "note": note,
                          "field_report_id": row.field_report_id, "department": department, "false_report": bool(false_report)})
    _step(db, alert, S.RECOMMENDED.value, actor=user, note=note, label=LABEL["recommend"], at=at,
          details={"recommendation_id": row.id, "recommendation": recommendation})
    from app.notify import service as notify

    notify.recommended(db, alert, user, recommendation, note, at)
    return row


def auto_close(db: Session, alert: Alert, verdict: str, at: dt.datetime | None = None) -> dict:
    return transition(db, alert, S.CLOSED.value, actor=None, note=AUTO_CLOSE[verdict], at=at,
                      resolution=Resolution.auto.value, details={"legal_check": verdict})


def review(db: Session, alert: Alert, user: User, outcome: str, note: str, at: dt.datetime | None = None) -> IncidentReview:
    """An official's review: real change, not real, or needs a site visit, with a note. The first one
    starts the review."""
    at = as_utc(at)
    who = Actor(db, alert, user)
    _need(who.officer, "Reviews are recorded by the district officer of the area or a senior official")
    if alert.state not in REVIEWABLE:
        raise Refused(f"This incident is {alert.state}; reviews are taken while it is open or under review")
    try:
        outcome = ReviewOutcome(outcome).value
    except ValueError as exc:
        raise Refused(f"Unknown review outcome {outcome}", 422) from exc
    note = _note(note)
    row = IncidentReview(alert_id=alert.id, reviewer_id=user.id, outcome=outcome, note=note, reviewed_at=at)
    db.add(row)
    db.flush()
    chain.record(db, actor_id=user.id, action="incident.reviewed", entity="alert", entity_id=alert.id,
                 details={"review_id": row.id, "outcome": outcome, "note": row.note}, at=at)
    if alert.state == S.OPEN.value:
        _step(db, alert, S.UNDER_REVIEW.value, actor=user, note="First review recorded", label=LABEL["start"], at=at,
              details={"by_review": True, "review_id": row.id}, ack_via="review")
    from app.notify import service as notify

    notify.acknowledge_for_alert(db, user, alert, "review", at)
    return row


def allowed_actions(db: Session, alert: Alert, user: User) -> list[dict]:
    """What this person can do next. The server still checks every step."""
    if user.role == Role.admin.value:
        return []
    who = Actor(db, alert, user)
    st = alert.state
    out: list[dict] = []
    if who.officer and st in REVIEWABLE:
        reviewed = db.scalar(select(IncidentReview.id).where(IncidentReview.alert_id == alert.id, IncidentReview.reviewer_id == user.id).limit(1))
        out.append({"action": "review", "label": "Record your review", "already_reviewed": reviewed is not None})
    if who.officer and st == S.OPEN.value:
        out.append({"action": "transition", "to": S.UNDER_REVIEW.value, "label": LABEL["start"]})
    if who.officer and st in ASSIGNABLE:
        out.append({"action": "assign", "label": LABEL["reassign" if st == S.FIELD_VISIT.value else "assign"]})
    if who.officer and st == S.FIELD_VISIT.value:
        out.append({"action": "transition", "to": S.UNDER_REVIEW.value, "label": LABEL["withdraw"]})
    if who.assigned and st == S.FIELD_VISIT.value:
        out.append({"action": "field_report", "label": LABEL["report"]})
    if who.district_steps and st == S.FIELD_REPORTED.value:
        out.append({"action": "transition", "to": S.FIELD_VISIT.value, "label": LABEL["return_report"]})
    if who.district and st in RECOMMENDABLE:
        out.append({"action": "recommend", "label": LABEL["recommend"]})
    if who.senior and who.uncovered and st in RECOMMENDABLE:
        out.append({"action": "transition", "to": S.CONFIRMED.value, "label": LABEL["decide_confirm"], "direct": True})
        out.append({"action": "transition", "to": S.DISMISSED.value, "label": LABEL["decide_dismiss"], "direct": True})
    if who.senior and st == S.RECOMMENDED.value:
        rec = latest_recommendation(db, alert.id)
        to = S.CONFIRMED.value if rec and rec.recommendation == "confirm" else S.DISMISSED.value
        out.append({"action": "transition", "to": to, "label": LABEL["approve_confirm" if to == S.CONFIRMED.value else "approve_dismiss"],
                    "approve": True})
        out.append({"action": "transition", "to": S.UNDER_REVIEW.value, "label": LABEL["return_recommendation"]})
    if who.senior and st in (S.CONFIRMED.value, S.DISMISSED.value):
        out.append({"action": "transition", "to": S.CLOSED.value, "label": LABEL["close"]})
    if alert.resolution == Resolution.confirmed.value and who.officer:
        out.append({"action": "evidence_pack", "label": "Generate the evidence pack"})
    return out


def court_hits(db: Session) -> list[int]:
    """Open incidents whose change now meets a live court matter (after a court register import)."""
    hits = []
    for alert in db.scalars(select(Alert).where(Alert.state.in_(sorted(OPEN_STATES)))).all():
        if legal_check.live_court_case(db, alert.candidate_id) is not None:
            hits.append(alert.id)
    return hits
