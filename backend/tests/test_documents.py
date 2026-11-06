"""Tests for secure PDF uploads and downloads."""

from typing import Any

def _create_accepted_case(client: Any, baseline: dict[str, int | str]) -> int:
    """Submit and accept a routed lead, returning the new case ID."""
    submitted = client.post(
        "/api/leads",
        user=str(baseline["jane_email"]),
        json={
            "plaintiff_name": "Jane Plaintiff",
            "email": str(baseline["jane_email"]),
            "category": "PERSONAL_INJURY",
            "region": "NY",
            "description": "A sufficiently detailed document test inquiry.",
        },
    )
    assert submitted.status_code == 201, submitted.text
    accepted = client.post(
        f"/api/leads/{submitted.json()['id']}/accept",
        user=str(baseline["sarah_email"]),
    )
    assert accepted.status_code == 201, accepted.text
    return accepted.json()["id"]


def test_plaintiff_and_assigned_firm_can_upload_and_download_pdf(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """Case owner and currently assigned staff can store and retrieve PDFs."""
    case_id = _create_accepted_case(client, baseline)
    pdf_content = b"%PDF-1.7\nlegal evidence"

    plaintiff_upload = client.post(
        f"/api/cases/{case_id}/documents",
        user=str(baseline["jane_email"]),
        files={"file": ("plaintiff.pdf", pdf_content, "application/pdf")},
    )
    assert plaintiff_upload.status_code == 201, plaintiff_upload.text
    plaintiff_document = plaintiff_upload.json()
    assert plaintiff_document["file_name"] == "plaintiff.pdf"
    assert plaintiff_document["file_size_bytes"] == len(pdf_content)
    assert "file_path" not in plaintiff_document

    staff_upload = client.post(
        f"/api/cases/{case_id}/documents",
        user=str(baseline["sarah_email"]),
        files={
            "file": (
                "firm-document.pdf",
                b"%PDF-1.7\nfirm exhibit",
                "application/pdf",
            )
        },
    )
    assert staff_upload.status_code == 201, staff_upload.text

    for email, document in (
        (str(baseline["jane_email"]), plaintiff_document),
        (str(baseline["sarah_email"]), staff_upload.json()),
    ):
        downloaded = client.get(
            f"/api/cases/{case_id}/documents/{document['id']}",
            user=email,
        )
        assert downloaded.status_code == 200
        assert downloaded.content.startswith(b"%PDF-")
        assert downloaded.headers["content-type"] == "application/pdf"


def test_unrelated_plaintiff_and_unassigned_firm_are_forbidden(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """Other plaintiffs and firms cannot upload or download another case's PDF."""
    case_id = _create_accepted_case(client, baseline)
    uploaded = client.post(
        f"/api/cases/{case_id}/documents",
        user=str(baseline["jane_email"]),
        files={"file": ("evidence.pdf", b"%PDF-1.7\ncontent", "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    document_id = uploaded.json()["id"]

    for email in (str(baseline["bob_email"]), str(baseline["david_email"])):
        denied_upload = client.post(
            f"/api/cases/{case_id}/documents",
            user=email,
            files={"file": ("intrusion.pdf", b"%PDF-1.7\ncontent", "application/pdf")},
        )
        assert denied_upload.status_code == 403

        denied_download = client.get(
            f"/api/cases/{case_id}/documents/{document_id}",
            user=email,
        )
        assert denied_download.status_code == 403
