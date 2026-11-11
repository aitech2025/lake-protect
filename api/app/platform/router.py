"""Versioned statewide platform APIs. Existing prototype endpoints remain supported."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User
from app.platform.schemas import AssetCreate, ResponsibilityCreate
from app.security import current_user, require_roles

router = APIRouter(prefix="/api/v1/platform", tags=["platform-registry"])

@router.get("/assets")
def list_assets(category: str | None = None, limit: int = Query(100, ge=1, le=500),
                offset: int = Query(0, ge=0), _: User = Depends(current_user),
                db: Session = Depends(get_db)):
    rows = db.execute(text("""
      SELECT id,asset_code,display_name,category_code,lifecycle_status,baseline_date,source_authority
      FROM public_assets WHERE (:category IS NULL OR category_code=:category)
      ORDER BY asset_code LIMIT :limit OFFSET :offset
    """), {"category":category,"limit":limit,"offset":offset}).mappings()
    return {"items":[dict(row) for row in rows],"limit":limit,"offset":offset}

@router.post("/assets", status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, _: User = Depends(require_roles("admin")),
                 db: Session = Depends(get_db)):
    try:
        row = db.execute(text("""
          INSERT INTO public_assets(asset_code,display_name,category_code,baseline_date,source_authority,source_record_ref)
          VALUES (:asset_code,:display_name,:category_code,:baseline_date,:source_authority,:source_record_ref)
          RETURNING id,asset_code,display_name,category_code,lifecycle_status,baseline_date,source_authority
        """),payload.model_dump()).mappings().one()
        db.commit()
        return dict(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409,detail="Asset code already exists or registry constraint failed.") from exc

@router.get("/assets/{asset_id}")
def get_asset(asset_id: str, _: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.execute(text("""
      SELECT id,asset_code,display_name,category_code,lifecycle_status,baseline_date,source_authority,
             source_record_ref,ST_AsGeoJSON(footprint)::json AS footprint
      FROM public_assets WHERE id=:asset_id
    """),{"asset_id":asset_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404,detail="Asset not found")
    return dict(row)

@router.post("/assets/{asset_id}/responsibilities",status_code=status.HTTP_201_CREATED)
def add_responsibility(asset_id: str,payload: ResponsibilityCreate,
                       _: User = Depends(require_roles("admin","nodal_officer")),db: Session = Depends(get_db)):
    try:
        row=db.execute(text("""
          INSERT INTO asset_responsibilities(asset_id,department_id,relationship_type,valid_from,valid_to,source_authority,source_record_ref)
          VALUES (:asset_id,:department_id,:relationship_type,:valid_from,:valid_to,:source_authority,:source_record_ref)
          RETURNING id,asset_id,department_id,relationship_type,valid_from,valid_to
        """),{"asset_id":asset_id,**payload.model_dump()}).mappings().one()
        db.commit()
        return dict(row)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409,detail="Asset or department reference is invalid.") from exc

@router.get("/departments")
def list_departments(_: User = Depends(current_user),db: Session = Depends(get_db)):
    rows=db.execute(text("SELECT id,code,name,parent_id,is_active FROM departments WHERE is_active ORDER BY name")).mappings()
    return {"items":[dict(row) for row in rows]}
