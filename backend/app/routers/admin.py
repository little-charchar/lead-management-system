"""Administrative firm reassignment and audit endpoints."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models import CaseStatus, LawFirm, User
from app.schemas.case import CaseDetailRead, CaseListRead
from app.schemas.admin import (
    AuditLogRead,
    ReassignCaseRequest,
    ReassignLeadRequest,
)
from app.schemas.common import LawFirmRead
from app.schemas.lead import LeadRead
from app.services.admin_service import (
    list_audit_logs,
    list_admin_cases,
    reassign_case,
    reassign_lead,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/cases", response_model=list[CaseListRead])
def list_cases_endpoint(
    db: Annotated[Session, Depends(get_db)],
    admin_user: Annotated[User, Depends(get_current_admin)],
    response: Response,
    search: Annotated[str | None, Query(min_length=2, max_length=200)] = None,
    case_status: Annotated[CaseStatus | None, Query(alias="status")] = None,
    firm_id: Annotated[int | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CaseListRead]:
    """Search cases across all firms and statuses for system oversight."""
    records, total = list_admin_cases(
        db,
        admin_user,
        search=search,
        case_status=case_status,
        firm_id=firm_id,
        limit=limit,
        offset=offset,
    )
    response.headers["X-Total-Count"] = str(total)
    return records


@router.post("/leads/{lead_id}/reassign", response_model=LeadRead)
def reassign_lead_endpoint(
    lead_id: int,
    payload: ReassignLeadRequest,
    db: Annotated[Session, Depends(get_db)],
    admin_user: Annotated[User, Depends(get_current_admin)],
) -> LeadRead:
    """Assign a lead to a firm and write the corresponding audit event."""
    return LeadRead.model_validate(
        reassign_lead(db, lead_id, payload.target_firm_id, admin_user)
    )


@router.post("/cases/{case_id}/reassign")
def reassign_case_endpoint(
    case_id: int,
    payload: ReassignCaseRequest,
    db: Annotated[Session, Depends(get_db)],
    admin_user: Annotated[User, Depends(get_current_admin)],
) -> dict[str, int | str]:
    """Reassign a case and its originating lead to another firm."""
    case = reassign_case(db, case_id, payload.target_firm_id, admin_user)
    return {
        "id": case.id,
        "lead_id": case.lead_id,
        "assigned_firm_id": case.assigned_firm_id,
        "status": case.status.value,
    }


@router.get("/audit-logs", response_model=list[AuditLogRead])
def get_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    admin_user: Annotated[User, Depends(get_current_admin)],
    entity_type: Annotated[Literal["LEAD", "CASE"] | None, Query()] = None,
    entity_id: Annotated[int | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AuditLogRead]:
    """Inspect system audit history with optional entity filters."""
    records = list_audit_logs(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )
    return [AuditLogRead.model_validate(record) for record in records]


@router.get("/firms", response_model=list[LawFirmRead])
def list_firms(
    db: Annotated[Session, Depends(get_db)],
    admin_user: Annotated[User, Depends(get_current_admin)],
) -> list[LawFirm]:
    """List firms for administrative reassignment workflows."""
    return list(db.scalars(select(LawFirm).order_by(LawFirm.name, LawFirm.id)).all())
