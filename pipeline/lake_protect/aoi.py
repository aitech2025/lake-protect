"""Area of interest and analysis grid for one asset (CONTEXT.md section 8.3).

The AOI is the defined boundary, its buffer and the 100 m watch ring. Everything is analysed on
a 10 m grid in EPSG:32644, snapped to whole multiples of 10 m so every scene lands on the same
pixels, whichever UTM zone it arrives in.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import math
from dataclasses import dataclass, field

import numpy as np
from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform as shp_transform

from lake_protect.rules import rules

ACRE_SQ_M = 4046.86
_TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True).transform
_TO_LL = Transformer.from_crs("EPSG:32644", "EPSG:4326", always_xy=True).transform


def to_utm(geom):
    return shp_transform(_TO_UTM, geom)


def to_lonlat(geom):
    return shp_transform(_TO_LL, geom)


def buffer_width_m(area_ha: float, cfg: dict | None = None) -> float:
    """Section 4 widths, as in api/app/rules/config.yaml: 30 m at 10 ha or more, else 9 m."""
    cfg = cfg or {"lake_10ha_or_more": 30, "lake_under_10ha": 9, "threshold_ha": 10}
    return cfg["lake_10ha_or_more"] if area_ha >= cfg["threshold_ha"] else cfg["lake_under_10ha"]


@dataclass
class Grid:
    crs: str
    x0: float  # west edge
    y0: float  # north edge
    width: int
    height: int
    res: float = 10.0

    @property
    def transform(self):
        from affine import Affine

        return Affine(self.res, 0, self.x0, 0, -self.res, self.y0)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return (self.x0, self.y0 - self.height * self.res, self.x0 + self.width * self.res, self.y0)

    def key(self) -> str:
        raw = f"{self.crs}|{self.x0:.1f}|{self.y0:.1f}|{self.width}|{self.height}|{self.res}"
        return hashlib.sha1(raw.encode()).hexdigest()[:16]


@dataclass
class AssetAOI:
    asset_id: int | None
    asset_key: str
    name: str
    baseline_date: dt.date
    primary_ll: object  # shapely geometry, lon/lat
    ring_ll: object  # outer edge of the watch ring, lon/lat (primary + buffer + ring)
    grid: Grid
    primary_utm: object = None
    aoi_utm: object = None
    buffer_outer_utm: object = None
    masks: dict = field(default_factory=dict)

    @property
    def aoi_ll(self):
        return self.ring_ll


def snap_grid(bounds_utm: tuple[float, float, float, float], res: float, pad: float) -> Grid:
    w, s, e, n = bounds_utm
    x0 = math.floor((w - pad) / res) * res
    y0 = math.ceil((n + pad) / res) * res
    x1 = math.ceil((e + pad) / res) * res
    y1 = math.floor((s - pad) / res) * res
    return Grid(rules()["grid"]["crs"], x0, y0, int(round((x1 - x0) / res)), int(round((y0 - y1) / res)), res)


def rasterize(geom_utm, grid: Grid) -> np.ndarray:
    from rasterio.features import rasterize as _rz

    if geom_utm is None or geom_utm.is_empty:
        return np.zeros((grid.height, grid.width), dtype=bool)
    return _rz([(mapping(geom_utm), 1)], out_shape=(grid.height, grid.width), transform=grid.transform, fill=0, dtype="uint8").astype(bool)


def build(
    *,
    asset_key: str,
    name: str,
    primary_geojson: dict,
    baseline_date: dt.date,
    asset_id: int | None = None,
    buffer_geojson: dict | None = None,
    ring_geojson: dict | None = None,
    watch_ring_m: float = 100.0,
) -> AssetAOI:
    """Build the AOI. If the API supplies the stored buffer and ring, they are used as stored;
    otherwise they are derived here with the same widths the API uses."""
    cfg = rules()["grid"]
    primary_ll = shape(primary_geojson)
    if not primary_ll.is_valid:
        primary_ll = primary_ll.buffer(0)
    primary_utm = to_utm(primary_ll)
    if ring_geojson:
        outer_utm = to_utm(shape(ring_geojson)).union(primary_utm)
        if buffer_geojson:
            outer_utm = outer_utm.union(to_utm(shape(buffer_geojson)))
        # A stored ring may be the band only: fill to its outer edge.
        outer_utm = outer_utm.union(primary_utm.buffer(0)).buffer(0)
        from shapely.geometry import MultiPolygon, Polygon

        def _fill(g):
            if g.geom_type == "Polygon":
                return Polygon(g.exterior)
            return MultiPolygon([Polygon(p.exterior) for p in g.geoms])

        outer_utm = _fill(outer_utm)
        buffer_outer = to_utm(shape(buffer_geojson)).union(primary_utm) if buffer_geojson else primary_utm
    else:
        width = buffer_width_m(primary_utm.area / 1e4)
        outer_utm = primary_utm.buffer(width + watch_ring_m)
        buffer_outer = primary_utm.buffer(width)
    grid = snap_grid(outer_utm.bounds, cfg["resolution_m"], cfg["pad_m"])
    aoi = AssetAOI(
        asset_id=asset_id,
        asset_key=asset_key,
        name=name,
        baseline_date=baseline_date,
        primary_ll=primary_ll,
        ring_ll=to_lonlat(outer_utm),
        grid=grid,
        primary_utm=primary_utm,
        aoi_utm=outer_utm,
        buffer_outer_utm=buffer_outer,
    )
    aoi.masks = {"primary": rasterize(primary_utm, grid), "aoi": rasterize(outer_utm, grid)}
    return aoi
