"""The intelligence list endpoints must answer when their optional filter is left out.

Before the explicit casts, `:param IS NULL` with no value gave psycopg an untyped parameter and
both endpoints returned 500 on their default call.
"""
import uuid

from tests.factories import auth, make_user


def test_evaluations_list_without_filter(client, db):
    admin = make_user(db, "admin")
    r = client.get("/api/v1/intelligence/evaluations", headers=auth(admin))
    assert r.status_code == 200, r.text
    assert r.json() == {"items": []}


def test_evaluations_list_with_model_filter(client, db):
    admin = make_user(db, "admin")
    r = client.get(f"/api/v1/intelligence/evaluations?model_version_id={uuid.uuid4()}", headers=auth(admin))
    assert r.status_code == 200, r.text
    assert r.json() == {"items": []}


def test_processing_runs_list_with_and_without_filter(client, db):
    admin = make_user(db, "admin")
    for path in ("/api/v1/intelligence/processing-runs", "/api/v1/intelligence/processing-runs?status=SUCCEEDED"):
        r = client.get(path, headers=auth(admin))
        assert r.status_code == 200, (path, r.text)
        assert r.json() == {"items": []}


def test_intelligence_lists_are_admin_only(client, db):
    viewer = make_user(db, "senior_official")
    for path in ("/api/v1/intelligence/evaluations", "/api/v1/intelligence/processing-runs"):
        assert client.get(path, headers=auth(viewer)).status_code == 403
