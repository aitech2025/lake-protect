"""What officers do on an incident a citizen reported (DECISIONS.md D-064, D-067).

The district officer of the area and senior officials may (the admin takes no step on an incident):
- **acknowledge** it, once each, with an optional note. The first acknowledgement starts the
  review, and the citizen is told an official is reviewing it.
- **add notes** at any time. Notes stay inside and are kept for good.
- **request a satellite look**: the latest, or a past date to compare (app.citizen.incident).
- **request a sharper paid image**. A senior official approves or declines it; nothing is ordered
  in the prototype.
- **attach the legal records** at the place. Each attachment is a dated snapshot, kept beside the
  earlier ones.
- **attach a legal document**: a file or a reference, kept on the location as well. The field
  officer on the visit may attach documents and add notes too.
- **add the place to the weekly watch**, with a reason, when it is not watched yet.

Deciding follows the incident lifecycle (app.workflow.incidents): the district officer recommends,
the senior official approves and closes.

Every step is in the audit log. The citizen is told the steps that matter to them, in their
language, never an official's note.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.citizen import service as citizen
from app.citizen import texts
from app.models import Alert, Asset, Candidate, ImageryRequest, IncidentLegalRecord, IncidentNote, LegalCheck, User
from app.services import boundaries as bsvc
from app.services import documents as doc_svc
from app.services import locations as loc_svc
from app.workflow import incidents as lifecycle

NOTE_MAX = 2000


def require_citizen(alert: Alert) -> None:
    if alert.origin != "citizen":
        raise lifecycle.Refused("This is for incidents opened by a citizen's report", 422)


def require_officer(db: Session, alert: Alert, user: User, *, field_officer: bool = False) -> None:
    """The district officer of the area or a senior official; with `field_officer`, also the one on the visit."""
    who = lifecycle.Actor(db, alert, user)
    if who.officer or (field_officer and who.assigned):
        return
    raise lifecycle.Refused("Only the officers working this incident can do this", 403)


def _text(value: str | None, what: str = "A note") -> str:
    value = (value or "").strip()
    if not value:
        raise lifecycle.Refused(f"{what} is required", 422)
    if len(value) > NOTE_MAX:
        raise lifecycle.Refused(f"Keep it under {NOTE_MAX:,} characters", 422)
    return value


# Acknowledging and notes ------------------------------------------------------------------------
def acknowledge(db: Session, alert: Alert, user: User, note: str | None, at: dt.datetime) -> IncidentNote:
    require_citizen(alert)
    require_officer(db, alert, user)
    if db.scalar(select(IncidentNote.id).where(IncidentNote.alert_id == alert.id, IncidentNote.author_id == user.id,
                                               IncidentNote.kind == "acknowledged")):
        raise lifecycle.Refused("You have already acknowledged this incident")
    row = IncidentNote(alert_id=alert.id, author_id=user.id, kind="acknowledged", text=(note or "").strip()[:NOTE_MAX] or "Acknowledged",
                       at=at, is_demo=alert.is_demo)
    db.add(row)
    db.flush()
    from app.notify import service as notify

    notify.acknowledge_for_alert(db, user, alert, "review", at)
    chain.record(db, actor_id=user.id, action="incident.acknowledged", entity="alert", entity_id=alert.id, at=at,
                 details={"note_id": row.id})
    if alert.state == lifecycle.S.OPEN.value:
        lifecycle.transition(db, alert, lifecycle.S.UNDER_REVIEW.value, actor=user, note=f"Acknowledged by {user.name}", at=at,
                             details={"by_acknowledgement": True})
    return row


def add_note(db: Session, alert: Alert, user: User, note: str, at: dt.datetime) -> IncidentNote:
    require_officer(db, alert, user, field_officer=True)
    row = IncidentNote(alert_id=alert.id, author_id=user.id, kind="note", text=_text(note), at=at, is_demo=alert.is_demo)
    db.add(row)
    db.flush()
    chain.record(db, actor_id=user.id, action="incident.note", entity="alert", entity_id=alert.id, at=at, details={"note_id": row.id})
    return row


# Sharper images ---------------------------------------------------------------------------------
def decide_imagery(db: Session, req: ImageryRequest, admin: User, approve: bool, note: str | None, at: dt.datetime) -> None:
    """A senior official approves or declines a sharper paid image (D-067)."""
    if admin.role != "senior_official":
        raise lifecycle.Refused("A senior official approves sharper images", 403)
    if req.status != "requested":
        raise lifecycle.Refused(f"This request is already {req.status}")
    req.status = "approved" if approve else "declined"
    req.decided_by, req.decided_at, req.decision_note = admin.id, at, (note or "").strip() or None
    if approve:
        req.approved_by = admin.id
    db.flush()
    chain.record(db, actor_id=admin.id, action="imagery.approved" if approve else "imagery.declined", entity="alert", entity_id=req.alert_id,
                 at=at, details={"imagery_request_id": req.id, "note": req.decision_note})


# Legal records ----------------------------------------------------------------------------------
NOT_CONNECTED = [
    "Section 22A list of prohibited properties (Registration and Stamps)",
    "Bhu Bharati Record of Rights and mutations",
    "Live case status from CCMS and eCourts",
    "Police FIRs on the land",
]


def _iso(v):
    return v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v


def legal_snapshot(db: Session, alert: Alert, at: dt.datetime) -> dict:
    """The legal records at the incident's place, as they stand now, each with its source."""
    cand = db.get(Candidate, alert.candidate_id)
    asset = db.get(Asset, cand.asset_id)
    params = {"c": cand.id, "demo": asset.is_demo, "a": asset.id}
    parcels = db.execute(text(
        """
        SELECT p.village, p.survey_no, p.sub_division, p.land_category, p.recorded_category, p.extent_acres, p.bhudhaar,
               round(ST_Area(ST_Transform(ST_Intersection(p.geom, c.geom), 32644))::numeric, 0) AS overlap_sq_m
        FROM land_parcels_current p, candidates c
        WHERE c.id = :c AND p.is_sample = :demo AND ST_Intersects(p.geom, c.geom)
        ORDER BY overlap_sq_m DESC, p.survey_no LIMIT 20
        """), params).mappings().all()
    courts = db.execute(text(
        """
        SELECT k.court, k.case_no, k.status, k.next_hearing FROM court_cases k, candidates c, assets a
        WHERE c.id = :c AND a.id = c.asset_id AND k.is_demo = :demo
          AND ((k.geom IS NOT NULL AND ST_Intersects(k.geom, c.geom)) OR k.asset_id = a.id
               OR (cardinality(k.survey_numbers) > 0 AND k.survey_numbers && a.survey_numbers))
        ORDER BY k.next_hearing NULLS LAST, k.case_no
        """), params).mappings().all()
    permits = db.execute(text(
        """
        SELECT p.ref, p.kind, p.source, p.valid_from, p.valid_to FROM permits p, candidates c
        WHERE c.id = :c AND p.is_demo = :demo AND ST_Intersects(p.geom, ST_Buffer(c.geom::geography, 50)::geometry)
        ORDER BY p.valid_from DESC
        """), params).mappings().all()
    works = db.execute(text(
        """
        SELECT w.ref, w.agency, w.description, w.starts_on, w.ends_on FROM authorised_works w, candidates c
        WHERE c.id = :c AND w.is_demo = :demo AND ST_Intersects(w.geom, ST_Buffer(c.geom::geography, 50)::geometry)
        ORDER BY w.starts_on DESC
        """), params).mappings().all()
    primary = bsvc.primary_of(bsvc.current_boundary_set(db, asset.id))
    check = db.scalar(select(LegalCheck).where(LegalCheck.candidate_id == cand.id).order_by(LegalCheck.id.desc()).limit(1))
    documents = [d for d in doc_svc.list_for(db, asset.id) if not d.get("superseded")]
    clean = lambda rows: [{k: (float(v) if hasattr(v, "is_finite") else _iso(v)) for k, v in dict(r).items()} for r in rows]  # noqa: E731
    return {
        "as_of": at.isoformat(),
        "place": {"name": asset.name, "type": asset.type, "district": asset.district, "mandal": asset.mandal, "village": asset.village,
                  "survey_numbers": asset.survey_numbers or [], "custodian": asset.custodian_agency},
        "boundary": None if primary is None else {
            "status": primary["status"], "version": primary["version"], "source": primary["source_name"],
            "notification_ref": primary["notification_ref"], "source_date": _iso(primary["source_date"]), "certified_by": primary["certified_by"],
        },
        "land_records": clean(parcels),
        "documents": [{k: d[k] for k in ("id", "doc_type", "title", "reference", "issued_on", "issued_by", "sha256", "has_file")} for d in documents],
        "court_cases": clean(courts),
        "permits": clean(permits),
        "authorised_works": clean(works),
        "legal_check": None if check is None else {"zone": check.zone, "verdict": check.result, "flags": check.flags or [],
                                                   "rule_version": check.rule_version, "checked_at": _iso(check.checked_at)},
        "not_connected": NOT_CONNECTED,
    }


def attach_legal(db: Session, alert: Alert, user: User, at: dt.datetime) -> IncidentLegalRecord:
    require_officer(db, alert, user)
    records = legal_snapshot(db, alert, at)
    row = IncidentLegalRecord(alert_id=alert.id, attached_by=user.id, at=at, records=records, is_demo=alert.is_demo)
    db.add(row)
    db.flush()
    chain.record(db, actor_id=user.id, action="incident.legal_records_attached", entity="alert", entity_id=alert.id, at=at,
                 details={"snapshot_id": row.id, **{k: len(records[k]) for k in ("land_records", "documents", "court_cases", "permits", "authorised_works")}})
    return row


def attach_document(db: Session, alert: Alert, user: User, at: dt.datetime, **doc) -> object:
    require_officer(db, alert, user, field_officer=True)
    cand = db.get(Candidate, alert.candidate_id)
    asset = db.get(Asset, cand.asset_id)
    row = doc_svc.add(db, asset, actor_id=user.id, at=at, alert_id=alert.id, **doc)
    chain.record(db, actor_id=user.id, action="incident.document_attached", entity="alert", entity_id=alert.id, at=at,
                 details={"document_id": row.id, "doc_type": row.doc_type})
    return row


# The weekly watch -------------------------------------------------------------------------------
def watch_place(db: Session, alert: Alert, user: User, reason: str, name: str | None, at: dt.datetime) -> Asset:
    """Put the incident's place on the weekly watch, so every screen from now on looks at it."""
    require_citizen(alert)
    require_officer(db, alert, user)
    cand = db.get(Candidate, alert.candidate_id)
    asset = db.get(Asset, cand.asset_id)
    if asset.monitored:
        raise lifecycle.Refused(f"{asset.name} is already on the weekly watch")
    reason = _text(reason, "A reason")
    name = (name or "").strip()
    if name and asset.type == "reported_place":
        old, asset.name = asset.name, name[:200]
        chain.record(db, actor_id=user.id, action="location.renamed", entity="asset", entity_id=asset.id, at=at,
                     details={"from": old, "to": asset.name})
    try:
        loc_svc.set_monitoring(db, user, asset, monitored=True, reason=reason, at=at)
    except loc_svc.LocationError as exc:
        raise lifecycle.Refused(str(exc), 422) from exc
    place = {"en": asset.name, "te": asset.name_te or asset.name}
    for report in citizen.open_reports_of(db, alert.id):
        citizen.add_event(db, report, "added_to_watch", status="CHECKING", note=texts.note("added_to_watch", place=place), at=at, actor=user,
                          internal=f"Added to the weekly watch by {user.name}")
    return asset


def notes_of(db: Session, alert_id: int) -> list[dict]:
    rows = db.execute(text(
        "SELECT n.id, n.kind, n.text, n.at, u.name AS author, u.role::text AS role FROM incident_notes n JOIN users u ON u.id = n.author_id "
        "WHERE n.alert_id = :a ORDER BY n.id"), {"a": alert_id}).mappings().all()
    return [{**dict(r), "at": r["at"].isoformat()} for r in rows]
