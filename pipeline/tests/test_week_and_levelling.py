"""detect-v2 (DECISIONS.md D-058) and the weekly image of each asset (D-057)."""
import datetime as dt

import numpy as np
from shapely.geometry import box

from lake_protect import chips
from lake_protect.aoi import Grid
from lake_protect.change import CHANGE_NAMES, LEVELLING, transition_table
from lake_protect.indices import BARE, OTHER, VEG
from lake_protect.rules import rule_version, rules


def test_levelling_is_its_own_change_type():
    table = transition_table()
    assert CHANGE_NAMES[table[OTHER, BARE]] == "levelling" and table[OTHER, BARE] == LEVELLING
    assert CHANGE_NAMES[table[VEG, BARE]] == "clearing"
    assert rules()["stage_by_change"]["levelling"] == "land_levelled"
    assert rule_version() == "detect-v2"


def test_week_image_is_a_png_of_the_whole_asset():
    grid = Grid("EPSG:32644", 500000.0, 1620000.0, 40, 40, 10.0)
    rng = np.random.default_rng(1)
    bands = {k: rng.uniform(0.02, 0.3, (40, 40)).astype(np.float32) for k in ("red", "green", "blue")}
    primary = box(500100, 1619700, 500300, 1619900)
    png = chips.render_week(bands, grid=grid, primary_utm=primary, buffer_outer_utm=primary.buffer(30),
                            changes_utm=box(500150, 1619750, 500200, 1619800), when=dt.datetime(2026, 11, 20, 5, tzinfo=dt.timezone.utc),
                            scene_id="S2-TEST", week="2026-W47")
    assert png.startswith(b"\x89PNG") and len(png) > 2000
