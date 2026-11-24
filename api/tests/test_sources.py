"""M11: the asset creation engine and its template government connectors (docs/asset-engine.md).

Everything here runs on the fictional sample files in app/sources/samples, which sit in open sea
(DECISIONS.md D-015), or on files written by the test itself. No government system is called.
"""
import datetime as dt
import json

import httpx
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.models import Asset, AssetSourceLink, Boundary, ImportRun, LandParcel, SourceSnapshot
from app.services import boundaries as bsvc
from app.sources import engine, privacy
from app.sources.base import AgreementRequired, SourceError
from app.sources.connectors import CONNECTORS
from app.sources.transports import SAMPLES_DIR, OfficialApiTransport
from tests.factories import Team, auth, make_user, square


def apply(db, name: str) -> dict:
    return engine.run(db, name, transport="sample", dry_run=False)


def asset(db, key: str) -> Asset:
    found = db.scalar(select(Asset).where(Asset.asset_key == key))
    assert found is not None, key
    return found


def items(report: dict, action: str) -> dict[str, dict]:
    return {i["ref"]: i for i in report["items"] if i["action"] == action}


def count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


# Privacy ------------------------------------------------------------------------------------


def test_personal_columns_are_removed_and_bhudhaar_is_kept():
    raw = b"survey_no,bhudhaar,pattadar_name,Father Name,mobile,land_classification\n1,S1,PERSON-X,PERSON-Y,99,Patta\n"
    out, dropped = privacy.sanitise(raw, "csv")
    assert dropped == ["Father Name", "mobile", "pattadar_name"]
    assert out.decode().splitlines() == ["survey_no,bhudhaar,land_classification", "1,S1,Patta"]

    doc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": None, "properties": {"lake_name": "Lake", "owner_name": "PERSON-Z", "village": "V"}}]}
    out, dropped = privacy.sanitise(json.dumps(doc).encode(), "geojson")
    assert dropped == ["owner_name"]
    assert json.loads(out)["features"][0]["properties"] == {"lake_name": "Lake", "village": "V"}


# Runs on the samples -------------------------------------------------------------------------


def test_dry_run_reports_the_plan_and_writes_nothing(db, isolated_storage):
    before = (count(db, Asset), count(db, SourceSnapshot), count(db, ImportRun), count(db, Boundary))
    report = engine.run(db, "hmda_lpc", transport="sample", dry_run=True)
    assert report["dry_run"] is True and report["run_id"] is None
    assert report["counts"] == {"assets_created": 3, "documents_tagged": 3, "links_added": 3, "rejected": 1, "waiting": 1}
    assert all("asset_id" not in i for i in report["items"])
    assert (count(db, Asset), count(db, SourceSnapshot), count(db, ImportRun), count(db, Boundary)) == before
    assert not (isolated_storage.root / "sources").exists()


def test_lake_register_creates_assets_with_cohort_and_provenance(db, isolated_storage):
    report = apply(db, "hmda_lpc")
    assert report["counts"] == {"assets_created": 3, "documents_tagged": 3, "links_added": 3, "rejected": 1, "waiting": 1}
    assert "reference" in items(report, "rejected")["hmda_lpc:S-004"]["reason"]
    assert "outline" in items(report, "waiting")["hmda_lpc:S-005"]["reason"]

    a, b, c = (asset(db, f"sample-lpc-s-00{n}") for n in (1, 2, 3))
    assert (a.cohort, b.cohort, c.cohort) == ("B_FINAL", "C_PRELIM", "D_UNNOTIFIED")
    assert all(x.is_demo for x in (a, b, c))
    assert a.baseline_date == dt.date(2024, 7, 19)
    assert a.name == "Sample Cheruvu A" and a.name_te and a.custodian_agency == "HMDA"

    rows = db.scalars(select(Boundary).where(Boundary.asset_id == a.id).order_by(Boundary.id)).all()
    assert [r.kind for r in rows] == ["ftl", "buffer", "watch_ring"]
    ftl_snap = db.scalar(select(SourceSnapshot).where(SourceSnapshot.dataset == "ftl"))
    assert all(r.source_snapshot_id == ftl_snap.id and float(r.positional_accuracy_m) == 3.5 for r in rows)
    primary = rows[0]
    assert primary.status == "final_notification" and primary.notification_ref == "SAMPLE/LPC/FINAL/001"
    assert primary.valid_from == dt.date(2025, 3, 14)

    # The file is kept as received, under its hash.
    assert ftl_snap.is_sample and ftl_snap.transport == "sample"
    stored = isolated_storage.get_object(ftl_snap.storage_key)
    assert stored == (SAMPLES_DIR / "hmda_lpc" / "ftl.geojson").read_bytes()

    run = db.get(ImportRun, report["run_id"])
    assert run.counts == report["counts"] and len(run.snapshot_ids) == 2
    links = db.scalars(select(AssetSourceLink).where(AssetSourceLink.asset_id == a.id)).all()
    assert [(link.connector, link.external_id, link.matched_by) for link in links] == [("hmda_lpc", "sample:S-001", "created")]


def test_running_the_same_files_again_changes_nothing(db, isolated_storage):
    apply(db, "hmda_lpc")
    snaps, bounds = count(db, SourceSnapshot), count(db, Boundary)
    report = apply(db, "hmda_lpc")
    assert report["counts"] == {"rejected": 1, "unchanged": 3, "waiting": 1}
    assert all(s["reused"] for s in report["snapshots"])
    assert (count(db, SourceSnapshot), count(db, Boundary)) == (snaps, bounds)


def test_irrigation_never_lowers_a_notified_boundary_and_flags_disagreement(db, isolated_storage):
    apply(db, "hmda_lpc")
    report = apply(db, "irrigation")
    weaker = items(report, "skipped_weaker")["irrigation:MI-S-0101"]
    assert weaker["asset_key"] == "sample-lpc-s-001" and weaker["matched_by"] == "crosswalk"
    assert "kept the current final_notification" in weaker["reason"]
    assert 0.5 < weaker["metrics"]["iou"] < 1

    created = items(report, "created")["irrigation:MI-S-0102"]
    assert created["asset_key"] == "sample-mi-mi-s-0102" and created["cohort_after"] == "D_UNNOTIFIED"

    conflict = items(report, "conflict")["irrigation:MI-S-0103"]
    assert conflict["asset_key"] == "sample-lpc-s-003" and conflict["matched_by"] == "spatial"
    assert "another source" in conflict["reason"]
    assert "MI-S-0104" in str(items(report, "waiting"))
    assert "above the 25 m limit" in items(report, "rejected")["irrigation:MI-S-0105"]["reason"]

    a = asset(db, "sample-lpc-s-001")
    assert a.cohort == "B_FINAL"
    assert db.scalar(select(func.max(Boundary.version)).where(Boundary.asset_id == a.id)) == 1
    connectors = set(db.scalars(select(AssetSourceLink.connector).where(AssetSourceLink.asset_id == a.id)))
    assert connectors == {"hmda_lpc", "irrigation"}


def test_hydraa_upgrades_a_preliminary_lake_and_adds_recovered_land(db, client, isolated_storage):
    apply(db, "hmda_lpc")
    report = apply(db, "hydraa")
    upgrade = items(report, "new_version")["hydraa:HR-S-002"]
    assert (upgrade["status_before"], upgrade["status"]) == ("preliminary_notification", "final_notification")
    assert (upgrade["cohort_before"], upgrade["cohort_after"]) == ("C_PRELIM", "B_FINAL")
    assert "order reference" in items(report, "rejected")["hydraa:HYD-REC-S-02"]["reason"]

    b = asset(db, "sample-lpc-s-002")
    versions = {v["version"]: v for v in bsvc.all_versions(db, b.id) if v["kind"] == "ftl"}
    assert versions[1]["status"] == "preliminary_notification" and versions[1]["superseded_by_id"] == versions[2]["id"]
    assert versions[2]["valid_from"] == dt.date(2026, 2, 10)

    parcel = asset(db, "sample-hydraa-hyd-rec-s-01")
    assert (parcel.type, parcel.cohort) == ("recovered_parcel", "A_RECOVERED")
    assert parcel.survey_numbers == ["41", "42"]

    analyst = make_user(db, "viewer")
    listed = {f["properties"]["asset_key"]: f["properties"] for f in client.get("/assets?dataset=demo", headers=auth(analyst)).json()["features"]}
    assert listed["sample-hydraa-hyd-rec-s-01"]["mode"] == "ACTION"
    assert listed["sample-lpc-s-002"]["boundary_status"] == "final_notification"
    real = client.get("/assets?dataset=real", headers=auth(analyst)).json()["features"]
    assert not any(f["properties"]["asset_key"].startswith("sample-") for f in real)


def test_land_records_load_without_owner_names_and_fill_survey_numbers(db, client, isolated_storage):
    apply(db, "hmda_lpc")
    report = apply(db, "bhu_bharati")
    parcels_snap = db.scalar(select(SourceSnapshot).where(SourceSnapshot.dataset == "ror"))
    assert parcels_snap.stripped_fields == ["pattadar_mobile", "pattadar_name"]
    assert parcels_snap.received_sha256 != parcels_snap.sha256
    assert b"FICTIONAL-NAME" not in isolated_storage.get_object(parcels_snap.storage_key)
    assert "pattadar_name" in str(items(report, "privacy"))

    assert report["counts"]["parcels_loaded"] == 180
    cats = dict(db.execute(select(LandParcel.land_category, func.count()).group_by(LandParcel.land_category)).all())
    assert {"tank", "shikam", "patta", "government", "assigned", "inam", "endowment", "unknown"} <= set(cats)
    assert "999" in str(items(report, "rejected"))
    warnings = [i["reason"] for i in report["items"] if i["action"] == "warning"]
    assert sum("recorded extent" in w for w in warnings) == 2
    assert sum("not recognised" in w for w in warnings) == 1

    columns = set(db.scalars(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'land_parcels'")))
    assert not any(word in c for c in columns for word in ("owner", "pattadar", "name", "mobile"))

    a = asset(db, "sample-lpc-s-001")
    assert f"asset:{a.asset_key}" in items(report, "survey_numbers")
    assert len(a.survey_numbers) > 3

    team = Team(db)
    reg = client.get(f"/assets/{a.id}/register", headers=auth(team.viewer))
    assert reg.status_code == 200, reg.text
    body = reg.json()
    assert body["core_area_sq_m"] > 0 and any(p["core"] for p in body["parcels"])
    assert {p["zone"] for p in body["parcels"]} >= {"inside", "buffer"}
    assert body["links"][0]["connector"] == "hmda_lpc" and body["links"][0]["external_id"] == "S-001"
    assert body["boundary_source"]["connector"] == "hmda_lpc"
    assert "FICTIONAL-NAME" not in reg.text
    assert client.get(f"/assets/{a.id}/register").status_code == 401


def test_the_order_of_sources_does_not_create_duplicates(db, isolated_storage):
    apply(db, "hydraa")  # the HYDRAA layer arrives before the LPC register
    report = apply(db, "hmda_lpc")
    weaker = items(report, "skipped_weaker")["hmda_lpc:S-002"]
    assert weaker["asset_key"] == "sample-hydraa-hr-s-002" and weaker["matched_by"] == "spatial"
    assert db.scalar(select(func.count()).select_from(Asset).where(Asset.name == "Sample Cheruvu B")) == 1


# Validation and transports ---------------------------------------------------------------------


def _drop(isolated_storage, name: str, files: dict[str, str], manifest: bool = True):
    folder = isolated_storage.local_path(f"source-drops/{name}")
    folder.mkdir(parents=True, exist_ok=True)
    if manifest:
        (folder / "manifest.yml").write_text("source_date: 2026-11-01\nreference: TEST\n", encoding="utf-8")
    for fname, content in files.items():
        (folder / fname).write_text(content, encoding="utf-8")
    return folder


def test_a_real_drop_must_lie_in_telangana(db, isolated_storage):
    lakes = ("lake_id,lake_name,district,mandal,village,survey_numbers,area_ha,notification_status\n"
             "T-1,Test Lake,D,M,V,,9,none\n")
    ftl = json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"lake_id": "T-1"}, "geometry": square()}]})
    _drop(isolated_storage, "hmda_lpc", {"lakes.csv": lakes, "ftl.geojson": ftl})
    report = engine.run(db, "hmda_lpc", transport="file_drop", dry_run=True)
    assert report["is_sample"] is False
    assert "outside Telangana" in items(report, "rejected")["hmda_lpc:T-1"]["reason"]


def test_a_drop_needs_files_and_a_manifest(db, isolated_storage):
    with pytest.raises(SourceError, match="no files"):
        engine.run(db, "irrigation", transport="file_drop")
    _drop(isolated_storage, "irrigation", {"tanks.csv": "tank_id,tank_name,district,mandal,village\n"}, manifest=False)
    with pytest.raises(SourceError, match="manifest"):
        engine.run(db, "irrigation", transport="file_drop")


def _sample_server(content_type_for):
    def handler(request: httpx.Request) -> httpx.Response:
        name = request.url.path.rsplit("/", 1)[-1]
        assert request.headers["authorization"] == "Bearer test-token"
        path = SAMPLES_DIR / "hmda_lpc" / name
        return httpx.Response(200, content=path.read_bytes(), headers={"content-type": content_type_for(name)})
    return httpx.Client(transport=httpx.MockTransport(handler))


def _api(client=None, agreement="TEST/AGREEMENT/1", base="https://data.example.test/lpc"):
    return OfficialApiTransport(base_url=base, agreement_ref=agreement, token_env="LP_SRC_TEST_TOKEN",
                                paths={"lakes": "/lakes.csv", "ftl": "/ftl.geojson"}, client=client)


def test_api_transport_needs_an_agreement_and_refuses_web_pages(db, client, monkeypatch, isolated_storage):
    with pytest.raises(AgreementRequired, match="no data-sharing agreement"):
        _api(agreement=None).fetch(CONNECTORS["hmda_lpc"])
    nodal = make_user(db, "admin")
    res = client.post("/sources/hmda_lpc/runs", json={"transport": "api"}, headers=auth(nodal))
    assert res.status_code == 409 and "agreement" in res.json()["detail"]

    monkeypatch.setenv("LP_SRC_TEST_TOKEN", "test-token")
    html = _api(_sample_server(lambda name: "text/html; charset=utf-8"))
    with pytest.raises(SourceError, match="does not read portal pages"):
        html.fetch(CONNECTORS["hmda_lpc"])

    ok = _api(_sample_server(lambda name: "text/csv" if name.endswith(".csv") else "application/geo+json"))
    report = engine.run(db, "hmda_lpc", transport="api", transport_obj=ok, dry_run=False)
    # Data through the API path is treated as real, so the sea-located samples are refused.
    assert report["transport"] == "api" and report["is_sample"] is False
    assert report["counts"] == {"rejected": 4, "waiting": 1}
    snap = db.scalar(select(SourceSnapshot).where(SourceSnapshot.transport == "api"))
    assert snap.agreement_ref == "TEST/AGREEMENT/1"


# API and guards ----------------------------------------------------------------------------------


def test_sources_api_roles_and_listing(db, client, isolated_storage):
    team = Team(db)
    listing = client.get("/sources", headers=auth(team.viewer))
    assert listing.status_code == 200
    by_name = {s["name"]: s for s in listing.json()["items"]}
    assert set(by_name) == {"hmda_lpc", "irrigation", "bhu_bharati", "hydraa"}
    assert all(s["sample_available"] and s["agreement_ref"] is None and not s["api_configured"] for s in by_name.values())
    assert [d["file_name"] for d in by_name["bhu_bharati"]["datasets"]] == ["village_parcels.geojson", "ror_extract.csv"]
    assert client.get("/sources").status_code == 401

    body = {"transport": "sample", "dry_run": True}
    assert client.post("/sources/hmda_lpc/runs", json=body, headers=auth(team.viewer)).status_code == 403
    assert client.post("/sources/nowhere/runs", json=body, headers=auth(team.admin)).status_code == 404
    preview = client.post("/sources/hmda_lpc/runs", json=body, headers=auth(team.admin))
    assert preview.status_code == 200 and preview.json()["counts"]["assets_created"] == 3

    applied = client.post("/sources/hmda_lpc/runs", json={"transport": "sample", "dry_run": False}, headers=auth(team.admin))
    assert applied.status_code == 200 and applied.json()["run_id"]
    runs = client.get("/sources/runs", headers=auth(team.viewer)).json()["items"]
    assert runs[0]["id"] == applied.json()["run_id"] and runs[0]["actor_id"] == team.admin.id
    assert any(i["action"] == "created" for i in runs[0]["items"])
    after = {s["name"]: s for s in client.get("/sources", headers=auth(team.admin)).json()["items"]}
    assert after["hmda_lpc"]["last_run"]["id"] == runs[0]["id"]


@pytest.mark.parametrize("statement", [
    "UPDATE source_snapshots SET reference = 'x'",
    "DELETE FROM land_parcels",
    "UPDATE asset_source_links SET external_id = 'x'",
    "DELETE FROM import_runs",
])
def test_source_tables_are_append_only(db, isolated_storage, statement):
    apply(db, "hmda_lpc")
    apply(db, "bhu_bharati")
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text(statement))
    db.rollback()
