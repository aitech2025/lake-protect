"""The weekly record of every asset (DECISIONS.md D-057).

Each weekly screen leaves one row per asset in `asset_screens`: the ISO week, whether the asset was
seen clearly, the image of that week with the boundary drawn on it, and what changed. A change is
linked to the incident it opened, or to the open incident it continues. The record never says
"no encroachment": it says "no change seen" only when there was a clear look.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Alert, Asset, AssetScreen, Candidate
from app.services.alert_view import CHANGE_LABEL
from app.storage import store

STATUS_LABEL = {
    "no_candidate": "No change seen",
    "candidate_found": "Change found",
    "no_usable_look": "No clear look this week",
    "not_observed": "Not observed",
    "failed": "Screen failed",
}

# Keep the active imagery thread to the most recent two months. Older weekly artifacts remain
# addressable through their stored object key, but live in the archive namespace on the same durable
# object store until a remote cold-storage backend is configured.
ACTIVE_IMAGE_DAYS = 60


def iso_week(day: dt.date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def store_image(asset: Asset, as_of: dt.date, png_b64: str | None) -> str | None:
    if not png_b64:
        return None
    data = base64.b64decode(png_b64)
    if not data.startswith(b"\x89PNG"):
        raise ValueError("A weekly image must be a PNG")
    digest = hashlib.sha256(data).hexdigest()[:16]
    cutoff = dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=ACTIVE_IMAGE_DAYS)
    namespace = "weeks" if as_of >= cutoff else "archive/weeks"
    return store.put_object(f"{namespace}/{asset.asset_key}/{as_of.isoformat()}_{digest}.png", data)


def change_entries(db: Session, asset_id: int, items: list[dict]) -> list[dict]:
    """Keep only changes that are candidates of this asset, with the fields the record needs."""
    out = []
    for item in items:
        cand = db.get(Candidate, int(item["candidate_id"])) if item.get("candidate_id") else None
        if cand is None or cand.asset_id != asset_id:
            raise ValueError(f"Change {item.get('candidate_id')} is not a candidate of asset {asset_id}")
        alert_id = item.get("alert_id") or db.scalar(select(Alert.id).where(Alert.candidate_id == cand.id))
        out.append({
            "candidate_id": cand.id,
            "alert_id": alert_id,
            "change_type": cand.change_type,
            "area_sq_m": float(cand.area_sq_m),
            "first_changed_at": cand.first_changed_at.isoformat(),
            "outcome": item.get("outcome"),
        })
    return out


def changes_since(db: Session, asset_id: int, since: dt.datetime) -> list[dict]:
    """Changes ingested for an asset since a run started, when the screen did not list them."""
    rows = db.execute(text(
        "SELECT id FROM candidates WHERE asset_id = :a AND created_at >= :s ORDER BY id"), {"a": asset_id, "s": since}).scalars().all()
    return change_entries(db, asset_id, [{"candidate_id": r} for r in rows])


_WEEKS_SQL = text(
    """
    WITH ranked AS (
        SELECT s.id AS screen_id, s.run_id, r.as_of, coalesce(s.week, to_char(r.as_of, 'IYYY-"W"IW')) AS week,
               s.status, s.looks, s.first_look, s.last_look, s.candidates, s.legacy_changes,
               s.image_key IS NOT NULL AS has_image, s.image_date, s.image_scene_id, s.changes, r.rule_version,
               row_number() OVER (
                   PARTITION BY coalesce(s.week, to_char(r.as_of, 'IYYY-"W"IW'))
                   ORDER BY r.as_of DESC, s.id DESC
               ) AS week_rank
        FROM asset_screens s JOIN screen_runs r ON r.id = s.run_id
        WHERE s.asset_id = :a
    )
    SELECT screen_id, run_id, as_of, week, status, looks, first_look, last_look, candidates, legacy_changes,
           has_image, image_date, image_scene_id, changes, rule_version
    FROM ranked
    WHERE week_rank = 1
    ORDER BY as_of DESC, screen_id DESC
    LIMIT :n
    """
)


def weeks_for_asset(db: Session, asset_id: int, limit: int = 26) -> list[dict]:
    rows = db.execute(_WEEKS_SQL, {"a": asset_id, "n": limit}).mappings().all()
    alert_ids = {c["alert_id"] for r in rows for c in (r["changes"] or []) if c.get("alert_id")}
    alerts = {a.id: a for a in db.scalars(select(Alert).where(Alert.id.in_(alert_ids or {0})))}
    out = []
    for r in rows:
        changes = []
        for c in r["changes"] or []:
            a = alerts.get(c.get("alert_id"))
            changes.append({
                **c,
                "change_label": CHANGE_LABEL.get(c["change_type"], c["change_type"]),
                "alert_code": a.code if a else None,
                "alert_state": a.state if a else None,
                "alert_resolution": a.resolution if a else None,
                "continues": c.get("outcome") == "recorded_on_open_incident",
            })
        out.append({
            **{k: (v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v) for k, v in r.items() if k != "changes"},
            "status_label": STATUS_LABEL.get(r["status"], r["status"]),
            "changed": bool(changes),
            "changes": changes,
        })
    return out


def image_key(db: Session, asset_id: int, screen_id: int) -> str | None:
    row = db.get(AssetScreen, screen_id)
    if row is None or row.asset_id != asset_id:
        return None
    return row.image_key
