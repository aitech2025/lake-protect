"""Lake Protect API."""
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.routers import alerts, assets, audit, auth, candidates, records

app = FastAPI(title="Lake Protect API", version="0.1.0")
for module in (auth, assets, candidates, alerts, records, audit):
    app.include_router(module.router)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    return {
        "status": "ok",
        "postgis": db.execute(text("SELECT postgis_version()")).scalar_one(),
        "migration": db.execute(text("SELECT version_num FROM alembic_version")).scalar_one(),
    }
