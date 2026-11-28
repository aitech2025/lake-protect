"""Enumerations from CONTEXT.md section 7. Values must match the migrations (0002, 0006, 0008)."""
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
    # Planned categories (app/categories.yaml, DECISIONS.md D-061): in the database, not yet watched.
    endowment_land = "endowment_land"
    forest_land = "forest_land"
    # A place outside every watched location, made from a citizen's report (D-063). Not watched.
    reported_place = "reported_place"


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
    levelling = "levelling"
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
    citizen_report = "citizen_report"  # the reported spot; the satellite review is kept beside it (D-063)


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
    """The legal check's verdict (legal_checks.result). Incidents use IncidentState since 0006."""

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
    """Two roles since 24 Nov 2026 (DECISIONS.md D-057): the admin runs the application; viewers
    are the officials, who see everything and record reviews of incidents."""

    admin = "admin"
    viewer = "viewer"


class IncidentState(StrEnum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    FIELD_VISIT = "FIELD_VISIT"  # a field officer is assigned (D-067)
    FIELD_REPORTED = "FIELD_REPORTED"  # the field report is in, for the district officer
    RECOMMENDED = "RECOMMENDED"  # the district officer recommends; the senior official decides
    CONFIRMED = "CONFIRMED"
    DISMISSED = "DISMISSED"
    CLOSED = "CLOSED"


class Resolution(StrEnum):
    confirmed = "confirmed"
    dismissed = "dismissed"
    auto = "auto"  # closed at once by the legal check: outside the zones, before the baseline, authorised


class ReviewOutcome(StrEnum):
    real_change = "real_change"
    not_real = "not_real"
    needs_site_visit = "needs_site_visit"


class DocumentType(StrEnum):
    notification = "notification"
    survey_map = "survey_map"
    land_record = "land_record"
    government_order = "government_order"
    court_order = "court_order"
    recovery_order = "recovery_order"
    other = "other"



class NotificationKind(StrEnum):
    """What a notification is about (DECISIONS.md D-059)."""

    incident_opened = "incident_opened"  # a new incident in the official's area: needs acknowledgement
    incident_decided = "incident_decided"  # the admin confirmed or dismissed an incident in the area
    reminder = "reminder"  # not acknowledged within 24 hours: sent again
    not_acknowledged = "not_acknowledged"  # to the admin: an official has not acknowledged in 48 hours
    weekly_digest = "weekly_digest"  # after each weekly screen: the official's area that week
    citizen_report = "citizen_report"  # a citizen's report in the area (D-062): needs acknowledgement
    satellite_review = "satellite_review"  # the satellite review of a citizen incident is done (D-063)
    incident_assigned = "incident_assigned"  # to a field officer: a field visit is theirs (D-067)
    field_reported = "field_reported"  # to the area's district officers: a field report is in
    recommended = "recommended"  # to the senior officials: a recommendation waits for approval
    returned = "returned"  # a field report or a recommendation was sent back, with a note


class Channel(StrEnum):
    in_app = "in_app"
    email = "email"
    sms = "sms"
    whatsapp = "whatsapp"


class DeliveryStatus(StrEnum):
    queued = "queued"
    sent = "sent"
    held = "held"  # the channel is not set up yet (no gateway agreement or approved template)
    failed = "failed"
    skipped = "skipped"  # no address, or demo data that must not leave the machine

class ReadinessStatus(StrEnum):
    yes = "yes"
    no = "no"
    not_applicable = "not_applicable"
