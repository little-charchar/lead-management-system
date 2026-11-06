"""Tests for deterministic lead routing and submission audit records."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine

from app.models import AuditLog, AuditAction, Lead, LeadStatus


def _lead_payload(
    *,
    name: str = "Jane Plaintiff",
    email: str = "jane@plaintiff.com",
    category: str = "PERSONAL_INJURY",
    region: str = "NY",
) -> dict[str, str]:
    """Return a valid intake payload with overridable routing fields."""
    return {
        "plaintiff_name": name,
        "email": email,
        "title": "Traffic collision injury",
        "category": category,
        "region": region,
        "description": "A sufficiently detailed legal inquiry for testing.",
    }


def test_matching_lead_is_routed_to_matching_firm(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """A matching category-region pair assigns Apex and enters its review queue."""
    response = client.post(
        "/api/leads",
        user=str(baseline["jane_email"]),
        json=_lead_payload(),
    )

    assert response.status_code == 201
    lead = response.json()
    assert lead["assigned_firm_id"] == baseline["apex_id"]
    assert lead["status"] == LeadStatus.PENDING_REVIEW.value
    assert lead["title"] == "Traffic collision injury"


def test_unmatched_lead_remains_unassigned(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """An unmatched category-region pair does not receive a firm assignment."""
    response = client.post(
        "/api/leads",
        user=str(baseline["jane_email"]),
        json=_lead_payload(category="IMMIGRATION", region="TX"),
    )

    assert response.status_code == 201
    lead = response.json()
    assert lead["assigned_firm_id"] is None
    assert lead["status"] == LeadStatus.UNASSIGNED.value


def test_submission_writes_audit_log(
    client: Any,
    baseline: dict[str, int | str],
    db_engine: Engine,
) -> None:
    """Lead submission records the routing decision in the audit history."""
    response = client.post(
        "/api/leads",
        user=str(baseline["jane_email"]),
        json=_lead_payload(category="IMMIGRATION", region="TX"),
    )
    assert response.status_code == 201
    lead_id = response.json()["id"]

    with Session(db_engine) as db:
        audit = db.scalar(
            select(AuditLog).where(
                AuditLog.entity_type == "LEAD",
                AuditLog.entity_id == lead_id,
                AuditLog.action == AuditAction.AUTO_ROUTED.value,
            )
        )

    assert audit is not None
    assert audit.previous_state is None
    assert audit.new_state["status"] == LeadStatus.UNASSIGNED.value
    assert audit.new_state["assigned_firm_id"] is None


def test_lead_details_are_limited_to_1000_words(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """The API rejects descriptions above the UI's 1,000-word limit."""
    payload = _lead_payload()
    payload["description"] = " ".join(["detail"] * 1001)

    response = client.post(
        "/api/leads",
        user=str(baseline["jane_email"]),
        json=payload,
    )

    assert response.status_code == 422
    assert "1000 words or fewer" in response.text


def test_lead_accepts_concise_required_details(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """A non-empty, concise description is valid without a word minimum."""
    payload = _lead_payload()
    payload["description"] = "Help"

    response = client.post(
        "/api/leads",
        user=str(baseline["jane_email"]),
        json=payload,
    )

    assert response.status_code == 201, response.text
    assert response.json()["description"] == "Help"


def test_lead_rejects_blank_details_after_trimming(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """Whitespace-only details do not satisfy the required description field."""
    payload = _lead_payload()
    payload["description"] = "   "

    response = client.post(
        "/api/leads",
        user=str(baseline["jane_email"]),
        json=payload,
    )

    assert response.status_code == 422


def test_plaintiff_can_page_only_unresolved_leads_with_a_total(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """Plaintiff lists can request unresolved pages without downloading all leads."""
    accepted_payload = _lead_payload()
    accepted_payload["title"] = "Accepted matter"
    pending_payload = _lead_payload()
    pending_payload["title"] = "Pending matter"
    accepted_lead = client.post(
        "/api/leads",
        user=str(baseline["jane_email"]),
        json=accepted_payload,
    )
    pending_lead = client.post(
        "/api/leads",
        user=str(baseline["jane_email"]),
        json=pending_payload,
    )
    assert accepted_lead.status_code == pending_lead.status_code == 201
    accepted = client.post(
        f"/api/leads/{accepted_lead.json()['id']}/accept",
        user=str(baseline["sarah_email"]),
    )
    assert accepted.status_code == 201

    response = client.get(
        "/api/leads?exclude_accepted=true&limit=1",
        user=str(baseline["jane_email"]),
    )

    assert response.status_code == 200, response.text
    assert response.headers["X-Total-Count"] == "1"
    assert [lead["id"] for lead in response.json()] == [pending_lead.json()["id"]]
