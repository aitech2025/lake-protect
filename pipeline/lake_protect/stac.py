"""Scene discovery on Earth Search (CONTEXT.md section 8.1) with the no-look-ahead guard.

Invariant 10: the backtest reads no scene acquired after `as_of`. Two layers enforce it:
1. the STAC query's datetime range ends at the end of the `as_of` day (UTC);
2. every item returned is checked again, and `assert_not_after` is called before any pixel is
   read, so a catalogue that ignored the range still could not leak a later scene.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass

from lake_protect.rules import cache_dir, rules


class LookAheadError(RuntimeError):
    """A scene acquired after `as_of` reached the reader."""


@dataclass(frozen=True)
class Scene:
    id: str
    sensor: str
    acquired_at: dt.datetime  # UTC
    cloud_pct: float | None
    epsg: int | None
    footprint: dict  # GeoJSON geometry
    hrefs: dict  # band -> https URL
    scale_offset: dict  # band -> [scale, offset]
    stac_href: str
    processing_baseline: str | None = None

    @property
    def date(self) -> dt.date:
        return self.acquired_at.date()

    def to_json(self) -> dict:
        d = asdict(self)
        d["acquired_at"] = self.acquired_at.isoformat()
        return d

    @classmethod
    def from_json(cls, d: dict) -> "Scene":
        d = dict(d)
        d["acquired_at"] = dt.datetime.fromisoformat(d["acquired_at"])
        return cls(**d)


def end_of_day(day: dt.date) -> dt.datetime:
    return dt.datetime.combine(day, dt.time(23, 59, 59, 999999), tzinfo=dt.timezone.utc)


def assert_not_after(scene: Scene, as_of: dt.date) -> None:
    if scene.acquired_at > end_of_day(as_of):
        raise LookAheadError(f"Scene {scene.id} ({scene.acquired_at.isoformat()}) was acquired after as_of {as_of}")


def _item_to_scene(item: dict) -> Scene:
    props = item["properties"]
    bands = rules()["sentinel2"]["bands"] + ["scl"]
    hrefs, scale_offset = {}, {}
    for band in bands + ["visual"]:
        asset = item["assets"].get(band)
        if not asset:
            continue
        hrefs[band] = asset["href"]
        rb = (asset.get("raster:bands") or [{}])[0]
        scale_offset[band] = [rb.get("scale", 1.0), rb.get("offset", 0.0)]
    epsg = props.get("proj:epsg")
    if epsg is None and str(props.get("proj:code", "")).startswith("EPSG:"):
        epsg = int(str(props["proj:code"]).split(":")[1])
    self_link = next((l["href"] for l in item.get("links", []) if l.get("rel") == "self"), "")
    return Scene(
        id=item["id"],
        sensor="sentinel-2",
        acquired_at=dt.datetime.fromisoformat(props["datetime"].replace("Z", "+00:00")).astimezone(dt.timezone.utc),
        cloud_pct=props.get("eo:cloud_cover"),
        epsg=epsg,
        footprint=item["geometry"],
        hrefs=hrefs,
        scale_offset=scale_offset,
        stac_href=self_link,
        processing_baseline=props.get("s2:processing_baseline"),
    )


def search_items(bbox_ll: tuple[float, float, float, float], start: dt.date, as_of: dt.date) -> list[dict]:
    """Raw STAC items, cached per query so repeat runs work offline. Range ends at as_of."""
    cfg = rules()["sentinel2"]
    key = f"{cfg['collection']}_{'_'.join(f'{v:.4f}' for v in bbox_ll)}_{start}_{as_of}"
    path = cache_dir() / "stac" / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    import pystac_client

    client = pystac_client.Client.open(cfg["stac_url"])
    search = client.search(
        collections=[cfg["collection"]],
        bbox=list(bbox_ll),
        datetime=[dt.datetime.combine(start, dt.time(0), tzinfo=dt.timezone.utc), end_of_day(as_of)],
        query={"eo:cloud_cover": {"lte": cfg["max_scene_cloud_pct"]}},
        max_items=5000,
    )
    items = [i.to_dict() for i in search.items()]
    # Only cache a query whose window is fully in the past, so a later run still sees new scenes.
    if as_of < dt.date.today():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(items), encoding="utf-8")
    return items


def parse_items(items: list[dict]) -> list[Scene]:
    bands = rules()["sentinel2"]["bands"] + ["scl"]
    out = []
    for item in items:
        scene = _item_to_scene(item)
        if all(b in scene.hrefs for b in bands):
            out.append(scene)
    return out


def scenes_for(aoi_ll, start: dt.date, as_of: dt.date, scenes: list[Scene] | None = None) -> list[Scene]:
    """Scenes covering the AOI, acquired on or before as_of, one per acquisition date.

    Hyderabad sits near the UTM 43/44 edge, so most dates arrive twice (43QHV and 44QKE). Keep one:
    a footprint that fully contains the AOI, preferring the analysis CRS (EPSG:32644) so no
    resampling across zones is needed.
    """
    from shapely.geometry import shape

    if scenes is None:
        scenes = parse_items(search_items(aoi_ll.bounds, start, as_of))
    by_date: dict[dt.date, list[Scene]] = {}
    for scene in scenes:
        if scene.acquired_at > end_of_day(as_of) or scene.date < start:
            continue  # layer 2 of the no-look-ahead guard
        if not _footprint(scene).contains(aoi_ll):
            continue
        by_date.setdefault(scene.date, []).append(scene)
    chosen = []
    for day in sorted(by_date):
        options = sorted(by_date[day], key=lambda s: (s.epsg != 32644, s.cloud_pct or 0, s.id))
        chosen.append(options[0])
    return chosen


_FOOTPRINTS: dict[str, object] = {}


def _footprint(scene: Scene):
    from shapely.geometry import shape
    from shapely.prepared import prep

    if scene.id not in _FOOTPRINTS:
        _FOOTPRINTS[scene.id] = prep(shape(scene.footprint))
    return _FOOTPRINTS[scene.id]
