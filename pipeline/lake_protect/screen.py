"""Screen many assets at once: one catalogue search, one pass per scene, detection per asset.

Two entry points share this code:
- `lp detect` reads assets from data/assets.geojson and writes a report folder (tuning, M2);
- `lp screen` reads the watch list from the API, sends candidates to `POST /candidates` and
  reports coverage for every asset to `POST /pipeline/runs` (the weekly screen).

Coverage is reported honestly (proposal, "Process each scene once"): an asset is "not observed",
"no usable look", "failed", "screened, no candidate" or "candidate found". Nothing here ever says
that an asset has no encroachment.
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import time
from pathlib import Path

from lake_protect.aoi import AssetAOI, build
from lake_protect.detect import AssetResult, apply_drought_control, detect_asset
from lake_protect.raster import select_and_fetch, window_start
from lake_protect.rules import rule_version, rules, rules_sha256
from lake_protect.stac import parse_items, scenes_for, search_items

API_FIELDS = (
    "asset_id", "geometry", "change_type", "stage_estimate", "last_clear_at", "first_changed_at", "observations",
    "sensor_basis", "confidence", "rule_version", "flags", "area_growth", "before_chip_png_b64", "after_chip_png_b64",
)


def aois_from_file(path: Path, keys: list[str] | None, baseline_override: dt.date | None) -> list[AssetAOI]:
    collection = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for f in collection["features"]:
        p = f["properties"]
        if keys and p["asset_key"] not in keys:
            continue
        baseline = baseline_override or dt.date.fromisoformat(p.get("baseline_date") or p["boundary"]["source_date"])
        out.append(build(asset_key=p["asset_key"], name=p["name"], primary_geojson=f["geometry"], baseline_date=baseline))
    if keys:
        missing = set(keys) - {a.asset_key for a in out}
        if missing:
            raise SystemExit(f"Not in {path}: {', '.join(sorted(missing))}")
    return out


def aois_from_watchlist(items: list[dict], keys: list[str] | None) -> list[AssetAOI]:
    out = []
    for a in items:
        if keys and a["asset_key"] not in keys:
            continue
        b = a["boundaries"]
        primary = b.get("ftl") or b.get("parcel")
        if not primary:
            continue
        out.append(
            build(
                asset_id=a["id"],
                asset_key=a["asset_key"],
                name=a["name"],
                primary_geojson=primary["geometry"],
                buffer_geojson=(b.get("buffer") or {}).get("geometry"),
                ring_geojson=(b.get("watch_ring") or {}).get("geometry"),
                baseline_date=dt.date.fromisoformat(a["baseline_date"]),
            )
        )
    return out


def run(aois: list[AssetAOI], as_of: dt.date, workers: int = 16, with_chips: bool = True, use_radar: bool = True, log=print) -> tuple[list[AssetResult], dict]:
    from shapely.ops import unary_union

    t0 = time.time()
    start = min(window_start(a.baseline_date) for a in aois)
    bbox = unary_union([a.ring_ll for a in aois]).bounds
    log(f"Catalogue: {rules()['sentinel2']['collection']} {start} to {as_of} over {len(aois)} assets")
    scenes = parse_items(search_items(bbox, start, as_of))
    log(f"  {len(scenes)} scenes at or under {rules()['sentinel2']['max_scene_cloud_pct']}% scene cloud")
    by_aoi = {a.asset_key: scenes_for(a.ring_ll, window_start(a.baseline_date), as_of, scenes) for a in aois}
    picks = select_and_fetch(aois, by_aoi, as_of, workers=workers, log=log)
    results = []
    for a in aois:
        try:
            r = detect_asset(a, picks.get(a.asset_key, []), as_of, with_chips, use_radar=use_radar, log=log)
            r.counts["scenes_available"] = len(by_aoi.get(a.asset_key, []))
        except Exception as exc:  # one asset failing never stops the screen; it is reported
            r = AssetResult(aoi=a, as_of=as_of, looks=0, first_look=None, last_look=None, counts={"error": f"{type(exc).__name__}: {exc}"})
        results.append(r)
    if len(results) >= 4:
        apply_drought_control(results)
    else:
        for r in results:
            for c in r.candidates:
                if c["change_type"] == "soil_fill":
                    c["flags"] = sorted(set(c["flags"]) | {"drought_control_not_run"})
    meta = {
        "as_of": as_of.isoformat(),
        "rule_version": rule_version(),
        "rules_sha256": rules_sha256(),
        "collection": rules()["sentinel2"]["collection"],
        "catalogue_start": start.isoformat(),
        "scenes_in_catalogue": len(scenes),
        "seconds": round(time.time() - t0, 1),
    }
    return results, meta


def coverage_status(r: AssetResult) -> str:
    if "error" in r.counts:
        return "failed"
    if r.counts.get("scenes_available", 0) == 0:
        return "not_observed"
    if r.looks < 2:
        return "no_usable_look"
    return "candidate_found" if r.candidates else "no_candidate"


def asset_summary(r: AssetResult) -> dict:
    stale = None
    if r.last_look:
        stale = (r.as_of - r.last_look).days
    return {
        "asset_key": r.aoi.asset_key,
        "asset_id": r.aoi.asset_id,
        "name": r.aoi.name,
        "baseline_date": r.aoi.baseline_date.isoformat(),
        "status": coverage_status(r),
        "looks": r.looks,
        "first_look": r.first_look.isoformat() if r.first_look else None,
        "last_look": r.last_look.isoformat() if r.last_look else None,
        "days_since_last_look": stale,
        "candidates": len(r.candidates),
        "legacy_changes": len(r.legacy),
        "counts": r.counts,
    }


def api_payload(cand: dict) -> dict:
    return {k: cand.get(k) for k in API_FIELDS if k in cand}


def write_report(results: list[AssetResult], meta: dict, out_dir: Path) -> Path:
    """One folder per run: summary.json, candidates.geojson, and the chips as PNG files."""
    out_dir.mkdir(parents=True, exist_ok=True)
    features = []
    for r in results:
        for n, c in enumerate(r.candidates, 1):
            props = {k: v for k, v in c.items() if k not in ("geometry", "before_chip_png_b64", "after_chip_png_b64")}
            props["asset_name"] = r.aoi.name
            for which in ("before", "after"):
                b64 = c.get(f"{which}_chip_png_b64")
                if b64:
                    name = f"chips/{r.aoi.asset_key}_{n}_{which}.png"
                    (out_dir / "chips").mkdir(exist_ok=True)
                    (out_dir / name).write_bytes(base64.b64decode(b64))
                    props[f"{which}_chip"] = name
            features.append({"type": "Feature", "geometry": c["geometry"], "properties": props})
    (out_dir / "candidates.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": features}, indent=1), encoding="utf-8")
    summary = {**meta, "assets": [asset_summary(r) for r in results], "candidates": len(features)}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    # Full API payloads, chips included, keyed by asset_key so `lp replay` can resend them after a
    # demo reset with no internet. Not committed (see .gitignore): it is large and rebuildable.
    with (out_dir / "payloads.jsonl").open("w", encoding="utf-8") as fh:
        for r in results:
            for c in r.candidates:
                fh.write(json.dumps({"asset_key": r.aoi.asset_key, "payload": api_payload(c)}) + "\n")
    return out_dir
