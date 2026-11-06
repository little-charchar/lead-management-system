"""CORS behavior for supported local frontend origins."""

from typing import Any


def test_local_frontend_origins_can_send_demo_user_header(client: Any) -> None:
    """Both common local frontend URLs pass the custom auth header preflight."""
    for origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
        response = client.request(
            "OPTIONS",
            "/api/leads",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "x-demo-user-email",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin


def test_local_frontend_can_read_pagination_total_header(client: Any) -> None:
    """The browser can read the custom total-count header on paginated lists."""
    response = client.get(
        "/api/leads",
        user="jane@plaintiff.com",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert "x-total-count" in response.headers["access-control-expose-headers"].lower()
