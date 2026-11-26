from app.routers.sources import _boundary_provenance


def test_derived_boundary_is_never_authority_confirmed():
    result = _boundary_provenance({
        "status": "derived",
        "source_name": "Irrigation tank outline",
        "source_url": None,
        "boundary_source_date": None,
        "notification_ref": None,
        "certified_by": None,
        "source_snapshot_id": 11,
        "connector": "irrigation",
        "agency": "Irrigation and CAD Department",
        "transport": "file_drop",
        "is_sample": False,
        "sha256": "a" * 64,
    })
    assert result["source_class"] == "derived_unverified"
    assert result["authority_confirmed"] is False


def test_demo_source_is_never_mislabelled_as_official():
    result = _boundary_provenance({
        "status": "final_notification",
        "source_name": "HMDA Lake Protection Committee",
        "source_url": "https://example.org/notice",
        "boundary_source_date": None,
        "notification_ref": "G.O. 12",
        "certified_by": "Officer",
        "source_snapshot_id": 12,
        "connector": "hmda_lpc",
        "agency": "HMDA",
        "transport": "sample",
        "is_sample": True,
        "sha256": "b" * 64,
    })
    assert result["source_class"] == "demo_sample"
    assert result["authority_confirmed"] is False


def test_hmda_notification_reference_can_be_classified_as_official_record():
    result = _boundary_provenance({
        "status": "final_notification",
        "source_name": "HMDA LPC notification",
        "source_url": "https://example.org/notice",
        "boundary_source_date": "2025-01-01",
        "notification_ref": "G.O. 12",
        "certified_by": "Department",
        "source_snapshot_id": 13,
        "connector": "hmda_lpc",
        "agency": "HMDA",
        "transport": "file_drop",
        "is_sample": False,
        "sha256": "c" * 64,
    })
    assert result["source_class"] == "official_record"
    assert result["authority_confirmed"] is True
    assert result["provenance_complete"] is True


def test_unclassified_source_does_not_gain_authority_from_source_name():
    result = _boundary_provenance({
        "status": "physically_marked",
        "source_name": "Local survey map",
        "source_url": None,
        "boundary_source_date": None,
        "notification_ref": None,
        "certified_by": None,
        "source_snapshot_id": None,
        "connector": None,
        "agency": None,
        "transport": None,
        "is_sample": False,
        "sha256": None,
    })
    assert result["source_class"] == "unclassified"
    assert result["authority_confirmed"] is False


def test_osm_source_is_labelled_as_derived():
    result = _boundary_provenance({
        "status": "derived",
        "source_name": "OpenStreetMap outline",
        "source_url": "https://openstreetmap.org",
        "boundary_source_date": None,
        "notification_ref": None,
        "certified_by": None,
        "source_snapshot_id": None,
        "connector": None,
        "agency": None,
        "transport": None,
        "is_sample": False,
        "sha256": None,
    })
    assert result["source_class"] == "derived_unverified"
    assert result["authority_confirmed"] is False
