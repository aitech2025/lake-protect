"""Before and after image chips (CONTEXT.md section 8.4 "Output").

True colour, same window, same stretch for both, with the boundary and the change drawn on top.
Pixels are enlarged with hard edges, so a chip never suggests more detail than 10 m data has
(DECISIONS.md D-027 applies the same rule to demo chips). Colours match the desk's legend:
boundary #46a0ff, buffer #e6463c dashed, change #ffd640 dashed.
"""
from __future__ import annotations

import datetime as dt
import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FTL = (70, 160, 255)
BUFFER = (230, 70, 60)
CHANGE = (255, 214, 64)
OUT_PX = 640

_FONT_DIRS = [
    Path(__file__).resolve().parents[2] / "api" / "app" / "assets" / "fonts",
    Path("/srv/api/app/assets/fonts"),
]


def _font(size: int, bold: bool = False):
    name = "NotoSans-Bold.ttf" if bold else "NotoSans-Regular.ttf"
    for d in _FONT_DIRS:
        if (d / name).exists():
            return ImageFont.truetype(str(d / name), size)
    return ImageFont.load_default(size=size)


def stretch_pair(before: dict, after: dict, win) -> tuple[np.ndarray, np.ndarray]:
    """One 2-98% stretch for both chips, so a brightness difference is real, not the stretch."""
    r0, r1, c0, c1 = win
    stack = []
    for b in (before, after):
        rgb = np.dstack([b["red"][r0:r1, c0:c1], b["green"][r0:r1, c0:c1], b["blue"][r0:r1, c0:c1]])
        stack.append(rgb)
    both = np.concatenate([s.reshape(-1, 3) for s in stack])
    both = both[np.all(np.isfinite(both), axis=1)]
    lo, hi = (np.percentile(both, 2, axis=0), np.percentile(both, 98, axis=0)) if len(both) else (np.zeros(3), np.full(3, 0.3))
    out = []
    for rgb in stack:
        x = np.clip((rgb - lo) / np.maximum(hi - lo, 1e-3), 0, 1) ** 0.85
        x = np.where(np.isfinite(x), x, 0)
        out.append((x * 255).astype(np.uint8))
    return out[0], out[1]


def stretch_one(bands: dict) -> np.ndarray:
    """A 2-98% stretch of one look, for the weekly image of a whole asset."""
    rgb = np.dstack([bands["red"], bands["green"], bands["blue"]])
    flat = rgb.reshape(-1, 3)
    flat = flat[np.all(np.isfinite(flat), axis=1)]
    lo, hi = (np.percentile(flat, 2, axis=0), np.percentile(flat, 98, axis=0)) if len(flat) else (np.zeros(3), np.full(3, 0.3))
    x = np.clip((rgb - lo) / np.maximum(hi - lo, 1e-3), 0, 1) ** 0.85
    return (np.where(np.isfinite(x), x, 0) * 255).astype(np.uint8)


def render_week(bands: dict, *, grid, primary_utm, buffer_outer_utm, changes_utm, when: dt.datetime, scene_id: str, week: str) -> bytes:
    """The whole asset as this week's clearest latest look saw it, boundary and buffer drawn, and any
    change found this week outlined (DECISIONS.md D-057)."""
    rgb = stretch_one(bands)
    return render(rgb, win=(0, grid.height, 0, grid.width), grid=grid, primary_utm=primary_utm,
                  buffer_outer_utm=buffer_outer_utm, change_utm=changes_utm, label=f"Week {week}", when=when, scene_id=scene_id)


def window_for(component: np.ndarray, min_side_px: int = 64, grow: float = 3.0) -> tuple[int, int, int, int]:
    """Square window around a change, at least `min_side_px` wide, clipped to the grid."""
    H, W = component.shape
    ys, xs = np.nonzero(component)
    cy, cx = (ys.min() + ys.max()) / 2, (xs.min() + xs.max()) / 2
    side = int(max(min_side_px, grow * max(ys.max() - ys.min() + 1, xs.max() - xs.min() + 1)))
    side = min(side, H, W) if min(H, W) >= min_side_px else max(H, W)
    r0 = int(round(cy - side / 2))
    c0 = int(round(cx - side / 2))
    r0 = max(0, min(r0, H - side)) if H >= side else 0
    c0 = max(0, min(c0, W - side)) if W >= side else 0
    return r0, min(H, r0 + side), c0, min(W, c0 + side)


def _outline(draw: ImageDraw.ImageDraw, geom_px, colour, width: int, dash: int | None) -> None:
    polys = getattr(geom_px, "geoms", [geom_px])
    for p in polys:
        for ring in [p.exterior, *p.interiors]:
            pts = list(ring.coords)
            if dash is None:
                draw.line(pts, fill=colour, width=width, joint="curve")
                continue
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                seg = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
                steps = max(1, int(seg // dash))
                for s in range(0, steps, 2):
                    a, b = s / steps, min(1.0, (s + 1) / steps)
                    draw.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)], fill=colour, width=width)


def render(
    rgb: np.ndarray,
    *,
    win,
    grid,
    primary_utm,
    buffer_outer_utm,
    change_utm,
    label: str,
    when: dt.datetime,
    scene_id: str,
) -> bytes:
    from shapely.affinity import affine_transform
    from shapely.geometry import box

    r0, r1, c0, c1 = win
    h, w = r1 - r0, c1 - c0
    scale = OUT_PX / max(h, w)
    big = Image.fromarray(rgb, "RGB").resize((int(round(w * scale)), int(round(h * scale))), Image.NEAREST)
    canvas = Image.new("RGB", (OUT_PX, OUT_PX), (20, 24, 28))
    canvas.paste(big, (0, 0))
    draw = ImageDraw.Draw(canvas)

    # UTM metres -> chip pixels
    x_left = grid.x0 + c0 * grid.res
    y_top = grid.y0 - r0 * grid.res
    k = scale / grid.res
    to_px = [k, 0, 0, -k, -x_left * k, y_top * k]
    view = box(x_left, y_top - h * grid.res, x_left + w * grid.res, y_top)
    for geom, colour, width, dash in (
        (buffer_outer_utm, BUFFER, 2, 7),
        (primary_utm, FTL, 3, None),
        (change_utm, CHANGE, 3, 6),
    ):
        if geom is None or geom.is_empty:
            continue
        g = geom.intersection(view.buffer(grid.res * 4))
        if not g.is_empty and g.geom_type in ("Polygon", "MultiPolygon"):
            _outline(draw, affine_transform(g, to_px), colour, width, dash)

    band = Image.new("RGBA", (OUT_PX, 30), (0, 0, 0, 150))
    canvas.paste(band, (0, 0), band)
    canvas.paste(band, (0, OUT_PX - 30), band)
    draw.text((10, 5), f"{label}  {when.date().isoformat()}  ·  Sentinel-2 L2A, 10 m pixels", font=_font(15, bold=True), fill=(255, 255, 255))
    draw.text((10, OUT_PX - 25), f"Contains modified Copernicus Sentinel data {when.year}  ·  {scene_id}", font=_font(12), fill=(235, 235, 235))
    bar = 100 * k
    draw.rectangle([OUT_PX - 20 - bar, OUT_PX - 44, OUT_PX - 20, OUT_PX - 39], fill=(255, 255, 255))
    draw.text((OUT_PX - 20 - bar, OUT_PX - 62), "100 m", font=_font(12, bold=True), fill=(255, 255, 255))
    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
