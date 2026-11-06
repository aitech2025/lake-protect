"""Alert lifecycle (CONTEXT.md section 6.5) as one table-driven state machine.

`transition` is the only code that changes `alert.state`. It switches on `lp.state_machine` for
the one UPDATE, and a database trigger refuses every other state change. Each transition, and
each first signature of a two-person closure, writes an audit event.

Rows in TABLE follow section 6.5 in order. Two rows fill gaps in that table and are recorded in
DECISIONS.md: HOLD_LEGAL to WATCH_LIST (D-017) and open states to HOLD_LEGAL (E-004).
"""
from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.clock import as_utc
from app.enums import AlertState as S
from app.enums import Mode, Role
from app.models import (
    Alert,
    Asset,
    Candidate,
    ClosureRequest,
    EvidencePack,
    FieldCheck,
    LegalCheck,
    OfficerRecord,
    ReadinessItem,
    User,
)
from app.rules import config as rules
from app.rules import legal_check
from app.services import boundaries as bsvc
from app.workflow import escalation, timers

SYSTEM = "system"
OFFICERS = frozenset({Role.legal_officer.value, Role.senior_officer.value})  # "Officer" (E-003)

READINESS_KEYS = (
    "boundary_confirmed",
    "joint_survey_done",
    "survey_notice_given",
    "no_live_court_matter",
    "title_permits_reviewed",
    "notice_and_hearing",
    "construction_dated",
)

OPEN_STATES = frozenset(
    s.value
    for s in (S.TRIAGE, S.CONFIRMED, S.ASSIGNED, S.FIELD_CONFIRMED, S.AWAITING_BOUNDARY, S.PACK_READY, S.WITH_OFFICER, S.WATCH_LIST)
)
REOPENABLE = frozenset(s.value for s in (S.CLOSED_NOT_REAL, S.CLOSED_FALSE_ALARM, S.CLOSED_NO_ACTION))
SYSTEM_CLOSURES = frozenset(s.value for s in (S.CLOSED_OUT_OF_SCOPE, S.CLOSED_LEGACY, S.CLOSED_AUTHORISED))
FIELD_CONFIRMED_OR_LATER = frozenset(
    s.value
    for s in (S.FIELD_CONFIRMED, S.AWAITING_BOUNDARY, S.PACK_READY, S.WITH_OFFICER, S.ACTION_RECORDED, S.CLOSED_NO_ACTION, S.POST_ACTION_WATCH)
)
# A re-check counts as persisting when the new footprint is at least this share of the old one.
PERSISTING_SHARE = 0.9


class Refused(Exception):
    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass
class Ctx:
    db: Session
    alert: Alert
    actor: User | None
    at: dt.datetime
    to: str
    reason: str | None = None
    data: dict = field(default_factory=dict)
    signer: str = "single"  # single, first or second

    @property
    def role(self) -> str:
        return self.actor.role if self.actor else SYSTEM

    @cached_property
    def candidate(self) -> Candidate:
        return self.db.get(Candidate, self.alert.candidate_id)

    @cached_property
    def asset(self) -> Asset:
        return self.db.get(Asset, self.candidate.asset_id)

    @property
    def mode(self) -> Mode:
        return rules.mode_for_cohort(self.asset.cohort)

    @cached_property
    def primary(self) -> dict | None:
        return bsvc.primary_of(bsvc.boundary_set_at(self.db, self.asset.id, self.at.date()))

    @cached_property
    def latest_legal(self) -> LegalCheck | None:
        return self.db.scalar(
            select(LegalCheck).where(LegalCheck.candidate_id == self.alert.candidate_id).order_by(LegalCheck.id.desc()).limit(1)
        )


Guard = Callable[[Ctx], None]


# Preconditions: the state of the world -------------------------------------------------------

def legal_result(ctx: Ctx) -> None:
    lc = ctx.latest_legal
    if lc is None or lc.result != ctx.to:
        raise Refused(f"The legal check result is {lc.result if lc else 'missing'}, not {ctx.to}")


def reference_stored(ctx: Ctx) -> None:
    lc = ctx.latest_legal
    if lc is None or (lc.matched_work_id is None and lc.matched_permit_id is None):
        raise Refused("An authorised closure must store the matched work or permit")


def mode_is(*modes: Mode) -> Guard:
    def guard(ctx: Ctx) -> None:
        if ctx.mode not in modes:
            raise Refused(f"This asset's mode is {ctx.mode.value}; this step needs {'/'.join(m.value for m in modes)}")

    guard.__name__ = f"mode_is_{'_'.join(m.value for m in modes)}"
    return guard


def mode_not(mode: Mode) -> Guard:
    def guard(ctx: Ctx) -> None:
        if ctx.mode == mode:
            reason = "watch-only assets never go to the field" if mode == Mode.WATCH else f"mode {mode.value} is not allowed"
            raise Refused(f"Refused: {reason} (cohort {ctx.asset.cohort})")

    guard.__name__ = f"mode_not_{mode.value}"
    return guard


def no_live_court(ctx: Ctx) -> None:
    case_id = legal_check.live_court_case(ctx.db, ctx.alert.candidate_id)
    if case_id is not None:
        raise Refused(f"The court register shows a live matter (court case {case_id}). It goes to the legal team, not the field.")


def live_court(ctx: Ctx) -> None:
    case_id = legal_check.live_court_case(ctx.db, ctx.alert.candidate_id)
    if case_id is None:
        raise Refused("No live court matter matches this alert")
    ctx.data["_court_case_id"] = case_id


def boundary_upgraded(ctx: Ctx) -> None:
    lc, primary = ctx.latest_legal, ctx.primary
    if primary is None or lc is None or primary["version"] <= lc.boundary_version:
        raise Refused("Moving off the watch list needs a new boundary version")
    if ctx.mode == Mode.WATCH:
        raise Refused(f"The new boundary status ({primary['status']}) still allows watching only")


def boundary_confirmed(ctx: Ctx) -> None:
    primary = ctx.primary
    if primary is None or not rules.is_confirmed_status(primary["status"]):
        status = primary["status"] if primary else "none"
        raise Refused(f"The boundary is not confirmed (status {status}). Only confirmed boundaries can lead to action.")


def image_pair_present(ctx: Ctx) -> None:
    if not (ctx.candidate.before_chip and ctx.candidate.after_chip):
        raise Refused("There is no before and after image pair to review")


def actor_is_owner(ctx: Ctx) -> None:
    if ctx.signer == "second":
        return
    if ctx.actor is None or ctx.actor.id != ctx.alert.owner_user_id:
        raise Refused("Only the field officer this alert is assigned to can do this", 403)


def pack_exists(ctx: Ctx) -> None:
    if ctx.db.scalar(select(EvidencePack.id).where(EvidencePack.alert_id == ctx.alert.id).limit(1)) is None:
        raise Refused("Generate the evidence pack first")


def checklist_recorded(ctx: Ctx) -> None:
    done = set(ctx.db.scalars(select(ReadinessItem.item_key).where(ReadinessItem.alert_id == ctx.alert.id)))
    missing = [k for k in READINESS_KEYS if k not in done]
    if missing:
        raise Refused(f"Record every checklist item first. Missing: {', '.join(missing)}")


# Data requirements: what the request must carry ---------------------------------------------

def need_reason(ctx: Ctx) -> None:
    if not (ctx.reason and ctx.reason.strip()):
        raise Refused("A reason is required", 422)


def need_data(key: str) -> Guard:
    def guard(ctx: Ctx) -> None:
        if not ctx.data.get(key):
            raise Refused(f"'{key}' is required", 422)

    guard.__name__ = f"need_{key}"
    return guard


def need_true(key: str) -> Guard:
    def guard(ctx: Ctx) -> None:
        if ctx.data.get(key) is not True:
            raise Refused(f"'{key}' must be true", 422)

    guard.__name__ = f"need_{key}"
    return guard


def need_field_owner(ctx: Ctx) -> None:
    uid = ctx.data.get("owner_user_id")
    if not uid:
        raise Refused("Name the field officer who owns this alert ('owner_user_id')", 422)
    owner = ctx.db.get(User, int(uid))
    if owner is None or not owner.is_active or owner.role != Role.field_officer.value:
        raise Refused("The owner must be an active field officer", 422)
    if owner.area_geom is not None:
        inside = ctx.db.scalar(
            text("SELECT ST_Intersects(c.geom, u.area_geom) FROM candidates c, users u WHERE c.id = :c AND u.id = :u"),
            {"c": ctx.alert.candidate_id, "u": owner.id},
        )
        if not inside:
            raise Refused("This alert is outside that field officer's area", 422)
    due = ctx.data.get("due_at")
    if due:
        due_at = dt.datetime.fromisoformat(str(due).replace("Z", "+00:00"))
        if due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=dt.timezone.utc)
        if due_at <= ctx.at:
            raise Refused("The due date must be in the future", 422)
        ctx.data["_due_at"] = due_at
    ctx.data["_owner_user_id"] = owner.id


def need_field_check(outcome: str, with_evidence: bool = False) -> Guard:
    def guard(ctx: Ctx) -> None:
        fc_id = ctx.data.get("field_check_id")
        fc = ctx.db.get(FieldCheck, int(fc_id)) if fc_id else None
        if fc is None or fc.alert_id != ctx.alert.id or fc.outcome != outcome:
            raise Refused(f"A field check with outcome '{outcome}' for this alert is required", 422)
        if ctx.actor is not None and fc.officer_id != ctx.actor.id:
            raise Refused("The field check must be your own", 403)
        if with_evidence and (not fc.photo_paths or fc.lat is None or fc.lon is None or fc.observed_at is None):
            raise Refused("Field confirmation needs a geotagged photo, a GPS fix and a timestamp", 422)

    guard.__name__ = f"need_field_check_{outcome}"
    return guard


def need_gap_reason(ctx: Ctx) -> None:
    gaps = list(
        ctx.db.scalars(select(ReadinessItem.item_key).where(ReadinessItem.alert_id == ctx.alert.id, ReadinessItem.status == "no"))
    )
    if gaps and not (ctx.data.get("gap_reason") or "").strip():
        raise Refused(f"Checklist gaps ({', '.join(gaps)}) need a logged reason ('gap_reason')", 422)
    ctx.data["_checklist_gaps"] = gaps


def need_officer_record(ctx: Ctx) -> None:
    rec_id = ctx.data.get("officer_record_id")
    rec = ctx.db.get(OfficerRecord, int(rec_id)) if rec_id else None
    if rec is None or rec.alert_id != ctx.alert.id:
        raise Refused("An officer record for this alert is required ('officer_record_id')", 422)
    if not any([rec.notice_ref, rec.order_ref, rec.action_date, rec.hearing_date]):
        raise Refused("The officer record needs at least one notice, hearing, order or action reference", 422)


def need_recheck(ctx: Ctx) -> None:
    new_id = ctx.data.get("recheck_candidate_id")
    new = ctx.db.get(Candidate, int(new_id)) if new_id else None
    old = ctx.candidate
    if new is None or new.asset_id != old.asset_id or new.id == old.id:
        raise Refused("Reopening needs a new re-check candidate on the same asset", 422)
    overlaps = ctx.db.scalar(
        text("SELECT ST_Intersects(a.geom, b.geom) FROM candidates a, candidates b WHERE a.id = :a AND b.id = :b"),
        {"a": old.id, "b": new.id},
    )
    if not overlaps or float(new.area_sq_m) < PERSISTING_SHARE * float(old.area_sq_m):
        raise Refused("The re-check does not show the change persisting or growing", 422)
    ctx.data["_growth"] = round(float(new.area_sq_m) / float(old.area_sq_m) - 1, 4)


# The table ---------------------------------------------------------------------------------

@dataclass(frozen=True)
class Rule:
    src: frozenset[str]
    dst: str
    actors: frozenset[str]
    cosigners: frozenset[str] = frozenset()
    pre: tuple[Guard, ...] = ()
    needs: tuple[Guard, ...] = ()
    label: str = ""


def _r(src, dst, actors, *, cosigners=(), pre=(), needs=(), label=""):
    src = frozenset(S(s).value for s in ([src] if isinstance(src, str) else src))
    actors = frozenset(str(a) for a in ([actors] if isinstance(actors, str) else actors))
    return Rule(src, S(dst).value, actors, frozenset(str(c) for c in cosigners), tuple(pre), tuple(needs), label)


A, RV, FO, NO, LO = (Role.analyst.value, Role.reviewer.value, Role.field_officer.value, Role.nodal_officer.value, Role.legal_officer.value)

TABLE: tuple[Rule, ...] = (
    _r(S.CANDIDATE, S.CLOSED_OUT_OF_SCOPE, SYSTEM, pre=[legal_result], label="Outside the boundary"),
    _r(S.CANDIDATE, S.CLOSED_LEGACY, SYSTEM, pre=[legal_result], label="Changed before the baseline date"),
    _r(S.CANDIDATE, S.CLOSED_AUTHORISED, SYSTEM, pre=[legal_result, reference_stored], label="Matches authorised work or permit"),
    _r(S.CANDIDATE, S.HOLD_LEGAL, SYSTEM, pre=[legal_result], label="Court register hit"),
    _r(S.CANDIDATE, S.WATCH_LIST, SYSTEM, pre=[legal_result, mode_is(Mode.WATCH)], label="Watch only"),
    _r(S.CANDIDATE, S.TRIAGE, SYSTEM, pre=[legal_result], label="Send to analyst review"),
    _r(S.HOLD_LEGAL, S.TRIAGE, LO, pre=[no_live_court, mode_not(Mode.WATCH)], needs=[need_reason, need_data("case_status_ref")], label="Release from legal hold"),
    _r(S.HOLD_LEGAL, S.WATCH_LIST, LO, pre=[no_live_court, mode_is(Mode.WATCH)], needs=[need_reason, need_data("case_status_ref")], label="Release to watch list"),
    _r(S.WATCH_LIST, S.TRIAGE, NO, pre=[boundary_upgraded], label="Move to review after boundary update"),
    _r(S.TRIAGE, S.CLOSED_NOT_REAL, A, cosigners=[RV], needs=[need_reason, need_data("reason_code")], label="Close as not real"),
    _r(S.TRIAGE, S.CONFIRMED, A, pre=[image_pair_present], needs=[need_true("image_pair_reviewed")], label="Confirm change"),
    _r(S.CONFIRMED, S.ASSIGNED, [NO, SYSTEM], pre=[mode_not(Mode.WATCH), no_live_court], needs=[need_field_owner], label="Assign to field officer"),
    _r(S.ASSIGNED, S.ASSIGNED, FO, pre=[actor_is_owner], needs=[need_reason, need_field_check("cannot_access")], label="Could not access"),
    _r(S.ASSIGNED, S.CLOSED_FALSE_ALARM, FO, cosigners=[NO], pre=[actor_is_owner], needs=[need_reason], label="Close as false alarm"),
    _r(S.ASSIGNED, S.FIELD_CONFIRMED, FO, pre=[actor_is_owner], needs=[need_field_check("confirmed", with_evidence=True)], label="Field-confirmed"),
    _r(S.FIELD_CONFIRMED, S.AWAITING_BOUNDARY, SYSTEM, pre=[mode_is(Mode.VERIFY)], label="Wait for final boundary"),
    _r(S.AWAITING_BOUNDARY, S.FIELD_CONFIRMED, NO, pre=[boundary_confirmed, mode_is(Mode.ACTION)], label="Boundary now final"),
    _r(S.FIELD_CONFIRMED, S.PACK_READY, [NO, LO], pre=[mode_is(Mode.ACTION), pack_exists, checklist_recorded], label="Mark case file ready"),
    _r(S.PACK_READY, S.WITH_OFFICER, NO, pre=[boundary_confirmed], needs=[need_gap_reason], label="Send to officer"),
    _r(S.WITH_OFFICER, S.ACTION_RECORDED, OFFICERS, needs=[need_officer_record], label="Record officer action"),
    _r(S.WITH_OFFICER, S.CLOSED_NO_ACTION, OFFICERS, cosigners=[NO], needs=[need_reason], label="Close with no action"),
    _r(S.ACTION_RECORDED, S.POST_ACTION_WATCH, SYSTEM, label="Keep on weekly watch"),
    _r(REOPENABLE, S.TRIAGE, SYSTEM, needs=[need_recheck], label="Reopen: change persists"),
    _r(OPEN_STATES, S.HOLD_LEGAL, SYSTEM, pre=[live_court], label="Court register hit"),
)

# System steps that follow on immediately (section 6.5).
AUTO_FOLLOW = {S.FIELD_CONFIRMED.value: S.AWAITING_BOUNDARY.value, S.ACTION_RECORDED.value: S.POST_ACTION_WATCH.value}


def _find(state: str, to: str, role: str) -> Rule:
    candidates = [r for r in TABLE if state in r.src and r.dst == to]
    if not candidates:
        raise Refused(f"There is no step from {state} to {to}")
    for r in candidates:
        if role in r.actors or role in r.cosigners:
            return r
    allowed = sorted({a for r in candidates for a in r.actors | r.cosigners})
    raise Refused(f"Role {role} cannot move an alert from {state} to {to} (allowed: {', '.join(allowed)})", 403)


def _pending_request(db: Session, alert: Alert, to: str) -> ClosureRequest | None:
    return db.scalar(
        select(ClosureRequest).where(
            ClosureRequest.alert_id == alert.id,
            ClosureRequest.to_state == to,
            ClosureRequest.from_state == alert.state,
            ClosureRequest.resolution.is_(None),
        )
    )


def _public(data: dict) -> dict:
    return {k: v for k, v in data.items() if not k.startswith("_")}


def transition(
    db: Session,
    alert: Alert,
    to: str,
    *,
    actor: User | None = None,
    reason: str | None = None,
    data: dict | None = None,
    at: dt.datetime | None = None,
) -> dict:
    at = as_utc(at)
    to = S(to).value
    role = actor.role if actor else SYSTEM
    rule = _find(alert.state, to, role)
    if rule.cosigners:
        return _two_person(db, alert, rule, actor, reason, dict(data or {}), at)
    ctx = Ctx(db, alert, actor, at, to, reason, dict(data or {}), "single")
    for guard in rule.pre + rule.needs:
        guard(ctx)
    return _apply(ctx, rule)


def _two_person(db: Session, alert: Alert, rule: Rule, actor: User | None, reason: str | None, data: dict, at: dt.datetime) -> dict:
    if actor is None:
        raise Refused("A closure is signed by two people, never by the system")
    pending = _pending_request(db, alert, rule.dst)
    if pending is None:
        if actor.role not in rule.actors:
            raise Refused(f"The first signature must come from: {', '.join(sorted(rule.actors))}", 403)
        ctx = Ctx(db, alert, actor, at, rule.dst, reason, data, "first")
        for guard in rule.pre + rule.needs:
            guard(ctx)
        req = ClosureRequest(
            alert_id=alert.id,
            from_state=alert.state,
            to_state=rule.dst,
            requested_by=actor.id,
            reason=reason,
            reason_code=data.get("reason_code"),
            data=_public(data),
            requested_at=at,
        )
        db.add(req)
        db.flush()
        chain.record(
            db,
            actor_id=actor.id,
            action="closure.requested",
            entity="alert",
            entity_id=alert.id,
            details={"to": rule.dst, "reason": reason, "reason_code": req.reason_code, "closure_request_id": req.id, "role": actor.role},
            at=at,
        )
        return {"status": "awaiting_second_signature", "state": alert.state, "closure_request_id": req.id}

    if pending.requested_by == actor.id:
        raise Refused("A closure needs two different people. You have already signed this one.")
    if actor.role not in rule.cosigners:
        raise Refused(f"The second signature must come from: {', '.join(sorted(rule.cosigners))}", 403)
    ctx = Ctx(db, alert, actor, at, rule.dst, pending.reason, {**pending.data, **data}, "second")
    for guard in rule.pre:
        guard(ctx)
    pending.resolved_by = actor.id
    pending.resolved_at = at
    pending.resolution = "cosigned"
    db.flush()
    return _apply(
        ctx,
        rule,
        extra={
            "first_signer_id": pending.requested_by,
            "second_signer_id": actor.id,
            "closure_request_id": pending.id,
            "reason_code": pending.reason_code,
            "second_signer_note": reason,
        },
    )


def _apply(ctx: Ctx, rule: Rule, extra: dict | None = None) -> dict:
    db, alert, at = ctx.db, ctx.alert, ctx.at
    frm = alert.state
    if timers.is_overdue(frm, alert.due_at, at) and not escalation.already_recorded(db, alert):
        escalation.record_miss(db, alert, at=at, detected="on_transition")

    if frm == rule.dst:
        due = alert.due_at  # the timer keeps running
    else:
        due = ctx.data.get("_due_at") or timers.due_for(rule.dst, at)

    db.execute(text("SELECT set_config('lp.state_machine', 'on', true)"))
    alert.state = rule.dst
    alert.due_at = due
    alert.updated_at = at
    if "_owner_user_id" in ctx.data:
        alert.owner_user_id = ctx.data["_owner_user_id"]
    reopened = frm in REOPENABLE and rule.dst == S.TRIAGE.value
    if reopened:
        alert.reopened_count = (alert.reopened_count or 0) + 1
    db.flush()
    db.execute(text("SELECT set_config('lp.state_machine', 'off', true)"))

    if frm != rule.dst:
        for req in db.scalars(select(ClosureRequest).where(ClosureRequest.alert_id == alert.id, ClosureRequest.resolution.is_(None))):
            req.resolution = "superseded"
            req.resolved_at = at

    details = {
        "from": frm,
        "to": rule.dst,
        "role": ctx.role,
        "rule": rule.label,
        "reason": ctx.reason,
        "data": _public(ctx.data),
        "due_at": due.isoformat() if due else None,
    }
    for key in ("_owner_user_id", "_court_case_id", "_checklist_gaps", "_growth"):
        if key in ctx.data:
            details[key.lstrip("_")] = ctx.data[key]
    if reopened:
        details["reopened"] = True
    details.update(extra or {})
    chain.record(db, actor_id=ctx.actor.id if ctx.actor else None, action="alert.transition", entity="alert", entity_id=alert.id, details=details, at=at)

    result = {"status": "applied", "from": frm, "state": alert.state, "auto": []}
    follow = AUTO_FOLLOW.get(alert.state)
    if follow and frm != alert.state:
        try:
            nxt = transition(db, alert, follow, actor=None, at=at)
            result["auto"] = [follow, *nxt["auto"]]
            result["state"] = alert.state
        except Refused:
            pass
    return result


def allowed_actions(db: Session, alert: Alert, user: User, at: dt.datetime | None = None) -> list[dict]:
    """What this user could do next, with the reason when a step is blocked. The server still enforces."""
    at = as_utc(at)
    out = []
    for rule in TABLE:
        if alert.state not in rule.src:
            continue
        if user.role not in rule.actors and user.role not in rule.cosigners:
            continue
        signer = "single"
        if rule.cosigners:
            pending = _pending_request(db, alert, rule.dst)
            if pending is not None:
                if pending.requested_by == user.id:
                    out.append(_action(rule, "first", False, "Waiting for a second person to sign"))
                    continue
                if user.role not in rule.cosigners:
                    continue
                signer = "second"
            else:
                if user.role not in rule.actors:
                    continue
                signer = "first"
        ctx = Ctx(db, alert, user, at, rule.dst, signer=signer)
        try:
            for guard in rule.pre:
                guard(ctx)
            out.append(_action(rule, signer, True, None))
        except Refused as exc:
            out.append(_action(rule, signer, False, exc.message))
    return out


def _action(rule: Rule, signer: str, enabled: bool, blocked: str | None) -> dict:
    return {
        "to": rule.dst,
        "label": rule.label,
        "two_person": bool(rule.cosigners),
        "signer": signer,
        "enabled": enabled,
        "blocked_reason": blocked,
        "needs": [g.__name__.removeprefix("need_") for g in rule.needs],
    }


def apply_court_holds(db: Session, *, at: dt.datetime | None = None) -> list[int]:
    """Move every open alert with a live court matter to HOLD_LEGAL (run after a court register import)."""
    held = []
    for alert in db.scalars(select(Alert).where(Alert.state.in_(sorted(OPEN_STATES)))).all():
        if legal_check.live_court_case(db, alert.candidate_id) is not None:
            transition(db, alert, S.HOLD_LEGAL.value, actor=None, at=at)
            held.append(alert.id)
    return held
