from sqlalchemy import text

from tests.factories import make_asset, make_user


def test_department_rls_scopes_canonical_and_legacy_assets(db):
    user = make_user(db, "analyst")
    asset_a = make_asset(db)
    asset_b = make_asset(db)

    dept_a = db.execute(text("""
      INSERT INTO departments(code,name) VALUES ('RLS-DEPT-A','RLS Department A')
      RETURNING id
    """)).scalar_one()
    dept_b = db.execute(text("""
      INSERT INTO departments(code,name) VALUES ('RLS-DEPT-B','RLS Department B')
      RETURNING id
    """)).scalar_one()

    canonical_a = db.execute(text("""
      INSERT INTO public_assets(asset_code,display_name,category_code,legacy_asset_id,baseline_date,
                                source_authority,source_record_ref)
      VALUES (:code,:name,'lake',:legacy_id,CURRENT_DATE,'DERIVED',:source)
      RETURNING id
    """), {"code":f"RLS-A-{asset_a.id}","name":asset_a.name,"legacy_id":asset_a.id,"source":f"test:{asset_a.id}"}).scalar_one()
    canonical_b = db.execute(text("""
      INSERT INTO public_assets(asset_code,display_name,category_code,legacy_asset_id,baseline_date,
                                source_authority,source_record_ref)
      VALUES (:code,:name,'lake',:legacy_id,CURRENT_DATE,'DERIVED',:source)
      RETURNING id
    """), {"code":f"RLS-B-{asset_b.id}","name":asset_b.name,"legacy_id":asset_b.id,"source":f"test:{asset_b.id}"}).scalar_one()

    for canonical_id, department_id in ((canonical_a, dept_a), (canonical_b, dept_b)):
        db.execute(text("""
          INSERT INTO asset_responsibilities(asset_id,department_id,relationship_type,valid_from,
                                             source_authority,source_record_ref)
          VALUES (:asset_id,:department_id,'CUSTODIAN',CURRENT_DATE,'DERIVED','test-assignment')
        """), {"asset_id":canonical_id,"department_id":department_id})
    db.execute(text("""
      INSERT INTO user_department_access(user_id,department_id,access_level,valid_from)
      VALUES (:user_id,:department_id,'READ',CURRENT_DATE)
    """), {"user_id":user.id,"department_id":dept_a})
    db.flush()

    # The test connection is normally a superuser/table owner. Switch to a
    # NOLOGIN, non-owner, non-BYPASSRLS role so assertions exercise real RLS.
    db.execute(text("SET LOCAL ROLE lakeprotect_rls_test"))
    db.execute(text("""
      SELECT set_config('lp.user_id',:user_id,true),
             set_config('lp.is_platform_admin','false',true),
             set_config('lp.is_auditor','false',true),
             set_config('lp.pipeline_ingest','false',true)
    """), {"user_id":str(user.id)})

    canonical_codes = set(db.scalars(text("SELECT asset_code FROM public_assets")).all())
    legacy_ids = set(db.scalars(text("SELECT id FROM assets")).all())
    boundary_asset_ids = set(db.scalars(text("SELECT DISTINCT asset_id FROM boundaries")).all())

    assert canonical_codes == {f"RLS-A-{asset_a.id}"}
    assert legacy_ids == {asset_a.id}
    assert boundary_asset_ids == {asset_a.id}


def test_legacy_operational_tables_force_row_security(db):
    names = [
        "assets","boundaries","candidates","observations","legal_checks","alerts",
        "permits","authorised_works","court_cases","closure_requests","field_checks",
        "owner_claims","readiness_items","evidence_packs","officer_records",
        "imagery_requests","signals","audit_log","bulletins",
    ]
    rows = db.execute(text("""
      SELECT relname,relrowsecurity,relforcerowsecurity
      FROM pg_class
      WHERE relnamespace='public'::regnamespace AND relname=ANY(:names)
    """), {"names":names}).all()
    assert len(rows) == len(names)
    assert all(row.relrowsecurity and row.relforcerowsecurity for row in rows)


def test_auditor_context_is_transaction_local(db):
    db.execute(text("SELECT set_config('lp.is_auditor','true',true)"))
    assert db.scalar(text("SELECT lp_is_auditor()")) is True
