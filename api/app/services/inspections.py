"""Field inspections: a visit to a location, its GPS position and its photos (migration 0018).

Photos lose their location and camera details before they are kept (app.citizen.service.clean_photo)
and each is stored with its SHA-256. Rows are append-only. A field officer's report on an incident
(D-067) records its visit through here too.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import chain
from app.models import Alert, Asset, AssetInspection, Candidate, User
from app.storage import store

OUTCOMES = ("confirmed", "false_alarm", "cannot_access")
MAX_PHOTOS = 5
MAX_PHOTO_BYTES = 8 * 1024 * 1024


class InspectionRefused(Exception):
    pass


def record(db: Session, asset: Asset, user: User, *, outcome: str, notes: str, observed_at: dt.datetime,
           lat: float | None, lon: float | None, photos: list[bytes], alert_id: int | None) -> AssetInspection:
    from app.citizen.service import clean_photo

    notes = (notes or "").strip()
    if outcome not in OUTCOMES:
        raise InspectionRefused(f"The outcome is one of: {', '.join(OUTCOMES)}")
    if len(notes) < 3:
        raise InspectionRefused("Inspection notes are required")
    if (lat is None) != (lon is None):
        raise InspectionRefused("Give both GPS coordinates, or neither")
    if len(photos) > MAX_PHOTOS:
        raise InspectionRefused(f"At most {MAX_PHOTOS} inspection photos are allowed")
    if alert_id is not None and db.scalar(select(Alert.id).join(Candidate, Candidate.id == Alert.candidate_id)
                                         .where(Alert.id == alert_id, Candidate.asset_id == asset.id)) is None:
        raise InspectionRefused("The incident does not belong to this asset")
    keys: list[str] = []
    hashes: list[str] = []
    folder = uuid.uuid4().hex
    for n, raw in enumerate(photos, 1):
        if len(raw) > MAX_PHOTO_BYTES:
            raise InspectionRefused("Each photo must be under 8 MB")
        try:
            clean, _, _ = clean_photo(raw)
        except Exception as exc:
            raise InspectionRefused(str(exc)) from exc
        key = f"field-inspections/{asset.id}/{folder}/{n}.jpg"
        store.put_object(key, clean)
        keys.append(key)
        hashes.append(hashlib.sha256(clean).hexdigest())
    row = AssetInspection(asset_id=asset.id, alert_id=alert_id, inspector_id=user.id, observed_at=observed_at, lat=lat, lon=lon,
                          outcome=outcome, notes=notes, photo_paths=keys, photo_sha256=hashes)
    db.add(row)
    db.flush()
    chain.record(db, actor_id=user.id, action="asset.inspection_recorded", entity="asset", entity_id=asset.id,
                 details={"inspection_id": row.id, "alert_id": alert_id, "outcome": outcome,
                          "observed_at": observed_at.isoformat(), "photos": len(keys)})
    return row
