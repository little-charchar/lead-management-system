"""Case access, status, note, and local document storage workflows."""

import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import String, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    AuditAction,
    AuditLog,
    Case,
    CaseStatus,
    Document,
    Lead,
    LeadAttachment,
    Note,
    User,
    UserRole,
)
from app.schemas.case import (
    CaseDetailRead,
    CaseListRead,
    FirmCaseDetailRead,
    NoteCreate,
    NoteRead,
    PlaintiffCaseDetailRead,
)
from app.search import region_search_terms

UPLOAD_DIRECTORY = Path(
    os.getenv(
        "UPLOAD_DIRECTORY",
        str(Path(__file__).resolve().parents[2] / "uploads"),
    )
).resolve()
MAX_DOCUMENT_BYTES = 25 * 1024 * 1024


def _load_case(db: Session, case_id: int) -> Case:
    """Load case metadata and response relationships, or return 404."""
    case = db.scalar(
        select(Case)
        .where(Case.id == case_id)
        .options(
            selectinload(Case.lead).selectinload(Lead.plaintiff),
            selectinload(Case.lead).selectinload(Lead.assigned_firm),
            selectinload(Case.lead)
            .selectinload(Lead.attachments)
            .selectinload(LeadAttachment.uploaded_by)
            .selectinload(User.law_firm),
            selectinload(Case.documents)
            .selectinload(Document.uploaded_by)
            .selectinload(User.law_firm),
        )
    )
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found."
        )
    return case


def _check_case_access(case: Case, user: User) -> None:
    """Enforce current assignment or plaintiff ownership for a case."""
    if user.role == UserRole.PLAINTIFF:
        if case.lead.plaintiff_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this case.",
            )
    elif user.role in {UserRole.ATTORNEY, UserRole.PARALEGAL}:
        if user.law_firm_id is None or case.assigned_firm_id != user.law_firm_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This case is not currently assigned to your law firm.",
            )
    elif user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this case.",
        )


def _document_visible_in_case(case: Case, document: Document, user: User) -> bool:
    """Limit case document metadata to the plaintiff and firms entitled to it."""
    if user.role == UserRole.ADMIN:
        return True
    if user.role == UserRole.PLAINTIFF:
        return (
            case.lead.plaintiff_id == user.id
            and (
                document.uploaded_by is not None
                and document.uploaded_by.role
                in {UserRole.PLAINTIFF, UserRole.ADMIN}
                or document.uploaded_by_firm_id == case.assigned_firm_id
            )
        )
    if user.role in {UserRole.ATTORNEY, UserRole.PARALEGAL}:
        return (
            document.uploaded_by is not None
            and document.uploaded_by.role in {UserRole.PLAINTIFF, UserRole.ADMIN}
        ) or document.uploaded_by_firm_id == user.law_firm_id
    return False


def _can_download_case_document(case: Case, document: Document, user: User) -> bool:
    """Authorize a case document while preserving former firms' own-file access."""
    if user.role == UserRole.ADMIN:
        return True
    if user.role == UserRole.PLAINTIFF:
        return (
            case.lead.plaintiff_id == user.id
            and _document_visible_in_case(case, document, user)
        )
    if user.role in {UserRole.ATTORNEY, UserRole.PARALEGAL}:
        return (
            user.law_firm_id == document.uploaded_by_firm_id
            or (
                user.law_firm_id == case.assigned_firm_id
                and _document_visible_in_case(case, document, user)
            )
        )
    return False


def get_case_detail(db: Session, case_id: int, user: User) -> (
    PlaintiffCaseDetailRead | FirmCaseDetailRead | CaseDetailRead
):
    """Return a persona-specific case view without exposing out-of-scope notes."""
    case = _load_case(db, case_id)
    _check_case_access(case, user)
    base = {
        "id": case.id,
        "lead_id": case.lead_id,
        "assigned_firm_id": case.assigned_firm_id,
        "status": case.status,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "lead": case.lead,
        "documents": [
            document
            for document in case.documents
            if _document_visible_in_case(case, document, user)
        ],
    }
    if user.role == UserRole.PLAINTIFF:
        return PlaintiffCaseDetailRead.model_validate(base)

    notes_statement = (
        select(Note)
        .where(Note.case_id == case.id)
        .options(selectinload(Note.author))
        .order_by(Note.created_at, Note.id)
    )
    if user.role != UserRole.ADMIN:
        notes_statement = notes_statement.where(
            Note.author_firm_id == user.law_firm_id
        )
    notes = list(db.scalars(notes_statement).all())
    response_data = {**base, "notes": notes}
    if user.role == UserRole.ADMIN:
        return CaseDetailRead.model_validate(response_data)
    return FirmCaseDetailRead.model_validate(response_data)


def get_case_summaries(
    db: Session, case_ids: list[int], user: User
) -> list[CaseListRead]:
    """Load case directory rows without fetching their notes or document records."""
    if not case_ids:
        return []

    cases = db.scalars(
        select(Case)
        .where(Case.id.in_(case_ids))
        .options(
            joinedload(Case.lead).joinedload(Lead.plaintiff),
            joinedload(Case.lead).joinedload(Lead.assigned_firm),
        )
    ).all()
    cases_by_id = {case.id: case for case in cases}
    document_counts = select(Document.case_id, func.count(Document.id)).where(
        Document.case_id.in_(case_ids)
    )
    if user.role != UserRole.ADMIN:
        document_counts = document_counts.outerjoin(
            User, User.id == Document.uploaded_by_id
        ).where(
            or_(
                User.role.in_({UserRole.PLAINTIFF, UserRole.ADMIN}),
                Document.uploaded_by_firm_id == user.law_firm_id,
            )
        )
    counts = dict(
        db.execute(document_counts.group_by(Document.case_id)).all()
    )
    return [
        CaseListRead.model_validate(
            {
                "id": case.id,
                "lead_id": case.lead_id,
                "assigned_firm_id": case.assigned_firm_id,
                "status": case.status,
                "created_at": case.created_at,
                "updated_at": case.updated_at,
                "lead": case.lead,
                "document_count": counts.get(case.id, 0),
            }
        )
        for case_id in case_ids
        if (case := cases_by_id.get(case_id)) is not None
    ]


def list_firm_cases(
    db: Session,
    staff_user: User,
    *,
    search: str | None,
    case_status: CaseStatus | None,
    include_closed: bool,
    offset: int,
    limit: int,
) -> tuple[list[CaseListRead], int]:
    """Return paginated cases assigned to the caller's firm."""
    statement = (
        select(Case.id)
        .join(Lead, Case.lead_id == Lead.id)
        .where(Case.assigned_firm_id == staff_user.law_firm_id)
    )
    if case_status is not None:
        statement = statement.where(Case.status == case_status)
    elif not include_closed:
        statement = statement.where(Case.status != CaseStatus.CLOSED)
    if search:
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
    total = (
        db.scalar(
            select(func.count()).select_from(statement.order_by(None).subquery())
        )
        or 0
    )
    case_ids = list(
        db.scalars(
            statement.order_by(Case.updated_at.desc(), Case.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return get_case_summaries(db, case_ids, staff_user), total


def list_plaintiff_cases(
    db: Session,
    plaintiff: User,
    *,
    search: str | None,
    offset: int,
    limit: int,
) -> tuple[list[CaseListRead], int]:
    """Return one paginated, searchable page of a plaintiff's accepted cases."""
    statement = (
        select(Case.id)
        .join(Lead, Case.lead_id == Lead.id)
        .where(Lead.plaintiff_id == plaintiff.id)
    )
    if search:
        pattern = f"%{search.strip()}%"
        region_patterns = [
            Lead.region.ilike(f"%{term}%") for term in region_search_terms(search)
        ]
        statement = statement.where(
            or_(
                Lead.title.ilike(pattern),
                Lead.category.ilike(pattern),
                *region_patterns,
                Lead.description.ilike(pattern),
                Case.status.cast(String).ilike(pattern),
            )
        )
    total = (
        db.scalar(
            select(func.count()).select_from(statement.order_by(None).subquery())
        )
        or 0
    )
    case_ids = list(
        db.scalars(
            statement.order_by(Case.updated_at.desc(), Case.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return get_case_summaries(db, case_ids, plaintiff), total


def get_case_for_lead(
    db: Session, lead_id: int, user: User
) -> PlaintiffCaseDetailRead | FirmCaseDetailRead | CaseDetailRead:
    """Resolve an accepted lead's case after enforcing current lead visibility."""
    lead = db.scalar(select(Lead).where(Lead.id == lead_id))
    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found."
        )
    if user.role == UserRole.PLAINTIFF:
        if lead.plaintiff_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this lead.",
            )
    elif user.role in {UserRole.ATTORNEY, UserRole.PARALEGAL}:
        if user.law_firm_id is None or lead.assigned_firm_id != user.law_firm_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This lead is not currently assigned to your law firm.",
            )
    elif user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this lead.",
        )

    case_id = db.scalar(select(Case.id).where(Case.lead_id == lead_id))
    if case_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This lead has not been accepted into a case.",
        )
    return get_case_detail(db, case_id, user)


def _check_lead_access(lead: Lead, user: User) -> None:
    """Enforce plaintiff ownership or current firm assignment for lead files."""
    if user.role == UserRole.PLAINTIFF:
        if lead.plaintiff_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this lead.",
            )
    elif user.role in {UserRole.ATTORNEY, UserRole.PARALEGAL}:
        if user.law_firm_id is None or lead.assigned_firm_id != user.law_firm_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This lead is not currently assigned to your law firm.",
            )
    elif user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this lead.",
        )


async def upload_lead_attachment(
    db: Session, lead_id: int, user: User, upload: UploadFile
) -> LeadAttachment:
    """Store an intake PDF with its lead until a case is accepted."""
    destination: Path | None = None
    try:
        lead = db.scalar(select(Lead).where(Lead.id == lead_id).with_for_update())
        if lead is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found."
            )
        _check_lead_access(lead, user)
        directory = UPLOAD_DIRECTORY / "leads" / str(lead.id)
        directory.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid.uuid4()}.pdf"
        destination = directory / stored_name
        file_size = await _write_upload(upload, destination)
        relative_path = destination.relative_to(UPLOAD_DIRECTORY).as_posix()
        original_filename = (upload.filename or stored_name).replace("\\", "/")
        safe_filename = "".join(
            character
            for character in Path(original_filename).name
            if character.isprintable()
        )
        attachment = LeadAttachment(
            lead_id=lead.id,
            uploaded_by_id=user.id,
            file_name=(safe_filename[:255] or stored_name),
            file_path=relative_path,
            file_size_bytes=file_size,
            mime_type="application/pdf",
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)
        return attachment
    except OSError as exc:
        db.rollback()
        if destination is not None:
            destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The lead attachment could not be stored.",
        ) from exc
    except Exception:
        db.rollback()
        if destination is not None:
            destination.unlink(missing_ok=True)
        raise


def get_lead_attachment(
    db: Session, lead_id: int, attachment_id: int, user: User
) -> tuple[LeadAttachment, Path]:
    """Authorize and safely resolve an attachment belonging to a lead."""
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found."
        )
    _check_lead_access(lead, user)
    attachment = db.scalar(
        select(LeadAttachment).where(
            LeadAttachment.id == attachment_id,
            LeadAttachment.lead_id == lead.id,
        )
    )
    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead attachment not found.",
        )
    path = (UPLOAD_DIRECTORY / attachment.file_path).resolve()
    if not path.is_relative_to(UPLOAD_DIRECTORY) or not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead attachment file not found.",
        )
    return attachment, path


def update_case_status(
    db: Session, case_id: int, new_status: CaseStatus, staff_user: User
) -> Case:
    """Set a case to the requested status and record the change."""
    try:
        case = db.scalar(select(Case).where(Case.id == case_id).with_for_update())
        if case is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Case not found."
            )
        _check_case_access(case, staff_user)
        if new_status == case.status:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Case is already in {new_status.value} status.",
            )
        previous_state = {"status": case.status.value}
        case.status = new_status
        db.add(
            AuditLog(
                entity_type="CASE",
                entity_id=case.id,
                actor_id=staff_user.id,
                action=AuditAction.STATUS_CHANGED.value,
                previous_state=previous_state,
                new_state={"status": case.status.value},
            )
        )
        db.commit()
        db.refresh(case)
        return case
    except Exception:
        db.rollback()
        raise


def create_case_note(
    db: Session, case_id: int, payload: NoteCreate, staff_user: User
) -> Note:
    """Create a case note tagged with its author's current firm."""
    try:
        case = db.scalar(select(Case).where(Case.id == case_id).with_for_update())
        if case is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Case not found."
            )
        _check_case_access(case, staff_user)
        if staff_user.role not in {UserRole.ATTORNEY, UserRole.PARALEGAL}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only law-firm staff can create private notes.",
            )
        if staff_user.law_firm_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The staff account is not associated with a law firm.",
            )
        note = Note(
            case_id=case.id,
            author_id=staff_user.id,
            author_firm_id=staff_user.law_firm_id,
            content=payload.content.strip(),
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        return note
    except Exception:
        db.rollback()
        raise


async def _write_upload(upload: UploadFile, destination: Path) -> int:
    """Stream and validate a PDF upload without buffering the whole file."""
    try:
        if upload.content_type != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only application/pdf uploads are accepted.",
            )
        if (
            not upload.filename
            or Path(upload.filename.replace("\\", "/")).suffix.lower() != ".pdf"
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The uploaded file must have a .pdf filename.",
            )

        size = 0
        header = b""
        with destination.open("xb") as output:
            while chunk := await upload.read(1024 * 1024):
                if not header:
                    header = chunk[:5]
                size += len(chunk)
                if size > MAX_DOCUMENT_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="PDF files must be 25 MiB or smaller.",
                    )
                output.write(chunk)
        if not header.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The uploaded content is not a valid PDF file.",
            )
        if size == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The uploaded PDF is empty.",
            )
        return size
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


async def upload_case_document(
    db: Session, case_id: int, user: User, upload: UploadFile
) -> Document:
    """Validate, persist, and register a PDF, removing it if the DB commit fails."""
    destination: Path | None = None
    try:
        case = _load_case(db, case_id)
        _check_case_access(case, user)
        directory = UPLOAD_DIRECTORY / str(case.id)
        directory.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid.uuid4()}.pdf"
        destination = directory / stored_name
        file_size = await _write_upload(upload, destination)
        relative_path = destination.relative_to(UPLOAD_DIRECTORY).as_posix()
        original_filename = (upload.filename or stored_name).replace("\\", "/")
        safe_filename = "".join(
            character
            for character in Path(original_filename).name
            if character.isprintable()
        )
        document = Document(
            case_id=case.id,
            uploaded_by_id=user.id,
            uploaded_by_firm_id=(
                user.law_firm_id
                if user.role in {UserRole.ATTORNEY, UserRole.PARALEGAL}
                else None
            ),
            file_name=(safe_filename[:255] or stored_name),
            file_path=relative_path,
            file_size_bytes=file_size,
            mime_type="application/pdf",
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        return document
    except OSError as exc:
        db.rollback()
        if destination is not None:
            destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The document could not be stored.",
        ) from exc
    except Exception:
        db.rollback()
        if destination is not None:
            destination.unlink(missing_ok=True)
        raise


def get_case_document(
    db: Session, case_id: int, document_id: int, user: User
) -> tuple[Document, Path]:
    """Authorize document access and resolve its path inside the upload root."""
    case = _load_case(db, case_id)
    document = db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.case_id == case.id,
        )
    )
    if user.role in {UserRole.PLAINTIFF, UserRole.ADMIN}:
        _check_case_access(case, user)
    elif user.role in {UserRole.ATTORNEY, UserRole.PARALEGAL} and (
        user.law_firm_id == case.assigned_firm_id
        or (
            document is not None
            and document.uploaded_by_firm_id == user.law_firm_id
        )
    ):
        pass
    else:
        _check_case_access(case, user)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        )
    if not _can_download_case_document(case, document, user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
        )
    path = (UPLOAD_DIRECTORY / document.file_path).resolve()
    if not path.is_relative_to(UPLOAD_DIRECTORY) or not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found."
        )
    return document, path
