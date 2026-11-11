"""Stable contracts for the statewide public-asset registry."""
from datetime import date
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class AssetCreate(BaseModel):
    asset_code: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    display_name: str = Field(min_length=2, max_length=240)
    category_code: str = Field(min_length=2, max_length=80)
    baseline_date: date | None = None
    source_authority: str = "UNVERIFIED"
    source_record_ref: str | None = Field(default=None, max_length=500)

class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    asset_code: str
    display_name: str
    category_code: str
    lifecycle_status: str
    baseline_date: date | None
    source_authority: str

class ResponsibilityCreate(BaseModel):
    department_id: UUID
    relationship_type: str
    valid_from: date
    valid_to: date | None = None
    source_authority: str
    source_record_ref: str = Field(min_length=1, max_length=500)
