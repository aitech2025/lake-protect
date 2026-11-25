import hashlib
import hmac
import json

from sqlalchemy import text

from app.config import settings


def _signed(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _payload(message_id="wamid.test-001"):
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "field": "messages",
                "value": {
                    "contacts": [{"wa_id": "919999999999"}],
                    "messages": [{
                        "id": message_id,
                        "from": "919999999999",
                        "timestamp": "1795640000",
                        "type": "location",
                        "location": {"latitude": 17.3, "longitude": 78.4, "name": "Lake edge"},
                    }],
                },
            }],
        }],
    }


def test_meta_webhook_verification_uses_meta_query_parameter_names(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_verify_token", "verify-me")
    response = client.get("/webhooks/whatsapp", params={
        "hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "challenge-123"
    })
    assert response.status_code == 200
    assert response.text == "challenge-123"


def test_signed_whatsapp_location_is_persisted_once_as_unverified_signal(client, db, monkeypatch):
    secret = "unit-test-app-secret"
    monkeypatch.setattr(settings, "whatsapp_app_secret", secret)
    raw = json.dumps(_payload(), separators=(",", ":")).encode()
    headers = {"X-Hub-Signature-256": _signed(raw, secret), "Content-Type": "application/json"}

    first = client.post("/webhooks/whatsapp", content=raw, headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["stored"] == 1
    assert first.json()["duplicates"] == 0

    duplicate = client.post("/webhooks/whatsapp", content=raw, headers=headers)
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json()["stored"] == 0
    assert duplicate.json()["duplicates"] == 1

    row = db.execute(text("""
        SELECT kind, ref FROM signals
        WHERE kind='citizen_whatsapp' AND ref LIKE '%wamid.test-001%'
    """)).mappings().one()
    assert row["kind"] == "citizen_whatsapp"
    assert '"trust": "UNVERIFIED"' in row["ref"]
    assert "919999999999" not in row["ref"]


def test_whatsapp_webhook_rejects_invalid_signature(client, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", "unit-test-app-secret")
    raw = json.dumps(_payload("wamid.bad-signature")).encode()
    response = client.post("/webhooks/whatsapp", content=raw,
                           headers={"X-Hub-Signature-256": "sha256=invalid"})
    assert response.status_code == 401
