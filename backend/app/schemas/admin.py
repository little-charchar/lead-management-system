"""Administrative request and audit-history schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AuditAction
from app.schemas.common import UserSummary


class ReassignLeadRequest(BaseModel):
    """Request payload to assign a lead to a law firm."""

    target_firm_id: int = Field(
        ...,
        gt=0,
        description="ID of the law firm to assign this lead to",
    )


class ReassignCaseRequest(BaseModel):
    """Request payload to reassign a case to another law firm."""

    target_firm_id: int = Field(
        ...,
        gt=0,
        description="ID of the new law firm taking over the case",
    )


class AuditLogRead(BaseModel):
    """Read-only audit event with before-and-after entity state."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    actor_id: int | None
    action: AuditAction
    previous_state: dict[str, Any] | None
    new_state: dict[str, Any]
    created_at: datetime
    actor: UserSummary | None = None
