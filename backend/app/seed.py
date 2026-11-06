"""Reset the application schema and load representative development data.

Run from the backend directory with ``python -m app.seed``. This command drops
and recreates all tables managed by the application's SQLAlchemy metadata.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import (
    AuditAction,
    AuditLog,
    Case,
    CaseStatus,
    Document,
    LawFirm,
    Lead,
    LeadStatus,
    Note,
    RoutingRule,
    User,
    UserRole,
)


def seed_database(db: Session) -> None:
    """Insert firms, routing rules, personas, leads, a case, and audit history."""
    apex = LawFirm(name="Apex Legal Partners")
    beacon = LawFirm(name="Beacon Rights Group")
    crestview = LawFirm(name="Crestview Counsel")
    db.add_all([apex, beacon, crestview])
    db.flush()

    db.add_all(
        [
            RoutingRule(category="PERSONAL_INJURY", region="NY", law_firm=apex),
            RoutingRule(category="LABOR", region="CA", law_firm=beacon),
            RoutingRule(category="FAMILY", region="ON", law_firm=crestview),
        ]
    )

    jane = User(
        name="Jane Doe", email="jane@plaintiff.com", role=UserRole.PLAINTIFF
    )
    bob = User(
        name="Bob Smith", email="bob@plaintiff.com", role=UserRole.PLAINTIFF
    )
    sarah = User(
        name="Sarah Attorney",
        email="sarah@apexlegal.com",
        role=UserRole.ATTORNEY,
        law_firm=apex,
    )
    mark = User(
        name="Mark Paralegal",
        email="mark@apexlegal.com",
        role=UserRole.PARALEGAL,
        law_firm=apex,
    )
    david = User(
        name="David Attorney",
        email="david@beaconrights.com",
        role=UserRole.ATTORNEY,
        law_firm=beacon,
    )
    admin = User(
        name="Elena Admin", email="admin@system.com", role=UserRole.ADMIN
    )
    db.add_all([jane, bob, sarah, mark, david, admin])
    db.flush()

    unmatched_lead = Lead(
        plaintiff=jane,
        title="Immigration status question",
        category="IMMIGRATION",
        region="TX",
        description="Needs help with an immigration matter.",
        status=LeadStatus.UNASSIGNED,
    )
    pending_lead = Lead(
        plaintiff=bob,
        title="Traffic collision injury",
        category="PERSONAL_INJURY",
        region="NY",
        description="Injured in a traffic collision and seeking representation.",
        status=LeadStatus.PENDING_REVIEW,
        assigned_firm=apex,
    )
    accepted_lead = Lead(
        plaintiff=jane,
        title="Workplace injury claim",
        category="PERSONAL_INJURY",
        region="NY",
        description="Workplace injury requiring legal representation.",
        status=LeadStatus.ACCEPTED,
        assigned_firm=apex,
    )
    accepted_case = Case(
        lead=accepted_lead,
        assigned_firm=apex,
        status=CaseStatus.INTAKE,
    )
    accepted_case.documents.append(
        Document(
            uploaded_by=jane,
            file_name="initial_intake.pdf",
            file_path="uploads/cases/initial_intake.pdf",
            file_size_bytes=245_760,
            mime_type="application/pdf",
        )
    )
    accepted_case.notes.append(
        Note(
            author=sarah,
            author_firm=apex,
            content="Initial intake reviewed; preserve this note within Apex Legal Partners.",
        )
    )
    db.add_all([unmatched_lead, pending_lead, accepted_case])
    db.flush()

    previous_pending: dict[str, Any] = {
        "status": LeadStatus.UNASSIGNED.value,
        "assigned_firm_id": None,
    }
    db.add_all(
        [
            AuditLog(
                entity_type="LEAD",
                entity_id=pending_lead.id,
                actor=admin,
                action=AuditAction.AUTO_ROUTED.value,
                previous_state=previous_pending,
                new_state={
                    "status": pending_lead.status.value,
                    "assigned_firm_id": apex.id,
                },
            ),
            AuditLog(
                entity_type="LEAD",
                entity_id=accepted_lead.id,
                actor=admin,
                action=AuditAction.ACCEPTED.value,
                previous_state={"status": LeadStatus.PENDING_REVIEW.value},
                new_state={
                    "status": accepted_lead.status.value,
                    "assigned_firm_id": apex.id,
                },
            ),
            AuditLog(
                entity_type="CASE",
                entity_id=accepted_case.id,
                actor=admin,
                action=AuditAction.STATUS_CHANGED.value,
                previous_state=None,
                new_state={
                    "status": accepted_case.status.value,
                    "assigned_firm_id": apex.id,
                },
            ),
        ]
    )


def main() -> None:
    """Drop and recreate the application schema, then load seed data."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal.begin() as db:
        seed_database(db)
    print("Database reset and seeded successfully.")


if __name__ == "__main__":
    main()
