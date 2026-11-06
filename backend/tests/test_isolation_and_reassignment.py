"""End-to-end tests for case privacy across firm reassignment."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import AuditAction, AuditLog


def test_case_reassignment_changes_firm_visibility_and_preserves_history(
    client: Any,
    baseline: dict[str, int | str],
    db_engine: Engine,
) -> None:
    """Plaintiffs see no notes; new firm cannot see prior firm's notes; admin can."""
    submitted = client.post(
        "/api/leads",
        user=str(baseline["jane_email"]),
        json={
            "plaintiff_name": "Jane Plaintiff",
            "email": str(baseline["jane_email"]),
            "category": "PERSONAL_INJURY",
            "region": "NY",
            "description": "Jane's sufficiently detailed legal inquiry.",
        },
    )
    assert submitted.status_code == 201, submitted.text
    lead = submitted.json()

    accepted = client.post(
        f"/api/leads/{lead['id']}/accept",
        user=str(baseline["sarah_email"]),
    )
    assert accepted.status_code == 201, accepted.text
    case_id = accepted.json()["id"]

    note = client.post(
        f"/api/cases/{case_id}/notes",
        user=str(baseline["sarah_email"]),
        json={"content": "Confidential Apex investigation notes."},
    )
    assert note.status_code == 201, note.text
    note_id = note.json()["id"]

    upload = client.post(
        f"/api/cases/{case_id}/documents",
        user=str(baseline["jane_email"]),
        files={
            "file": (
                "initial-evidence.pdf",
                b"%PDF-1.7\nshared case evidence",
                "application/pdf",
            )
        },
    )
    assert upload.status_code == 201, upload.text
    document_id = upload.json()["id"]

    plaintiff_case = client.get(
        f"/api/cases/{case_id}",
        user=str(baseline["jane_email"]),
    )
    assert plaintiff_case.status_code == 200
    plaintiff_data = plaintiff_case.json()
    assert plaintiff_data["status"] == "INTAKE"
    assert len(plaintiff_data["documents"]) == 1
    assert "notes" not in plaintiff_data

    reassigned = client.post(
        f"/api/admin/cases/{case_id}/reassign",
        user=str(baseline["admin_email"]),
        json={"target_firm_id": baseline["beacon_id"]},
    )
    assert reassigned.status_code == 200, reassigned.text
    assert reassigned.json()["assigned_firm_id"] == baseline["beacon_id"]

    with Session(db_engine) as db:
        audit = db.scalar(
            select(AuditLog).where(
                AuditLog.entity_type == "CASE",
                AuditLog.entity_id == case_id,
                AuditLog.action == AuditAction.REASSIGNED.value,
            )
        )
    assert audit is not None
    assert audit.previous_state["assigned_firm_id"] == baseline["apex_id"]
    assert audit.new_state["assigned_firm_id"] == baseline["beacon_id"]

    former_firm_case = client.get(
        f"/api/cases/{case_id}",
        user=str(baseline["sarah_email"]),
    )
    assert former_firm_case.status_code == 403

    new_firm_case = client.get(
        f"/api/cases/{case_id}",
        user=str(baseline["david_email"]),
    )
    assert new_firm_case.status_code == 200
    new_firm_data = new_firm_case.json()
    assert new_firm_data["assigned_firm_id"] == baseline["beacon_id"]
    assert len(new_firm_data["documents"]) == 1
    assert new_firm_data["notes"] == []

    admin_case = client.get(
        f"/api/cases/{case_id}",
        user=str(baseline["admin_email"]),
    )
    assert admin_case.status_code == 200
    assert [item["id"] for item in admin_case.json()["notes"]] == [note_id]
    assert admin_case.json()["notes"][0]["author_firm_id"] == baseline["apex_id"]

    plaintiff_after_reassignment = client.get(
        f"/api/cases/{case_id}",
        user=str(baseline["jane_email"]),
    )
    assert plaintiff_after_reassignment.status_code == 200
    assert "notes" not in plaintiff_after_reassignment.json()
    assert len(plaintiff_after_reassignment.json()["documents"]) == 1
