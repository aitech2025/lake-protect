import json
from sqlalchemy import text

from app.config import settings


def _headers():
    return {"X-Pipeline-Token": settings.pipeline_token}


def test_authorised_social_post_is_ingested_once_as_unverified_signal(client, db):
    payload = {
        "items": [{
            "provider": "x",
            "post_id": "post-geo-001",
            "created_at": "2026-11-25T10:00:00Z",
            "text": "soil dumping near lake buffer zone",
            "author_id": "raw-social-account-id",
            "url": "https://social.example/post-geo-001",
            "latitude": 17.3,
            "longitude": 78.4,
        }]
    }
    first = client.post("/api/v1/ingestion/social-signals", headers=_headers(), json=payload)
    assert first.status_code == 202, first.text
    assert first.json()["stored"] == 1

    duplicate = client.post("/api/v1/ingestion/social-signals", headers=_headers(), json=payload)
    assert duplicate.status_code == 202, duplicate.text
    assert duplicate.json()["stored"] == 0
    assert duplicate.json()["duplicates"] == 1

    row = db.execute(text("""
        SELECT kind, ref, ST_X(geom) AS lon, ST_Y(geom) AS lat
        FROM signals WHERE kind='social_x' AND ref LIKE '%post-geo-001%'
    """)).mappings().one()
    assert row["kind"] == "social_x"
    assert row["lon"] == 78.4 and row["lat"] == 17.3
    assert '"trust": "UNVERIFIED"' in row["ref"]
    assert "raw-social-account-id" not in row["ref"]


def test_social_ingestion_rejects_partial_coordinates(client):
    payload = {"items": [{
        "provider": "youtube", "post_id": "video-1",
        "created_at": "2026-11-25T10:00:00Z", "text": "lake pollution",
        "latitude": 17.3,
    }]}
    response = client.post("/api/v1/ingestion/social-signals", headers=_headers(), json=payload)
    assert response.status_code == 422
