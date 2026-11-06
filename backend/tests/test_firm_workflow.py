"""Tests for firm lead inbox visibility and decision workflows."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import AuditAction, AuditLog, Case, CaseStatus, Lead, LeadStatus


def _submit_lead(
    client: Any,
    plaintiff_email: str,
    *,
    category: str,
    region: str,
    name: str,
) -> dict[str, Any]:
    """Submit a lead using an existing plaintiff persona."""
    response = client.post(
        "/api/leads",
        user=plaintiff_email,
        json={
            "plaintiff_name": name,
            "email": plaintiff_email,
            "category": category,
            "region": region,
            "description": "A sufficiently detailed legal inquiry for testing.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_firm_inbox_only_contains_its_assigned_leads(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """Apex staff see Apex's pending lead but not Beacon's lead."""
    apex_lead = _submit_lead(
        client,
        str(baseline["jane_email"]),
        category="PERSONAL_INJURY",
        region="NY",
        name="Jane Plaintiff",
    )
    beacon_lead = _submit_lead(
        client,
        str(baseline["bob_email"]),
        category="LABOR",
        region="CA",
        name="Bob Plaintiff",
    )
    second_apex_lead = _submit_lead(
        client,
        str(baseline["jane_email"]),
        category="PERSONAL_INJURY",
        region="NY",
        name="Jane Plaintiff",
    )

    response = client.get("/api/leads", user=str(baseline["sarah_email"]))

    assert response.status_code == 200
    lead_ids = {lead["id"] for lead in response.json()}
    assert apex_lead["id"] in lead_ids
    assert second_apex_lead["id"] in lead_ids
    assert beacon_lead["id"] not in lead_ids

    first_page = client.get(
        "/api/leads?search=Jane&limit=1&offset=0",
        user=str(baseline["sarah_email"]),
    )
    second_page = client.get(
        "/api/leads?search=Jane&limit=1&offset=1",
        user=str(baseline["sarah_email"]),
    )
    assert first_page.status_code == 200, first_page.text
    assert second_page.status_code == 200, second_page.text
    assert first_page.headers["X-Total-Count"] == "2"
    assert second_page.headers["X-Total-Count"] == "2"
    assert len(first_page.json()) == 1
    assert len(second_page.json()) == 1
    assert first_page.json()[0]["id"] != second_page.json()[0]["id"]

    category_filtered = client.get(
        "/api/leads?category=PERSONAL_INJURY",
        user=str(baseline["sarah_email"]),
    )
    region_filtered = client.get(
        "/api/leads?region=NY",
        user=str(baseline["sarah_email"]),
    )
    assert category_filtered.status_code == 200, category_filtered.text
    assert region_filtered.status_code == 200, region_filtered.text
    assert {lead["id"] for lead in category_filtered.json()} == {
        apex_lead["id"],
        second_apex_lead["id"],
    }
    assert {lead["id"] for lead in region_filtered.json()} == {
        apex_lead["id"],
        second_apex_lead["id"],
    }


def test_accepting_lead_creates_case_and_audit_records(
    client: Any,
    baseline: dict[str, int | str],
    db_engine: Engine,
) -> None:
    """Acceptance changes lead state, creates an intake case, and writes history."""
    lead = _submit_lead(
        client,
        str(baseline["jane_email"]),
        category="PERSONAL_INJURY",
        region="NY",
        name="Jane Plaintiff",
    )

    response = client.post(
        f"/api/leads/{lead['id']}/accept",
        user=str(baseline["sarah_email"]),
    )

    assert response.status_code == 201, response.text
    case_data = response.json()
    assert case_data["lead_id"] == lead["id"]
    assert case_data["status"] == CaseStatus.INTAKE.value

    with Session(db_engine) as db:
        stored_lead = db.get(Lead, lead["id"])
        stored_case = db.scalar(select(Case).where(Case.lead_id == lead["id"]))
        audit = db.scalar(
            select(AuditLog).where(
                AuditLog.entity_type == "LEAD",
                AuditLog.entity_id == lead["id"],
                AuditLog.action == AuditAction.ACCEPTED.value,
            )
        )

    assert stored_lead is not None
    assert stored_lead.status == LeadStatus.ACCEPTED
    assert stored_case is not None
    assert stored_case.status == CaseStatus.INTAKE
    assert audit is not None
    assert audit.previous_state["status"] == LeadStatus.PENDING_REVIEW.value
    assert audit.new_state["status"] == LeadStatus.ACCEPTED.value


def test_declined_lead_leaves_active_inbox_for_admin_resolution(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """A declined lead remains assigned but no longer appears in firm inbox."""
    lead = _submit_lead(
        client,
        str(baseline["jane_email"]),
        category="PERSONAL_INJURY",
        region="NY",
        name="Jane Plaintiff",
    )

    response = client.post(
        f"/api/leads/{lead['id']}/decline",
        user=str(baseline["sarah_email"]),
    )

    assert response.status_code == 200
    declined = response.json()
    assert declined["status"] == LeadStatus.DECLINED.value
    assert declined["assigned_firm_id"] == baseline["apex_id"]

    inbox = client.get("/api/leads", user=str(baseline["sarah_email"]))
    assert inbox.status_code == 200
    assert lead["id"] not in {item["id"] for item in inbox.json()}

    admin_leads = client.get(
        "/api/leads?status=DECLINED",
        user=str(baseline["admin_email"]),
    )
    assert admin_leads.status_code == 200
    assert lead["id"] in {item["id"] for item in admin_leads.json()}
