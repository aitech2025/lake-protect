"""GeoGuard API (formerly Lake Protect; DECISIONS.md D-061)."""
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.platform import intelligence_router, ingestion_router
from app.platform import router as platform_router
from app.routers import (
    alerts,
    assets,
    audit,
    auth,
    bulletins,
    candidates,
    citizen,
    dashboard,
    documents,
    notifications,
    pipeline,
    records,
    reports,
    satellites,
    sources,
    tiles,
    users,
)

app = FastAPI(title="GeoGuard API", version="0.1.0")
for module in (auth, assets, candidates, pipeline, alerts, records, sources, documents, audit, users, tiles, bulletins, notifications, dashboard,
               citizen, reports, satellites):
    app.include_router(module.router)
app.include_router(platform_router.router)
app.include_router(intelligence_router.router)
app.include_router(ingestion_router.router)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    return {
        "status": "ok",
        "postgis": db.execute(text("SELECT postgis_version()")).scalar_one(),
        "migration": db.execute(text("SELECT version_num FROM alembic_version")).scalar_one(),
    }
