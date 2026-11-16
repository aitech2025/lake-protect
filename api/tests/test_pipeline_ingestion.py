from uuid import uuid4

from app.config import settings


def _pipeline_headers():
    return {"X-Pipeline-Token": settings.pipeline_token}


def test_pipeline_ingestion_is_idempotent_and_processing_run_has_state_machine(client):
    batch_response = client.post(
        "/api/v1/ingestion/batches",
        headers=_pipeline_headers(),
        json={
            "source_system": "test-source",
            "source_authority": "CERTIFIED",
            "schema_version": "1",
            "mapping_version": "1",
            "source_uri": "file://test/batch.csv",
            "checksum_sha256": "a" * 64,
        },
    )
    assert batch_response.status_code == 201, batch_response.text
    batch_id = batch_response.json()["id"]

    record_payload = {
        "source_record_id": "survey-plot-0001",
        "authority_class": "CERTIFIED",
        "source_uri": "file://test/plot-0001.json",
        "source_version": "2026-11",
        "source_effective_at": "2026-11-01T00:00:00Z",
        "checksum_sha256": "b" * 64,
        "payload": {"district_code": "TEST", "survey_number": "1"},
    }
    first = client.post(f"/api/v1/ingestion/batches/{batch_id}/records",
                        headers=_pipeline_headers(), json=record_payload)
    assert first.status_code == 201, first.text
    assert first.json()["duplicate"] is False
    duplicate = client.post(f"/api/v1/ingestion/batches/{batch_id}/records",
                            headers=_pipeline_headers(), json=record_payload)
    assert duplicate.status_code == 201, duplicate.text
    assert duplicate.json()["duplicate"] is True

    changed = {**record_payload, "checksum_sha256": "c" * 64}
    conflict = client.post(f"/api/v1/ingestion/batches/{batch_id}/records",
                           headers=_pipeline_headers(), json=changed)
    assert conflict.status_code == 409

    record_id = first.json()["record"]["id"]
    validated = client.patch(
        f"/api/v1/ingestion/batches/{batch_id}/records/{record_id}",
        headers=_pipeline_headers(),
        json={"validation_status": "VALID"},
    )
    assert validated.status_code == 200, validated.text
    assert validated.json()["batch_status"] == "ACCEPTED"
    repeated_validation = client.patch(
        f"/api/v1/ingestion/batches/{batch_id}/records/{record_id}",
        headers=_pipeline_headers(),
        json={"validation_status": "VALID"},
    )
    assert repeated_validation.status_code == 200
    assert repeated_validation.json()["duplicate"] is True

    scene_payload = {
        "provider": "test-provider",
        "collection_id": "sentinel-2-l2a",
        "item_id": "scene-0001",
        "platform": "Sentinel-2",
        "instrument": "MSI",
        "acquired_at": "2026-11-01T10:00:00Z",
        "footprint": {
            "type": "Polygon",
            "coordinates": [[[78.0, 17.0], [78.1, 17.0], [78.1, 17.1], [78.0, 17.1], [78.0, 17.0]]],
        },
        "cloud_cover": 4.5,
        "gsd_m": 10,
        "license": "Copernicus",
        "stac_item": {"id": "scene-0001", "type": "Feature", "assets": {}},
        "object_uri": "scenes/scene-0001.json",
        "checksum_sha256": "d" * 64,
    }
    scene = client.post("/api/v1/ingestion/scenes", headers=_pipeline_headers(), json=scene_payload)
    assert scene.status_code == 201, scene.text
    assert scene.json()["duplicate"] is False
    scene_duplicate = client.post("/api/v1/ingestion/scenes",
                                  headers=_pipeline_headers(), json=scene_payload)
    assert scene_duplicate.status_code == 201
    assert scene_duplicate.json()["duplicate"] is True

    run_id = str(uuid4())
    run_payload = {
        "id": run_id,
        "pipeline_name": "sentinel-change-detection",
        "pipeline_version": "0.1.0",
        "config_hash": "e" * 64,
        "input_manifest": {"scene_ids": ["scene-0001"], "asset_ids": ["ASSET-1"]},
        "geographic_scope": {
            "type": "Polygon",
            "coordinates": [[[78.0, 17.0], [78.1, 17.0], [78.1, 17.1], [78.0, 17.1], [78.0, 17.0]]],
        },
    }
    created = client.post("/api/v1/ingestion/processing-runs",
                          headers=_pipeline_headers(), json=run_payload)
    assert created.status_code == 201, created.text
    assert created.json()["run"]["status"] == "QUEUED"
    repeated = client.post("/api/v1/ingestion/processing-runs",
                           headers=_pipeline_headers(), json=run_payload)
    assert repeated.status_code == 201
    assert repeated.json()["duplicate"] is True

    running = client.patch(f"/api/v1/ingestion/processing-runs/{run_id}",
                           headers=_pipeline_headers(),
                           json={"status": "RUNNING", "output_manifest": {}})
    assert running.status_code == 200, running.text
    succeeded = client.patch(f"/api/v1/ingestion/processing-runs/{run_id}",
                             headers=_pipeline_headers(),
                             json={"status": "SUCCEEDED", "output_manifest": {"candidate_count": 0}})
    assert succeeded.status_code == 200, succeeded.text
    invalid = client.patch(f"/api/v1/ingestion/processing-runs/{run_id}",
                           headers=_pipeline_headers(),
                           json={"status": "RUNNING", "output_manifest": {}})
    assert invalid.status_code == 409
