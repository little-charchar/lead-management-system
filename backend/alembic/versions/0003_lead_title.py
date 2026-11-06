"""Add a summary title to leads.

Revision ID: 0003_lead_title
Revises: 0002_lead_attachments
Create Date: 2026-11-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003_lead_title"
down_revision: str | None = "0002_lead_attachments"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Add and backfill the lead summary title."""
    op.add_column("leads", sa.Column("title", sa.String(length=200), nullable=True))
    op.execute("UPDATE leads SET title = category WHERE title IS NULL")
    op.alter_column(
        "leads",
        "title",
        existing_type=sa.String(length=200),
        nullable=False,
        server_default=sa.text("'Legal inquiry'"),
    )


def downgrade() -> None:
    """Remove lead summary titles."""
    op.drop_column("leads", "title")
