"""The image sources the admin keeps in the app (DECISIONS.md D-066): what a run applies. Offline."""
from __future__ import annotations

import pytest

from lake_protect import rules as R

APP = {
    "screen_optical": {"key": "sentinel-2-l2a", "name": "Sentinel-2 L2A", "stac_url": "https://earth-search.aws.element84.com/v1",
                       "collection": "sentinel-2-c1-l2a", "max_scene_cloud_pct": 70, "licence_notice": "Contains modified Copernicus Sentinel data {year}"},
    "screen_radar": {"key": "sentinel-1-rtc", "name": "Sentinel-1 RTC (radar)", "stac_url": "https://planetarycomputer.microsoft.com/api/stac/v1",
                     "collection": "sentinel-1-rtc", "licence_notice": "Contains modified Copernicus Sentinel data {year}"},
}


@pytest.fixture(autouse=True)
def _reset():
    yield
    R.set_sources(None)


def test_the_seeded_sources_match_the_rule_file_so_the_hash_does_not_change():
    plain = R.rules_sha256()
    lines = R.set_sources(APP)
    assert R.rules_sha256() == plain and R.radar_enabled()
    assert lines[0] == "Optical source: Sentinel-2 L2A (sentinel-2-c1-l2a)"


def test_a_changed_source_is_used_and_changes_the_hash_but_never_the_thresholds():
    plain, threshold = R.rules_sha256(), R.rules()["controls"]["min_area_sq_m"]
    mirror = {**APP, "screen_optical": {**APP["screen_optical"], "stac_url": "https://stac.example/v1", "max_scene_cloud_pct": 40}}
    lines = R.set_sources(mirror)
    assert R.rules()["sentinel2"]["stac_url"] == "https://stac.example/v1" and R.rules()["sentinel2"]["max_scene_cloud_pct"] == 40
    assert R.rules()["sentinel2"]["bands"] == ["blue", "green", "red", "nir", "swir16"]  # the rule file's
    assert R.rules()["controls"]["min_area_sq_m"] == threshold and R.rules_sha256() != plain
    assert "changed from the rule file: max_scene_cloud_pct, stac_url" in lines[0]
    R.set_sources(None)
    assert R.rules()["sentinel2"]["max_scene_cloud_pct"] == 70 and R.rules_sha256() == plain


def test_no_radar_source_turns_the_radar_check_off_and_no_optical_source_stops_the_run():
    assert "Radar check: off" in R.set_sources({**APP, "screen_radar": None})[1]
    assert not R.radar_enabled()
    with pytest.raises(RuntimeError, match="no optical source"):
        R.set_sources({**APP, "screen_optical": None})
