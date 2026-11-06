"""Field check intake (section 9.2, 9.5 POST /alerts/{id}/field-checks).

Idempotent by client_uuid, so an offline queue can resend safely. Photos are hashed on arrival;
when the device sent its own hashes they must match. The server keeps both device time and
server time, and computes the distance to the candidate itself.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import uuid

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.clock import as_utc
from app.enums import AlertState, FieldOutcome, Stage
from app.models import Alert, FieldCheck, User
from app.rules import config as rules
from app.storage import store
from app.workflow import state_machine as sm


class FieldCheckMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_uuid: uuid.UUID
    observed_at: dt.datetime
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    gps_accuracy_m: float | None = None
    outcome: FieldOutcome
    observed_stage: Stage | None = None
    notes: str | None = None
    reason: str | None = None
    device_time: dt.datetime | None = None
    photo_sha256: list[str] = []


class FieldRefused(Exception):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.message = message
        self.status = status


def submit(db: Session, alert: Alert, officer: User, meta: FieldCheckMeta, photos: list[bytes], at: dt.datetime | None = None) -> dict:
    at = as_utc(at)
    existing = db.scalar(select(FieldCheck).where(FieldCheck.client_uuid == meta.client_uuid))
    if existing is not None:
        if existing.alert_id != alert.id:
            raise FieldRefused("This capture was already synced for another alert", 409)
        return {"field_check_id": existing.id, "duplicate": True, "state": alert.state}
    if alert.owner_user_id != officer.id:
        raise FieldRefused("Only the field officer this alert is assigned to can submit a check", 403)
    if meta.photo_sha256 and len(meta.photo_sha256) != len(photos):
        raise FieldRefused("Photo count does not match the device's photo hashes")

    paths, hashes = [], []
    for i, data in enumerate(photos):
        digest = hashlib.sha256(data).hexdigest()
        if meta.photo_sha256 and meta.photo_sha256[i].lower() != digest:
            raise FieldRefused(f"Photo {i + 1} changed in transit: its hash does not match the device's")
        ext = "png" if data.startswith(b"\x89PNG") else "jpg"
        paths.append(store.put_object(f"field/{alert.id}/{meta.client_uuid}/{i + 1}.{ext}", data))
        hashes.append(digest)

    distance = None
    if meta.lat is not None and meta.lon is not None:
        distance = db.scalar(
            text("SELECT ST_Distance(c.geom::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) FROM candidates c WHERE c.id = :c"),
            {"lon": meta.lon, "lat": meta.lat, "c": alert.candidate_id},
        )
    fc = FieldCheck(
        alert_id=alert.id,
        officer_id=officer.id,
        client_uuid=meta.client_uuid,
        observed_at=meta.observed_at,
        lat=meta.lat,
        lon=meta.lon,
        gps_accuracy_m=meta.gps_accuracy_m,
        distance_to_candidate_m=round(distance, 2) if distance is not None else None,
        outcome=meta.outcome.value,
        observed_stage=meta.observed_stage.value if meta.observed_stage else None,
        notes=meta.notes,
        photo_paths=paths,
        photo_sha256=hashes,
        device_time=meta.device_time,
        synced_at=at,
    )
    db.add(fc)
    db.flush()
    warn_m = rules.rules()["field_distance_warning_m"]
    chain.record(
        db,
        actor_id=officer.id,
        action="field_check.synced",
        entity="alert",
        entity_id=alert.id,
        details={"field_check_id": fc.id, "outcome": fc.outcome, "photos": len(paths), "distance_m": fc.distance_to_candidate_m and float(fc.distance_to_candidate_m), "device_time": meta.device_time, "synced_at": at},
        at=at,
    )

    result = {"field_check_id": fc.id, "duplicate": False, "distance_m": float(fc.distance_to_candidate_m) if distance is not None else None,
              "distance_warning": distance is not None and distance > warn_m, "warning_threshold_m": warn_m}
    if alert.state != AlertState.ASSIGNED.value:
        result.update(state=alert.state, note="Stored as a record. The alert had already moved on, so no step was taken.")
        return result
    target = {
        FieldOutcome.confirmed: AlertState.FIELD_CONFIRMED,
        FieldOutcome.cannot_access: AlertState.ASSIGNED,
        FieldOutcome.false_alarm: AlertState.CLOSED_FALSE_ALARM,
    }[meta.outcome]
    # The capture is evidence and is kept even if the step it asks for is refused.
    try:
        with db.begin_nested():
            step = sm.transition(db, alert, target.value, actor=officer, reason=meta.reason or meta.notes, data={"field_check_id": fc.id}, at=at)
        result.update(state=alert.state, transition=step)
    except sm.Refused as exc:
        db.refresh(alert)
        result.update(state=alert.state, step_refused=exc.message)
    return result
