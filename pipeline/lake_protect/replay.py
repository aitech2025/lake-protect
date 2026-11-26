"""Resumable, as-of weekly historical replay for the M3 blind backtest.

Each replay date runs the production screen against only scenes acquired on or before that date.
A candidate's `detected_at` is the first replay date on which the frozen detector emitted it,
not the retrospective first-change date. This is the date used for lead-time scoring.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Callable


class ReplayError(RuntimeError):
    """The replay output cannot safely be resumed."""


def weekly_dates(start: dt.date, end: dt.date, step_days: int = 7) -> list[dt.date]:
    if step_days < 1:
        raise ValueError("step_days must be at least 1")
    if start > end:
        raise ValueError("start must be on or before end")
    dates = []
    day = start
    while day <= end:
        dates.append(day)
        day += dt.timedelta(days=step_days)
    if dates[-1] != end:
        dates.append(end)
    return dates


def _json_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(path)


def _asset_fingerprint(aois: list) -> list[dict]:
    from shapely.geometry import mapping

    return [
        {
            "asset_id": a.asset_id,
            "asset_key": a.asset_key,
            "baseline_date": a.baseline_date.isoformat(),
            "primary_geometry": mapping(a.primary_ll),
        }
        for a in sorted(aois, key=lambda x: x.asset_key)
    ]


def _candidate_key(properties: dict) -> str:
    """Stable event key across weekly runs; avoid relying on run-local candidate IDs."""
    from shapely.geometry import shape

    geom = shape(properties["geometry"])
    centre = geom.centroid
    identity = {
        "asset_key": properties.get("asset_key"),
        "change_type": properties.get("change_type"),
        "first_changed_at": properties.get("first_changed_at"),
        "area_sq_m_rounded": round(float(properties.get("area_sq_m") or 0) / 10) * 10,
        "centroid": [round(centre.x, 5), round(centre.y, 5)],
    }
    return "replay-" + _json_hash(identity)[:20]


def _load_week_features(path: Path, as_of: dt.date) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("type") != "FeatureCollection" or not isinstance(data.get("features"), list):
        raise ReplayError(f"Weekly report {path} does not contain a GeoJSON FeatureCollection")
    out = []
    for feature in data["features"]:
        properties = dict(feature.get("properties") or {})
        if not isinstance(feature.get("geometry"), dict):
            raise ReplayError(f"Weekly candidate in {path} has no GeoJSON geometry")
        properties["geometry_crs"] = "EPSG:4326"
        properties["detected_at"] = as_of.isoformat()
        properties["replay_as_of"] = as_of.isoformat()
        properties["replay_detection_id"] = _candidate_key({**properties, "geometry": feature["geometry"]})
        out.append({
            "type": "Feature",
            "id": properties["replay_detection_id"],
            "geometry": feature["geometry"],
            "properties": properties,
        })
    return out


def run_replay(
    aois: list,
    *,
    start: dt.date,
    end: dt.date,
    out_dir: Path,
    step_days: int = 7,
    workers: int = 16,
    with_chips: bool = True,
    use_radar: bool = True,
    resume: bool = True,
    log: Callable[[str], None] = print,
    screen_run: Callable | None = None,
    report_writer: Callable | None = None,
) -> dict:
    """Replay the production detector at weekly as-of dates and checkpoint every completed week.

    The run fingerprint binds the output directory to its date range, AOIs and exact detector
    rules hash. A changed AOI, date range or rules file must use a new output directory.
    """
    if not aois:
        raise ValueError("at least one AOI is required")
    dates = weekly_dates(start, end, step_days)
    from lake_protect.rules import rule_version, rules_sha256
    from lake_protect import screen

    execute = screen_run or screen.run
    write_week = report_writer or screen.write_report
    rules_hash = rules_sha256()
    rule = rule_version()
    config = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "step_days": step_days,
        "rules_sha256": rules_hash,
        "rule_version": rule,
        "assets": _asset_fingerprint(aois),
    }
    fingerprint = _json_hash(config)
    out_dir = Path(out_dir)
    manifest_path = out_dir / "replay-manifest.json"
    checkpoints = out_dir / "checkpoints"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("fingerprint") != fingerprint:
            raise ReplayError(
                "Replay inputs or detector rules differ from this output directory; use a new directory"
            )
        if not resume:
            raise FileExistsError(f"{out_dir} already contains a replay; use a new directory or enable resume")
    else:
        out_dir.mkdir(parents=True, exist_ok=True)
        existing = {
            "schema_version": 1,
            "status": "running",
            "fingerprint": fingerprint,
            "config": config,
            "as_of_dates": [d.isoformat() for d in dates],
            "completed_dates": [],
            "detections": 0,
        }
        _atomic_json(manifest_path, existing)

    detections: dict[str, dict] = {}
    completed = set(existing.get("completed_dates", []))
    for day in dates:
        day_key = day.isoformat()
        checkpoint = checkpoints / f"{day_key}.json"
        if day_key in completed and checkpoint.exists():
            saved = json.loads(checkpoint.read_text(encoding="utf-8"))
            if saved.get("fingerprint") != fingerprint or saved.get("as_of") != day_key:
                raise ReplayError(f"Checkpoint {checkpoint} does not match this replay")
            week_features = saved.get("detections", [])
            log(f"{day_key}: resumed ({len(week_features)} candidates)")
        else:
            log(f"{day_key}: screening {len(aois)} assets")
            try:
                results, meta = execute(
                    aois, day, workers=workers, with_chips=with_chips, use_radar=use_radar, log=log
                )
                week_dir = out_dir / "weeks" / day_key
                report_path = write_week(results, meta, week_dir)
                week_features = _load_week_features(Path(report_path) / "candidates.geojson", day)
                _atomic_json(checkpoint, {
                    "schema_version": 1,
                    "fingerprint": fingerprint,
                    "as_of": day_key,
                    "meta": meta,
                    "detections": week_features,
                })
                completed.add(day_key)
            except Exception as exc:
                existing.update(status="failed", failed_date=day_key,
                                error=f"{type(exc).__name__}: {exc}"[:500],
                                completed_dates=sorted(completed))
                _atomic_json(manifest_path, existing)
                raise
        for feature in week_features:
            key = feature["id"]
            prior = detections.get(key)
            if prior is None or feature["properties"]["detected_at"] < prior["properties"]["detected_at"]:
                detections[key] = feature
        existing.update(
            status="running",
            completed_dates=sorted(completed),
            detections=len(detections),
            last_completed_date=day_key,
            failed_date=None,
            error=None,
        )
        _atomic_json(out_dir / "detections.geojson", {
            "type": "FeatureCollection",
            "features": sorted(detections.values(), key=lambda f: (f["properties"]["detected_at"], f["id"])),
        })
        _atomic_json(manifest_path, existing)

    existing.update(status="complete", completed_dates=[d.isoformat() for d in dates],
                    detections=len(detections), detections_path="detections.geojson")
    _atomic_json(manifest_path, existing)
    log(f"Replay complete: {len(dates)} dates, {len(detections)} unique detections")
    return existing
