"""Every citizen report opens an incident, with a satellite review of the place (DECISIONS.md D-063).

Once a report has a place:
1. **The same place reported before** (100 m, 60 days): it follows that report and its incident.
2. **An open incident within 150 m** on the same location: it joins that incident.
3. **Otherwise a new incident**, origin 'citizen', in the regular flow (D-057):
   - **Its candidate is the reported spot:** a 30 m circle around the pin, with the change the
     citizen named.
   - **Its location** is the watched location that holds the pin. Outside every location it is a
     new "reported place": a 50 m circle, not on the weekly watch, with the district and mandal
     found for the pin.
   - **The legal check runs and is kept**, but it never closes a citizen incident on its own: an
     official always reviews it.
4. **The satellite review:**
   - **Demo data:** the demo world answers at once.
   - **Real data:** it waits for the screener (`lp review-reports`), which looks at the newest
     Sentinel-2 images of the place.
   - **What it adds:** the result, the dates and the before and after images, which become the
     incident's images and observations.

Officials are told about the incident in the usual way, and again when a real review comes back.
From then on it is an incident like any other: reviews, sharper images, decision and closing, each
with a note. Every step is passed on to the citizen.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json

from geoalchemy2.elements import WKTElement
from shapely.geometry import Point
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.citizen import locate, texts
from app.models import Alert, Asset, Candidate, CitizenReport, MonitoringChange, Observation, SatelliteReview, ScreenRun
from app.rules import config as rules
from app.rules import legal_check
from app.services import boundaries as bsvc
from app.storage import store

CHANGE_OF = {"dumping": "soil_fill", "construction": "building", "fencing": "small_structure", "clearing": "clearing", "other": "other"}
STAGE_OF = {"dumping": "soil_dumped", "construction": "building_rises", "fencing": "sheds_fences", "clearing": "land_levelled", "other": None}
SPOT_M = 30
PLACE_M = 50
NEAR_M = 150
RULES = "citizen-v1"
LICENCE_DEMO = "Demo world: synthetic imagery. Not satellite data"
REVIEW_NOTE = {"change_found": "review_change", "no_change": "review_no_change", "no_clear_look": "review_no_look"}
MAX_ATTEMPTS = 3


def _circle(db: Session, lon: float, lat: float, radius_m: float) -> dict:
    return json.loads(db.scalar(text(
        "SELECT ST_AsGeoJSON(ST_Multi(ST_Buffer(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :r, 16)::geometry), 7)"
    ), {"lon": lon, "lat": lat, "r": radius_m}))


def reported_place(db: Session, report: CitizenReport, lon: float, lat: float, area: dict, at: dt.datetime) -> Asset:
    """A place outside every watched location, so the report's incident has a place and a boundary."""
    asset = Asset(
        asset_key=f"rep-{report.ref.lower()}", name=f"{'Demo reported' if report.is_demo else 'Reported'} place {report.ref}",
        name_te=f"{'డెమో ' if report.is_demo else ''}పౌరులు తెలిపిన ప్రదేశం {report.ref}",
        type="reported_place", cohort=rules.cohort_for_status("derived").value, district=area.get("district"),
        mandal=area.get("mandal"), village=area.get("village"), survey_numbers=[], baseline_date=rules.policy_cutoff_date(),
        is_demo=report.is_demo, added_at=at,
        notes=f"Made from citizen report {report.ref}." + (f" District and mandal: {area['source']}." if area.get("source") else ""),
    )
    db.add(asset)
    db.flush()
    bsvc.add_version(db, asset, kind="parcel", status="derived", geometry=_circle(db, lon, lat, PLACE_M),
                     source_name=f"A {PLACE_M} m circle around the citizen's pin (report {report.ref})", valid_from=at.date(), at=at)
    db.add(MonitoringChange(asset_id=asset.id, monitored=False, at=at,
                            reason=f"Made from citizen report {report.ref}. Not on the weekly watch until the admin starts it"))
    db.flush()
    db.refresh(asset)
    return asset


def create(db: Session, report: CitizenReport, lon: float, lat: float, matched: dict | None, at: dt.datetime) -> Alert:
    """The citizen incident: the reported spot as its candidate, in the regular flow."""
    from app.services import ingest

    if matched:
        asset = db.get(Asset, matched["id"])
    else:
        area = locate.area_of(db, lon, lat, report.is_demo, None)
        asset = reported_place(db, report, lon, lat, area, at)
    primary = bsvc.primary_of(bsvc.boundary_set_at(db, asset.id, at.date()))
    spot = bsvc.to_multipolygon(_circle(db, lon, lat, SPOT_M))
    area_sq_m = db.scalar(text("SELECT ST_Area(ST_Transform(ST_GeomFromText(:w, 4326), 32644))"), {"w": spot.wkt})
    flags = ["citizen_report"] + (["placed_from_description"] if report.placed_by == "description" else [])
    candidate = Candidate(
        asset_id=asset.id, boundary_id=primary["id"], geom=WKTElement(spot.wkt, srid=4326), area_sq_m=round(area_sq_m, 2),
        change_type=CHANGE_OF[report.what], stage_estimate=STAGE_OF[report.what], last_clear_at=None,
        first_changed_at=report.created_at.date(), observation_ids=[], sensor_basis="citizen_report", confidence=0,
        rule_version=RULES, flags=flags, created_at=at,
    )
    db.add(candidate)
    db.flush()
    check, decision = legal_check.run(db, candidate, asset, at)
    alert = ingest._new_alert(db, candidate, asset, at)
    alert.origin, alert.report_id = "citizen", report.id
    db.flush()
    chain.record(db, actor_id=None, action="citizen.incident_opened", entity="alert", entity_id=alert.id, at=at,
                 details={"code": alert.code, "ref": report.ref, "asset_id": asset.id, "reported_place": matched is None,
                          "legal_check": decision.result.value})
    return alert


# The satellite review ---------------------------------------------------------------------------
def request(db: Session, alert: Alert, report: CitizenReport, lon: float, lat: float, at: dt.datetime, *, send: bool = True) -> SatelliteReview:
    review = SatelliteReview(alert_id=alert.id, status="pending", source="demo-synthetic" if report.is_demo else "sentinel-2",
                             requested_at=at, scenes=[], attempts=0, is_demo=report.is_demo)
    db.add(review)
    db.flush()
    if report.is_demo:
        record(db, review, demo_result(db, report, lon, lat, at), at, tell_officials=False, send=send)
    return review


def _chip_key(alert: Alert, kind: str, data: bytes) -> str:
    if not data.startswith(b"\x89PNG"):
        raise ValueError("Review images must be PNG")
    return store.put_object(f"reviews/{alert.code}/{hashlib.sha256(data).hexdigest()[:16]}_{kind}.png", data)


def record(db: Session, review: SatelliteReview, result: dict, at: dt.datetime, tell_officials: bool = True, send: bool = True) -> None:
    """A finished review: kept, made the incident's images, and passed to the citizen and officials."""
    from app.citizen import service

    alert = db.get(Alert, review.alert_id)
    candidate = db.get(Candidate, alert.candidate_id)
    review.status, review.result, review.done_at = "done", result["result"], at
    review.as_of = result.get("as_of")
    review.before_date, review.after_date = result.get("before_date"), result.get("after_date")
    review.scenes = [{**s, "acquired_at": str(s["acquired_at"])} for s in result.get("scenes", [])]
    review.detail = result.get("detail")
    change = result.get("change") or {}
    review.change_type, review.change_area_sq_m = change.get("change_type"), change.get("area_sq_m")
    review.first_changed_at = change.get("first_changed_at")
    if result.get("before_png"):
        review.before_chip = candidate.before_chip = _chip_key(alert, "before", result["before_png"])
    if result.get("after_png"):
        review.after_chip = candidate.after_chip = _chip_key(alert, "after", result["after_png"])
    obs_ids = []
    for s in result.get("scenes", []):
        row = db.scalar(select(Observation).where(Observation.scene_id == s["scene_id"], Observation.sensor == s["sensor"]))
        if row is None:
            row = Observation(sensor=s["sensor"], scene_id=s["scene_id"], acquired_at=s["acquired_at"], cloud_pct=s.get("cloud_pct"),
                              stac_href=s.get("stac_href"), licence_notice=s.get("licence_notice") or LICENCE_DEMO, is_demo=review.is_demo)
            db.add(row)
            db.flush()
        obs_ids.append(row.id)
    if obs_ids:
        candidate.observation_ids = sorted(set(obs_ids))
    if review.result == "change_found" and change.get("first_changed_at"):
        candidate.flags = sorted(set(candidate.flags or []) | {"satellite_change_seen"})
    db.flush()
    chain.record(db, actor_id=None, action="citizen.satellite_review", entity="alert", entity_id=alert.id, at=at,
                 details={"result": review.result, "source": review.source, "after_date": str(review.after_date) if review.after_date else None,
                          "change_area_sq_m": float(review.change_area_sq_m) if review.change_area_sq_m is not None else None})
    date = review.first_changed_at if review.result == "change_found" else review.after_date
    when = {lang: date.strftime("%d %b %Y") for lang in texts.LANGS} if date else {lang: "" for lang in texts.LANGS}
    for report in service.open_reports_of(db, alert.id):
        service.add_event(db, report, f"satellite_{review.result}", status="CHECKING", note=texts.note(REVIEW_NOTE[review.result], date=when),
                          at=at, internal=f"Satellite review ({review.source}): {review.result}", send=send)
    if tell_officials:
        from app.notify import service as notify

        notify.satellite_review(db, alert, at)


def failed(db: Session, review: SatelliteReview, detail: str, at: dt.datetime) -> None:
    review.attempts += 1
    review.detail = detail[:500]
    if review.attempts >= MAX_ATTEMPTS:
        review.status, review.done_at = "failed", at
    chain.record(db, actor_id=None, action="citizen.satellite_review_failed", entity="alert", entity_id=review.alert_id, at=at,
                 details={"attempts": review.attempts, "detail": detail[:200]})


def pending(db: Session, limit: int = 20) -> list[SatelliteReview]:
    return list(db.scalars(select(SatelliteReview).where(SatelliteReview.status == "pending", SatelliteReview.is_demo.is_(False))
                           .order_by(SatelliteReview.requested_at).limit(limit)))


# The demo world's answer ------------------------------------------------------------------------
# Set by the demo seeder while it runs, before any weekly screen exists to date the world.
SEED_DAY: dt.date | None = None


def _seed_day(db: Session, at: dt.datetime) -> dt.date:
    """Day 0 of the demo world: the seed day, which is the date of its latest weekly screen."""
    if SEED_DAY is not None:
        return SEED_DAY
    return db.scalar(select(ScreenRun.as_of).where(ScreenRun.is_demo.is_(True)).order_by(ScreenRun.as_of.desc()).limit(1)) or at.date()


def demo_result(db: Session, report: CitizenReport, lon: float, lat: float, at: dt.datetime) -> dict:
    """What the demo sensor shows at the pin. Changes after the last weekly screen
    (`unscreened_changes` in world.yml) are found here first; everywhere else shows no change."""
    from app.seed import demo_render as render
    from app.seed.demo_world import World

    world = World.load()
    e, n = world.from_lonlat(lon, lat)
    here = Point(e, n)
    seed = _seed_day(db, at)
    day = (at.date() - seed).days
    found = next((c for c in world.spec.get("unscreened_changes", [])
                  if c["first_changed"] <= day and world.change_m(c).distance(here) <= NEAR_M), None)
    after_date = at.date()
    before_date = after_date - dt.timedelta(days=30)

    def scene(d: dt.date) -> dict:
        return {"sensor": "demo_synthetic_optical", "scene_id": f"DEMO-REVIEW-{d.isoformat()}", "acquired_at": dt.datetime.combine(d, dt.time(5, 0), tzinfo=dt.timezone.utc),
                "cloud_pct": 4.0, "licence_notice": LICENCE_DEMO}

    if found:
        window = render.chip_window(world, found)
        first = seed + dt.timedelta(days=found["first_changed"])
        return {
            "result": "change_found", "as_of": after_date, "before_date": before_date, "after_date": after_date,
            "scenes": [scene(before_date), scene(after_date)],
            "before_png": render.render_chip(world, found, when=before_date, after=False, window=window),
            "after_png": render.render_chip(world, found, when=after_date, after=True, window=window),
            "change": {"change_type": found["change"]["type"], "area_sq_m": round(world.change_m(found).area, 1), "first_changed_at": first},
            "detail": "Demo sensor: a change the weekly screen has not seen yet",
        }
    nearest = min(world.spec["assets"], key=lambda a: Point(*world.asset_centre_m(a)).distance(here))
    pseudo = {"key": f"review-{report.ref}", "asset": nearest["key"], "change": {"type": "other", "shape": "inside", "offset": [0, 0], "size": [10, 10]}}
    window = (e, n, 560.0)
    return {
        "result": "no_change", "as_of": after_date, "before_date": before_date, "after_date": after_date,
        "scenes": [scene(before_date), scene(after_date)],
        "before_png": render.render_chip(world, pseudo, when=before_date, after=False, window=window, show_change=False),
        "after_png": render.render_chip(world, pseudo, when=after_date, after=True, window=window, show_change=False),
        "detail": "Demo sensor: no change at the pin",
    }


def decode(b64: str | None) -> bytes | None:
    return base64.b64decode(b64) if b64 else None
