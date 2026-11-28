"""Legal documents tagged to assets (DECISIONS.md D-057): uploads, references, supersession,
append-only storage, and the documents the source engine tags from what it loads."""
import hashlib

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.models import Asset, AssetDocument
from app.sources import engine
from tests.factories import Team, auth, make_asset

PDF = b"%PDF-1.4\n% test document\n"


def _upload(client, asset_id, user, **form):
    files = form.pop("files", {"file": ("notice.pdf", PDF, "application/pdf")})
    data = {"doc_type": "notification", "title": "Final FTL notification TEST/1", "reference": "TEST/1", "issued_on": "2025-03-14"} | form
    return client.post(f"/assets/{asset_id}/documents", data=data, files=files, headers=auth(user))


def test_admin_uploads_and_everyone_reads(db, client, isolated_storage):
    team = Team(db)
    asset = make_asset(db)
    r = _upload(client, asset.id, team.admin)
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["has_file"] and doc["sha256"] == hashlib.sha256(PDF).hexdigest() and doc["issued_on"] == "2025-03-14"
    listed = client.get(f"/assets/{asset.id}/documents", headers=auth(team.district)).json()["items"]
    assert [d["title"] for d in listed] == ["Final FTL notification TEST/1"]
    file = client.get(f"/documents/{doc['id']}/file", headers=auth(team.district))
    assert file.status_code == 200 and file.content == PDF and file.headers["X-SHA256"] == doc["sha256"]
    assert db.scalar(text("SELECT count(*) FROM audit_log WHERE action = 'export.document'")) == 1


def test_viewers_cannot_add_documents(db, client):
    team = Team(db)
    assert _upload(client, make_asset(db).id, team.district).status_code == 403


def test_files_must_be_what_they_claim(db, client):
    team = Team(db)
    asset = make_asset(db)
    bad = _upload(client, asset.id, team.admin, files={"file": ("notice.pdf", b"not a pdf", "application/pdf")})
    assert bad.status_code == 422 and "not a valid" in bad.json()["detail"]
    exe = _upload(client, asset.id, team.admin, files={"file": ("tool.exe", b"MZ", "application/octet-stream")})
    assert exe.status_code == 422


def test_a_reference_alone_is_enough_but_something_is_needed(db, client):
    team = Team(db)
    asset = make_asset(db)
    ref = client.post(f"/assets/{asset.id}/documents", data={"doc_type": "court_order", "title": "Case TEST-WP-1", "reference": "TEST-WP-1"}, headers=auth(team.admin))
    assert ref.status_code == 201 and ref.json()["has_file"] is False
    empty = client.post(f"/assets/{asset.id}/documents", data={"doc_type": "other", "title": "Nothing"}, headers=auth(team.admin))
    assert empty.status_code == 422


def test_corrections_supersede_and_rows_never_change(db, client):
    team = Team(db)
    asset = make_asset(db)
    first = _upload(client, asset.id, team.admin).json()
    second = _upload(client, asset.id, team.admin, title="Final FTL notification TEST/1 (corrected)", supersedes_id=str(first["id"])).json()
    listed = {d["id"]: d for d in client.get(f"/assets/{asset.id}/documents", headers=auth(team.district)).json()["items"]}
    assert listed[first["id"]]["superseded"] is True and listed[second["id"]]["superseded"] is False
    with pytest.raises(DBAPIError, match="append-only"):
        with db.begin_nested():
            db.execute(text("UPDATE asset_documents SET title = 'x' WHERE id = :i"), {"i": first["id"]})


def test_the_source_engine_tags_the_documents_behind_each_record(db, isolated_storage):
    engine.run(db, "hmda_lpc", transport="sample", dry_run=False)
    engine.run(db, "hydraa", transport="sample", dry_run=False)
    engine.run(db, "bhu_bharati", transport="sample", dry_run=False)

    def docs(key):
        asset = db.scalar(select(Asset).where(Asset.asset_key == key))
        return {(d.doc_type, d.reference) for d in db.scalars(select(AssetDocument).where(AssetDocument.asset_id == asset.id))}

    a = docs("sample-lpc-s-001")
    assert ("notification", "SAMPLE/LPC/FINAL/001") in a and ("land_record", None) in a
    b = docs("sample-lpc-s-002")
    assert {("notification", "SAMPLE/LPC/PRELIM/002"), ("notification", "SAMPLE/LPC/FINAL/002")} <= b
    assert ("survey_map", None) in docs("sample-lpc-s-003")
    assert ("recovery_order", "SAMPLE/HYDRAA/ORDER/01") in docs("sample-hydraa-hyd-rec-s-01")
    tagged = db.scalar(select(AssetDocument).where(AssetDocument.reference == "SAMPLE/LPC/FINAL/001"))
    assert tagged.file_key and isolated_storage.get_object(tagged.file_key).startswith(b"{")
    # Running the same files again tags nothing new.
    before = db.scalar(text("SELECT count(*) FROM asset_documents"))
    engine.run(db, "hmda_lpc", transport="sample", dry_run=False)
    assert db.scalar(text("SELECT count(*) FROM asset_documents")) == before
