import json

import numpy as np
import rasterio
from rasterio.transform import from_origin

from lake_protect.geospatial.change import compare_water_masks


def _write_mask(path, data):
    profile = {
        "driver": "GTiff", "height": data.shape[0], "width": data.shape[1],
        "count": 1, "dtype": "uint8", "crs": "EPSG:32644",
        "transform": from_origin(500000, 1900000, 10, 10), "nodata": 255,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data.astype("uint8"), 1)


def test_temporal_water_comparison_identifies_loss_and_gain(tmp_path):
    reference = np.array([[1, 1, 0], [1, 0, 0], [0, 0, 0]], dtype="uint8")
    current = np.array([[1, 0, 1], [1, 0, 0], [0, 0, 0]], dtype="uint8")
    ref_path, cur_path = tmp_path / "reference.tif", tmp_path / "current.tif"
    _write_mask(ref_path, reference)
    _write_mask(cur_path, current)

    result = compare_water_masks(ref_path, cur_path, tmp_path / "change", minimum_area_sq_m=1)
    assert result["water_loss_pixels"] == 1
    assert result["water_gain_pixels"] == 1
    features = json.loads((tmp_path / "change" / "water-change.geojson").read_text())
    assert {f["properties"]["change_type"] for f in features["features"]} == {"water_loss", "water_gain"}

def test_temporal_comparison_rejects_non_overlapping_scenes(tmp_path):
    from rasterio.transform import from_origin
    ref_path, cur_path = tmp_path / "ref-no-overlap.tif", tmp_path / "cur-no-overlap.tif"
    _write_mask(ref_path, np.ones((3, 3), dtype="uint8"))
    profile = {
        "driver": "GTiff", "height": 3, "width": 3, "count": 1, "dtype": "uint8",
        "crs": "EPSG:32644", "transform": from_origin(501000, 1900000, 10, 10),
        "nodata": 255,
    }
    with rasterio.open(cur_path, "w", **profile) as dst:
        dst.write(np.ones((3, 3), dtype="uint8"), 1)
    import pytest
    with pytest.raises(ValueError, match="Insufficient scene overlap"):
        compare_water_masks(ref_path, cur_path, tmp_path / "no-overlap", minimum_area_sq_m=1)
