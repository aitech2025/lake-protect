from copy import deepcopy

from lake_protect.geospatial.backtest import evaluate

POLYGON = {
    "type": "Polygon",
    "coordinates": [[[78.0, 17.0], [78.01, 17.0], [78.01, 17.01], [78.0, 17.01], [78.0, 17.0]]],
}


def case(case_id="case-1", **overrides):
    properties = {
        "case_id": case_id,
        "event_type": "soil_fill",
        "event_date": "2024-06-01",
        "event_date_precision": "exact",
        "public_action_date": "2024-09-01",
        "area_acres": 1.0,
        "area_source": "independent published measurement",
        "source_url": "https://example.org/report",
        "source_title": "Published report",
        "geometry_source": "dated imagery manually traced",
        "geometry_status": "verified",
        "geometry_crs": "EPSG:4326",
    }
    properties.update(overrides)
    return {"type": "Feature", "id": case_id, "geometry": deepcopy(POLYGON), "properties": properties}


def detection(detection_id="det-1", detected_at="2024-07-01", **overrides):
    properties = {"detected_at": detected_at}
    properties.update(overrides)
    return {
        "type": "Feature",
        "id": detection_id,
        "geometry": deepcopy(POLYGON),
        "properties": properties,
    }


def test_verified_detection_before_public_action_is_a_true_positive():
    result = evaluate([case()], [detection()])
    assert result["true_positive"] == 1
    assert result["false_negative"] == 0
    assert result["matches"][0]["lead_time_days"] == 62
    assert result["matches"][0]["before_public_action"] is True


def test_detection_on_or_after_public_action_is_not_a_lead_time_hit():
    result = evaluate([case()], [detection(detected_at="2024-09-01")])
    assert result["true_positive"] == 0
    assert result["false_negative"] == 1


def test_detection_before_event_date_is_not_a_match():
    result = evaluate([case()], [detection(detected_at="2024-05-31")])
    assert result["true_positive"] == 0
    assert result["false_negative"] == 1


def test_unknown_public_action_date_is_excluded_not_claimed_as_pre_action():
    result = evaluate([case(public_action_date=None)], [detection()])
    assert result["eligible_cases"] == 0
    assert result["true_positive"] == 0
    assert result["excluded_cases"][0]["reasons"] == ["public_action_date_unknown"]
    assert result["precision"] is None


def test_exactly_quarter_acre_is_excluded_because_prd_says_over_quarter_acre():
    result = evaluate([case(area_acres=0.25)], [detection()])
    assert result["eligible_cases"] == 0
    assert result["excluded_cases"][0]["reasons"] == ["area_not_over_0.25_acre"]


def test_unmatched_detection_is_not_automatically_called_false_positive():
    result = evaluate([case()], [detection("unmatched", detected_at="2024-09-02", review_disposition=None)])
    assert result["true_positive"] == 0
    assert result["false_positive"] == 0
    assert result["unreviewed_detections"] == 1
    assert result["precision"] is None
    assert result["precision_status"] == "pending_manual_review"


def test_human_adjudicated_false_positive_is_counted():
    result = evaluate([case()], [
        detection(
            "false-1",
            detected_at="2024-09-02",
            review_status="reviewed",
            review_disposition="false_positive",
            reviewed_by="independent-reviewer",
            reviewed_at="2024-09-03",
            review_evidence="manual comparison against dated high-resolution history",
        )
    ])
    assert result["false_positive"] == 1
    assert result["unreviewed_detections"] == 0
    assert result["precision"] == 0.0
    assert result["precision_status"] == "complete"


def test_non_exact_case_date_is_excluded_from_primary_scoring():
    result = evaluate([case(event_date_precision="month")], [])
    assert result["eligible_cases"] == 0
    assert "event_date_not_exact" in result["excluded_cases"][0]["reasons"]


def test_pre_2018_case_is_excluded_from_scoring():
    result = evaluate([case(event_date="2017-12-31")], [detection()])
    assert result["eligible_cases"] == 0
    assert "event_before_2018-01-01" in result["excluded_cases"][0]["reasons"]


def test_incomplete_false_positive_review_does_not_count_as_adjudicated():
    result = evaluate([case()], [
        detection("false-1", detected_at="2024-09-02", review_disposition="false_positive")
    ])
    assert result["false_positive"] == 0
    assert result["unreviewed_detections"] == 1
    assert result["precision"] is None


def test_precision_is_not_estimable_when_no_detections_exist():
    result = evaluate([case()], [])
    assert result["precision"] is None
    assert result["precision_status"] == "not_estimable"

def test_retrospective_first_changed_at_cannot_substitute_for_detected_at():
    item = detection()
    item["properties"] = {"first_changed_at": "2024-06-15"}
    try:
        evaluate([case()], [item])
    except ValueError as exc:
        assert "detected_at" in str(exc)
        assert "retrospective" in str(exc)
    else:
        raise AssertionError("A retrospective change date must not be accepted as a detection date")


def test_duplicate_detection_ids_are_rejected():
    try:
        evaluate([case()], [detection("same"), detection("same", detected_at="2024-07-10")])
    except ValueError as exc:
        assert "Duplicate detection id" in str(exc)
    else:
        raise AssertionError("Duplicate replay detection IDs must be rejected")
