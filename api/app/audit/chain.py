"""Append-only audit log with a hash chain (CONTEXT.md section 7).

hash = sha256(prev_hash + canonical row). The chain is verified by recomputing every hash in
id order, so editing, deleting or reordering any row breaks verification.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import AuditLog

GENESIS = "0" * 64
_LOCK_KEY = 7_447_001  # serialises chain appends across connections


def _canonical(actor_id: int | None, action: str, entity: str, entity_id: str | None, details: dict, at: dt.datetime) -> str:
    return json.dumps(
        {
            "actor_id": actor_id,
            "action": action,
            "entity": entity,
            "entity_id": entity_id,
            "details": details,
            "at": at.astimezone(dt.timezone.utc).isoformat(timespec="microseconds"),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _digest(prev_hash: str, canonical: str) -> str:
    return hashlib.sha256((prev_hash + canonical).encode("utf-8")).hexdigest()


def _normalise(details: dict | None) -> dict:
    # Round-trip through JSON so the hashed form equals what JSONB gives back.
    return json.loads(json.dumps(details or {}, default=str, ensure_ascii=False))


def record(
    db: Session,
    *,
    actor_id: int | None,
    action: str,
    entity: str,
    entity_id: Any = None,
    details: dict | None = None,
    at: dt.datetime | None = None,
) -> AuditLog:
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _LOCK_KEY})
    prev = db.execute(select(AuditLog.hash).order_by(AuditLog.id.desc()).limit(1)).scalar() or GENESIS
    at = (at or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    eid = None if entity_id is None else str(entity_id)
    details = _normalise(details)
    row = AuditLog(
        actor_id=actor_id,
        action=action,
        entity=entity,
        entity_id=eid,
        details=details,
        at=at,
        prev_hash=prev,
        hash=_digest(prev, _canonical(actor_id, action, entity, eid, details, at)),
    )
    db.add(row)
    db.flush()
    return row


def verify(db: Session) -> dict:
    """Recompute the whole chain. Returns ok, rows checked, and the first broken row if any."""
    prev = GENESIS
    count = 0
    for row in db.execute(select(AuditLog).order_by(AuditLog.id)).scalars():
        count += 1
        if row.prev_hash != prev:
            return {"ok": False, "rows_checked": count, "first_bad_id": row.id, "problem": "prev_hash does not link"}
        expected = _digest(prev, _canonical(row.actor_id, row.action, row.entity, row.entity_id, row.details, row.at))
        if row.hash != expected:
            return {"ok": False, "rows_checked": count, "first_bad_id": row.id, "problem": "row content does not match its hash"}
        prev = row.hash
    return {"ok": True, "rows_checked": count, "first_bad_id": None, "problem": None, "head": prev}
