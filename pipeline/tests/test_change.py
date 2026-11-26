"""Change rules, version 0 (CONTEXT.md section 8.4), on synthetic class stacks.

A 30 x 30 pixel scene at 10 m: the west half is land (bare soil), the east half is lake. A block
at the shore changes as each test needs.
"""
import datetime as dt

import numpy as np

from lake_protect.change import detect
from lake_protect.indices import BARE, BUILT, MASKED, OTHER, VEG, WATER, classify

H = W = 30
AOI = np.ones((H, W), bool)
BASELINE = dt.date(2024, 7, 19)


def looks(start: dt.date, n: int, step: int = 10) -> list[dt.date]:
    return [start + dt.timedelta(days=step * i) for i in range(n)]


def scene() -> np.ndarray:
    a = np.full((H, W), WATER, np.uint8)
    a[:, :12] = BARE
    return a


BLOCK = (slice(10, 15), slice(12, 16))  # 5 x 4 = 20 pixels = 2,000 sq m, touching the shore


def stack(dates, change_from: int | None, new=BARE, block=BLOCK, pattern=None):
    out = []
    for i, _ in enumerate(dates):
        s = scene()
        if pattern is not None:
            s[block] = pattern[i]
        elif change_from is not None and i >= change_from:
            s[block] = new
        out.append(s)
    return np.stack(out)


def run(dates, cls, as_of=None, baseline=BASELINE):
    return detect(dates, cls, AOI, baseline, as_of or dates[-1])


def test_soil_fill_at_the_shore_is_found_with_its_dated_bracket():
    dates = looks(dt.date(2024, 9, 1), 40)
    res = run(dates, stack(dates, 30))
    assert len(res.candidates) == 1
    c = res.candidates[0]
    assert c.change_type == "soil_fill" and c.stage == "soil_dumped"
    assert c.first_changed_at == dates[30] and c.last_clear_at == dates[29]
    assert c.area_sq_m == 2000
    assert len(c.changed_idx) == 10


def test_water_loss_alone_never_becomes_a_candidate():
    """Invariant 8: water turning to vegetation (weed cover, drying) is counted, never alerted."""
    dates = looks(dt.date(2024, 9, 1), 40)
    res = run(dates, stack(dates, 30, new=VEG))
    assert res.candidates == [] and res.counts["px_water_loss_only"] >= 20


def test_one_changed_look_is_not_persistence():
    dates = looks(dt.date(2024, 9, 1), 40)
    res = run(dates, stack(dates, 39))
    assert res.candidates == []


def test_a_reversal_breaks_the_run():
    dates = looks(dt.date(2024, 9, 1), 40)
    pattern = [WATER] * 30 + [BARE, BARE, WATER, BARE, BARE, WATER, BARE, BARE, WATER, BARE]
    res = run(dates, stack(dates, None, pattern=pattern))
    assert res.candidates == []


def test_masked_and_mixed_looks_do_not_break_the_run():
    dates = looks(dt.date(2024, 9, 1), 40)
    pattern = [WATER] * 30 + [BARE, MASKED, BARE, OTHER, BARE, MASKED, BARE, BARE, MASKED, BARE]
    res = run(dates, stack(dates, None, pattern=pattern))
    assert len(res.candidates) == 1


def test_below_the_minimum_area_is_dropped():
    dates = looks(dt.date(2024, 9, 1), 40)
    small = (slice(10, 13), slice(12, 15))  # 9 pixels = 900 sq m
    res = run(dates, stack(dates, 30, block=small))
    assert res.candidates == []


def test_change_before_the_baseline_is_never_a_candidate():
    """Rule 3 and invariant 6 in the pipeline: old change is kept apart as legacy."""
    dates = looks(dt.date(2023, 1, 1), 70)
    res = run(dates, stack(dates, 30), baseline=dates[40])
    assert res.candidates == [] and len(res.legacy) == 1


def test_the_same_season_last_year_suppresses_a_seasonal_change():
    """Bare in the same months a year earlier means the lake edge dries every year."""
    dates = looks(dt.date(2023, 9, 1), 80)
    pattern = []
    for d in dates:
        dry = d.month in (3, 4, 5)
        pattern.append(BARE if (dry and d.year == 2024) or d >= dt.date(2025, 3, 1) else WATER)
    res = run(dates, stack(dates, None, pattern=pattern), as_of=dates[-1])
    assert res.candidates == []
    assert res.counts["px_dropped_seasonal"] + res.counts["px_dropped_not_new"] >= 20


def test_a_class_that_came_and_went_last_year_is_not_new():
    """Novelty control: bare soil read as built in last year's wet months is not a new building."""
    dates = looks(dt.date(2024, 1, 1), 100, step=10)
    pattern = []
    for d in dates:
        wet_last_year = dt.date(2025, 7, 1) <= d < dt.date(2026, 1, 1) and d.month in (7, 8, 11, 12)
        pattern.append(BUILT if wet_last_year or d >= dt.date(2026, 6, 1) else BARE)
    res = run(dates, stack(dates, None, pattern=pattern), as_of=dates[-1])
    assert all(c.change_type != "building" for c in res.candidates)


def test_an_island_in_the_lake_is_not_soil_fill():
    """Soil fill must start at the shore; water dropping round a mid-lake shoal is not fill."""
    dates = looks(dt.date(2024, 9, 1), 40)
    island = (slice(10, 15), slice(22, 26))
    res = run(dates, stack(dates, 30, block=island))
    assert res.candidates == [] and res.counts.get("components_dropped_not_at_shore") == 1


def test_classes_follow_the_section_8_4_rules():
    def px(blue, green, red, nir, swir16):
        return {k: np.array([[v]], np.float32) for k, v in zip(["blue", "green", "red", "nir", "swir16"], [blue, green, red, nir, swir16])}

    clear = np.array([[True]])
    assert classify(px(0.05, 0.08, 0.05, 0.03, 0.02), clear)[0, 0] == WATER
    assert classify(px(0.04, 0.07, 0.04, 0.35, 0.18), clear)[0, 0] == VEG
    assert classify(px(0.10, 0.14, 0.20, 0.25, 0.35), clear)[0, 0] == BARE
    assert classify(px(0.12, 0.13, 0.15, 0.20, 0.22), clear)[0, 0] == BUILT
    assert classify(px(0.05, 0.08, 0.05, 0.03, 0.02), np.array([[False]]))[0, 0] == MASKED


def test_patches_close_together_are_one_change():
    """D-051: two qualifying patches 20 m apart are one candidate; specks never add up to one."""
    dates = looks(dt.date(2024, 9, 1), 40)
    pattern_blocks = [(slice(5, 10), slice(12, 14)), (slice(12, 17), slice(12, 14))]  # 10 px each, 2 px gap
    cls = stack(dates, None)
    for b in pattern_blocks:
        cls[30:, b[0], b[1]] = BARE
    res = run(dates, cls)
    assert len(res.candidates) == 1 and res.candidates[0].area_sq_m == 2000

    specks = stack(dates, None)
    for r0 in (2, 6, 10, 14, 18):
        specks[30:, r0:r0 + 2, 12:14] = BARE  # 4 px each, 2 px apart: none reaches 1,000 sq m alone
    res = run(dates, specks)
    assert res.candidates == []


def test_levelling_rule_reports_raw_and_kept_transition_pixels():
    """D-058: other-to-bare pixels are counted separately for tuning."""
    dates = looks(dt.date(2024, 9, 1), 40)
    pattern = [OTHER] * 30 + [BARE] * 10
    res = run(dates, stack(dates, None, pattern=pattern))
    assert len(res.candidates) == 1
    assert res.candidates[0].change_type == "levelling"
    assert res.counts["px_levelling_raw"] == 20
    assert res.counts["px_levelling_kept"] == 20
