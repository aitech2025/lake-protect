"""Records import from CSV (section 9.5 POST /records/{permits|works|court-cases}/import).

Live government integrations are out of scope (section 3), so records arrive as CSV with a WKT
geometry column. A court register import immediately puts matching open alerts on legal hold.
"""
from __future__ import annotations

import csv
import datetime as dt
import io

from geoalchemy2.elements import WKTElement
from shapely import wkt as shapely_wkt
from shapely.geometry import MultiPolygon
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, AuthorisedWork, CourtCase, Permit

KINDS = {"permits", "works", "court-cases"}
REQUIRED = {
    "permits": ["source", "ref", "kind", "valid_from", "wkt"],
    "works": ["agency", "description", "ref", "starts_on", "wkt"],
    "court-cases": ["court", "case_no", "status"],
}


class ImportError_(ValueError):
    pass


def _date(value: str | None) -> dt.date | None:
    value = (value or "").strip()
    return dt.date.fromisoformat(value) if value else None


def _geom(value: str | None, required: bool) -> WKTElement | None:
    value = (value or "").strip()
    if not value:
        if required:
            raise ImportError_("wkt is required")
        return None
    g = shapely_wkt.loads(value)
    if g.geom_type == "Polygon":
        g = MultiPolygon([g])
    if g.geom_type != "MultiPolygon" or not g.is_valid:
        raise ImportError_(f"wkt must be a valid Polygon or MultiPolygon, got {g.geom_type}")
    return WKTElement(g.wkt, srid=4326)


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes"}


def parse_and_insert(db: Session, kind: str, content: bytes) -> list[int]:
    if kind not in KINDS:
        raise ImportError_(f"Unknown record kind {kind}")
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    missing = [c for c in REQUIRED[kind] if c not in (reader.fieldnames or [])]
    if missing:
        raise ImportError_(f"Missing columns: {', '.join(missing)}")
    ids = []
    for n, row in enumerate(reader, start=2):
        try:
            if kind == "permits":
                rec = Permit(source=row["source"], ref=row["ref"], kind=row["kind"], valid_from=_date(row["valid_from"]),
                             valid_to=_date(row.get("valid_to")), geom=_geom(row["wkt"], True), is_demo=_bool(row.get("is_demo")))
            elif kind == "works":
                rec = AuthorisedWork(agency=row["agency"], description=row["description"], ref=row["ref"],
                                     starts_on=_date(row["starts_on"]), ends_on=_date(row.get("ends_on")),
                                     geom=_geom(row["wkt"], True), is_demo=_bool(row.get("is_demo")))
            else:
                asset_id = None
                if (row.get("asset_key") or "").strip():
                    asset_id = db.scalar(select(Asset.id).where(Asset.asset_key == row["asset_key"].strip()))
                    if asset_id is None:
                        raise ImportError_(f"unknown asset_key {row['asset_key']}")
                geom = _geom(row.get("wkt"), False)
                surveys = [s.strip() for s in (row.get("survey_numbers") or "").split(";") if s.strip()]
                if asset_id is None and geom is None and not surveys:
                    raise ImportError_("a court case needs an asset_key, a wkt footprint or survey numbers")
                rec = CourtCase(court=row["court"], case_no=row["case_no"], status=row["status"].strip(), asset_id=asset_id,
                                survey_numbers=surveys, geom=geom, next_hearing=_date(row.get("next_hearing")),
                                last_checked_at=dt.datetime.now(dt.timezone.utc), is_demo=_bool(row.get("is_demo")))
        except (ValueError, KeyError) as exc:
            raise ImportError_(f"Row {n}: {exc}") from exc
        db.add(rec)
        db.flush()
        ids.append(rec.id)
    return ids
