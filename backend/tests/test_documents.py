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
    assert plaintiff_document["uploader"]["role"] == "PLAINTIFF"
    assert plaintiff_document["uploader"]["name"] == "Jane Plaintiff"

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
    assert staff_upload.json()["uploader"]["name"] == "Sarah Apex"
    assert staff_upload.json()["uploader"]["law_firm_name"] == "Apex Legal"

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

    admin_preview = client.get(
        f"/api/cases/{case_id}/documents/{plaintiff_document['id']}",
        user=str(baseline["admin_email"]),
    )
    assert admin_preview.status_code == 200
    assert admin_preview.content.startswith(b"%PDF-")


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


def test_document_access_tracks_uploader_firm_after_case_reassignment(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """Keep prior firm files private while plaintiff files follow the case."""
    case_id = _create_accepted_case(client, baseline)

    def upload(email: str, file_name: str) -> int:
        response = client.post(
            f"/api/cases/{case_id}/documents",
            user=email,
            files={"file": (file_name, b"%PDF-1.7\ncontent", "application/pdf")},
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    plaintiff_document_id = upload(str(baseline["jane_email"]), "plaintiff.pdf")
    old_firm_document_id = upload(str(baseline["sarah_email"]), "apex.pdf")

    reassigned = client.post(
        f"/api/admin/cases/{case_id}/reassign",
        user=str(baseline["admin_email"]),
        json={"target_firm_id": baseline["beacon_id"]},
    )
    assert reassigned.status_code == 200, reassigned.text

    admin_document_id = upload(str(baseline["admin_email"]), "admin.pdf")
    new_firm_case = client.get(
        f"/api/cases/{case_id}",
        user=str(baseline["david_email"]),
    )
    assert new_firm_case.status_code == 200
    assert {
        document["id"] for document in new_firm_case.json()["documents"]
    } == {plaintiff_document_id, admin_document_id}
    new_firm_summary = client.get(
        "/api/cases",
        user=str(baseline["david_email"]),
    )
    assert new_firm_summary.status_code == 200
    assert new_firm_summary.json()[0]["document_count"] == 2

    plaintiff_case = client.get(
        f"/api/cases/{case_id}",
        user=str(baseline["jane_email"]),
    )
    assert plaintiff_case.status_code == 200
    assert {
        document["id"] for document in plaintiff_case.json()["documents"]
    } == {plaintiff_document_id, admin_document_id}
    plaintiff_summary = client.get(
        "/api/cases/mine",
        user=str(baseline["jane_email"]),
    )
    assert plaintiff_summary.status_code == 200
    assert plaintiff_summary.json()[0]["document_count"] == 2
    old_firm_case = client.get(
        f"/api/cases/{case_id}",
        user=str(baseline["sarah_email"]),
    )
    assert old_firm_case.status_code == 403

    old_firm_document = client.get(
        f"/api/cases/{case_id}/documents/{old_firm_document_id}",
        user=str(baseline["sarah_email"]),
    )
    assert old_firm_document.status_code == 200
    assert old_firm_document.content.startswith(b"%PDF-")
    for email in (str(baseline["jane_email"]), str(baseline["david_email"])):
        denied = client.get(
            f"/api/cases/{case_id}/documents/{old_firm_document_id}",
            user=email,
        )
        assert denied.status_code == 404

    new_firm_document_id = upload(
        str(baseline["david_email"]),
        "beacon.pdf",
    )
    for email in (
        str(baseline["jane_email"]),
        str(baseline["david_email"]),
        str(baseline["admin_email"]),
    ):
        allowed = client.get(
            f"/api/cases/{case_id}/documents/{new_firm_document_id}",
            user=email,
        )
        assert allowed.status_code == 200
    denied_to_old_firm = client.get(
        f"/api/cases/{case_id}/documents/{new_firm_document_id}",
        user=str(baseline["sarah_email"]),
    )
    assert denied_to_old_firm.status_code == 403

    denied_admin_document_to_old_firm = client.get(
        f"/api/cases/{case_id}/documents/{admin_document_id}",
        user=str(baseline["sarah_email"]),
    )
    assert denied_admin_document_to_old_firm.status_code == 403

    admin_case = client.get(
        f"/api/cases/{case_id}",
        user=str(baseline["admin_email"]),
    )
    assert admin_case.status_code == 200
    assert len(admin_case.json()["documents"]) == 4
