"""Legal check (CONTEXT.md section 6.2), run on every candidate before analyst time or paid imagery.

`decide` is the section 6.2 function, step for step, over facts gathered from the database.
`run` gathers the facts with PostGIS, decides, and stores the result with the rule version, the
boundary version used and every record it matched.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.clock import as_utc
from app.enums import AlertClass, AlertState, AssetType, Cohort, Mode, Zone
from app.models import Asset, Candidate, LegalCheck
from app.rules import config as rules
from app.services import boundaries as bsvc


@dataclass
class Facts:
    zone: Zone
    first_changed_at: dt.date
    baseline_date: dt.date
    mode: Mode
    work_id: int | None = None
    permit_id: int | None = None
    court_case_id: int | None = None


@dataclass
class Decision:
    result: AlertState
    flags: set[str] = field(default_factory=set)


def decide(f: Facts) -> Decision:
    """Section 6.2, in the same order."""
    flags: set[str] = set()
    if f.zone == Zone.outside:
        return Decision(AlertState.CLOSED_OUT_OF_SCOPE, flags)
    if f.first_changed_at <= f.baseline_date:
        return Decision(AlertState.CLOSED_LEGACY, flags)  # logged, never alerted
    if f.work_id is not None:
        return Decision(AlertState.CLOSED_AUTHORISED, flags)  # stores the reference
    if f.permit_id is not None and f.zone == Zone.watch_ring:
        return Decision(AlertState.CLOSED_AUTHORISED, flags)
    if f.permit_id is not None:
        flags.add("permit_conflict")  # never auto-close inside FTL or buffer
    if f.court_case_id is not None:
        return Decision(AlertState.HOLD_LEGAL, flags)
    if f.mode == Mode.WATCH:
        return Decision(AlertState.WATCH_LIST, flags)
    return Decision(AlertState.TRIAGE, flags)


# Interiors must overlap: a candidate that only touches a zone's edge is not inside it.
_INTERIOR = "T********"


def locate(db: Session, candidate_id: int, boundary_set: dict[str, dict]) -> Zone:
    """Most restrictive zone whose interior the candidate overlaps (DECISIONS.md D-016)."""
    order = [("ftl", Zone.inside_ftl), ("parcel", Zone.inside_ftl), ("buffer", Zone.buffer), ("watch_ring", Zone.watch_ring)]
    for kind, zone in order:
        row = boundary_set.get(kind)
        if row is None:
            continue
        hit = db.scalar(
            text("SELECT ST_Relate(c.geom, b.geom, :pat) FROM candidates c, boundaries b WHERE c.id = :c AND b.id = :b"),
            {"pat": _INTERIOR, "c": candidate_id, "b": row["id"]},
        )
        if hit:
            return zone
    return Zone.outside


def matched_work(db: Session, candidate: Candidate) -> int | None:
    return db.scalar(
        text(
            """
            SELECT w.id FROM authorised_works w, candidates c
            WHERE c.id = :c AND ST_Relate(w.geom, c.geom, :pat)
              AND w.starts_on <= c.first_changed_at
              AND (w.ends_on IS NULL OR w.ends_on >= coalesce(c.last_clear_at, c.first_changed_at))
            ORDER BY w.id LIMIT 1
            """
        ),
        {"c": candidate.id, "pat": _INTERIOR},
    )


def matched_permit(db: Session, candidate: Candidate) -> int | None:
    return db.scalar(
        text(
            """
            SELECT p.id FROM permits p, candidates c
            WHERE c.id = :c AND ST_Relate(p.geom, c.geom, :pat)
              AND p.valid_from <= c.first_changed_at
              AND (p.valid_to IS NULL OR p.valid_to >= c.first_changed_at)
            ORDER BY p.id LIMIT 1
            """
        ),
        {"c": candidate.id, "pat": _INTERIOR},
    )


def live_court_case(db: Session, candidate_id: int) -> int | None:
    """A live court matter on the candidate's footprint, its asset, or a shared survey number."""
    return db.scalar(
        text(
            """
            SELECT k.id FROM court_cases k, candidates c, assets a
            WHERE c.id = :c AND a.id = c.asset_id
              AND k.status = ANY(:live)
              AND ((k.geom IS NOT NULL AND ST_Intersects(k.geom, c.geom))
                   OR (k.asset_id = a.id AND k.geom IS NULL)
                   OR (cardinality(k.survey_numbers) > 0 AND k.survey_numbers && a.survey_numbers))
            ORDER BY k.id LIMIT 1
            """
        ),
        {"c": candidate_id, "live": rules.live_court_statuses()},
    )


def alert_class_for(asset: Asset, court_case_id: int | None, private_title_claim: bool = False, zone: Zone | None = None) -> AlertClass:
    """Section 6.3. Land category, never an owner name."""
    if court_case_id is not None:
        return AlertClass.DISPUTED
    if asset.type == AssetType.recovered_parcel.value or asset.cohort == Cohort.A_RECOVERED.value:
        return AlertClass.GOVT_LAND
    if private_title_claim and zone in (Zone.inside_ftl.value, Zone.buffer.value):
        return AlertClass.RESTRICTED_PRIVATE
    return AlertClass.UNKNOWN


class NoBoundary(Exception):
    pass


def run(db: Session, candidate: Candidate, asset: Asset, at: dt.datetime | None = None) -> tuple[LegalCheck, Decision]:
    at = as_utc(at)
    bset = bsvc.boundary_set_at(db, asset.id, at.date())
    primary = bsvc.primary_of(bset)
    if primary is None:
        raise NoBoundary(f"Asset {asset.id} has no boundary in force on {at.date()}")
    facts = Facts(
        zone=locate(db, candidate.id, bset),
        first_changed_at=candidate.first_changed_at,
        baseline_date=asset.baseline_date,
        mode=rules.mode_for_cohort(asset.cohort),
        work_id=matched_work(db, candidate),
        permit_id=matched_permit(db, candidate),
        court_case_id=live_court_case(db, candidate.id),
    )
    decision = decide(facts)
    row = LegalCheck(
        candidate_id=candidate.id,
        zone=facts.zone.value,
        boundary_status=primary["status"],
        mode=facts.mode.value,
        alert_class=alert_class_for(asset, facts.court_case_id).value,
        result=decision.result.value,
        matched_permit_id=facts.permit_id,
        matched_work_id=facts.work_id if decision.result == AlertState.CLOSED_AUTHORISED else None,
        matched_court_case_id=facts.court_case_id,
        boundary_id=primary["id"],
        boundary_version=primary["version"],
        flags=sorted(decision.flags),
        rule_version=rules.rule_version(),
        checked_at=at,
    )
    db.add(row)
    if decision.flags:
        candidate.flags = sorted(set(candidate.flags or []) | decision.flags)
    db.flush()
    return row, decision
