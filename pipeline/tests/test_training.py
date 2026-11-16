from pathlib import Path
import csv
import hashlib

import pytest

from lake_protect.intelligence.training import TrainingDataError, _read_dataset, predict, train_model


HEADER = ["asset_id","label","area_sq_m","area_growth","persistence_count","observation_gap_days","sensor_agreement","boundary_quality","stage_preventability"]


def test_training_dataset_rejects_missing_feature_columns(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text("asset_id,label,area_sq_m\na,1,20\n", encoding="utf-8")
    with pytest.raises(TrainingDataError, match="missing required columns"):
        _read_dataset(path)


def test_training_dataset_rejects_out_of_range_features(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text(",".join(HEADER) + "\na,1,100,0.1,2,10,1.5,0.8,0.5\n", encoding="utf-8")
    with pytest.raises(TrainingDataError, match="must be in \\[0,1\\]"):
        _read_dataset(path)


def test_training_dataset_rejects_unexpected_columns(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text(",".join(HEADER + ["owner_name"]) + "\na,1,100,0.1,2,10,0.8,0.8,0.5,not-used\n", encoding="utf-8")
    with pytest.raises(TrainingDataError, match="Unexpected columns"):
        _read_dataset(path)


def test_train_uses_asset_group_holdout_and_artifact_integrity(tmp_path: Path):
    pytest.importorskip("sklearn")
    pytest.importorskip("joblib")
    dataset = tmp_path / "labels.csv"
    with dataset.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        for asset_num in range(60):
            label = asset_num % 2
            for replicate in range(2):
                writer.writerow([
                    f"asset-{asset_num}", label,
                    9000 + label * 12000 + replicate * 10,
                    0.1 + label * 0.6, 2 + label, 10,
                    0.8, 0.7, 0.5 + label * 0.4,
                ])
    artifact = tmp_path / "model.joblib"
    result = train_model(dataset, artifact, dataset_ref="test-dataset-v1")
    metrics = result["model_card"]["metrics"]
    assert metrics["split_strategy"] == "GroupShuffleSplit(asset_id)"
    assert metrics["train_assets"] > 0 and metrics["test_assets"] > 0
    assert metrics["train_assets"] + metrics["test_assets"] == 60
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == result["artifact_sha256"]
    features = {
        "area_sq_m": 12000, "area_growth": 0.5, "persistence_count": 3,
        "observation_gap_days": 10, "sensor_agreement": 0.8,
        "boundary_quality": 0.7, "stage_preventability": 0.8,
    }
    prediction = predict(artifact, result["artifact_sha256"], features)
    assert 0 <= prediction["score"] <= 100
    assert "not a legal finding" in prediction["disclaimer"]
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        predict(artifact, "0" * 64, features)
