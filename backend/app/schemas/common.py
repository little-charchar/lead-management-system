"""Shared Pydantic schemas used across the API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import UserRole


class UserSummary(BaseModel):
    """Public user identity fields safe to embed in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: UserRole
    law_firm_id: int | None


class DocumentUploaderRead(BaseModel):
    """Uploader identity with firm attribution for shared document history."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    role: UserRole
    law_firm_id: int | None
    law_firm_name: str | None = None


class LawFirmRead(BaseModel):
    """Read-only law firm representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
