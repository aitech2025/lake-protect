"""Versioned statewide registry APIs. Department-level RLS is a follow-on hardening step."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session
from app.audit import chain
from app.db import get_db
from app.models import User
from app.platform.schemas import AssetCreate, ResponsibilityCreate, DepartmentCreate, DepartmentAccessCreate
from app.security import current_user, require_roles

router = APIRouter(prefix="/api/v1/platform", tags=["platform-registry"])

@router.get("/candidate-assets")
def list_candidate_assets(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
                         actor: User = Depends(current_user), db: Session = Depends(get_db)):
    """Unverified reported locations, separate from the registered government asset registry."""
    rows = db.execute(text("""
      SELECT ca.id, ca.candidate_code, ca.display_name, ca.category_hint, ca.district, ca.mandal, ca.village,
             ca.status, ca.created_at, r.ref AS source_report_ref, ca.detection_candidate_id, ca.incident_id,
             ST_AsGeoJSON(ca.footprint)::json AS footprint
      FROM candidate_assets ca JOIN citizen_reports r ON r.id=ca.source_report_id
      WHERE NOT ca.is_demo
      ORDER BY ca.created_at DESC, ca.id LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset}).mappings().all()
    chain.record(db, actor_id=actor.id, action="view.candidate_assets", entity="candidate_asset",
                 details={"count": len(rows), "limit": limit, "offset": offset})
    db.commit()
    return {"items": [dict(row) for row in rows], "limit": limit, "offset": offset,
            "notice": "Candidate locations are unverified intelligence, not registered government assets."}

@router.get("/assets")
def list_assets(category: str | None = None, limit: int = Query(100, ge=1, le=500),
                offset: int = Query(0, ge=0), _: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(text("""
      SELECT id,asset_code,display_name,category_code,lifecycle_status,baseline_date,source_authority
      FROM public_assets WHERE category_code <> 'reported_place'
        AND (:category IS NULL OR category_code=:category)
      ORDER BY asset_code LIMIT :limit OFFSET :offset
    """), {"category":category,"limit":limit,"offset":offset}).mappings()
    return {"items":[dict(row) for row in rows],"limit":limit,"offset":offset}

@router.post("/assets", status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, actor: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    try:
        row = db.execute(text("""
          INSERT INTO public_assets(asset_code,display_name,category_code,baseline_date,source_authority,source_record_ref)
          VALUES (:asset_code,:display_name,:category_code,:baseline_date,:source_authority,:source_record_ref)
          RETURNING id,asset_code,display_name,category_code,lifecycle_status,baseline_date,source_authority
        """),payload.model_dump()).mappings().one()
        chain.record(db, actor_id=actor.id, action="public_asset.created", entity="public_asset",
                     entity_id=row["id"], details={"asset_code":payload.asset_code,"category_code":payload.category_code,
                     "source_authority":payload.source_authority,"source_record_ref":payload.source_record_ref})
        db.commit()
        return dict(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409,detail="Asset code already exists or registry constraint failed.") from exc

@router.get("/assets/{asset_id}")
def get_asset(asset_id: UUID, _: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.execute(text("""
      SELECT id,asset_code,display_name,category_code,lifecycle_status,baseline_date,source_authority,
             source_record_ref,ST_AsGeoJSON(footprint)::json AS footprint
      FROM public_assets WHERE id=:asset_id AND category_code <> 'reported_place'
    """),{"asset_id":str(asset_id)}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404,detail="Asset not found")
    return dict(row)

@router.post("/assets/{asset_id}/responsibilities",status_code=status.HTTP_201_CREATED)
def add_responsibility(asset_id: UUID,payload: ResponsibilityCreate,
                       actor: User = Depends(require_roles("admin")),db: Session = Depends(get_db)):
    try:
        row=db.execute(text("""
          INSERT INTO asset_responsibilities(asset_id,department_id,relationship_type,valid_from,valid_to,source_authority,source_record_ref)
          VALUES (:asset_id,:department_id,:relationship_type,:valid_from,:valid_to,:source_authority,:source_record_ref)
          RETURNING id,asset_id,department_id,relationship_type,valid_from,valid_to
        """),{"asset_id":str(asset_id),**payload.model_dump()}).mappings().one()
        chain.record(db, actor_id=actor.id, action="asset.responsibility_added", entity="public_asset",
                     entity_id=asset_id, details={"department_id":payload.department_id,
                     "relationship_type":payload.relationship_type,"source_authority":payload.source_authority,
                     "source_record_ref":payload.source_record_ref})
        db.commit()
        return dict(row)
    except DBAPIError as exc:
        db.rollback()
        if getattr(exc.orig, "sqlstate", None) == "42501":
            raise HTTPException(status_code=403,detail="Your department scope does not permit this responsibility change.") from exc
        if isinstance(exc, IntegrityError):
            raise HTTPException(status_code=409,detail="Asset or department reference is invalid.") from exc
        raise

@router.get("/departments")
def list_departments(_: User = Depends(current_user),db: Session = Depends(get_db)):
    rows=db.execute(text("SELECT id,code,name,parent_id,is_active FROM departments WHERE is_active ORDER BY name")).mappings()
    return {"items":[dict(row) for row in rows]}

@router.post("/departments",status_code=status.HTTP_201_CREATED)
def create_department(payload: DepartmentCreate,actor: User = Depends(require_roles("admin")),db: Session = Depends(get_db)):
    try:
        row=db.execute(text("""
          INSERT INTO departments(code,name,parent_id) VALUES (:code,:name,:parent_id)
          RETURNING id,code,name,parent_id,is_active
        """),payload.model_dump()).mappings().one()
        chain.record(db, actor_id=actor.id, action="department.created", entity="department",
                     entity_id=row["id"], details={"code":payload.code})
        db.commit()
        return dict(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409,detail="Department code or parent reference is invalid.") from exc

@router.post("/departments/{department_id}/members/{user_id}",status_code=status.HTTP_201_CREATED)
def grant_department_access(department_id: UUID,user_id: int,payload: DepartmentAccessCreate,
                            actor: User = Depends(require_roles("admin")),db: Session = Depends(get_db)):
    try:
        row=db.execute(text("""
          INSERT INTO user_department_access(user_id,department_id,access_level,valid_from,granted_by)
          VALUES (:user_id,:department_id,:access_level,:valid_from,:granted_by)
          ON CONFLICT (user_id,department_id,valid_from) DO NOTHING
          RETURNING id,user_id,department_id,access_level,valid_from,valid_to
        """),{"user_id":user_id,"department_id":str(department_id),**payload.model_dump(),"granted_by":actor.id}).mappings().first()
        if row is None:
            row=db.execute(text("""
              SELECT id,user_id,department_id,access_level,valid_from,valid_to
              FROM user_department_access
              WHERE user_id=:user_id AND department_id=:department_id AND valid_from=:valid_from
            """),{"user_id":user_id,"department_id":str(department_id),"valid_from":payload.valid_from}).mappings().one()
        else:
            chain.record(db, actor_id=actor.id, action="department.access_granted", entity="department",
                         entity_id=department_id, details={"user_id":user_id,"access_level":payload.access_level,
                         "valid_from":payload.valid_from})
        db.commit()
        return dict(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=404,detail="User or department not found.") from exc

@router.delete("/departments/{department_id}/members/{user_id}",status_code=status.HTTP_204_NO_CONTENT)
def revoke_department_access(department_id: UUID,user_id: int,actor: User = Depends(require_roles("admin")),db: Session = Depends(get_db)):
    revoked=db.execute(text("""
      UPDATE user_department_access
      SET valid_to=GREATEST(CURRENT_DATE,valid_from)
      WHERE department_id=:department_id AND user_id=:user_id AND valid_to IS NULL
      RETURNING valid_from,valid_to
    """),{"department_id":str(department_id),"user_id":user_id}).mappings().all()
    if not revoked:
        db.rollback()
        raise HTTPException(status_code=404,detail="Active or scheduled department membership not found.")
    chain.record(db, actor_id=actor.id, action="department.access_revoked", entity="department",
                 entity_id=department_id, details={"user_id":user_id,
                 "intervals":[{"valid_from":r["valid_from"],"valid_to":r["valid_to"]} for r in revoked]})
    db.commit()
    return None

@router.get("/assets/{asset_id}/responsibilities")
def list_asset_responsibilities(asset_id: UUID, _: User = Depends(current_user), db: Session = Depends(get_db)):
    rows=db.execute(text("""
      SELECT id,department_id,relationship_type,valid_from,valid_to,source_authority,source_record_ref,recorded_at
      FROM asset_responsibilities
      WHERE asset_id=:asset_id AND valid_from<=CURRENT_DATE
        AND (valid_to IS NULL OR valid_to>CURRENT_DATE)
      ORDER BY relationship_type,valid_from DESC
    """),{"asset_id":str(asset_id)}).mappings()
    return {"items":[dict(row) for row in rows]}

@router.get("/candidates/{candidate_id}/predictions")
def list_candidate_predictions(candidate_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    rows=db.execute(text("""
      SELECT id,candidate_id,score_type,score,model_name,model_version,feature_schema_version,
             features,factors,disclaimer,generated_at
      FROM candidate_predictions WHERE candidate_id=:candidate_id
      ORDER BY generated_at DESC
    """),{"candidate_id":candidate_id}).mappings()
    items=[dict(row) for row in rows]
    if not items:
        raise HTTPException(status_code=404,detail="No prediction is available in your department scope.")
    return {"items":items}
