"""Real data only: the demo world is removed (DECISIONS.md D-065).

Deletes every record of the fictional demo world and the fictional sample registers:
- rows flagged `is_demo` (every table except `users`: the role accounts stay, at the owner's
  request) and rows flagged `is_sample`;
- then every row left pointing at a deleted row (boundaries, candidates, weekly records,
  deliveries and so on), until none is left;
- the role accounts' areas in the demo districts.

The append-only guards would refuse these deletes, by design. This migration turns them off for
its own transaction only (`session_replication_role = replica`, which needs the database owner's
superuser role, as in the Docker image). The audit log is kept whole: its hash chain must not
break, so the entries about demo records stay as history.

There is no way back: the downgrade does nothing. A fresh database gets the real lakes and the role
accounts from `python -m app.seed.reset`.

Revision ID: 0012
Revises: 0011
"""
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

UP = r"""
SET LOCAL session_replication_role = replica;

DO $$
DECLARE
    t text;
    fk record;
    n bigint;
    total bigint;
BEGIN
    FOR t IN
        SELECT c.table_name FROM information_schema.columns c
        JOIN information_schema.tables tb ON tb.table_schema = c.table_schema AND tb.table_name = c.table_name
        WHERE c.table_schema = 'public' AND tb.table_type = 'BASE TABLE' AND c.column_name = 'is_demo' AND c.table_name <> 'users'
    LOOP
        EXECUTE format('DELETE FROM %I WHERE is_demo', t);
    END LOOP;
    FOR t IN
        SELECT c.table_name FROM information_schema.columns c
        JOIN information_schema.tables tb ON tb.table_schema = c.table_schema AND tb.table_name = c.table_name
        WHERE c.table_schema = 'public' AND tb.table_type = 'BASE TABLE' AND c.column_name = 'is_sample'
    LOOP
        EXECUTE format('DELETE FROM %I WHERE is_sample', t);
    END LOOP;

    -- Rows that point at a deleted row, through any single-column foreign key, until none is left.
    LOOP
        total := 0;
        FOR fk IN
            SELECT cl.relname AS child, ca.attname AS col, pl.relname AS parent, pa.attname AS pcol
            FROM pg_constraint k
            JOIN pg_class cl ON cl.oid = k.conrelid
            JOIN pg_class pl ON pl.oid = k.confrelid
            JOIN pg_namespace ns ON ns.oid = cl.relnamespace
            JOIN pg_attribute ca ON ca.attrelid = k.conrelid AND ca.attnum = k.conkey[1]
            JOIN pg_attribute pa ON pa.attrelid = k.confrelid AND pa.attnum = k.confkey[1]
            WHERE k.contype = 'f' AND ns.nspname = 'public' AND cardinality(k.conkey) = 1
        LOOP
            EXECUTE format('DELETE FROM %I c WHERE c.%I IS NOT NULL AND NOT EXISTS (SELECT 1 FROM %I p WHERE p.%I = c.%I)',
                           fk.child, fk.col, fk.parent, fk.pcol, fk.col);
            GET DIAGNOSTICS n = ROW_COUNT;
            total := total + n;
        END LOOP;
        EXIT WHEN total = 0;
    END LOOP;
END $$;

DELETE FROM official_areas WHERE district LIKE 'Demo %';
"""


def run_raw(sql: str) -> None:
    with op.get_bind().connection.dbapi_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    run_raw(UP)


def downgrade() -> None:
    """Deleted demo records cannot come back; nothing to undo."""
