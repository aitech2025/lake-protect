"""Legal documents tagged to an asset (DECISIONS.md D-057).

A document is a file with its SHA-256, or a reference to one held elsewhere (a notification
number, a court case, a URL), or both. Rows are append-only: a correction is a new row that
supersedes the old one, so what an incident relied on can always be shown again.

Three ways in:
- the admin uploads a file or records a reference;
- the source engine tags the notification, order or land-record file an asset's record came from;
- the demo seed adds fictional documents to the demo world.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import chain
from app.enums import DocumentType
from app.models import Asset, AssetDocument
from app.storage import store

MAX_BYTES = 25 * 1024 * 1024
ALLOWED_TYPES = {"application/pdf": ".pdf", "image/png": ".png", "image/jpeg": ".jpg"}
MAGIC = {"application/pdf": b"%PDF", "image/png": b"\x89PNG", "image/jpeg": b"\xff\xd8"}


class DocumentRefused(ValueError):
    pass


def _safe_name(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", name or "document").strip("._") or "document"
    return stem[-80:]


def add(
    db: Session,
    asset: Asset,
    *,
    doc_type: str,
    title: str,
    reference: str | None = None,
    issued_on: dt.date | None = None,
    issued_by: str | None = None,
    source_url: str | None = None,
    content: bytes | None = None,
    file_name: str | None = None,
    content_type: str | None = None,
    file_key: str | None = None,
    file_sha256: str | None = None,
    source_snapshot_id: int | None = None,
    supersedes_id: int | None = None,
    actor_id: int | None = None,
    at: dt.datetime | None = None,
    alert_id: int | None = None,
) -> AssetDocument:
    """Add a document. Give `content` to store a new file, or `file_key` and `file_sha256` to point at
    a file already in the store (a source snapshot)."""
    try:
        doc_type = DocumentType(doc_type).value
    except ValueError as exc:
        raise DocumentRefused(f"Unknown document type {doc_type}") from exc
    if not (title and title.strip()):
        raise DocumentRefused("A document needs a title")
    if supersedes_id is not None:
        old = db.get(AssetDocument, supersedes_id)
        if old is None or old.asset_id != asset.id:
            raise DocumentRefused("A document can only supersede another document of the same asset")
    sha = file_sha256
    size = None
    if content is not None:
        if content_type not in ALLOWED_TYPES:
            raise DocumentRefused("Upload a PDF, PNG or JPEG file")
        if not content.startswith(MAGIC[content_type]):
            raise DocumentRefused(f"The file is not a valid {content_type}")
        if len(content) > MAX_BYTES:
            raise DocumentRefused("The file is larger than 25 MB")
        sha = hashlib.sha256(content).hexdigest()
        size = len(content)
        name = _safe_name(file_name or f"document{ALLOWED_TYPES[content_type]}")
        file_key = store.put_object(f"documents/{asset.asset_key}/{sha[:16]}_{name}", content)
        file_name = name
    if not (file_key or (reference and reference.strip()) or source_url):
        raise DocumentRefused("Give a file, a reference or a link")
    doc = AssetDocument(
        asset_id=asset.id, doc_type=doc_type, title=title.strip(), reference=(reference or "").strip() or None,
        issued_on=issued_on, issued_by=issued_by, file_key=file_key, file_name=file_name, content_type=content_type,
        sha256=sha if file_key else None, byte_size=size, source_url=source_url, source_snapshot_id=source_snapshot_id,
        supersedes_id=supersedes_id, added_by=actor_id, is_demo=asset.is_demo, alert_id=alert_id,
    )
    if at is not None:
        doc.added_at = at
    db.add(doc)
    db.flush()
    chain.record(db, actor_id=actor_id, action="document.added", entity="asset", entity_id=asset.id,
                 details={"document_id": doc.id, "doc_type": doc_type, "title": doc.title, "reference": doc.reference,
                          "sha256": doc.sha256, "supersedes_id": supersedes_id, "source_snapshot_id": source_snapshot_id},
                 at=at)
    return doc


def tag_once(db: Session, asset: Asset, *, doc_type: str, title: str, reference: str | None, source_snapshot_id: int, **kw) -> AssetDocument | None:
    """Tag a source document unless the same one is already on the asset."""
    exists = db.scalar(select(AssetDocument.id).where(
        AssetDocument.asset_id == asset.id, AssetDocument.doc_type == doc_type,
        AssetDocument.source_snapshot_id == source_snapshot_id,
        AssetDocument.reference.is_(None) if reference is None else AssetDocument.reference == reference,
    ).limit(1))
    if exists:
        return None
    return add(db, asset, doc_type=doc_type, title=title, reference=reference, source_snapshot_id=source_snapshot_id, **kw)


def as_dict(d: AssetDocument, superseded: set[int]) -> dict:
    return {
        "id": d.id, "doc_type": d.doc_type, "title": d.title, "reference": d.reference,
        "issued_on": d.issued_on.isoformat() if d.issued_on else None, "issued_by": d.issued_by,
        "has_file": bool(d.file_key), "file_name": d.file_name, "content_type": d.content_type, "sha256": d.sha256,
        "byte_size": d.byte_size, "source_url": d.source_url, "source_snapshot_id": d.source_snapshot_id,
        "supersedes_id": d.supersedes_id, "superseded": d.id in superseded, "added_at": d.added_at.isoformat() if d.added_at else None,
        "is_demo": d.is_demo, "alert_id": d.alert_id,
    }


def list_for(db: Session, asset_id: int) -> list[dict]:
    docs = db.scalars(select(AssetDocument).where(AssetDocument.asset_id == asset_id).order_by(AssetDocument.id)).all()
    superseded = {d.supersedes_id for d in docs if d.supersedes_id}
    return [as_dict(d, superseded) for d in docs]
