"""Lead intake, inbox, acceptance, and decline endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import (
    get_current_firm_staff,
    get_current_user,
    get_optional_current_user,
)
from app.models import Lead, LeadAttachment, LeadStatus, User, UserRole
from app.schemas.case import (
    CaseDetailRead,
    FirmCaseDetailRead,
    PlaintiffCaseDetailRead,
)
from app.schemas.lead import (
    LeadAttachmentRead,
    LeadCreate,
    LeadFilterParams,
    LeadRead,
)
from app.search import region_search_terms
from app.services.case_service import (
    get_case_detail,
    get_case_for_lead,
    get_lead_attachment,
    upload_lead_attachment,
)
from app.services.lead_service import accept_lead, create_lead, decline_lead

router = APIRouter(tags=["leads"])


@router.post(
    "/leads",
    response_model=LeadRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_lead(
    payload: LeadCreate,
    db: Annotated[Session, Depends(get_db)],
    authenticated_user: Annotated[User | None, Depends(get_optional_current_user)],
) -> Lead:
    """Submit public intake or an authenticated plaintiff's own lead."""
    return create_lead(db, payload, authenticated_user)


@router.get("/leads", response_model=list[LeadRead])
def list_leads(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    filters: Annotated[LeadFilterParams, Depends()],
    response: Response,
    search: Annotated[str | None, Query(min_length=2, max_length=200)] = None,
    assigned_firm_id: Annotated[int | None, Query(gt=0)] = None,
    exclude_accepted: bool = False,
) -> list[Lead]:
    """List leads within the caller's ownership, firm inbox, or admin scope."""
    statement = select(Lead).options(
        selectinload(Lead.plaintiff),
        selectinload(Lead.assigned_firm),
        selectinload(Lead.attachments).selectinload(LeadAttachment.uploaded_by),
    )
    if assigned_firm_id is not None and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Firm assignment filters are available to administrators only.",
        )
    if exclude_accepted and current_user.role not in {
        UserRole.ADMIN,
        UserRole.PLAINTIFF,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lead conversion filters are available to administrators and plaintiffs.",
        )
    if current_user.role == UserRole.PLAINTIFF:
        statement = statement.where(Lead.plaintiff_id == current_user.id)
        if exclude_accepted:
            statement = statement.where(Lead.status != LeadStatus.ACCEPTED)
    elif current_user.role in {UserRole.ATTORNEY, UserRole.PARALEGAL}:
        if current_user.law_firm_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The staff account is not associated with a law firm.",
            )
        if filters.status not in (None, LeadStatus.PENDING_REVIEW):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Firm inboxes can only be filtered to pending-review leads.",
            )
        statement = statement.where(
            Lead.assigned_firm_id == current_user.law_firm_id,
            Lead.status == LeadStatus.PENDING_REVIEW,
        )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to list leads.",
        )
    elif current_user.role == UserRole.ADMIN:
        if exclude_accepted:
            statement = statement.where(Lead.status != LeadStatus.ACCEPTED)
        if assigned_firm_id is not None:
            statement = statement.where(Lead.assigned_firm_id == assigned_firm_id)

    if search is not None:
        pattern = f"%{search.strip()}%"
        region_patterns = [
            Lead.region.ilike(f"%{term}%") for term in region_search_terms(search)
        ]
        statement = statement.join(User, User.id == Lead.plaintiff_id).where(
            or_(
                Lead.title.ilike(pattern),
                Lead.category.ilike(pattern),
                *region_patterns,
                Lead.description.ilike(pattern),
                User.name.ilike(pattern),
                User.email.ilike(pattern),
            )
        )

    if filters.status is not None and current_user.role not in {
        UserRole.ATTORNEY,
        UserRole.PARALEGAL,
    }:
        statement = statement.where(Lead.status == filters.status)
    if filters.category is not None:
        statement = statement.where(Lead.category.ilike(filters.category))
    if filters.region is not None:
        statement = statement.where(Lead.region.ilike(filters.region))
    total = db.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    ) or 0
    response.headers["X-Total-Count"] = str(total)
    return list(
        db.scalars(
            statement.order_by(Lead.created_at.desc(), Lead.id.desc())
            .limit(filters.limit)
            .offset(filters.offset)
        )
        .unique()
        .all()
    )


@router.get("/leads/{lead_id}/case", response_model=None)
def get_accepted_case_for_lead(
    lead_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CaseDetailRead | FirmCaseDetailRead | PlaintiffCaseDetailRead:
    """Open an accepted lead's case without requiring a separate case ID."""
    return get_case_for_lead(db, lead_id, current_user)


@router.post(
    "/leads/{lead_id}/attachments",
    response_model=LeadAttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_lead_file(
    lead_id: int,
    file: UploadFile,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LeadAttachment:
    """Attach a PDF to an owned or currently assigned lead."""
    return await upload_lead_attachment(db, lead_id, current_user, file)


@router.get("/leads/{lead_id}/attachments/{attachment_id}")
def download_lead_file(
    lead_id: int,
    attachment_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    """Download a lead PDF after verifying current lead visibility."""
    attachment, path = get_lead_attachment(
        db, lead_id, attachment_id, current_user
    )
    return FileResponse(
        path=path,
        media_type="application/pdf",
        filename=attachment.file_name,
        content_disposition_type="attachment",
        headers={"Cache-Control": "private, no-store"},
    )


@router.post(
    "/leads/{lead_id}/accept",
    response_model=FirmCaseDetailRead,
    status_code=status.HTTP_201_CREATED,
)
def accept(
    lead_id: int,
    db: Annotated[Session, Depends(get_db)],
    staff_user: Annotated[User, Depends(get_current_firm_staff)],
) -> FirmCaseDetailRead:
    """Accept an assigned pending lead and return its newly created case."""
    case = accept_lead(db, lead_id, staff_user)
    return get_case_detail(db, case.id, staff_user)  # type: ignore[return-value]


@router.post("/leads/{lead_id}/decline", response_model=LeadRead)
def decline(
    lead_id: int,
    db: Annotated[Session, Depends(get_db)],
    staff_user: Annotated[User, Depends(get_current_firm_staff)],
) -> Lead:
    """Decline a lead while preserving it for later administrative reassignment."""
    return decline_lead(db, lead_id, staff_user)
