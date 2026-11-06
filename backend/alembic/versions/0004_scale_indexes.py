"""Add indexes for paginated queries and substring search at scale.

Revision ID: 0004_scale_indexes
Revises: 0003_lead_title
Create Date: 2026-11-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004_scale_indexes"
down_revision: str | None = "0003_lead_title"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


_BTREE_INDEXES = (
    ("ix_leads_assigned_firm_status_created", "leads", "assigned_firm_id, status, created_at, id"),
    ("ix_leads_plaintiff_created", "leads", "plaintiff_id, created_at, id"),
    ("ix_leads_status_created", "leads", "status, created_at, id"),
    ("ix_leads_created", "leads", "created_at, id"),
    ("ix_cases_firm_status_updated", "cases", "assigned_firm_id, status, updated_at, id"),
    ("ix_cases_firm_updated", "cases", "assigned_firm_id, updated_at, id"),
    ("ix_cases_status_updated", "cases", "status, updated_at, id"),
    ("ix_cases_updated", "cases", "updated_at, id"),
    ("ix_documents_case_created", "documents", "case_id, created_at, id"),
    ("ix_lead_attachments_lead_created", "lead_attachments", "lead_id, created_at, id"),
    ("ix_notes_case_firm_created", "notes", "case_id, author_firm_id, created_at, id"),
    ("ix_audit_logs_entity_type_entity_id_created_at", "audit_logs", "entity_type, entity_id, created_at, id"),
)

_TRIGRAM_INDEXES = (
    ("ix_leads_title_trgm", "leads", "title"),
    ("ix_leads_category_trgm", "leads", "category"),
    ("ix_leads_region_trgm", "leads", "region"),
    ("ix_leads_description_trgm", "leads", "description"),
    ("ix_users_name_trgm", "users", "name"),
    ("ix_users_email_trgm", "users", "email"),
)


def upgrade() -> None:
    """Create production query indexes without blocking table writes."""
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.drop_index("ix_leads_assigned_firm_id_status", table_name="leads")
    op.drop_index("ix_documents_case_id", table_name="documents")
    op.drop_index("ix_lead_attachments_lead_id", table_name="lead_attachments")
    op.drop_index("ix_notes_case_id_author_firm_id", table_name="notes")
    op.drop_index(
        "ix_audit_logs_entity_type_entity_id_created_at",
        table_name="audit_logs",
    )

    with op.get_context().autocommit_block():
        for name, table, columns in _BTREE_INDEXES:
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} "
                f"ON {table} ({columns})"
            )
        for name, table, column in _TRIGRAM_INDEXES:
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} "
                f"ON {table} USING gin ({column} gin_trgm_ops)"
            )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_users_email_lower "
            "ON users (lower(email))"
        )


def downgrade() -> None:
    """Remove indexes and restore the original single-column indexes."""
    if op.get_bind().dialect.name != "postgresql":
        return

    with op.get_context().autocommit_block():
        for name, _, _ in reversed(_TRIGRAM_INDEXES):
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
        for name, _, _ in reversed(_BTREE_INDEXES):
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_users_email_lower")

    op.create_index(
        "ix_leads_assigned_firm_id_status",
        "leads",
        ["assigned_firm_id", "status"],
    )
    op.create_index("ix_documents_case_id", "documents", ["case_id"])
    op.create_index(
        "ix_lead_attachments_lead_id",
        "lead_attachments",
        ["lead_id"],
    )
    op.create_index(
        "ix_notes_case_id_author_firm_id",
        "notes",
        ["case_id", "author_firm_id"],
    )
    op.create_index(
        "ix_audit_logs_entity_type_entity_id_created_at",
        "audit_logs",
        ["entity_type", "entity_id", "created_at"],
    )
