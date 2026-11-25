"""Detection rule file (detect_rules.yaml), the image sources the admin keeps, and the cache directory.

The image sources (DECISIONS.md D-066) are kept in the app, on the Satellites page. A run that can
reach the app applies them with `set_sources`. Only these source settings can change, and only
where they differ from the rule file:
- **Optical:** the catalogue address and collection, the scene cloud limit and the licence line.
- **Radar:** the same, or the radar check switched off.

The detection thresholds stay in the rule file. A run's `rules_sha256` covers the source settings
it used, so two runs with different sources never share a hash.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

import yaml

RULES_PATH = Path(__file__).with_name("detect_rules.yaml")
_SOURCES: dict = {}  # source settings from the app that differ from the rule file


def _file_rules() -> dict:
    return yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def rules() -> dict:
    out = _file_rules()
    for section, values in _SOURCES.items():
        out[section] = {**out.get(section, {}), **copy.deepcopy(values)}
    return out


def rule_version() -> str:
    return rules()["rule_version"]


def rules_sha256() -> str:
    digest = hashlib.sha256(RULES_PATH.read_bytes())
    if _SOURCES:
        digest.update(b"\nsources:" + json.dumps(_SOURCES, sort_keys=True).encode())
    return digest.hexdigest()


def set_sources(found: dict | None) -> list[str]:
    """Apply the screening sources the app holds (GET /pipeline/satellites); None keeps the rule
    file's. Returns lines saying what the run uses."""
    _SOURCES.clear()
    rules.cache_clear()
    if found is None:
        return ["Image sources: the rule file's (the app did not answer)"]
    base = _file_rules()
    lines = []
    for purpose, section, keys in (("screen_optical", "sentinel2", ("stac_url", "collection", "max_scene_cloud_pct", "licence_notice")),
                                   ("screen_radar", "radar", ("stac_url", "collection", "licence_notice"))):
        src = found.get(purpose)
        if src is None:
            if purpose == "screen_optical":
                raise RuntimeError("The app has no optical source on: turn one on under Satellites")
            _SOURCES["radar"] = {"enabled": False}
            lines.append("Radar check: off (no radar source is on in the app)")
            continue
        diff = {k: src[k] for k in keys if src.get(k) is not None and src[k] != base[section].get(k)}
        if diff:
            _SOURCES[section] = diff
        lines.append(f"{'Optical' if section == 'sentinel2' else 'Radar'} source: {src['name']} ({src['collection']})"
                     + (f", changed from the rule file: {', '.join(sorted(diff))}" if diff else ""))
    rules.cache_clear()
    return lines


def radar_enabled() -> bool:
    return rules().get("radar", {}).get("enabled", True)


def cache_dir() -> Path:
    """Imagery cache. Must sit outside OneDrive (CONTEXT.md section 11)."""
    root = Path(os.environ.get("LP_CACHE_DIR") or (Path.home() / ".lp-cache"))
    if "onedrive" in str(root.resolve()).lower():
        raise RuntimeError(f"LP_CACHE_DIR ({root}) is inside OneDrive. Set it to a local folder such as C:\\lp-cache.")
    root.mkdir(parents=True, exist_ok=True)
    return root


def configure_gdal() -> None:
    """Read windows from cloud-optimised GeoTIFFs over HTTPS; never download whole scenes."""
    defaults = {
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.tiff,.TIF",
        "GDAL_HTTP_MULTIPLEX": "YES",
        "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
        "GDAL_HTTP_MAX_RETRY": "4",
        "GDAL_HTTP_RETRY_DELAY": "2",
        "GDAL_HTTP_TIMEOUT": "60",
        "AWS_NO_SIGN_REQUEST": "YES",
        "VSI_CACHE": "TRUE",
        "VSI_CACHE_SIZE": str(256 * 1024 * 1024),
        "CPL_VSIL_CURL_CACHE_SIZE": str(512 * 1024 * 1024),
        "GDAL_CACHEMAX": "512",
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)
