"""Database engine and session dependency."""
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# All timestamps are handled in UTC, so audit hashes are stable.
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args={"options": "-c timezone=UTC"})
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


# SQLSTATEs raised by our guard triggers and constraints.
_GUARD_STATES = {"23514": "check_violation", "23001": "restrict_violation", "23505": "unique_violation", "23503": "foreign_key_violation"}


@contextmanager
def db_guard(db: Session):
    """Turn a database guard (trigger or constraint) into HTTP 409 and roll the session back."""
    try:
        yield
    except DBAPIError as exc:
        db.rollback()
        sqlstate = getattr(exc.orig, "sqlstate", None)
        if sqlstate in _GUARD_STATES:
            message = str(exc.orig).splitlines()[0]
            raise HTTPException(status_code=409, detail=f"Refused by the database: {message}") from exc
        raise
