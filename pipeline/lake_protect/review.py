"""The satellite review of a citizen's report (DECISIONS.md D-063).

`lp review-reports` asks the API for citizen incidents waiting for their review. For each one it
screens the reported place's location now, with the same rules and imagery as the weekly screen.
It then says what the newest images show within 150 m of the pin:
- **change_found:** the nearest change, with its before and after images and the scenes used;
- **no_change:** clear looks and no change, with the latest clear image;
- **no_clear_look:** too few clear looks, because of cloud.

The weekly screen's rules apply unchanged: a change smaller than 1,000 sq m is not reported, and a
change must persist over two looks. Citizens are told small works may not show from space.
"""
from __future__ import annotations

import base64
import datetime as dt

from shapely.geometry import Point, shape

from lake_protect.aoi import AssetAOI, build, to_utm
from lake_protect.detect import AssetResult
from lake_protect.screen import coverage_status

NEAR_M = 150


def aoi_for(item: dict) -> AssetAOI:
    a = item["asset"]
    b = a["boundaries"]
    primary = b.get("ftl") or b.get("parcel")
    return build(
        asset_id=a["id"], asset_key=a["asset_key"], name=a["name"], primary_geojson=primary["geometry"],
        buffer_geojson=(b.get("buffer") or {}).get("geometry"), ring_geojson=(b.get("watch_ring") or {}).get("geometry"),
        baseline_date=dt.date.fromisoformat(a["baseline_date"]),
    )


def result_for(item: dict, r: AssetResult) -> dict:
    """The body for POST /pipeline/reviews/{id}."""
    status = coverage_status(r)
    if status == "failed":
        return {"status": "failed", "detail": str(r.counts.get("error", "The screen failed"))[:400]}
    if status in ("not_observed", "no_usable_look"):
        return {"status": "done", "result": "no_clear_look", "as_of": r.as_of.isoformat(),
                "detail": f"{r.looks} clear look(s) of the place; at least two are needed"}
    pin = to_utm(Point(item["lon"], item["lat"]))
    near = sorted(((to_utm(shape(c["geometry"])).distance(pin), i, c) for i, c in enumerate(r.candidates)), key=lambda x: (x[0], x[1]))
    near = [x for x in near if x[0] <= NEAR_M]
    if near:
        c = near[0][2]
        return {
            "status": "done", "result": "change_found", "as_of": r.as_of.isoformat(),
            "before_date": c.get("last_clear_at"), "after_date": c.get("latest_changed_at") or c["first_changed_at"],
            "scenes": c.get("observations", []),
            "before_png_b64": c.get("before_chip_png_b64"), "after_png_b64": c.get("after_chip_png_b64"),
            "change": {"change_type": c["change_type"], "area_sq_m": c["area_sq_m"], "first_changed_at": c["first_changed_at"]},
            "detail": f"{len(r.candidates)} change(s) on the location; the nearest is {near[0][0]:.0f} m from the pin",
        }
    scenes = []
    if r.week_image_scene_id and r.week_image_date:
        scenes = [{"sensor": "sentinel-2-l2a", "scene_id": r.week_image_scene_id, "acquired_at": f"{r.week_image_date.isoformat()}T00:00:00+00:00",
                   "licence_notice": f"Contains modified Copernicus Sentinel data {r.week_image_date.year}"}]
    return {
        "status": "done", "result": "no_change", "as_of": r.as_of.isoformat(),
        "after_date": (r.week_image_date or r.last_look).isoformat() if (r.week_image_date or r.last_look) else None,
        "scenes": scenes,
        "after_png_b64": base64.b64encode(r.week_image_png).decode() if r.week_image_png else None,
        "detail": f"{r.looks} clear looks; no change within {NEAR_M} m of the pin",
    }
