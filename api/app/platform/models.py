"""SQLAlchemy mappings for the additive statewide platform schema.

The physical schema is owned by Alembic migrations. These mappings extend the
legacy lake mappings in app.models; they do not create tables at import time.
"""
from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base

TZ = DateTime(timezone=True)
UUID_PK = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("departments.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[dt.datetime] = mapped_column(TZ, server_default=text("now()"))


class AdministrativeUnit(Base):
    __tablename__ = "administrative_units"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    code: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    unit_type: Mapped[str] = mapped_column(Text)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("administrative_units.id"))
    valid_from: Mapped[dt.date] = mapped_column(Date)
    valid_to: Mapped[dt.date | None] = mapped_column(Date)
    recorded_at: Mapped[dt.datetime] = mapped_column(TZ, server_default=text("now()"))
    source_record_ref: Mapped[str | None] = mapped_column(Text)


class PublicAsset(Base):
    __tablename__ = "public_assets"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    asset_code: Mapped[str] = mapped_column(Text, unique=True)
    display_name: Mapped[str] = mapped_column(Text)
    category_code: Mapped[str] = mapped_column(Text)
    lifecycle_status: Mapped[str] = mapped_column(Text, server_default=text("'ACTIVE'"))
    legacy_asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), unique=True)
    baseline_date: Mapped[dt.date | None] = mapped_column(Date)
    centroid = mapped_column(Geometry("POINT", srid=4326))
    footprint = mapped_column(Geometry("MULTIPOLYGON", srid=4326))
    source_authority: Mapped[str] = mapped_column(Text, server_default=text("'UNVERIFIED'"))
    source_record_ref: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(TZ, server_default=text("now()"))
    updated_at: Mapped[dt.datetime] = mapped_column(TZ, server_default=text("now()"))


class LandParcel(Base):
    __tablename__ = "land_parcels"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    state_code: Mapped[str] = mapped_column(Text, server_default=text("'TS'"))
    district_code: Mapped[str | None] = mapped_column(Text)
    mandal_code: Mapped[str | None] = mapped_column(Text)
    village_code: Mapped[str | None] = mapped_column(Text)
    survey_number: Mapped[str] = mapped_column(Text)
    subdivision_number: Mapped[str | None] = mapped_column(Text)
    land_classification: Mapped[str | None] = mapped_column(Text)
    source_authority: Mapped[str] = mapped_column(Text, server_default=text("'UNVERIFIED'"))
    source_record_ref: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[dt.date] = mapped_column(Date)
    valid_to: Mapped[dt.date | None] = mapped_column(Date)
    recorded_at: Mapped[dt.datetime] = mapped_column(TZ, server_default=text("now()"))
    footprint = mapped_column(Geometry("MULTIPOLYGON", srid=4326))


class AssetParcel(Base):
    __tablename__ = "asset_parcels"
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("public_assets.id"), primary_key=True)
    parcel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("land_parcels.id"), primary_key=True)
    overlap_area_sq_m: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    relation_type: Mapped[str] = mapped_column(Text, server_default=text("'INTERSECTS'"))
    valid_from: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    valid_to: Mapped[dt.date | None] = mapped_column(Date)


class AssetAdminLink(Base):
    __tablename__ = "asset_admin_links"
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("public_assets.id"), primary_key=True)
    administrative_unit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("administrative_units.id"), primary_key=True)
    valid_from: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    valid_to: Mapped[dt.date | None] = mapped_column(Date)


class AssetResponsibility(Base):
    __tablename__ = "asset_responsibilities"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("public_assets.id"))
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id"))
    relationship_type: Mapped[str] = mapped_column(Text)
    valid_from: Mapped[dt.date] = mapped_column(Date)
    valid_to: Mapped[dt.date | None] = mapped_column(Date)
    source_authority: Mapped[str] = mapped_column(Text)
    source_record_ref: Mapped[str] = mapped_column(Text)
    recorded_at: Mapped[dt.datetime] = mapped_column(TZ, server_default=text("now()"))


class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    source_system: Mapped[str] = mapped_column(Text)
    source_authority: Mapped[str] = mapped_column(Text)
    schema_version: Mapped[str] = mapped_column(Text)
    mapping_version: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    source_uri: Mapped[str | None] = mapped_column(Text)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    records_received: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    records_accepted: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    records_rejected: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    error_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    started_at: Mapped[dt.datetime] = mapped_column(TZ, server_default=text("now()"))
    completed_at: Mapped[dt.datetime | None] = mapped_column(TZ)


class SourceRecord(Base):
    __tablename__ = "source_records"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    batch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ingestion_batches.id"))
    source_system: Mapped[str] = mapped_column(Text)
    source_record_id: Mapped[str] = mapped_column(Text)
    authority_class: Mapped[str] = mapped_column(Text)
    source_uri: Mapped[str | None] = mapped_column(Text)
    source_version: Mapped[str | None] = mapped_column(Text)
    source_effective_at: Mapped[dt.datetime | None] = mapped_column(TZ)
    retrieved_at: Mapped[dt.datetime] = mapped_column(TZ, server_default=text("now()"))
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    validation_status: Mapped[str] = mapped_column(Text, server_default=text("'PENDING'"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))


class SatelliteScene(Base):
    __tablename__ = "satellite_scenes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    provider: Mapped[str] = mapped_column(Text)
    collection_id: Mapped[str] = mapped_column(Text)
    item_id: Mapped[str] = mapped_column(Text)
    platform: Mapped[str | None] = mapped_column(Text)
    instrument: Mapped[str | None] = mapped_column(Text)
    acquired_at: Mapped[dt.datetime] = mapped_column(TZ)
    footprint = mapped_column(Geometry("POLYGON", srid=4326))
    cloud_cover: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    gsd_m: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    license: Mapped[str] = mapped_column(Text)
    stac_item: Mapped[dict[str, Any]] = mapped_column(JSONB)
    object_uri: Mapped[str | None] = mapped_column(Text)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    suitability_status: Mapped[str] = mapped_column(Text, server_default=text("'PENDING'"))
    ingested_at: Mapped[dt.datetime] = mapped_column(TZ, server_default=text("now()"))


class ProcessingRun(Base):
    __tablename__ = "processing_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    pipeline_name: Mapped[str] = mapped_column(Text)
    pipeline_version: Mapped[str] = mapped_column(Text)
    config_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(Text)
    input_manifest: Mapped[dict[str, Any]] = mapped_column(JSONB)
    output_manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    geographic_scope = mapped_column(Geometry("GEOMETRY", srid=4326))
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), server_default=text("gen_random_uuid()"))
    attempt: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    started_at: Mapped[dt.datetime | None] = mapped_column(TZ)
    finished_at: Mapped[dt.datetime | None] = mapped_column(TZ)
    error_code: Mapped[str | None] = mapped_column(Text)
    error_detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(TZ, server_default=text("now()"))


class CandidateAssetLink(Base):
    __tablename__ = "candidate_asset_links"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    legacy_candidate_id: Mapped[int | None] = mapped_column(ForeignKey("candidates.id"))
    platform_asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("public_assets.id"))
    parcel_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("land_parcels.id"))
    boundary_id: Mapped[int | None] = mapped_column(ForeignKey("boundaries.id"))
    processing_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("processing_runs.id"))
    spatial_relation: Mapped[str] = mapped_column(Text)
    overlap_area_sq_m: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    matched_at: Mapped[dt.datetime] = mapped_column(TZ, server_default=text("now()"))


class MLModelVersion(Base):
    __tablename__ = "ml_model_versions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    model_name: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(Text)
    task_type: Mapped[str] = mapped_column(Text)
    framework: Mapped[str | None] = mapped_column(Text)
    artifact_uri: Mapped[str | None] = mapped_column(Text)
    artifact_sha256: Mapped[str | None] = mapped_column(String(64))
    feature_schema_version: Mapped[str] = mapped_column(Text)
    training_dataset_ref: Mapped[str | None] = mapped_column(Text)
    validation_report_uri: Mapped[str | None] = mapped_column(Text)
    model_card: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    status: Mapped[str] = mapped_column(Text)
    approved_by: Mapped[str | None] = mapped_column(Text)
    approved_at: Mapped[dt.datetime | None] = mapped_column(TZ)
    created_at: Mapped[dt.datetime] = mapped_column(TZ, server_default=text("now()"))


class MLEvaluation(Base):
    __tablename__ = "ml_evaluations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    model_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ml_model_versions.id"))
    evaluation_type: Mapped[str] = mapped_column(Text)
    dataset_ref: Mapped[str] = mapped_column(Text)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB)
    slice_metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    evaluated_at: Mapped[dt.datetime] = mapped_column(TZ, server_default=text("now()"))
    evaluator: Mapped[str] = mapped_column(Text)
    passed: Mapped[bool] = mapped_column(Boolean)
    notes: Mapped[str | None] = mapped_column(Text)


class UserDepartmentAccess(Base):
    __tablename__ = "user_department_access"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id"))
    access_level: Mapped[str] = mapped_column(Text)
    valid_from: Mapped[dt.date] = mapped_column(Date)
    valid_to: Mapped[dt.date | None] = mapped_column(Date)
    granted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(TZ, server_default=text("now()"))


class CandidatePrediction(Base):
    __tablename__ = "candidate_predictions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    score_type: Mapped[str] = mapped_column(Text)
    score: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    model_name: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(Text)
    feature_schema_version: Mapped[str] = mapped_column(Text)
    features: Mapped[dict[str, Any]] = mapped_column(JSONB)
    factors: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    disclaimer: Mapped[str] = mapped_column(Text)
    generated_at: Mapped[dt.datetime] = mapped_column(TZ, server_default=text("now()"))


class CandidateIngestRequest(Base):
    __tablename__ = "candidate_ingest_requests"
    idempotency_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload_sha256: Mapped[str] = mapped_column(String(64))
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    response: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[dt.datetime] = mapped_column(TZ, server_default=text("now()"))


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, server_default=text("gen_random_uuid()"))
    event_type: Mapped[str] = mapped_column(Text)
    schema_version: Mapped[str] = mapped_column(Text, server_default=text("'1.0'"))
    aggregate_type: Mapped[str] = mapped_column(Text)
    aggregate_id: Mapped[str] = mapped_column(Text)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    occurred_at: Mapped[dt.datetime] = mapped_column(TZ, server_default=text("now()"))
    published_at: Mapped[dt.datetime | None] = mapped_column(TZ)
    publish_attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    last_error: Mapped[str | None] = mapped_column(Text)
