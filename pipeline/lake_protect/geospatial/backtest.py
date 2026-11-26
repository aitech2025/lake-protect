"""Spatial and temporal scoring for independently verified M3 cases.

Precision is deliberately withheld until every unmatched detection has a human
review disposition. An unmatched candidate is not automatically a false alarm.
"""
from __future__ import annotations

import json
from datetime import date
from math import isfinite
from pathlib import Path
from typing import Any

from shapely.geometry import shape

from .cases import validate_case_collection


def load_features(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        raise ValueError("Input must be a GeoJSON FeatureCollection")
    features = data.get("features")
    if not isinstance(features, list):
        raise ValueError("FeatureCollection.features must be an array")
    return features


def _iso_date(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) < 10:
        raise ValueError(f"{label} must be an ISO date or timestamp")
    try:
        from datetime import date
        parsed = date.fromisoformat(value[:10])
    except ValueError as exc:
        raise ValueError(f"{label} must begin with YYYY-MM-DD") from exc
    if parsed.isoformat() != value[:10]:
        raise ValueError(f"{label} must begin with YYYY-MM-DD")
    return parsed.isoformat()


def evaluate(
    cases: list[dict[str, Any]],
    detections: list[dict[str, Any]],
    *,
    minimum_area_acres: float = 0.25,
    match_iou: float = 0.10,
) -> dict[str, Any]:
    """Score only eligible cases and only detections strictly before public action.

    Primary eligibility requires the M3 case validator to pass: exact event date,
    known public-action date, verified geometry, supported area > threshold and
    complete provenance. Unknown-action cases remain visible as exclusions.
    """
    if isinstance(minimum_area_acres, bool) or not isfinite(minimum_area_acres) or minimum_area_acres < 0:
        raise ValueError("minimum_area_acres must be a finite non-negative number")
    if isinstance(match_iou, bool) or not isfinite(match_iou) or not 0 <= match_iou <= 1:
        raise ValueError("match_iou must be between 0 and 1")

    validation = validate_case_collection(
        {"type": "FeatureCollection", "features": cases},
        minimum_area_acres=minimum_area_acres,
    )
    if not validation["valid"]:
        raise ValueError("Invalid case manifest: " + "; ".join(validation["errors"]))

    eligible_ids = set(validation["eligible_case_ids"])
    eligible: list[tuple[dict[str, Any], Any]] = []
    for feature in cases:
        props = feature.get("properties", {})
        if props.get("case_id") in eligible_ids:
            eligible.append((feature, shape(feature["geometry"])))

    remaining = set(range(len(detections)))
    matches: list[dict[str, Any]] = []
    for case, case_geom in eligible:
        props = case["properties"]
        event_date = _iso_date(props["event_date"], f"{props['case_id']}.event_date")
        action_date = _iso_date(props["public_action_date"], f"{props['case_id']}.public_action_date")
        choices: list[tuple[float, int, str]] = []
        for idx in remaining:
            detection = detections[idx]
            if not isinstance(detection, dict) or not isinstance(detection.get("geometry"), dict):
                raise ValueError(f"Detection at index {idx} must contain GeoJSON geometry")
            det_props = detection.get("properties") or {}
            detected = det_props.get("detected_at") or det_props.get("first_changed_at")
            if not detected:
                continue
            detected_date = _iso_date(detected, f"detection[{idx}].detected_at")
            # A valid lead-time hit must occur on/after the observed event and
            # strictly before the first public action.
            if detected_date < event_date or detected_date >= action_date:
                continue
            geom = shape(detection["geometry"])
            if geom.is_empty or not geom.is_valid:
                raise ValueError(f"Detection at index {idx} has invalid geometry")
            union_area = case_geom.union(geom).area
            iou = case_geom.intersection(geom).area / union_area if union_area else 0.0
            if iou >= match_iou:
                choices.append((iou, idx, detected))
        if choices:
            iou, idx, detected = max(choices)
            remaining.remove(idx)
            matches.append({
                "case_id": props["case_id"],
                "detection_id": detections[idx].get("id"),
                "iou": round(iou, 4),
                "detected_at": detected,
                "public_action_date": props["public_action_date"],
                "lead_time_days": (
                    date.fromisoformat(props["public_action_date"])
                    - date.fromisoformat(detected[:10])
                ).days,
                "before_public_action": True,
            })

    true_positive = len(matches)
    false_negative = len(eligible) - true_positive
    unmatched = [
        {
            "detection_id": detections[idx].get("id"),
            "detected_at": (detections[idx].get("properties") or {}).get("detected_at")
                or (detections[idx].get("properties") or {}).get("first_changed_at"),
            "review_status": (detections[idx].get("properties") or {}).get("review_status"),
            "review_disposition": (detections[idx].get("properties") or {}).get("review_disposition"),
            "reviewed_by": (detections[idx].get("properties") or {}).get("reviewed_by"),
            "reviewed_at": (detections[idx].get("properties") or {}).get("reviewed_at"),
            "review_evidence": (detections[idx].get("properties") or {}).get("review_evidence"),
        }
        for idx in sorted(remaining)
    ]

    def has_complete_review(item: dict[str, Any]) -> bool:
        return (
            item["review_status"] == "reviewed"
            and item["review_disposition"] in {"false_positive", "valid_unscored_change"}
            and isinstance(item["reviewed_by"], str) and bool(item["reviewed_by"].strip())
            and isinstance(item["review_evidence"], str) and bool(item["review_evidence"].strip())
            and bool(_iso_date(item["reviewed_at"], "reviewed_at"))
        )

    adjudicated_false_positive = sum(
        1 for item in unmatched
        if has_complete_review(item) and item["review_disposition"] == "false_positive"
    )
    reviewed_valid_unscored = sum(
        1 for item in unmatched
        if has_complete_review(item) and item["review_disposition"] == "valid_unscored_change"
    )
    unreviewed = len(unmatched) - adjudicated_false_positive - reviewed_valid_unscored
    precision = (
        true_positive / (true_positive + adjudicated_false_positive)
        if unreviewed == 0 and true_positive + adjudicated_false_positive > 0
        else (0.0 if unreviewed == 0 else None)
    )
    recall = true_positive / len(eligible) if eligible else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall > 0
        else (0.0 if precision == 0 and recall == 0 else None)
    )

    return {
        "eligible_cases": len(eligible),
        "eligible_case_ids": [feature["properties"]["case_id"] for feature, _ in eligible],
        "excluded_cases": validation["excluded_cases"],
        "detections": len(detections),
        "true_positive": true_positive,
        "false_negative": false_negative,
        "false_positive": adjudicated_false_positive,
        "unmatched_detections": len(unmatched),
        "reviewed_valid_unscored_detections": reviewed_valid_unscored,
        "unreviewed_detections": unreviewed,
        "unmatched_detection_details": unmatched,
        "precision": round(precision, 4) if precision is not None else None,
        "recall": round(recall, 4) if recall is not None else None,
        "f1": round(f1, 4) if f1 is not None else None,
        "precision_status": "complete" if unreviewed == 0 else "pending_manual_review",
        "minimum_area_acres_exclusive": minimum_area_acres,
        "match_iou": match_iou,
        "matches": matches,
        "warning": (
            "Screening metrics only. Precision remains unavailable until every unmatched "
            "candidate has a documented human review disposition, reviewer and evidence. Verified changes outside the scored event set are reported separately, not as false positives. Verify blind-test "
            "independence and imagery provenance before reporting."
        ),
    }


def evaluate_files(
    cases_path: str | Path,
    detections_path: str | Path,
    output_path: str | Path,
    *,
    minimum_area_acres: float = 0.25,
    match_iou: float = 0.10,
) -> dict[str, Any]:
    result = evaluate(
        load_features(cases_path),
        load_features(detections_path),
        minimum_area_acres=minimum_area_acres,
        match_iou=match_iou,
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
