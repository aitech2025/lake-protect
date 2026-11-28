from types import SimpleNamespace

from app.readiness import build_readiness
from tests.factories import auth, make_user


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class FakeDb:
    def execute(self, statement):
        sql = str(statement)
        if "alembic_version" in sql:
            return FakeResult("0009")
        return FakeResult(1)


def test_readiness_reports_configuration_without_exposing_secrets(tmp_path):
    config = SimpleNamespace(
        storage_dir=tmp_path,
        jwt_secret="x" * 48,
        pipeline_token="pipeline-secret-do-not-return",
        public_url="https://geoguard.example.gov",
        email_transport="smtp",
        smtp_host="smtp.example.gov",
        email_from="GeoGuard <noreply@example.gov>",
    )
    result = build_readiness(FakeDb(), config)
    statuses = {item["key"]: item["status"] for item in result["checks"]}

    assert result["overall"] == "prototype_ready"
    assert result["production_ready"] is False
    assert result["production_certification"] == "not_performed"
    assert statuses["database"] == "configured"
    assert statuses["object_storage"] == "configured"
    assert statuses["jwt_signing_secret"] == "configured"
    assert statuses["pipeline_ingestion"] == "configured"
    assert statuses["public_url"] == "configured"
    assert statuses["email_delivery"] == "configured"
    assert statuses["department_data_isolation"] == "not_verified"
    assert "pipeline-secret-do-not-return" not in str(result)
    assert "smtp.example.gov" not in str(result)


def test_readiness_does_not_claim_production_ready_for_weak_configuration(tmp_path):
    config = SimpleNamespace(
        storage_dir=tmp_path,
        jwt_secret="weak",
        pipeline_token=None,
        public_url="http://localhost:8180",
        email_transport="file",
        smtp_host=None,
        email_from="GeoGuard <no-reply@geoguard.invalid>",
    )
    result = build_readiness(FakeDb(), config)
    statuses = {item["key"]: item["status"] for item in result["checks"]}

    assert result["production_ready"] is False
    assert statuses["jwt_signing_secret"] == "weak_or_missing"
    assert statuses["pipeline_ingestion"] == "not_configured"
    assert statuses["public_url"] == "not_production_url"
    assert statuses["email_delivery"] == "local_or_disabled"
    assert "sso_mfa" in result["production_blockers"]


def test_readiness_endpoint_is_admin_only_and_never_returns_secret_values(client, db):
    viewer = make_user(db, "senior_official")
    admin = make_user(db, "admin")

    denied = client.get("/readiness", headers=auth(viewer))
    assert denied.status_code == 403

    response = client.get("/readiness", headers=auth(admin))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["production_ready"] is False
    assert body["production_certification"] == "not_performed"
    assert "checks" in body and "production_blockers" in body
    assert "jwt_secret" not in str(body).lower()
    assert "database_url" not in str(body).lower()
