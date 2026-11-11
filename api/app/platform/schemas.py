"""Validated contracts for statewide registry and department administration."""
from datetime import date
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

AuthorityClass = Literal["AUTHORITATIVE","CERTIFIED","DERIVED","EXTERNAL","FIELD","MODEL","UNVERIFIED"]
RelationshipType = Literal["OWNER","CUSTODIAN","POSSESSOR","JURISDICTION","OPERATIONAL","ENFORCEMENT","DATA_STEWARD"]

class AssetCreate(BaseModel):
    asset_code: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    display_name: str = Field(min_length=2, max_length=240)
    category_code: str = Field(min_length=2, max_length=80)
    baseline_date: date | None = None
    source_authority: AuthorityClass = "UNVERIFIED"
    source_record_ref: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def authoritative_source_required(self):
        if self.source_authority in {"AUTHORITATIVE","CERTIFIED"} and not self.source_record_ref:
            raise ValueError("Authoritative or certified assets require a source record reference.")
        return self

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
    relationship_type: RelationshipType
    valid_from: date
    valid_to: date | None = None
    source_authority: AuthorityClass
    source_record_ref: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def valid_interval(self):
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to must not be earlier than valid_from.")
        if self.source_authority in {"AUTHORITATIVE","CERTIFIED"} and not self.source_record_ref:
            raise ValueError("Authoritative relationships require a source record reference.")
        return self

class DepartmentCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=2, max_length=240)
    parent_id: UUID | None = None

class DepartmentAccessCreate(BaseModel):
    access_level: Literal["READ","CONTRIBUTE","MANAGE"] = "READ"
    valid_from: date = Field(default_factory=date.today)
