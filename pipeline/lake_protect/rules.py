"""Detection rule file (detect_rules.yaml) and the cache directory."""
from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path

import yaml

RULES_PATH = Path(__file__).with_name("detect_rules.yaml")


@lru_cache(maxsize=1)
def rules() -> dict:
    return yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))


def rule_version() -> str:
    return rules()["rule_version"]


def rules_sha256() -> str:
    return hashlib.sha256(RULES_PATH.read_bytes()).hexdigest()


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
