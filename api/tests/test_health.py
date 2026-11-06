"""M0: the API reaches the database, PostGIS is on and migrations have run."""
from alembic.config import Config
from alembic.script import ScriptDirectory


def test_health_reports_postgis_and_head_migration(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["postgis"].startswith("3.")
    head = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
    assert body["migration"] == head
