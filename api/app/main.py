"""GeoGuard API (formerly Lake Protect; DECISIONS.md D-061)."""
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.enums import Role
from app.models import User
from app.readiness import build_readiness
from app.security import require_roles
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


@app.get("/readiness")
def readiness(user: User = Depends(require_roles(Role.admin)), db: Session = Depends(get_db)) -> dict:
    """Admin-only operational configuration checklist; never certifies production readiness."""
    return build_readiness(db, settings)
