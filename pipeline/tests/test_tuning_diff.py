from copy import deepcopy

import pytest
from shapely.geometry import box, mapping

from lake_protect.geospatial.tuning_diff import TuningDiffError, compare_collections


def feature(feature_id, asset, geometry, change_type="clearing", area_sq_m=4000):
    return {
        "type": "Feature",
        "id": feature_id,
        "geometry": mapping(geometry),
        "properties": {
            "asset_key": asset,
            "change_type": change_type,
            "area_sq_m": area_sq_m,
            "first_changed_at": "2026-06-01",
        },
    }


def collection(*features):
    return {"type": "FeatureCollection", "features": list(features)}


def test_spatial_diff_matches_overlapping_candidates_and_lists_disappeared_and_added():
    before = collection(
        feature("old-match", "kapra", box(78.0, 17.0, 78.001, 17.001)),
        feature("old-lost", "kapra", box(78.01, 17.01, 78.011, 17.011)),
    )
    after = collection(
        feature("new-match", "kapra", box(78.0001, 17.0, 78.0011, 17.001)),
        feature("new-added", "gangaram", box(78.02, 17.02, 78.021, 17.021)),
    )

    result = compare_collections(before, after, iou_threshold=0.10)

    assert (result["before_candidates"], result["after_candidates"]) == (2, 2)
    assert (result["matched"], result["disappeared"], result["added"]) == (1, 1, 1)
    assert result["matches"][0]["before_id"] == "old-match"
    assert result["matches"][0]["after_id"] == "new-match"
    assert result["disappeared_candidates"][0]["id"] == "old-lost"
    assert result["added_candidates"][0]["id"] == "new-added"
    assert result["disappeared_candidates"][0]["area_acres"] == pytest.approx(0.9884)
    assert "not false positives" in result["interpretation"]


def test_candidates_on_different_assets_do_not_match_even_if_geometry_overlaps():
    polygon = box(78.0, 17.0, 78.001, 17.001)
    result = compare_collections(
        collection(feature("old", "kapra", polygon)),
        collection(feature("new", "gangaram", polygon)),
    )
    assert result["matched"] == 0
    assert result["disappeared"] == 1
    assert result["added"] == 1


def test_candidates_of_different_change_types_do_not_match():
    polygon = box(78.0, 17.0, 78.001, 17.001)
    result = compare_collections(
        collection(feature("old", "kapra", polygon, "clearing")),
        collection(feature("new", "kapra", polygon, "building")),
    )
    assert result["matched"] == 0


def test_invalid_or_unscoped_feature_is_rejected():
    invalid = {"type": "Feature", "id": "x", "geometry": mapping(box(78, 17, 78.001, 17.001)), "properties": {"change_type": "clearing"}}
    with pytest.raises(TuningDiffError, match="asset_key"):
        compare_collections(collection(invalid), collection())


def test_duplicate_ids_are_rejected():
    item = feature("same", "kapra", box(78, 17, 78.001, 17.001))
    with pytest.raises(TuningDiffError, match="duplicate feature id"):
        compare_collections(collection(item, deepcopy(item)), collection())


def test_iou_threshold_is_bounded():
    with pytest.raises(ValueError, match="iou_threshold"):
        compare_collections(collection(), collection(), iou_threshold=1.1)
