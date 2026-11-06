"""Reset application data and load a larger representative demo dataset.

Run from the backend directory with ``python -m app.seed``. Existing database
schema and Alembic-managed indexes are preserved. Pass ``--if-empty`` to seed
only when the database contains no users.
"""

import argparse

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    AuditAction,
    AuditLog,
    Case,
    CaseStatus,
    Document,
    Document,
    LawFirm,
    Lead,
    LeadAttachment,
    LeadStatus,
    Note,
    RoutingRule,
    User,
    UserRole,
)


GENERATED_LEAD_COUNT = 97
GENERATED_CASE_COUNT = 39


def reset_database_data(db: Session) -> None:
    """Delete application rows in FK-safe order without dropping the schema."""
    for model in (
        AuditLog,
        Document,
        Note,
        Case,
        LeadAttachment,
        Lead,
        RoutingRule,
        User,
        LawFirm,
    ):
        db.execute(delete(model))
    db.flush()


def seed_database(db: Session) -> None:
    """Insert demo personas, routing activity, 100 leads, and 40 cases."""
    apex = LawFirm(name="Apex Legal Partners")
    beacon = LawFirm(name="Beacon Rights Group")
    crestview = LawFirm(name="Crestview Counsel")
    db.add_all([apex, beacon, crestview])
    db.flush()

    routing = [
        ("PERSONAL_INJURY", "NY", apex),
        ("LABOR", "CA", beacon),
        ("FAMILY", "ON", crestview),
    ]
    db.add_all(
        [
            RoutingRule(category=category, region=region, law_firm=firm)
            for category, region, firm in routing
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
    olivia = User(
        name="Olivia Attorney",
        email="olivia@crestviewcounsel.com",
        role=UserRole.ATTORNEY,
        law_firm=crestview,
    )
    admin = User(
        name="Elena Admin", email="admin@system.com", role=UserRole.ADMIN
    )
    plaintiffs = [jane, bob]
    client_names = (
        "Alex Morgan",
        "Taylor Reed",
        "Jordan Rivera",
        "Casey Brooks",
        "Riley Bennett",
        "Avery Parker",
        "Cameron Ellis",
        "Quinn Foster",
        "Drew Hayes",
        "Morgan Kelly",
        "Jamie Lane",
        "Robin Murphy",
    )
    plaintiffs.extend(
        User(
            name=name,
            email=f"client{index:02d}@plaintiff.com",
            role=UserRole.PLAINTIFF,
        )
        for index, name in enumerate(client_names, start=1)
    )
    db.add_all([*plaintiffs, sarah, mark, david, olivia, admin])
    db.flush()

    firm_staff = {
        apex.id: [sarah, mark],
        beacon.id: [david],
        crestview.id: [olivia],
    }

    unmatched_lead = Lead(
        plaintiff=jane,
        title="Immigration status question",
        category="IMMIGRATION",
        region="TX",
        description="Needs help understanding an immigration matter and available next steps.",
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
        description="Workplace injury requiring legal representation and case review.",
        status=LeadStatus.ACCEPTED,
        assigned_firm=apex,
    )
    sample_case = Case(
        lead=accepted_lead,
        assigned_firm=apex,
        status=CaseStatus.INTAKE,
    )
    sample_case.documents.append(
        Document(
            uploaded_by=jane,
            file_name="initial_intake.pdf",
            file_path="uploads/cases/initial_intake.pdf",
            file_size_bytes=245_760,
            mime_type="application/pdf",
        )
    )
    sample_case.notes.append(
        Note(
            author=sarah,
            author_firm=apex,
            content="Initial intake reviewed; preserve this note within Apex Legal Partners.",
        )
    )
    db.add_all([unmatched_lead, pending_lead, sample_case])
    db.flush()

    categories = (
        ("PERSONAL_INJURY", "NY", apex),
        ("LABOR", "CA", beacon),
        ("FAMILY", "ON", crestview),
    )
    titles = (
        "Workplace accommodation request",
        "Unpaid overtime review",
        "Rental deposit dispute",
        "Employment contract question",
        "Family support arrangement",
        "Vehicle collision follow-up",
        "Workplace injury consultation",
        "Insurance claim review",
        "Parenting schedule guidance",
        "Wrongful termination concern",
    )
    descriptions = (
        "The client is gathering records and requests a review of available legal options.",
        "The client would like to understand the relevant deadlines and next steps.",
        "Documents and a timeline are being organized for an initial consultation.",
        "The client is seeking representation and guidance about the claims process.",
        "Please review the circumstances and advise whether the matter fits the firm's practice.",
    )
    generated_statuses = (
        [LeadStatus.ACCEPTED] * GENERATED_CASE_COUNT
        + [LeadStatus.PENDING_REVIEW] * 37
        + [LeadStatus.UNASSIGNED] * 11
        + [LeadStatus.DECLINED] * 10
    )
    case_statuses = (
        CaseStatus.INTAKE,
        CaseStatus.INVESTIGATION,
        CaseStatus.DISCOVERY,
        CaseStatus.SETTLED,
        CaseStatus.CLOSED,
    )
    generated_cases: list[tuple[Lead, Case, LawFirm, User]] = []
    generated_leads: list[tuple[Lead, User | None, LawFirm | None]] = []
    for index, lead_status in enumerate(generated_statuses):
        plaintiff = plaintiffs[(index + 2) % len(plaintiffs)]
        if lead_status == LeadStatus.UNASSIGNED:
            category, region, firm = "IMMIGRATION", "TX", None
        else:
            category, region, firm = categories[index % len(categories)]
        lead = Lead(
            plaintiff=plaintiff,
            title=f"{titles[index % len(titles)]} · {index + 1:03d}",
            category=category,
            region=region,
            description=(
                f"{descriptions[index % len(descriptions)]} "
                f"Reference intake batch {index + 1:03d}."
            ),
            status=lead_status,
            assigned_firm=firm,
        )
        db.add(lead)
        staff = (
            firm_staff[firm.id][index % len(firm_staff[firm.id])]
            if firm is not None
            else None
        )
        generated_leads.append((lead, staff, firm))
        if lead_status == LeadStatus.ACCEPTED:
            assert firm is not None
            case_status = case_statuses[
                (len(generated_cases) + 1) % len(case_statuses)
            ]
            case = Case(
                lead=lead,
                assigned_firm=firm,
                status=case_status,
            )
            assert staff is not None
            case.notes.append(
                Note(
                    author=staff,
                    author_firm=firm,
                    content=(
                        f"Initial review completed for intake batch {index + 1:03d}."
                    ),
                )
            )
            db.add(case)
            generated_cases.append((lead, case, firm, staff))

    db.flush()

    for lead, staff, firm in generated_leads:
        if lead.status == LeadStatus.UNASSIGNED:
            continue
        assert firm is not None
        accepted = lead.status == LeadStatus.ACCEPTED
        action = (
            AuditAction.ACCEPTED
            if accepted
            else AuditAction.DECLINED
            if lead.status == LeadStatus.DECLINED
            else AuditAction.AUTO_ROUTED
        )
        previous_status = (
            LeadStatus.PENDING_REVIEW
            if accepted or lead.status == LeadStatus.DECLINED
            else LeadStatus.UNASSIGNED
        )
        db.add(
            AuditLog(
                entity_type="LEAD",
                entity_id=lead.id,
                actor=staff if accepted or lead.status == LeadStatus.DECLINED else admin,
                action=action.value,
                previous_state={
                    "status": previous_status.value,
                    "assigned_firm_id": firm.id
                    if previous_status == LeadStatus.PENDING_REVIEW
                    else None,
                },
                new_state={
                    "status": lead.status.value,
                    "assigned_firm_id": firm.id,
                },
            )
        )

    for lead, case, firm, staff in generated_cases:
        db.add_all(
            [
                AuditLog(
                    entity_type="CASE",
                    entity_id=case.id,
                    actor=staff,
                    action=AuditAction.STATUS_CHANGED.value,
                    previous_state=None,
                    new_state={
                        "status": case.status.value,
                        "assigned_firm_id": firm.id,
                    },
                ),
            ]
        )

    db.add_all(
        [
            AuditLog(
                entity_type="LEAD",
                entity_id=pending_lead.id,
                actor=admin,
                action=AuditAction.AUTO_ROUTED.value,
                previous_state={
                    "status": LeadStatus.UNASSIGNED.value,
                    "assigned_firm_id": None,
                },
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
                entity_id=sample_case.id,
                actor=admin,
                action=AuditAction.STATUS_CHANGED.value,
                previous_state=None,
                new_state={
                    "status": sample_case.status.value,
                    "assigned_firm_id": apex.id,
                },
            ),
        ]
    )


def main(*, if_empty: bool = False) -> None:
    """Reset application data and seed it, or seed an empty database only."""
    with SessionLocal.begin() as db:
        if if_empty and db.scalar(select(User.id).limit(1)) is not None:
            print("Database already contains users; preserving existing data.")
            return
        if not if_empty:
            reset_database_data(db)
        seed_database(db)
        db.flush()
        lead_count = db.scalar(select(func.count()).select_from(Lead)) or 0
        case_count = db.scalar(select(func.count()).select_from(Case)) or 0
        note_count = db.scalar(select(func.count()).select_from(Note)) or 0
        audit_count = db.scalar(select(func.count()).select_from(AuditLog)) or 0
    print(
        "Database seeded successfully: "
        f"{lead_count} leads, {case_count} cases, "
        f"{note_count} private notes, {audit_count} audit events."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--if-empty",
        action="store_true",
        help="seed only when the database has no users; do not reset existing data",
    )
    main(if_empty=parser.parse_args().if_empty)
