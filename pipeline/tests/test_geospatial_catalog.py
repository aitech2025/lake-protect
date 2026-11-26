from datetime import datetime, timezone

from lake_protect.geospatial.catalog import assess_item


class Asset:
    def __init__(self, href):
        self.href = href


class Item:
    id = "S2A_TEST"
    collection_id = "sentinel-2-l2a"
    properties = {"datetime": "2026-11-20T05:00:00Z", "eo:cloud_cover": 12.0,
                  "gsd": 10, "platform": "sentinel-2a"}
    assets = {"B03": Asset("https://example.test/green.tif"),
              "B11": Asset("https://example.test/swir.tif")}


def test_sentinel_scene_is_suitable_when_required_assets_and_quality_pass():
    result = assess_item(Item(), max_cloud_pct=20,
                         now=datetime(2026, 11, 25, tzinfo=timezone.utc),
                         max_age_days=10)
    assert result.suitable is True
    assert result.gsd_m == 10
    assert result.assets["B03"].endswith("green.tif")


def test_scene_is_rejected_for_cloud_cover_and_missing_green_band():
    class BadItem(Item):
        properties = {**Item.properties, "eo:cloud_cover": 80.0}
        assets = {"B11": Asset("https://example.test/swir.tif")}
    result = assess_item(BadItem(), max_cloud_pct=30)
    assert result.suitable is False
    assert "cloud_cover>30%" in result.reasons
    assert "missing_green_band" in result.reasons
