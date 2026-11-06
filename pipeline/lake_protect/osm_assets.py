"""Build data/assets.geojson from OpenStreetMap water polygons.

OpenStreetMap is a free, non-government source (CONTEXT.md section 8.2: "JRC maximum water
extent, or OpenStreetMap water ... status `derived`"). Every asset produced here is cohort D
(`derived`, mode WATCH): fine for a first backtest run, never for field action.

The Overpass response is saved next to the output with its retrieval time, so the asset file can
be rebuilt and checked without querying again.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path

import yaml

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "lake-protect-prototype/0.1 (research prototype)"
ACRE_SQ_M = 4046.86


def normalise(name: str) -> str:
    return re.sub(r"[^a-z]+", " ", name.lower()).strip()


def overpass_query(bbox: list[float]) -> str:
    west, south, east, north = bbox
    b = f"({south},{west},{north},{east})"
    return f"""[out:json][timeout:120];
(
  way["natural"="water"]["name"]{b};
  relation["natural"="water"]["name"]{b};
  way["landuse"="reservoir"]["name"]{b};
  relation["landuse"="reservoir"]["name"]{b};
  way["water"]["name"]{b};
);
out tags geom;"""


def fetch(bbox: list[float], raw_path: Path) -> dict:
    import httpx

    query = overpass_query(bbox)
    resp = httpx.post(OVERPASS_URL, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=180)
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


def _ring(coords: list[dict]) -> list[tuple[float, float]]:
    return [(p["lon"], p["lat"]) for p in coords]


def element_geometry(el: dict):
    """Polygon for a closed way, or a multipolygon assembled from a relation's outer/inner ways."""
    from shapely.geometry import MultiPolygon, Polygon
    from shapely.ops import linemerge, polygonize, unary_union

    if el["type"] == "way":
        ring = _ring(el.get("geometry", []))
        if len(ring) < 4 or ring[0] != ring[-1]:
            return None
        return Polygon(ring)

    outers, inners = [], []
    for member in el.get("members", []):
        if member.get("type") != "way" or "geometry" not in member:
            continue
        line = _ring(member["geometry"])
        (inners if member.get("role") == "inner" else outers).append(line)
    if not outers:
        return None
    from shapely.geometry import LineString

    outer_polys = list(polygonize(linemerge([LineString(l) for l in outers])))
    inner_polys = list(polygonize(linemerge([LineString(l) for l in inners]))) if inners else []
    if not outer_polys:
        return None
    shape = unary_union(outer_polys)
    if inner_polys:
        shape = shape.difference(unary_union(inner_polys))
    if shape.geom_type == "Polygon":
        shape = MultiPolygon([shape])
    return shape


def area_sq_m(geom) -> float:
    from pyproj import Transformer
    from shapely.ops import transform

    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True).transform
    return transform(to_utm, geom).area


def build(search_path: Path, raw_path: Path, out_path: Path, refetch: bool) -> dict:
    from shapely.geometry import MultiPolygon, mapping
    from shapely.validation import make_valid

    spec = yaml.safe_load(search_path.read_text(encoding="utf-8"))
    payload = fetch(spec["bbox"], raw_path) if refetch or not raw_path.exists() else json.loads(
        raw_path.read_text(encoding="utf-8")
    )
    retrieved = payload["retrieved_at"][:10]
    elements = payload["response"]["elements"]

    compiled = [(l["case"], [re.compile(p) for p in l["patterns"]]) for l in spec["lakes"]]
    matches: dict[str, list[dict]] = {c: [] for c, _ in compiled}
    features = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name", "")
        norm = normalise(name + " " + tags.get("name:en", "") + " " + tags.get("alt_name", ""))
        hit_cases = [case for case, pats in compiled if any(p.search(norm) for p in pats)]
        if not hit_cases:
            continue
        geom = element_geometry(el)
        if geom is None or geom.is_empty:
            continue
        if not geom.is_valid:
            geom = make_valid(geom)
        if geom.geom_type == "Polygon":
            geom = MultiPolygon([geom])
        if geom.geom_type != "MultiPolygon":
            polys = [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]
            if not polys:
                continue
            geom = MultiPolygon(polys)
        area = area_sq_m(geom)
        osm_ref = f"{el['type']}/{el['id']}"
        for case in hit_cases:
            matches[case].append({"osm": osm_ref, "name": name, "area_acres": round(area / ACRE_SQ_M, 2)})
        features.append(
            {
                "type": "Feature",
                "geometry": mapping(geom),
                "properties": {
                    "asset_key": f"osm-{el['type']}-{el['id']}",
                    "name": name,
                    "name_te": tags.get("name:te"),
                    "type": "lake",
                    "cohort": "D_UNNOTIFIED",
                    "district": None,
                    "mandal": None,
                    "village": None,
                    "survey_numbers": [],
                    "area_acres": round(area / ACRE_SQ_M, 2),
                    "custodian_agency": None,
                    "has_cctv": None,
                    "is_demo": False,
                    "boundary": {
                        "kind": "ftl",
                        "status": "derived",
                        "source_name": f"OpenStreetMap contributors, {osm_ref} (ODbL)",
                        "source_url": f"https://www.openstreetmap.org/{osm_ref}",
                        "source_date": retrieved,
                        "notification_ref": None,
                        "certified_by": None,
                    },
                    "osm_tags": {k: v for k, v in tags.items() if k in {"name", "name:te", "name:en", "alt_name", "natural", "water", "landuse", "wikidata"}},
                    "matched_case_names": hit_cases,
                    "notes": "OSM water outline used as a stand-in boundary. Not a certified FTL. "
                    "Name match only: not yet confirmed as the lake in any case report.",
                },
            }
        )

    features.sort(key=lambda f: f["properties"]["asset_key"])
    for case, hits in matches.items():
        for f in features:
            if case in f["properties"]["matched_case_names"]:
                f["properties"].setdefault("match_status", {})[case] = (
                    "unique_name_match" if len(hits) == 1 else f"ambiguous_name ({len(hits)} OSM polygons)"
                )
    collection = {
        "type": "FeatureCollection",
        "name": "lake-protect-real-assets",
        "source": {
            "description": "OpenStreetMap water polygons whose names match CONTEXT.md section 13 lakes",
            "licence": "Open Database Licence (ODbL). Attribution: (c) OpenStreetMap contributors",
            "overpass_endpoint": payload["endpoint"],
            "retrieved_at": payload["retrieved_at"],
            "raw_response_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        },
        "features": features,
    }
    out_path.write_text(json.dumps(collection, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"elements": len(elements), "features": len(features), "matches": matches}
