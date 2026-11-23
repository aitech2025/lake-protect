"""Build data/assets.geojson from OpenStreetMap water polygons.

OpenStreetMap is a free, non-government source (CONTEXT.md section 8.2: "JRC maximum water
extent, or OpenStreetMap water ... status `derived`"). Every asset produced here is cohort D
(`derived`, mode WATCH): fine for screening and a first backtest run, never for field action.

The file holds two kinds of feature (DECISIONS.md D-038):
- every named lake or tank in the ORR box within the registry's size limits, the watch list for
  the weekly screen; and
- every polygon whose name matches a section 13 case lake, whatever its size.

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


def _drop_duplicates(features: list[dict]) -> list[dict]:
    """Two OSM outlines of the same lake (mapped twice) are one asset: keep a case-matched one,
    else the older OSM id. Same lake means intersection over union of 0.8 or more."""

    def rank(f):
        p = f["properties"]
        return (0 if p["matched_case_names"] else 1, int(p["asset_key"].rsplit("-", 1)[1]))

    kept: list[dict] = []
    for f in sorted(features, key=rank):
        g = f["_geom"]
        same = False
        for k in kept:
            h = k["_geom"]
            if g.intersects(h):
                inter = g.intersection(h).area
                if inter / max(g.union(h).area, 1e-12) >= 0.8:
                    same = True
                    break
        if not same:
            kept.append(f)
    return kept


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
    registry = spec.get("registry") or {}
    excluded_water = set(registry.get("exclude_water", []))
    features = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name", "")
        norm = normalise(name + " " + tags.get("name:en", "") + " " + tags.get("alt_name", ""))
        hit_cases = [case for case, pats in compiled if any(p.search(norm) for p in pats)]
        in_registry = bool(registry) and tags.get("water") not in excluded_water
        if not hit_cases and not in_registry:
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
        if not hit_cases and not (registry["min_area_ha"] * 1e4 <= area <= registry["max_area_ha"] * 1e4):
            continue
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
                    "baseline_date": registry.get("baseline_date"),
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
                    "notes": "OSM water outline used as a stand-in boundary. Not a certified FTL."
                    + (" Name match only: not yet confirmed as the lake in any case report." if hit_cases else ""),
                },
                "_geom": geom,
            }
        )

    features = _drop_duplicates(features)
    for f in features:
        f.pop("_geom", None)
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
            "description": "OpenStreetMap water polygons: named lakes and tanks in the ORR box within the registry limits, plus every polygon whose name matches a CONTEXT.md section 13 lake",
            "registry": registry,
            "licence": "Open Database Licence (ODbL). Attribution: (c) OpenStreetMap contributors",
            "overpass_endpoint": payload["endpoint"],
            "retrieved_at": payload["retrieved_at"],
            "raw_response_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        },
        "features": features,
    }
    out_path.write_text(json.dumps(collection, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"elements": len(elements), "features": len(features), "matches": matches}
