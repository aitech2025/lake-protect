"""Governed model registry and intelligence read APIs.

Only authorised administrators may approve a model. Predictions remain advisory;
this API never turns a model score into a legal or enforcement decision.
"""
from __future__ import annotations

import json
import re
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import chain
from app.db import get_db
from app.models import User
from app.security import current_user, require_roles
from app.storage import store

router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence"])
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ModelRegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_name: str = Field(min_length=2, max_length=160)
    model_version: str = Field(min_length=1, max_length=80)
    task_type: str = Field(min_length=2, max_length=120)
    framework: str | None = Field(default=None, max_length=120)
    artifact_uri: str = Field(min_length=1, max_length=2048)
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    feature_schema_version: str = Field(min_length=1, max_length=40)
    training_dataset_ref: str | None = Field(default=None, max_length=500)
    validation_report_uri: str | None = Field(default=None, max_length=2048)
    model_card: dict[str, Any]


class EvaluationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evaluation_type: Literal["BACKTEST", "VALIDATION", "SHADOW", "DRIFT", "PRODUCTION"]
    dataset_ref: str = Field(min_length=1, max_length=500)
    metrics: dict[str, Any]
    slice_metrics: dict[str, Any] = Field(default_factory=dict)
    passed: bool
    notes: str | None = Field(default=None, max_length=4000)


@router.post("/models", status_code=201)
def register_model(
    body: ModelRegisterIn,
    actor: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    if body.model_card.get("model_name") != body.model_name or body.model_card.get("model_version") != body.model_version:
        raise HTTPException(422, "Model card name and version must match the registry fields.")
    if body.model_card.get("feature_schema_version") != body.feature_schema_version:
        raise HTTPException(422, "Model card feature schema version does not match the registry fields.")
    try:
        artifact_meta = store.head_object(body.artifact_uri)
    except Exception as exc:
        raise HTTPException(422, "Unable to inspect the model artifact in configured object storage.") from exc
    if not artifact_meta or artifact_meta.get("sha256") != body.artifact_sha256:
        raise HTTPException(422, "Model artifact is missing or its SHA-256 does not match.")
    try:
        row = db.execute(text("""
            INSERT INTO ml_model_versions
              (model_name, model_version, task_type, framework, artifact_uri, artifact_sha256,
               feature_schema_version, training_dataset_ref, validation_report_uri, model_card, status)
            VALUES
              (:model_name, :model_version, :task_type, :framework, :artifact_uri, :artifact_sha256,
               :feature_schema_version, :training_dataset_ref, :validation_report_uri,
               CAST(:model_card AS jsonb), 'REGISTERED')
            RETURNING id, model_name, model_version, status, created_at
        """), {**body.model_dump(exclude={"model_card"}), "model_card": json.dumps(body.model_card)}).mappings().one()
        chain.record(db, actor_id=actor.id, action="ml_model.registered", entity="ml_model_version",
                     entity_id=row["id"], details={"model_name": body.model_name,
                     "model_version": body.model_version, "artifact_sha256": body.artifact_sha256})
        db.commit()
        return dict(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "This model name/version is already registered or violates a registry constraint.") from exc


@router.post("/models/{model_id}/evaluations", status_code=201)
def record_evaluation(
    model_id: UUID,
    body: EvaluationCreate,
    actor: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    model = db.execute(text("""
        SELECT status FROM ml_model_versions WHERE id=:model_id FOR UPDATE
    """), {"model_id": model_id}).scalar_one_or_none()
    if model is None:
        raise HTTPException(404, "Model version not found.")
    if model in {"REJECTED", "RETIRED"}:
        raise HTTPException(409, "Evaluations cannot be added to a rejected or retired model.")
    row = db.execute(text("""
        INSERT INTO ml_evaluations
          (model_version_id, evaluation_type, dataset_ref, metrics, slice_metrics, evaluator, passed, notes)
        VALUES (:model_id, :evaluation_type, :dataset_ref, CAST(:metrics AS jsonb),
                CAST(:slice_metrics AS jsonb), :evaluator, :passed, :notes)
        RETURNING id, model_version_id, evaluation_type, passed, evaluated_at
    """), {"model_id": model_id, "evaluation_type": body.evaluation_type,
           "dataset_ref": body.dataset_ref, "metrics": json.dumps(body.metrics),
           "slice_metrics": __import__("json").dumps(body.slice_metrics),
           "evaluator": actor.username, "passed": body.passed, "notes": body.notes}).mappings().one()
    chain.record(db, actor_id=actor.id, action="ml_model.evaluated", entity="ml_model_version",
                 entity_id=model_id, details={"evaluation_id": str(row["id"]),
                 "evaluation_type": body.evaluation_type, "passed": body.passed})
    db.commit()
    return dict(row)


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
    except Exception:
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


@router.post("/models/{model_id}/promote")
def promote_model(
    model_id: UUID,
    actor: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    model = db.execute(text("""
        SELECT id, model_name, model_version, task_type, artifact_uri, artifact_sha256,
               feature_schema_version, status
        FROM ml_model_versions WHERE id=:model_id FOR UPDATE
    """), {"model_id": model_id}).mappings().first()
    if model is None:
        raise HTTPException(404, "Model version not found.")
    if model["status"] != "APPROVED":
        raise HTTPException(409, "Only an approved model can be promoted to production.")
    if model["task_type"] != "physical_change_review_priority":
        raise HTTPException(409, "No runtime inference adapter is configured for this model task.")
    if model["feature_schema_version"] != "1.0":
        raise HTTPException(409, "The model feature schema is not supported by this API version.")
    evaluation = db.execute(text("""
        SELECT passed FROM ml_evaluations
        WHERE model_version_id=:model_id
        ORDER BY evaluated_at DESC LIMIT 1
    """), {"model_id": model_id}).scalar_one_or_none()
    if evaluation is not True:
        raise HTTPException(409, "A passing latest evaluation is required for production promotion.")
    try:
        artifact_meta = store.head_object(model["artifact_uri"])
    except Exception as exc:
        raise HTTPException(409, "Unable to verify the model artifact in object storage.") from exc
    if not artifact_meta or artifact_meta.get("sha256") != model["artifact_sha256"]:
        raise HTTPException(409, "Model artifact is missing or its SHA-256 does not match.")
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:task_type))"), {"task_type": model["task_type"]})
    previous = db.execute(text("""
        SELECT id, model_name, model_version FROM ml_model_versions
        WHERE task_type=:task_type AND status='PRODUCTION' AND id<>:model_id
        FOR UPDATE
    """), {"task_type": model["task_type"], "model_id": model_id}).mappings().all()
    db.execute(text("""
        UPDATE ml_model_versions SET status='SHADOW'
        WHERE task_type=:task_type AND status='PRODUCTION' AND id<>:model_id
    """), {"task_type": model["task_type"], "model_id": model_id})
    db.execute(text("""
        UPDATE ml_model_versions SET status='PRODUCTION'
        WHERE id=:model_id
    """), {"model_id": model_id})
    chain.record(db, actor_id=actor.id, action="ml_model.promoted", entity="ml_model_version",
                 entity_id=model_id, details={"model_name": model["model_name"],
                 "model_version": model["model_version"],
                 "previous_production_models": [f"{item['model_name']}:{item['model_version']}" for item in previous]})
    db.commit()
    return {"id": str(model_id), "status": "PRODUCTION",
            "previous_models_moved_to_shadow": len(previous)}


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
