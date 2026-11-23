"""Windowed reads of Sentinel-2 COGs onto an asset's 10 m grid, with a local cache.

Only the asset's window is read (section 8.3: never download whole scenes). The scene
classification layer is read first; the five reflectance bands are read only if enough of the
area of interest is clear. Results are cached in LP_CACHE_DIR, outside OneDrive.
"""
from __future__ import annotations

import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from lake_protect.aoi import AssetAOI, Grid
from lake_protect.rules import cache_dir, configure_gdal, rules
from lake_protect.stac import Scene, assert_not_after


def _read_band(href: str, grid: Grid, nearest: bool) -> np.ndarray:
    configure_gdal()
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT

    last_error = None
    for _ in range(3):
        try:
            with rasterio.open(href) as src:
                with WarpedVRT(
                    src,
                    crs=grid.crs,
                    transform=grid.transform,
                    width=grid.width,
                    height=grid.height,
                    resampling=Resampling.nearest if nearest else Resampling.bilinear,
                    src_nodata=0,
                    nodata=0,
                ) as vrt:
                    return vrt.read(1)
        except Exception as exc:  # network hiccups: retry, then give up on this scene
            last_error = exc
    raise RuntimeError(f"Could not read {href}: {last_error}")


def _cache_path(scene: Scene, grid: Grid, kind: str) -> Path:
    return cache_dir() / "s2" / scene.id / f"{grid.key()}.{kind}.npz"


def read_scl(scene: Scene, grid: Grid, as_of: dt.date) -> np.ndarray:
    assert_not_after(scene, as_of)
    path = _cache_path(scene, grid, "scl")
    if path.exists():
        return np.load(path)["scl"]
    scl = _read_band(scene.hrefs["scl"], grid, nearest=True).astype(np.uint8)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, scl=scl)
    return scl


def clear_mask(scl: np.ndarray) -> np.ndarray:
    return ~np.isin(scl, rules()["sentinel2"]["scl_masked"])


def clear_fraction(scl: np.ndarray, aoi_mask: np.ndarray) -> float:
    n = int(aoi_mask.sum())
    return float((clear_mask(scl) & aoi_mask).sum()) / n if n else 0.0


def read_bands(scene: Scene, grid: Grid, as_of: dt.date, pool: ThreadPoolExecutor | None = None) -> dict[str, np.ndarray]:
    """Surface reflectance (float32) for the five bands, scale and offset applied."""
    assert_not_after(scene, as_of)
    bands = rules()["sentinel2"]["bands"]
    path = _cache_path(scene, grid, "bands")
    if path.exists():
        raw = dict(np.load(path))
    else:
        if pool is None:
            with ThreadPoolExecutor(max_workers=len(bands)) as own:
                arrays = list(own.map(lambda b: _read_band(scene.hrefs[b], grid, nearest=False), bands))
        else:
            arrays = list(pool.map(lambda b: _read_band(scene.hrefs[b], grid, nearest=False), bands))
        raw = {b: a.astype(np.uint16) for b, a in zip(bands, arrays)}
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **raw)
    out = {}
    for b in bands:
        scale, offset = scene.scale_offset.get(b, [1e-4, 0.0])
        dn = raw[b].astype(np.float32)
        refl = dn * float(scale) + float(offset)
        refl[raw[b] == 0] = np.nan
        out[b] = refl
    return out


def is_cached(scene: Scene, grid: Grid) -> bool:
    return _cache_path(scene, grid, "bands").exists()


def window_start(baseline: dt.date) -> dt.date:
    """Earliest date any look is needed: seasonal history before the monitoring lead."""
    s = rules()["sampling"]
    c = rules()["controls"]
    return baseline - dt.timedelta(days=s["monitor_lead_days"] + 365 * s["history_years"] + c["seasonal_window_days"] + 5)


def period_key(day: dt.date, monitor_from: dt.date) -> tuple[int, int]:
    """Monitoring period (from baseline minus the lead) every `monitor_period_days`; earlier
    history, which feeds only the seasonal control, every `history_period_days`."""
    s = rules()["sampling"]
    days = s["monitor_period_days"] if day >= monitor_from else s["history_period_days"]
    return days, (day - dt.date(2015, 1, 1)).days // days


def _read_windows(href: str, grids: list[Grid], nearest: bool) -> list[np.ndarray | None]:
    """Open one COG once and read a window for every grid from it. Image blocks shared by
    nearby assets come down once, and the file header is parsed once."""
    configure_gdal()
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT

    for attempt in range(3):
        try:
            out: list[np.ndarray | None] = []
            with rasterio.open(href) as src:
                for g in grids:
                    try:
                        with WarpedVRT(src, crs=g.crs, transform=g.transform, width=g.width, height=g.height,
                                       resampling=Resampling.nearest if nearest else Resampling.bilinear, src_nodata=0, nodata=0) as vrt:
                            out.append(vrt.read(1))
                    except Exception:
                        out.append(None)
            return out
        except Exception:
            if attempt == 2:
                return [None] * len(grids)
    return [None] * len(grids)


def select_and_fetch(
    aois: list[AssetAOI],
    scenes_by_aoi: dict[str, list[Scene]],
    as_of: dt.date,
    workers: int = 16,
    candidates_per_period: int = 3,
    log=lambda *_: None,
) -> dict[str, list[tuple[Scene, float]]]:
    """Pick one clear look per period for every asset, then read its bands. Scene-major.

    Each scene file is opened once and every asset's window is read from it in the same pass, so
    image blocks shared by nearby lakes come down once (the proposal's "process each scene once,
    match every asset"). Within a period, scenes are tried in order of scene-level cloud until
    each asset has a look whose area of interest is clear enough. Periods run in parallel.
    """
    import threading

    cfg = rules()
    min_clear = cfg["sentinel2"]["min_clear_fraction"]
    by_key = {a.asset_key: a for a in aois}
    monitor_from = min(a.baseline_date for a in aois) - dt.timedelta(days=cfg["sampling"]["monitor_lead_days"])

    periods: dict[tuple, dict[str, Scene]] = {}
    covers: dict[str, set[str]] = {}
    for key, scenes in scenes_by_aoi.items():
        start = window_start(by_key[key].baseline_date)
        for s in scenes:
            if s.date < start:
                continue
            periods.setdefault(period_key(s.date, monitor_from), {})[s.id] = s
            covers.setdefault(s.id, set()).add(key)

    lock = threading.Lock()
    chosen: dict[str, list[tuple[Scene, float]]] = {a.asset_key: [] for a in aois}
    stats = {"scl_files": 0, "periods_done": 0}

    def do_period(pk) -> None:
        needing = {k for s in periods[pk].values() for k in covers[s.id]}
        ordered = sorted(periods[pk].values(), key=lambda s: (s.cloud_pct if s.cloud_pct is not None else 100, s.id))
        for scene in ordered[:candidates_per_period]:
            assert_not_after(scene, as_of)
            targets = sorted(needing & covers[scene.id])
            if not targets:
                continue
            fracs: dict[str, float] = {}
            missing = []
            for k in targets:
                path = _cache_path(scene, by_key[k].grid, "scl")
                if path.exists():
                    fracs[k] = clear_fraction(np.load(path)["scl"], by_key[k].masks["aoi"])
                else:
                    missing.append(k)
            if missing:
                arrays = _read_windows(scene.hrefs["scl"], [by_key[k].grid for k in missing], nearest=True)
                for k, arr in zip(missing, arrays):
                    if arr is None:
                        fracs[k] = 0.0
                        continue
                    path = _cache_path(scene, by_key[k].grid, "scl")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    np.savez_compressed(path, scl=arr.astype(np.uint8))
                    fracs[k] = clear_fraction(arr, by_key[k].masks["aoi"])
            with lock:
                stats["scl_files"] += 1 if missing else 0
                for k, frac in fracs.items():
                    if frac >= min_clear:
                        chosen[k].append((scene, frac))
                        needing.discard(k)
            if not needing:
                break
        with lock:
            stats["periods_done"] += 1
            if stats["periods_done"] % 20 == 0:
                log(f"  periods {stats['periods_done']}/{len(periods)}: {sum(len(v) for v in chosen.values())} looks chosen, {stats['scl_files']} cloud-mask files opened")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(do_period, sorted(periods)))

        # Bands: one job per (scene, band), reading the windows of every asset that chose the scene.
        by_scene: dict[str, list[str]] = {}
        scene_of: dict[str, Scene] = {}
        for k, picks in chosen.items():
            for scene, _ in picks:
                if not is_cached(scene, by_key[k].grid):
                    by_scene.setdefault(scene.id, []).append(k)
                scene_of[scene.id] = scene
        total = sum(len(v) for v in by_scene.values())
        log(f"  reading bands: {total} asset windows across {len(by_scene)} scenes ({sum(len(v) for v in chosen.values()) - total} cached)")
        bands = cfg["sentinel2"]["bands"]
        jobs = [(sid, b) for sid in sorted(by_scene, key=lambda i: scene_of[i].acquired_at) for b in bands]
        results: dict[tuple[str, str], list] = {}

        def read_job(job):
            sid, b = job
            keys = by_scene[sid]
            return job, _read_windows(scene_of[sid].hrefs[b], [by_key[k].grid for k in keys], nearest=False)

        done_scenes = 0
        pending: dict[str, int] = {sid: len(bands) for sid in by_scene}
        for (sid, b), arrays in pool.map(read_job, jobs):
            results[(sid, b)] = arrays
            pending[sid] -= 1
            if pending[sid]:
                continue
            for n, k in enumerate(by_scene[sid]):
                per = {band: results[(sid, band)][n] for band in bands}
                if any(v is None for v in per.values()):
                    chosen[k] = [(s, f) for s, f in chosen[k] if s.id != sid]
                    continue
                path = _cache_path(scene_of[sid], by_key[k].grid, "bands")
                path.parent.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(path, **{band: a.astype(np.uint16) for band, a in per.items()})
            for band in bands:
                results.pop((sid, band), None)
            done_scenes += 1
            if done_scenes % 10 == 0:
                log(f"  bands: {done_scenes}/{len(by_scene)} scenes read")
    return {k: sorted(v, key=lambda sf: sf[0].acquired_at) for k, v in chosen.items()}
