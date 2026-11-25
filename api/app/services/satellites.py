"""Satellite image sources, maintained by the admin (DECISIONS.md D-066).

Each source has one purpose:
- **screen_optical:** what the weekly screen and citizens' satellite looks read (Sentinel-2 today).
  Exactly one is on: the screen cannot run without it.
- **screen_radar:** the radar check for built-up (Sentinel-1 today). At most one is on. With none,
  the screen runs without radar, and built-up changes carry the flag `built_without_radar`.
- **sharper:** sharper paid images an official may ask for. Any number may be on. The price per
  sq km and the smallest order make the estimate; nothing is ordered in the prototype.

**Rules:**
- **Turning a screening source on** turns off the one it replaces.
- **Deleting:** any source may be deleted except the optical source the screen is using. Requests
  made through a deleted source keep its key.
- **The key never changes:** requests and runs record it.
- **The log:** every change goes to the audit log with the values before and after.

The detection thresholds are not here: they stay in the versioned rule file, so a scored backtest
cannot be changed from a screen. The pipeline records the source settings it used in the run's
rules hash.
"""
from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.models import SatelliteSource, User

PURPOSES = ("screen_optical", "screen_radar", "sharper")
FIELDS = ("name", "provider", "purpose", "resolution_m", "revisit_days", "stac_url", "collection", "max_scene_cloud_pct",
          "price_usd_per_sq_km", "min_order_sq_km", "licence_notice", "notes", "active")
KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,40}$")


class Refused(ValueError):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


def _num(v):
    return float(v) if isinstance(v, Decimal) else v


def as_dict(s: SatelliteSource, users: dict[int, str] | None = None) -> dict:
    users = users or {}
    return {
        "id": s.id, "key": s.key, **{f: _num(getattr(s, f)) for f in FIELDS},
        "added_at": s.added_at.isoformat() if s.added_at else None, "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        "added_by": users.get(s.added_by), "updated_by": users.get(s.updated_by),
    }


def user_names(db: Session) -> dict[int, str]:
    return dict(db.execute(text("SELECT id, name FROM users")).all())


def list_all(db: Session, purpose: str | None = None, active: bool | None = None) -> list[dict]:
    q = select(SatelliteSource)
    if purpose:
        q = q.where(SatelliteSource.purpose == purpose)
    if active is not None:
        q = q.where(SatelliteSource.active.is_(active))
    order = {p: i for i, p in enumerate(PURPOSES)}
    rows = sorted(db.scalars(q), key=lambda s: (order[s.purpose], not s.active, s.name.lower()))
    names = user_names(db)
    return [as_dict(s, names) for s in rows]


def _clean(values: dict, purpose: str) -> dict:
    """Check one source's values for its purpose; return them tidied."""
    v = {k: (x.strip() if isinstance(x, str) else x) for k, x in values.items()}
    for k in ("stac_url", "collection", "licence_notice", "notes", "revisit_days", "max_scene_cloud_pct", "price_usd_per_sq_km", "min_order_sq_km"):
        if v.get(k) == "":
            v[k] = None
    if not (2 <= len(v.get("name") or "") <= 120):
        raise Refused("Give the source a name (2 to 120 characters)")
    if not (2 <= len(v.get("provider") or "") <= 200):
        raise Refused("Say who provides it (2 to 200 characters)")
    res = v.get("resolution_m")
    if res is None or not (0 < float(res) <= 1000):
        raise Refused("Resolution is the ground size of one pixel, in metres: more than 0, at most 1,000")
    if v.get("revisit_days") is not None and not (0 < float(v["revisit_days"]) <= 365):
        raise Refused("Revisit is in days: more than 0, at most 365")
    if purpose == "sharper":
        for k in ("stac_url", "collection", "max_scene_cloud_pct"):
            v[k] = None
        for k, what in (("price_usd_per_sq_km", "The price"), ("min_order_sq_km", "The smallest order")):
            if v.get(k) is not None and float(v[k]) < 0:
                raise Refused(f"{what} cannot be negative")
    else:
        v["price_usd_per_sq_km"] = v["min_order_sq_km"] = None
        if not re.match(r"^https://[^\s]+$", v.get("stac_url") or ""):
            raise Refused("A screening source needs its catalogue address (STAC), starting https://")
        if not re.match(r"^[A-Za-z0-9._:-]{2,100}$", v.get("collection") or ""):
            raise Refused("A screening source needs its catalogue collection, such as sentinel-2-c1-l2a")
        if purpose == "screen_optical":
            cloud = v.get("max_scene_cloud_pct")
            if cloud is None or not (0 <= float(cloud) <= 100):
                raise Refused("An optical source needs the scene cloud limit, 0 to 100 per cent")
        else:
            v["max_scene_cloud_pct"] = None
    if v.get("licence_notice") and len(v["licence_notice"]) > 300:
        raise Refused("Keep the licence line under 300 characters")
    if v.get("notes") and len(v["notes"]) > 1000:
        raise Refused("Keep the notes under 1,000 characters")
    return v


def _switch_off_others(db: Session, s: SatelliteSource, user: User, at: dt.datetime) -> list[str]:
    """One screening source is on per purpose: turning this one on turns off the one it replaces."""
    if s.purpose == "sharper":
        return []
    off = []
    for other in db.scalars(select(SatelliteSource).where(SatelliteSource.purpose == s.purpose, SatelliteSource.active.is_(True),
                                                          SatelliteSource.id != (s.id or 0))):
        other.active, other.updated_by, other.updated_at = False, user.id, at
        chain.record(db, actor_id=user.id, action="satellite_source.switched_off", entity="satellite_source", entity_id=other.id, at=at,
                     details={"key": other.key, "replaced_by": s.key})
        off.append(other.name)
    db.flush()
    return off


def _keeps_an_optical_source(db: Session, s: SatelliteSource) -> None:
    if s.purpose == "screen_optical" and s.active:
        raise Refused(f"The weekly screen reads {s.name}. Turn another optical source on first; this one then turns off.", 409)


def create(db: Session, user: User, values: dict, at: dt.datetime) -> tuple[SatelliteSource, list[str]]:
    key = (values.get("key") or "").strip().lower()
    if not KEY_RE.match(key):
        raise Refused("The key is 3 to 41 lower-case letters, digits, - or _, starting with a letter or digit")
    if db.scalar(select(SatelliteSource.id).where(SatelliteSource.key == key)):
        raise Refused(f"A source with the key {key} exists already", 409)
    purpose = values.get("purpose")
    if purpose not in PURPOSES:
        raise Refused("The purpose is screen_optical, screen_radar or sharper")
    v = _clean({f: values.get(f) for f in FIELDS}, purpose)
    v["active"] = bool(values.get("active", True))
    s = SatelliteSource(key=key, **v, added_by=user.id, added_at=at, updated_by=user.id, updated_at=at)
    off = _switch_off_others(db, s, user, at) if s.active else []
    db.add(s)
    db.flush()
    chain.record(db, actor_id=user.id, action="satellite_source.added", entity="satellite_source", entity_id=s.id, at=at,
                 details={"after": as_dict(s)})
    return s, off


def update(db: Session, user: User, s: SatelliteSource, values: dict, at: dt.datetime) -> tuple[SatelliteSource, list[str]]:
    if "key" in values and values["key"] != s.key:
        raise Refused("The key cannot change: requests and runs record it. Add a new source instead")
    if "purpose" in values and values["purpose"] != s.purpose:
        raise Refused("The purpose cannot change. Add a new source for the other purpose")
    before = as_dict(s)
    merged = {f: values.get(f, getattr(s, f)) for f in FIELDS}
    v = _clean(merged, s.purpose)
    turning_off = s.active and not bool(v["active"])
    if turning_off:
        _keeps_an_optical_source(db, s)
    turning_on = bool(v["active"]) and not s.active
    off = _switch_off_others(db, s, user, at) if turning_on else []  # first, so one stays on per purpose
    for f in FIELDS:
        if f != "purpose":
            setattr(s, f, v[f])
    s.active = bool(v["active"])
    s.updated_by, s.updated_at = user.id, at
    db.flush()
    after = as_dict(s)
    changed = sorted(k for k in FIELDS if before.get(k) != after.get(k))
    if changed:
        chain.record(db, actor_id=user.id, action="satellite_source.changed", entity="satellite_source", entity_id=s.id, at=at,
                     details={"changed": changed, "before": {k: before[k] for k in changed}, "after": {k: after[k] for k in changed}})
    return s, off


def delete(db: Session, user: User, s: SatelliteSource, reason: str, at: dt.datetime) -> None:
    reason = (reason or "").strip()
    if len(reason) < 5:
        raise Refused("Say why it is deleted (at least 5 characters)")
    _keeps_an_optical_source(db, s)
    record = as_dict(s)
    chain.record(db, actor_id=user.id, action="satellite_source.deleted", entity="satellite_source", entity_id=s.id, at=at,
                 details={"reason": reason, "before": record})
    db.delete(s)
    db.flush()


def history(db: Session, limit: int = 50) -> list[dict]:
    rows = db.execute(text(
        """
        SELECT l.id, l.action, l.entity_id, l.details, l.at, coalesce(u.name, 'System') AS actor, s.name AS source_name
        FROM audit_log l LEFT JOIN users u ON u.id = l.actor_id LEFT JOIN satellite_sources s ON s.id::text = l.entity_id
        WHERE l.entity = 'satellite_source' ORDER BY l.id DESC LIMIT :n
        """), {"n": limit}).mappings().all()
    return [{**dict(r), "at": r["at"].isoformat()} for r in rows]


# For the rest of the app -------------------------------------------------------------------------
def sharper_source(db: Session, key: str | None) -> SatelliteSource:
    """The sharper-image source a request names, or the first one on."""
    q = select(SatelliteSource).where(SatelliteSource.purpose == "sharper", SatelliteSource.active.is_(True))
    s = db.scalar(q.where(SatelliteSource.key == key)) if key else db.scalar(q.order_by(SatelliteSource.id).limit(1))
    if s is None:
        raise Refused(f"No sharper-image source {key!r} is on" if key else "No sharper-image source is on: the admin adds one on Satellites")
    return s


def names_by_key(db: Session) -> dict[str, str]:
    return dict(db.execute(text("SELECT key, name FROM satellite_sources")).all())


def for_pipeline(db: Session) -> dict:
    """What the weekly screen and the reviewer read: the screening sources that are on."""
    out = {}
    for purpose in ("screen_optical", "screen_radar"):
        s = db.scalar(select(SatelliteSource).where(SatelliteSource.purpose == purpose, SatelliteSource.active.is_(True)))
        out[purpose] = None if s is None else {k: _num(getattr(s, k)) for k in
                                               ("key", "name", "stac_url", "collection", "max_scene_cloud_pct", "licence_notice", "resolution_m")}
    return out
