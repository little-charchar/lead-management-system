"""Shared fixtures for isolated API and database tests."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from starlette.responses import Response

from app.database import Base, get_db
from app.main import app
from app.models import LawFirm, RoutingRule, User, UserRole
from app.services import case_service


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(
    type_: JSONB, compiler: Any, **kwargs: Any
) -> str:
    """Compile the PostgreSQL JSONB column as SQLite's JSON storage type."""
    return "JSON"


class DemoClient:
    """TestClient wrapper that adds the demo persona header to requests."""

    def __init__(self, client: TestClient) -> None:
        self._client = client

    def request(
        self,
        method: str,
        url: str,
        *,
        user: str | None = None,
        **kwargs: Any,
    ) -> Response:
        """Send a request with an optional demo-user persona."""
        headers = dict(kwargs.pop("headers", {}) or {})
        if user is not None:
            headers["X-Demo-User-Email"] = user
        return self._client.request(method, url, headers=headers, **kwargs)

    def get(self, url: str, *, user: str | None = None, **kwargs: Any) -> Response:
        """Send a GET request as the requested demo persona."""
        return self.request("GET", url, user=user, **kwargs)

    def post(self, url: str, *, user: str | None = None, **kwargs: Any) -> Response:
        """Send a POST request as the requested demo persona."""
        return self.request("POST", url, user=user, **kwargs)

    def patch(
        self, url: str, *, user: str | None = None, **kwargs: Any
    ) -> Response:
        """Send a PATCH request as the requested demo persona."""
        return self.request("PATCH", url, user=user, **kwargs)


@pytest.fixture
def db_engine() -> Iterator[Engine]:
    """Create and dispose an isolated in-memory SQLite database per test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        json_serializer=json.dumps,
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(connection: Any, _: Any) -> None:
        """Keep SQLite foreign-key behavior consistent with PostgreSQL."""
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(autouse=True)
def isolate_upload_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep uploaded documents in a temporary directory for each test."""
    monkeypatch.setattr(case_service, "UPLOAD_DIRECTORY", tmp_path)


@pytest.fixture
def baseline(db_engine: Engine) -> dict[str, int | str]:
    """Seed baseline firms, demo personas, and deterministic routing rules."""
    with Session(db_engine) as db:
        apex = LawFirm(name="Apex Legal")
        beacon = LawFirm(name="Beacon Rights")
        db.add_all([apex, beacon])
        db.flush()

        jane = User(
            name="Jane Plaintiff",
            email="jane@plaintiff.com",
            role=UserRole.PLAINTIFF,
        )
        bob = User(
            name="Bob Plaintiff",
            email="bob@plaintiff.com",
            role=UserRole.PLAINTIFF,
        )
        sarah = User(
            name="Sarah Apex",
            email="sarah@apexlegal.com",
            role=UserRole.ATTORNEY,
            law_firm_id=apex.id,
        )
        david = User(
            name="David Beacon",
            email="david@beaconrights.com",
            role=UserRole.ATTORNEY,
            law_firm_id=beacon.id,
        )
        admin = User(
            name="Elena Admin",
            email="admin@system.com",
            role=UserRole.ADMIN,
        )
        db.add_all([jane, bob, sarah, david, admin])
        db.add_all(
            [
                RoutingRule(
                    category="PERSONAL_INJURY",
                    region="NY",
                    law_firm_id=apex.id,
                ),
                RoutingRule(
                    category="LABOR",
                    region="CA",
                    law_firm_id=beacon.id,
                ),
            ]
        )
        db.commit()
        return {
            "apex_id": apex.id,
            "beacon_id": beacon.id,
            "jane_email": jane.email,
            "bob_email": bob.email,
            "sarah_email": sarah.email,
            "david_email": david.email,
            "admin_email": admin.email,
        }


@pytest.fixture
def client(
    db_engine: Engine,
    baseline: dict[str, int | str],
) -> Iterator[DemoClient]:
    """Provide an HTTP client backed by the isolated, seeded database."""
    del baseline

    def override_get_db() -> Iterator[Session]:
        with Session(db_engine, expire_on_commit=False) as db:
            yield db

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield DemoClient(test_client)
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override
