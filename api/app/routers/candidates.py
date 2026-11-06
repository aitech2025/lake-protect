"""POST /candidates: pipeline ingest. Runs the legal check and the priority score."""
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
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
    with db_guard(db):
        try:
            out = ingest_svc.ingest(db, body)
        except ingest_svc.IngestRefused as exc:
            db.rollback()
            raise HTTPException(exc.status, exc.message) from exc
        except NoBoundary as exc:
            db.rollback()
            raise HTTPException(422, str(exc)) from exc
        db.commit()
    return out
