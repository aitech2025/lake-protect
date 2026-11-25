"""Where a citizen's report is (DECISIONS.md D-063).

For a point: the watched location and zone that hold it, the district and mandal, and the survey
numbers under it when land records are loaded. Districts and mandals come from the location, or,
outside every location, from OpenStreetMap's boundaries (`data/areas/admin_orr.geojson`, made by
`lp assets-areas`): not the revenue record, and the incident says so.

For words only (a WhatsApp landmark, a caller's description): if they name exactly one watched
location, the report is placed on it and marked as placed from the description.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

from shapely.geometry import Point, shape
from shapely.prepared import prep
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings

AREA_SOURCE = "OpenStreetMap boundaries (not the revenue record)"


@lru_cache(maxsize=1)
def _areas() -> list[tuple[str, str, str | None, object]]:
    path = settings.data_dir / "areas" / "admin_orr.geojson"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [(f["properties"]["level"], f["properties"]["name"], f["properties"].get("name_te"), prep(shape(f["geometry"])))
            for f in data["features"]]


def osm_area(lon: float, lat: float) -> dict:
    p = Point(lon, lat)
    out: dict = {}
    for level, name, _te, geom in _areas():
        if level not in out and geom.contains(p):
            out[level] = name
    return out


def survey_numbers(db: Session, lon: float, lat: float) -> list[dict]:
    rows = db.execute(text(
        """
        SELECT p.village, p.survey_no, p.sub_division, p.land_category
        FROM land_parcels_current p
        WHERE NOT p.is_sample AND ST_Intersects(p.geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
        ORDER BY p.survey_no LIMIT 5
        """
    ), {"lon": lon, "lat": lat}).mappings().all()
    return [dict(r) for r in rows]


def area_of(db: Session, lon: float, lat: float, asset: dict | None) -> dict:
    """District, mandal and village, and where they came from."""
    if asset and asset.get("district"):
        return {"district": asset["district"], "mandal": asset.get("mandal"), "village": asset.get("village"), "source": "location"}
    found = osm_area(lon, lat)
    if found.get("district"):
        return {"district": found["district"], "mandal": found.get("mandal"), "village": None, "source": AREA_SOURCE}
    return {"district": None, "mandal": None, "village": None, "source": None}


def from_words(db: Session, words: str | None) -> dict | None:
    """A point on the one watched location the words name, or None if they name none or several."""
    if not words or len(words.strip()) < 3:
        return None
    norm = re.sub(r"\s+", " ", words.lower())
    rows = db.execute(text(
        """
        SELECT a.id, a.name, a.name_te, ST_X(ST_PointOnSurface(b.geom)) AS lon, ST_Y(ST_PointOnSurface(b.geom)) AS lat
        FROM assets a JOIN LATERAL (SELECT geom FROM boundaries b WHERE b.asset_id = a.id AND b.kind IN ('ftl', 'parcel')
                                    ORDER BY b.version DESC LIMIT 1) b ON true
        WHERE a.type::text <> 'reported_place'
        """
    )).mappings().all()
    hits = [r for r in rows if re.search(rf"\b{re.escape(r['name'].lower())}\b", norm)
            or (r["name_te"] and r["name_te"] in words)]
    if len(hits) != 1:
        return None
    h = hits[0]
    return {"asset_id": h["id"], "name": h["name"], "lon": round(float(h["lon"]), 6), "lat": round(float(h["lat"]), 6)}
