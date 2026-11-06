"""Tests for system-wide admin search, filters, and reassignment traceability."""

from typing import Any


def _submit_lead(
    client: Any,
    email: str,
    name: str,
    *,
    category: str = "PERSONAL_INJURY",
    region: str = "NY",
) -> dict[str, Any]:
    """Create a lead associated with an existing plaintiff persona."""
    response = client.post(
        "/api/leads",
        user=email,
        json={
            "plaintiff_name": name,
            "email": email,
            "title": f"{name} legal intake",
            "category": category,
            "region": region,
            "description": "A sufficiently detailed legal inquiry for admin testing.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_admin_case_directory_searches_and_filters_across_firms(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """Administrators can query case status, client, and assigned firm globally."""
    jane_lead = _submit_lead(
        client,
        str(baseline["jane_email"]),
        "Jane Plaintiff",
    )
    jane_case = client.post(
        f"/api/leads/{jane_lead['id']}/accept",
        user=str(baseline["sarah_email"]),
    )
    assert jane_case.status_code == 201, jane_case.text
    jane_case_id = jane_case.json()["id"]
    lead_transfer = client.post(
        f"/api/admin/leads/{jane_lead['id']}/reassign",
        user=str(baseline["admin_email"]),
        json={"target_firm_id": baseline["beacon_id"]},
    )
    assert lead_transfer.status_code == 409

    bob_lead = _submit_lead(
        client,
        str(baseline["bob_email"]),
        "Bob Plaintiff",
        category="LABOR",
        region="CA",
    )
    bob_case = client.post(
        f"/api/leads/{bob_lead['id']}/accept",
        user=str(baseline["david_email"]),
    )
    assert bob_case.status_code == 201, bob_case.text
    bob_case_id = bob_case.json()["id"]

    all_cases = client.get(
        "/api/admin/cases?status=INTAKE&limit=100",
        user=str(baseline["admin_email"]),
    )
    assert all_cases.status_code == 200, all_cases.text
    assert all_cases.headers["X-Total-Count"] == "2"
    assert {item["id"] for item in all_cases.json()} == {
        jane_case_id,
        bob_case_id,
    }

    jane_cases = client.get(
        f"/api/admin/cases?search=Jane&firm_id={baseline['apex_id']}",
        user=str(baseline["admin_email"]),
    )
    assert jane_cases.status_code == 200, jane_cases.text
    assert jane_cases.headers["X-Total-Count"] == "1"
    assert [item["id"] for item in jane_cases.json()] == [jane_case_id]

    other_firm_cases = client.get(
        f"/api/admin/cases?firm_id={baseline['beacon_id']}",
        user=str(baseline["admin_email"]),
    )
    assert other_firm_cases.status_code == 200, other_firm_cases.text
    assert [item["id"] for item in other_firm_cases.json()] == [bob_case_id]

    denied = client.get(
        "/api/admin/cases",
        user=str(baseline["sarah_email"]),
    )
    assert denied.status_code == 403


def test_admin_lead_directory_filters_all_firms_and_rejects_non_admin_filter(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """The admin lead query includes every status and supports firm filtering."""
    apex_lead = _submit_lead(
        client,
        str(baseline["jane_email"]),
        "Jane Plaintiff",
    )
    beacon_lead = _submit_lead(
        client,
        str(baseline["bob_email"]),
        "Bob Plaintiff",
        category="LABOR",
        region="CA",
    )
    unmatched_lead = _submit_lead(
        client,
        str(baseline["jane_email"]),
        "Jane Plaintiff",
        category="IMMIGRATION",
        region="TX",
    )
    accepted_lead = _submit_lead(
        client,
        str(baseline["bob_email"]),
        "Bob Plaintiff",
    )
    accepted_case = client.post(
        f"/api/leads/{accepted_lead['id']}/accept",
        user=str(baseline["sarah_email"]),
    )
    assert accepted_case.status_code == 201, accepted_case.text

    all_statuses = client.get(
        "/api/leads?limit=100",
        user=str(baseline["admin_email"]),
    )
    assert all_statuses.status_code == 200, all_statuses.text
    assert all_statuses.headers["X-Total-Count"] == "4"
    assert {item["id"] for item in all_statuses.json()} == {
        apex_lead["id"],
        beacon_lead["id"],
        unmatched_lead["id"],
        accepted_lead["id"],
    }

    unresolved = client.get(
        "/api/leads?exclude_accepted=true&limit=100",
        user=str(baseline["admin_email"]),
    )
    assert unresolved.status_code == 200, unresolved.text
    assert unresolved.headers["X-Total-Count"] == "3"
    assert {item["id"] for item in unresolved.json()} == {
        apex_lead["id"],
        beacon_lead["id"],
        unmatched_lead["id"],
    }

    accepted_cases = client.get(
        f"/api/admin/cases?search=Bob&limit=100",
        user=str(baseline["admin_email"]),
    )
    assert accepted_cases.status_code == 200, accepted_cases.text
    assert accepted_case.json()["id"] in {
        item["id"] for item in accepted_cases.json()
    }

    apex_only = client.get(
        f"/api/leads?assigned_firm_id={baseline['apex_id']}&exclude_accepted=true",
        user=str(baseline["admin_email"]),
    )
    assert apex_only.status_code == 200, apex_only.text
    assert apex_only.headers["X-Total-Count"] == "1"
    assert {item["id"] for item in apex_only.json()} == {apex_lead["id"]}

    non_admin = client.get(
        f"/api/leads?assigned_firm_id={baseline['apex_id']}",
        user=str(baseline["sarah_email"]),
    )
    assert non_admin.status_code == 403


def test_admin_lead_reassignment_revokes_old_firm_and_records_actor_state(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """Reassigning a lead revokes the old firm's attachment access immediately."""
    lead = _submit_lead(
        client,
        str(baseline["jane_email"]),
        "Jane Plaintiff",
    )
    attachment = client.post(
        f"/api/leads/{lead['id']}/attachments",
        user=str(baseline["jane_email"]),
        files={"file": ("intake.pdf", b"%PDF-1.7\nintake evidence", "application/pdf")},
    )
    assert attachment.status_code == 201, attachment.text
    attachment_id = attachment.json()["id"]

    reassigned = client.post(
        f"/api/admin/leads/{lead['id']}/reassign",
        user=str(baseline["admin_email"]),
        json={"target_firm_id": baseline["beacon_id"]},
    )
    assert reassigned.status_code == 200, reassigned.text
    assert reassigned.json()["assigned_firm_id"] == baseline["beacon_id"]
    assert reassigned.json()["status"] == "PENDING_REVIEW"

    former_firm = client.get(
        f"/api/leads/{lead['id']}/attachments/{attachment_id}",
        user=str(baseline["sarah_email"]),
    )
    assert former_firm.status_code == 403
    new_firm = client.get(
        f"/api/leads/{lead['id']}/attachments/{attachment_id}",
        user=str(baseline["david_email"]),
    )
    assert new_firm.status_code == 200
    assert new_firm.content.startswith(b"%PDF-")

    audit = client.get(
        f"/api/admin/audit-logs?entity_type=LEAD&entity_id={lead['id']}",
        user=str(baseline["admin_email"]),
    )
    assert audit.status_code == 200, audit.text
    assignment = next(
        item for item in audit.json() if item["action"] == "REASSIGNED"
    )
    assert assignment["actor_id"] is not None
    assert assignment["actor"]["email"] == baseline["admin_email"]
    assert assignment["previous_state"]["assigned_firm_id"] == baseline["apex_id"]
    assert assignment["new_state"]["assigned_firm_id"] == baseline["beacon_id"]


def test_case_status_changes_are_traceable_in_admin_audit_history(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """Case status updates record the actor and exact old/new status values."""
    lead = _submit_lead(
        client,
        str(baseline["jane_email"]),
        "Jane Plaintiff",
    )
    accepted = client.post(
        f"/api/leads/{lead['id']}/accept",
        user=str(baseline["sarah_email"]),
    )
    assert accepted.status_code == 201, accepted.text
    case_id = accepted.json()["id"]

    updated = client.patch(
        f"/api/cases/{case_id}/status",
        user=str(baseline["sarah_email"]),
        json={"status": "INVESTIGATION"},
    )
    assert updated.status_code == 200, updated.text

    history = client.get(
        f"/api/admin/audit-logs?entity_type=CASE&entity_id={case_id}",
        user=str(baseline["admin_email"]),
    )
    assert history.status_code == 200, history.text
    status_change = next(
        item
        for item in history.json()
        if item["action"] == "STATUS_CHANGED"
    )
    assert status_change["actor"]["email"] == baseline["sarah_email"]
    assert status_change["previous_state"] == {"status": "INTAKE"}
    assert status_change["new_state"] == {"status": "INVESTIGATION"}

    for next_status in ("DISCOVERY", "SETTLED", "CLOSED"):
        progression = client.patch(
            f"/api/cases/{case_id}/status",
            user=str(baseline["sarah_email"]),
            json={"status": next_status},
        )
        assert progression.status_code == 200, progression.text

    closed_case_transfer = client.post(
        f"/api/admin/cases/{case_id}/reassign",
        user=str(baseline["admin_email"]),
        json={"target_firm_id": baseline["beacon_id"]},
    )
    assert closed_case_transfer.status_code == 409


def test_firm_can_set_any_case_status_and_filter_closed_cases(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """Firm staff can set a requested stage directly and include closed cases."""
    lead = _submit_lead(
        client,
        str(baseline["jane_email"]),
        "Jane Plaintiff",
    )
    accepted = client.post(
        f"/api/leads/{lead['id']}/accept",
        user=str(baseline["sarah_email"]),
    )
    assert accepted.status_code == 201, accepted.text
    case_id = accepted.json()["id"]

    jump_to_discovery = client.patch(
        f"/api/cases/{case_id}/status",
        user=str(baseline["sarah_email"]),
        json={"status": "DISCOVERY"},
    )
    assert jump_to_discovery.status_code == 200, jump_to_discovery.text
    assert jump_to_discovery.json()["status"] == "DISCOVERY"

    change_back = client.patch(
        f"/api/cases/{case_id}/status",
        user=str(baseline["sarah_email"]),
        json={"status": "INVESTIGATION"},
    )
    assert change_back.status_code == 200, change_back.text
    assert change_back.json()["status"] == "INVESTIGATION"

    set_closed = client.patch(
        f"/api/cases/{case_id}/status",
        user=str(baseline["sarah_email"]),
        json={"status": "CLOSED"},
    )
    assert set_closed.status_code == 200, set_closed.text

    active_cases = client.get(
        "/api/cases?limit=11",
        user=str(baseline["sarah_email"]),
    )
    assert active_cases.status_code == 200, active_cases.text
    assert case_id not in {record["id"] for record in active_cases.json()}

    all_cases = client.get(
        "/api/cases?include_closed=true&limit=11",
        user=str(baseline["sarah_email"]),
    )
    assert all_cases.status_code == 200, all_cases.text
    assert case_id in {record["id"] for record in all_cases.json()}

    closed_cases = client.get(
        "/api/cases?status=CLOSED&limit=11",
        user=str(baseline["sarah_email"]),
    )
    assert closed_cases.status_code == 200, closed_cases.text
    assert case_id in {record["id"] for record in closed_cases.json()}
