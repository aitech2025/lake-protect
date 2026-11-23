"""Invariant 10: the backtest reads no scene acquired after `as_of`.

Three layers are tested: the catalogue query ends at the end of the as_of day, items a catalogue
returns anyway are dropped, and the readers refuse a later scene before touching any pixel.
"""
import datetime as dt

import numpy as np
import pytest
from shapely.geometry import box, mapping

from lake_protect import raster, stac
from lake_protect.aoi import Grid
from lake_protect.stac import LookAheadError, Scene, assert_not_after, end_of_day, parse_items, scenes_for

AOI = box(78.38, 17.42, 78.39, 17.43)
FOOT = mapping(box(78.0, 17.0, 79.0, 18.0))
BANDS = ["blue", "green", "red", "nir", "swir16", "scl"]


def _item(day: str, tile: str = "44QKE", epsg: int = 32644, cloud: float = 5.0) -> dict:
    return {
        "id": f"S2X_T{tile}_{day.replace('-', '')}T052000_L2A",
        "geometry": FOOT,
        "properties": {"datetime": f"{day}T05:24:00Z", "eo:cloud_cover": cloud, "proj:code": f"EPSG:{epsg}", "s2:processing_baseline": "05.11"},
        "assets": {b: {"href": f"https://example.invalid/{day}/{b}.tif", "raster:bands": [{"scale": 0.0001, "offset": -0.1}]} for b in BANDS},
        "links": [],
    }


def test_items_after_as_of_are_dropped_even_if_the_catalogue_returns_them():
    items = [_item("2024-06-01"), _item("2024-06-30"), _item("2024-07-01"), _item("2025-01-01")]
    chosen = scenes_for(AOI, dt.date(2024, 1, 1), dt.date(2024, 6, 30), parse_items(items))
    assert [s.date.isoformat() for s in chosen] == ["2024-06-01", "2024-06-30"]


def test_same_day_duplicates_from_two_utm_zones_keep_one_in_the_analysis_crs():
    items = [_item("2024-03-03", "43QHV", 32643, 1.0), _item("2024-03-03", "44QKE", 32644, 9.0)]
    chosen = scenes_for(AOI, dt.date(2024, 1, 1), dt.date(2024, 6, 30), parse_items(items))
    assert len(chosen) == 1 and chosen[0].epsg == 32644


def test_the_catalogue_query_ends_at_the_end_of_the_as_of_day(monkeypatch, tmp_path):
    monkeypatch.setenv("LP_CACHE_DIR", str(tmp_path))
    seen = {}

    class FakeSearch:
        def items(self):
            return iter([])

    class FakeClient:
        def search(self, **kw):
            seen.update(kw)
            return FakeSearch()

    import pystac_client

    monkeypatch.setattr(pystac_client.Client, "open", staticmethod(lambda url: FakeClient()))
    stac.search_items((78.0, 17.0, 78.1, 17.1), dt.date(2023, 1, 1), dt.date(2024, 6, 30))
    assert seen["datetime"][1] == end_of_day(dt.date(2024, 6, 30))
    assert seen["datetime"][1] < dt.datetime(2024, 7, 1, tzinfo=dt.timezone.utc)


def _scene(day: dt.date) -> Scene:
    return parse_items([_item(day.isoformat())])[0]


def test_assert_not_after_allows_the_as_of_day_and_refuses_the_next():
    assert_not_after(_scene(dt.date(2024, 6, 30)), dt.date(2024, 6, 30))
    with pytest.raises(LookAheadError):
        assert_not_after(_scene(dt.date(2024, 7, 1)), dt.date(2024, 6, 30))


def test_readers_refuse_a_later_scene_before_reading_any_pixel(monkeypatch, tmp_path):
    monkeypatch.setenv("LP_CACHE_DIR", str(tmp_path))

    def must_not_read(*a, **k):
        raise AssertionError("a pixel was read from a scene after as_of")

    monkeypatch.setattr(raster, "_read_band", must_not_read)
    grid = Grid("EPSG:32644", 300000.0, 1930000.0, 10, 10)
    later = _scene(dt.date(2024, 7, 2))
    with pytest.raises(LookAheadError):
        raster.read_scl(later, grid, dt.date(2024, 6, 30))
    with pytest.raises(LookAheadError):
        raster.read_bands(later, grid, dt.date(2024, 6, 30))


def test_change_detection_refuses_a_look_after_as_of():
    from lake_protect.change import detect

    dates = [dt.date(2024, 6, 1), dt.date(2024, 7, 5)]
    with pytest.raises(AssertionError):
        detect(dates, np.ones((2, 4, 4), np.uint8), np.ones((4, 4), bool), dt.date(2024, 1, 1), dt.date(2024, 6, 30))
