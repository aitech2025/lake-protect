"""Change candidates from a stack of classified looks (CONTEXT.md section 8.4, version 0).

Input: looks in time order (all acquired on or before `as_of`), one class per pixel per look.
For every pixel:

1. The current class Y is the class of the newest informative look (water, vegetation, bare,
   built; masked and mixed looks carry no information).
2. Walking back from the newest look, the run of looks still showing Y ends at the first look
   that shows anything else. That look is the old state X, and its date is the last clear date.
   A run that reaches the start of the window has no known start, so it never alerts.
3. Controls, all required: the old state held in the last looks before the change; two looks
   of the new state at least 5 days apart with no reversal (persistence); the newest look is
   recent; the change started after the asset's baseline date; the same months in the two
   previous years did not show the new state (seasonal control); the new state was rare at that
   pixel in the year before the change (novelty, DECISIONS.md D-042); the old state held for most
   of that year (established, D-050); 1,000 sq m or more, 8-connected.
4. Water loss alone (water to vegetation or mixed) is counted and never becomes a candidate.

Every count of what each control removed is kept, so the tuning report can show it.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import numpy as np

from lake_protect.indices import BARE, BUILT, CLASS_CODES, MASKED, OTHER, VEG, WATER
from lake_protect.rules import rules

NONE, SOIL_FILL, CLEARING, BUILDING, LEVELLING, WATER_LOSS = 0, 1, 2, 3, 4, 9
CHANGE_NAMES = {SOIL_FILL: "soil_fill", CLEARING: "clearing", BUILDING: "building", LEVELLING: "levelling", WATER_LOSS: "water_loss"}
ALERTING = (SOIL_FILL, CLEARING, BUILDING, LEVELLING)


def transition_table(cfg: dict | None = None) -> np.ndarray:
    cfg = cfg or rules()["transitions"]
    codes = {"soil_fill": SOIL_FILL, "clearing": CLEARING, "building": BUILDING, "levelling": LEVELLING}
    table = np.zeros((6, 6), dtype=np.uint8)
    for key, name in cfg.items():
        x, y = key.split(">")
        table[CLASS_CODES[x], CLASS_CODES[y]] = codes[name]
    # Water lost to anything that is not fill or building is water loss alone (invariant 8).
    for y in (VEG, OTHER):
        table[WATER, y] = WATER_LOSS
    return table


@dataclass
class Candidate:
    component: np.ndarray  # bool mask on the grid
    change_type: str
    stage: str
    first_idx: int
    last_clear_idx: int | None
    changed_idx: list[int]
    area_sq_m: float
    area_growth: float | None
    confidence: float
    flags: list[str]
    first_changed_at: dt.date
    last_clear_at: dt.date | None
    old_class: int
    new_class: int


@dataclass
class Result:
    candidates: list[Candidate]
    counts: dict = field(default_factory=dict)
    legacy: list[Candidate] = field(default_factory=list)


def _days(dates: list[dt.date]) -> np.ndarray:
    base = dt.date(2015, 1, 1)
    return np.array([(d - base).days for d in dates], dtype=np.int32)


def _date(days: int) -> dt.date:
    return dt.date(2015, 1, 1) + dt.timedelta(days=int(days))


def detect(
    dates: list[dt.date],
    cls: np.ndarray,
    aoi_mask: np.ndarray,
    baseline: dt.date,
    as_of: dt.date,
    res_m: float = 10.0,
    cfg: dict | None = None,
    shore_check: bool = True,
) -> Result:
    from scipy import ndimage

    cfg = cfg or rules()
    c = cfg["controls"]
    n, H, W = cls.shape
    if n < 2:
        return Result([], {"looks": n})
    assert all(d <= as_of for d in dates), "a look after as_of reached change detection"
    assert list(dates) == sorted(dates), "looks must be in time order"
    day = _days(list(dates))
    informative = (cls != MASKED) & (cls != OTHER)

    # Step 1 and 2: newest class, run of looks back to the first that differs.
    Y = np.zeros((H, W), np.uint8)
    run_first = np.full((H, W), -1, np.int32)
    run_last = np.full((H, W), -1, np.int32)
    run_count = np.zeros((H, W), np.int32)
    brk = np.full((H, W), -1, np.int32)
    for i in range(n - 1, -1, -1):
        ci, inf = cls[i], informative[i]
        unset = Y == 0
        new = unset & inf
        Y[new] = ci[new]
        run_last[new] = i
        run_first[new] = i
        run_count[new] = 1
        active = ~unset & (brk < 0) & inf
        same = active & (ci == Y)
        run_first[same] = i
        run_count[same] += 1
        brk[active & (ci != Y)] = i

    has_brk = brk >= 0
    rr, cc = np.nonzero(has_brk)
    X = np.zeros((H, W), np.uint8)
    X[rr, cc] = cls[brk[rr, cc], rr, cc]

    # Old state must have held: `prior_stable_obs` of the last `prior_window_obs` looks.
    seen = np.zeros((H, W), np.int32)
    agree = np.zeros((H, W), np.int32)
    for i in range(n - 1, -1, -1):
        consider = has_brk & (i <= brk) & (seen < c["prior_window_obs"]) & informative[i]
        seen[consider] += 1
        agree[consider & (cls[i] == X)] += 1
    stable = agree >= c["prior_stable_obs"]

    ctype = transition_table(cfg["transitions"])[X, Y]
    ctype[~has_brk] = NONE

    safe_first = np.clip(run_first, 0, n - 1)
    safe_last = np.clip(run_last, 0, n - 1)
    first_day = day[safe_first]
    span = day[safe_last] - first_day
    persistent = (run_count >= c["persistence_min_obs"]) & (span >= c["persistence_min_days"])
    fresh = (day[-1] - day[safe_last]) <= c["max_staleness_days"]
    fresh &= (_days([as_of])[0] - day[safe_last]) <= c["max_staleness_days"]
    after_baseline = first_day > _days([baseline])[0]

    # Seasonal control: the same calendar window in each of the previous two years.
    seasonal = np.zeros((H, W), bool)
    season_seen_any = np.zeros((H, W), bool)
    for k in range(1, cfg["sampling"]["history_years"] + 1):
        seen_k = np.zeros((H, W), np.int32)
        same_k = np.zeros((H, W), np.int32)
        for i in range(n):
            delta = day[i] - first_day + 365 * k
            inside = (np.abs(delta) <= c["seasonal_window_days"]) & informative[i]
            seen_k[inside] += 1
            same_k[inside & (cls[i] == Y)] += 1
        frac = np.divide(same_k, seen_k, out=np.zeros((H, W), float), where=seen_k > 0)
        seasonal |= (seen_k > 0) & (frac >= c["seasonal_same_class_fraction"])
        season_seen_any |= seen_k > 0

    # Novelty: the new state must have been rare at this pixel in the year before the change.
    # Catches surfaces that flip between classes with the seasons (bare soil read as built in
    # the wet months), which a window around one date can miss (DECISIONS.md D-042).
    # Established: the old state held for most of that year. Grass that greens in the monsoon and
    # dries after it, or a lake edge that is wet for a few months, is not an established state, so
    # its change is not a change of land use (DECISIONS.md D-050).
    nov_seen = np.zeros((H, W), np.int32)
    nov_same = np.zeros((H, W), np.int32)
    old_same = np.zeros((H, W), np.int32)
    for i in range(n):
        inside = (day[i] < first_day) & (day[i] >= first_day - c["novelty_window_days"]) & informative[i]
        nov_seen[inside] += 1
        nov_same[inside & (cls[i] == Y)] += 1
        old_same[inside & (cls[i] == X)] += 1
    nov_frac = np.divide(nov_same, nov_seen, out=np.zeros((H, W), float), where=nov_seen > 0)
    novel = nov_frac <= c["novelty_max_fraction"]
    old_frac = np.divide(old_same, nov_seen, out=np.zeros((H, W), float), where=nov_seen > 0)
    established = (nov_seen == 0) | (old_frac >= c["established_min_fraction"])

    in_aoi = aoi_mask.astype(bool)
    alerting = np.isin(ctype, ALERTING)
    base = in_aoi & has_brk
    counts = {
        "looks": n,
        "pixels_aoi": int(in_aoi.sum()),
        "px_changed_any": int((base & (ctype != NONE)).sum()),
        "px_water_loss_only": int((base & (ctype == WATER_LOSS)).sum()),
        "px_alerting_type": int((base & alerting).sum()),
        "px_dropped_unstable_before": int((base & alerting & ~stable).sum()),
        "px_dropped_not_persistent": int((base & alerting & stable & ~persistent).sum()),
        "px_dropped_stale": int((base & alerting & stable & persistent & ~fresh).sum()),
        "px_dropped_seasonal": int((base & alerting & stable & persistent & fresh & seasonal).sum()),
        "px_dropped_not_new": int((base & alerting & stable & persistent & fresh & ~seasonal & ~novel).sum()),
        "px_dropped_not_established": int((base & alerting & stable & persistent & fresh & ~seasonal & novel & ~established).sum()),
    }
    keep = base & alerting & stable & persistent & fresh & ~seasonal & novel & established
    counts["px_before_baseline"] = int((keep & ~after_baseline).sum())
    counts["px_kept"] = int((keep & after_baseline).sum())

    structure = np.ones((3, 3), bool)
    min_px = int(np.ceil(c["min_area_sq_m"] / (res_m * res_m)))
    result = Result([], counts)
    for want_after, bucket in ((True, result.candidates), (False, result.legacy)):
        mask = keep & (after_baseline if want_after else ~after_baseline)
        # Each 8-connected patch must reach the minimum area on its own (rule 2). Only then are
        # patches within `merge_distance_m` of each other joined into one change (D-051).
        own, n_own = ndimage.label(mask, structure=structure)
        if n_own:
            own_sizes = ndimage.sum(mask, own, index=np.arange(1, n_own + 1))
            small_ids = np.nonzero(own_sizes < min_px)[0] + 1
            counts["patches_small" + ("" if want_after else "_legacy")] = int(len(small_ids))
            mask = mask & ~np.isin(own, small_ids)
        grow = int(c.get("merge_distance_m", 0) // (2 * res_m))
        grown = ndimage.binary_dilation(mask, structure=structure, iterations=grow) if grow > 0 else mask
        labels, nlab = ndimage.label(grown, structure=structure)
        labels[~mask] = 0
        if nlab == 0:
            continue
        sizes = ndimage.sum(mask, labels, index=np.arange(1, nlab + 1))
        for lab in np.nonzero(sizes >= min_px)[0] + 1:
            comp = labels == lab
            cand = _component(comp, cls, informative, day, Y, X, ctype, seasonal, season_seen_any, res_m, cfg, shore_check)
            if cand is None:
                counts["components_dropped_bracket"] = counts.get("components_dropped_bracket", 0) + 1
                continue
            if isinstance(cand, str):
                counts[f"components_dropped_{cand}"] = counts.get(f"components_dropped_{cand}", 0) + 1
                continue
            if want_after and cand.first_changed_at <= baseline:
                result.legacy.append(cand)
                continue
            bucket.append(cand)
        counts["components_small" + ("" if want_after else "_legacy")] = int((sizes < min_px).sum())
    counts["candidates"] = len(result.candidates)
    counts["legacy_candidates"] = len(result.legacy)
    return result


def _component(comp, cls, informative, day, Y, X, ctype, seasonal, season_seen_any, res_m, cfg, shore_check):
    from scipy import ndimage

    c = cfg["controls"]
    n = cls.shape[0]
    size = int(comp.sum())
    ys, xs = np.nonzero(comp)
    y_pix, x_pix = Y[ys, xs], X[ys, xs]
    types = ctype[ys, xs]
    vals, cnts = np.unique(types, return_counts=True)
    main = int(vals[np.argmax(cnts)])

    cov = np.array([informative[i][ys, xs].mean() for i in range(n)])
    frac_y = np.array([((cls[i][ys, xs] == y_pix) & informative[i][ys, xs]).sum() / max(1, informative[i][ys, xs].sum()) for i in range(n)])
    frac_x = np.array([((cls[i][ys, xs] == x_pix) & informative[i][ys, xs]).sum() / max(1, informative[i][ys, xs].sum()) for i in range(n)])
    good = cov >= c["bracket_min_coverage"]
    agree = c["bracket_agree_fraction"]

    # First changed: the earliest look from which every later covered look agrees on the new state.
    first = None
    for i in range(n - 1, -1, -1):
        if not good[i]:
            continue
        if frac_y[i] >= agree:
            first = i
        else:
            break
    if first is None:
        return None
    changed = [i for i in range(first, n) if good[i]]
    if len(changed) < c["persistence_min_obs"] or (day[changed[-1]] - day[changed[0]]) < c["persistence_min_days"]:
        return "not_persistent"
    last_clear = None
    for i in range(first - 1, -1, -1):
        if good[i] and frac_x[i] >= agree:
            last_clear = i
            break
    if last_clear is None:
        return "no_clear_look_before"

    flags: list[str] = []
    old_class = int(np.bincount(x_pix, minlength=6).argmax())
    new_class = int(np.bincount(y_pix, minlength=6).argmax())
    if main == SOIL_FILL and shore_check:
        ring = ndimage.binary_dilation(comp, iterations=2) & ~comp
        ring_cls = cls[last_clear][ring]
        ring_inf = (ring_cls != MASKED) & (ring_cls != OTHER)
        land = ((ring_cls != WATER) & ring_inf).sum() / max(1, ring_inf.sum())
        if land < c["soil_fill_shore_land_fraction"]:
            return "not_at_shore"
    if new_class == BUILT or (main == SOIL_FILL and new_class == BUILT):
        flags.append("built_without_radar")
    if old_class == WATER and new_class == BUILT:
        flags.append("water_to_built")
    if not season_seen_any[ys, xs].all():
        flags.append("seasonal_history_partial")

    area = size * res_m * res_m
    n_first = ((cls[first][ys, xs] == y_pix)).sum()
    n_last = ((cls[changed[-1]][ys, xs] == y_pix)).sum()
    growth = float((n_last - n_first) / max(1, n_first)) if good[changed[-1]] else None

    k = cfg["confidence"]
    conf = k["base"] + k["per_obs"] * min(len(changed), k["max_obs_counted"])
    if area >= k["large_area_sq_m"]:
        conf += k["large_area_bonus"]
    if "seasonal_history_partial" in flags:
        conf -= k["missing_season_penalty"]
    if "built_without_radar" in flags:
        conf -= k["built_without_radar_penalty"]
    conf = round(float(min(k["cap"], max(0.05, conf))), 3)

    name = CHANGE_NAMES[main]
    return Candidate(
        component=comp,
        change_type=name,
        stage=cfg["stage_by_change"][name],
        first_idx=first,
        last_clear_idx=last_clear,
        changed_idx=changed,
        area_sq_m=float(area),
        area_growth=round(growth, 4) if growth is not None else None,
        confidence=conf,
        flags=sorted(set(flags)),
        first_changed_at=_date(day[first]),
        last_clear_at=_date(day[last_clear]),
        old_class=old_class,
        new_class=new_class,
    )


def water_series(cls_stack: np.ndarray, dates: list[dt.date], primary: np.ndarray) -> list[tuple[dt.date, float]]:
    """Share of the lake (inside its outline) classed as water, per look with enough coverage."""
    out = []
    if not primary.any():
        return out
    for i, d in enumerate(dates):
        c = cls_stack[i][primary]
        inf = (c != MASKED) & (c != OTHER)
        if inf.sum() >= 0.5 * primary.sum():
            out.append((d, float((c[inf] == WATER).mean())))
    return out


def anomaly_at(series: list[tuple[dt.date, float]], around: dt.date, window_days: int, years: int) -> float | None:
    """Section 8.4 rule 4 input: water share near a date minus the same window in previous years,
    in percentage points. None when either side has no look."""

    def mean_near(day: dt.date):
        vals = [f for d, f in series if abs((d - day).days) <= window_days]
        return float(np.mean(vals)) if vals else None

    now = mean_near(around)
    past = [mean_near(around - dt.timedelta(days=365 * k)) for k in range(1, years + 1)]
    past = [p for p in past if p is not None]
    if now is None or not past:
        return None
    return round(100.0 * (now - float(np.mean(past))), 1)
