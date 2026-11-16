"""Leakage-aware training and evaluation for review-priority models.

Training labels must represent independently field-verified physical change.
This model does not classify ownership, legality, or encroachment.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from .features import FEATURE_NAMES, FEATURE_SCHEMA_VERSION

REQUIRED_COLUMNS = {"asset_id", "label", *FEATURE_NAMES}
MODEL_NAME = "lake_change_review_priority"
MODEL_VERSION = "rf-1.0.0"
DISCLAIMER = "Model output is a screening aid for human review, not a legal finding."


class TrainingDataError(ValueError):
    pass


def _read_dataset(path: Path):
    import numpy as np

    rows: list[list[float]] = []
    labels: list[int] = []
    groups: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
            missing = sorted(REQUIRED_COLUMNS - set(reader.fieldnames or []))
            raise TrainingDataError(f"Dataset is missing required columns: {', '.join(missing)}")
        unexpected = sorted(set(reader.fieldnames) - REQUIRED_COLUMNS)
        if unexpected:
            raise TrainingDataError(f"Unexpected columns are not accepted (owner-blind contract): {', '.join(unexpected)}")
        for line, row in enumerate(reader, start=2):
            try:
                label = int(row["label"])
                if label not in (0, 1):
                    raise ValueError("label must be 0 or 1")
                vector = [float(row[name]) for name in FEATURE_NAMES]
                if not all(np.isfinite(v) for v in vector):
                    raise ValueError("features must be finite")
                if vector[0] < 0 or vector[2] < 0 or vector[3] < 0:
                    raise ValueError("area, persistence and observation gap cannot be negative")
                if any(not 0 <= vector[i] <= 1 for i in (4, 5, 6)):
                    raise ValueError("agreement, boundary quality and preventability must be in [0,1]")
                group = str(row["asset_id"]).strip()
                if not group:
                    raise ValueError("asset_id is required for grouped validation")
            except (TypeError, ValueError, KeyError) as exc:
                raise TrainingDataError(f"Invalid row {line}: {exc}") from exc
            rows.append(vector)
            labels.append(label)
            groups.append(group)
    if len(rows) < 40 or len(set(labels)) != 2:
        raise TrainingDataError("At least 40 labelled rows and both label classes are required.")
    if min(labels.count(0), labels.count(1)) < 20:
        raise TrainingDataError("At least 20 examples of each label are required.")
    return np.asarray(rows, dtype=float), np.asarray(labels, dtype=int), np.asarray(groups)


def train_model(dataset: str | Path, artifact_path: str | Path, *, dataset_ref: str | None = None) -> dict[str, Any]:
    """Train with asset-group holdout; no observations from a test asset enter training."""
    try:
        from joblib import dump
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import (average_precision_score, brier_score_loss,
                                     confusion_matrix, precision_score, recall_score,
                                     roc_auc_score)
        from sklearn.model_selection import GroupShuffleSplit
    except ImportError as exc:
        raise RuntimeError("Install pipeline optional dependencies with: pip install -e '.[ml]'") from exc

    dataset_path = Path(dataset)
    X, y, groups = _read_dataset(dataset_path)
    split = None
    splitter = GroupShuffleSplit(n_splits=40, test_size=0.25, random_state=42)
    for train_idx, test_idx in splitter.split(X, y, groups):
        if len(set(y[train_idx])) == 2 and len(set(y[test_idx])) == 2:
            if min(int((y[test_idx] == 0).sum()), int((y[test_idx] == 1).sum())) >= 5:
                split = train_idx, test_idx
                break
    if split is None:
        raise TrainingDataError("Could not form a group-held-out test set containing at least five examples of each class.")

    train_idx, test_idx = split
    model = RandomForestClassifier(
        n_estimators=400, min_samples_leaf=3, max_features="sqrt",
        class_weight="balanced_subsample", random_state=42, n_jobs=-1,
    )
    model.fit(X[train_idx], y[train_idx])
    probabilities = model.predict_proba(X[test_idx])[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    matrix = confusion_matrix(y[test_idx], predictions, labels=[0, 1])
    metrics = {
        "roc_auc": float(roc_auc_score(y[test_idx], probabilities)),
        "average_precision": float(average_precision_score(y[test_idx], probabilities)),
        "brier_score": float(brier_score_loss(y[test_idx], probabilities)),
        "precision_at_0_5": float(precision_score(y[test_idx], predictions, zero_division=0)),
        "recall_at_0_5": float(recall_score(y[test_idx], predictions, zero_division=0)),
        "confusion_matrix_labels_0_1": matrix.tolist(),
        "test_rows": int(len(test_idx)),
        "train_rows": int(len(train_idx)),
        "test_assets": int(len(set(groups[test_idx]))),
        "train_assets": int(len(set(groups[train_idx]))),
        "split_strategy": "GroupShuffleSplit(asset_id)",
        "decision_threshold": 0.5,
    }
    # A model is evaluated, not automatically approved or deployed.
    card = {
        "model_name": MODEL_NAME, "model_version": MODEL_VERSION,
        "task_type": "physical_change_review_priority",
        "framework": "scikit-learn RandomForestClassifier",
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "features": list(FEATURE_NAMES),
        "dataset_ref": dataset_ref or dataset_path.name,
        "label_definition": "1=physical change confirmed by independent field verification; 0=no physical change on verification",
        "metrics": metrics,
        "limitations": [
            "Requires representative, independently field-verified labels.",
            "Asset-group holdout reduces spatial/entity leakage but does not replace temporal and district-level external validation.",
            "Does not infer title, ownership, statutory boundary validity, legality or encroachment.",
            "Do not deploy until an authorised reviewer approves the model card and validation report.",
        ],
        "disclaimer": DISCLAIMER,
    }
    artifact = Path(artifact_path)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    dump({"model": model, "feature_names": list(FEATURE_NAMES),
          "feature_schema_version": FEATURE_SCHEMA_VERSION, "model_card": card}, artifact)
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    return {"model_card": card, "artifact_path": str(artifact),
            "artifact_sha256": digest, "status": "EVALUATED_PENDING_APPROVAL"}


def predict(artifact_path: str | Path, expected_sha256: str, features: dict[str, float]) -> dict[str, Any]:
    """Load a model only after artifact integrity and feature-contract checks."""
    import hashlib
    from joblib import load

    path = Path(artifact_path)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected_sha256:
        raise ValueError("Model artifact SHA-256 mismatch.")
    payload = load(path)
    if payload.get("feature_schema_version") != FEATURE_SCHEMA_VERSION:
        raise ValueError("Unsupported feature schema version.")
    if payload.get("feature_names") != list(FEATURE_NAMES):
        raise ValueError("Model feature order does not match the current contract.")
    vector = [float(features[name]) for name in FEATURE_NAMES]
    probability = float(payload["model"].predict_proba([vector])[0][1])
    return {"score": round(probability * 100, 2), "score_type": "PHYSICAL_CHANGE_REVIEW_PRIORITY",
            "model_version": payload["model_card"]["model_version"],
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "disclaimer": DISCLAIMER}
