"""Priority score (section 6.4)."""
import pytest

from app.rules.priority import score


@pytest.mark.parametrize(
    "stage,area,growth,cohort,expected",
    [
        ("soil_dumped", 1_000, 0, "A_RECOVERED", 55.0),  # 35 + 0 + 0 + 20
        ("soil_dumped", 100_000, 0, "A_RECOVERED", 80.0),  # area factor 1
        ("land_levelled", 10_000, 0.5, "B_FINAL", 100 * (0.35 + 0.25 * 0.5 + 0.2 * 0.5 + 0.2 * 0.9)),
        ("building_rises", 1_000, 0, "C_PRELIM", 100 * (0.35 * 0.8 + 0.2 * 0.5)),
        ("occupied", 500, 3.0, "A_RECOVERED", 100 * (0.35 * 0.2 + 0 + 0.2 * 1 + 0.2)),  # area and growth clipped
    ],
)
def test_score_matches_formula(stage, area, growth, cohort, expected):
    total, factors = score(stage=stage, area_sq_m=area, growth=growth, cohort=cohort)
    assert total == pytest.approx(expected, abs=0.01)
    assert set(factors) >= {"stage", "area", "growth", "cohort", "rule_version"}


def test_score_is_owner_blind():
    import inspect

    params = set(inspect.signature(score).parameters)
    assert params == {"stage", "area_sq_m", "growth", "cohort"}
