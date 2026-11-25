import pytest
from lake_protect.integrations.social import normalize_post


def test_normalize_social_post_hashes_author_and_classifies_content():
    result=normalize_post("x",{"id":"post-1","created_at":"2026-11-25T10:00:00Z",
        "text":"soil dumping near lake buffer zone","author_id":"raw-user-id",
        "latitude":17.3,"longitude":78.4,"url":"https://x.example/post-1"})
    assert "land_filling" in result["category_hints"]
    assert "lake_encroachment" in result["category_hints"]
    assert result["author_ref"] != "raw-user-id"
    assert result["trust"]=="UNVERIFIED"


def test_normalize_social_post_rejects_invalid_or_inferred_coordinates():
    with pytest.raises(ValueError):
        normalize_post("instagram",{"id":"p","created_at":"2026-11-25T10:00:00Z",
            "text":"test","latitude":17.3})
    with pytest.raises(ValueError):
        normalize_post("facebook",{"id":"p","created_at":"2026-11-25T10:00:00Z",
            "text":"test","latitude":100,"longitude":78})
