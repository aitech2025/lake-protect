"""Requests for a sharper image of an incident (CONTEXT.md section 8.1). Recorded only: nothing is ordered.

The estimate covers a box 250 m around the change, at the reseller guide's upper prices. Citizens
who reported the place are told sharper images were asked for (DECISIONS.md D-063).
"""
from __future__ import annotations

import datetime as dt
import math

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit import chain
from app.models import Alert, ImageryRequest, User

# Reseller guide figures from CONTEXT.md section 8.1, upper end. Planning estimates, not quotes.
USD_PER_SQ_KM = {"isro_nrsc": None, "commercial_archive": 26.0, "commercial_tasking": 55.0}


def request(db: Session, alert: Alert, user: User, provider: str, note: str | None, at: dt.datetime) -> ImageryRequest:
    area = db.scalar(
        text("SELECT ST_Area(ST_Transform(ST_Envelope(ST_Buffer(geom::geography, 250)::geometry), 32644)) / 1e6 FROM candidates WHERE id = :c"),
        {"c": alert.candidate_id},
    )
    rate = USD_PER_SQ_KM[provider]
    req = ImageryRequest(alert_id=alert.id, provider=provider, area_sq_km=round(area, 3),
                         est_cost_usd=None if rate is None else round(math.ceil(area * 100) / 100 * rate, 2),
                         status="recorded", requested_by=user.id, created_at=at)
    db.add(req)
    db.flush()
    chain.record(db, actor_id=user.id, action="imagery.requested", entity="alert", entity_id=alert.id, at=at,
                 details={"imagery_request_id": req.id, "provider": provider, "area_sq_km": float(req.area_sq_km),
                          "est_cost_usd": req.est_cost_usd and float(req.est_cost_usd), "note": note})
    from app.citizen import service as citizen

    citizen.on_imagery_requested(db, alert, at)
    return req
