"""Load real assets from data/assets.geojson.

    python -m app.seed.real_assets /srv/data/assets.geojson

Idempotent by asset_key. If a boundary geometry changed in the file, a new version is added and
the old one stays retrievable. Real assets are never marked is_demo.

baseline_date: monitoring starts on the date the boundary was retrieved, so only change after
enrolment can alert (rule 3). The backtest sets its own per-case baseline (DECISIONS.md D-014).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Asset
from app.services import boundaries as bsvc

REQUIRED_BOUNDARY_FIELDS = ("kind", "status", "source_name", "source_url", "source_date")


def load(db: Session, path: Path) -> dict:
    collection = json.loads(path.read_text(encoding="utf-8"))
    created = versioned = unchanged = 0
    for feature in collection["features"]:
        p = feature["properties"]
        b = p["boundary"]
        missing = [f for f in REQUIRED_BOUNDARY_FIELDS if not b.get(f)]
        if missing:
            raise ValueError(f"{p['asset_key']}: boundary is missing {missing}")
        if p.get("is_demo"):
            raise ValueError(f"{p['asset_key']}: demo data does not belong in the real asset file")
        source_date = dt.date.fromisoformat(b["source_date"])
        asset = db.scalar(select(Asset).where(Asset.asset_key == p["asset_key"]))
        if asset is None:
            asset = Asset(
                asset_key=p["asset_key"],
                name=p["name"],
                name_te=p.get("name_te"),
                type=p["type"],
                cohort=p["cohort"],
                district=p.get("district"),
                mandal=p.get("mandal"),
                village=p.get("village"),
                survey_numbers=p.get("survey_numbers") or [],
                area_acres=p.get("area_acres"),
                custodian_agency=p.get("custodian_agency"),
                has_cctv=p.get("has_cctv"),
                baseline_date=source_date,
                is_demo=False,
                notes=p.get("notes"),
            )
            db.add(asset)
            db.flush()
            created += 1
        else:
            current = bsvc.primary_of(bsvc.current_boundary_set(db, asset.id))
            same = current is not None and db.scalar(
                text("SELECT ST_Equals(geom, ST_GeomFromGeoJSON(:g)) FROM boundaries WHERE id = :i"),
                {"g": json.dumps(feature["geometry"]), "i": current["id"]},
            )
            if same:
                unchanged += 1
                continue
            versioned += 1
        bsvc.add_version(
            db,
            asset,
            kind=b["kind"],
            status=b["status"],
            geometry=feature["geometry"],
            source_name=b["source_name"],
            source_url=b.get("source_url"),
            source_date=source_date,
            notification_ref=b.get("notification_ref"),
            certified_by=b.get("certified_by"),
            valid_from=source_date,
        )
    db.commit()
    return {"created": created, "new_versions": versioned, "unchanged": unchanged}


if __name__ == "__main__":
    from app.db import SessionLocal

    target = Path(sys.argv[1] if len(sys.argv) > 1 else "/srv/data/assets.geojson")
    with SessionLocal() as session:
        print(load(session, target))
