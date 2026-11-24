"""Synthetic pictures for the fictional demo world. None of this is satellite data.

- Image chips are drawn at 10 m per pixel, like Sentinel-2, then enlarged with hard pixel edges,
  so they never look sharper than the real sensor. The boundary is drawn on top (section 8.4).
- Base-map tiles are a plain cartographic drawing of the world file, for offline use (M9).
- Field photos are drawings with a large "synthetic" label.

Every image carries a "Demo data" mark.
"""
from __future__ import annotations

import datetime as dt
import io
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely import contains_xy
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from app.seed.demo_world import M_PER_DEG_LAT, World

FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"
DEMO_MARK = "DEMO DATA · SYNTHETIC IMAGE · NOT SATELLITE DATA"


def font(size: int, bold: bool = False, telugu: bool = False) -> ImageFont.FreeTypeFont:
    name = f"NotoSans{'Telugu' if telugu else ''}-{'Bold' if bold else 'Regular'}.ttf"
    return ImageFont.truetype(str(FONT_DIR / name), size)


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _noise(shape: tuple[int, int], seed: int, scale: float = 1.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(0, scale, size=shape)


# Image chips ------------------------------------------------------------------------------------

CHANGE_COLOUR = {
    "soil_fill": (196, 168, 128),
    "clearing": (182, 160, 112),
    "levelling": (190, 172, 138),
    "building": (204, 204, 198),
    "small_structure": (200, 196, 188),
    "other": (180, 170, 150),
}


def chip_window(world: World, scenario: dict, grow: float = 1.0) -> tuple[float, float, float]:
    change = world.change_m(scenario, grow)
    cx, cy = change.centroid.x, change.centroid.y
    minx, miny, maxx, maxy = change.bounds
    side = max(560.0, 4.0 * max(maxx - minx, maxy - miny))
    return cx, cy, side


def render_chip(
    world: World,
    scenario: dict,
    *,
    when: dt.date,
    after: bool,
    grow: float = 1.0,
    window: tuple[float, float, float] | None = None,
    out_px: int = 512,
) -> bytes:
    asset = world.asset(scenario["asset"])
    cx, cy, side = window or chip_window(world, scenario, grow)
    n = int(round(side / 10))  # 10 m pixels
    xs = cx - side / 2 + (np.arange(n) + 0.5) * 10
    ys = cy + side / 2 - (np.arange(n) + 0.5) * 10
    gx, gy = np.meshgrid(xs, ys)

    seed = sum(map(ord, scenario["key"])) + (7 if after else 0)
    season = 0.15 if after else 0.0
    base = np.array([148, 134, 108], dtype=float)
    img = np.broadcast_to(base, (n, n, 3)).copy()
    img += _noise((n, n, 1), seed, 9.0)

    shape = world.asset_shape_m(asset)
    margin = shape.buffer(45).difference(shape.buffer(-5))
    img[contains_xy(margin, gx, gy)] = (72, 96, 52)
    for village in world.spec.get("villages", []):
        (vx, vy), vr = village["at"], village["r"]
        img[(gx - vx) ** 2 + (gy - vy) ** 2 < vr ** 2] = (166, 160, 150)
    for road in world.spec.get("roads", []):
        line = LineString(road).buffer(7)
        img[contains_xy(line, gx, gy)] = (176, 170, 160)
    water = world.water_m(asset, season)
    if water is not None and not water.is_empty:
        img[contains_xy(water, gx, gy)] = (34, 58, 74)
    if after:
        change = world.change_m(scenario, grow)
        colour = CHANGE_COLOUR.get(scenario["change"]["type"], CHANGE_COLOUR["other"])
        img[contains_xy(change, gx, gy)] = colour
    img += _noise((n, n, 3), seed + 1, 4.0)
    img = np.clip(img * (1.04 if after else 1.0), 0, 255).astype(np.uint8)

    big = Image.fromarray(img, "RGB").resize((out_px, out_px), Image.NEAREST)
    draw = ImageDraw.Draw(big)
    scale = out_px / side

    def to_px(x: float, y: float) -> tuple[float, float]:
        return (x - (cx - side / 2)) * scale, ((cy + side / 2) - y) * scale

    def outline(poly: Polygon, colour, width: int, dash: int | None = None) -> None:
        pts = [to_px(x, y) for x, y in poly.exterior.coords]
        if dash is None:
            draw.line(pts, fill=colour, width=width, joint="curve")
            return
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            seg = math.hypot(x1 - x0, y1 - y0)
            steps = max(1, int(seg // dash))
            for i in range(0, steps, 2):
                a, b = i / steps, min(1, (i + 1) / steps)
                draw.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)], fill=colour, width=width)

    width_m = 30 if ("lake" in asset and shape.area >= 100_000) else 9
    if "lake" in asset:
        outline(shape.buffer(width_m), (230, 70, 60), 2, dash=7)
    outline(shape, (70, 160, 255), 3)
    outline(world.change_m(scenario, grow), (255, 214, 64), 2, dash=5)

    # Labels
    draw.rectangle([0, 0, out_px, 30], fill=(0, 0, 0, 160))
    draw.text((10, 6), f"{'After' if after else 'Before'}  {when.isoformat()}  ·  demo sensor, 10 m pixels", font=font(14, bold=True), fill=(255, 255, 255))
    draw.rectangle([0, out_px - 26, out_px, out_px], fill=(150, 20, 20))
    draw.text((10, out_px - 22), DEMO_MARK, font=font(12, bold=True), fill=(255, 255, 255))
    bar_px = 100 * scale
    draw.rectangle([out_px - 20 - bar_px, out_px - 46, out_px - 20, out_px - 40], fill=(255, 255, 255))
    draw.text((out_px - 20 - bar_px, out_px - 64), "100 m", font=font(12), fill=(255, 255, 255))
    return _png(big)


# Weekly images ----------------------------------------------------------------------------------

def render_week(world: World, asset_key: str, *, when: dt.date, week: str, changes: list[tuple[dict, float]], out_px: int = 480) -> bytes:
    """One asset as the week's screen saw it: the whole lake or parcel with its buffer, 10 m pixels,
    and every change that had happened by that date drawn in, outlined in yellow."""
    asset = world.asset(asset_key)
    shape = world.asset_shape_m(asset)
    minx, miny, maxx, maxy = shape.bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    side = max(520.0, 1.9 * max(maxx - minx, maxy - miny))
    n = int(round(side / 10))
    xs = cx - side / 2 + (np.arange(n) + 0.5) * 10
    ys = cy + side / 2 - (np.arange(n) + 0.5) * 10
    gx, gy = np.meshgrid(xs, ys)

    seed = sum(map(ord, asset_key)) + when.toordinal() % 97
    season = 0.08 * (1 + math.sin(when.toordinal() / 58.0))
    img = np.broadcast_to(np.array([148, 134, 108], dtype=float), (n, n, 3)).copy()
    img += _noise((n, n, 1), sum(map(ord, asset_key)), 9.0)
    margin = shape.buffer(45).difference(shape.buffer(-5))
    img[contains_xy(margin, gx, gy)] = (72, 96, 52)
    for village in world.spec.get("villages", []):
        (vx, vy), vr = village["at"], village["r"]
        img[(gx - vx) ** 2 + (gy - vy) ** 2 < vr ** 2] = (166, 160, 150)
    for road in world.spec.get("roads", []):
        img[contains_xy(LineString(road).buffer(7), gx, gy)] = (176, 170, 160)
    water = world.water_m(asset, season)
    if water is not None and not water.is_empty:
        img[contains_xy(water, gx, gy)] = (34, 58, 74)
    for scenario, grow in changes:
        colour = CHANGE_COLOUR.get(scenario["change"]["type"], CHANGE_COLOUR["other"])
        img[contains_xy(world.change_m(scenario, grow), gx, gy)] = colour
    img += _noise((n, n, 3), seed, 4.0)
    img = np.clip(img, 0, 255).astype(np.uint8)

    big = Image.fromarray(img, "RGB").resize((out_px, out_px), Image.NEAREST)
    draw = ImageDraw.Draw(big)
    scale = out_px / side

    def to_px(x: float, y: float) -> tuple[float, float]:
        return (x - (cx - side / 2)) * scale, ((cy + side / 2) - y) * scale

    def outline(poly: Polygon, colour, width: int, dash: int | None = None) -> None:
        pts = [to_px(x, y) for x, y in poly.exterior.coords]
        if dash is None:
            draw.line(pts, fill=colour, width=width, joint="curve")
            return
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            seg = math.hypot(x1 - x0, y1 - y0)
            steps = max(1, int(seg // dash))
            for i in range(0, steps, 2):
                a, b = i / steps, min(1, (i + 1) / steps)
                draw.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)], fill=colour, width=width)

    width_m = 30 if ("lake" in asset and shape.area >= 100_000) else 9
    if "lake" in asset:
        outline(shape.buffer(width_m), (230, 70, 60), 2, dash=7)
    outline(shape, (70, 160, 255), 3)
    for scenario, grow in changes:
        outline(world.change_m(scenario, grow), (255, 214, 64), 2, dash=5)

    draw.rectangle([0, 0, out_px, 28], fill=(0, 0, 0))
    draw.text((10, 5), f"Week {week}  ·  latest look {when.isoformat()}  ·  demo sensor, 10 m pixels", font=font(13, bold=True), fill=(255, 255, 255))
    draw.rectangle([0, out_px - 24, out_px, out_px], fill=(150, 20, 20))
    draw.text((10, out_px - 21), DEMO_MARK, font=font(11, bold=True), fill=(255, 255, 255))
    bar_px = 100 * scale
    draw.rectangle([out_px - 20 - bar_px, out_px - 42, out_px - 20, out_px - 37], fill=(255, 255, 255))
    draw.text((out_px - 20 - bar_px, out_px - 58), "100 m", font=font(11), fill=(255, 255, 255))
    return _png(big)


# Field photos -----------------------------------------------------------------------------------

def render_field_photo(asset_name: str, when: dt.datetime, stage: str, n: int = 1) -> bytes:
    w, h = 800, 600
    img = Image.new("RGB", (w, h), (196, 220, 240))
    d = ImageDraw.Draw(img)
    for i in range(h // 2):
        c = int(196 + 40 * i / (h / 2))
        d.line([(0, i), (w, i)], fill=(c - 20, c, 245))
    d.rectangle([0, h // 2, w, h], fill=(118, 134, 82))
    d.rectangle([0, int(h * 0.58), w, int(h * 0.66)], fill=(58, 92, 118))  # water line
    rng = random.Random(asset_name + str(n))
    if stage in ("soil_dumped", "land_levelled"):
        for _ in range(4):
            x = rng.randint(80, 600)
            d.polygon([(x, 470), (x + 90, 360 + rng.randint(-20, 20)), (x + 200, 470)], fill=(160, 124, 84))
    else:
        d.rectangle([300, 300, 520, 470], fill=(190, 186, 176))
    d.rectangle([0, 0, w, 54], fill=(150, 20, 20))
    d.text((16, 12), "DEMO DATA · SYNTHETIC FIELD PHOTO", font=font(24, bold=True), fill=(255, 255, 255))
    d.rectangle([0, h - 44, w, h], fill=(0, 0, 0))
    d.text((16, h - 36), f"{asset_name} · {when.strftime('%Y-%m-%d %H:%M')} UTC · photo {n}", font=font(18), fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
    return buf.getvalue()


# Base-map tiles ---------------------------------------------------------------------------------

LAND = (240, 236, 226)
WATER = (164, 202, 230)
VILLAGE = (224, 216, 202)
ROAD = (255, 255, 255)
ROAD_CASING = (205, 198, 186)
PARCEL = (232, 225, 208)
FIELD = (226, 232, 206)


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    n = 2 ** z

    def lat(yy: int) -> float:
        return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * yy / n))))

    return x / n * 360 - 180, lat(y + 1), (x + 1) / n * 360 - 180, lat(y)


def tile_range(z: int, bounds: tuple[float, float, float, float]) -> tuple[range, range]:
    w, s, e, n_ = bounds
    n = 2 ** z

    def tx(lon: float) -> int:
        return int((lon + 180) / 360 * n)

    def ty(lat: float) -> int:
        r = math.radians(lat)
        return int((1 - math.asinh(math.tan(r)) / math.pi) / 2 * n)

    return range(tx(w), tx(e) + 1), range(ty(n_), ty(s) + 1)


class TileRenderer:
    def __init__(self, world: World):
        self.world = world
        lon0, lat0 = world.origin
        self.m_per_deg_lon = M_PER_DEG_LAT * math.cos(math.radians(lat0))
        rng = random.Random(4242)
        fields = []
        for _ in range(140):
            x, y = rng.uniform(-4800, 4800), rng.uniform(-4800, 4800)
            fw, fh = rng.uniform(120, 380), rng.uniform(90, 300)
            fields.append(box(x, y, x + fw, y + fh))
        lakes = [world.asset_shape_m(a).buffer(60) for a in world.spec["assets"]]
        self.fields = unary_union(fields).difference(unary_union(lakes))
        self.water = [w for w in (world.water_m(a) for a in world.spec["assets"]) if w is not None and not w.is_empty]
        self.parcels = [world.asset_shape_m(a) for a in world.spec["assets"] if "parcel" in a]
        self.villages = world.spec.get("villages", [])
        self.roads = world.spec.get("roads", [])

    def render(self, z: int, x: int, y: int, size: int = 256) -> bytes:
        ss = 2  # draw at twice the size, then reduce, for smooth edges
        px = size * ss
        w, s, e, n = tile_bounds(z, x, y)
        lon0, lat0 = self.world.origin

        def merc_y(lat: float) -> float:
            return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))

        my_n, my_s = merc_y(n), merc_y(s)

        def to_px(xm: float, ym: float) -> tuple[float, float]:
            lon = lon0 + xm / self.m_per_deg_lon
            lat = lat0 + ym / M_PER_DEG_LAT
            return (lon - w) / (e - w) * px, (my_n - merc_y(lat)) / (my_n - my_s) * px

        img = Image.new("RGB", (px, px), LAND)
        d = ImageDraw.Draw(img)
        metres_per_px = (e - w) * self.m_per_deg_lon / px

        def poly(p, fill):
            geoms = getattr(p, "geoms", [p])
            for g in geoms:
                if g.geom_type == "Polygon" and not g.is_empty:
                    d.polygon([to_px(*c) for c in g.exterior.coords], fill=fill)
                    for hole in g.interiors:
                        d.polygon([to_px(*c) for c in hole.coords], fill=LAND)

        poly(self.fields, FIELD)
        for v in self.villages:
            (vx, vy), vr = v["at"], v["r"]
            poly(Polygon([(vx + vr * math.cos(t / 20 * math.pi), vy + vr * math.sin(t / 20 * math.pi)) for t in range(40)]), VILLAGE)
            if z >= 15:
                rng = random.Random(vx * 7 + vy)
                for _ in range(40):
                    bx, by = vx + rng.uniform(-0.75, 0.75) * vr, vy + rng.uniform(-0.75, 0.75) * vr
                    poly(box(bx, by, bx + 14, by + 10), (206, 196, 180))
        for p in self.parcels:
            poly(p, PARCEL)
        for wpoly in self.water:
            poly(wpoly, WATER)
        road_w = max(3 * ss, int(22 / metres_per_px))
        for road in self.roads:
            pts = [to_px(*c) for c in road]
            d.line(pts, fill=ROAD_CASING, width=road_w + 2 * ss, joint="curve")
        for road in self.roads:
            d.line([to_px(*c) for c in road], fill=ROAD, width=road_w, joint="curve")
        return _png(img.resize((size, size), Image.LANCZOS))
