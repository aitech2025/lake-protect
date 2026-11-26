from datetime import date

from lake_protect.geospatial.cases import validate_case_collection

POLYGON = {
    "type": "Polygon",
    "coordinates": [[[78.0, 17.0], [78.01, 17.0], [78.01, 17.01], [78.0, 17.01], [78.0, 17.0]]],
}


def feature(case_id="case-1", **overrides):
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
        "geometry_source": "hand-traced from dated public map",
        "geometry_status": "verified",
        "geometry_crs": "EPSG:4326",
    }
    properties.update(overrides)
    return {"type": "Feature", "geometry": POLYGON, "properties": properties}


def collection(*features):
    return {"type": "FeatureCollection", "features": list(features)}


def test_verified_case_is_eligible():
    result = validate_case_collection(collection(feature()))
    assert result["valid"] is True
    assert result["eligible_case_ids"] == ["case-1"]
    assert result["excluded_cases"] == []


def test_unknown_public_action_date_is_explicitly_excluded():
    result = validate_case_collection(collection(feature(public_action_date=None)))
    assert result["valid"] is True
    assert result["eligible_cases"] == 0
    assert "public_action_date_unknown" in result["excluded_cases"][0]["reasons"]


def test_event_below_quarter_acre_is_excluded():
    result = validate_case_collection(collection(feature(area_acres=0.25)))
    assert result["valid"] is True
    assert result["eligible_cases"] == 0
    assert "area_not_over_0.25_acre" in result["excluded_cases"][0]["reasons"]


def test_approximate_geometry_is_not_primary_score_eligible():
    result = validate_case_collection(collection(feature(geometry_status="approximate")))
    assert result["valid"] is True
    assert result["eligible_cases"] == 0
    assert "event_geometry_not_verified" in result["excluded_cases"][0]["reasons"]


def test_broad_date_window_is_not_primary_score_eligible():
    result = validate_case_collection(collection(feature(event_date_precision="range")))
    assert result["valid"] is True
    assert result["eligible_cases"] == 0
    assert "event_date_not_exact" in result["excluded_cases"][0]["reasons"]


def test_pre_2018_event_is_excluded():
    result = validate_case_collection(collection(feature(event_date="2017-12-31")))
    assert result["valid"] is True
    assert result["eligible_cases"] == 0
    assert any("event_before_2018-01-01" in item["reasons"] for item in result["excluded_cases"])


def test_missing_action_date_key_is_a_manifest_error():
    item = feature()
    del item["properties"]["public_action_date"]
    result = validate_case_collection(collection(item))
    assert result["valid"] is False
    assert any("public_action_date key is required" in error for error in result["errors"])


def test_duplicate_case_ids_are_rejected():
    result = validate_case_collection(collection(feature(), feature()))
    assert result["valid"] is False
    assert any("duplicate case_id" in error for error in result["errors"])


def test_personal_fields_are_rejected():
    result = validate_case_collection(collection(feature(owner_name="not allowed")))
    assert result["valid"] is False
    assert any("personal/owner fields are prohibited" in error for error in result["errors"])


def test_invalid_geometry_is_rejected():
    bad = feature()
    bad["geometry"] = {"type": "Polygon", "coordinates": []}
    result = validate_case_collection(collection(bad))
    assert result["valid"] is False
    assert any("event geometry" in error for error in result["errors"])
