"""Lead routing and lifecycle workflows."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AuditAction,
    AuditLog,
    Case,
    CaseStatus,
    Lead,
    LeadStatus,
    RoutingRule,
    User,
    UserRole,
)
from app.schemas.lead import LeadCreate


def create_lead(
    db: Session,
    payload: LeadCreate,
    authenticated_user: User | None = None,
) -> Lead:
    """Create a plaintiff and lead, route deterministically, and audit the result."""
    email = str(payload.email).strip().lower()
    try:
        plaintiff = db.scalar(
            select(User).where(func.lower(User.email) == email).with_for_update()
        )
        if authenticated_user is not None:
            if (
                authenticated_user.role != UserRole.PLAINTIFF
                or authenticated_user.id != (plaintiff.id if plaintiff else None)
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="The authenticated plaintiff must submit using their own email.",
                )
        elif plaintiff is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email already has an account; submit with its demo-user header.",
            )

        if plaintiff is None:
            plaintiff = User(
                name=payload.plaintiff_name.strip(),
                email=email,
                role=UserRole.PLAINTIFF,
            )
            db.add(plaintiff)
            db.flush()
        elif plaintiff.role != UserRole.PLAINTIFF:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email belongs to a non-plaintiff account.",
            )

        category = payload.category.strip().upper()
        region = payload.region.strip().upper()
        rule = db.scalar(
            select(RoutingRule).where(
                func.upper(RoutingRule.category) == category,
                func.upper(RoutingRule.region) == region,
            )
        )
        assigned_firm_id = rule.law_firm_id if rule is not None else None
        lead = Lead(
            plaintiff_id=plaintiff.id,
            title=payload.title.strip(),
            category=category,
            region=region,
            description=payload.description.strip(),
            assigned_firm_id=assigned_firm_id,
            status=(
                LeadStatus.PENDING_REVIEW
                if rule is not None
                else LeadStatus.UNASSIGNED
            ),
        )
        db.add(lead)
        db.flush()
        db.add(
            AuditLog(
                entity_type="LEAD",
                entity_id=lead.id,
                actor_id=authenticated_user.id if authenticated_user else plaintiff.id,
                action=AuditAction.AUTO_ROUTED.value,
                previous_state=None,
                new_state={
                    "status": lead.status.value,
                    "assigned_firm_id": lead.assigned_firm_id,
                    "title": lead.title,
                    "category": lead.category,
                    "region": lead.region,
                },
            )
        )
        db.commit()
        db.refresh(lead)
        return lead
    except Exception:
        db.rollback()
        raise


def _get_lead_for_staff(db: Session, lead_id: int, firm_id: int) -> Lead:
    """Lock a lead and verify it is in the staff member's current firm inbox."""
    lead = db.scalar(select(Lead).where(Lead.id == lead_id).with_for_update())
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
    if lead.assigned_firm_id != firm_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This lead is not assigned to your law firm.",
        )
    if lead.status != LeadStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only leads pending review can be accepted or declined.",
        )
    return lead


def accept_lead(db: Session, lead_id: int, staff_user: User) -> Case:
    """Atomically accept a firm's pending lead, create its case, and record history."""
    try:
        lead = _get_lead_for_staff(db, lead_id, staff_user.law_firm_id or -1)
        if lead.assigned_firm_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A lead must be assigned to a firm before acceptance.",
            )
        case = Case(
            lead_id=lead.id,
            assigned_firm_id=lead.assigned_firm_id,
            status=CaseStatus.INTAKE,
        )
        previous_state = {
            "status": lead.status.value,
            "assigned_firm_id": lead.assigned_firm_id,
        }
        lead.status = LeadStatus.ACCEPTED
        db.add(case)
        db.flush()
        db.add_all(
            [
                AuditLog(
                    entity_type="LEAD",
                    entity_id=lead.id,
                    actor_id=staff_user.id,
                    action=AuditAction.ACCEPTED.value,
                    previous_state=previous_state,
                    new_state={
                        "status": lead.status.value,
                        "assigned_firm_id": lead.assigned_firm_id,
                    },
                ),
                AuditLog(
                    entity_type="CASE",
                    entity_id=case.id,
                    actor_id=staff_user.id,
                    action=AuditAction.ACCEPTED.value,
                    previous_state=None,
                    new_state={
                        "lead_id": lead.id,
                        "status": case.status.value,
                        "assigned_firm_id": case.assigned_firm_id,
                    },
                ),
            ]
        )
        db.commit()
        db.refresh(case)
        return case
    except Exception:
        db.rollback()
        raise


def decline_lead(db: Session, lead_id: int, staff_user: User) -> Lead:
    """Decline a pending lead while preserving its firm assignment for admin review."""
    try:
        lead = _get_lead_for_staff(db, lead_id, staff_user.law_firm_id or -1)
        previous_state = {
            "status": lead.status.value,
            "assigned_firm_id": lead.assigned_firm_id,
        }
        lead.status = LeadStatus.DECLINED
        db.add(
            AuditLog(
                entity_type="LEAD",
                entity_id=lead.id,
                actor_id=staff_user.id,
                action=AuditAction.DECLINED.value,
                previous_state=previous_state,
                new_state={
                    "status": lead.status.value,
                    "assigned_firm_id": lead.assigned_firm_id,
                },
            )
        )
        db.commit()
        db.refresh(lead)
        return lead
    except Exception:
        db.rollback()
        raise
