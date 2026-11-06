"""Case, document, and firm-private note schemas."""

from datetime import datetime

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.models.enums import CaseStatus, LeadStatus
from app.schemas.common import LawFirmRead, UserSummary
from app.schemas.lead import LeadRead


class CaseStatusUpdate(BaseModel):
    """Request payload for changing a case's workflow status."""

    status: CaseStatus


class DocumentRead(BaseModel):
    """Document metadata without exposing its storage path."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    uploaded_by_id: int | None
    file_name: str
    file_size_bytes: int
    mime_type: str
    created_at: datetime
    uploader: UserSummary | None = Field(
        default=None,
        validation_alias=AliasChoices("uploaded_by", "uploader"),
    )


class NoteCreate(BaseModel):
    """Request payload for creating a firm-private case note."""

    content: str = Field(..., min_length=1)

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, value: object) -> object:
        """Reject whitespace-only notes after trimming surrounding whitespace."""
        return value.strip() if isinstance(value, str) else value


class NoteRead(BaseModel):
    """Private case note with its authoring firm identified."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    author_id: int | None
    author_firm_id: int
    content: str
    created_at: datetime
    author: UserSummary | None = None


class CaseDetailRead(BaseModel):
    """Firm/admin case detail; notes must be filtered by the caller's policy."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    assigned_firm_id: int
    status: CaseStatus
    created_at: datetime
    updated_at: datetime
    lead: LeadRead
    documents: list[DocumentRead] = Field(default_factory=list)
    notes: list[NoteRead] = Field(default_factory=list)


class FirmCaseDetailRead(CaseDetailRead):
    """Case detail for staff, containing only notes filtered to their firm."""


class PlaintiffCaseDetailRead(BaseModel):
    """Plaintiff-visible case detail that has no field capable of exposing notes."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    assigned_firm_id: int
    status: CaseStatus
    created_at: datetime
    updated_at: datetime
    lead: LeadRead
    documents: list[DocumentRead] = Field(default_factory=list)


class CaseLeadSummaryRead(BaseModel):
    """Lead fields needed to identify a case in a directory row."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    plaintiff_id: int
    title: str
    category: str
    region: str
    status: LeadStatus
    assigned_firm_id: int | None
    created_at: datetime
    updated_at: datetime
    plaintiff: UserSummary | None = None
    assigned_firm: LawFirmRead | None = None


class CaseListRead(BaseModel):
    """Compact case directory result without unbounded notes or documents."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    assigned_firm_id: int
    status: CaseStatus
    created_at: datetime
    updated_at: datetime
    lead: CaseLeadSummaryRead
    document_count: int
