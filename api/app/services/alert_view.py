"""Incident list rows and the incident detail payload.

Two roles see the same incidents (DECISIONS.md D-057). Owner names never appear here: the
change is described by what the satellite saw, where it is and what the records say about the
land. Each incident says plainly what changed: construction, land fill, levelling or clearing.
"""
from __future__ import annotations

import datetime as dt

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    Asset,
    AssetDocument,
    Candidate,
    EvidencePack,
    ImageryRequest,
    IncidentReview,
    LegalCheck,
    Notification,
    Observation,
    User,
)
from app.rules import config as rules
from app.rules import legal_check
from app.services import boundaries as bsvc
from app.workflow import incidents as lifecycle

STATEMENT_EN = "Imagery shows physical change. It does not establish title or legality."

# What changed, in the words the officials use.
CHANGE_LABEL = {
    "building": "Construction",
    "small_structure": "Construction (small structure)",
    "soil_fill": "Land fill",
    "levelling": "Levelling",
    "clearing": "Clearing",
    "water_loss": "Water loss",
    "other": "Other change",
}
ZONE_LABEL = {
    "inside_ftl": "inside the boundary",
    "buffer": "in the buffer zone",
    "watch_ring": "in the 100 m watch ring",
    "outside": "outside the watched zones",
}

_LIST_SQL = """
SELECT al.id, al.code, al.state::text AS state, al.resolution, al.closed_at, al.related_alert_id,
       al.priority_score, al.is_demo, al.created_at, al.updated_at,
       a.id AS asset_id, a.name AS asset_name, a.name_te AS asset_name_te, a.cohort::text AS cohort,
       a.type::text AS asset_type, a.district, a.mandal, a.village, c.id AS candidate_id, c.change_type::text AS change_type,
       c.stage_estimate::text AS stage_estimate, c.area_sq_m, c.first_changed_at, c.last_clear_at,
       c.sensor_basis::text AS sensor_basis, c.confidence, c.flags,
       lc.zone::text AS zone, lc.alert_class::text AS alert_class, lc.boundary_status::text AS checked_boundary_status,
       lc.result::text AS legal_verdict,
       (SELECT count(*) FROM incident_reviews r WHERE r.alert_id = al.id) AS review_count,
       (SELECT r.outcome FROM incident_reviews r WHERE r.alert_id = al.id ORDER BY r.id DESC LIMIT 1) AS last_review_outcome,
       ST_X(ST_PointOnSurface(c.geom)) AS lon, ST_Y(ST_PointOnSurface(c.geom)) AS lat,
       ST_AsGeoJSON(c.geom)::json AS geometry,
       al.origin, al.report_id, cr.ref AS report_ref, cr.channel AS report_channel, cr.what AS report_what,
       cr.created_at AS report_at, cr.placed_by AS report_placed_by,
       sr.status AS review_status, sr.result AS review_result, sr.after_date AS review_after_date,
       sr.first_changed_at AS review_first_changed, sr.change_area_sq_m AS review_change_area, sr.source AS review_source,
       (SELECT count(*) FROM citizen_reports r2 WHERE r2.alert_id = al.id) AS citizen_reports
FROM alerts al
JOIN candidates c ON c.id = al.candidate_id
JOIN assets a ON a.id = c.asset_id
LEFT JOIN citizen_reports cr ON cr.id = al.report_id
LEFT JOIN satellite_reviews sr ON sr.alert_id = al.id
LEFT JOIN LATERAL (SELECT * FROM legal_checks l WHERE l.candidate_id = c.id ORDER BY l.id DESC LIMIT 1) lc ON true
WHERE (CAST(:alert_id AS bigint) IS NULL OR al.id = CAST(:alert_id AS bigint))
  AND (CAST(:asset_id AS bigint) IS NULL OR a.id = CAST(:asset_id AS bigint))
ORDER BY CASE al.state WHEN 'OPEN' THEN 0 WHEN 'UNDER_REVIEW' THEN 1 WHEN 'CONFIRMED' THEN 2 WHEN 'DISMISSED' THEN 3 ELSE 4 END,
         al.priority_score DESC NULLS LAST, al.id DESC
"""


def describe(change_type: str, area_sq_m: float | None, zone: str | None, first_changed_at) -> str:
    """One plain sentence: what changed, how big, where, and when it was first seen."""
    what = CHANGE_LABEL.get(change_type, "Change")
    size = f" of about {area_sq_m:,.0f} sq m" if area_sq_m else ""
    where = f" {ZONE_LABEL[zone]}" if zone in ZONE_LABEL else ""
    when = f", first seen {first_changed_at:%d %b %Y}" if isinstance(first_changed_at, (dt.date, dt.datetime)) else ""
    return f"{what}{size}{where}{when}"


def citizen_summary(row: dict) -> tuple[str, str]:
    """A citizen incident in one sentence, English and Telugu: what was reported, when, and what the
    satellite review shows (D-063)."""
    from app.citizen import texts

    what = texts.REPORTED.get(row["report_what"], texts.REPORTED["other"])
    day = row["report_at"]
    en, te = f"{what['en']} reported by a citizen on {day:%d %b %Y}", f"{day:%d %b %Y}న ఒక పౌరుడు తెలిపారు: {what['te']}"
    result, status = row.get("review_result"), row.get("review_status")
    if result == "change_found":
        area = f" of about {float(row['review_change_area']):,.0f} sq m" if row.get("review_change_area") else ""
        area_te = f"సుమారు {float(row['review_change_area']):,.0f} చ.మీ. " if row.get("review_change_area") else ""
        first = row.get("review_first_changed")
        en += f"; the satellite shows a change{area}" + (f", first seen {first:%d %b %Y}" if first else "")
        te += f"; ఉపగ్రహ చిత్రంలో {area_te}మార్పు కనిపిస్తోంది" + (f", మొదట {first:%d %b %Y}న" if first else "")
    elif result == "no_change":
        after = row.get("review_after_date")
        en += "; no change visible on satellite images" + (f" up to {after:%d %b %Y}" if after else "")
        te += "; ఉపగ్రహ చిత్రాల్లో మార్పు కనిపించలేదు" + (f" ({after:%d %b %Y} వరకు)" if after else "")
    elif result == "no_clear_look":
        en += "; no clear satellite image yet"
        te += "; ఇంకా స్పష్టమైన ఉపగ్రహ చిత్రం లేదు"
    elif status == "pending":
        en += "; satellite review pending"
        te += "; ఉపగ్రహ పరిశీలన జరుగుతోంది"
    elif status == "failed":
        en += "; the satellite review could not be done"
        te += "; ఉపగ్రహ పరిశీలన జరగలేదు"
    return en, te


def _row_out(row: dict) -> dict:
    out = dict(row)
    for k in ("priority_score", "area_sq_m", "confidence", "review_change_area"):
        out[k] = float(out[k]) if out.get(k) is not None else None
    out["mode"] = rules.mode_for_cohort(row["cohort"]).value
    out["area_acres"] = round(out["area_sq_m"] / 4046.86, 2) if out["area_sq_m"] else None
    out["change_label"] = CHANGE_LABEL.get(row["change_type"], row["change_type"])
    out["summary"] = describe(row["change_type"], out["area_sq_m"], row["zone"], row["first_changed_at"])
    out["summary_te"] = None
    if row.get("origin") == "citizen":
        out["summary"], out["summary_te"] = citizen_summary(row)
    out["court_matter"] = row["legal_verdict"] == "HOLD_LEGAL"
    out["boundary_confirmed"] = bool(row["checked_boundary_status"]) and rules.is_confirmed_status(row["checked_boundary_status"])
    out["permit_conflict"] = "permit_conflict" in (row["flags"] or [])
    return out


# Open and not yet decided for longer than this: "waiting" on the monthly page and the dashboard.
WAITING_DAYS = 14
# In an area filter, "-" means "not recorded": an asset with no district, mandal or village.
NOT_RECORDED = "-"


def _same(have: str | None, want: str) -> bool:
    want = "" if want == NOT_RECORDED else want
    return (have or "").strip().lower() == want.strip().lower()


def in_area(row: dict, district: str | None = None, mandal: str | None = None, village: str | None = None) -> bool:
    """Does an incident or asset row fall in an area? Names match without regard to case."""
    return all(want is None or _same(row.get(k), want) for k, want in (("district", district), ("mandal", mandal), ("village", village)))


def is_waiting(row: dict, now: dt.datetime) -> bool:
    """Open or under review for more than 14 whole days: the monthly page's rule."""
    return row["state"] in lifecycle.REVIEWABLE and (now - row["created_at"]).days > WAITING_DAYS


def list_alerts(db: Session, *, state=None, change_type=None, cohort=None, asset_id=None, district=None, mandal=None,
                village=None, waiting: bool = False, new_in_week: str | None = None, now: dt.datetime | None = None) -> list[dict]:
    rows = db.execute(text(_LIST_SQL), {"alert_id": None, "asset_id": asset_id}).mappings().all()
    out = [_row_out(dict(r)) for r in rows]
    if state:
        out = [r for r in out if r["state"] in set(state.split(","))]
    if change_type:
        out = [r for r in out if r["change_type"] in set(change_type.split(","))]
    if cohort:
        out = [r for r in out if r["cohort"] in set(cohort.split(","))]
    if any(v is not None for v in (district, mandal, village)):
        out = [r for r in out if in_area(r, district, mandal, village)]
    if waiting:
        now = now or dt.datetime.now(dt.timezone.utc)
        out = [r for r in out if is_waiting(r, now)]
    if new_in_week:
        out = [r for r in out if r["resolution"] != "auto" and "{}-W{:02d}".format(*r["created_at"].isocalendar()[:2]) == new_in_week]
    return out


def row_for(db: Session, alert_id: int) -> dict:
    """One incident's list row: what changed, where, and its flags (for notifications)."""
    row = db.execute(text(_LIST_SQL), {"alert_id": alert_id, "asset_id": None}).mappings().first()
    if row is None:
        raise HTTPException(404, "Incident not found")
    return _row_out(dict(row))


def get_visible(db: Session, alert_id: int) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(404, "Incident not found")
    return alert


def _iso(v):
    return v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v


def _citizen_block(db: Session, alert: Alert) -> dict | None:
    """The report that opened a citizen incident (D-063): what the citizen said, never who they are."""
    from app.citizen import locate
    from app.models import CitizenReport

    if alert.report_id is None:
        return None
    r = db.get(CitizenReport, alert.report_id)
    lon, lat = db.execute(text("SELECT ST_X(geom), ST_Y(geom) FROM citizen_reports WHERE id = :i"), {"i": r.id}).one()
    asset = db.get(Asset, db.get(Candidate, alert.candidate_id).asset_id)
    area_source = None
    if asset.type == "reported_place":
        area_source = "nearest demo location" if asset.is_demo else (locate.AREA_SOURCE if asset.district else None)
    return {
        "report_id": r.id, "ref": r.ref, "channel": r.channel, "language": r.language, "what": r.what, "description": r.description,
        "location_text": r.location_text, "placed_by": r.placed_by, "photos": len(r.photos or []), "created_at": _iso(r.created_at),
        "lon": lon, "lat": lat, "updates": r.wants_updates, "source_ref": r.source_ref, "reported_place": asset.type == "reported_place",
        "area_source": area_source,
        "survey_numbers": locate.survey_numbers(db, lon, lat, r.is_demo) if lon is not None else [],
    }


def _review_block(db: Session, alert: Alert) -> dict | None:
    from app.models import SatelliteReview

    rv = db.scalar(select(SatelliteReview).where(SatelliteReview.alert_id == alert.id))
    if rv is None:
        return None
    return {
        "status": rv.status, "result": rv.result, "source": rv.source, "requested_at": _iso(rv.requested_at), "done_at": _iso(rv.done_at),
        "before_date": _iso(rv.before_date), "after_date": _iso(rv.after_date), "scenes": rv.scenes, "change_type": rv.change_type,
        "change_area_sq_m": float(rv.change_area_sq_m) if rv.change_area_sq_m is not None else None,
        "first_changed_at": _iso(rv.first_changed_at), "detail": rv.detail, "attempts": rv.attempts,
        "has_images": bool(rv.after_chip),
    }


def detail(db: Session, alert: Alert, user: User) -> dict:
    row = _row_out(dict(db.execute(text(_LIST_SQL), {"alert_id": alert.id, "asset_id": None}).mappings().one()))
    cand = db.get(Candidate, alert.candidate_id)
    asset = db.get(Asset, cand.asset_id)
    bset = bsvc.current_boundary_set(db, asset.id)
    checks = db.scalars(select(LegalCheck).where(LegalCheck.candidate_id == cand.id).order_by(LegalCheck.id)).all()
    latest = checks[-1] if checks else None
    observations = db.scalars(select(Observation).where(Observation.id.in_(cand.observation_ids or [0])).order_by(Observation.acquired_at)).all()
    users = {u.id: u for u in db.scalars(select(User))}
    timeline = db.execute(
        text(
            "SELECT id, actor_id, action, details, at FROM audit_log WHERE entity = 'alert' AND entity_id = :i "
            "AND action NOT LIKE 'view.%' ORDER BY id"
        ),
        {"i": str(alert.id)},
    ).mappings().all()
    primary = bsvc.primary_of(bset)
    court_now = legal_check.live_court_case(db, cand.id)
    related = db.get(Alert, alert.related_alert_id) if alert.related_alert_id else None
    documents = db.scalar(select(func.count()).select_from(AssetDocument).where(AssetDocument.asset_id == asset.id))

    return {
        **row,
        "statement": STATEMENT_EN,
        "statement_key": "statement.imagery",
        "candidate": {
            "id": cand.id,
            "geometry": row["geometry"],
            "change_type": cand.change_type,
            "change_label": CHANGE_LABEL.get(cand.change_type, cand.change_type),
            "stage_estimate": cand.stage_estimate,
            "area_sq_m": float(cand.area_sq_m),
            "last_clear_at": _iso(cand.last_clear_at),
            "first_changed_at": _iso(cand.first_changed_at),
            "sensor_basis": cand.sensor_basis,
            "optical_confirmation_pending": cand.sensor_basis == "radar_only",
            "confidence": float(cand.confidence),
            "rule_version": cand.rule_version,
            "flags": cand.flags,
            "has_image_pair": bool(cand.before_chip and cand.after_chip),
            "observations": [
                {"id": o.id, "sensor": o.sensor, "scene_id": o.scene_id, "acquired_at": _iso(o.acquired_at),
                 "cloud_pct": float(o.cloud_pct) if o.cloud_pct is not None else None, "licence_notice": o.licence_notice, "is_demo": o.is_demo}
                for o in observations
            ],
        },
        "asset": {
            "id": asset.id, "name": asset.name, "name_te": asset.name_te, "type": asset.type, "cohort": asset.cohort,
            "mode": rules.mode_for_cohort(asset.cohort).value, "baseline_date": _iso(asset.baseline_date),
            "survey_numbers": asset.survey_numbers, "is_demo": asset.is_demo,
            "area_acres": float(asset.area_acres) if asset.area_acres is not None else None,
            "documents": int(documents or 0),
        },
        "boundary": {
            "status": primary["status"] if primary else None,
            "version": primary["version"] if primary else None,
            "confirmed": bool(primary) and rules.is_confirmed_status(primary["status"]),
            "source_name": primary["source_name"] if primary else None,
            "source_url": primary["source_url"] if primary else None,
            "notification_ref": primary["notification_ref"] if primary else None,
            "features": [
                {"type": "Feature", "geometry": b["geometry"], "properties": {"kind": k, "status": b["status"], "version": b["version"]}}
                for k, b in bset.items()
            ],
        },
        "legal_check": None if latest is None else {
            "zone": latest.zone, "boundary_status": latest.boundary_status, "boundary_version": latest.boundary_version,
            "mode": latest.mode, "alert_class": latest.alert_class, "verdict": latest.result, "flags": latest.flags,
            "matched_permit_id": latest.matched_permit_id, "matched_work_id": latest.matched_work_id,
            "matched_court_case_id": latest.matched_court_case_id, "rule_version": latest.rule_version,
            "checked_at": _iso(latest.checked_at), "live_court_matter_now": court_now,
            "permit_conflict": "permit_conflict" in (latest.flags or []),
            "auto_close_reason": lifecycle.AUTO_CLOSE.get(latest.result),
        },
        "reviews": [
            {"id": r.id, "reviewer": users[r.reviewer_id].name, "outcome": r.outcome, "note": r.note, "reviewed_at": _iso(r.reviewed_at)}
            for r in db.scalars(select(IncidentReview).where(IncidentReview.alert_id == alert.id).order_by(IncidentReview.id))
        ],
        "related": None if related is None else {"id": related.id, "code": related.code, "state": related.state, "resolution": related.resolution},
        "timeline": [
            {"id": t["id"], "action": t["action"], "at": _iso(t["at"]), "actor": users[t["actor_id"]].name if t["actor_id"] in users else "System",
             "actor_role": users[t["actor_id"]].role if t["actor_id"] in users else "system", "details": t["details"]}
            for t in timeline
        ],
        "allowed_actions": lifecycle.allowed_actions(db, alert, user),
        # What this person was sent about the incident and has not acknowledged yet, while it is
        # still open or under review (D-059).
        "my_notifications": [] if alert.state not in lifecycle.REVIEWABLE else [
            {"id": n.id, "kind": n.kind, "created_at": _iso(n.created_at)}
            for n in db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.alert_id == alert.id,
                                                           Notification.needs_ack.is_(True), Notification.acknowledged_at.is_(None))
                                .order_by(Notification.id))
        ],
        "evidence_packs": [
            {"id": p.id, "version": p.version, "generated_at": _iso(p.generated_at), "manifest_sha256": p.manifest_sha256, "counsel_reviewed": p.counsel_reviewed}
            for p in db.scalars(select(EvidencePack).where(EvidencePack.alert_id == alert.id).order_by(EvidencePack.version))
        ],
        "citizen": _citizen_block(db, alert),
        "satellite_review": _review_block(db, alert),
        "imagery_requests": [
            {"id": r.id, "provider": r.provider, "area_sq_km": float(r.area_sq_km), "est_cost_usd": float(r.est_cost_usd) if r.est_cost_usd is not None else None, "status": r.status}
            for r in db.scalars(select(ImageryRequest).where(ImageryRequest.alert_id == alert.id))
        ],
        "policy_cutoff_date": rules.policy_cutoff_date().isoformat(),
    }
