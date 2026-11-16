from pathlib import Path

import pytest

from lake_protect.intelligence.training import TrainingDataError, _read_dataset


HEADER = "asset_id,label,area_sq_m,area_growth,persistence_count,observation_gap_days,sensor_agreement,boundary_quality,stage_preventability"


def test_training_dataset_rejects_missing_feature_columns(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text("asset_id,label,area_sq_m\na,1,20\n", encoding="utf-8")
    with pytest.raises(TrainingDataError, match="missing required columns"):
        _read_dataset(path)


def test_training_dataset_rejects_out_of_range_features(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text(HEADER + "\na,1,100,0.1,2,10,1.5,0.8,0.5\n", encoding="utf-8")
    with pytest.raises(TrainingDataError, match="must be between 0 and 1"):
        _read_dataset(path)


def test_training_dataset_rejects_unexpected_columns(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text(HEADER + ",owner_name\na,1,100,0.1,2,10,0.8,0.8,0.5,not-used\n", encoding="utf-8")
    with pytest.raises(TrainingDataError, match="Unexpected columns"):
        _read_dataset(path)
