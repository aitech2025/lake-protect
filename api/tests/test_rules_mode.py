"""M1: mode by cohort (section 6.1) and the boundary-status rules that feed it."""
import pytest

from app.enums import BoundaryStatus, Cohort
from app.rules import config as rules
from tests.factories import auth, make_asset, make_user

MODE_BY_COHORT = [
    ("A_RECOVERED", "ACTION"),
    ("B_FINAL", "ACTION"),
    ("C_PRELIM", "VERIFY"),
    ("D_UNNOTIFIED", "WATCH"),
    ("E_AGENCY", "ACTION"),
    ("F_REVENUE", "WATCH"),
]


@pytest.mark.parametrize("cohort,mode", MODE_BY_COHORT)
def test_mode_by_cohort(cohort, mode):
    assert rules.mode_for_cohort(cohort).value == mode


def test_every_cohort_has_exactly_one_mode():
    assert set(rules.rules()["mode_by_cohort"]) == {c.value for c in Cohort}


@pytest.mark.parametrize(
    "status,cohort",
    [
        ("physically_marked", "A_RECOVERED"),
        ("final_notification", "B_FINAL"),
        ("preliminary_notification", "C_PRELIM"),
        ("derived", "D_UNNOTIFIED"),
        ("surveyed_agency", "E_AGENCY"),
        ("survey_number_only", "F_REVENUE"),
    ],
)
def test_cohort_follows_boundary_status(status, cohort):
    assert rules.cohort_for_status(status).value == cohort


def test_only_confirmed_boundaries_can_lead_to_action():
    confirmed = {s.value for s in BoundaryStatus if rules.is_confirmed_status(s.value)}
    assert confirmed == {"physically_marked", "final_notification", "surveyed_agency"}


def test_buffer_width_follows_lake_size():
    assert rules.lake_buffer_width_m(10.0) == 30
    assert rules.lake_buffer_width_m(9.99) == 9


@pytest.mark.parametrize("cohort,mode", MODE_BY_COHORT)
def test_api_reports_mode_for_each_cohort(db, client, cohort, mode):
    asset = make_asset(db, cohort=cohort)
    analyst = make_user(db, "analyst")
    body = client.get(f"/assets/{asset.id}", headers=auth(analyst)).json()
    assert body["properties"]["cohort"] == cohort
    assert body["properties"]["mode"] == mode
    assert body["properties"]["boundary_confirmed"] == (mode == "ACTION")
