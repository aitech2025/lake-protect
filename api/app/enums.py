"""Enumerations from CONTEXT.md section 7. Values must match migration 0002."""
from enum import StrEnum


class Cohort(StrEnum):
    A_RECOVERED = "A_RECOVERED"
    B_FINAL = "B_FINAL"
    C_PRELIM = "C_PRELIM"
    D_UNNOTIFIED = "D_UNNOTIFIED"
    E_AGENCY = "E_AGENCY"
    F_REVENUE = "F_REVENUE"


class AssetType(StrEnum):
    lake = "lake"
    recovered_parcel = "recovered_parcel"
    agency_parcel = "agency_parcel"
    revenue_parcel = "revenue_parcel"


class BoundaryKind(StrEnum):
    ftl = "ftl"
    buffer = "buffer"
    parcel = "parcel"
    watch_ring = "watch_ring"


class BoundaryStatus(StrEnum):
    physically_marked = "physically_marked"
    final_notification = "final_notification"
    preliminary_notification = "preliminary_notification"
    derived = "derived"
    surveyed_agency = "surveyed_agency"
    survey_number_only = "survey_number_only"


class Zone(StrEnum):
    inside_ftl = "inside_ftl"
    buffer = "buffer"
    watch_ring = "watch_ring"
    outside = "outside"


class ChangeType(StrEnum):
    soil_fill = "soil_fill"
    clearing = "clearing"
    small_structure = "small_structure"
    building = "building"
    water_loss = "water_loss"
    other = "other"


class Stage(StrEnum):
    soil_dumped = "soil_dumped"
    land_levelled = "land_levelled"
    sheds_fences = "sheds_fences"
    building_rises = "building_rises"
    occupied = "occupied"


class SensorBasis(StrEnum):
    optical_and_radar = "optical_and_radar"
    optical_only = "optical_only"
    radar_only = "radar_only"


class AlertClass(StrEnum):
    GOVT_LAND = "GOVT_LAND"
    RESTRICTED_PRIVATE = "RESTRICTED_PRIVATE"
    DISPUTED = "DISPUTED"
    UNKNOWN = "UNKNOWN"


class Mode(StrEnum):
    ACTION = "ACTION"
    VERIFY = "VERIFY"
    WATCH = "WATCH"


class AlertState(StrEnum):
    CANDIDATE = "CANDIDATE"
    CLOSED_OUT_OF_SCOPE = "CLOSED_OUT_OF_SCOPE"
    CLOSED_LEGACY = "CLOSED_LEGACY"
    CLOSED_AUTHORISED = "CLOSED_AUTHORISED"
    HOLD_LEGAL = "HOLD_LEGAL"
    WATCH_LIST = "WATCH_LIST"
    TRIAGE = "TRIAGE"
    CLOSED_NOT_REAL = "CLOSED_NOT_REAL"
    CONFIRMED = "CONFIRMED"
    ASSIGNED = "ASSIGNED"
    CLOSED_FALSE_ALARM = "CLOSED_FALSE_ALARM"
    FIELD_CONFIRMED = "FIELD_CONFIRMED"
    AWAITING_BOUNDARY = "AWAITING_BOUNDARY"
    PACK_READY = "PACK_READY"
    WITH_OFFICER = "WITH_OFFICER"
    ACTION_RECORDED = "ACTION_RECORDED"
    CLOSED_NO_ACTION = "CLOSED_NO_ACTION"
    POST_ACTION_WATCH = "POST_ACTION_WATCH"


class FieldOutcome(StrEnum):
    confirmed = "confirmed"
    false_alarm = "false_alarm"
    cannot_access = "cannot_access"


class Role(StrEnum):
    analyst = "analyst"
    reviewer = "reviewer"
    field_officer = "field_officer"
    nodal_officer = "nodal_officer"
    legal_officer = "legal_officer"
    senior_officer = "senior_officer"
    auditor = "auditor"
    admin = "admin"


class ReadinessStatus(StrEnum):
    yes = "yes"
    no = "no"
    not_applicable = "not_applicable"
