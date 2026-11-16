"""Pipeline ingestion and processing-run APIs.

Machine credentials are checked before setting transaction-local RLS context.
Inputs are metadata/provenance only; raster assets remain in object storage.
"""
from __future__ import annotations

import hmac
import json
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db

router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])

AuthorityClass = Literal["AUTHORITATIVE", "CERTIFIED", "DERIVED", "EXTERNAL", "FIELD", "MODEL", "UNVERIFIED"]


def pipeline_credential(x_pipeline_token: str | None = Header(default=None)) -> None:
    if not settings.pipeline_token:
        raise HTTPException(503, "Pipeline ingestion is disabled.")
    if not x_pipeline_token or not hmac.compare_digest(x_pipeline_token, settings.pipeline_token):
        raise HTTPException(401, "Valid pipeline credential required.")


def _pipeline_context(db: Session) -> None:
    db.execute(text("""
        SELECT set_config('lp.pipeline_ingest','true',true),
               set_config('lp.is_platform_admin','false',true),
               set_config('lp.user_id','',true)
    """))


class BatchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_system: str = Field(min_length=2, max_length=120)
    source_authority: AuthorityClass
    schema_version: str = Field(min_length=1, max_length=40)
    mapping_version: str = Field(min_length=1, max_length=40)
    source_uri: str | None = Field(default=None, max_length=2048)
    checksum_sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")


class SourceRecordCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_record_id: str = Field(min_length=1, max_length=300)
    authority_class: AuthorityClass
    source_uri: str | None = Field(default=None, max_length=2048)
    source_version: str = Field(min_length=1, max_length=120)
    source_effective_at: datetime | None = None
    checksum_sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    payload: dict[str, Any] = Field(default_factory=dict)


class SourceRecordValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    validation_status: Literal["VALID", "INVALID", "CONFLICT", "QUARANTINED"]


class SceneCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str = Field(min_length=2, max_length=80)
    collection_id: str = Field(min_length=1, max_length=160)
    item_id: str = Field(min_length=1, max_length=300)
    platform: str | None = None
    instrument: str | None = None
    acquired_at: datetime
    footprint: dict[str, Any]
    cloud_cover: float | None = Field(default=None, ge=0, le=100)
    gsd_m: float | None = Field(default=None, gt=0)
    license: str = Field(min_length=1, max_length=300)
    stac_item: dict[str, Any]
    object_uri: str | None = Field(default=None, max_length=2048)
    checksum_sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")


class ProcessingRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    pipeline_name: str = Field(min_length=1, max_length=120)
    pipeline_version: str = Field(min_length=1, max_length=80)
    config_hash: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    input_manifest: dict[str, Any]
    geographic_scope: dict[str, Any] | None = None


class ProcessingRunUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["RUNNING", "SUCCEEDED", "PARTIAL", "FAILED", "CANCELLED"]
    output_manifest: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = Field(default=None, max_length=100)
    error_detail: str | None = Field(default=None, max_length=2000)


@router.post("/batches", status_code=201, dependencies=[Depends(pipeline_credential)])
def create_batch(body: BatchCreate, db: Session = Depends(get_db)):
    _pipeline_context(db)
    row = db.execute(text("""
        INSERT INTO ingestion_batches
          (source_system, source_authority, schema_version, mapping_version, status,
           source_uri, checksum_sha256)
        VALUES (:source_system, :source_authority, :schema_version, :mapping_version,
                'RECEIVED', :source_uri, :checksum_sha256)
        RETURNING id, status, started_at
    """), body.model_dump()).mappings().one()
    db.commit()
    return dict(row)


@router.post("/batches/{batch_id}/records", status_code=201, dependencies=[Depends(pipeline_credential)])
def add_source_record(batch_id: UUID, body: SourceRecordCreate, db: Session = Depends(get_db)):
    _pipeline_context(db)
    batch = db.execute(text("""
        SELECT id, status, source_system FROM ingestion_batches WHERE id=:batch_id FOR UPDATE
    """), {"batch_id": batch_id}).mappings().first()
    if batch is None:
        raise HTTPException(404, "Ingestion batch not found.")
    if batch["status"] not in {"RECEIVED", "VALIDATING"}:
        raise HTTPException(409, "This ingestion batch no longer accepts records.")
    row = db.execute(text("""
        INSERT INTO source_records
          (batch_id, source_system, source_record_id, authority_class, source_uri,
           source_version, source_effective_at, checksum_sha256, validation_status, payload)
        SELECT :batch_id, b.source_system, :source_record_id, :authority_class, :source_uri,
               :source_version, :source_effective_at, :checksum_sha256, 'PENDING',
               CAST(:payload AS jsonb)
        FROM ingestion_batches b WHERE b.id=:batch_id
        ON CONFLICT (source_system, source_record_id, source_version) DO NOTHING
        RETURNING id, validation_status, retrieved_at
    """), {**body.model_dump(exclude={"payload"}), "batch_id": batch_id,
           "payload": json.dumps(body.payload)}).mappings().first()
    if row is None:
        existing = db.execute(text("""
            SELECT id, validation_status, retrieved_at, checksum_sha256 FROM source_records
            WHERE source_system=:source_system AND source_record_id=:source_record_id
              AND source_version IS NOT DISTINCT FROM :source_version
        """), {"source_system": batch["source_system"], "source_record_id": body.source_record_id,
               "source_version": body.source_version}).mappings().first()
        if existing and existing["checksum_sha256"] != body.checksum_sha256:
            db.rollback()
            raise HTTPException(409, "Source record ID/version already exists with a different checksum.")
        db.rollback()
        return {"duplicate": True, "record": {k: existing[k] for k in ("id", "validation_status", "retrieved_at")} if existing else None}
    db.execute(text("""
        UPDATE ingestion_batches
        SET records_received=records_received+1
        WHERE id=:batch_id
    """), {"batch_id": batch_id})
    db.commit()
    return {"duplicate": False, "record": dict(row)}


@router.patch("/batches/{batch_id}/records/{record_id}", dependencies=[Depends(pipeline_credential)])
def validate_source_record(
    batch_id: UUID,
    record_id: UUID,
    body: SourceRecordValidation,
    db: Session = Depends(get_db),
):
    _pipeline_context(db)
    record = db.execute(text("""
        SELECT validation_status FROM source_records
        WHERE id=:record_id AND batch_id=:batch_id FOR UPDATE
    """), {"record_id": record_id, "batch_id": batch_id}).mappings().first()
    if record is None:
        raise HTTPException(404, "Source record not found in this batch.")
    if record["validation_status"] != "PENDING":
        if record["validation_status"] == body.validation_status:
            return {"id": str(record_id), "validation_status": record["validation_status"], "duplicate": True}
        raise HTTPException(409, "A validated source record cannot be reclassified.")
    db.execute(text("""
        UPDATE source_records SET validation_status=:validation_status WHERE id=:record_id
    """), {"validation_status": body.validation_status, "record_id": record_id})
    counts = db.execute(text("""
        SELECT
          count(*) FILTER (WHERE validation_status='VALID') AS accepted,
          count(*) FILTER (WHERE validation_status IN ('INVALID','CONFLICT','QUARANTINED')) AS rejected,
          count(*) FILTER (WHERE validation_status='PENDING') AS pending
        FROM source_records WHERE batch_id=:batch_id
    """), {"batch_id": batch_id}).mappings().one()
    if counts["pending"] > 0:
        batch_status = "VALIDATING"
        completed_at = None
    elif counts["rejected"] == 0:
        batch_status = "ACCEPTED"
        completed_at = "now"
    elif counts["accepted"] == 0:
        batch_status = "REJECTED"
        completed_at = "now"
    else:
        batch_status = "PARTIAL"
        completed_at = "now"
    db.execute(text("""
        UPDATE ingestion_batches
        SET status=:status, records_accepted=:accepted, records_rejected=:rejected,
            completed_at=CASE WHEN :is_complete THEN now() ELSE NULL END
        WHERE id=:batch_id
    """), {"status": batch_status, "accepted": counts["accepted"],
           "rejected": counts["rejected"], "is_complete": counts["pending"] == 0,
           "batch_id": batch_id})
    db.commit()
    return {"id": str(record_id), "validation_status": body.validation_status,
            "batch_status": batch_status, "records_accepted": counts["accepted"],
            "records_rejected": counts["rejected"], "records_pending": counts["pending"]}


@router.post("/scenes", status_code=201, dependencies=[Depends(pipeline_credential)])
def register_scene(body: SceneCreate, db: Session = Depends(get_db)):
    _pipeline_context(db)
    geometry = json.dumps(body.footprint)
    valid = db.execute(text("""
        SELECT ST_IsValid(ST_SetSRID(ST_GeomFromGeoJSON(:footprint),4326))
           AND GeometryType(ST_SetSRID(ST_GeomFromGeoJSON(:footprint),4326)) = 'POLYGON'
    """), {"footprint": geometry}).scalar_one()
    if not valid:
        raise HTTPException(422, "Scene footprint must be a valid Polygon in WGS84.")
    row = db.execute(text("""
        INSERT INTO satellite_scenes
          (provider, collection_id, item_id, platform, instrument, acquired_at,
           footprint, cloud_cover, gsd_m, license, stac_item, object_uri, checksum_sha256)
        VALUES
          (:provider, :collection_id, :item_id, :platform, :instrument, :acquired_at,
           ST_SetSRID(ST_GeomFromGeoJSON(:footprint),4326), :cloud_cover, :gsd_m,
           :license, CAST(:stac_item AS jsonb), :object_uri, :checksum_sha256)
        ON CONFLICT (provider, collection_id, item_id) DO NOTHING
        RETURNING id, suitability_status, ingested_at
    """), {**body.model_dump(exclude={"footprint", "stac_item"}),
           "footprint": geometry, "stac_item": json.dumps(body.stac_item)}).mappings().first()
    if row is None:
        existing = db.execute(text("""
            SELECT id, suitability_status, ingested_at FROM satellite_scenes
            WHERE provider=:provider AND collection_id=:collection_id AND item_id=:item_id
        """), body.model_dump(include={"provider", "collection_id", "item_id"})).mappings().one()
        db.commit()
        return {"duplicate": True, "scene": dict(existing)}
    db.commit()
    return {"duplicate": False, "scene": dict(row)}


@router.post("/processing-runs", status_code=201, dependencies=[Depends(pipeline_credential)])
def create_processing_run(body: ProcessingRunCreate, db: Session = Depends(get_db)):
    _pipeline_context(db)
    scope = json.dumps(body.geographic_scope) if body.geographic_scope is not None else None
    row = db.execute(text("""
        INSERT INTO processing_runs
          (id, pipeline_name, pipeline_version, config_hash, status, input_manifest, geographic_scope)
        VALUES (:id, :pipeline_name, :pipeline_version, :config_hash, 'QUEUED',
                CAST(:input_manifest AS jsonb),
                CASE WHEN :scope IS NULL THEN NULL
                     ELSE ST_SetSRID(ST_GeomFromGeoJSON(:scope),4326) END)
        ON CONFLICT (id) DO NOTHING
        RETURNING id, status, correlation_id, created_at
    """), {"id": body.id, "pipeline_name": body.pipeline_name,
           "pipeline_version": body.pipeline_version, "config_hash": body.config_hash,
           "input_manifest": json.dumps(body.input_manifest), "scope": scope}).mappings().first()
    if row is None:
        existing = db.execute(text("""
            SELECT id, status, correlation_id, created_at, pipeline_name, pipeline_version,
                   config_hash, input_manifest
            FROM processing_runs WHERE id=:id
        """), {"id": body.id}).mappings().one()
        if (existing["pipeline_name"], existing["pipeline_version"], existing["config_hash"],
            existing["input_manifest"]) != (body.pipeline_name, body.pipeline_version,
                                             body.config_hash, body.input_manifest):
            db.rollback()
            raise HTTPException(409, "Run ID was already used for a different processing request.")
        db.commit()
        return {"duplicate": True, "run": {k: existing[k] for k in ("id", "status", "correlation_id", "created_at")}}
    db.commit()
    return {"duplicate": False, "run": dict(row)}


@router.patch("/processing-runs/{run_id}", dependencies=[Depends(pipeline_credential)])
def update_processing_run(run_id: UUID, body: ProcessingRunUpdate, db: Session = Depends(get_db)):
    _pipeline_context(db)
    current = db.execute(text("""
        SELECT status, attempt FROM processing_runs WHERE id=:run_id FOR UPDATE
    """), {"run_id": run_id}).mappings().first()
    if current is None:
        raise HTTPException(404, "Processing run not found.")
    allowed = {
        "QUEUED": {"RUNNING", "CANCELLED", "FAILED"},
        "RUNNING": {"SUCCEEDED", "PARTIAL", "FAILED", "CANCELLED"},
    }
    if body.status != current["status"] and body.status not in allowed.get(current["status"], set()):
        raise HTTPException(409, f"Invalid processing-run transition {current['status']} -> {body.status}.")
    row = db.execute(text("""
        UPDATE processing_runs
        SET status=:status,
            output_manifest=CAST(:output_manifest AS jsonb),
            error_code=:error_code, error_detail=:error_detail,
            attempt=attempt + CASE WHEN :status='RUNNING' AND status='QUEUED' THEN 1 ELSE 0 END,
            started_at=CASE WHEN :status='RUNNING' AND started_at IS NULL THEN now() ELSE started_at END,
            finished_at=CASE WHEN :status IN ('SUCCEEDED','PARTIAL','FAILED','CANCELLED') AND finished_at IS NULL THEN now() ELSE finished_at END
        WHERE id=:run_id
        RETURNING id, status, attempt, started_at, finished_at, error_code
    """), {"status": body.status, "output_manifest": json.dumps(body.output_manifest),
           "error_code": body.error_code, "error_detail": body.error_detail,
           "run_id": run_id}).mappings().one()
    db.commit()
    return dict(row)
