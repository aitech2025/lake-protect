"""Candidate ingest (section 9.5 POST /candidates): pipeline output in, legal check and priority run.

Order matters:
1. Refuse water loss alone (invariant 8) and anything below the minimum area or persistence rule.
2. Store the candidate and run the legal check.
3. A system closure (out of scope, legacy, authorised) is logged as a closed alert and goes no further.
4. Otherwise, if the change overlaps an alert closed by people and persists, reopen that alert.
   If it overlaps an alert still open, record the re-check on it and create nothing new.
5. Otherwise create the alert and move it to the legal check's result.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib

from geoalchemy2.elements import WKTElement
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.clock import as_utc
from app.enums import AlertState, ChangeType, Mode, SensorBasis, Stage
from app.models import Alert, Asset, Candidate, Observation
from app.rules import config as rules
from app.rules import legal_check, priority
from app.services import boundaries as bsvc
from app.storage import store
from app.workflow import state_machine as sm

PERSISTENCE_MIN_DAYS = 5


class IngestRefused(Exception):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.message = message
        self.status = status


class ObservationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sensor: str
    scene_id: str
    acquired_at: dt.datetime
    cloud_pct: float | None = None
    stac_href: str | None = None
    processing_version: str | None = None
    licence_notice: str
    sha256: str | None = None


class CandidateIn(BaseModel):
    """Owner-blind by construction: unknown fields, such as any owner name, are rejected (rule 4)."""

    model_config = ConfigDict(extra="forbid")
    asset_id: int
    geometry: dict
    change_type: ChangeType
    stage_estimate: Stage | None = None
    last_clear_at: dt.date | None = None
    first_changed_at: dt.date
    observations: list[ObservationIn] = Field(min_length=1)
    sensor_basis: SensorBasis
    confidence: float = Field(ge=0, le=1)
    rule_version: str
    flags: list[str] = []
    area_growth: float | None = None
    before_chip_png_b64: str | None = None
    after_chip_png_b64: str | None = None


def _store_chip(asset: Asset, kind: str, b64: str | None) -> str | None:
    if not b64:
        return None
    data = base64.b64decode(b64)
    if not data.startswith(b"\x89PNG"):
        raise IngestRefused("Image chips must be PNG")
    digest = hashlib.sha256(data).hexdigest()
    return store.put_object(f"chips/{asset.asset_key}/{digest[:16]}_{kind}.png", data)


def _observations(db: Session, items: list[ObservationIn], is_demo: bool) -> list[Observation]:
    rows = []
    for item in items:
        row = db.scalar(select(Observation).where(Observation.scene_id == item.scene_id, Observation.sensor == item.sensor))
        if row is None:
            row = Observation(**item.model_dump(), is_demo=is_demo)
            db.add(row)
            db.flush()
        rows.append(row)
    return rows


def _check_persistence(obs: list[Observation]) -> None:
    """Section 8.4: at least two independent observations at least 5 days apart."""
    times = sorted(o.acquired_at for o in obs)
    if len({o.scene_id for o in obs}) < 2 or (times[-1] - times[0]) < dt.timedelta(days=PERSISTENCE_MIN_DAYS):
        raise IngestRefused("The persistence rule needs two observations at least 5 days apart")


def _overlapping_alerts(db: Session, candidate: Candidate, states: frozenset[str]) -> list[Alert]:
    ids = db.scalars(
        text(
            """
            SELECT al.id FROM alerts al JOIN candidates c ON c.id = al.candidate_id, candidates n
            WHERE n.id = :n AND c.asset_id = n.asset_id AND c.id <> n.id
              AND al.state::text = ANY(:states) AND ST_Intersects(c.geom, n.geom)
            ORDER BY al.updated_at DESC
            """
        ),
        {"n": candidate.id, "states": sorted(states)},
    ).all()
    return [db.get(Alert, i) for i in ids]


def _new_alert(db: Session, candidate: Candidate, asset: Asset, at: dt.datetime) -> Alert:
    alert = Alert(
        code=f"pending-{candidate.id}",
        candidate_id=candidate.id,
        state=AlertState.CANDIDATE.value,
        is_demo=asset.is_demo,
        created_at=at,
        updated_at=at,
        priority_factors={},
    )
    db.add(alert)
    db.flush()
    alert.code = f"{'DEMO' if asset.is_demo else 'LP'}-{at.year}-{alert.id:04d}"
    score, factors = priority.score(
        stage=candidate.stage_estimate,
        area_sq_m=float(candidate.area_sq_m),
        growth=float(candidate.area_growth) if candidate.area_growth is not None else None,
        cohort=asset.cohort,
    )
    alert.priority_score = score
    alert.priority_factors = factors
    db.flush()
    chain.record(
        db,
        actor_id=None,
        action="alert.created",
        entity="alert",
        entity_id=alert.id,
        details={"code": alert.code, "candidate_id": candidate.id, "priority": score},
        at=at,
    )
    return alert


def ingest(db: Session, body: CandidateIn, *, at: dt.datetime | None = None) -> dict:
    at = as_utc(at)
    if body.change_type == ChangeType.water_loss:
        raise IngestRefused("Water loss alone never creates an alert (section 8.4)")
    asset = db.get(Asset, body.asset_id)
    if asset is None:
        raise IngestRefused("Unknown asset", 404)
    try:
        geom = bsvc.to_multipolygon(body.geometry)
    except bsvc.BoundaryError as exc:
        raise IngestRefused(str(exc)) from exc
    area = db.scalar(text("SELECT ST_Area(ST_Transform(ST_GeomFromText(:w, 4326), 32644))"), {"w": geom.wkt})
    if area < rules.rules()["min_candidate_area_sq_m"]:
        raise IngestRefused(f"Area {area:.0f} sq m is below the minimum of {rules.rules()['min_candidate_area_sq_m']} sq m")
    primary = bsvc.primary_of(bsvc.boundary_set_at(db, asset.id, at.date()))
    if primary is None:
        raise IngestRefused("The asset has no boundary in force")

    if body.first_changed_at > at.date() or any(o.acquired_at > at for o in body.observations):
        raise IngestRefused("A candidate cannot use observations acquired after its ingest time")
    obs = _observations(db, body.observations, asset.is_demo)
    _check_persistence(obs)
    candidate = Candidate(
        asset_id=asset.id,
        boundary_id=primary["id"],
        geom=WKTElement(geom.wkt, srid=4326),
        area_sq_m=round(area, 2),
        change_type=body.change_type.value,
        stage_estimate=body.stage_estimate.value if body.stage_estimate else None,
        last_clear_at=body.last_clear_at,
        first_changed_at=body.first_changed_at,
        observation_ids=[o.id for o in obs],
        sensor_basis=body.sensor_basis.value,
        confidence=body.confidence,
        rule_version=body.rule_version,
        flags=sorted(set(body.flags)),
        before_chip=_store_chip(asset, "before", body.before_chip_png_b64),
        after_chip=_store_chip(asset, "after", body.after_chip_png_b64),
        area_growth=body.area_growth,
        created_at=at,
    )
    db.add(candidate)
    db.flush()
    check, decision = legal_check.run(db, candidate, asset, at)

    if decision.result.value in sm.SYSTEM_CLOSURES:
        alert = _new_alert(db, candidate, asset, at)
        sm.transition(db, alert, decision.result.value, at=at)
        return _out(alert, candidate, check, "closed_by_legal_check")

    if rules.mode_for_cohort(asset.cohort) != Mode.WATCH:
        closed = _overlapping_alerts(db, candidate, sm.REOPENABLE)
        if closed:
            alert = closed[0]
            sm.transition(db, alert, AlertState.TRIAGE.value, data={"recheck_candidate_id": candidate.id}, at=at)
            if legal_check.live_court_case(db, alert.candidate_id) is not None:
                sm.transition(db, alert, AlertState.HOLD_LEGAL.value, at=at)
            return _out(alert, candidate, check, "reopened")
    open_alerts = _overlapping_alerts(db, candidate, sm.OPEN_STATES | {AlertState.HOLD_LEGAL.value})
    if open_alerts:
        alert = open_alerts[0]
        chain.record(
            db,
            actor_id=None,
            action="recheck.persisting",
            entity="alert",
            entity_id=alert.id,
            details={"recheck_candidate_id": candidate.id, "area_sq_m": float(candidate.area_sq_m)},
            at=at,
        )
        return _out(alert, candidate, check, "recorded_on_open_alert")

    alert = _new_alert(db, candidate, asset, at)
    sm.transition(db, alert, decision.result.value, at=at)
    return _out(alert, candidate, check, "created")


def _out(alert: Alert, candidate: Candidate, check, outcome: str) -> dict:
    return {
        "outcome": outcome,
        "alert_id": alert.id,
        "alert_code": alert.code,
        "state": alert.state,
        "candidate_id": candidate.id,
        "legal_check": {"zone": check.zone, "result": check.result, "flags": check.flags, "rule_version": check.rule_version},
    }
