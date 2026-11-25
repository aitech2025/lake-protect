"""WhatsApp Cloud API webhook; persist reports as unverified citizen signals.

The existing citizen web application is unchanged. A WhatsApp message is a lead,
not a verified incident or legal finding. Media bytes are not downloaded here.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config import settings
from app.db import get_db
from lake_protect.integrations.citizen import verify_meta_signature, normalize_meta_webhook, classify_report

router=APIRouter(tags=["citizen-whatsapp"])

@router.get("/webhooks/whatsapp")
def verify_webhook(mode: str | None = Query(default=None, alias="hub.mode"),
                   token: str | None = Query(default=None, alias="hub.verify_token"),
                   challenge: str | None = Query(default=None, alias="hub.challenge")):
    if not settings.whatsapp_verify_token:
        raise HTTPException(503,"WhatsApp webhook verification is not configured.")
    if mode=="subscribe" and token and token==settings.whatsapp_verify_token and challenge is not None:
        return PlainTextResponse(challenge)
    raise HTTPException(403,"WhatsApp webhook verification failed.")

@router.post("/webhooks/whatsapp")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    if not settings.whatsapp_app_secret:
        raise HTTPException(503,"WhatsApp webhook signing secret is not configured.")
    raw=await request.body()
    signature=request.headers.get("X-Hub-Signature-256")
    if not verify_meta_signature(raw,signature,settings.whatsapp_app_secret):
        raise HTTPException(401,"Invalid WhatsApp webhook signature.")
    try:
        payload=json.loads(raw)
        reports=normalize_meta_webhook(payload)
    except (ValueError,TypeError) as exc:
        raise HTTPException(400,"Invalid WhatsApp webhook payload.") from exc
    # Provider signature is checked before any transaction-local machine context.
    db.execute(text("""SELECT set_config('lp.pipeline_ingest','true',true),
        set_config('lp.is_platform_admin','false',true),set_config('lp.user_id','',true)"""))
    accepted=duplicates=0
    for report in reports:
        if report.latitude is not None and not (-90<=report.latitude<=90 and -180<=report.longitude<=180):
            continue
        # Serialise same provider message ID so webhook retries cannot create duplicate signals.
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                   {"key":"whatsapp:"+report.provider_message_id})
        existing=db.execute(text("""SELECT id FROM signals WHERE kind='citizen_whatsapp'
            AND CAST(ref AS jsonb) ->> 'provider_message_id' = :message_id LIMIT 1"""),
            {"message_id": report.provider_message_id}).scalar_one_or_none()
        if existing is not None:
            duplicates+=1
            continue
        envelope={**report.as_dict(),"category_hints":classify_report(report.text),
                  "received_at_server":datetime.now(timezone.utc).isoformat()}
        geometry=(json.dumps({"type":"Point","coordinates":[report.longitude,report.latitude]})
                  if report.latitude is not None and report.longitude is not None else None)
        db.execute(text("""INSERT INTO signals(kind,geom,received_at,ref,is_demo)
            VALUES ('citizen_whatsapp',
              CASE WHEN CAST(:geometry AS text) IS NULL THEN NULL
                   ELSE ST_SetSRID(ST_GeomFromGeoJSON(CAST(:geometry AS text)),4326) END,
              now(),:ref,false)"""),{"geometry":geometry,"ref":json.dumps(envelope,ensure_ascii=False)})
        accepted+=1
    db.commit()
    return {"status":"accepted","received":len(reports),"stored":accepted,"duplicates":duplicates,
            "note":"Reports are unverified signals; media retrieval and officer review are separate steps."}
