"""Citizen reports: intake, placing, the incident and updates (CONTEXT.md 17.8; DECISIONS.md D-062, D-063).

**Upstream.** A report comes in from the web portal, WhatsApp, or staff who take a 1070 call, a
Praja Vani petition or a visit. On arrival:
1. **Reference.** It gets a reference number.
2. **Place.** From the pin, or from words that name one watched location (app.citizen.locate). With
   no place, the admin is asked to put it on the map.
3. **Incident** (app.citizen.incident):
   - it follows an earlier report of the same place (100 m, 60 days);
   - or it joins an open incident within 150 m;
   - or it opens a citizen incident.

   A new citizen incident gets a satellite review of the place and its officials are told.
   Officials then work it in the regular flow: reviews, sharper images, a decision and closing,
   each with a note.
4. **Signal.** It becomes a row in `signals` (CONTEXT.md section 7).

**Downstream.**
- **Every step is an event** with a public note in English and Telugu.
- **Where the citizen sees it:** on the portal with the reference, and by SMS or WhatsApp if they
  asked for updates.
- **The note never names** an officer, owner or claimant, and never shows evidence.
- **Steps come from the incident:**
  - opened, with the satellite review's result;
  - under review;
  - sharper images asked for;
  - confirmed, dismissed or passed to a department.

Privacy (DPDP Act 2023). Name and phone are optional. A phone is kept only to send updates, only
once verified (one-time password, the WhatsApp number itself, or taken by staff from the caller),
and is removed 90 days after the report closes. Photos are re-encoded, which drops their EXIF
metadata (camera, time and the phone's own location). Rate limits use a salted hash of the network
address or phone, never the address itself.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import io
import json
import re
import secrets

from geoalchemy2.elements import WKTElement
from shapely.geometry import Point, box
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.citizen import locate, sender, texts
from app.config import settings
from app.models import Alert, Asset, CitizenMessage, CitizenReport, CitizenReportEvent, Signal, User
from app.sources import engine
from app.storage import store

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base 32: no I, L, O or U
REF_RE = re.compile(r"GGR-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}", re.IGNORECASE)
STAFF_CHANNELS = ("helpline_1070", "praja_vani", "walk_in")
CHANNELS = ("web", "whatsapp", *STAFF_CHANNELS)
WHATS = texts.WHAT_ORDER

DUPLICATE_M = 100
DUPLICATE_DAYS = 60
INCIDENT_M = 150
MAX_PHOTOS = 3
MAX_PHOTO_BYTES = 8 * 1024 * 1024
MAX_SIDE = 2048
PER_HOUR = 5
PER_DAY = 20
KEEP_CONTACT = dt.timedelta(days=90)
OPEN_INCIDENT = ("OPEN", "UNDER_REVIEW", "CONFIRMED")


class CitizenError(ValueError):
    status_code = 422


class TooMany(CitizenError):
    status_code = 429


# Small helpers ----------------------------------------------------------------------------------
def _key() -> bytes:
    return hmac.new(settings.jwt_secret.encode(), b"geoguard-citizen", hashlib.sha256).digest()


def source_hash(value: str) -> str:
    """Salted, so the hash cannot be turned back into an address or a phone number."""
    return hmac.new(_key(), value.encode(), hashlib.sha256).hexdigest()[:32]


def new_ref(db: Session) -> str:
    while True:
        raw = "".join(secrets.choice(ALPHABET) for _ in range(8))
        ref = f"GGR-{raw[:4]}-{raw[4:]}"
        if db.scalar(select(CitizenReport.id).where(CitizenReport.ref == ref)) is None:
            return ref


def in_telangana(lon: float, lat: float) -> bool:
    """Reports are taken for places in Telangana only (the box around the State)."""
    return box(*engine.settings()["real_bbox"]).contains(Point(lon, lat))


def normalise_phone(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    digits = re.sub(r"[^\d+]", "", value.strip())
    if re.fullmatch(r"[6-9]\d{9}", digits):
        digits = "+91" + digits
    elif re.fullmatch(r"91\d{10}", digits):
        digits = "+" + digits
    if not re.fullmatch(r"\+[1-9]\d{7,14}", digits):
        raise CitizenError("Give a mobile number with 10 digits, or with +91")
    return digits


def clean_photo(data: bytes) -> tuple[bytes, int, int]:
    """Re-encode as JPEG, at most 2048 px a side. Drops EXIF and every other metadata block."""
    from PIL import Image, ImageOps, UnidentifiedImageError

    if len(data) > MAX_PHOTO_BYTES:
        raise CitizenError("A photo can be at most 8 MB")
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))
    except (UnidentifiedImageError, OSError) as exc:
        raise CitizenError("A photo must be a JPEG, PNG or WebP image") from exc
    if img.format not in ("JPEG", "PNG", "WEBP"):
        raise CitizenError("A photo must be a JPEG, PNG or WebP image")
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85)
    return out.getvalue(), img.width, img.height


def store_photo(prefix: str, n: int, data: bytes) -> dict:
    clean, w, h = clean_photo(data)
    key = f"citizen/{prefix}/{n}.jpg"
    store.put_object(key, clean)
    return {"key": key, "sha256": hashlib.sha256(clean).hexdigest(), "width": w, "height": h}


# Placing a report -------------------------------------------------------------------------------
_MATCH = text(
    """
    WITH p AS (SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) AS g)
    SELECT a.id, a.name, a.name_te, a.monitored, bv.kind::text AS kind,
           ST_Distance(bv.geom::geography, p.g::geography) AS d
    FROM boundary_versions bv JOIN assets a ON a.id = bv.asset_id CROSS JOIN p
    WHERE bv.kind IN ('ftl', 'parcel', 'buffer', 'watch_ring')
      AND bv.valid_from <= CURRENT_DATE AND (bv.effective_valid_to IS NULL OR bv.effective_valid_to > CURRENT_DATE)
      AND ST_Intersects(bv.geom, p.g)
    ORDER BY CASE WHEN bv.kind IN ('ftl', 'parcel') THEN 0 WHEN bv.kind = 'buffer' THEN 1 ELSE 2 END, a.monitored DESC, d
    LIMIT 1
    """
)
ZONE = {"ftl": "inside", "parcel": "inside", "buffer": "buffer", "watch_ring": "watch_ring"}


def match(db: Session, lon: float, lat: float) -> dict | None:
    row = db.execute(_MATCH, {"lon": lon, "lat": lat}).mappings().first()
    return {**dict(row), "zone": ZONE[row["kind"]]} if row else None


def near_incident(db: Session, asset_id: int, lon: float | None, lat: float | None) -> int | None:
    """An open, under-review or confirmed incident on the location, within 150 m of the pin."""
    return db.scalar(text(
        """
        SELECT al.id FROM alerts al JOIN candidates c ON c.id = al.candidate_id
        WHERE c.asset_id = :a AND al.state::text = ANY(:states)
          AND (CAST(:lon AS float8) IS NULL OR ST_DWithin(c.geom::geography,
               ST_SetSRID(ST_MakePoint(CAST(:lon AS float8), CAST(:lat AS float8)), 4326)::geography, :m))
        ORDER BY CASE WHEN CAST(:lon AS float8) IS NULL THEN 0
                      ELSE ST_Distance(c.geom::geography, ST_SetSRID(ST_MakePoint(CAST(:lon AS float8), CAST(:lat AS float8)), 4326)::geography) END,
                 al.id DESC
        LIMIT 1
        """
    ), {"a": asset_id, "lon": lon, "lat": lat, "m": INCIDENT_M, "states": list(OPEN_INCIDENT)})


def duplicate_root(db: Session, lon: float, lat: float, at: dt.datetime) -> CitizenReport | None:
    rid = db.scalar(text(
        """
        SELECT coalesce(r.duplicate_of, r.id) FROM citizen_reports r
        WHERE r.status <> 'CLOSED' AND r.geom IS NOT NULL AND r.created_at >= :since
          AND ST_DWithin(r.geom::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :m)
        ORDER BY r.created_at, r.id LIMIT 1
        """
    ), {"lon": lon, "lat": lat, "m": DUPLICATE_M, "since": at - dt.timedelta(days=DUPLICATE_DAYS)})
    return db.get(CitizenReport, rid) if rid else None


def place_name(db: Session, report: CitizenReport) -> dict:
    asset = db.get(Asset, report.asset_id) if report.asset_id else None
    if asset is None:
        return dict(texts.PLACE_UNWATCHED)
    return {"en": asset.name, "te": asset.name_te or asset.name, "ur": asset.name}


# Events and updates -----------------------------------------------------------------------------
def _children(db: Session, report: CitizenReport) -> list[CitizenReport]:
    return list(db.scalars(select(CitizenReport).where(CitizenReport.duplicate_of == report.id, CitizenReport.status != "CLOSED")
                           .order_by(CitizenReport.id)))


def add_event(db: Session, report: CitizenReport, kind: str, *, status: str, note: dict, at: dt.datetime,
              internal: str | None = None, actor: User | None = None, closed_reason: str | None = None, mirror: bool = True,
              send: bool = True) -> None:
    """One step: the report's new status, the public note, and an update to the citizen if they asked."""
    report.status = status
    report.closed_reason = closed_reason if status == "CLOSED" else None
    report.updated_at = at
    db.add(CitizenReportEvent(report_id=report.id, kind=kind, status=status, public_note=note, internal_note=internal,
                              actor_id=actor.id if actor else None, at=at))
    db.flush()
    if send:
        sender.queue_update(db, report, status, note, at)
    if mirror:
        for child in _children(db, report):
            child.alert_id = report.alert_id or child.alert_id
            child.asset_id = report.asset_id or child.asset_id
            add_event(db, child, kind, status=status, note=note, at=at, internal=internal, actor=actor, closed_reason=closed_reason, mirror=False)


def _rate_limit(db: Session, source: str, at: dt.datetime) -> None:
    def count(since: dt.datetime) -> int:
        return int(db.scalar(select(func.count()).select_from(CitizenReport).where(
            CitizenReport.source_hash == source, CitizenReport.created_at >= since)) or 0)

    if count(at - dt.timedelta(hours=1)) >= PER_HOUR or count(at - dt.timedelta(days=1)) >= PER_DAY:
        raise TooMany("Too many reports from here in a short time. Please try again later.")


def submit(
    db: Session,
    *,
    channel: str,
    language: str,
    what: str,
    at: dt.datetime,
    source: str,
    lon: float | None = None,
    lat: float | None = None,
    location_text: str | None = None,
    description: str | None = None,
    photos: list[bytes] | None = None,
    stored_photos: list[dict] | None = None,
    reporter_name: str | None = None,
    phone: str | None = None,
    phone_verified_via: str | None = None,
    wants_updates: bool = False,
    source_ref: str | None = None,
    entered_by: User | None = None,
) -> CitizenReport:
    if channel not in CHANNELS:
        raise CitizenError(f"Unknown channel {channel}")
    if (channel in STAFF_CHANNELS) != (entered_by is not None):
        raise CitizenError("Staff enter 1070, Praja Vani and walk-in reports from the desk")
    if language not in texts.LANGS:
        raise CitizenError("Language must be en or te")
    if what not in WHATS:
        raise CitizenError(f"What was seen must be one of: {', '.join(WHATS)}")
    description = (description or "").strip() or None
    if description and len(description) > 1000:
        raise CitizenError("Keep the description under 1,000 characters")
    location_text = (location_text or "").strip()[:300] or None
    if lon is None or lat is None:
        lon = lat = None
        if not location_text:
            raise CitizenError("Mark the place on the map, or say where it is")
    elif not in_telangana(lon, lat):
        raise CitizenError("The place must be in Telangana")
    if len(photos or []) + len(stored_photos or []) > MAX_PHOTOS:
        raise CitizenError(f"At most {MAX_PHOTOS} photos")
    if channel not in STAFF_CHANNELS:
        _rate_limit(db, source, at)
    if phone is not None and not (wants_updates and phone_verified_via):
        phone = None  # kept only to send updates, and only once verified
    flags = []
    falses = db.scalar(select(func.count()).select_from(CitizenReport).where(CitizenReport.source_hash == source,
                                                                            CitizenReport.false_report.is_(True))) or 0
    if falses >= 2:
        flags.append("repeat_false_reports")

    ref = new_ref(db)
    kept = list(stored_photos or []) + [store_photo(ref, i + 1 + len(stored_photos or []), p) for i, p in enumerate(photos or [])]
    report = CitizenReport(
        ref=ref, channel=channel, language=language, what=what, description=description,
        geom=WKTElement(f"POINT({lon} {lat})", srid=4326) if lon is not None else None, location_text=location_text,
        photos=kept, reporter_name=((reporter_name or "").strip()[:120] or None) if phone else None,
        reporter_phone=phone, phone_verified_via=phone_verified_via if phone else None, wants_updates=bool(phone),
        source_ref=(source_ref or "").strip() or None, entered_by=entered_by.id if entered_by else None,
        status="RECEIVED", flags=flags, source_hash=source, is_demo=False, created_at=at, updated_at=at,
    )
    db.add(report)
    db.flush()
    # The first steps send one update, the last. On WhatsApp the chat's own reply says them.
    send = channel != "whatsapp"
    add_event(db, report, "received", status="RECEIVED", note=texts.note("received", ref=ref), at=at, actor=entered_by, mirror=False, send=False)

    placed_by = "pin"
    if lon is None:
        guess = locate.from_words(db, location_text or description)
        if guess:
            lon, lat, placed_by = guess["lon"], guess["lat"], "description"
            add_event(db, report, "placed_from_words", status="RECEIVED", note=texts.note("placed_from_words", place={"en": guess["name"], "te": guess["name"]}),
                      at=at, internal=f"Placed on {guess['name']} from the words: {(location_text or description or '')[:120]}", mirror=False, send=False)
    if lon is None:
        add_event(db, report, "no_place", status="RECEIVED", note=texts.note("no_place"), at=at, send=send)
        db.add(Signal(kind="citizen_report", asset_id=None, geom=None, received_at=at, ref=ref, linked_alert_id=None, is_demo=report.is_demo))
        db.flush()
        from app.notify import service as notify

        notify.citizen_report(db, report, at)  # the admin places it
    else:
        place(db, report, lon, lat, placed_by, at, send=send)
    chain.record(db, actor_id=entered_by.id if entered_by else None, action="citizen.report_received", entity="citizen_report",
                 entity_id=report.id, at=at,
                 details={"ref": ref, "channel": channel, "what": what, "asset_id": report.asset_id, "zone": report.zone,
                          "alert_id": report.alert_id, "duplicate_of": report.duplicate_of, "photos": len(kept),
                          "updates": report.wants_updates, "flags": flags, "placed_by": report.placed_by})
    return report


def place(db: Session, report: CitizenReport, lon: float, lat: float, placed_by: str, at: dt.datetime, *,
          send: bool = True, actor: User | None = None) -> None:
    """Where the report is, and the incident it belongs to: an earlier report's, an open one nearby, or
    a new citizen incident with its satellite review (D-063)."""
    from app.citizen import incident
    from app.notify import service as notify

    report.geom = WKTElement(f"POINT({lon} {lat})", srid=4326)
    report.placed_by = placed_by
    db.flush()
    root = duplicate_root(db, lon, lat, at)
    if root is not None and root.id != report.id and root.alert_id:
        report.duplicate_of, report.asset_id, report.zone, report.alert_id = root.id, root.asset_id, root.zone, root.alert_id
        add_event(db, report, "duplicate", status=root.status, note=texts.note("duplicate"), at=at, internal=f"Same place as {root.ref}",
                  mirror=False, send=send, actor=actor)
    else:
        m = match(db, lon, lat)
        if m:
            report.asset_id, report.zone = m["id"], m["zone"]
        existing = near_incident(db, m["id"], lon, lat) if m else None
        if existing:
            report.alert_id = existing
            add_event(db, report, "linked_incident", status="CHECKING", note=texts.note("linked_incident", place=place_name(db, report)),
                      at=at, send=send, actor=actor)
            notify.citizen_report(db, report, at)  # for information: the incident already has its officials
            alert = db.get(Alert, existing)
            if alert.state == "CONFIRMED":
                add_event(db, report, "closed_incident_confirmed", status="CLOSED", note=texts.note("incident_confirmed"), at=at,
                          closed_reason="incident_confirmed", internal=f"Incident {alert.code} was already confirmed")
        else:
            alert = incident.create(db, report, lon, lat, m, at)
            report.alert_id = alert.id
            if not m:
                report.asset_id = db.scalar(text("SELECT c.asset_id FROM candidates c WHERE c.id = :c"), {"c": alert.candidate_id})
                report.zone = "inside"
            add_event(db, report, "case_opened", status="CHECKING", note=texts.note("case_opened"), at=at, actor=actor,
                      internal=f"Incident {alert.code} opened", send=send)
            incident.request(db, alert, report, lon, lat, at, send=send)
            notify.incident_opened(db, alert, at)
    db.add(Signal(kind="citizen_report", asset_id=report.asset_id, geom=report.geom, received_at=at, ref=report.ref,
                  linked_alert_id=report.alert_id, is_demo=report.is_demo))
    db.flush()


def place_by_official(db: Session, report: CitizenReport, user: User, lon: float, lat: float, at: dt.datetime) -> None:
    """A report with no place: an official puts it on the map, and it goes on as any other."""
    if report.geom is not None or report.alert_id:
        raise CitizenError("This report already has its place")
    if not in_telangana(lon, lat):
        raise CitizenError("The place must be in Telangana")
    db.execute(text("DELETE FROM signals WHERE kind = 'citizen_report' AND ref = :r AND geom IS NULL"), {"r": report.ref})
    add_event(db, report, "placed", status="RECEIVED", note=texts.note("placed", place={"en": f"{lat:.5f}, {lon:.5f}", "te": f"{lat:.5f}, {lon:.5f}"}),
              at=at, actor=user, internal="Placed on the map by an official", send=False)
    place(db, report, lon, lat, "official", at, actor=user)
    from app.notify import service as notify

    notify.acknowledge_for_report(db, user, report, "report_check", at)
    chain.record(db, actor_id=user.id, action="citizen.report_placed", entity="citizen_report", entity_id=report.id, at=at,
                 details={"ref": report.ref, "alert_id": report.alert_id})


def open_reports_of(db: Session, alert_id: int) -> list[CitizenReport]:
    """The reports an incident's steps are passed on to. Reports that follow another follow its events."""
    return list(db.scalars(select(CitizenReport).where(CitizenReport.alert_id == alert_id, CitizenReport.status != "CLOSED",
                                                       CitizenReport.duplicate_of.is_(None)).order_by(CitizenReport.id)))


# Steps on the incident, passed on to the citizen (D-063) ---------------------------------------
def on_review_started(db: Session, alert: Alert, at: dt.datetime) -> int:
    """The incident's first review: once per report."""
    reports = [r for r in open_reports_of(db, alert.id)
               if not db.scalar(select(CitizenReportEvent.id).where(CitizenReportEvent.report_id == r.id, CitizenReportEvent.kind == "under_review"))]
    for r in reports:
        add_event(db, r, "under_review", status="CHECKING", note=texts.note("under_review"), at=at, internal=f"Incident {alert.code} under review")
    return len(reports)


def on_imagery_requested(db: Session, alert: Alert, at: dt.datetime) -> int:
    reports = open_reports_of(db, alert.id)
    for r in reports:
        add_event(db, r, "sharper_images", status="CHECKING", note=texts.note("sharper_images"), at=at,
                  internal=f"Sharper images requested on incident {alert.code}")
    return len(reports)


def on_incident_opened(db: Session, alert: Alert, at: dt.datetime) -> int:
    """A new satellite incident: open reports of that place with no incident yet now follow it."""
    rows = db.scalars(text(
        """
        SELECT r.id FROM citizen_reports r JOIN alerts al ON al.id = :al JOIN candidates c ON c.id = al.candidate_id
        WHERE r.asset_id = c.asset_id AND r.status <> 'CLOSED' AND r.alert_id IS NULL AND r.duplicate_of IS NULL
          AND (r.geom IS NULL OR ST_DWithin(r.geom::geography, c.geom::geography, :m))
        ORDER BY r.id
        """
    ), {"al": alert.id, "m": INCIDENT_M}).all()
    for rid in rows:
        report = db.get(CitizenReport, rid)
        report.alert_id = alert.id
        add_event(db, report, "change_found", status="CHECKING", note=texts.note("change_found"), at=at, internal=f"Incident {alert.code} opened")
    return len(rows)


def on_incident_decided(db: Session, alert: Alert, to: str, at: dt.datetime, department: str | None = None,
                        false_report: bool = False) -> int:
    """The admin's decision closes the reports of the incident. A dismissal may say which department
    the report was passed to."""
    reason = {"CONFIRMED": "incident_confirmed", "DISMISSED": "incident_dismissed"}.get(to)
    if reason is None:
        return 0
    if department and to == "DISMISSED":
        if department not in texts.DEPARTMENTS:
            raise CitizenError(f"Department must be one of: {', '.join(texts.DEPARTMENTS)}")
        reason = "passed_on"
    reports = open_reports_of(db, alert.id)
    for report in reports:
        if false_report:
            report.false_report = True
            for child in _children(db, report):
                child.false_report = True
        add_event(db, report, f"closed_{reason}", status="CLOSED", note=texts.note(reason, **({"department": texts.DEPARTMENTS[department]} if department else {})),
                  at=at, closed_reason=reason, internal=f"Incident {alert.code} {to.lower()}" + (f"; passed to {department}" if department else ""))
    return len(reports)


def on_screen_stored(db: Session, run_id: int, at: dt.datetime) -> int:
    """The weekly screen looked clearly at a reported place and found no change: the citizen is told."""
    rows = db.execute(text(
        """
        SELECT r.id, s.last_look FROM citizen_reports r JOIN asset_screens s ON s.asset_id = r.asset_id AND s.run_id = :run
        WHERE r.status = 'CHECKING' AND r.duplicate_of IS NULL
          AND s.status = 'no_candidate' AND s.last_look IS NOT NULL AND s.last_look >= (r.created_at AT TIME ZONE 'UTC')::date
          AND NOT EXISTS (SELECT 1 FROM citizen_report_events e WHERE e.report_id = r.id AND e.kind IN ('satellite_checked', 'satellite_no_change')
                          AND e.at >= CAST(:at AS timestamptz) - interval '6 days')
          AND NOT EXISTS (SELECT 1 FROM citizen_report_events e WHERE e.report_id = r.id AND e.kind = 'satellite_checked'
                          AND e.internal_note = 'Look of ' || s.last_look::text)
        """
    ), {"run": run_id, "at": at}).all()
    for rid, last_look in rows:
        report = db.get(CitizenReport, rid)
        when = {lang: last_look.strftime("%d %b %Y") for lang in texts.LANGS}
        add_event(db, report, "satellite_checked", status="CHECKING", note=texts.note("satellite_checked", date=when), at=at,
                  internal=f"Look of {last_look.isoformat()}")
    return len(rows)


def purge_contacts(db: Session, now: dt.datetime) -> int:
    """Names and phones go 90 days after a report closes. The report and its history stay."""
    reports = list(db.scalars(select(CitizenReport).where(
        CitizenReport.status == "CLOSED", CitizenReport.updated_at < now - KEEP_CONTACT, CitizenReport.contact_purged_at.is_(None),
        (CitizenReport.reporter_phone.is_not(None)) | (CitizenReport.reporter_name.is_not(None)))))
    for r in reports:
        r.reporter_phone = r.reporter_name = r.phone_verified_via = None
        r.wants_updates = False
        r.contact_purged_at = now
    if reports:
        chain.record(db, actor_id=None, action="citizen.contacts_removed", entity="citizen_report", at=now, details={"reports": len(reports)})
    return len(reports)


# Reading ----------------------------------------------------------------------------------------
def events_of(db: Session, report_id: int, internal: bool) -> list[dict]:
    rows = db.execute(text(
        """
        SELECT e.id, e.kind, e.status, e.public_note, e.internal_note, e.at, u.name AS actor
        FROM citizen_report_events e LEFT JOIN users u ON u.id = e.actor_id
        WHERE e.report_id = :r ORDER BY e.id
        """
    ), {"r": report_id}).mappings().all()
    out = []
    for r in rows:
        item = {"kind": r["kind"], "status": r["status"], "note": r["public_note"], "at": r["at"].isoformat()}
        if internal:
            item.update({"id": r["id"], "internal_note": r["internal_note"], "actor": r["actor"]})
        out.append(item)
    return out


def public_view(db: Session, ref: str) -> dict | None:
    """What anyone with the reference sees: no photos, contact, officers or evidence."""
    report = db.scalar(select(CitizenReport).where(CitizenReport.ref == ref.upper().strip()))
    if report is None:
        return None
    return {
        "ref": report.ref, "status": report.status, "status_label": texts.STATUS[report.status], "what": report.what,
        "what_label": texts.WHAT[report.what], "place": place_name(db, report) if report.asset_id else None,
        "channel": report.channel, "language": report.language, "created_at": report.created_at.isoformat(),
        "updated_at": report.updated_at.isoformat(), "closed_reason": report.closed_reason, "updates": report.wants_updates,
        "events": events_of(db, report.id, internal=False),
    }


def stats(db: Session, days: int = 30, now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    row = db.execute(text(
        """
        SELECT count(*) AS received,
               count(*) FILTER (WHERE status = 'CHECKING') AS checking,
               count(*) FILTER (WHERE status = 'CLOSED') AS closed,
               count(*) FILTER (WHERE alert_id IS NOT NULL) AS with_incident
        FROM citizen_reports WHERE created_at >= :since
        """
    ), {"since": now - dt.timedelta(days=days)}).mappings().one()
    return {"days": days, **{k: int(v) for k, v in row.items()}}


def desk_row(db: Session, r: CitizenReport) -> dict:
    lonlat = db.execute(text("SELECT ST_X(geom), ST_Y(geom) FROM citizen_reports WHERE id = :i"), {"i": r.id}).one() if r.geom is not None else (None, None)
    asset = db.get(Asset, r.asset_id) if r.asset_id else None
    alert = db.get(Alert, r.alert_id) if r.alert_id else None
    dups = db.scalar(select(func.count()).select_from(CitizenReport).where(CitizenReport.duplicate_of == r.id)) or 0
    root = db.get(CitizenReport, r.duplicate_of) if r.duplicate_of else None
    return {
        "id": r.id, "ref": r.ref, "channel": r.channel, "language": r.language, "what": r.what, "description": r.description,
        "lon": lonlat[0], "lat": lonlat[1], "location_text": r.location_text, "photos": len(r.photos or []),
        "asset_id": r.asset_id, "asset_name": asset.name if asset else None, "asset_name_te": asset.name_te if asset else None,
        "district": asset.district if asset else None, "mandal": asset.mandal if asset else None, "zone": r.zone,
        "alert_id": r.alert_id, "alert_code": alert.code if alert else None, "alert_state": alert.state if alert else None,
        "duplicate_of": r.duplicate_of, "duplicate_of_ref": root.ref if root else None, "duplicates": int(dups),
        "status": r.status, "closed_reason": r.closed_reason, "false_report": r.false_report, "flags": r.flags or [],
        "updates": r.wants_updates, "phone_masked": sender.mask(r.reporter_phone), "has_name": bool(r.reporter_name),
        "source_ref": r.source_ref, "created_at": r.created_at.isoformat(), "updated_at": r.updated_at.isoformat(),
    }


def messages_of(db: Session, report_id: int) -> list[dict]:
    rows = list(db.scalars(select(CitizenMessage).where(CitizenMessage.report_id == report_id).order_by(CitizenMessage.id)))
    retried = {m.retry_of for m in rows if m.retry_of}
    rows = [m for m in rows if m.id not in retried]  # each message once, at its latest attempt
    return [{"id": m.id, "channel": m.channel, "direction": m.direction, "kind": m.kind, "to_masked": m.to_masked, "text": m.text,
             "status": m.status, "detail": m.detail, "at": m.at.isoformat()} for m in rows]


def as_json(value) -> str:
    return json.dumps(value, ensure_ascii=False)
