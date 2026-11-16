"""Governed model registry and intelligence read APIs.

Only authorised administrators may approve a model. Predictions remain advisory;
this API never turns a model score into a legal or enforcement decision.
"""
from __future__ import annotations

import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit import chain
from app.db import get_db
from app.models import User
from app.security import current_user, require_roles
from app.storage import store

router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence"])
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@router.get("/models")
def list_models(
    _: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    rows = db.execute(text("""
        SELECT id, model_name, model_version, task_type, framework,
               feature_schema_version, status, artifact_sha256,
               validation_report_uri, model_card, created_at, approved_at
        FROM ml_model_versions
        ORDER BY created_at DESC
        LIMIT 200
    """)).mappings()
    return {"items": [dict(row) for row in rows]}


@router.get("/evaluations")
def list_evaluations(
    model_version_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    _: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    rows = db.execute(text("""
        SELECT e.id, e.model_version_id, e.evaluation_type, e.dataset_ref,
               e.metrics, e.slice_metrics, e.evaluated_at, e.evaluator, e.passed, e.notes
        FROM ml_evaluations e
        WHERE (:model_id IS NULL OR e.model_version_id = :model_id)
        ORDER BY e.evaluated_at DESC
        LIMIT :limit
    """), {"model_id": model_version_id, "limit": limit}).mappings()
    return {"items": [dict(row) for row in rows]}


@router.get("/processing-runs")
def list_processing_runs(
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    _: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    rows = db.execute(text("""
        SELECT id, pipeline_name, pipeline_version, status, input_manifest,
               output_manifest, correlation_id, attempt, started_at, finished_at,
               error_code, created_at
        FROM processing_runs
        WHERE (:status IS NULL OR status = :status)
        ORDER BY created_at DESC LIMIT :limit
    """), {"status": status, "limit": limit}).mappings()
    return {"items": [dict(row) for row in rows]}


@router.post("/models/{model_id}/approve")
def approve_model(
    model_id: UUID,
    actor: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    model = db.execute(text("""
        SELECT id, model_name, model_version, artifact_uri, artifact_sha256,
               feature_schema_version, status, model_card
        FROM ml_model_versions WHERE id = :model_id FOR UPDATE
    """), {"model_id": model_id}).mappings().first()
    if model is None:
        raise HTTPException(404, "Model version not found.")
    if not model["artifact_uri"] or not model["artifact_sha256"] or not _SHA256.fullmatch(model["artifact_sha256"]):
        raise HTTPException(409, "Model artifact URI and SHA-256 are required before approval.")
    if model["status"] == "APPROVED":
        return {"id": str(model_id), "status": "APPROVED", "already_approved": True}
    if model["status"] not in {"REGISTERED", "VALIDATING"}:
        raise HTTPException(409, f"Model status {model['status']} cannot be approved.")
    try:
        artifact_meta = store.head_object(model["artifact_uri"])
    except (OSError, ValueError):
        artifact_meta = None
    if not artifact_meta or artifact_meta.get("sha256") != model["artifact_sha256"]:
        raise HTTPException(409, "Stored model artifact is missing or its SHA-256 metadata does not match.")
    evaluation = db.execute(text("""
        SELECT passed, metrics FROM ml_evaluations
        WHERE model_version_id = :model_id
        ORDER BY evaluated_at DESC LIMIT 1
    """), {"model_id": model_id}).mappings().first()
    if evaluation is None or not evaluation["passed"]:
        raise HTTPException(409, "A passing, recorded evaluation is required before approval.")
    db.execute(text("""
        UPDATE ml_model_versions
        SET status = 'APPROVED', approved_by = :approver, approved_at = now()
        WHERE id = :model_id
    """), {"approver": actor.username, "model_id": model_id})
    chain.record(db, actor_id=actor.id, action="ml_model.approved", entity="ml_model_version",
                 entity_id=model_id, details={"model_name": model["model_name"],
                 "model_version": model["model_version"], "artifact_sha256": model["artifact_sha256"]})
    db.commit()
    return {"id": str(model_id), "status": "APPROVED", "approved_by": actor.username}


@router.get("/candidates/{candidate_id}/predictions")
def candidate_predictions(
    candidate_id: int,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    rows = db.execute(text("""
        SELECT id, candidate_id, score_type, score, model_name, model_version,
               feature_schema_version, features, factors, disclaimer, generated_at
        FROM candidate_predictions
        WHERE candidate_id = :candidate_id
        ORDER BY generated_at DESC
    """), {"candidate_id": candidate_id}).mappings().all()
    if not rows:
        raise HTTPException(404, "No prediction is available in your authorised scope.")
    return {"items": [dict(row) for row in rows]}
