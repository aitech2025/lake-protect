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


# SQLSTATE codes raised by our guard triggers and constraints. Messages from our own triggers are
# shown as written; generic constraint messages are replaced with plain wording (section 6.8).
_OWN_MESSAGE = {"23514", "23001"}
_PLAIN = {"23505": "This record already exists.", "23503": "This refers to a record that does not exist."}


@contextmanager
def db_guard(db: Session):
    """Turn a database guard (trigger or constraint) into HTTP 409 and roll the session back."""
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
