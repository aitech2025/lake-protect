"""Sentinel-1 radar check for "built" (CONTEXT.md section 8.4: built is NDBI > 0 *and* VV at least
3 dB above baseline).

Sentinel-2 alone confuses bare ground with built-up ground (DECISIONS.md D-042). For every
candidate whose new state is built, radar is read over its asset's window from Planetary Computer
`sentinel-1-rtc` (terrain-corrected gamma0, 10 m, EPSG:32644, anonymous read tokens, D-049):

- one relative orbit only, the asset's most frequent, so viewing geometry is constant;
- speckle reduced with a per-pixel median over several dates, never a spatial filter;
- before: looks in the 120 days up to the last clear date; after: looks from the first changed
  date to as_of; seasonal: the after window's months one year earlier, which removes the rise
  in backscatter that wet soil gives in the monsoon.

The rise is the mean over the candidate's pixels of 10 log10(after / before), and the same
against the seasonal window when it has looks. Built is confirmed when every available rise is
at least 3 dB. No look after as_of is ever read (invariant 10).
"""
from __future__ import annotations

import datetime as dt
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np

from lake_protect.aoi import AssetAOI, Grid
from lake_protect.rules import cache_dir, configure_gdal, rules
from lake_protect.stac import end_of_day



def _source() -> tuple[str, str]:
    """The radar catalogue and collection: the rule file's, or the admin's source (D-066)."""
    cfg = rules()["radar"]
    return cfg["stac_url"], cfg["collection"]


@dataclass(frozen=True)
class RadarScene:
    id: str
    acquired_at: dt.datetime
    relative_orbit: int | None
    orbit_state: str | None
    vv_href: str
    footprint: dict

    @property
    def date(self) -> dt.date:
        return self.acquired_at.date()


def search(bbox_ll, start: dt.date, as_of: dt.date) -> list[RadarScene]:
    stac_url, collection = _source()
    key = f"{collection}_{'_'.join(f'{v:.4f}' for v in bbox_ll)}_{start}_{as_of}"
    path = cache_dir() / "stac" / f"{key}.json"
    if path.exists():
        items = json.loads(path.read_text(encoding="utf-8"))
    else:
        import pystac_client

        client = pystac_client.Client.open(stac_url)
        found = client.search(
            collections=[collection],
            bbox=list(bbox_ll),
            datetime=[dt.datetime.combine(start, dt.time(0), tzinfo=dt.timezone.utc), end_of_day(as_of)],
            max_items=3000,
        )
        items = [i.to_dict() for i in found.items()]
        if as_of < dt.date.today():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(items), encoding="utf-8")
    out = []
    for it in items:
        p = it["properties"]
        acquired = dt.datetime.fromisoformat(p["datetime"].replace("Z", "+00:00")).astimezone(dt.timezone.utc)
        if acquired > end_of_day(as_of) or "vv" not in it["assets"]:
            continue
        out.append(RadarScene(it["id"], acquired, p.get("sat:relative_orbit"), p.get("sat:orbit_state"), it["assets"]["vv"]["href"], it["geometry"]))
    return sorted(out, key=lambda s: s.acquired_at)


def _signed(href: str) -> str:
    import planetary_computer

    return planetary_computer.sign(href)


def read_vv(scene: RadarScene, grid: Grid, as_of: dt.date) -> np.ndarray | None:
    """Gamma0 VV (linear) on the asset grid, NaN where no data. Cached outside OneDrive."""
    if scene.acquired_at > end_of_day(as_of):
        from lake_protect.stac import LookAheadError

        raise LookAheadError(f"Radar scene {scene.id} is after as_of {as_of}")
    path = cache_dir() / "s1" / scene.id / f"{grid.key()}.vv.npz"
    if path.exists():
        return np.load(path)["vv"]
    configure_gdal()
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT

    for _ in range(3):
        try:
            with rasterio.open(_signed(scene.vv_href)) as src:
                with WarpedVRT(src, crs=grid.crs, transform=grid.transform, width=grid.width, height=grid.height,
                               resampling=Resampling.nearest, src_nodata=-32768, nodata=np.nan) as vrt:
                    vv = vrt.read(1).astype(np.float32)
            vv[(vv <= 0) | ~np.isfinite(vv)] = np.nan
            path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(path, vv=vv)
            return vv
        except Exception:
            continue
    return None


def _median(stack: list[np.ndarray]) -> np.ndarray | None:
    import warnings

    if not stack:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmedian(np.stack(stack), axis=0)


def _rise_db(after: np.ndarray, before: np.ndarray, mask: np.ndarray) -> float | None:
    a, b = after[mask], before[mask]
    ok = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
    if ok.sum() < max(3, 0.5 * mask.sum()):
        return None
    return round(float(np.mean(10 * np.log10(a[ok] / b[ok]))), 2)


def check_built(aoi: AssetAOI, cands: list[dict], components: list[np.ndarray], as_of: dt.date, workers: int = 8, log=lambda *_: None) -> None:
    """Confirm or refuse each built candidate in place. Adds `radar` details to each one."""
    if not cands:
        return
    cfg = rules().get("radar", {})
    min_rise = cfg.get("built_min_rise_db", 3.0)
    before_days = cfg.get("before_days", 120)
    max_after = cfg.get("max_after_looks", 8)
    season_pad = cfg.get("seasonal_pad_days", 30)
    earliest = min(dt.date.fromisoformat(c["last_clear_at"]) for c in cands) - dt.timedelta(days=before_days + 400)
    scenes = [s for s in search(aoi.ring_ll.bounds, earliest, as_of) if _covers(s, aoi)]
    if not scenes:
        for c in cands:
            c["radar"] = {"status": "no_radar_scene"}
            c["flags"] = sorted(set(c["flags"]) | {"radar_unavailable"})
        return
    orbit = Counter(s.relative_orbit for s in scenes).most_common(1)[0][0]
    scenes = [s for s in scenes if s.relative_orbit == orbit]

    def window(lo: dt.date, hi: dt.date, last: int | None = None) -> list[RadarScene]:
        sel = [s for s in scenes if lo <= s.date <= hi]
        return sel[-last:] if last else sel

    needed: dict[str, RadarScene] = {}
    plans = []
    for c in cands:
        lc, fc = dt.date.fromisoformat(c["last_clear_at"]), dt.date.fromisoformat(c["first_changed_at"])
        before = window(lc - dt.timedelta(days=before_days), lc)
        after = window(fc, as_of, max_after)
        season = []
        if after:
            season = window(after[0].date - dt.timedelta(days=365 + season_pad), after[-1].date - dt.timedelta(days=365 - season_pad))
            season = [s for s in season if s.date < lc]
        plans.append((before, after, season))
        for s in before + after + season:
            needed[s.id] = s
    with ThreadPoolExecutor(max_workers=workers) as pool:
        arrays = dict(zip(needed, pool.map(lambda s: read_vv(s, aoi.grid, as_of), needed.values())))
    for c, comp, (before, after, season) in zip(cands, components, plans):
        b = _median([arrays[s.id] for s in before if arrays.get(s.id) is not None])
        a = _median([arrays[s.id] for s in after if arrays.get(s.id) is not None])
        z = _median([arrays[s.id] for s in season if arrays.get(s.id) is not None])
        rise = _rise_db(a, b, comp) if a is not None and b is not None else None
        rise_season = _rise_db(a, z, comp) if a is not None and z is not None else None
        detail = {
            "relative_orbit": orbit,
            "looks_before": len(before), "looks_after": len(after), "looks_season": len(season),
            "rise_db": rise, "rise_vs_last_year_db": rise_season, "min_rise_db": min_rise,
            "scenes_after": [s.id for s in after],
        }
        if rise is None:
            detail["status"] = "not_enough_radar"
            c["flags"] = sorted(set(c["flags"]) | {"radar_unavailable"})
        elif rise >= min_rise and (rise_season is None or rise_season >= min_rise):
            detail["status"] = "confirmed"
            c["sensor_basis"] = "optical_and_radar"
            c["flags"] = sorted((set(c["flags"]) - {"built_without_radar"}) | {"radar_confirmed"})
            c["confidence"] = round(min(rules()["confidence"]["cap"], c["confidence"] + rules()["confidence"]["built_without_radar_penalty"] + 0.1), 3)
            c["observations"] = c["observations"] + [observation(s) for s in after[:2]]
        else:
            detail["status"] = "not_confirmed"
        c["radar"] = detail
        log(f"    radar {aoi.name}: {detail['status']} rise {rise} dB, vs last year {rise_season} dB ({len(before)}/{len(after)}/{len(season)} looks)")


def observation(scene: RadarScene) -> dict:
    """In the shape `POST /candidates` takes for each observation."""
    cfg = rules().get("radar", {})
    stac_url, collection = _source()
    return {
        "sensor": "sentinel-1",
        "scene_id": scene.id,
        "acquired_at": scene.acquired_at.isoformat(),
        "cloud_pct": None,
        "stac_href": f"{stac_url}/collections/{collection}/items/{scene.id}",
        "processing_version": f"{collection} from {stac_url}, gamma0 VV, multi-date median; {rules()['rule_version']}",
        "licence_notice": cfg.get("licence_notice", "Contains modified Copernicus Sentinel data {year}").format(year=scene.acquired_at.year),
    }


def _covers(scene: RadarScene, aoi: AssetAOI) -> bool:
    from shapely.geometry import shape

    return shape(scene.footprint).contains(aoi.ring_ll)
