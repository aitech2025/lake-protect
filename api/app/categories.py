"""The kinds of public land GeoGuard watches, read from categories.yaml (DECISIONS.md D-061)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from app.enums import AssetType

FILE = Path(__file__).with_name("categories.yaml")
LIVE = "live"


class CategoryError(ValueError):
    pass


@lru_cache
def registry() -> dict:
    data = yaml.safe_load(FILE.read_text(encoding="utf-8"))
    seen: dict[str, str] = {}
    for name, cat in data["categories"].items():
        if cat["status"] not in ("live", "planned"):
            raise CategoryError(f"{name}: status must be live or planned")
        if cat["primary_kind"] not in ("ftl", "parcel"):
            raise CategoryError(f"{name}: primary_kind must be ftl or parcel")
        for t in cat["types"]:
            if t not in AssetType.__members__:
                raise CategoryError(f"{name}: {t} is not an asset type in the database")
            if t in seen:
                raise CategoryError(f"{t} is in both {seen[t]} and {name}")
            seen[t] = name
    missing = set(AssetType.__members__) - set(seen)
    if missing:
        raise CategoryError(f"Asset types with no category: {sorted(missing)}")
    return data


def category_of(asset_type: str) -> str:
    for name, cat in registry()["categories"].items():
        if asset_type in cat["types"]:
            return name
    raise CategoryError(f"Unknown asset type {asset_type}")


def get(name: str) -> dict:
    try:
        return registry()["categories"][name]
    except KeyError as exc:
        raise CategoryError(f"Unknown category {name}") from exc


def is_live(asset_type: str) -> bool:
    return get(category_of(asset_type))["status"] == LIVE


def primary_kind(asset_type: str) -> str:
    return get(category_of(asset_type))["primary_kind"]


def limits() -> dict:
    return registry()["limits"]


def as_list(counts: dict[str, int] | None = None) -> list[dict]:
    """Every category with its types, labels and, if given, how many locations each watches."""
    reg = registry()
    out = []
    for name, cat in reg["categories"].items():
        out.append({
            "name": name,
            "status": cat["status"],
            "label": cat["label"],
            "one": cat["one"],
            "primary_kind": cat["primary_kind"],
            "custodians": cat["custodians"],
            "boundary_from": cat["boundary_from"],
            "watch_for": cat["watch_for"],
            "needs": cat.get("needs", []),
            "types": [{"type": t, "label": reg["types"][t]} for t in cat["types"]],
            "watched": sum((counts or {}).get(t, 0) for t in cat["types"]),
        })
    return out
