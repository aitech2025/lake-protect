"""Pipeline candidate ingest. Machine submissions require a shared pipeline credential."""
import hashlib
import hmac
import json
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config import settings
from app.db import db_guard, get_db
from app.rules.legal_check import NoBoundary
from app.services import ingest as ingest_svc

router = APIRouter(tags=["pipeline"])

def pipeline_token(x_pipeline_token: str | None = Header(default=None)) -> None:
    if not settings.pipeline_token:
        raise HTTPException(503, "Pipeline ingest is off: LP_PIPELINE_TOKEN is not set")
    if not x_pipeline_token or not hmac.compare_digest(x_pipeline_token, settings.pipeline_token):
        raise HTTPException(401, "Pipeline token required")

@router.post("/candidates", status_code=201, dependencies=[Depends(pipeline_token)])
def post_candidate(body: ingest_svc.CandidateIn, db: Session = Depends(get_db)) -> dict:
    # RLS context is set only after the machine credential has been validated.
    db.execute(text("SELECT set_config('lp.pipeline_ingest','true',true), set_config('lp.is_platform_admin','false',true)"))
    canonical = json.dumps(body.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    request_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    with db_guard(db):
        # Serialize identical submissions so retries cannot create duplicate candidates/alerts.
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": request_hash})
        previous = db.execute(text("""
          SELECT response FROM candidate_ingest_requests WHERE idempotency_key=:key
        """), {"key": request_hash}).scalar_one_or_none()
        if previous is not None:
            db.commit()
            return previous
        try:
            out = ingest_svc.ingest(db, body)
        except ingest_svc.IngestRefused as exc:
            db.rollback()
            raise HTTPException(exc.status, exc.message) from exc
        except NoBoundary as exc:
            db.rollback()
            raise HTTPException(422, str(exc)) from exc
        db.execute(text("""
          INSERT INTO candidate_ingest_requests(idempotency_key,payload_sha256,candidate_id,response)
          VALUES (:key,:payload_hash,:candidate_id,CAST(:response AS jsonb))
        """), {
            "key": request_hash,
            "payload_hash": request_hash,
            "candidate_id": out["candidate_id"],
            "response": json.dumps(out),
        })
        db.commit()
    return out
