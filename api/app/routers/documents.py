"""Legal documents tagged to assets (DECISIONS.md D-057).

GET  /assets/{id}/documents      every document on the asset, newest last; superseded ones marked
POST /assets/{id}/documents      admin: upload a PDF, PNG or JPEG, or record a reference
GET  /documents/{id}/file        the file itself, if one is held; every download is logged
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.audit import chain
from app.db import db_guard, get_db
from app.enums import Role
from app.models import Asset, AssetDocument, User
from app.security import current_user, require_roles
from app.services import documents as doc_svc
from app import access
from app.storage import store

router = APIRouter(tags=["documents"])


@router.get("/assets/{asset_id}/documents")
def list_documents(asset_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    access.require_asset(db, user, asset_id)
    items = doc_svc.list_for(db, asset_id)
    chain.record(db, actor_id=user.id, action="view.documents", entity="asset", entity_id=asset_id, details={"count": len(items)})
    db.commit()
    return {"asset_id": asset_id, "items": items}


@router.post("/assets/{asset_id}/documents", status_code=201)
async def add_document(
    asset_id: int,
    doc_type: str = Form(...),
    title: str = Form(...),
    reference: str | None = Form(None),
    issued_on: str | None = Form(None),
    issued_by: str | None = Form(None),
    source_url: str | None = Form(None),
    supersedes_id: int | None = Form(None),
    file: UploadFile | None = File(None),
    user: User = Depends(require_roles(Role.admin)),
    db: Session = Depends(get_db),
) -> dict:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(404, "Asset not found")
    try:
        issued = dt.date.fromisoformat(issued_on) if issued_on else None
    except ValueError as exc:
        raise HTTPException(422, "issued_on must be YYYY-MM-DD") from exc
    content = await file.read() if file is not None and file.filename else None
    with db_guard(db):
        try:
            doc = doc_svc.add(
                db, asset, doc_type=doc_type, title=title, reference=reference, issued_on=issued, issued_by=issued_by,
                source_url=source_url or None, content=content, file_name=file.filename if content else None,
                content_type=file.content_type if content else None, supersedes_id=supersedes_id, actor_id=user.id,
            )
        except doc_svc.DocumentRefused as exc:  # refused before anything is written
            raise HTTPException(422, str(exc)) from exc
        db.commit()
    return doc_svc.as_dict(doc, set())


@router.get("/documents/{doc_id}/file")
def get_document_file(doc_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    doc = db.get(AssetDocument, doc_id)
    if doc is None or not doc.file_key or store.head_object(doc.file_key) is None:
        raise HTTPException(404, "No file is held for this document")
    access.require_asset(db, user, doc.asset_id)
    data = store.get_object(doc.file_key)
    chain.record(db, actor_id=user.id, action="export.document", entity="asset", entity_id=doc.asset_id,
                 details={"document_id": doc.id, "sha256": doc.sha256})
    db.commit()
    media = doc.content_type or ("application/geo+json" if (doc.file_name or "").endswith(".geojson") else "application/octet-stream")
    name = doc.file_name or f"document-{doc.id}"
    return Response(data, media_type=media, headers={"Content-Disposition": f'inline; filename="{name}"', "X-SHA256": doc.sha256 or ""})
