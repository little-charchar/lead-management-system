"""Case detail, workflow, private-note, and document endpoints."""

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from fastapi import Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import (
    get_current_firm_staff,
    get_current_plaintiff,
    get_current_user,
)
from app.models import User, UserRole
from app.models.enums import CaseStatus
from app.schemas.case import (
    CaseDetailRead,
    CaseListRead,
    CaseStatusUpdate,
    DocumentRead,
    FirmCaseDetailRead,
    NoteCreate,
    NoteRead,
    PlaintiffCaseDetailRead,
)
from app.services.case_service import (
    create_case_note,
    get_case_detail,
    get_case_document,
    list_firm_cases,
    list_plaintiff_cases,
    update_case_status,
    upload_case_document,
)

router = APIRouter(tags=["cases"])


@router.get("/cases/mine", response_model=list[CaseListRead])
def list_my_cases(
    db: Annotated[Session, Depends(get_db)],
    plaintiff: Annotated[User, Depends(get_current_plaintiff)],
    response: Response,
    search: Annotated[str | None, Query(min_length=2, max_length=200)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> list[CaseListRead]:
    """Return one searchable page of the authenticated plaintiff's cases."""
    records, total = list_plaintiff_cases(
        db,
        plaintiff,
        search=search,
        offset=offset,
        limit=limit,
    )
    response.headers["X-Total-Count"] = str(total)
    return records


@router.get("/cases", response_model=list[CaseListRead])
def list_cases(
    db: Annotated[Session, Depends(get_db)],
    staff_user: Annotated[User, Depends(get_current_firm_staff)],
    response: Response,
    search: Annotated[str | None, Query(min_length=2, max_length=200)] = None,
    case_status: Annotated[CaseStatus | None, Query(alias="status")] = None,
    include_closed: bool = False,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> list[CaseListRead]:
    """List assigned cases with optional status and text filters."""
    records, total = list_firm_cases(
        db,
        staff_user,
        search=search,
        case_status=case_status,
        include_closed=include_closed,
        offset=offset,
        limit=limit,
    )
    response.headers["X-Total-Count"] = str(total)
    return records


@router.get("/cases/{case_id}", response_model=None)
def read_case(
    case_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CaseDetailRead | FirmCaseDetailRead | PlaintiffCaseDetailRead:
    """Return only the case fields and notes permitted for the current persona."""
    return get_case_detail(db, case_id, current_user)


@router.patch("/cases/{case_id}/status", response_model=FirmCaseDetailRead)
def change_case_status(
    case_id: int,
    payload: CaseStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    staff_user: Annotated[User, Depends(get_current_firm_staff)],
) -> FirmCaseDetailRead:
    """Advance the status of a case currently assigned to the caller's firm."""
    case = update_case_status(db, case_id, payload.status, staff_user)
    return get_case_detail(db, case.id, staff_user)  # type: ignore[return-value]


@router.post(
    "/cases/{case_id}/notes",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
)
def add_note(
    case_id: int,
    payload: NoteCreate,
    db: Annotated[Session, Depends(get_db)],
    staff_user: Annotated[User, Depends(get_current_firm_staff)],
) -> NoteRead:
    """Add a note visible only to the firm that authored it and to admins."""
    return NoteRead.model_validate(create_case_note(db, case_id, payload, staff_user))


@router.post(
    "/cases/{case_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    case_id: int,
    file: UploadFile,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentRead:
    """Upload a validated PDF for a case the current user can access."""
    if current_user.role not in {
        UserRole.PLAINTIFF,
        UserRole.ATTORNEY,
        UserRole.PARALEGAL,
        UserRole.ADMIN,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to upload case documents.",
        )
    document = await upload_case_document(db, case_id, current_user, file)
    return DocumentRead.model_validate(document)


@router.get("/cases/{case_id}/documents/{document_id}")
def download_document(
    case_id: int,
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    """Stream a case PDF after checking current case visibility."""
    document, path = get_case_document(db, case_id, document_id, current_user)
    return FileResponse(
        path=path,
        media_type="application/pdf",
        filename=document.file_name,
        content_disposition_type="attachment",
        headers={"Cache-Control": "private, no-store"},
    )
