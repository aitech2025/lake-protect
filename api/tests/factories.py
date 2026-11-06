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


def make_user(db, role: str, *, name: str | None = None, area: dict | None = None, is_demo: bool = True) -> User:
    n = next(_seq)
    user = User(username=f"test-{role}-{n}", name=name or f"Test {role} {n}", role=role, is_demo=is_demo)
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
