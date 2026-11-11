"""Lake Protect API."""
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.platform import router as platform_router
from app.routers import alerts, assets, audit, auth, bulletins, candidates, records, tiles, users

app = FastAPI(title="Lake Protect API", version="0.2.0")
for module in (auth, assets, candidates, alerts, records, audit, users, tiles, bulletins):
    app.include_router(module.router)
app.include_router(platform_router.router)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    return {
        "status": "ok",
        "postgis": db.execute(text("SELECT postgis_version()")).scalar_one(),
        "migration": db.execute(text("SELECT version_num FROM alembic_version")).scalar_one(),
    }
