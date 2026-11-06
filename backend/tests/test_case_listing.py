"""Tests for firm-scoped, searchable active case listings."""

from typing import Any


def _accept_lead(client: Any, email: str, name: str, title: str) -> int:
    """Create and accept a routed lead, returning the case ID."""
    submitted = client.post(
        "/api/leads",
        user=email,
        json={
            "plaintiff_name": name,
            "email": email,
            "title": title,
            "category": "PERSONAL_INJURY",
            "region": "NY",
            "description": "A sufficiently detailed legal inquiry for case listing.",
        },
    )
    assert submitted.status_code == 201, submitted.text
    accepted = client.post(
        f"/api/leads/{submitted.json()['id']}/accept",
        user="sarah@apexlegal.com",
    )
    assert accepted.status_code == 201, accepted.text
    return accepted.json()["id"]


def test_firm_case_listing_is_scoped_searchable_and_paginated(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """Firm staff see their own active cases and can search client/title."""
    first_case_id = _accept_lead(
        client,
        str(baseline["jane_email"]),
        "Jane Plaintiff",
        "Collision at Main Street",
    )
    second_case_id = _accept_lead(
        client,
        str(baseline["bob_email"]),
        "Bob Plaintiff",
        "Workplace injury review",
    )

    all_cases = client.get(
        "/api/cases?limit=10",
        user=str(baseline["sarah_email"]),
    )
    assert all_cases.status_code == 200, all_cases.text
    assert all_cases.headers["X-Total-Count"] == "2"
    assert {item["id"] for item in all_cases.json()} == {
        first_case_id,
        second_case_id,
    }
    assert all(
        "documents" not in item
        and "notes" not in item
        and "document_count" in item
        for item in all_cases.json()
    )

    case_detail = client.get(
        f"/api/cases/{first_case_id}",
        user=str(baseline["sarah_email"]),
    )
    assert case_detail.status_code == 200, case_detail.text
    assert "documents" in case_detail.json()
    assert "notes" in case_detail.json()

    search_by_name = client.get(
        "/api/cases?search=Jane&limit=10",
        user=str(baseline["sarah_email"]),
    )
    assert search_by_name.status_code == 200, search_by_name.text
    assert search_by_name.headers["X-Total-Count"] == "1"
    assert [item["id"] for item in search_by_name.json()] == [first_case_id]

    search_by_title = client.get(
        "/api/cases?search=Workplace&limit=10",
        user=str(baseline["sarah_email"]),
    )
    assert search_by_title.status_code == 200, search_by_title.text
    assert [item["id"] for item in search_by_title.json()] == [second_case_id]

    other_firm = client.get("/api/cases?limit=10", user=str(baseline["david_email"]))
    assert other_firm.status_code == 200, other_firm.text
    assert other_firm.json() == []
    assert other_firm.headers["X-Total-Count"] == "0"

    invalid_page_size = client.get(
        "/api/cases?limit=101",
        user=str(baseline["sarah_email"]),
    )
    assert invalid_page_size.status_code == 422


def test_plaintiff_case_listing_is_scoped_searchable_and_paginated(
    client: Any, baseline: dict[str, int | str]
) -> None:
    """Plaintiffs can search and page their cases without reading other matters."""
    first_case_id = _accept_lead(
        client,
        str(baseline["jane_email"]),
        "Jane Plaintiff",
        "First collision",
    )
    second_case_id = _accept_lead(
        client,
        str(baseline["jane_email"]),
        "Jane Plaintiff",
        "Second collision",
    )
    _accept_lead(
        client,
        str(baseline["bob_email"]),
        "Bob Plaintiff",
        "Other plaintiff collision",
    )

    first_page = client.get(
        "/api/cases/mine?search=New%20York&limit=1&offset=0",
        user=str(baseline["jane_email"]),
    )
    second_page = client.get(
        "/api/cases/mine?limit=1&offset=1",
        user=str(baseline["jane_email"]),
    )
    assert first_page.status_code == 200, first_page.text
    assert second_page.status_code == 200, second_page.text
    assert first_page.headers["X-Total-Count"] == "2"
    assert second_page.headers["X-Total-Count"] == "2"
    assert len(first_page.json()) == len(second_page.json()) == 1
    assert {
        first_page.json()[0]["id"],
        second_page.json()[0]["id"],
    } == {first_case_id, second_case_id}
    assert "notes" not in first_page.json()[0]
    assert "documents" not in first_page.json()[0]
    assert "document_count" in first_page.json()[0]

    denied = client.get(
        "/api/cases/mine",
        user=str(baseline["admin_email"]),
    )
    assert denied.status_code == 403
