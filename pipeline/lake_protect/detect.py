"""Detection for one asset, from looks already fetched (raster.select_and_fetch).

Produces candidates in the shape `POST /candidates` takes (api/app/services/ingest.py
CandidateIn): owner-blind by construction, with the dated bracket, the observations used,
the rule version, flags and the before and after chips.
"""
from __future__ import annotations

import base64
import datetime as dt
from dataclasses import dataclass, field

import numpy as np

from lake_protect import change, chips, radar
from lake_protect.aoi import AssetAOI, rasterize, to_lonlat
from lake_protect.indices import BUILT, classify
from lake_protect.raster import clear_mask, read_bands, read_scl
from lake_protect.rules import rule_version, rules
from lake_protect.stac import Scene, assert_not_after


@dataclass
class Looks:
    scenes: list[Scene]
    cls: np.ndarray  # (n, H, W)
    bands: list[dict]

    @property
    def dates(self) -> list[dt.date]:
        return [s.date for s in self.scenes]


@dataclass
class AssetResult:
    aoi: AssetAOI
    as_of: dt.date
    looks: int
    first_look: dt.date | None
    last_look: dt.date | None
    counts: dict
    candidates: list[dict] = field(default_factory=list)
    legacy: list[dict] = field(default_factory=list)
    water: list[tuple[dt.date, float]] = field(default_factory=list)


def load_looks(aoi: AssetAOI, picks: list[tuple[Scene, float]], as_of: dt.date) -> Looks:
    scenes, stack, bands_all = [], [], []
    for scene, _ in picks:
        assert_not_after(scene, as_of)
        try:
            bands = read_bands(scene, aoi.grid, as_of)
            scl = read_scl(scene, aoi.grid, as_of)
        except (RuntimeError, OSError, KeyError):
            continue
        stack.append(classify(bands, clear_mask(scl)))
        bands_all.append(bands)
        scenes.append(scene)
    H, W = aoi.grid.height, aoi.grid.width
    cls = np.stack(stack) if stack else np.zeros((0, H, W), np.uint8)
    return Looks(scenes, cls, bands_all)


def _polygon(component: np.ndarray, aoi: AssetAOI):
    from rasterio.features import shapes
    from shapely.geometry import MultiPolygon, shape
    from shapely.ops import unary_union

    polys = [shape(g) for g, v in shapes(component.astype(np.uint8), mask=component, transform=aoi.grid.transform) if v == 1]
    utm = unary_union(polys)
    if utm.geom_type == "Polygon":
        utm = MultiPolygon([utm])
    return utm


def _observation(scene: Scene) -> dict:
    return {
        "sensor": scene.sensor,
        "scene_id": scene.id,
        "acquired_at": scene.acquired_at.isoformat(),
        "cloud_pct": round(float(scene.cloud_pct), 2) if scene.cloud_pct is not None else None,
        "stac_href": scene.stac_href,
        "processing_version": f"earth-search {rules()['sentinel2']['collection']}, baseline {scene.processing_baseline}; {rule_version()}",
        "licence_notice": rules()["sentinel2"]["licence_notice"].format(year=scene.acquired_at.year),
    }


def _payload(cand: change.Candidate, looks: Looks, aoi: AssetAOI, with_chips: bool) -> dict:
    from shapely.geometry import mapping

    utm = _polygon(cand.component, aoi)
    used = [cand.last_clear_idx] if cand.last_clear_idx is not None else []
    changed = cand.changed_idx
    used += changed[:4] + ([changed[-1]] if len(changed) > 4 else [])
    obs = [_observation(looks.scenes[i]) for i in sorted(set(used))]
    out = {
        "asset_id": aoi.asset_id,
        "asset_key": aoi.asset_key,
        "geometry": mapping(to_lonlat(utm)),
        "change_type": cand.change_type,
        "stage_estimate": cand.stage,
        "last_clear_at": cand.last_clear_at.isoformat() if cand.last_clear_at else None,
        "first_changed_at": cand.first_changed_at.isoformat(),
        "observations": obs,
        "sensor_basis": "optical_only",
        "confidence": cand.confidence,
        "rule_version": rule_version(),
        "flags": list(cand.flags),
        "area_growth": cand.area_growth,
        "area_sq_m": cand.area_sq_m,
        "looks_changed": len(changed),
        "latest_changed_at": looks.scenes[changed[-1]].date.isoformat(),
    }
    if with_chips and cand.last_clear_idx is not None:
        win = chips.window_for(cand.component)
        before_b, after_b = looks.bands[cand.last_clear_idx], looks.bands[cand.first_idx]
        rgb_b, rgb_a = chips.stretch_pair(before_b, after_b, win)
        common = dict(win=win, grid=aoi.grid, primary_utm=aoi.primary_utm, buffer_outer_utm=aoi.buffer_outer_utm, change_utm=utm)
        sb, sa = looks.scenes[cand.last_clear_idx], looks.scenes[cand.first_idx]
        out["before_chip_png_b64"] = base64.b64encode(chips.render(rgb_b, label="Before", when=sb.acquired_at, scene_id=sb.id, **common)).decode()
        out["after_chip_png_b64"] = base64.b64encode(chips.render(rgb_a, label="After", when=sa.acquired_at, scene_id=sa.id, **common)).decode()
    return out


def detect_asset(
    aoi: AssetAOI,
    picks: list[tuple[Scene, float]],
    as_of: dt.date,
    with_chips: bool = True,
    use_radar: bool = True,
    log=lambda *_: None,
) -> AssetResult:
    looks = load_looks(aoi, picks, as_of)
    res = change.detect(looks.dates, looks.cls, aoi.masks["aoi"], aoi.baseline_date, as_of, aoi.grid.res)
    out = AssetResult(
        aoi=aoi,
        as_of=as_of,
        looks=len(looks.scenes),
        first_look=looks.dates[0] if looks.scenes else None,
        last_look=looks.dates[-1] if looks.scenes else None,
        counts=res.counts,
        water=change.water_series(looks.cls, looks.dates, aoi.masks["primary"]),
    )
    pairs = [(c, _payload(c, looks, aoi, with_chips)) for c in res.candidates]
    built = [(c, p) for c, p in pairs if c.new_class == BUILT]
    if built and use_radar:
        # Section 8.4: built needs radar. Not confirmed means the rule is not met: dropped.
        try:
            radar.check_built(aoi, [p for _, p in built], [c.component for c, _ in built], as_of, log=log)
        except Exception as exc:  # radar down: keep the candidate, say so
            for _, p in built:
                p["radar"] = {"status": "radar_error", "error": f"{type(exc).__name__}: {exc}"[:200]}
                p["flags"] = sorted(set(p["flags"]) | {"radar_unavailable"})
        dropped = [p for _, p in built if p.get("radar", {}).get("status") == "not_confirmed"]
        out.counts["candidates_dropped_radar"] = len(dropped)
        pairs = [(c, p) for c, p in pairs if p not in dropped]
    out.candidates = [p for _, p in pairs]
    out.legacy = [_payload(c, looks, aoi, False) for c in res.legacy]
    return out


def apply_drought_control(results: list[AssetResult]) -> None:
    """Section 8.4 rule 4, read as DECISIONS.md D-040: when the nearest lakes are themselves well
    below their usual water share (a dry year), a soil-fill candidate stands only if its lake is
    at least 10 points worse than their median. In a normal year the control does not remove
    anything, because one fill on a large lake moves its water share by well under a point."""
    c = rules()["controls"]
    window, years = c["seasonal_window_days"], rules()["sampling"]["history_years"]
    centres = {r.aoi.asset_key: r.aoi.primary_utm.centroid for r in results if r.aoi.primary_utm is not None}
    for r in results:
        if not any(x["change_type"] == "soil_fill" for x in r.candidates):
            continue
        here = centres[r.aoi.asset_key]
        others = sorted((p.distance(here), k) for k, p in centres.items() if k != r.aoi.asset_key)[: c["drought_neighbours"]]
        by_key = {x.aoi.asset_key: x for x in results}
        kept = []
        for cand in r.candidates:
            if cand["change_type"] != "soil_fill":
                kept.append(cand)
                continue
            day = dt.date.fromisoformat(cand["first_changed_at"])
            mine = change.anomaly_at(r.water, day, window, years)
            theirs = [change.anomaly_at(by_key[k].water, day, window, years) for _, k in others]
            theirs = [t for t in theirs if t is not None]
            if mine is None or len(theirs) < 3:
                cand["flags"] = sorted(set(cand["flags"]) | {"drought_control_not_run"})
                kept.append(cand)
                continue
            median = float(np.median(theirs))
            cand["drought"] = {"lake_anomaly_pp": mine, "neighbour_median_pp": median, "neighbours": len(theirs)}
            if median <= c["drought_regional_pp"] and mine > median - c["drought_worse_by_pp"]:
                r.counts["candidates_dropped_drought"] = r.counts.get("candidates_dropped_drought", 0) + 1
                continue
            kept.append(cand)
        r.candidates = kept
