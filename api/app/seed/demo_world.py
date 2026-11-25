"""Geometry for the fictional demo world (data/demo/world.yml).

Shapes are generated deterministically from the world file, so the seed, the image chips and the
base-map tiles always agree.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import yaml
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon

from app.config import settings

M_PER_DEG_LAT = 111_320.0


def world_path() -> Path:
    return settings.data_dir / "demo" / "world.yml"


@dataclass
class World:
    spec: dict

    @classmethod
    def load(cls, path: Path | None = None) -> "World":
        return cls(yaml.safe_load((path or world_path()).read_text(encoding="utf-8")))

    @property
    def origin(self) -> tuple[float, float]:
        lon, lat = self.spec["origin"]
        return float(lon), float(lat)

    def to_lonlat(self, east: float, north: float) -> tuple[float, float]:
        lon0, lat0 = self.origin
        return lon0 + east / (M_PER_DEG_LAT * math.cos(math.radians(lat0))), lat0 + north / M_PER_DEG_LAT

    def from_lonlat(self, lon: float, lat: float) -> tuple[float, float]:
        lon0, lat0 = self.origin
        return (lon - lon0) * M_PER_DEG_LAT * math.cos(math.radians(lat0)), (lat - lat0) * M_PER_DEG_LAT

    def poly_to_lonlat(self, poly: Polygon) -> Polygon:
        return Polygon([self.to_lonlat(x, y) for x, y in poly.exterior.coords])

    # Shapes in local metres ----------------------------------------------------------------
    @staticmethod
    def _blob(cx: float, cy: float, r: float, seed: int, n: int = 72, wobble: float = 0.12) -> Polygon:
        rng = random.Random(seed)
        harmonics = [(k, rng.uniform(0.3, 1.0) * wobble / k ** 0.6, rng.uniform(0, 2 * math.pi)) for k in range(2, 6)]
        pts = []
        for i in range(n):
            t = 2 * math.pi * i / n
            rr = r * (1 + sum(a * math.sin(k * t + p) for k, a, p in harmonics))
            pts.append((cx + rr * math.cos(t), cy + rr * math.sin(t)))
        return Polygon(pts).buffer(0)

    def asset_shape_m(self, asset: dict) -> Polygon:
        if "lake" in asset:
            (x, y), r = asset["lake"]["at"], asset["lake"]["r"]
            return self._blob(x, y, r, asset["lake"]["seed"])
        (x, y), (w, h) = asset["parcel"]["at"], asset["parcel"]["size"]
        rect = Polygon([(x - w / 2, y - h / 2), (x + w / 2, y - h / 2), (x + w / 2, y + h / 2), (x - w / 2, y + h / 2)])
        return affinity.rotate(rect, asset["parcel"].get("rot", 0), origin=(x, y))

    def asset_centre_m(self, asset: dict) -> tuple[float, float]:
        return tuple(asset["lake"]["at"] if "lake" in asset else asset["parcel"]["at"])

    def water_m(self, asset: dict, season: float = 0.0) -> Polygon | None:
        """The water extent: a little inside the FTL, lower when `season` is positive (dry)."""
        if "lake" not in asset:
            return None
        shape = self.asset_shape_m(asset)
        r = asset["lake"]["r"]
        return shape.buffer(-(0.06 + 0.08 * season) * r)

    def change_m(self, scenario: dict, grow: float = 1.0) -> Polygon:
        asset = self.asset(scenario["asset"])
        ch = scenario["change"]
        cx, cy = self.asset_centre_m(asset)
        w, h = (s * math.sqrt(grow) for s in ch["size"])
        seed = sum(map(ord, scenario["key"]))
        if ch["shape"] == "inside":
            ox, oy = ch["offset"]
            px, py, rot = cx + ox, cy + oy, 0.0
        else:
            ang = math.radians(ch["angle"])
            shape = self.asset_shape_m(asset)
            # Walk out from the centre to the boundary along the angle.
            far = Point(cx + 5000 * math.cos(ang), cy + 5000 * math.sin(ang))
            edge = shape.exterior.intersection(LineString([(cx, cy), far.coords[0]]))
            ex, ey = (edge.coords[0] if edge.geom_type == "Point" else list(edge.geoms)[0].coords[0])
            extra = {"edge": 0.0, "ring": 90.0, "far": 420.0}[ch["shape"]]
            px, py = ex + extra * math.cos(ang), ey + extra * math.sin(ang)
            rot = math.degrees(ang) + 90
        blob = self._blob(0, 0, 1.0, seed, wobble=0.18)
        blob = affinity.scale(blob, w / 2, h / 2, origin=(0, 0))
        blob = affinity.rotate(blob, rot, origin=(0, 0))
        return affinity.translate(blob, px, py)

    def box_m(self, asset_key: str, box: list[float]) -> Polygon:
        cx, cy = self.asset_centre_m(self.asset(asset_key))
        x0, x1, y0, y1 = box
        return Polygon([(cx + x0, cy + y0), (cx + x1, cy + y0), (cx + x1, cy + y1), (cx + x0, cy + y1)])

    # Lookups ----------------------------------------------------------------------------------
    @cached_property
    def assets_by_key(self) -> dict[str, dict]:
        return {a["key"]: a for a in self.spec["assets"]}

    def asset(self, key: str) -> dict:
        return self.assets_by_key[key]

    def lonlat_multipolygon(self, poly_m: Polygon) -> MultiPolygon:
        return MultiPolygon([self.poly_to_lonlat(poly_m)])

    def bounds_lonlat(self, margin_m: float = 600) -> tuple[float, float, float, float]:
        xs, ys = [], []
        for a in self.spec["assets"]:
            minx, miny, maxx, maxy = self.asset_shape_m(a).bounds
            xs += [minx, maxx]
            ys += [miny, maxy]
        w, s = self.to_lonlat(min(xs) - margin_m, min(ys) - margin_m)
        e, n = self.to_lonlat(max(xs) + margin_m, max(ys) + margin_m)
        return w, s, e, n
