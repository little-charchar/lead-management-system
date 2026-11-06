"""Track the firm that uploaded each case document.

Revision ID: 0005_document_firm_ownership
Revises: 0004_scale_indexes
Create Date: 2026-11-06
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0005_document_firm_ownership"
down_revision: str | None = "0004_scale_indexes"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Add and backfill the firm ownership snapshot for case documents."""
    op.add_column(
        "documents",
        sa.Column("uploaded_by_firm_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_documents_uploaded_by_firm_id_law_firms",
        "documents",
        "law_firms",
        ["uploaded_by_firm_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        """
        UPDATE documents
        SET uploaded_by_firm_id = users.law_firm_id
        FROM users
        WHERE documents.uploaded_by_id = users.id
          AND users.role IN ('ATTORNEY', 'PARALEGAL')
        """
    )
    op.create_index(
        "ix_documents_case_uploader_firm_created",
        "documents",
        ["case_id", "uploaded_by_firm_id", "created_at", "id"],
    )


def downgrade() -> None:
    """Remove document firm ownership metadata."""
    op.drop_index(
        "ix_documents_case_uploader_firm_created",
        table_name="documents",
    )
    op.drop_constraint(
        "fk_documents_uploaded_by_firm_id_law_firms",
        "documents",
        type_="foreignkey",
    )
    op.drop_column("documents", "uploaded_by_firm_id")
