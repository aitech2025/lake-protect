"""Ground-truth case manifest validation for the M3 blind backtest.

This module validates evidence metadata before any case can enter the primary score.
It deliberately does not infer dates, area, source provenance or event geometry.
"""
from __future__ import annotations

from datetime import date
from math import isfinite
from typing import Any
from urllib.parse import urlparse

from shapely.geometry import shape
from shapely.validation import explain_validity

SCORE_START = date(2018, 1, 1)
SENSITIVE_PROPERTY_NAMES = {
    "owner", "owner_name", "claimant", "claimant_name", "phone",
    "mobile", "aadhaar", "aadhar", "pan",
}


def _parse_date(value: Any, field: str, case_id: str, errors: list[str]) -> date | None:
    if not isinstance(value, str):
        errors.append(f"{case_id}: {field} must be an ISO date string")
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        errors.append(f"{case_id}: {field} must use YYYY-MM-DD")
        return None
    if parsed.isoformat() != value:
        errors.append(f"{case_id}: {field} must use YYYY-MM-DD")
        return None
    return parsed


def validate_case_collection(
    collection: dict[str, Any],
    *,
    minimum_area_acres: float = 0.25,
    score_start: date = SCORE_START,
) -> dict[str, Any]:
    """Validate a GeoJSON FeatureCollection and classify cases for primary scoring.

    Structural/provenance errors make the manifest invalid. A structurally valid case
    can still be excluded from the primary gate with explicit exclusion reasons.
    """
    errors: list[str] = []
    exclusions: list[dict[str, Any]] = []
    eligible: list[str] = []

    if collection.get("type") != "FeatureCollection":
        return {
            "valid": False, "total_cases": 0, "eligible_case_ids": [],
            "excluded_cases": [], "errors": ["Input must be a GeoJSON FeatureCollection"],
        }
    features = collection.get("features")
    if not isinstance(features, list):
        return {
            "valid": False, "total_cases": 0, "eligible_case_ids": [],
            "excluded_cases": [], "errors": ["FeatureCollection.features must be an array"],
        }

    seen: set[str] = set()
    for index, feature in enumerate(features):
        prefix = f"feature[{index}]"
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            errors.append(f"{prefix}: entry must be a GeoJSON Feature")
            continue
        props = feature.get("properties")
        if not isinstance(props, dict):
            errors.append(f"{prefix}: properties must be an object")
            continue

        case_id = props.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(f"{prefix}: case_id is required")
            case_id = f"{prefix}"
        case_id = case_id.strip()
        if case_id in seen:
            errors.append(f"{case_id}: duplicate case_id")
        seen.add(case_id)

        sensitive = sorted(k for k in props if k.lower() in SENSITIVE_PROPERTY_NAMES)
        if sensitive:
            errors.append(f"{case_id}: personal/owner fields are prohibited: {', '.join(sensitive)}")

        for required in ("event_type", "source_url", "source_title", "area_source",
                         "geometry_source", "geometry_status", "geometry_crs",
                         "event_date_precision"):
            if not isinstance(props.get(required), str) or not props[required].strip():
                errors.append(f"{case_id}: {required} is required")

        parsed_event = _parse_date(props.get("event_date"), "event_date", case_id, errors)
        if "public_action_date" not in props:
            errors.append(f"{case_id}: public_action_date key is required; use null when unknown")
            parsed_action = None
        elif props.get("public_action_date") is None:
            parsed_action = None
        else:
            parsed_action = _parse_date(props.get("public_action_date"), "public_action_date", case_id, errors)

        area = props.get("area_acres")
        if isinstance(area, bool) or not isinstance(area, (int, float)) or not isfinite(float(area)) or float(area) <= 0:
            errors.append(f"{case_id}: area_acres must be a finite positive number")
            area = None
        elif float(area) <= minimum_area_acres:
            exclusions.append({"case_id": case_id, "reasons": ["area_not_over_0.25_acre"]})

        source_url = props.get("source_url")
        if isinstance(source_url, str):
            parsed_url = urlparse(source_url)
            if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
                errors.append(f"{case_id}: source_url must be an http(s) URL")

        if parsed_event and parsed_event < score_start:
            exclusions.append({"case_id": case_id, "reasons": [f"event_before_{score_start.isoformat()}"]})
        if parsed_action and parsed_event and parsed_action < parsed_event:
            errors.append(f"{case_id}: public_action_date cannot precede event_date")

        if props.get("event_date_precision") != "exact":
            exclusions.append({"case_id": case_id, "reasons": ["event_date_not_exact"]})
        if props.get("geometry_status") != "verified":
            exclusions.append({"case_id": case_id, "reasons": ["event_geometry_not_verified"]})
        if props.get("geometry_crs") != "EPSG:4326":
            errors.append(f"{case_id}: geometry_crs must be EPSG:4326 (GeoJSON longitude/latitude)")

        if parsed_action is None:
            exclusions.append({"case_id": case_id, "reasons": ["public_action_date_unknown"]})

        geometry = feature.get("geometry")
        if not isinstance(geometry, dict):
            errors.append(f"{case_id}: event geometry is required")
        else:
            try:
                geom = shape(geometry)
                if geom.is_empty:
                    errors.append(f"{case_id}: event geometry is empty")
                elif geom.geom_type not in ("Polygon", "MultiPolygon"):
                    errors.append(f"{case_id}: event geometry must be Polygon or MultiPolygon")
                elif not geom.is_valid:
                    errors.append(f"{case_id}: invalid event geometry: {explain_validity(geom)}")
                elif geom.area <= 0:
                    errors.append(f"{case_id}: event geometry has zero area")
                else:
                    minx, miny, maxx, maxy = geom.bounds
                    if minx < -180 or maxx > 180 or miny < -90 or maxy > 90:
                        errors.append(f"{case_id}: geometry coordinates are outside EPSG:4326 bounds")
            except Exception as exc:
                errors.append(f"{case_id}: could not parse event geometry: {exc}")

        reasons = []
        if isinstance(area, (int, float)) and float(area) <= minimum_area_acres:
            reasons.append("area_not_over_0.25_acre")
        if parsed_event and parsed_event < score_start:
            reasons.append(f"event_before_{score_start.isoformat()}")
        if props.get("event_date_precision") != "exact":
            reasons.append("event_date_not_exact")
        if props.get("geometry_status") != "verified":
            reasons.append("event_geometry_not_verified")
        if parsed_action is None:
            reasons.append("public_action_date_unknown")
        if not errors and not reasons:
            eligible.append(case_id)
        elif reasons and not any(item["case_id"] == case_id for item in exclusions):
            exclusions.append({"case_id": case_id, "reasons": sorted(set(reasons))})

    # Merge exclusion reasons accumulated by independent checks.
    merged: dict[str, set[str]] = {}
    for item in exclusions:
        merged.setdefault(item["case_id"], set()).update(item["reasons"])
    excluded = [
        {"case_id": case_id, "reasons": sorted(reasons)}
        for case_id, reasons in sorted(merged.items())
    ]

    return {
        "valid": not errors,
        "total_cases": len(features),
        "eligible_cases": len(eligible) if not errors else 0,
        "eligible_case_ids": eligible if not errors else [],
        "excluded_cases": excluded,
        "errors": errors,
        "minimum_area_acres_exclusive": minimum_area_acres,
        "score_start": score_start.isoformat(),
        "note": "Eligibility validation only; independent source review and blind-test controls remain mandatory.",
    }
