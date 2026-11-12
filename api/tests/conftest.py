"""Test harness.

Tests run against a separate database that is migrated once per session. Each test runs inside
one outer transaction that is rolled back, so tests see real triggers and constraints but leave
nothing behind.
"""
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.main import app


@pytest.fixture(scope="session")
def test_engine():
    url = make_url(settings.test_database_url)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()

    cfg = Config("alembic.ini")
    cfg.attributes["url"] = settings.test_database_url
    command.upgrade(cfg, "head")

    engine = create_engine(settings.test_database_url, connect_args={"options": "-c timezone=UTC"})

    # A separate non-owner role is used by the RLS integration tests. The normal
    # test connection is an administrator and would otherwise bypass row security.
    role_admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with role_admin.connect() as conn:
        conn.execute(text("""
          DO $role$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='lakeprotect_rls_test') THEN
              CREATE ROLE lakeprotect_rls_test NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
            END IF;
          END $role$
        """))
        conn.execute(text(f'GRANT CONNECT ON DATABASE "{url.database}" TO lakeprotect_rls_test'))
    role_admin.dispose()
    with engine.begin() as conn:
        conn.execute(text("GRANT USAGE ON SCHEMA public TO lakeprotect_rls_test"))
        conn.execute(text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO lakeprotect_rls_test"))
        conn.execute(text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO lakeprotect_rls_test"))

    yield engine
    engine.dispose()


@pytest.fixture()
def db(test_engine) -> Iterator[Session]:
    connection = test_engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Tests write chips, photos and packs to a temporary folder, never to the real store."""
    from app.storage import store

    monkeypatch.setattr(store, "root", tmp_path / "storage")
    yield store


@pytest.fixture()
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
