"""Runtime model selection with verified artifacts and deterministic fallback."""
from __future__ import annotations

import hashlib
import io
import logging
from functools import lru_cache

from joblib import load
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.storage import store
from lake_protect.intelligence.features import CandidateFeatures, FEATURE_NAMES, FEATURE_SCHEMA_VERSION
from lake_protect.intelligence.triage import TriageResult, baseline_triage

logger = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def _load_production_artifact(artifact_uri: str, expected_sha256: str):
    """Cache only hash-verified immutable object versions."""
    data = store.get_object(artifact_uri)
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256:
        raise ValueError("Production model artifact SHA-256 mismatch.")
    payload = load(io.BytesIO(data))
    if payload.get("feature_schema_version") != FEATURE_SCHEMA_VERSION:
        raise ValueError("Production model feature schema is incompatible.")
    if payload.get("feature_names") != list(FEATURE_NAMES):
        raise ValueError("Production model feature order is incompatible.")
    card = payload.get("model_card") or {}
    if card.get("feature_schema_version") != FEATURE_SCHEMA_VERSION:
        raise ValueError("Production model card feature schema is incompatible.")
    return payload


def score_review_priority(db: Session, features: CandidateFeatures) -> TriageResult:
    """Use the single promoted production model; fall back transparently if none is deployed."""
    features.validate()
    baseline = baseline_triage(features)
    model = db.execute(text("""
        SELECT model_name, model_version, artifact_uri, artifact_sha256, feature_schema_version
        FROM ml_model_versions
        WHERE task_type='physical_change_review_priority' AND status='PRODUCTION'
        ORDER BY approved_at DESC, created_at DESC
        LIMIT 1
    """)).mappings().first()
    if model is None:
        return baseline
    try:
        if model["feature_schema_version"] != FEATURE_SCHEMA_VERSION:
            raise ValueError("Registry feature schema version is incompatible.")
        payload = _load_production_artifact(model["artifact_uri"], model["artifact_sha256"])
        vector = features.to_vector()
        probability = float(payload["model"].predict_proba([vector])[0][1])
        if not 0 <= probability <= 1:
            raise ValueError("Model returned a probability outside [0,1].")
        return TriageResult(
            score=round(probability * 100, 2),
            method=model["model_name"],
            model_version=model["model_version"],
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            factors={
                "physical_change_probability": round(probability, 6),
                "decision_threshold": 0.5,
                **{f"feature_importance_{name}": float(value)
                   for name, value in zip(FEATURE_NAMES, payload["model"].feature_importances_)},
            },
            disclaimer="Physical-change review priority only; not an ownership, legality, or encroachment finding.",
        )
    except Exception:
        logger.exception("Production model inference failed; using transparent baseline fallback",
                         extra={"model_name": model["model_name"], "model_version": model["model_version"]})
        return TriageResult(
            score=baseline.score,
            method=baseline.method,
            model_version=baseline.model_version,
            feature_schema_version=baseline.feature_schema_version,
            factors={**baseline.factors, "production_model_fallback": 1.0},
            disclaimer=baseline.disclaimer,
        )
