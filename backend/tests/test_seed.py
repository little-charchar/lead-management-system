"""Tests for repeatable, schema-preserving demo data seeding."""

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import AuditLog, Case, LawFirm, Lead, Note, User
from app.seed import reset_database_data, seed_database


def test_seed_loads_larger_dataset_and_can_be_repeated(db_engine: Engine) -> None:
    """Seeding creates the expected demo volume and reset removes prior rows."""
    with Session(db_engine) as db:
        seed_database(db)
        assert db.scalar(select(func.count()).select_from(Lead)) == 100
        assert db.scalar(select(func.count()).select_from(Case)) == 40
        assert db.scalar(select(func.count()).select_from(Note)) == 40
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 128
        assert db.scalar(select(func.count()).select_from(LawFirm)) == 3
        assert db.scalar(select(func.count()).select_from(User)) == 19

        reset_database_data(db)
        seed_database(db)
        assert db.scalar(select(func.count()).select_from(Lead)) == 100
        assert db.scalar(select(func.count()).select_from(Case)) == 40
        assert db.scalar(select(func.count()).select_from(Note)) == 40
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 128
