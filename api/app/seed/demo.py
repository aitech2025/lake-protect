"""Seed the fictional demo (CONTEXT.md section 13, "Demo data rules").

    python -m app.seed.demo            # seed relative to today
    python -m app.seed.demo --no-tiles

Everything is invented, marked is_demo, and placed in open sea (DECISIONS.md D-015). Alerts are
not written directly: each scenario runs through the real ingest, legal check, priority and state
machine, in time order, so the demo shows the system's actual behaviour.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import uuid
from collections.abc import Callable

from geoalchemy2.elements import WKTElement
from shapely.geometry import box as shp_box
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import AlertState
from app.models import Alert, Asset, AuthorisedWork, CourtCase, Permit, User
from app.rules import config as rules
from app.services import boundaries as bsvc
from app.services import field as field_svc
from app.services import ingest as ingest_svc
from app.seed import demo_render as render
from app.seed.demo_world import World
from app.storage import store
from app.workflow import escalation
from app.workflow import state_machine as sm

STATUS_BY_COHORT = {
    "A_RECOVERED": "physically_marked",
    "B_FINAL": "final_notification",
    "C_PRELIM": "preliminary_notification",
    "D_UNNOTIFIED": "derived",
}
ACRE = 4046.86
DEMO_RULES = "demo-synthetic-v0"
LICENCE = "Synthetic demo image. Not satellite data."


class Seeder:
    def __init__(self, db: Session, today: dt.date | None = None):
        self.db = db
        self.world = World.load()
        self.T = dt.datetime.combine(today or dt.date.today(), dt.time(4, 30), tzinfo=dt.timezone.utc)
        self.users: dict[str, User] = {}
        self.assets: dict[str, Asset] = {}
        self.alerts: dict[str, Alert] = {}
        self.plan: list[tuple[dt.datetime, int, str, Callable[[], None]]] = []

    def day(self, n: float, minutes: int = 0) -> dt.datetime:
        return self.T + dt.timedelta(days=n, minutes=minutes)

    # Users, assets and records ------------------------------------------------------------------
    def seed_users(self) -> None:
        w, s, e, n = self.world.bounds_lonlat(margin_m=2000)
        south = self.world.to_lonlat(0, 0)[1]
        areas = {"demo.field1": shp_box(w, s, e, n), "demo.field2": shp_box(w, s, e, south + 0.004)}
        for spec in self.world.spec["users"]:
            user = User(username=spec["username"], name=spec["name"], role=spec["role"], language=spec.get("language", "en"), is_demo=True)
            if spec["username"] in areas:
                user.area_geom = WKTElement(f"MULTIPOLYGON((({', '.join(f'{x} {y}' for x, y in areas[spec['username']].exterior.coords)})))", srid=4326)
            self.db.add(user)
            self.db.flush()
            self.users[spec["username"]] = user

    def seed_assets(self) -> None:
        baseline = (self.T - dt.timedelta(days=self.world.spec["baseline_days_ago"])).date()
        b_day = self.T - dt.timedelta(days=self.world.spec["boundary_days_ago"])
        for spec in self.world.spec["assets"]:
            shape_m = self.world.asset_shape_m(spec)
            asset = Asset(
                asset_key=spec["key"], name=spec["name"], name_te=spec.get("name_te"),
                type="lake" if "lake" in spec else "recovered_parcel", cohort=spec["cohort"],
                district="Demo District", mandal="Demo Mandal", village="Demo Village",
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

        self._add(self.day(det["day"]), f"{sc['key']}: detect", detect)
        for i, step in enumerate(sc.get("steps", [])):
            when = self.day(step["day"], minutes=30 + 20 * i)
            self._add(when, f"{sc['key']}: {step['do']}", self._step(sc, step, when, i))

    def _step(self, sc: dict, step: dict, when: dt.datetime, i: int) -> Callable[[], None]:
        def run() -> None:
            alert = self.alerts[sc["key"]]
            by = self.users.get(step.get("by", ""))
            do = step["do"]
            if do == "confirm":
                sm.transition(self.db, alert, "CONFIRMED", actor=by, data={"image_pair_reviewed": True}, at=when)
            elif do == "assign":
                sm.transition(self.db, alert, "ASSIGNED", actor=by, data={"owner_user_id": self.users[step["to"]].id}, at=when)
            elif do == "close_not_real":
                sm.transition(self.db, alert, "CLOSED_NOT_REAL", actor=by, reason=step["reason"], data={"reason_code": step["code"]}, at=when)
                sm.transition(self.db, alert, "CLOSED_NOT_REAL", actor=self.users[step["cosign"]], at=when + dt.timedelta(hours=3))
            elif do in ("field", "false_alarm"):
                outcome = step.get("outcome", "false_alarm")
                self._field(sc, alert, by, outcome, step.get("stage"), step.get("reason"), when, i)
                if do == "false_alarm":
                    sm.transition(self.db, alert, "CLOSED_FALSE_ALARM", actor=self.users[step["cosign"]], at=when + dt.timedelta(hours=5))
            elif do == "recheck":
                body = self._candidate(sc, first_changed=step["first_changed"], last_clear=step["last_clear"], grow=step["grow"])
                ingest_svc.ingest(self.db, body, at=when)
            else:
                raise ValueError(f"Unknown demo step {do}")

        return run

    def _field(self, sc: dict, alert: Alert, officer: User, outcome: str, stage: str | None, reason: str | None, when: dt.datetime, i: int) -> None:
        centre = self.world.change_m(sc).centroid
        lon, lat = self.world.to_lonlat(centre.x + 8, centre.y - 6)  # standing at the edge of the change
        meta = field_svc.FieldCheckMeta(
            client_uuid=uuid.uuid5(uuid.NAMESPACE_URL, f"lake-protect-demo/{sc['key']}/{i}"),
            observed_at=when, lat=lat, lon=lon, gps_accuracy_m=6.0, outcome=outcome, observed_stage=stage,
            notes=reason or "Change seen on site (demo record).", reason=reason, device_time=when - dt.timedelta(seconds=40),
        )
        photos = [render.render_field_photo(self.assets[sc["asset"]].name, when, stage or "none", n) for n in (1, 2)]
        field_svc.submit(self.db, alert, officer, meta, photos, at=when + dt.timedelta(minutes=50))

    # Run ------------------------------------------------------------------------------------------
    def run(self) -> dict:
        self.seed_users()
        self.seed_assets()
        self.seed_records()
        for sc in self.world.spec["scenarios"]:
            self.plan_scenario(sc)
        for when, _, label, fn in sorted(self.plan, key=lambda p: (p[0], p[1])):
            try:
                fn()
            except sm.Refused as exc:
                raise RuntimeError(f"Demo step refused ({label}): {exc.message}") from exc
        misses = escalation.run(self.db, now=self.T)
        self.db.flush()
        return {
            "seed_date": self.T.date().isoformat(),
            "users": len(self.users),
            "assets": len(self.assets),
            "alerts": {k: a.state for k, a in self.alerts.items()},
            "timer_misses": len(misses),
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
