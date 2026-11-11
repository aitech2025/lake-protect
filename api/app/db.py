"""Bounded SQLAlchemy pool and transaction-scoped database sessions."""
from collections.abc import Iterator
from contextlib import contextmanager
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker
from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout_seconds,
    pool_recycle=settings.db_pool_recycle_seconds,
    connect_args={
        "options": f"-c timezone=UTC -c statement_timeout={settings.db_statement_timeout_ms}",
        "application_name": "lake-protect-api",
    },
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

_OWN_MESSAGE = {"23514", "23001"}
_PLAIN = {"23505": "This record already exists.", "23503": "This refers to a record that does not exist."}

@contextmanager
def db_guard(db: Session):
    """Map expected integrity/immutability guards to HTTP 409; preserve unexpected errors."""
    try:
        yield
    except DBAPIError as exc:
        db.rollback()
        sqlstate = getattr(exc.orig, "sqlstate", None)
        if sqlstate in _OWN_MESSAGE:
            message = str(exc.orig).splitlines()[0]
            raise HTTPException(status_code=409, detail=f"Refused by the database: {message}") from exc
        if sqlstate in _PLAIN:
            raise HTTPException(status_code=409, detail=_PLAIN[sqlstate]) from exc
        raise
