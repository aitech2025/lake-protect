"""The satellite review of a citizen's report (D-063): what `lp review-reports` sends back. Offline."""
from __future__ import annotations

import datetime as dt
import math

from shapely.geometry import box, mapping

from lake_protect.detect import AssetResult
from lake_protect.review import aoi_for, result_for

LON, LAT = 78.47, 17.40  # a fictional square near Hyderabad: geometry only, no imagery is read


def square(lon: float, lat: float, side_m: float) -> dict:
    dlat = side_m / 111_320 / 2
    dlon = side_m / (111_320 * math.cos(math.radians(lat))) / 2
    return mapping(box(lon - dlon, lat - dlat, lon + dlon, lat + dlat))


def item(lon: float = LON, lat: float = LAT) -> dict:
    return {"id": 1, "lon": lon, "lat": lat, "asset": {
        "id": 7, "asset_key": "rep-test", "name": "Test reported place", "baseline_date": "2024-07-19",
        "boundaries": {"parcel": {"geometry": square(LON, LAT, 100)}, "watch_ring": {"geometry": square(LON, LAT, 300)}}}}


def result(candidates=(), looks=6, scenes=8, image=b"\x89PNG-test") -> AssetResult:
    return AssetResult(aoi=aoi_for(item()), as_of=dt.date(2026, 11, 25), looks=looks, first_look=dt.date(2026, 8, 1),
                       last_look=dt.date(2026, 11, 22), counts={"scenes_available": scenes}, candidates=list(candidates),
                       week_image_png=image, week_image_date=dt.date(2026, 11, 22), week_image_scene_id="S2TEST_20261122")


def cand(east_m: float, area: float = 1500) -> dict:
    lon = LON + east_m / (111_320 * math.cos(math.radians(LAT)))
    return {"geometry": square(lon, LAT, 40), "change_type": "building", "area_sq_m": area, "first_changed_at": "2026-11-02",
            "last_clear_at": "2026-10-20", "latest_changed_at": "2026-11-22", "observations": [{"sensor": "sentinel-2-l2a", "scene_id": "S2A"}],
            "before_chip_png_b64": "YmVmb3Jl", "after_chip_png_b64": "YWZ0ZXI="}


def test_the_nearest_change_within_150_m_of_the_pin_is_the_finding():
    body = result_for(item(), result([cand(400), cand(60, area=2200), cand(120)]))
    assert body["result"] == "change_found" and body["change"] == {"change_type": "building", "area_sq_m": 2200, "first_changed_at": "2026-11-02"}
    assert (body["before_date"], body["after_date"], body["after_png_b64"]) == ("2026-10-20", "2026-11-22", "YWZ0ZXI=")


def test_a_change_further_away_is_not_this_report():
    body = result_for(item(), result([cand(400)]))
    assert body["result"] == "no_change" and body["after_date"] == "2026-11-22" and body["scenes"][0]["scene_id"] == "S2TEST_20261122"
    assert body["after_png_b64"] and "within 150 m" in body["detail"]


def test_too_few_clear_looks_or_a_failure_say_so():
    assert result_for(item(), result(looks=1))["result"] == "no_clear_look"
    assert result_for(item(), result(scenes=0))["result"] == "no_clear_look"
    failed = result(scenes=3)
    failed.counts["error"] = "TimeoutError: STAC"
    assert result_for(item(), failed) == {"status": "failed", "detail": "TimeoutError: STAC"}
