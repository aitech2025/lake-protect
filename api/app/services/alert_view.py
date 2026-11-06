"""Alert queue rows and the alert detail payload (section 9.1).

Access is decided here, on the server: field officers see only alerts assigned to them inside
their area (section 10). Owner claims are personal data, so claimant names go only to the legal
team and the nodal officer.
"""
from __future__ import annotations

import datetime as dt

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.clock import as_utc
from app.enums import Role
from app.models import (
    Alert,
    Asset,
    Candidate,
    ClosureRequest,
    EvidencePack,
    FieldCheck,
    ImageryRequest,
    LegalCheck,
    Observation,
    OfficerRecord,
    OwnerClaim,
    ReadinessItem,
    User,
)
from app.rules import config as rules
from app.rules import legal_check
from app.services import boundaries as bsvc
from app.workflow import state_machine as sm
from app.workflow import timers

STATEMENT_EN = "Imagery shows physical change. It does not establish title or legality."

_LIST_SQL = """
SELECT al.id, al.code, al.state::text AS state, al.priority_score, al.due_at, al.escalation_level,
       al.reopened_count, al.is_demo, al.created_at, al.updated_at, al.owner_user_id, u.name AS owner_name,
       a.id AS asset_id, a.name AS asset_name, a.name_te AS asset_name_te, a.cohort::text AS cohort,
       a.type::text AS asset_type, c.id AS candidate_id, c.change_type::text AS change_type,
       c.stage_estimate::text AS stage_estimate, c.area_sq_m, c.first_changed_at, c.last_clear_at,
       c.sensor_basis::text AS sensor_basis, c.confidence, c.flags,
       lc.zone::text AS zone, lc.alert_class::text AS alert_class, lc.boundary_status::text AS checked_boundary_status,
       ST_X(ST_PointOnSurface(c.geom)) AS lon, ST_Y(ST_PointOnSurface(c.geom)) AS lat,
       ST_AsGeoJSON(c.geom)::json AS geometry
FROM alerts al
JOIN candidates c ON c.id = al.candidate_id
JOIN assets a ON a.id = c.asset_id
LEFT JOIN users u ON u.id = al.owner_user_id
LEFT JOIN LATERAL (SELECT * FROM legal_checks l WHERE l.candidate_id = c.id ORDER BY l.id DESC LIMIT 1) lc ON true
WHERE (CAST(:field_user AS bigint) IS NULL OR (
          al.owner_user_id = CAST(:field_user AS bigint)
          AND ((SELECT area_geom FROM users WHERE id = CAST(:field_user AS bigint)) IS NULL
               OR ST_Intersects(c.geom, (SELECT area_geom FROM users WHERE id = CAST(:field_user AS bigint))))))
  AND (CAST(:alert_id AS bigint) IS NULL OR al.id = CAST(:alert_id AS bigint))
ORDER BY al.priority_score DESC NULLS LAST, al.id
"""


def _field_user(user: User) -> int | None:
    return user.id if user.role == Role.field_officer.value else None


def _row_out(row: dict, now: dt.datetime) -> dict:
    out = dict(row)
    for k in ("priority_score", "area_sq_m", "confidence"):
        out[k] = float(out[k]) if out[k] is not None else None
    out["mode"] = rules.mode_for_cohort(row["cohort"]).value
    out["overdue"] = timers.is_overdue(row["state"], row["due_at"], now)
    out["area_acres"] = round(out["area_sq_m"] / 4046.86, 2) if out["area_sq_m"] else None
    return out


def list_alerts(db: Session, user: User, *, state=None, mode=None, cohort=None, overdue=None, now=None) -> list[dict]:
    now = as_utc(now)
    rows = db.execute(text(_LIST_SQL), {"field_user": _field_user(user), "alert_id": None}).mappings().all()
    out = [_row_out(dict(r), now) for r in rows]
    if state:
        wanted = set(state.split(","))
        out = [r for r in out if r["state"] in wanted]
    if mode:
        out = [r for r in out if r["mode"] in set(mode.split(","))]
    if cohort:
        out = [r for r in out if r["cohort"] in set(cohort.split(","))]
    if overdue is not None:
        out = [r for r in out if r["overdue"] == overdue]
    return out


def get_visible(db: Session, alert_id: int, user: User) -> Alert:
    row = db.execute(text(_LIST_SQL), {"field_user": _field_user(user), "alert_id": alert_id}).first()
    if row is None:
        raise HTTPException(404, "Alert not found")
    return db.get(Alert, alert_id)


def _iso(v):
    return v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v


def detail(db: Session, alert: Alert, user: User, now: dt.datetime | None = None) -> dict:
    now = as_utc(now)
    row = _row_out(dict(db.execute(text(_LIST_SQL), {"field_user": None, "alert_id": alert.id}).mappings().one()), now)
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

    pending = db.scalars(select(ClosureRequest).where(ClosureRequest.alert_id == alert.id, ClosureRequest.resolution.is_(None))).all()
    claims_visible = user.role in (Role.legal_officer.value, Role.nodal_officer.value)
    readiness = {r.item_key: r for r in db.scalars(select(ReadinessItem).where(ReadinessItem.alert_id == alert.id))}
    primary = bsvc.primary_of(bset)
    court_now = legal_check.live_court_case(db, cand.id)

    return {
        **row,
        "statement": STATEMENT_EN,
        "statement_key": "statement.imagery",
        "candidate": {
            "id": cand.id,
            "geometry": row["geometry"],
            "change_type": cand.change_type,
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
                {"id": o.id, "sensor": o.sensor, "scene_id": o.scene_id, "acquired_at": _iso(o.acquired_at), "cloud_pct": float(o.cloud_pct) if o.cloud_pct is not None else None, "licence_notice": o.licence_notice, "is_demo": o.is_demo}
                for o in observations
            ],
        },
        "asset": {
            "id": asset.id, "name": asset.name, "name_te": asset.name_te, "type": asset.type, "cohort": asset.cohort,
            "mode": rules.mode_for_cohort(asset.cohort).value, "baseline_date": _iso(asset.baseline_date),
            "survey_numbers": asset.survey_numbers, "is_demo": asset.is_demo, "area_acres": float(asset.area_acres) if asset.area_acres is not None else None,
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
            "mode": latest.mode, "alert_class": latest.alert_class, "result": latest.result, "flags": latest.flags,
            "matched_permit_id": latest.matched_permit_id, "matched_work_id": latest.matched_work_id,
            "matched_court_case_id": latest.matched_court_case_id, "rule_version": latest.rule_version,
            "checked_at": _iso(latest.checked_at), "live_court_matter_now": court_now,
            "permit_conflict": "permit_conflict" in (latest.flags or []),
        },
        "timeline": [
            {"id": t["id"], "action": t["action"], "at": _iso(t["at"]), "actor": users[t["actor_id"]].name if t["actor_id"] in users else "System",
             "actor_role": users[t["actor_id"]].role if t["actor_id"] in users else "system", "details": t["details"]}
            for t in timeline
        ],
        "pending_closures": [
            {"id": p.id, "to": p.to_state, "requested_by": users[p.requested_by].name, "requested_by_id": p.requested_by, "reason": p.reason, "reason_code": p.reason_code, "requested_at": _iso(p.requested_at)}
            for p in pending
        ],
        "allowed_actions": sm.allowed_actions(db, alert, user, now),
        "field_checks": [
            {"id": f.id, "officer": users[f.officer_id].name, "observed_at": _iso(f.observed_at), "lat": f.lat, "lon": f.lon,
             "gps_accuracy_m": float(f.gps_accuracy_m) if f.gps_accuracy_m is not None else None,
             "distance_to_candidate_m": float(f.distance_to_candidate_m) if f.distance_to_candidate_m is not None else None,
             "outcome": f.outcome, "observed_stage": f.observed_stage, "notes": f.notes, "photo_count": len(f.photo_paths),
             "photo_sha256": f.photo_sha256, "device_time": _iso(f.device_time), "synced_at": _iso(f.synced_at)}
            for f in db.scalars(select(FieldCheck).where(FieldCheck.alert_id == alert.id).order_by(FieldCheck.id))
        ],
        "owner_claims": [
            {"id": c.id, "claim_type": c.claim_type, "claimant_name": c.claimant_name if claims_visible else None, "document_ref": c.document_ref if claims_visible else None, "entered_at": _iso(c.entered_at)}
            for c in db.scalars(select(OwnerClaim).where(OwnerClaim.alert_id == alert.id))
        ],
        "readiness": [
            {"item_key": k, "status": readiness[k].status if k in readiness else None,
             "evidence_ref": readiness[k].evidence_ref if k in readiness else None,
             "checked_by": users[readiness[k].checked_by].name if k in readiness else None,
             "checked_at": _iso(readiness[k].checked_at) if k in readiness else None,
             "system_hint": _hint(k, primary, court_now, cand)}
            for k in sm.READINESS_KEYS
        ],
        "evidence_packs": [
            {"id": p.id, "version": p.version, "generated_at": _iso(p.generated_at), "manifest_sha256": p.manifest_sha256, "counsel_reviewed": p.counsel_reviewed}
            for p in db.scalars(select(EvidencePack).where(EvidencePack.alert_id == alert.id).order_by(EvidencePack.version))
        ],
        "officer_records": [
            {"id": r.id, "officer": users[r.officer_id].name, "notice_ref": r.notice_ref, "notice_date": _iso(r.notice_date),
             "hearing_date": _iso(r.hearing_date), "order_ref": r.order_ref, "order_date": _iso(r.order_date),
             "action_date": _iso(r.action_date), "action_summary": r.action_summary, "created_at": _iso(r.created_at)}
            for r in db.scalars(select(OfficerRecord).where(OfficerRecord.alert_id == alert.id).order_by(OfficerRecord.id))
        ],
        "imagery_requests": [
            {"id": r.id, "provider": r.provider, "area_sq_km": float(r.area_sq_km), "est_cost_usd": float(r.est_cost_usd) if r.est_cost_usd is not None else None, "status": r.status}
            for r in db.scalars(select(ImageryRequest).where(ImageryRequest.alert_id == alert.id))
        ],
        "policy_cutoff_date": rules.policy_cutoff_date().isoformat(),
    }


def _hint(key: str, primary: dict | None, court_case: int | None, cand: Candidate) -> str | None:
    """Facts the system already holds for a checklist item. Officers still record each item."""
    if key == "boundary_confirmed" and primary:
        return f"Boundary status: {primary['status']} (version {primary['version']})"
    if key == "no_live_court_matter":
        return f"Court register: live matter {court_case}" if court_case else "Court register: no live matter found"
    if key == "construction_dated":
        return f"Last clear {cand.last_clear_at or 'unknown'}, first changed {cand.first_changed_at}; policy cut-off {rules.policy_cutoff_date()}"
    return None
