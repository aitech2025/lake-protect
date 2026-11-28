"""Evidence pack for a confirmed incident: invariant 13, verify-pack passing and failing, and versioning."""
import datetime as dt
import io
import json
import re
import subprocess
import zipfile

import pytest
from pypdf import PdfReader
from sqlalchemy import select

from app.config import settings
from app.evidence import pack as pack_svc
from app.evidence.verify import verify
from app.models import AuditLog, EvidencePack
from app.services import documents as doc_svc
from tests.factories import Team, auth, decide, ingest, make_asset, review

T0 = dt.datetime(2025, 10, 6, 6, tzinfo=dt.timezone.utc)
STATEMENT = "Imagery shows physical change. It does not establish title or legality."


def at(days: float) -> dt.datetime:
    return T0 + dt.timedelta(days=days)


@pytest.fixture()
def confirmed(db):
    team = Team(db)
    asset = make_asset(db, cohort="A_RECOVERED", is_demo=True)
    _, alert = ingest(db, asset, at=T0, first_changed=dt.date(2025, 9, 25), last_clear=dt.date(2025, 9, 15))
    review(db, alert, team.district, "real_change", "Fresh soil on both images", at=at(1))
    decide(db, alert, team.senior, "CONFIRMED", "Real change", at=at(2))
    doc_svc.add(db, asset, doc_type="recovery_order", title="Recovery order TEST/1", reference="TEST/1",
                content=b"%PDF-1.4 test", file_name="order.pdf", content_type="application/pdf", actor_id=team.admin.id)
    assert alert.state == "CONFIRMED"
    return team, alert


def _pdf_text(data: bytes) -> str:
    return re.sub(r"\s+", " ", " ".join(page.extract_text() for page in PdfReader(io.BytesIO(data)).pages))


def _zip(store, pack) -> bytes:
    return store.get_object(pack.zip_path)


def test_invariant_13_pack_shows_the_statement_and_the_draft_mark(db, confirmed, isolated_storage):
    team, alert = confirmed
    pack = pack_svc.build(db, alert, team.senior, at=at(4))
    assert pack.counsel_reviewed is False
    text = _pdf_text(isolated_storage.get_object(pack.pdf_path))
    assert STATEMENT in text
    assert "Draft for counsel review" in text
    with zipfile.ZipFile(io.BytesIO(_zip(isolated_storage, pack))) as z:
        cert = z.read("certificate/section-63-4-template.html").decode()
        manifest = json.loads(z.read("manifest.json"))
    assert "Draft for counsel review" in cert
    assert manifest["statement"] == STATEMENT and manifest["counsel_reviewed"] is False


def test_invariant_13_draft_mark_goes_only_after_counsel_review(db, confirmed, isolated_storage, monkeypatch):
    team, alert = confirmed
    monkeypatch.setattr(settings, "counsel_reviewed_template", True)
    pack = pack_svc.build(db, alert, team.senior, at=at(4))
    text = _pdf_text(isolated_storage.get_object(pack.pdf_path))
    assert pack.counsel_reviewed is True
    assert STATEMENT in text and "Draft for counsel review" not in text


def test_pack_contents_follow_section_9_3(db, confirmed, isolated_storage):
    team, alert = confirmed
    pack = pack_svc.build(db, alert, team.senior, at=at(4))
    with zipfile.ZipFile(io.BytesIO(_zip(isolated_storage, pack))) as z:
        names = set(z.namelist())
    assert {"evidence/before.png", "evidence/after.png", "evidence/boundary.geojson", "evidence/change.geojson", "records/legal_check.json",
            "records/reviews.json", "records/history.json", "records/processing_note.json", "certificate/section-63-4-template.html",
            "case_file.pdf", "manifest.json"} <= names
    assert sum(n.startswith("documents/") for n in names) == 1
    text = _pdf_text(isolated_storage.get_object(pack.pdf_path))
    for heading in ["1. Asset and boundary", "2. Dated image pair", "3. Processing note", "4. File hashes", "5. Reviews by officials",
                    "6. Decision", "Recovery order TEST/1", "7. Section 63(4) certificate", "Part A", "Part B", "8. Statement"]:
        assert heading in text, heading
    assert "Demo data" in text  # test assets are demo data


def test_verify_pack_passes_and_fails_when_a_file_changes(db, confirmed, isolated_storage, tmp_path):
    team, alert = confirmed
    pack = pack_svc.build(db, alert, team.senior, at=at(4))
    good = tmp_path / "good.zip"
    good.write_bytes(_zip(isolated_storage, pack))
    assert verify(good, pack.manifest_sha256)["ok"] is True

    def rewrite(target, change):
        with zipfile.ZipFile(good) as src, zipfile.ZipFile(target, "w") as dst:
            for info in src.infolist():
                data = change(info.filename, src.read(info.filename))
                if data is not None:
                    dst.writestr(info, data)
            if change("__add__", b"") is not None:
                dst.writestr("extra.txt", b"added later")

    changed = tmp_path / "changed.zip"
    rewrite(changed, lambda n, d: (d + b"\x00") if n == "evidence/after.png" else (None if n == "__add__" else d))
    assert verify(changed)["problems"] == ["changed: evidence/after.png"]

    removed = tmp_path / "removed.zip"
    rewrite(removed, lambda n, d: None if n in ("records/reviews.json", "__add__") else d)
    assert verify(removed)["problems"] == ["missing: records/reviews.json"]

    added = tmp_path / "added.zip"
    rewrite(added, lambda n, d: d if n != "__add__" else b"")
    assert verify(added)["problems"] == ["not listed in the manifest: extra.txt"]

    # Someone edits a file and rewrites the manifest to match: only the recorded hash catches it.
    forged = tmp_path / "forged.zip"
    manifest = json.loads(zipfile.ZipFile(good).read("manifest.json"))
    import hashlib

    tampered = zipfile.ZipFile(good).read("evidence/after.png") + b"\x00"
    for f in manifest["files"]:
        if f["path"] == "evidence/after.png":
            f["sha256"] = hashlib.sha256(tampered).hexdigest()
    rewrite(forged, lambda n, d: None if n == "__add__" else tampered if n == "evidence/after.png" else json.dumps(manifest).encode() if n == "manifest.json" else d)
    assert verify(forged)["ok"] is True
    assert verify(forged, pack.manifest_sha256)["ok"] is False


def test_lp_verify_pack_command_exit_codes(db, confirmed, isolated_storage, tmp_path):
    team, alert = confirmed
    pack = pack_svc.build(db, alert, team.senior, at=at(4))
    good = tmp_path / "pack.zip"
    good.write_bytes(_zip(isolated_storage, pack))
    ok = subprocess.run(["lp", "verify-pack", str(good), "--manifest-sha256", pack.manifest_sha256], capture_output=True, text=True)
    assert ok.returncode == 0 and "PASS" in ok.stdout
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(good) as src, zipfile.ZipFile(bad, "w") as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            dst.writestr(info, data + b"x" if info.filename == "case_file.pdf" else data)
    fail = subprocess.run(["lp", "verify-pack", str(bad)], capture_output=True, text=True)
    assert fail.returncode == 1 and "changed: case_file.pdf" in fail.stdout


def test_regenerating_adds_a_version_and_keeps_the_old_one(db, client, confirmed, isolated_storage):
    team, alert = confirmed
    r1 = client.post(f"/alerts/{alert.id}/evidence-pack", headers=auth(team.senior))
    r2 = client.post(f"/alerts/{alert.id}/evidence-pack", headers=auth(team.senior))
    assert r1.status_code == 201 and r2.status_code == 201
    assert (r1.json()["version"], r2.json()["version"]) == (1, 2)
    packs = db.scalars(select(EvidencePack).where(EvidencePack.alert_id == alert.id).order_by(EvidencePack.version)).all()
    assert packs[0].zip_path != packs[1].zip_path and isolated_storage.head_object(packs[0].zip_path) is not None
    v1 = client.get(f"/alerts/{alert.id}/evidence-pack?version=1", headers=auth(team.admin))
    assert v1.status_code == 200 and v1.headers["X-Manifest-SHA256"] == packs[0].manifest_sha256
    assert client.get(f"/alerts/{alert.id}/evidence-pack/verify", headers=auth(team.admin)).json()["ok"] is True
    exports = db.scalars(select(AuditLog).where(AuditLog.action == "export.evidence_pack")).all()
    assert len(exports) == 1  # every export is logged


def test_pack_needs_a_confirmed_change(db, client):
    team = Team(db)
    _, alert = ingest(db, make_asset(db), at=T0, first_changed=dt.date(2025, 9, 25), last_clear=dt.date(2025, 9, 15))
    assert client.post(f"/alerts/{alert.id}/evidence-pack", headers=auth(team.senior)).status_code == 409
    assert client.post(f"/alerts/{alert.id}/evidence-pack", headers=auth(team.admin)).status_code == 403
    assert client.post(f"/alerts/{alert.id}/evidence-pack", headers=auth(team.field)).status_code == 403
