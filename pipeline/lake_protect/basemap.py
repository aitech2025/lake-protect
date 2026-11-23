"""Offline base map: a Sentinel-2 true-colour mosaic of the area up to the ORR, as XYZ tiles.

The desk's map of real lakes must work with no internet (M9), and should show real ground, not a
drawing. Recent clear scenes are read once (the 8-bit `visual` asset, 10 m), clouds removed with
the scene classification layer, combined by a per-pixel median, reprojected to Web Mercator on
the zoom-14 tile grid (about 9 m per pixel at Hyderabad's latitude, close to the data's own 10 m),
and cut into tiles. Coarser zooms are averages of finer ones. Nothing finer than zoom 14 is
made: the map enlarges zoom 14 rather than invent detail.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import math
import zipfile
from pathlib import Path

import numpy as np

from lake_protect.rules import configure_gdal, rules
from lake_protect.stac import parse_items, search_items

ORR_BBOX = (78.22, 17.20, 78.72, 17.62)  # CONTEXT.md section 8.3, approximate
TILE = 256
R = 6378137.0


def merc(lon: float, lat: float) -> tuple[float, float]:
    return math.radians(lon) * R, math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * R


def tile_xy(lon: float, lat: float, z: int) -> tuple[int, int]:
    n = 2**z
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
    return x, y


def tile_origin(x: int, y: int, z: int) -> tuple[float, float]:
    """Web Mercator metres of a tile's north-west corner."""
    size = 2 * math.pi * R / 2**z
    return -math.pi * R + x * size, math.pi * R - y * size


def build(
    out_zip: Path,
    as_of: dt.date,
    bbox: tuple[float, float, float, float] = ORR_BBOX,
    days: int = 75,
    max_scenes: int = 4,
    minzoom: int = 9,
    maxzoom: int = 14,
    log=print,
) -> dict:
    configure_gdal()
    import rasterio
    from affine import Affine
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT
    from shapely.geometry import box, shape

    scenes = parse_items(search_items(bbox, as_of - dt.timedelta(days=days), as_of))
    area = box(*bbox)
    covering = [s for s in scenes if shape(s.footprint).contains(area) and "visual" in s.hrefs]
    covering.sort(key=lambda s: (s.cloud_pct if s.cloud_pct is not None else 100))
    chosen = covering[:max_scenes]
    if not chosen:
        raise SystemExit("No scene covers the whole area in that window")
    log(f"Base map from {len(chosen)} scenes: " + ", ".join(f"{s.id} ({s.cloud_pct:.0f}% cloud)" for s in chosen))

    x0, y0 = tile_xy(bbox[0], bbox[3], maxzoom)
    x1, y1 = tile_xy(bbox[2], bbox[1], maxzoom)
    nx, ny = x1 - x0 + 1, y1 - y0 + 1
    W, H = nx * TILE, ny * TILE
    ox, oy = tile_origin(x0, y0, maxzoom)
    px = 2 * math.pi * R / 2**maxzoom / TILE
    transform = Affine(px, 0, ox, 0, -px, oy)
    log(f"Mosaic {W} x {H} px at {px:.2f} m (Web Mercator), {nx * ny} tiles at zoom {maxzoom}")

    rgbs, bads = [], []
    for s in chosen:
        with rasterio.open(s.hrefs["visual"]) as src, WarpedVRT(src, crs="EPSG:3857", transform=transform, width=W, height=H, resampling=Resampling.bilinear) as vrt:
            rgb = vrt.read()  # (3, H, W) uint8
        with rasterio.open(s.hrefs["scl"]) as src, WarpedVRT(src, crs="EPSG:3857", transform=transform, width=W, height=H, resampling=Resampling.nearest) as vrt:
            scl = vrt.read(1)
        bad = np.isin(scl, rules()["sentinel2"]["scl_masked"]) | (rgb.max(axis=0) == 0)
        del scl
        rgbs.append(rgb)
        bads.append(bad)
        log(f"  read {s.id}: {100 * (1 - bad.mean()):.0f}% clear")

    # Per-pixel median of the clear looks, in strips so memory stays small.
    import warnings

    mosaic = np.zeros((3, H, W), np.uint8)
    holes = np.ones((H, W), bool)
    for r0 in range(0, H, 256):
        r1 = min(H, r0 + 256)
        st = np.stack([x[:, r0:r1] for x in rgbs]).astype(np.float32)  # (n, 3, h, W)
        m = np.stack([b[r0:r1] for b in bads])  # (n, h, W)
        st[np.broadcast_to(m[:, None], st.shape)] = np.nan
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            med = np.nanmedian(st, axis=0)
        ok = np.isfinite(med).all(axis=0)
        mosaic[:, r0:r1] = np.where(np.isfinite(med), med, 0).astype(np.uint8)
        holes[r0:r1] = ~ok
    del rgbs, bads

    from PIL import Image

    count = 0
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_STORED) as zf:
        level = np.moveaxis(mosaic, 0, -1)  # (H, W, 3)
        mask = holes
        lx0, ly0 = x0, y0
        for z in range(maxzoom, minzoom - 1, -1):
            h, w = level.shape[:2]
            for ty in range(h // TILE):
                for tx in range(w // TILE):
                    tile = level[ty * TILE:(ty + 1) * TILE, tx * TILE:(tx + 1) * TILE]
                    if mask[ty * TILE:(ty + 1) * TILE, tx * TILE:(tx + 1) * TILE].all():
                        continue
                    buf = io.BytesIO()
                    Image.fromarray(tile, "RGB").save(buf, format="JPEG", quality=82, optimize=True)
                    zf.writestr(f"{z}/{lx0 + tx}/{ly0 + ty}.jpg", buf.getvalue())
                    count += 1
            if z == minzoom:
                break
            # Next coarser zoom: pad to whole parent tiles, then average 2 x 2.
            px0, py0 = lx0 // 2, ly0 // 2
            pad_l, pad_t = (lx0 - px0 * 2) * TILE, (ly0 - py0 * 2) * TILE
            full_w = math.ceil((pad_l + w) / (2 * TILE)) * 2 * TILE
            full_h = math.ceil((pad_t + h) / (2 * TILE)) * 2 * TILE
            canvas = np.zeros((full_h, full_w, 3), np.float32)
            cmask = np.ones((full_h, full_w), bool)
            canvas[pad_t:pad_t + h, pad_l:pad_l + w] = level
            cmask[pad_t:pad_t + h, pad_l:pad_l + w] = mask
            level = canvas.reshape(full_h // 2, 2, full_w // 2, 2, 3).mean(axis=(1, 3)).astype(np.uint8)
            mask = cmask.reshape(full_h // 2, 2, full_w // 2, 2).all(axis=(1, 3))
            lx0, ly0 = px0, py0
        meta = {
            "bounds": list(bbox),
            "minzoom": minzoom,
            "maxzoom": maxzoom,
            "format": "jpg",
            "scenes": [{"id": s.id, "acquired_at": s.acquired_at.isoformat(), "cloud_pct": s.cloud_pct} for s in chosen],
            "attribution": f"Contains modified Copernicus Sentinel data {max(s.acquired_at.year for s in chosen)}",
            "made_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "tiles": count,
        }
        zf.writestr("meta.json", json.dumps(meta, indent=1))
    log(f"{count} tiles written to {out_zip}")
    return meta
