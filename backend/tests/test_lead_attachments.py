"""Tests for pre-acceptance lead PDFs and case lookup by lead."""

from typing import Any


def _submit_lead(client: Any, email: str) -> int:
    """Submit a routed lead owned by the supplied plaintiff."""
    response = client.post(
        "/api/leads",
        user=email,
        json={
            "plaintiff_name": "Jane Plaintiff",
            "email": email,
            "category": "PERSONAL_INJURY",
            "region": "NY",
            "description": "A sufficiently detailed legal inquiry with documents.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_lead_pdfs_are_shared_with_assigned_firm_and_remain_after_acceptance(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """The owner and assigned firm can retrieve attachments linked to a lead."""
    plaintiff = str(baseline["jane_email"])
    firm_staff = str(baseline["sarah_email"])
    lead_id = _submit_lead(client, plaintiff)

    upload = client.post(
        f"/api/leads/{lead_id}/attachments",
        user=plaintiff,
        files={"file": ("intake-evidence.pdf", b"%PDF-1.7\nsupporting evidence", "application/pdf")},
    )
    assert upload.status_code == 201, upload.text
    attachment = upload.json()
    assert attachment["file_name"] == "intake-evidence.pdf"
    assert attachment["file_size_bytes"] == len(b"%PDF-1.7\nsupporting evidence")
    assert "file_path" not in attachment

    inbox = client.get("/api/leads", user=firm_staff)
    assert inbox.status_code == 200, inbox.text
    firm_lead = next(item for item in inbox.json() if item["id"] == lead_id)
    assert firm_lead["attachments"][0]["id"] == attachment["id"]

    for email in (plaintiff, firm_staff):
        downloaded = client.get(
            f"/api/leads/{lead_id}/attachments/{attachment['id']}",
            user=email,
        )
        assert downloaded.status_code == 200
        assert downloaded.content.startswith(b"%PDF-")

    admin_download = client.get(
        f"/api/leads/{lead_id}/attachments/{attachment['id']}",
        user=str(baseline["admin_email"]),
    )
    assert admin_download.status_code == 200
    assert admin_download.content.startswith(b"%PDF-")

    accepted = client.post(f"/api/leads/{lead_id}/accept", user=firm_staff)
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["lead"]["attachments"][0]["id"] == attachment["id"]
    opened = client.get(f"/api/leads/{lead_id}/case", user=plaintiff)
    assert opened.status_code == 200, opened.text
    assert opened.json()["lead"]["attachments"][0]["id"] == attachment["id"]
    firm_case = client.get(f"/api/cases/{accepted.json()['id']}", user=firm_staff)
    assert firm_case.status_code == 200, firm_case.text
    assert firm_case.json()["lead"]["attachments"][0]["id"] == attachment["id"]


def test_lead_attachment_and_case_lookup_enforce_current_visibility(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """Unrelated plaintiffs and firms cannot inspect or download the lead."""
    owner = str(baseline["jane_email"])
    lead_id = _submit_lead(client, owner)
    upload = client.post(
        f"/api/leads/{lead_id}/attachments",
        user=owner,
        files={"file": ("evidence.pdf", b"%PDF-1.7\ncontent", "application/pdf")},
    )
    assert upload.status_code == 201, upload.text
    attachment_id = upload.json()["id"]

    for email in (str(baseline["bob_email"]), str(baseline["david_email"])):
        for path in (
            f"/api/leads/{lead_id}/attachments/{attachment_id}",
            f"/api/leads/{lead_id}/case",
        ):
            response = client.get(path, user=email)
            assert response.status_code == 403
