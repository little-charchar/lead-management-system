"""Add PDF attachments to leads before case acceptance.

Revision ID: 0002_lead_attachments
Revises: 0001_initial_schema
Create Date: 2026-11-06
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002_lead_attachments"
down_revision: str | None = "0001_initial_schema"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Create the lead attachment metadata table."""
    op.create_table(
        "lead_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "mime_type",
            sa.String(length=255),
            server_default=sa.text("'application/pdf'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_lead_attachments_lead_id",
        "lead_attachments",
        ["lead_id"],
    )


def downgrade() -> None:
    """Drop lead attachments metadata."""
    op.drop_index("ix_lead_attachments_lead_id", table_name="lead_attachments")
    op.drop_table("lead_attachments")
