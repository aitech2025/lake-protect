from tests.factories import auth, make_user


def test_citizen_operations_is_admin_only_and_exposes_privacy_safe_queue_metadata(client, db):
    viewer = make_user(db, "senior_official")
    admin = make_user(db, "admin")

    denied = client.get("/citizen/operations", headers=auth(viewer))
    assert denied.status_code == 403

    response = client.get("/citizen/operations", headers=auth(admin))
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"satellite_reviews", "outbound_messages", "outbound_channels", "citizen_updates", "whatsapp_inbound"}
    assert body["satellite_reviews"]["pending"] == 0
    assert body["outbound_messages"]["retry_pending"] == 0
    assert body["outbound_messages"]["retry_exhausted"] == 0
    assert body["whatsapp_inbound"]["mode"] in {"configured", "disabled"}
    assert all("phone" not in str(item).lower() and "reporter" not in str(item).lower()
               for item in body["satellite_reviews"]["items"])
