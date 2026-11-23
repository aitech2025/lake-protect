"""Section 8.4: built needs radar, VV at least 3 dB above baseline (D-049)."""
import numpy as np

from lake_protect.radar import _median, _rise_db


def test_rise_is_the_mean_db_change_over_the_candidate():
    mask = np.zeros((4, 4), bool)
    mask[1:3, 1:3] = True
    before = np.full((4, 4), 0.05, np.float32)
    after = before * 2  # +3.01 dB
    assert _rise_db(after, before, mask) == 3.01


def test_too_few_valid_pixels_gives_no_answer():
    mask = np.ones((4, 4), bool)
    before = np.full((4, 4), np.nan, np.float32)
    before[0, 0] = 0.05
    assert _rise_db(np.full((4, 4), 0.1, np.float32), before, mask) is None


def test_median_over_dates_ignores_missing_looks():
    a = np.array([[0.1, np.nan]], np.float32)
    b = np.array([[0.3, 0.2]], np.float32)
    c = np.array([[0.2, 0.4]], np.float32)
    m = _median([a, b, c])
    assert np.allclose(m, [[0.2, 0.3]])
    assert _median([]) is None
