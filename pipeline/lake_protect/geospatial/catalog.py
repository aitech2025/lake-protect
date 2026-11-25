"""STAC discovery and scene suitability for Sentinel imagery."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

@dataclass(frozen=True)
class SceneDecision:
    item_id: str
    collection: str
    acquired_at: str | None
    sensor: str
    cloud_cover: float | None
    gsd_m: float | None
    suitable: bool
    reasons: tuple[str, ...]
    assets: dict[str, str]
    def as_dict(self) -> dict[str, Any]: return asdict(self)

def assess_item(item: Any, *, max_cloud_pct: float = 35.0, max_age_days: int | None = None, now: datetime | None = None) -> SceneDecision:
    props = item.properties or {}
    cloud = props.get("eo:cloud_cover")
    gsd = props.get("gsd") or props.get("spatial_resolution")
    acquired = props.get("datetime") or props.get("start_datetime")
    collection = item.collection_id or "unknown"
    sensor = str(props.get("platform") or props.get("constellation") or collection)
    reasons: list[str] = []
    if cloud is not None and float(cloud) > max_cloud_pct: reasons.append(f"cloud_cover>{max_cloud_pct:g}%")
    if not acquired: reasons.append("missing_acquisition_datetime")
    elif max_age_days is not None:
        stamp = datetime.fromisoformat(str(acquired).replace("Z", "+00:00"))
        current = now or datetime.now(stamp.tzinfo)
        if (current - stamp).days > max_age_days: reasons.append("observation_too_old")
    hrefs = {key: asset.href for key, asset in item.assets.items() if getattr(asset, "href", None)}
    if not hrefs: reasons.append("no_accessible_assets")
    if collection.lower().startswith("sentinel-2") and not any(k in hrefs for k in ("B03", "green")):
        reasons.append("missing_green_band")
    return SceneDecision(item_id=item.id, collection=collection, acquired_at=str(acquired) if acquired else None,
        sensor=sensor, cloud_cover=float(cloud) if cloud is not None else None,
        gsd_m=float(gsd) if gsd is not None else None, suitable=not reasons, reasons=tuple(reasons), assets=hrefs)

def search_scenes(*, endpoint: str, collections: list[str], bbox: list[float], start: str, end: str,
                  max_cloud_pct: float = 35.0, limit: int = 100) -> list[dict[str, Any]]:
    try: from pystac_client import Client
    except ImportError as exc: raise RuntimeError("Install pipeline geo extras to enable STAC discovery") from exc
    if len(bbox) != 4 or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
        raise ValueError("bbox must be [west,south,east,north] in EPSG:4326")
    client = Client.open(endpoint)
    items = client.search(collections=collections, bbox=bbox, datetime=f"{start}/{end}", max_items=limit).items()
    decisions = [assess_item(item, max_cloud_pct=max_cloud_pct).as_dict() for item in items]
    return sorted(decisions, key=lambda x: x.get("acquired_at") or "", reverse=True)
