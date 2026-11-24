"""Legal check (section 6.2): the decision order, zone location and the stored result."""
import datetime as dt

import pytest
from geoalchemy2.elements import WKTElement
from shapely.geometry import shape

from app.enums import AlertState as S
from app.enums import Mode, Zone
from app.models import AuthorisedWork, CourtCase, LegalCheck, Permit
from app.rules import config as rules
from app.rules.legal_check import Facts, decide
from tests.factories import ingest, make_asset, rect, square

# A 450 m lake is 20.25 ha, so its buffer is 30 m: FTL edge at 225 m, buffer to 255 m, ring to 355 m.
BIG_LAKE = square(side_m=450)
IN_FTL = square(side_m=60)
IN_BUFFER = rect(230, 250, -50, 50)
TOUCHES_FTL_EDGE = rect(225, 250, -50, 50)
IN_RING = rect(270, 310, -20, 20)
OUTSIDE = rect(400, 440, -20, 20)


def wkt(geojson: dict) -> WKTElement:
    g = shape(geojson)
    return WKTElement(f"MULTIPOLYGON((({', '.join(f'{x} {y}' for x, y in g.exterior.coords)})))", srid=4326)


def facts(**kw) -> Facts:
    base = dict(zone=Zone.inside_ftl, first_changed_at=dt.date(2025, 6, 10), baseline_date=dt.date(2025, 1, 1), mode=Mode.ACTION)
    return Facts(**{**base, **kw})


@pytest.mark.parametrize(
    "kw,result,flags",
    [
        (dict(zone=Zone.outside, first_changed_at=dt.date(2024, 1, 1), court_case_id=1), S.CLOSED_OUT_OF_SCOPE, set()),
        (dict(first_changed_at=dt.date(2024, 12, 1), work_id=1, court_case_id=1), S.CLOSED_LEGACY, set()),
        (dict(first_changed_at=dt.date(2025, 1, 1)), S.CLOSED_LEGACY, set()),  # on the baseline date
        (dict(work_id=1, court_case_id=1), S.CLOSED_AUTHORISED, set()),
        (dict(zone=Zone.watch_ring, permit_id=1), S.CLOSED_AUTHORISED, set()),
        (dict(zone=Zone.inside_ftl, permit_id=1), S.TRIAGE, {"permit_conflict"}),
        (dict(zone=Zone.buffer, permit_id=1, court_case_id=1), S.HOLD_LEGAL, {"permit_conflict"}),
        (dict(court_case_id=1, mode=Mode.WATCH), S.HOLD_LEGAL, set()),
        (dict(mode=Mode.WATCH), S.WATCH_LIST, set()),
        (dict(mode=Mode.VERIFY), S.TRIAGE, set()),
        (dict(), S.TRIAGE, set()),
    ],
)
def test_decide_follows_section_6_2_order(kw, result, flags):
    d = decide(facts(**kw))
    assert d.result == result and d.flags == flags


@pytest.mark.parametrize(
    "geometry,zone",
    [(IN_FTL, "inside_ftl"), (IN_BUFFER, "buffer"), (TOUCHES_FTL_EDGE, "buffer"), (IN_RING, "watch_ring"), (OUTSIDE, "outside")],
)
def test_zone_is_located_against_the_boundary_version(db, geometry, zone):
    asset = make_asset(db, cohort="B_FINAL", geometry=BIG_LAKE)
    out, alert = ingest(db, asset, geometry=geometry)
    assert out["legal_check"]["zone"] == zone
    assert alert.state == ("CLOSED" if zone == "outside" else "OPEN")


def test_result_stores_rule_version_boundary_version_and_matches(db):
    asset = make_asset(db, cohort="A_RECOVERED", geometry=BIG_LAKE)
    work = AuthorisedWork(agency="Test agency", description="Test restoration", ref="TEST-WORK-1", geom=wkt(IN_FTL), starts_on=dt.date(2025, 5, 1), is_demo=True)
    db.add(work)
    db.flush()
    out, alert = ingest(db, asset, geometry=square(side_m=40))
    lc = db.query(LegalCheck).filter_by(candidate_id=alert.candidate_id).one()
    assert (alert.state, alert.resolution, lc.result) == ("CLOSED", "auto", "CLOSED_AUTHORISED") and lc.matched_work_id == work.id
    assert lc.rule_version == rules.rule_version() and lc.boundary_version == 1 and lc.boundary_status == "physically_marked"
    assert lc.alert_class == "GOVT_LAND"


def test_work_outside_its_dates_does_not_authorise(db):
    asset = make_asset(db, cohort="B_FINAL", geometry=BIG_LAKE)
    db.add(AuthorisedWork(agency="Test", description="Old work", ref="TEST-OLD", geom=wkt(IN_FTL), starts_on=dt.date(2023, 1, 1), ends_on=dt.date(2023, 12, 31), is_demo=True))
    db.flush()
    _, alert = ingest(db, asset, geometry=square(side_m=40))
    assert alert.state == "OPEN"


def test_court_register_hit_holds_and_marks_disputed(db):
    asset = make_asset(db, cohort="B_FINAL", geometry=BIG_LAKE)
    db.add(CourtCase(court="Test court", case_no="TEST-1", status="pending", asset_id=asset.id, is_demo=True))
    db.flush()
    _, alert = ingest(db, asset)
    lc = db.query(LegalCheck).filter_by(candidate_id=alert.candidate_id).one()
    assert alert.state == "OPEN" and lc.result == "HOLD_LEGAL" and lc.alert_class == "DISPUTED" and lc.matched_court_case_id is not None


def test_disposed_court_case_is_not_a_live_matter(db):
    asset = make_asset(db, cohort="B_FINAL", geometry=BIG_LAKE)
    db.add(CourtCase(court="Test court", case_no="TEST-2", status="disposed", asset_id=asset.id, is_demo=True))
    db.flush()
    _, alert = ingest(db, asset)
    assert alert.state == "OPEN"


def test_permit_must_be_valid_on_the_change_date(db):
    asset = make_asset(db, cohort="B_FINAL", geometry=BIG_LAKE)
    db.add(Permit(source="Test", ref="TEST-P-EXPIRED", kind="building", geom=wkt(IN_RING), valid_from=dt.date(2020, 1, 1), valid_to=dt.date(2021, 1, 1), is_demo=True))
    db.flush()
    _, alert = ingest(db, asset, geometry=IN_RING)
    assert alert.state == "OPEN"
