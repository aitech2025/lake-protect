"""ORM models for the section 7 data model. The schema itself lives in the migrations."""
from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

from geoalchemy2 import Geometry
from sqlalchemy import ARRAY, BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app import enums


def pg_enum(enum_cls, name: str) -> ENUM:
    return ENUM(*[e.value for e in enum_cls], name=name, create_type=False)


COHORT = pg_enum(enums.Cohort, "cohort")
ASSET_TYPE = pg_enum(enums.AssetType, "asset_type")
BOUNDARY_KIND = pg_enum(enums.BoundaryKind, "boundary_kind")
BOUNDARY_STATUS = pg_enum(enums.BoundaryStatus, "boundary_status")
ZONE = pg_enum(enums.Zone, "zone")
CHANGE_TYPE = pg_enum(enums.ChangeType, "change_type")
STAGE = pg_enum(enums.Stage, "stage")
SENSOR_BASIS = pg_enum(enums.SensorBasis, "sensor_basis")
ALERT_CLASS = pg_enum(enums.AlertClass, "alert_class")
MODE = pg_enum(enums.Mode, "mode")
ALERT_STATE = pg_enum(enums.AlertState, "alert_state")
FIELD_OUTCOME = pg_enum(enums.FieldOutcome, "field_outcome")
ROLE = pg_enum(enums.Role, "role")
READINESS_STATUS = pg_enum(enums.ReadinessStatus, "readiness_status")

MULTIPOLYGON = Geometry("MULTIPOLYGON", srid=4326, spatial_index=False)
TZ = DateTime(timezone=True)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(ROLE)
    language: Mapped[str] = mapped_column(Text, default="en")
    area_geom = mapped_column(MULTIPOLYGON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    asset_key: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    name_te: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(ASSET_TYPE)
    cohort: Mapped[str] = mapped_column(COHORT)
    district: Mapped[str | None] = mapped_column(Text)
    mandal: Mapped[str | None] = mapped_column(Text)
    village: Mapped[str | None] = mapped_column(Text)
    survey_numbers: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    area_acres: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    custodian_agency: Mapped[str | None] = mapped_column(Text)
    has_cctv: Mapped[bool | None] = mapped_column(Boolean)
    baseline_date: Mapped[dt.date] = mapped_column(Date)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)


class Boundary(Base):
    """Append-only. Never update a row: add a new version instead (invariant 12)."""

    __tablename__ = "boundaries"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    version: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(BOUNDARY_KIND)
    status: Mapped[str] = mapped_column(BOUNDARY_STATUS)
    geom = mapped_column(MULTIPOLYGON)
    source_name: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_date: Mapped[dt.date | None] = mapped_column(Date)
    notification_ref: Mapped[str | None] = mapped_column(Text)
    certified_by: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[dt.date] = mapped_column(Date)
    valid_to: Mapped[dt.date | None] = mapped_column(Date)
    supersedes_id: Mapped[int | None] = mapped_column(ForeignKey("boundaries.id"))
    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("boundaries.id"))
    sha256: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[dt.datetime] = mapped_column(TZ, server_default="now()")


class Observation(Base):
    __tablename__ = "observations"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sensor: Mapped[str] = mapped_column(Text)
    scene_id: Mapped[str] = mapped_column(Text)
    acquired_at: Mapped[dt.datetime] = mapped_column(TZ)
    cloud_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    stac_href: Mapped[str | None] = mapped_column(Text)
    processing_version: Mapped[str | None] = mapped_column(Text)
    licence_notice: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str | None] = mapped_column(String(64))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class Candidate(Base):
    """No owner fields, by design (rule 4)."""

    __tablename__ = "candidates"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    boundary_id: Mapped[int] = mapped_column(ForeignKey("boundaries.id"))
    geom = mapped_column(MULTIPOLYGON)
    area_sq_m: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    change_type: Mapped[str] = mapped_column(CHANGE_TYPE)
    stage_estimate: Mapped[str | None] = mapped_column(STAGE)
    last_clear_at: Mapped[dt.date | None] = mapped_column(Date)
    first_changed_at: Mapped[dt.date] = mapped_column(Date)
    observation_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), default=list)
    sensor_basis: Mapped[str] = mapped_column(SENSOR_BASIS)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    rule_version: Mapped[str] = mapped_column(Text)
    flags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    before_chip: Mapped[str | None] = mapped_column(Text)
    after_chip: Mapped[str | None] = mapped_column(Text)
    area_growth: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    created_at: Mapped[dt.datetime] = mapped_column(TZ, server_default="now()")


class Permit(Base):
    __tablename__ = "permits"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str] = mapped_column(Text)
    ref: Mapped[str] = mapped_column(Text)
    geom = mapped_column(MULTIPOLYGON)
    kind: Mapped[str] = mapped_column(Text)
    valid_from: Mapped[dt.date] = mapped_column(Date)
    valid_to: Mapped[dt.date | None] = mapped_column(Date)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class AuthorisedWork(Base):
    __tablename__ = "authorised_works"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    agency: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    ref: Mapped[str] = mapped_column(Text)
    geom = mapped_column(MULTIPOLYGON)
    starts_on: Mapped[dt.date] = mapped_column(Date)
    ends_on: Mapped[dt.date | None] = mapped_column(Date)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class CourtCase(Base):
    __tablename__ = "court_cases"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    court: Mapped[str] = mapped_column(Text)
    case_no: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"))
    survey_numbers: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    geom = mapped_column(MULTIPOLYGON, nullable=True)
    next_hearing: Mapped[dt.date | None] = mapped_column(Date)
    last_checked_at: Mapped[dt.datetime | None] = mapped_column(TZ)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class LegalCheck(Base):
    __tablename__ = "legal_checks"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    zone: Mapped[str] = mapped_column(ZONE)
    boundary_status: Mapped[str] = mapped_column(BOUNDARY_STATUS)
    mode: Mapped[str] = mapped_column(MODE)
    alert_class: Mapped[str] = mapped_column(ALERT_CLASS)
    result: Mapped[str] = mapped_column(ALERT_STATE)
    matched_permit_id: Mapped[int | None] = mapped_column(ForeignKey("permits.id"))
    matched_work_id: Mapped[int | None] = mapped_column(ForeignKey("authorised_works.id"))
    matched_court_case_id: Mapped[int | None] = mapped_column(ForeignKey("court_cases.id"))
    boundary_id: Mapped[int] = mapped_column(ForeignKey("boundaries.id"))
    boundary_version: Mapped[int] = mapped_column(Integer)
    flags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    rule_version: Mapped[str] = mapped_column(Text)
    checked_at: Mapped[dt.datetime] = mapped_column(TZ)


class Alert(Base):
    """`state` changes only through app.workflow.state_machine (section 6.5). No owner fields."""

    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), unique=True)
    state: Mapped[str] = mapped_column(ALERT_STATE)
    priority_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    priority_factors: Mapped[dict] = mapped_column(JSONB, default=dict)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    due_at: Mapped[dt.datetime | None] = mapped_column(TZ)
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    reopened_count: Mapped[int] = mapped_column(Integer, default=0)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(TZ)
    updated_at: Mapped[dt.datetime] = mapped_column(TZ)


class ClosureRequest(Base):
    __tablename__ = "closure_requests"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"))
    from_state: Mapped[str] = mapped_column(ALERT_STATE)
    to_state: Mapped[str] = mapped_column(ALERT_STATE)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text)
    reason_code: Mapped[str | None] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    requested_at: Mapped[dt.datetime] = mapped_column(TZ)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[dt.datetime | None] = mapped_column(TZ)
    resolution: Mapped[str | None] = mapped_column(Text)


class FieldCheck(Base):
    __tablename__ = "field_checks"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"))
    officer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    client_uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True)
    observed_at: Mapped[dt.datetime] = mapped_column(TZ)
    lat: Mapped[float | None]
    lon: Mapped[float | None]
    gps_accuracy_m: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    distance_to_candidate_m: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    outcome: Mapped[str] = mapped_column(FIELD_OUTCOME)
    observed_stage: Mapped[str | None] = mapped_column(STAGE)
    notes: Mapped[str | None] = mapped_column(Text)
    photo_paths: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    photo_sha256: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    device_time: Mapped[dt.datetime | None] = mapped_column(TZ)
    synced_at: Mapped[dt.datetime] = mapped_column(TZ)


class OwnerClaim(Base):
    __tablename__ = "owner_claims"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"))
    claim_type: Mapped[str] = mapped_column(Text)
    claimant_name: Mapped[str] = mapped_column(Text)
    document_ref: Mapped[str | None] = mapped_column(Text)
    entered_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    entered_at: Mapped[dt.datetime] = mapped_column(TZ)


class ReadinessItem(Base):
    __tablename__ = "readiness_items"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"))
    item_key: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(READINESS_STATUS)
    evidence_ref: Mapped[str | None] = mapped_column(Text)
    checked_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    checked_at: Mapped[dt.datetime] = mapped_column(TZ)


class EvidencePack(Base):
    """Append-only: regenerating a pack adds a version (section 9.3)."""

    __tablename__ = "evidence_packs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"))
    version: Mapped[int] = mapped_column(Integer)
    pdf_path: Mapped[str] = mapped_column(Text)
    zip_path: Mapped[str] = mapped_column(Text)
    manifest_sha256: Mapped[str] = mapped_column(String(64))
    generated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    generated_at: Mapped[dt.datetime] = mapped_column(TZ)
    counsel_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)


class OfficerRecord(Base):
    __tablename__ = "officer_records"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"))
    officer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    notice_ref: Mapped[str | None] = mapped_column(Text)
    notice_date: Mapped[dt.date | None] = mapped_column(Date)
    hearing_date: Mapped[dt.date | None] = mapped_column(Date)
    order_ref: Mapped[str | None] = mapped_column(Text)
    order_date: Mapped[dt.date | None] = mapped_column(Date)
    action_date: Mapped[dt.date | None] = mapped_column(Date)
    action_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(TZ)


class ImageryRequest(Base):
    __tablename__ = "imagery_requests"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"))
    provider: Mapped[str] = mapped_column(Text)
    area_sq_km: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    est_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(Text, default="recorded")
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(TZ)


class Signal(Base):
    __tablename__ = "signals"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    kind: Mapped[str] = mapped_column(Text)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"))
    geom = mapped_column(Geometry("GEOMETRY", srid=4326, spatial_index=False), nullable=True)
    received_at: Mapped[dt.datetime] = mapped_column(TZ)
    ref: Mapped[str | None] = mapped_column(Text)
    linked_alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id"))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(Base):
    """Append-only hash chain. Write only through app.audit.chain.record."""

    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(Text)
    entity: Mapped[str] = mapped_column(Text)
    entity_id: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    at: Mapped[dt.datetime] = mapped_column(TZ)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)


class Bulletin(Base):
    __tablename__ = "bulletins"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    month: Mapped[str] = mapped_column(String(7))
    stats: Mapped[dict] = mapped_column(JSONB)
    pdf_path: Mapped[str | None] = mapped_column(Text)
    generated_at: Mapped[dt.datetime] = mapped_column(TZ)
    scope_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
