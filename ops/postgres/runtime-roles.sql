-- Run as a PostgreSQL administrator before the first production migration.
-- Set both passwords out-of-band through the approved secrets manager.
-- PostGIS extension creation may require DBA privileges; install it here before migrations.
CREATE EXTENSION IF NOT EXISTS postgis;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lakeprotect_migrator') THEN
    CREATE ROLE lakeprotect_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lakeprotect_app') THEN
    CREATE ROLE lakeprotect_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
  END IF;
END
$$;

GRANT CONNECT ON DATABASE lakeprotect TO lakeprotect_migrator, lakeprotect_app;
GRANT USAGE, CREATE ON SCHEMA public TO lakeprotect_migrator;
GRANT USAGE ON SCHEMA public TO lakeprotect_app;

-- Run Alembic migrations using lakeprotect_migrator as the object owner.
-- The API connects only as lakeprotect_app; never use the migrator or a superuser at runtime.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO lakeprotect_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO lakeprotect_app;

ALTER DEFAULT PRIVILEGES FOR ROLE lakeprotect_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO lakeprotect_app;
ALTER DEFAULT PRIVILEGES FOR ROLE lakeprotect_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO lakeprotect_app;

-- Verify before deployment:
-- SELECT rolname, rolsuper, rolbypassrls FROM pg_roles
-- WHERE rolname IN ('lakeprotect_migrator','lakeprotect_app');
-- Both roles must return rolsuper=false and rolbypassrls=false.
