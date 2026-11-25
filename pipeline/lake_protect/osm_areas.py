"""District and mandal for every real lake, from OpenStreetMap administrative boundaries.

The drill-down dashboard (DECISIONS.md D-060) groups assets by district, mandal and village. In
production these come with the government record: the HMDA and Bhu Bharati files carry them
(docs/asset-engine.md). The real lakes come from OpenStreetMap and carry none, so this command
places each lake, by a point on its surface, inside OSM's district (admin_level 5) and mandal
(admin_level 6) boundaries.

The result is a convenience for grouping and routing, never a revenue record: every placed lake
says where its area came from (`area_source`). The Overpass response is saved, so the placement
can be rebuilt and checked without querying again.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path

from lake_protect.osm_assets import OVERPASS_URL, USER_AGENT, element_geometry

AREA_SOURCE = "OpenStreetMap administrative boundaries (not the revenue record)"
LEVELS = {"5": "district", "6": "mandal"}


def admin_query(bbox: list[float]) -> str:
    west, south, east, north = bbox
    return f"""[out:json][timeout:180];
rel["boundary"="administrative"]["admin_level"~"^(5|6)$"]({south},{west},{north},{east});
out geom;"""


def fetch(bbox: list[float], raw_path: Path) -> dict:
    import httpx

    query = admin_query(bbox)
    resp = httpx.post(OVERPASS_URL, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=300)
    resp.raise_for_status()
    payload = {
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "endpoint": OVERPASS_URL,
        "query": query,
        "response": resp.json(),
    }
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def clean_name(name: str, level: str) -> str:
    """'Kapra mandal' -> 'Kapra'. District names are kept as OSM spells them."""
    name = name.strip()
    if LEVELS.get(level) == "mandal":
        name = re.sub(r"\s+mandal$", "", name, flags=re.IGNORECASE).strip()
    return name


def areas(payload: dict) -> list[dict]:
    out = []
    for el in payload["response"].get("elements", []):
        tags = el.get("tags", {})
        level = tags.get("admin_level")
        if el.get("type") != "relation" or level not in LEVELS or not tags.get("name"):
            continue
        geom = element_geometry(el)
        if geom is None or geom.is_empty:
            continue
        if not geom.is_valid:
            geom = geom.buffer(0)
        out.append({"level": LEVELS[level], "name": clean_name(tags["name"], level), "name_te": tags.get("name:te"),
                    "osm": f"relation/{el['id']}", "geom": geom})
    return out


def place(features: list[dict], found: list[dict]) -> dict:
    """Set district and mandal on each feature from the boundary that holds a point on its surface."""
    from shapely.geometry import shape
    from shapely.prepared import prep

    prepared = [(a, prep(a["geom"])) for a in found]
    placed = {"district": 0, "mandal": 0}
    unplaced = []
    for f in features:
        p = f["properties"]
        point = shape(f["geometry"]).representative_point()
        hits = {"district": None, "mandal": None}
        for a, pa in prepared:
            if hits[a["level"]] is None and pa.contains(point):
                hits[a["level"]] = a
        for level in ("district", "mandal"):
            if hits[level] is not None:
                p[level] = hits[level]["name"]
                placed[level] += 1
        if hits["district"] is None:
            unplaced.append(p["asset_key"])
        p["area_source"] = AREA_SOURCE if hits["district"] else None
    return {**placed, "unplaced": unplaced}


def run(assets_path: Path, raw_path: Path, bbox: list[float], refetch: bool) -> dict:
    payload = fetch(bbox, raw_path) if refetch or not raw_path.exists() else json.loads(raw_path.read_text(encoding="utf-8"))
    found = areas(payload)
    collection = json.loads(assets_path.read_text(encoding="utf-8"))
    result = place(collection["features"], found)
    collection.setdefault("source", {})["areas"] = {
        "description": "district and mandal of each lake: the OSM boundary holding a point on its surface",
        "licence": "Open Database Licence (ODbL). Attribution: (c) OpenStreetMap contributors",
        "overpass_endpoint": payload["endpoint"],
        "retrieved_at": payload["retrieved_at"],
        "raw_response_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
    }
    assets_path.write_text(json.dumps(collection, ensure_ascii=False, indent=1), encoding="utf-8")
    counts: dict[str, int] = {}
    for f in collection["features"]:
        key = f"{f['properties'].get('district')} / {f['properties'].get('mandal')}"
        counts[key] = counts.get(key, 0) + 1
    return {"boundaries": len(found), "features": len(collection["features"]), **result, "by_area": dict(sorted(counts.items()))}
