"""Spectral indices and the version 0 land classes (CONTEXT.md section 8.4)."""
from __future__ import annotations

import numpy as np

from lake_protect.rules import rules

MASKED, WATER, VEG, BARE, BUILT, OTHER = 0, 1, 2, 3, 4, 5
CLASS_NAMES = {MASKED: "masked", WATER: "water", VEG: "veg", BARE: "bare", BUILT: "built", OTHER: "other"}
CLASS_CODES = {v: k for k, v in CLASS_NAMES.items()}


def _ratio(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        out = (a - b) / (a + b)
    return np.where(np.isfinite(out), out, np.nan).astype(np.float32)


def mndwi(green, swir16):
    return _ratio(green, swir16)


def ndvi(nir, red):
    return _ratio(nir, red)


def ndbi(swir16, nir):
    return _ratio(swir16, nir)


def bsi(swir16, red, nir, blue):
    return _ratio(swir16 + red, nir + blue)


def classify(bands: dict[str, np.ndarray], clear: np.ndarray, cfg: dict | None = None) -> np.ndarray:
    """One class per pixel. Precedence: water, vegetation, bare soil, built, other."""
    c = cfg or rules()["classes"]
    w = mndwi(bands["green"], bands["swir16"])
    v = ndvi(bands["nir"], bands["red"])
    b = bsi(bands["swir16"], bands["red"], bands["nir"], bands["blue"])
    u = ndbi(bands["swir16"], bands["nir"])
    valid = clear & np.isfinite(w) & np.isfinite(v) & np.isfinite(b) & np.isfinite(u)
    out = np.full(w.shape, OTHER, dtype=np.uint8)
    water = w > c["water_mndwi_gt"]
    veg = ~water & (v > c["veg_ndvi_gt"])
    bare = ~water & ~veg & (b > c["bare_bsi_gt"]) & (v < c["bare_ndvi_lt"])
    built = ~water & ~veg & ~bare & (u > c["built_ndbi_gt"]) & (v < c["built_ndvi_lt"])
    out[water] = WATER
    out[veg] = VEG
    out[bare] = BARE
    out[built] = BUILT
    out[~valid] = MASKED
    return out
