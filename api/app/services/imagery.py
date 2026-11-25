"""Requests for a sharper image of an incident (CONTEXT.md section 8.1). Nothing is ordered in the prototype.

The estimate covers a box 250 m around the change, at the price per sq km the admin keeps for the
source on Satellites (D-066), and at least its smallest order. An
official's request waits for the admin's approval; the admin's own request is approved as made
(D-064). Citizens who reported the place are told sharper images were asked for (D-063).
"""
from __future__ import annotations

import datetime as dt
import math

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit import chain
from app.models import Alert, ImageryRequest, User

def estimate(area_sq_km: float, rate: float | None, min_order: float | None) -> float | None:
    """A planning estimate, not a quote: the area rounded up to 0.01 sq km, at least the smallest order."""
    if rate is None:
        return None
    billed = max(math.ceil(area_sq_km * 100) / 100, min_order or 0)
    return round(billed * rate, 2)


def request(db: Session, alert: Alert, user: User, provider: str | None, note: str | None, at: dt.datetime) -> ImageryRequest:
    from app.enums import Role
    from app.services import satellites

    source = satellites.sharper_source(db, provider)  # refuses a source that is off or unknown
    provider = source.key
    by_admin = user.role == Role.admin.value
    area = db.scalar(
        text("SELECT ST_Area(ST_Transform(ST_Envelope(ST_Buffer(geom::geography, 250)::geometry), 32644)) / 1e6 FROM candidates WHERE id = :c"),
        {"c": alert.candidate_id},
    )
    rate = float(source.price_usd_per_sq_km) if source.price_usd_per_sq_km is not None else None
    req = ImageryRequest(alert_id=alert.id, provider=provider, area_sq_km=round(area, 3),
                         est_cost_usd=estimate(area, rate, float(source.min_order_sq_km) if source.min_order_sq_km is not None else None),
                         status="approved" if by_admin else "requested", requested_by=user.id, created_at=at,
                         note=(note or "").strip() or None, decided_by=user.id if by_admin else None,
                         decided_at=at if by_admin else None, approved_by=user.id if by_admin else None)
    db.add(req)
    db.flush()
    chain.record(db, actor_id=user.id, action="imagery.requested", entity="alert", entity_id=alert.id, at=at,
                 details={"imagery_request_id": req.id, "provider": provider, "area_sq_km": float(req.area_sq_km),
                          "est_cost_usd": req.est_cost_usd and float(req.est_cost_usd), "note": note})
    from app.citizen import service as citizen

    citizen.on_imagery_requested(db, alert, at)
    return req
