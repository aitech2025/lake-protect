from sqlalchemy import text


def test_statewide_registry_and_security_tables_exist(db):
    names = db.execute(text("""
      SELECT tablename FROM pg_tables
      WHERE schemaname='public' AND tablename = ANY(:names)
    """), {"names": [
        "public_assets", "departments", "asset_responsibilities", "asset_parcels", "asset_admin_links",
        "land_parcels", "candidate_asset_links", "user_department_access", "candidate_predictions",
        "candidate_ingest_requests", "ingestion_batches", "source_records", "satellite_scenes",
        "processing_runs", "ml_model_versions", "ml_evaluations", "outbox_events",
    ]}).scalars().all()
    assert set(names) == {
        "public_assets", "departments", "asset_responsibilities", "asset_parcels", "asset_admin_links",
        "land_parcels", "candidate_asset_links", "user_department_access", "candidate_predictions",
        "candidate_ingest_requests", "ingestion_batches", "source_records", "satellite_scenes",
        "processing_runs", "ml_model_versions", "ml_evaluations", "outbox_events",
    }


def test_rls_is_enabled_and_forced_on_department_scoped_tables(db):
    rows = db.execute(text("""
      SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
      FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='public' AND c.relname = ANY(:names)
    """), {"names": ["departments", "public_assets", "asset_responsibilities",
                     "asset_parcels", "asset_admin_links", "land_parcels",
                     "candidate_asset_links", "candidate_predictions", "candidate_ingest_requests", "user_department_access", "ingestion_batches", "source_records", "satellite_scenes", "processing_runs", "ml_model_versions", "ml_evaluations", "outbox_events"]}).all()
    assert len(rows) == 17
    assert all(row.relrowsecurity and row.relforcerowsecurity for row in rows)


def test_database_request_context_helpers_read_transaction_local_scope(db):
    db.execute(text("""
      SELECT set_config('lp.user_id','731',true),
             set_config('lp.is_platform_admin','false',true),
             set_config('lp.pipeline_ingest','true',true)
    """))
    values = db.execute(text("""
      SELECT lp_current_user_id(), lp_is_platform_admin(), lp_is_pipeline_ingest()
    """)).one()
    assert values == (731, False, True)


def test_department_membership_can_be_revoked_on_its_start_date(db):
    user_id = db.execute(text("""
      INSERT INTO users(username,name,role,is_demo)
      VALUES ('rls-test-user','RLS Test','analyst',true) RETURNING id
    """)).scalar_one()
    department_id = db.execute(text("""
      INSERT INTO departments(code,name) VALUES ('RLS_TEST','RLS Test Department') RETURNING id
    """)).scalar_one()
    db.execute(text("""
      INSERT INTO user_department_access(user_id,department_id,access_level,valid_from,valid_to)
      VALUES (:user_id,:department_id,'READ',CURRENT_DATE,CURRENT_DATE)
    """), {"user_id": user_id, "department_id": department_id})
    active = db.scalar(text("""
      SELECT count(*) FROM user_department_access
      WHERE user_id=:user_id AND valid_to > CURRENT_DATE
    """), {"user_id": user_id})
    assert active == 0
