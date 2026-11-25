"""Test helpers. Everything made here is fictional test data and never leaves the test database."""
from __future__ import annotations

import datetime as dt
import itertools
import math

from shapely.geometry import box, mapping

from app.models import Asset, User
from app.security import issue_token
from app.services import boundaries as bsvc

_seq = itertools.count(1)

# Open sea in the Bay of Bengal, inside UTM zone 44N: no real lake, parcel or person can sit here.
TEST_LON, TEST_LAT = 81.50, 14.50


def square(lon: float = TEST_LON, lat: float = TEST_LAT, side_m: float = 300.0) -> dict:
    dlat = side_m / 111_320 / 2
    dlon = side_m / (111_320 * math.cos(math.radians(lat))) / 2
    return mapping(box(lon - dlon, lat - dlat, lon + dlon, lat + dlat))


def offset(lon: float, lat: float, east_m: float = 0.0, north_m: float = 0.0) -> tuple[float, float]:
    return lon + east_m / (111_320 * math.cos(math.radians(lat))), lat + north_m / 111_320


def rect(east_from: float, east_to: float, north_from: float, north_to: float, lon: float = TEST_LON, lat: float = TEST_LAT) -> dict:
    """A rectangle given in metres east and north of a centre point."""
    x0, y0 = offset(lon, lat, east_from, north_from)
    x1, y1 = offset(lon, lat, east_to, north_to)
    return mapping(box(x0, y0, x1, y1))


def _png() -> str:
    import base64
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (120, 90, 60)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


PNG_B64 = _png()
_scene = itertools.count(1)


def candidate_in(
    asset,
    *,
    geometry: dict | None = None,
    change_type: str = "soil_fill",
    stage: str | None = "soil_dumped",
    first_changed: dt.date = dt.date(2025, 6, 10),
    last_clear: dt.date | None = dt.date(2025, 6, 1),
    chips: bool = True,
    days_apart: int = 6,
    sensor_basis: str = "optical_only",
    **extra,
):
    from app.services.ingest import CandidateIn

    t0 = dt.datetime.combine(first_changed, dt.time(5, 0), tzinfo=dt.timezone.utc)
    obs = [
        {"sensor": "test-sensor", "scene_id": f"TEST-{next(_scene)}", "acquired_at": t0 + dt.timedelta(days=d), "licence_notice": "Test fixture, not satellite data"}
        for d in (0, days_apart)
    ]
    return CandidateIn(
        asset_id=asset.id,
        geometry=geometry or square(side_m=60),
        change_type=change_type,
        stage_estimate=stage,
        first_changed_at=first_changed,
        last_clear_at=last_clear,
        observations=obs,
        sensor_basis=sensor_basis,
        confidence=0.8,
        rule_version="test-rules",
        before_chip_png_b64=PNG_B64 if chips else None,
        after_chip_png_b64=PNG_B64 if chips else None,
        **extra,
    )


def ingest(db, asset, *, at: dt.datetime | None = None, **kw):
    from app.models import Alert
    from app.services import ingest as ingest_svc

    out = ingest_svc.ingest(db, candidate_in(asset, **kw), at=at or dt.datetime(2025, 6, 20, 6, tzinfo=dt.timezone.utc))
    return out, db.get(Alert, out["alert_id"])


class Team:
    """One fictional account per role (D-057): an admin and two viewers."""

    def __init__(self, db):
        self.admin = make_user(db, "admin")
        self.viewer = make_user(db, "viewer")
        self.viewer2 = make_user(db, "viewer")


def review(db, alert, user, outcome: str = "real_change", note: str = "Test review", at: dt.datetime | None = None):
    from app.workflow import incidents

    return incidents.review(db, alert, user, outcome, note, at=at or dt.datetime(2025, 6, 21, 6, tzinfo=dt.timezone.utc))


def decide(db, alert, admin, to: str = "CONFIRMED", note: str = "Test decision", at: dt.datetime | None = None):
    """Admin decision, starting the review first if no viewer has."""
    from app.workflow import incidents

    at = at or dt.datetime(2025, 6, 22, 6, tzinfo=dt.timezone.utc)
    if alert.state == "OPEN":
        incidents.transition(db, alert, "UNDER_REVIEW", actor=admin, note="Review started", at=at - dt.timedelta(minutes=5))
    return incidents.transition(db, alert, to, actor=admin, note=note, at=at)


def add_pack_row(db, alert, user):
    """Stand-in for a generated pack: the guard only checks that a pack exists."""
    from app.models import EvidencePack

    db.add(EvidencePack(alert_id=alert.id, version=1, pdf_path="test.pdf", zip_path="test.zip", manifest_sha256="0" * 64,
                        generated_by=user.id, generated_at=dt.datetime(2025, 6, 26, tzinfo=dt.timezone.utc)))
    db.flush()


def make_user(db, role: str, *, name: str | None = None, area: dict | None = None, is_demo: bool = True,
              email: str | None = None, phone: str | None = None, channels: list[str] | None = None, language: str = "en") -> User:
    n = next(_seq)
    user = User(username=f"test-{role}-{n}", name=name or f"Test {role} {n}", role=role, is_demo=is_demo, email=email, phone=phone,
                channels=channels or ["in_app", "email"], language=language)
    if area is not None:
        from geoalchemy2.elements import WKTElement
        from shapely.geometry import MultiPolygon, shape

        g = shape(area)
        user.area_geom = WKTElement((MultiPolygon([g]) if g.geom_type == "Polygon" else g).wkt, srid=4326)
    db.add(user)
    db.flush()
    return user


def auth(user: User) -> dict:
    return {"Authorization": f"Bearer {issue_token(user)}"}


def make_asset(
    db,
    *,
    cohort: str = "A_RECOVERED",
    type: str = "lake",
    kind: str = "ftl",
    status: str | None = None,
    geometry: dict | None = None,
    baseline: dt.date = dt.date(2025, 1, 1),
    valid_from: dt.date = dt.date(2025, 1, 1),
    name: str | None = None,
    district: str | None = None,
    mandal: str | None = None,
    village: str | None = None,
) -> Asset:
    """A test asset with a first boundary version whose status matches the cohort."""
    status_by_cohort = {
        "A_RECOVERED": "physically_marked",
        "B_FINAL": "final_notification",
        "C_PRELIM": "preliminary_notification",
        "D_UNNOTIFIED": "derived",
        "E_AGENCY": "surveyed_agency",
        "F_REVENUE": "survey_number_only",
    }
    n = next(_seq)
    asset = Asset(
        asset_key=f"test-asset-{n}",
        name=name or f"Test Cheruvu {n}",
        type=type,
        cohort=cohort,
        baseline_date=baseline,
        is_demo=True,
        survey_numbers=[],
        district=district,
        mandal=mandal,
        village=village,
    )
    db.add(asset)
    db.flush()
    bsvc.add_version(
        db,
        asset,
        kind=kind,
        status=status or status_by_cohort[cohort],
        geometry=geometry or square(),
        source_name="Test fixture",
        valid_from=valid_from,
    )
    return asset


def cover(db, user, district: str, mandal: str | None = None) -> None:
    """Give an official an area (what the admin's Officials page does)."""
    from app.models import OfficialArea

    db.add(OfficialArea(user_id=user.id, district=district, mandal=mandal, added_at=dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc)))
    db.flush()
