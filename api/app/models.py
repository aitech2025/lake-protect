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
INCIDENT_STATE = pg_enum(enums.IncidentState, "incident_state")
FIELD_OUTCOME = pg_enum(enums.FieldOutcome, "field_outcome")
ROLE = pg_enum(enums.Role, "role")
NOTIFICATION_KIND = pg_enum(enums.NotificationKind, "notification_kind")
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
    # Work contact details and channels (migration 0007). Only the admin sees or changes them.
    email: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    channels: Mapped[list[str]] = mapped_column(ARRAY(Text), default=lambda: ["in_app", "email"])


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
    # Migration 0008: whether the weekly screen watches it (changed only through MonitoringChange),
    # and who added it by hand.
    monitored: Mapped[bool] = mapped_column(Boolean, server_default="true")
    added_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    added_at: Mapped[dt.datetime | None] = mapped_column(TZ)


class MonitoringChange(Base):
    """Append-only. Inserting a row starts or stops the weekly watch of its asset (migration 0008)."""

    __tablename__ = "monitoring_changes"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    monitored: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    at: Mapped[dt.datetime] = mapped_column(TZ, server_default="now()")


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
    # Migration 0005: the file it came from, and how far its lines may be off on the ground.
    source_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("source_snapshots.id"))
    positional_accuracy_m: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))


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
    """An incident. `state` changes only through app.workflow.incidents (migration 0006). No owner fields."""

    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True)
    # Migration 0010: 'satellite' or 'citizen', and the report a citizen incident came from (D-063).
    origin: Mapped[str] = mapped_column(Text, server_default="satellite")
    report_id: Mapped[int | None] = mapped_column(ForeignKey("citizen_reports.id"))
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), unique=True)
    state: Mapped[str] = mapped_column(INCIDENT_STATE)
    resolution: Mapped[str | None] = mapped_column(Text)
    closed_at: Mapped[dt.datetime | None] = mapped_column(TZ)
    related_alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id"))
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


class AssetInspection(Base):
    """Append-only field visit evidence attached directly to an asset."""
    __tablename__ = "asset_inspections"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id"))
    inspector_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    observed_at: Mapped[dt.datetime] = mapped_column(TZ)
    lat: Mapped[float | None]
    lon: Mapped[float | None]
    outcome: Mapped[str] = mapped_column(FIELD_OUTCOME)
    notes: Mapped[str] = mapped_column(Text)
    photo_paths: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    photo_sha256: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    created_at: Mapped[dt.datetime] = mapped_column(TZ, default=lambda: dt.datetime.now(dt.timezone.utc))


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
    # Migration 0011: an official's request, then the admin's approval or refusal (D-064).
    note: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[dt.datetime | None] = mapped_column(TZ)
    decision_note: Mapped[str | None] = mapped_column(Text)


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


class ScreenRun(Base):
    """One run of the weekly screen from space (migration 0004). Append-only."""

    __tablename__ = "screen_runs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    as_of: Mapped[dt.date] = mapped_column(Date)
    rule_version: Mapped[str] = mapped_column(Text)
    rules_sha256: Mapped[str] = mapped_column(String(64))
    collection: Mapped[str] = mapped_column(Text)
    started_at: Mapped[dt.datetime] = mapped_column(TZ)
    finished_at: Mapped[dt.datetime] = mapped_column(TZ)
    received_at: Mapped[dt.datetime] = mapped_column(TZ, server_default="now()")
    assets_total: Mapped[int] = mapped_column(Integer)
    outcomes: Mapped[dict] = mapped_column(JSONB, default=dict)


class AssetScreen(Base):
    """Coverage of one asset in one run: never "no encroachment", only what was observed."""

    __tablename__ = "asset_screens"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("screen_runs.id"))
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    status: Mapped[str] = mapped_column(Text)
    looks: Mapped[int] = mapped_column(Integer)
    first_look: Mapped[dt.date | None] = mapped_column(Date)
    last_look: Mapped[dt.date | None] = mapped_column(Date)
    candidates: Mapped[int] = mapped_column(Integer, default=0)
    legacy_changes: Mapped[int] = mapped_column(Integer, default=0)
    counts: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Migration 0006: the week, that week's image of the asset, and what changed.
    week: Mapped[str | None] = mapped_column(Text)
    image_key: Mapped[str | None] = mapped_column(Text)
    image_date: Mapped[dt.date | None] = mapped_column(Date)
    image_scene_id: Mapped[str | None] = mapped_column(Text)
    changes: Mapped[list] = mapped_column(JSONB, default=list)


class SourceSnapshot(Base):
    """One file received from a government source (migration 0005). Append-only."""

    __tablename__ = "source_snapshots"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    connector: Mapped[str] = mapped_column(Text)
    agency: Mapped[str] = mapped_column(Text)
    dataset: Mapped[str] = mapped_column(Text)
    transport: Mapped[str] = mapped_column(Text)
    file_name: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(Text)
    received_sha256: Mapped[str] = mapped_column(String(64))
    sha256: Mapped[str] = mapped_column(String(64))
    byte_size: Mapped[int] = mapped_column(BigInteger)
    storage_key: Mapped[str] = mapped_column(Text)
    source_date: Mapped[dt.date] = mapped_column(Date)
    reference: Mapped[str | None] = mapped_column(Text)
    agreement_ref: Mapped[str | None] = mapped_column(Text)
    licence_note: Mapped[str] = mapped_column(Text)
    is_sample: Mapped[bool] = mapped_column(Boolean)
    stripped_fields: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    received_at: Mapped[dt.datetime] = mapped_column(TZ, server_default="now()")
    received_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class ImportRun(Base):
    """One run of the asset creation engine, with what it did to each record. Append-only."""

    __tablename__ = "import_runs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    connector: Mapped[str] = mapped_column(Text)
    transport: Mapped[str] = mapped_column(Text)
    is_sample: Mapped[bool] = mapped_column(Boolean)
    started_at: Mapped[dt.datetime] = mapped_column(TZ)
    finished_at: Mapped[dt.datetime] = mapped_column(TZ)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    snapshot_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), default=list)
    counts: Mapped[dict] = mapped_column(JSONB, default=dict)
    items: Mapped[list] = mapped_column(JSONB, default=list)


class AssetSourceLink(Base):
    """The ID a department uses for an asset (the crosswalk). Append-only."""

    __tablename__ = "asset_source_links"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    connector: Mapped[str] = mapped_column(Text)
    external_id: Mapped[str] = mapped_column(Text)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("source_snapshots.id"))
    matched_by: Mapped[str] = mapped_column(Text)
    linked_at: Mapped[dt.datetime] = mapped_column(TZ, server_default="now()")


class LandParcel(Base):
    """A survey-number parcel with its land category. No owner fields, by design (17.10)."""

    __tablename__ = "land_parcels"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("source_snapshots.id"))
    district: Mapped[str] = mapped_column(Text)
    mandal: Mapped[str] = mapped_column(Text)
    village: Mapped[str] = mapped_column(Text)
    survey_no: Mapped[str] = mapped_column(Text)
    sub_division: Mapped[str] = mapped_column(Text, default="")
    bhudhaar: Mapped[str | None] = mapped_column(Text)
    land_category: Mapped[str] = mapped_column(Text)
    recorded_category: Mapped[str | None] = mapped_column(Text)
    extent_acres: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    positional_accuracy_m: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    geom = mapped_column(MULTIPOLYGON)
    is_sample: Mapped[bool] = mapped_column(Boolean)


class IncidentReview(Base):
    """A viewer's review of an incident (migration 0006). Append-only."""

    __tablename__ = "incident_reviews"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"))
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    outcome: Mapped[str] = mapped_column(Text)
    note: Mapped[str] = mapped_column(Text)
    reviewed_at: Mapped[dt.datetime] = mapped_column(TZ)


class AssetDocument(Base):
    """A legal document tagged to an asset: a file with its hash, or a reference (0006). Append-only."""

    __tablename__ = "asset_documents"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    doc_type: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    reference: Mapped[str | None] = mapped_column(Text)
    issued_on: Mapped[dt.date | None] = mapped_column(Date)
    issued_by: Mapped[str | None] = mapped_column(Text)
    file_key: Mapped[str | None] = mapped_column(Text)
    file_name: Mapped[str | None] = mapped_column(Text)
    content_type: Mapped[str | None] = mapped_column(Text)
    sha256: Mapped[str | None] = mapped_column(String(64))
    byte_size: Mapped[int | None] = mapped_column(BigInteger)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("source_snapshots.id"))
    supersedes_id: Mapped[int | None] = mapped_column(ForeignKey("asset_documents.id"))
    added_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    added_at: Mapped[dt.datetime] = mapped_column(TZ, server_default="now()")
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id"))  # migration 0011: attached to an incident
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class OfficialArea(Base):
    """A district, or a mandal within one, that an official covers (migration 0007)."""

    __tablename__ = "official_areas"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    district: Mapped[str] = mapped_column(Text)
    mandal: Mapped[str | None] = mapped_column(Text)
    added_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    added_at: Mapped[dt.datetime] = mapped_column(TZ)


class Notification(Base):
    """One notification to one person (0007). Kept for good; only its acknowledgement can be set, once."""

    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(NOTIFICATION_KIND)
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id"))
    report_id: Mapped[int | None] = mapped_column(ForeignKey("citizen_reports.id"))  # migration 0009
    week: Mapped[str | None] = mapped_column(Text)
    about_id: Mapped[int | None] = mapped_column(ForeignKey("notifications.id"))
    subject: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    needs_ack: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[dt.datetime] = mapped_column(TZ)
    acknowledged_at: Mapped[dt.datetime | None] = mapped_column(TZ)
    ack_via: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class NotificationDelivery(Base):
    """One attempt to deliver a notification on an outside channel (0007). Append-only."""

    __tablename__ = "notification_deliveries"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    notification_id: Mapped[int] = mapped_column(ForeignKey("notifications.id"))
    channel: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    to_masked: Mapped[str | None] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)
    at: Mapped[dt.datetime] = mapped_column(TZ)


# Citizen reports (migration 0009, DECISIONS.md D-062) -------------------------------------------
class CitizenReport(Base):
    __tablename__ = "citizen_reports"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ref: Mapped[str] = mapped_column(Text, unique=True)
    channel: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(Text, default="en")
    what: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    geom = mapped_column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)
    location_text: Mapped[str | None] = mapped_column(Text)
    photos: Mapped[list] = mapped_column(JSONB, default=list)
    reporter_name: Mapped[str | None] = mapped_column(Text)
    reporter_phone: Mapped[str | None] = mapped_column(Text)
    phone_verified_via: Mapped[str | None] = mapped_column(Text)
    wants_updates: Mapped[bool] = mapped_column(Boolean, default=False)
    source_ref: Mapped[str | None] = mapped_column(Text)
    entered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"))
    zone: Mapped[str | None] = mapped_column(Text)
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id"))
    duplicate_of: Mapped[int | None] = mapped_column(ForeignKey("citizen_reports.id"))
    status: Mapped[str] = mapped_column(Text, default="RECEIVED")
    closed_reason: Mapped[str | None] = mapped_column(Text)
    false_report: Mapped[bool] = mapped_column(Boolean, default=False)
    flags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    source_hash: Mapped[str] = mapped_column(Text)
    placed_by: Mapped[str | None] = mapped_column(Text)  # migration 0010: pin, description or official
    candidate_asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_assets.id"))
    contact_purged_at: Mapped[dt.datetime | None] = mapped_column(TZ)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(TZ)
    updated_at: Mapped[dt.datetime] = mapped_column(TZ)


class CandidateAsset(Base):
    """An unverified location from citizen intelligence, separate from registered Assets."""
    __tablename__ = "candidate_assets"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    candidate_code: Mapped[str] = mapped_column(Text, unique=True)
    source_report_id: Mapped[int] = mapped_column(ForeignKey("citizen_reports.id"), unique=True)
    support_asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), unique=True)
    detection_candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), unique=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"), unique=True)
    display_name: Mapped[str] = mapped_column(Text)
    category_hint: Mapped[str] = mapped_column(Text)
    district: Mapped[str | None] = mapped_column(Text)
    mandal: Mapped[str | None] = mapped_column(Text)
    village: Mapped[str | None] = mapped_column(Text)
    footprint = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)
    status: Mapped[str] = mapped_column(Text, default="PENDING_VERIFICATION")
    provenance: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(TZ)
    updated_at: Mapped[dt.datetime] = mapped_column(TZ)


class CitizenReportEvent(Base):
    """Append-only. `public_note` is {en, te, ur}: what the citizen sees."""

    __tablename__ = "citizen_report_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("citizen_reports.id"))
    kind: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    public_note: Mapped[dict] = mapped_column(JSONB)
    internal_note: Mapped[str | None] = mapped_column(Text)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    at: Mapped[dt.datetime] = mapped_column(TZ)


class CitizenChat(Base):
    __tablename__ = "citizen_chats"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    wa_hash: Mapped[str] = mapped_column(Text)
    wa_id: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text)
    draft: Mapped[dict] = mapped_column(JSONB, default=dict)
    report_id: Mapped[int | None] = mapped_column(ForeignKey("citizen_reports.id"))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[dt.datetime] = mapped_column(TZ)


class CitizenMessage(Base):
    """Append-only: every message to or from a citizen on SMS or WhatsApp, address masked."""

    __tablename__ = "citizen_messages"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    report_id: Mapped[int | None] = mapped_column(ForeignKey("citizen_reports.id"))
    chat_id: Mapped[int | None] = mapped_column(ForeignKey("citizen_chats.id"))
    direction: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(Text)
    to_masked: Mapped[str | None] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    retry_of: Mapped[int | None] = mapped_column(ForeignKey("citizen_messages.id"))
    detail: Mapped[str | None] = mapped_column(Text)
    provider_message_id: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    at: Mapped[dt.datetime] = mapped_column(TZ)


class CitizenOtp(Base):
    __tablename__ = "citizen_otps"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    phone_hash: Mapped[str] = mapped_column(Text)
    code_hash: Mapped[str] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[dt.datetime] = mapped_column(TZ)
    verified_at: Mapped[dt.datetime | None] = mapped_column(TZ)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(TZ)


class SatelliteReview(Base):
    """The satellite look at a citizen incident's place (migration 0010, DECISIONS.md D-063)."""

    __tablename__ = "satellite_reviews"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"), unique=True)
    status: Mapped[str] = mapped_column(Text, default="pending")
    result: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    requested_at: Mapped[dt.datetime] = mapped_column(TZ)
    done_at: Mapped[dt.datetime | None] = mapped_column(TZ)
    as_of: Mapped[dt.date | None] = mapped_column(Date)
    before_date: Mapped[dt.date | None] = mapped_column(Date)
    after_date: Mapped[dt.date | None] = mapped_column(Date)
    scenes: Mapped[list] = mapped_column(JSONB, default=list)
    before_chip: Mapped[str | None] = mapped_column(Text)
    after_chip: Mapped[str | None] = mapped_column(Text)
    change_type: Mapped[str | None] = mapped_column(Text)
    change_area_sq_m: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    first_changed_at: Mapped[dt.date | None] = mapped_column(Date)
    detail: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    # Migration 0011: 'automatic' (when the report arrives) or 'requested' by an official, for the
    # latest image or a past date.
    kind: Mapped[str] = mapped_column(Text, server_default="automatic")
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    look_date: Mapped[dt.date | None] = mapped_column(Date)


class IncidentNote(Base):
    """Append-only: an official's acknowledgement or note on an incident (migration 0011)."""

    __tablename__ = "incident_notes"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    at: Mapped[dt.datetime] = mapped_column(TZ)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class IncidentLegalRecord(Base):
    """Append-only: the legal records at an incident's place, as they stood when attached (migration 0011)."""

    __tablename__ = "incident_legal_records"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"))
    attached_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    at: Mapped[dt.datetime] = mapped_column(TZ)
    records: Mapped[dict] = mapped_column(JSONB)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class SatelliteSource(Base):
    """A satellite image source the admin maintains (migration 0013, D-066)."""
    __tablename__ = "satellite_sources"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    key: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text)
    purpose: Mapped[str] = mapped_column(Text)
    resolution_m: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    revisit_days: Mapped[Decimal | None] = mapped_column(Numeric(6, 1))
    stac_url: Mapped[str | None] = mapped_column(Text)
    collection: Mapped[str | None] = mapped_column(Text)
    max_scene_cloud_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    price_usd_per_sq_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    min_order_sq_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    licence_notice: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    added_at: Mapped[dt.datetime] = mapped_column(TZ)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[dt.datetime] = mapped_column(TZ)
