"""Audit hash chain at the storage level. The API check (invariant 9) is in test_invariants.py."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.audit import chain


def _seed(db, n=3):
    return [chain.record(db, actor_id=None, action="test.event", entity="test", entity_id=i, details={"i": i, "x": 0.1 * i, "te": "చెరువు"}) for i in range(n)]


def test_chain_links_and_verifies(db):
    rows = _seed(db)
    assert rows[1].prev_hash == rows[0].hash and rows[2].prev_hash == rows[1].hash
    assert chain.verify(db)["ok"] is True


def test_audit_rows_cannot_be_updated_by_the_app(db):
    rows = _seed(db)
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text("UPDATE audit_log SET action = 'x' WHERE id = :i"), {"i": rows[0].id})
    db.rollback()


def test_edit_that_bypasses_the_trigger_breaks_the_chain(db):
    rows = _seed(db)
    # A database superuser can switch triggers off. The hash chain still catches the edit.
    db.execute(text("SET LOCAL session_replication_role = replica"))
    db.execute(text("UPDATE audit_log SET details = '{\"i\": 99}' WHERE id = :i"), {"i": rows[1].id})
    db.execute(text("SET LOCAL session_replication_role = origin"))
    db.expire_all()
    result = chain.verify(db)
    assert result["ok"] is False and result["first_bad_id"] == rows[1].id
