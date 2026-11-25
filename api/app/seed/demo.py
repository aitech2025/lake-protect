"""Seed the fictional demo (CONTEXT.md section 13, "Demo data rules"; DECISIONS.md D-057).

    python -m app.seed.demo            # seed relative to today
    python -m app.seed.demo --no-tiles

Everything is invented, marked is_demo, and placed in open sea (DECISIONS.md D-015). Incidents
are not written directly: each scenario runs through the real ingest, legal check and incident
lifecycle, in time order, so the demo shows the system's actual behaviour. Then every demo asset
gets its legal documents and eight weeks of weekly records, each with that week's image.

Notifications come from the same code (D-059): each incident notifies its area's official and the
admin as it opens, the notifier's follow-up runs every simulated morning (reminders after 24 hours,
the admin told after 48), and the latest week's digest goes to everyone at the end.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
from collections.abc import Callable

from geoalchemy2.elements import WKTElement
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.audit import chain
from app.citizen import service as citizen
from app.evidence import pack as pack_svc
from app.models import Alert, Asset, AssetScreen, AuthorisedWork, CourtCase, OfficialArea, Permit, ScreenRun, User
from app.notify import service as notify
from app.seed import demo_docs
from app.seed import demo_render as render
from app.seed.demo_world import World
from app.services import boundaries as bsvc
from app.services import documents as doc_svc
from app.services import ingest as ingest_svc
from app.services import weeks as weeks_svc
from app.storage import store
from app.workflow import incidents as lifecycle

STATUS_BY_COHORT = {
    "A_RECOVERED": "physically_marked",
    "B_FINAL": "final_notification",
    "C_PRELIM": "preliminary_notification",
    "D_UNNOTIFIED": "derived",
}
ACRE = 4046.86
DEMO_RULES = "demo-synthetic-v0"
LICENCE = "Synthetic demo image. Not satellite data."
WEEKS = 8
# A cloudy week: two assets had no clear look, so the record says so instead of "no change".
CLOUDY_WEEK = 5
CLOUDY_ASSETS = {"demo-kunta-7", "demo-kunta-8"}


class Seeder:
    def __init__(self, db: Session, today: dt.date | None = None):
        self.db = db
        self.world = World.load()
        if today is None:
            # Today at 10:00 IST, or now if that is still ahead: nothing in the demo may be dated in the future.
            now = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)
            self.T = min(dt.datetime.combine(now.date(), dt.time(4, 30), tzinfo=dt.timezone.utc), now)
        else:
            self.T = dt.datetime.combine(today, dt.time(4, 30), tzinfo=dt.timezone.utc)
        self.users: dict[str, User] = {}
        self.assets: dict[str, Asset] = {}
        self.alerts: dict[str, Alert] = {}
        self.ingests: dict[str, list[dict]] = {}  # scenario key -> ingest results, in order
        self.plan: list[tuple[dt.datetime, int, str, Callable[[], None]]] = []
        self.reports: dict[str, object] = {}

    def day(self, n: float, minutes: int = 0) -> dt.datetime:
        return self.T + dt.timedelta(days=n, minutes=minutes)

    # Users, assets and records ------------------------------------------------------------------
    def seed_users(self) -> None:
        b_day = self.T - dt.timedelta(days=self.world.spec["boundary_days_ago"])
        for spec in self.world.spec["users"]:
            user = User(username=spec["username"], name=spec["name"], role=spec["role"], language=spec.get("language", "en"), is_demo=True,
                        email=spec.get("email"), phone=spec.get("phone"), channels=spec.get("channels", ["in_app", "email"]))
            self.db.add(user)
            self.db.flush()
            self.users[spec["username"]] = user
        admin = next((u for u in self.users.values() if u.role == "admin"), None)
        for spec in self.world.spec["users"]:
            for area in spec.get("areas", []):
                self.db.add(OfficialArea(user_id=self.users[spec["username"]].id, district=area["district"], mandal=area.get("mandal"),
                                         added_by=admin.id if admin else None, added_at=b_day))
        self.db.flush()

    def seed_assets(self) -> None:
        baseline = (self.T - dt.timedelta(days=self.world.spec["baseline_days_ago"])).date()
        b_day = self.T - dt.timedelta(days=self.world.spec["boundary_days_ago"])
        for spec in self.world.spec["assets"]:
            shape_m = self.world.asset_shape_m(spec)
            asset = Asset(
                asset_key=spec["key"], name=spec["name"], name_te=spec.get("name_te"),
                type="lake" if "lake" in spec else "recovered_parcel", cohort=spec["cohort"],
                district=spec["area"][0], mandal=spec["area"][1], village=spec["area"][2],
                survey_numbers=spec.get("survey", []), area_acres=round(shape_m.area / ACRE, 2),
                custodian_agency="Demo Agency", has_cctv=bool(spec.get("cctv")), baseline_date=baseline,
                is_demo=True, notes="Fictional demo asset. Not a real place.",
            )
            self.db.add(asset)
            self.db.flush()
            status = STATUS_BY_COHORT[spec["cohort"]]
            bsvc.add_version(
                self.db, asset, kind="ftl" if "lake" in spec else "parcel", status=status,
                geometry=json.loads(json.dumps(self.world.lonlat_multipolygon(shape_m).__geo_interface__)),
                source_name="Demo boundary (fictional)" if status != "derived" else "Demo derived outline (fictional)",
                source_date=b_day.date(), notification_ref=spec.get("ref"),
                certified_by="Demo Survey Office" if status in ("physically_marked", "final_notification") else None,
                valid_from=b_day.date(), at=b_day,
            )
            self.assets[spec["key"]] = asset

    def _wkt(self, poly_m) -> WKTElement:
        return WKTElement(self.world.lonlat_multipolygon(poly_m).wkt, srid=4326)

    def seed_records(self) -> None:
        for p in self.world.spec.get("permits", []):
            self.db.add(Permit(source=p["source"], ref=p["ref"], kind=p["kind"], geom=self._wkt(self.world.box_m(p["asset"], p["box"])),
                               valid_from=self.day(p["valid_from_days"]).date(), is_demo=True))
        for w in self.world.spec.get("works", []):
            self.db.add(AuthorisedWork(agency=w["agency"], description=w["description"], ref=w["ref"], geom=self._wkt(self.world.box_m(w["asset"], w["box"])),
                                       starts_on=self.day(w["starts_days"]).date(), ends_on=self.day(w["ends_days"]).date(), is_demo=True))
        for c in self.world.spec.get("court_cases", []):
            self.db.add(CourtCase(court=c["court"], case_no=c["case_no"], status=c["status"], asset_id=self.assets[c["asset"]].id,
                                  next_hearing=self.day(c["next_hearing_days"]).date(), last_checked_at=self.T, is_demo=True))
        self.db.flush()

    def seed_documents(self) -> None:
        """Every demo asset carries its fictional legal documents (D-057)."""
        b_day = (self.T - dt.timedelta(days=self.world.spec["boundary_days_ago"])).date()
        courts = {c["asset"]: c for c in self.world.spec.get("court_cases", [])}
        admin = self.users.get("demo.admin")
        for spec in self.world.spec["assets"]:
            asset = self.assets[spec["key"]]
            for d in demo_docs.documents_for(spec, spec["cohort"], b_day.isoformat(), courts.get(spec["key"])):
                content = None
                if d["pdf"]:
                    content = demo_docs.simple_pdf(d["title"], d["pdf"] + [f"Issued by: {d['issued_by']}", f"Reference: {d['reference'] or 'none'}"])
                doc_svc.add(
                    self.db, asset, doc_type=d["doc_type"], title=d["title"], reference=d["reference"],
                    issued_on=dt.date.fromisoformat(d["issued_on"]) if d["issued_on"] else None, issued_by=d["issued_by"],
                    content=content, file_name=f"{d['doc_type']}-{spec['key']}.pdf" if content else None,
                    content_type="application/pdf" if content else None, actor_id=admin.id if admin else None,
                    at=self.T - dt.timedelta(days=self.world.spec["boundary_days_ago"]),
                )

    # Scenarios ----------------------------------------------------------------------------------
    def _candidate(self, sc: dict, *, first_changed: int, last_clear: int, grow: float = 1.0, sensor_basis: str = "optical_only", confidence: float = 0.8) -> ingest_svc.CandidateIn:
        fc, lc = self.day(first_changed).date(), self.day(last_clear).date()
        window = render.chip_window(self.world, sc, grow)
        before = render.render_chip(self.world, sc, when=lc, after=False, grow=grow, window=window)
        after = render.render_chip(self.world, sc, when=fc, after=True, grow=grow, window=window)
        obs_t = dt.datetime.combine(fc, dt.time(1, 0), tzinfo=dt.timezone.utc)
        sensor = "demo_synthetic_radar" if sensor_basis == "radar_only" else "demo_synthetic_optical"
        observations = [
            {"sensor": sensor, "scene_id": f"DEMO-{sc['key']}-{(obs_t + dt.timedelta(days=d)).date().isoformat()}", "acquired_at": obs_t + dt.timedelta(days=d),
             "cloud_pct": None if sensor_basis == "radar_only" else 4.0, "processing_version": DEMO_RULES, "licence_notice": LICENCE}
            for d in (0, 6)
        ]
        change = sc["change"]
        return ingest_svc.CandidateIn(
            asset_id=self.assets[sc["asset"]].id,
            geometry=json.loads(json.dumps(self.world.lonlat_multipolygon(self.world.change_m(sc, grow)).__geo_interface__)),
            change_type=change["type"], stage_estimate=change.get("stage"), first_changed_at=fc, last_clear_at=lc,
            observations=observations, sensor_basis=sensor_basis, confidence=confidence, rule_version=DEMO_RULES,
            area_growth=round(grow - 1, 3) if grow != 1 else None,
            before_chip_png_b64=base64.b64encode(before).decode(), after_chip_png_b64=base64.b64encode(after).decode(),
        )

    def _add(self, when: dt.datetime, label: str, fn: Callable[[], None]) -> None:
        self.plan.append((when, len(self.plan), label, fn))

    def plan_scenario(self, sc: dict) -> None:
        det = sc["detect"]

        def detect() -> None:
            body = self._candidate(sc, first_changed=det["first_changed"], last_clear=det["last_clear"],
                                   sensor_basis=det.get("sensor_basis", "optical_only"), confidence=det.get("confidence", 0.8))
            out = ingest_svc.ingest(self.db, body, at=self.day(det["day"]))
            self.alerts[sc["key"]] = self.db.get(Alert, out["alert_id"])
            self.ingests.setdefault(sc["key"], []).append({**out, "day": det["day"], "grow": 1.0, "first_changed": det["first_changed"]})

        self._add(self.day(det["day"]), f"{sc['key']}: detect", detect)
        for i, step in enumerate(sc.get("steps", [])):
            # Officials act from 09:00 IST, an hour before the screen's daily time: a review the next
            # morning comes within the 24 hours an acknowledgement is asked for (D-059).
            when = self.day(step["day"], minutes=-60 + 20 * i)
            self._add(when, f"{sc['key']}: {step['do']}", self._step(sc, step, when))

    def _step(self, sc: dict, step: dict, when: dt.datetime) -> Callable[[], None]:
        def run() -> None:
            alert = self.alerts[sc["key"]]
            by = self.users.get(step.get("by", ""))
            do = step["do"]
            if do == "review":
                lifecycle.review(self.db, alert, by, step["outcome"], step["note"], at=when)
            elif do == "decide":
                if alert.state == "OPEN":
                    lifecycle.transition(self.db, alert, "UNDER_REVIEW", actor=by, note="Review started", at=when - dt.timedelta(minutes=5))
                lifecycle.transition(self.db, alert, step["to"], actor=by, note=step["note"], at=when)
            elif do == "close":
                lifecycle.transition(self.db, alert, "CLOSED", actor=by, note=step["note"], at=when)
            elif do == "pack":
                pack_svc.build(self.db, alert, by, at=when)
            elif do == "recheck":
                body = self._candidate(sc, first_changed=step["first_changed"], last_clear=step["last_clear"], grow=step["grow"])
                out = ingest_svc.ingest(self.db, body, at=when)
                self.alerts[sc["key"]] = self.db.get(Alert, out["alert_id"])
                self.ingests[sc["key"]].append({**out, "day": step["day"], "grow": step["grow"], "first_changed": step["first_changed"]})
            else:
                raise ValueError(f"Unknown demo step {do}")

        return run

    def plan_notifier(self) -> None:
        """The notifier's follow-up and outbox, each simulated morning from the first incident to today."""
        first = min(sc["detect"]["day"] for sc in self.world.spec["scenarios"])
        hour = float(self.world.spec.get("notifier_hour_utc", 3.5))
        start = dt.datetime.combine(self.day(first).date(), dt.time(), tzinfo=dt.timezone.utc) + dt.timedelta(hours=hour)
        when = start
        while when <= self.T:
            self._add(when, "notifier", lambda at=when: notify.tick(self.db, at))
            when += dt.timedelta(days=1)
        self._add(self.T, "notifier", lambda: notify.tick(self.db, self.T))

    # Citizen reports (D-062) ----------------------------------------------------------------------
    def _report_point(self, spec: dict) -> tuple[float, float]:
        dx, dy = spec.get("offset", [0, 0])
        if "near" in spec:
            sc = next(s for s in self.world.spec["scenarios"] if s["key"] == spec["near"])
            c = self.world.change_m(sc).centroid
            e, n = c.x, c.y
        elif "asset" in spec:
            e, n = self.world.asset_centre_m(self.world.asset(spec["asset"]))
        else:
            e, n = spec["at"]
        lon, lat = self.world.to_lonlat(e + dx, n + dy)
        return round(lon, 6), round(lat, 6)

    @staticmethod
    def _demo_photo(label: str) -> bytes:
        """A drawn picture, plainly marked as a demo, never a real photograph."""
        import io

        from PIL import Image, ImageDraw

        img = Image.new("RGB", (640, 480), (150, 175, 205))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 260, 640, 480], fill=(96, 128, 76))
        d.polygon([(120, 330), (260, 230), (420, 330)], fill=(132, 96, 60))
        d.rectangle([0, 0, 640, 34], fill=(75, 58, 110))
        d.text((12, 10), f"DEMO PHOTO (fictional): {label}", fill=(255, 255, 255))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=85)
        return out.getvalue()

    def plan_citizen(self) -> None:
        for spec in self.world.spec.get("citizen_reports", []):
            when = self.day(spec["day"], minutes=150)
            self._add(when, f"citizen {spec['key']}: report", self._citizen_report(spec, when))
            for i, step in enumerate(spec.get("steps", [])):
                at = self.day(step["day"], minutes=-40 + 20 * i)
                self._add(at, f"citizen {spec['key']}: {step['do']}", self._citizen_step(spec, step, at))

    def _citizen_report(self, spec: dict, when: dt.datetime) -> Callable[[], None]:
        def run() -> None:
            lon, lat = self._report_point(spec)
            channel = spec["channel"]
            phone = spec.get("phone")
            via = None
            if phone:
                via = "whatsapp" if channel == "whatsapp" else "staff" if channel in citizen.STAFF_CHANNELS else "otp"
            report = citizen.submit(
                self.db, channel=channel, language=spec["language"], what=spec["what"], at=when,
                source=citizen.source_hash(f"demo-seed:{spec['key']}"), lon=lon, lat=lat, description=spec.get("description"),
                photos=[self._demo_photo(spec["what"])] if spec.get("photo") else [], phone=phone, phone_verified_via=via,
                wants_updates=bool(phone), source_ref=spec.get("source_ref"), entered_by=self.users.get(spec.get("by", "")),
                is_demo=True,
            )
            self.reports[spec["key"]] = report

        return run

    def _citizen_step(self, spec: dict, step: dict, at: dt.datetime) -> Callable[[], None]:
        def run() -> None:
            report = self.reports[spec["key"]]
            by = self.users[step["by"]]
            if step["do"] == "check":
                citizen.record_check(self.db, report, by, step["outcome"], step["note"], at)
            elif step["do"] == "close":
                citizen.close(self.db, report, by, step["reason"], step["note"], at, department=step.get("department"))
            else:
                raise ValueError(f"Unknown citizen step {step['do']}")

        return run

    # Weekly records -----------------------------------------------------------------------------
    def _open_on(self, alert_id: int, day: dt.date) -> bool:
        """Was this incident still open (not yet dismissed or closed) at the end of that day?"""
        ended = self.db.scalar(text(
            "SELECT min(at) FROM audit_log WHERE entity = 'alert' AND entity_id = :i AND action = 'alert.transition' "
            "AND details->>'to' IN ('DISMISSED', 'CLOSED')"), {"i": str(alert_id)})
        return ended is None or ended.date() > day

    def seed_weeks(self) -> int:
        """Eight weekly screens of the demo world, each with every asset's week (D-057)."""
        by_asset: dict[str, list[tuple[dict, dict]]] = {}
        for sc in self.world.spec["scenarios"]:
            for result in self.ingests.get(sc["key"], []):
                by_asset.setdefault(sc["asset"], []).append((sc, result))
        rows = 0
        for k in range(WEEKS - 1, -1, -1):
            as_of = (self.T - dt.timedelta(days=7 * k)).date()
            week = weeks_svc.iso_week(as_of)
            started = min(dt.datetime.combine(as_of, dt.time(2, 0), tzinfo=dt.timezone.utc), self.T - dt.timedelta(minutes=15))
            run = ScreenRun(as_of=as_of, rule_version=DEMO_RULES, rules_sha256=hashlib.sha256(DEMO_RULES.encode()).hexdigest(),
                            collection="demo-synthetic", started_at=started, finished_at=started + dt.timedelta(minutes=12),
                            assets_total=len(self.assets), outcomes={}, is_demo=True)
            self.db.add(run)
            self.db.flush()
            coverage: dict[str, int] = {}
            for key, asset in self.assets.items():
                cloudy = k == CLOUDY_WEEK and key in CLOUDY_ASSETS
                changes, drawn = [], []
                for sc, result in by_asset.get(key, []):
                    seen = self.day(result["day"]).date()
                    # Drawn from the week the screen found it, so each image agrees with its week's record.
                    if seen <= as_of and result["outcome"] != "closed_by_legal_check":
                        drawn.append((sc, result["grow"]))
                    if cloudy or seen > as_of:
                        continue
                    if as_of - dt.timedelta(days=7) < seen:
                        changes.append({"candidate_id": result["candidate_id"], "alert_id": result["alert_id"], "outcome": result["outcome"]})
                    elif result["outcome"] in ("created", "recorded_on_open_incident") and self._open_on(result["alert_id"], as_of):
                        changes.append({"candidate_id": result["candidate_id"], "alert_id": result["alert_id"], "outcome": "recorded_on_open_incident"})
                if cloudy:
                    status, image, looks = "no_usable_look", None, 0
                else:
                    look = as_of - dt.timedelta(days=2)
                    png = render.render_week(self.world, key, when=look, week=week, changes=drawn)
                    image = weeks_svc.store_image(asset, as_of, base64.b64encode(png).decode())
                    status, looks = ("candidate_found" if changes else "no_candidate"), 2
                coverage[status] = coverage.get(status, 0) + 1
                self.db.add(AssetScreen(
                    run_id=run.id, asset_id=asset.id, status=status, looks=looks,
                    first_look=None if cloudy else as_of - dt.timedelta(days=7), last_look=None if cloudy else as_of - dt.timedelta(days=2),
                    candidates=len(changes), legacy_changes=0, counts={}, week=week, image_key=image,
                    image_date=None if cloudy else as_of - dt.timedelta(days=2),
                    image_scene_id=None if cloudy else f"DEMO-WEEK-{week}-{key}",
                    changes=weeks_svc.change_entries(self.db, asset.id, changes),
                ))
                rows += 1
            self.db.flush()
            chain.record(self.db, actor_id=None, action="screen.run", entity="screen_run", entity_id=run.id,
                         details={"as_of": as_of.isoformat(), "rule_version": DEMO_RULES, "coverage": coverage, "demo": True},
                         at=run.finished_at)
        return rows

    # Run ------------------------------------------------------------------------------------------
    def run(self) -> dict:
        self.seed_users()
        self.seed_assets()
        self.seed_records()
        self.seed_documents()
        for sc in self.world.spec["scenarios"]:
            self.plan_scenario(sc)
        self.plan_citizen()
        self.plan_notifier()
        for when, _, label, fn in sorted(self.plan, key=lambda p: (p[0], p[1])):
            try:
                fn()
            except lifecycle.Refused as exc:
                raise RuntimeError(f"Demo step refused ({label}): {exc.message}") from exc
        weeks = self.seed_weeks()
        last_run = self.db.scalar(select(ScreenRun.id).where(ScreenRun.is_demo.is_(True)).order_by(ScreenRun.as_of.desc(), ScreenRun.id.desc()).limit(1))
        satellite_checked = citizen.on_screen_stored(self.db, last_run, self.T) if last_run else 0
        latest = weeks_svc.iso_week(self.T.date())
        digests = notify.send_digests(self.db, latest, is_demo=True, at=self.T)
        notify.tick(self.db, self.T + dt.timedelta(minutes=1))
        self.db.flush()
        return {
            "seed_date": self.T.date().isoformat(),
            "users": len(self.users),
            "assets": len(self.assets),
            "incidents": {k: f"{a.state}{'/' + a.resolution if a.resolution else ''}" for k, a in self.alerts.items()},
            "weekly_records": weeks,
            "notifications": self.db.scalar(text("SELECT count(*) FROM notifications WHERE is_demo")),
            "digests": digests["sent"],
            "citizen_reports": {k: f"{r.status}{'/' + r.closed_reason if r.closed_reason else ''}" for k, r in self.reports.items()},
            "citizen_satellite_checked": satellite_checked,
        }


def render_tiles(zmin: int = 11, zmax: int = 17, force: bool = False) -> int:
    world = World.load()
    renderer = render.TileRenderer(world)
    bounds = world.bounds_lonlat(margin_m=1500)
    count = 0
    for z in range(zmin, zmax + 1):
        xs, ys = render.tile_range(z, bounds)
        for x in xs:
            for y in ys:
                key = f"tiles/demo/{z}/{x}/{y}.png"
                if not force and store.head_object(key) is not None:
                    continue
                store.put_object(key, renderer.render(z, x, y))
                count += 1
    w, s, e, n = world.bounds_lonlat(margin_m=300)
    store.put_object("tiles/demo/meta.json", json.dumps({"bounds": [w, s, e, n], "center": list(world.origin), "minzoom": zmin, "maxzoom": zmax}).encode())
    return count


def seed(db: Session, today: dt.date | None = None) -> dict:
    if db.scalar(select(Asset.id).where(Asset.is_demo.is_(True)).limit(1)) is not None:
        raise RuntimeError("Demo data already exists. Reset the database first: python -m app.seed.reset")
    summary = Seeder(db, today).run()
    db.commit()
    return summary


if __name__ == "__main__":
    from app.db import SessionLocal

    parser = argparse.ArgumentParser()
    parser.add_argument("--no-tiles", action="store_true")
    parser.add_argument("--today", type=dt.date.fromisoformat)
    args = parser.parse_args()
    with SessionLocal() as session:
        print(json.dumps(seed(session, args.today), indent=1))
    if not args.no_tiles:
        print(f"tiles rendered: {render_tiles()}")
