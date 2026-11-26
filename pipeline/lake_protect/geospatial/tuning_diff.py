"""Spatially compare two non-scored M2 tuning candidate exports.

The comparison is deliberately diagnostic: a disappeared candidate is not automatically a
false positive, and a new candidate is not an alert recommendation. It identifies footprints
that need human review before detector rules are frozen.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform

# UTM 44N is the appropriate local metric CRS for the Hyderabad/Telangana tuning AOIs.
_TO_METRES = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True).transform


class TuningDiffError(ValueError):
    """The supplied tuning exports cannot be compared safely."""


def _read_features(collection: dict[str, Any], label: str) -> list[dict[str, Any]]:
    if collection.get("type") != "FeatureCollection" or not isinstance(collection.get("features"), list):
        raise TuningDiffError(f"{label} must be a GeoJSON FeatureCollection")
    out = []
    seen = set()
    for index, feature in enumerate(collection["features"]):
        if not isinstance(feature, dict) or feature.get("type") != "Feature" or not isinstance(feature.get("geometry"), dict):
            raise TuningDiffError(f"{label} feature[{index}] must be a GeoJSON Feature with geometry")
        props = feature.get("properties") or {}
        if not isinstance(props, dict):
            raise TuningDiffError(f"{label} feature[{index}] properties must be an object")
        asset = props.get("asset_key") or props.get("asset_name") or props.get("asset_id")
        change_type = props.get("change_type")
        if asset is None or not change_type:
            raise TuningDiffError(f"{label} feature[{index}] needs asset_key/asset_name/asset_id and change_type")
        geom = shape(feature["geometry"])
        if geom.is_empty or not geom.is_valid or geom.geom_type not in ("Polygon", "MultiPolygon"):
            raise TuningDiffError(f"{label} feature[{index}] has invalid polygon geometry")
        minx, miny, maxx, maxy = geom.bounds
        if minx < -180 or maxx > 180 or miny < -90 or maxy > 90:
            raise TuningDiffError(f"{label} feature[{index}] coordinates are outside EPSG:4326 bounds")
        stable_id = str(feature.get("id") or props.get("candidate_id") or f"{asset}:{change_type}:{index}")
        if stable_id in seen:
            raise TuningDiffError(f"{label} contains duplicate feature id {stable_id}")
        seen.add(stable_id)
        projected = transform(_TO_METRES, geom)
        out.append({
            "id": stable_id,
            "asset": str(asset),
            "change_type": str(change_type),
            "geometry": geom,
            "projected": projected,
            "properties": props,
        })
    return out


def _area_acres(feature: dict[str, Any]) -> float | None:
    props = feature["properties"]
    if props.get("area_acres") is not None:
        return round(float(props["area_acres"]), 4)
    if props.get("area_sq_m") is not None:
        return round(float(props["area_sq_m"]) / 4046.8564224, 4)
    return None


def compare_collections(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    iou_threshold: float = 0.10,
) -> dict[str, Any]:
    """Greedy one-to-one spatial match by asset and change type, using projected polygon IoU."""
    if not 0 <= iou_threshold <= 1:
        raise ValueError("iou_threshold must be between 0 and 1")
    old = _read_features(before, "before")
    new = _read_features(after, "after")

    pairs = []
    for i, a in enumerate(old):
        for j, b in enumerate(new):
            if a["asset"] != b["asset"] or a["change_type"] != b["change_type"]:
                continue
            intersection = a["projected"].intersection(b["projected"]).area
            union = a["projected"].union(b["projected"]).area
            iou = intersection / union if union else 0.0
            if iou >= iou_threshold:
                pairs.append((iou, i, j))
    pairs.sort(reverse=True)

    used_old: set[int] = set()
    used_new: set[int] = set()
    matched = []
    for iou, i, j in pairs:
        if i in used_old or j in used_new:
            continue
        used_old.add(i)
        used_new.add(j)
        matched.append({
            "before_id": old[i]["id"],
            "after_id": new[j]["id"],
            "asset": old[i]["asset"],
            "change_type": old[i]["change_type"],
            "iou": round(iou, 5),
            "before_area_acres": _area_acres(old[i]),
            "after_area_acres": _area_acres(new[j]),
        })

    def review_row(item: dict[str, Any], reason: str) -> dict[str, Any]:
        return {
            "id": item["id"],
            "asset": item["asset"],
            "change_type": item["change_type"],
            "area_acres": _area_acres(item),
            "first_changed_at": item["properties"].get("first_changed_at"),
            "reason": reason,
            "geometry": mapping(item["geometry"]),
            "properties": item["properties"],
        }

    disappeared = [review_row(item, "present_before_absent_after") for i, item in enumerate(old) if i not in used_old]
    added = [review_row(item, "absent_before_present_after") for j, item in enumerate(new) if j not in used_new]
    old_by_type = Counter(x["change_type"] for x in old)
    new_by_type = Counter(x["change_type"] for x in new)
    return {
        "schema_version": 1,
        "comparison": "one_to_one_spatial_iou_same_asset_same_change_type",
        "iou_threshold": iou_threshold,
        "before_candidates": len(old),
        "after_candidates": len(new),
        "matched": len(matched),
        "disappeared": len(disappeared),
        "added": len(added),
        "before_by_change_type": dict(sorted(old_by_type.items())),
        "after_by_change_type": dict(sorted(new_by_type.items())),
        "matches": matched,
        "disappeared_candidates": disappeared,
        "added_candidates": added,
        "interpretation": (
            "Spatial comparison only. Disappeared/added footprints are review leads, not "
            "false positives, true positives, legal findings or enforcement recommendations."
        ),
    }


def compare_files(before_path: Path, after_path: Path, output_path: Path, *, iou_threshold: float = 0.10) -> dict:
    before = json.loads(Path(before_path).read_text(encoding="utf-8"))
    after = json.loads(Path(after_path).read_text(encoding="utf-8"))
    result = compare_collections(before, after, iou_threshold=iou_threshold)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
