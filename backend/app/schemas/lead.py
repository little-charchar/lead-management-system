"""Lead request and response schemas."""

from datetime import datetime

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from app.models.enums import LeadStatus
from app.schemas.common import DocumentUploaderRead, LawFirmRead, UserSummary

MAX_LEAD_DESCRIPTION_WORDS = 1000


class LeadAttachmentRead(BaseModel):
    """Read-only metadata for a PDF attached to a lead."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    uploaded_by_id: int | None
    file_name: str
    file_size_bytes: int
    mime_type: str
    created_at: datetime
    uploader: DocumentUploaderRead | None = Field(
        default=None,
        validation_alias=AliasChoices("uploaded_by", "uploader"),
    )


class LeadCreate(BaseModel):
    """Validated plaintiff-submitted lead information."""

    plaintiff_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    title: str = Field(default="Legal inquiry", min_length=3, max_length=200)
    category: str = Field(..., min_length=2, max_length=100)
    region: str = Field(..., min_length=2, max_length=50)
    description: str = Field(..., min_length=1, max_length=20_000)

    @field_validator(
        "plaintiff_name", "title", "category", "region", "description", mode="before"
    )
    @classmethod
    def strip_text(cls, value: object) -> object:
        """Trim surrounding whitespace before applying length validation."""
        return value.strip() if isinstance(value, str) else value

    @field_validator("description")
    @classmethod
    def limit_description_words(cls, value: str) -> str:
        """Keep lead narratives within a reasonable 1,000-word limit."""
        if len(value.split()) > MAX_LEAD_DESCRIPTION_WORDS:
            raise ValueError(
                f"Details must be {MAX_LEAD_DESCRIPTION_WORDS} words or fewer."
            )
        return value


class LeadRead(BaseModel):
    """Lead details suitable for plaintiff, firm, or admin responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    plaintiff_id: int
    title: str
    category: str
    region: str
    description: str
    status: LeadStatus
    assigned_firm_id: int | None
    created_at: datetime
    updated_at: datetime
    plaintiff: UserSummary | None = None
    assigned_firm: LawFirmRead | None = None
    attachments: list[LeadAttachmentRead] = Field(default_factory=list)


class LeadFilterParams(BaseModel):
    """Validated optional filters and pagination for lead inbox queries."""

    status: LeadStatus | None = None
    category: str | None = Field(default=None, min_length=2, max_length=100)
    region: str | None = Field(default=None, min_length=2, max_length=50)
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
