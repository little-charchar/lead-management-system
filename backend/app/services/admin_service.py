"""Administrator-only reassignment and audit-history queries."""

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import CaseStatus
from app.models import (
    AuditAction,
    AuditLog,
    Case,
    Lead,
    LeadStatus,
    LawFirm,
    User,
)
from app.schemas.case import CaseListRead
from app.search import region_search_terms
from app.services.case_service import get_case_summaries


def reassign_lead(
    db: Session, lead_id: int, target_firm_id: int, actor: User
) -> Lead:
    """Reassign a lead that has not yet been accepted and capture its routing state."""
    try:
        lead = db.scalar(select(Lead).where(Lead.id == lead_id).with_for_update())
        if lead is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found."
            )
        if lead.status not in {
            LeadStatus.UNASSIGNED,
            LeadStatus.PENDING_REVIEW,
            LeadStatus.DECLINED,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Accepted leads must be reassigned through their case.",
            )
        firm = db.get(LawFirm, target_firm_id)
        if firm is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Target firm not found."
            )
        case = db.scalar(
            select(Case).where(Case.lead_id == lead.id).with_for_update()
        )
        previous_state = {
            "status": lead.status.value,
            "assigned_firm_id": lead.assigned_firm_id,
        }
        if case is not None:
            previous_state["case_assigned_firm_id"] = case.assigned_firm_id
        lead.assigned_firm_id = firm.id
        if lead.status in {LeadStatus.UNASSIGNED, LeadStatus.DECLINED}:
            lead.status = LeadStatus.PENDING_REVIEW
        new_state = {
            "status": lead.status.value,
            "assigned_firm_id": lead.assigned_firm_id,
        }
        if case is not None:
            case.assigned_firm_id = firm.id
            new_state["case_assigned_firm_id"] = case.assigned_firm_id
        db.add(
            AuditLog(
                entity_type="LEAD",
                entity_id=lead.id,
                actor_id=actor.id,
                action=AuditAction.REASSIGNED.value,
                previous_state=previous_state,
                new_state=new_state,
            )
        )
        if case is not None:
            db.add(
                AuditLog(
                    entity_type="CASE",
                    entity_id=case.id,
                    actor_id=actor.id,
                    action=AuditAction.REASSIGNED.value,
                    previous_state={
                        "assigned_firm_id": previous_state["case_assigned_firm_id"]
                    },
                    new_state={"assigned_firm_id": case.assigned_firm_id},
                )
            )
        db.commit()
        db.refresh(lead)
        return lead
    except Exception:
        db.rollback()
        raise


def reassign_case(
    db: Session, case_id: int, target_firm_id: int, actor: User
) -> Case:
    """Reassign a case without changing historical note ownership."""
    try:
        lead_id = db.scalar(select(Case.lead_id).where(Case.id == case_id))
        if lead_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Case not found."
            )
        lead = db.scalar(select(Lead).where(Lead.id == lead_id).with_for_update())
        if lead is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The case's lead was not found.",
            )
        case = db.scalar(
            select(Case).where(Case.id == case_id).with_for_update()
        )
        if case is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Case not found."
            )
        if case.status == CaseStatus.CLOSED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Closed cases cannot be reassigned.",
            )
        firm = db.get(LawFirm, target_firm_id)
        if firm is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Target firm not found."
            )
        previous_case_firm_id = case.assigned_firm_id
        previous_case_status = case.status.value
        previous_lead_firm_id = lead.assigned_firm_id
        firm_changed = case.assigned_firm_id != firm.id
        case.assigned_firm_id = firm.id
        lead.assigned_firm_id = firm.id
        if firm_changed:
            case.status = CaseStatus.INTAKE
        db.add(
            AuditLog(
                entity_type="LEAD",
                entity_id=lead.id,
                actor_id=actor.id,
                action=AuditAction.REASSIGNED.value,
                previous_state={
                    "assigned_firm_id": previous_lead_firm_id,
                    "status": lead.status.value,
                },
                new_state={
                    "assigned_firm_id": lead.assigned_firm_id,
                    "status": lead.status.value,
                },
            )
        )
        db.add(
            AuditLog(
                entity_type="CASE",
                entity_id=case.id,
                actor_id=actor.id,
                action=AuditAction.REASSIGNED.value,
                previous_state={
                    "assigned_firm_id": previous_case_firm_id,
                    "status": previous_case_status,
                },
                new_state={
                    "assigned_firm_id": case.assigned_firm_id,
                    "status": case.status.value,
                },
            )
        )
        db.commit()
        db.refresh(case)
        return case
    except Exception:
        db.rollback()
        raise


def list_audit_logs(
    db: Session,
    *,
    entity_type: str | None,
    entity_id: int | None,
    limit: int,
    offset: int,
) -> list[AuditLog]:
    """Return audit records filtered by entity, newest first."""
    statement = select(AuditLog).options(selectinload(AuditLog.actor))
    if entity_type is not None:
        statement = statement.where(AuditLog.entity_type == entity_type.upper())
    if entity_id is not None:
        statement = statement.where(AuditLog.entity_id == entity_id)
    return list(
        db.scalars(
            statement.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )


def list_admin_cases(
    db: Session,
    admin: User,
    *,
    search: str | None,
    case_status: CaseStatus | None,
    firm_id: int | None,
    limit: int,
    offset: int,
) -> tuple[list[CaseListRead], int]:
    """Search and filter compact case rows across all firms."""
    statement = (
        select(Case.id)
        .join(Lead, Case.lead_id == Lead.id)
        .join(User, User.id == Lead.plaintiff_id)
    )
    if case_status is not None:
        statement = statement.where(Case.status == case_status)
    if firm_id is not None:
        statement = statement.where(Case.assigned_firm_id == firm_id)
    if search is not None:
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
                User.name.ilike(pattern),
                User.email.ilike(pattern),
            )
        )
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    case_ids = db.scalars(
        statement.order_by(Case.updated_at.desc(), Case.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return get_case_summaries(db, list(case_ids), admin), total
