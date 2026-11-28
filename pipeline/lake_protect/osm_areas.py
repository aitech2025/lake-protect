"""District, mandal and village for every real lake, from OpenStreetMap.

The drill-down dashboard (DECISIONS.md D-060) groups assets by district, mandal and village. In
production these come with the government record: the HMDA and Bhu Bharati files carry them
(docs/asset-engine.md). The real lakes come from OpenStreetMap and carry none, so this command
places each lake, by a point on its surface, inside OSM's district (admin_level 5) and mandal
(admin_level 6) boundaries.

OpenStreetMap has no revenue-village boundaries around Hyderabad, so the village is the nearest
OSM settlement (a village, town or suburb) inside the lake's mandal (D-069). Smaller named places
(hamlet, locality, neighbourhood) are used only when no settlement is near, then any settlement
close by. Every lake says which place it took (`village_source`).

The result is a convenience for grouping and routing, never a revenue record: every placed lake
says where its area came from (`area_source`). The Overpass responses are saved, so the placement
can be rebuilt and checked without querying again.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
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


SETTLEMENTS = ("village", "town", "suburb")
SMALL_PLACES = ("hamlet", "locality", "neighbourhood", "quarter")
# Where to look for a lake's village, in order: (kinds of place, inside the lake's mandal only, metres).
VILLAGE_SEARCH = ((SETTLEMENTS, True, 5000), (SMALL_PLACES, True, 3000), (SETTLEMENTS, False, 8000))
VILLAGE_NOTE = "nearest place in the mandal, not the revenue village"


def places_query(bbox: list[float]) -> str:
    # A margin around the box, so a lake near its edge still finds the places beyond it.
    west, south, east, north = (round(v, 4) for v in (bbox[0] - 0.1, bbox[1] - 0.1, bbox[2] + 0.1, bbox[3] + 0.1))
    kinds = "|".join(SETTLEMENTS + SMALL_PLACES)
    return f"""[out:json][timeout:180];
node["place"~"^({kinds})$"]["name"]({south},{west},{north},{east});
out;"""


def fetch(bbox: list[float], raw_path: Path, query_of=admin_query) -> dict:
    import httpx

    query = query_of(bbox)
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


def places(payload: dict) -> list[dict]:
    """Named OSM places (village, town, suburb and smaller), as points."""
    out = []
    for el in payload["response"].get("elements", []):
        tags = el.get("tags", {})
        if el.get("type") != "node" or tags.get("place") not in SETTLEMENTS + SMALL_PLACES or not tags.get("name"):
            continue
        out.append({"name": tags["name"].strip(), "name_te": tags.get("name:te"), "place": tags["place"],
                    "osm": f"node/{el['id']}", "lon": el["lon"], "lat": el["lat"]})
    return out


def _metres(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    dx = (lon2 - lon1) * 111_320 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dx, (lat2 - lat1) * 110_540)


def nearest_village(point, mandal, named: list[dict]) -> dict | None:
    """The place a lake's village is named after (VILLAGE_SEARCH), or None when nothing is near.

    `mandal` is the lake's prepared mandal boundary, or None when the lake has no mandal.
    """
    from shapely.geometry import Point

    for kinds, in_mandal, limit in VILLAGE_SEARCH:
        if in_mandal and mandal is None:
            continue
        best, best_d = None, float(limit)
        for c in named:
            if c["place"] not in kinds:
                continue
            d = _metres(point.x, point.y, c["lon"], c["lat"])
            if d <= best_d and (not in_mandal or mandal.contains(Point(c["lon"], c["lat"]))):
                best, best_d = c, d
        if best is not None:
            return {**best, "metres": round(best_d)}
    return None


def place(features: list[dict], found: list[dict], named: list[dict] | None = None) -> dict:
    """Set district and mandal on each feature from the boundary that holds a point on its surface,
    and its village from the nearest named place (when `named` is given)."""
    from shapely.geometry import shape
    from shapely.prepared import prep

    prepared = [(a, prep(a["geom"])) for a in found]
    placed = {"district": 0, "mandal": 0}
    if named is not None:
        placed["village"] = 0
    unplaced = []
    for f in features:
        p = f["properties"]
        point = shape(f["geometry"]).representative_point()
        hits = {"district": None, "mandal": None}
        for a, pa in prepared:
            if hits[a["level"]] is None and pa.contains(point):
                hits[a["level"]] = (a, pa)
        for level in ("district", "mandal"):
            if hits[level] is not None:
                p[level] = hits[level][0]["name"]
                placed[level] += 1
        if hits["district"] is None:
            unplaced.append(p["asset_key"])
        p["area_source"] = AREA_SOURCE if hits["district"] else None
        if named is not None:
            v = nearest_village(point, hits["mandal"][1] if hits["mandal"] else None, named)
            p["village"] = v["name"] if v else None
            p["village_source"] = (f"OpenStreetMap {v['place']} {v['osm']}, {v['metres']} m away: {VILLAGE_NOTE}" if v else None)
            placed["village"] += 1 if v else 0
    return {**placed, "unplaced": unplaced}


AREAS_OUT = Path("data/areas/admin_orr.geojson")


def export(found: list[dict], payload: dict, out_path: Path) -> int:
    """District and mandal outlines for the API, so a citizen's pin gets its area (D-063).

    Simplified to about 20 m: enough to say which mandal holds a point, small enough to load fast.
    """
    from shapely.geometry import mapping

    feats = [{"type": "Feature", "properties": {"level": a["level"], "name": a["name"], "name_te": a["name_te"], "osm": a["osm"]},
              "geometry": mapping(a["geom"].simplify(0.0002, preserve_topology=True))} for a in found]
    out = {"type": "FeatureCollection", "source": {"description": AREA_SOURCE, "licence": "ODbL, (c) OpenStreetMap contributors",
                                                   "retrieved_at": payload.get("retrieved_at")}, "features": feats}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return len(feats)


PLACES_RAW = Path("data/sources/overpass_places_orr.json")


def run(assets_path: Path, raw_path: Path, bbox: list[float], refetch: bool, areas_out: Path | None = AREAS_OUT,
        places_raw: Path | None = PLACES_RAW) -> dict:
    payload = fetch(bbox, raw_path) if refetch or not raw_path.exists() else json.loads(raw_path.read_text(encoding="utf-8"))
    found = areas(payload)
    if areas_out is not None:
        export(found, payload, areas_out)
    named = None
    if places_raw is not None:
        named_payload = (fetch(bbox, places_raw, places_query) if refetch or not places_raw.exists()
                         else json.loads(places_raw.read_text(encoding="utf-8")))
        named = places(named_payload)
    collection = json.loads(assets_path.read_text(encoding="utf-8"))
    result = place(collection["features"], found, named)
    collection.setdefault("source", {})["areas"] = {
        "description": "district and mandal of each lake: the OSM boundary holding a point on its surface",
        "licence": "Open Database Licence (ODbL). Attribution: (c) OpenStreetMap contributors",
        "overpass_endpoint": payload["endpoint"],
        "retrieved_at": payload["retrieved_at"],
        "raw_response_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
    }
    if named is not None:
        collection["source"]["villages"] = {
            "description": f"village of each lake: the {VILLAGE_NOTE} (OSM village, town or suburb; smaller places only when none is near)",
            "licence": "Open Database Licence (ODbL). Attribution: (c) OpenStreetMap contributors",
            "overpass_endpoint": named_payload["endpoint"],
            "retrieved_at": named_payload["retrieved_at"],
            "raw_response_sha256": hashlib.sha256(places_raw.read_bytes()).hexdigest(),
        }
    assets_path.write_text(json.dumps(collection, ensure_ascii=False, indent=1), encoding="utf-8")
    counts: dict[str, int] = {}
    for f in collection["features"]:
        key = f"{f['properties'].get('district')} / {f['properties'].get('mandal')} / {f['properties'].get('village')}"
        counts[key] = counts.get(key, 0) + 1
    return {"boundaries": len(found), "features": len(collection["features"]), **result, "by_area": dict(sorted(counts.items()))}
