"""Create the initial legal lead-management schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-04
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

user_role = postgresql.ENUM(
    "PLAINTIFF", "ATTORNEY", "PARALEGAL", "ADMIN", name="user_role"
)
lead_status = postgresql.ENUM(
    "UNASSIGNED",
    "PENDING_REVIEW",
    "ACCEPTED",
    "DECLINED",
    name="lead_status",
)
case_status = postgresql.ENUM(
    "INTAKE", "INVESTIGATION", "DISCOVERY", "SETTLED", "CLOSED", name="case_status"
)


def upgrade() -> None:
    """Create tables, foreign keys, enums, and indexes."""
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    lead_status.create(bind, checkfirst=True)
    case_status.create(bind, checkfirst=True)

    op.create_table(
        "law_firms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_law_firms_name"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("law_firm_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["law_firm_id"], ["law_firms.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "routing_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.Column("law_firm_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["law_firm_id"], ["law_firms.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "category", "region", name="uq_routing_rules_category_region"
        ),
    )
    op.create_index("ix_routing_rules_category", "routing_rules", ["category"])
    op.create_index("ix_routing_rules_region", "routing_rules", ["region"])
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plaintiff_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "status",
            lead_status,
            server_default=sa.text("'UNASSIGNED'"),
            nullable=False,
        ),
        sa.Column("assigned_firm_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["assigned_firm_id"], ["law_firms.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["plaintiff_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_leads_assigned_firm_id_status",
        "leads",
        ["assigned_firm_id", "status"],
    )
    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("assigned_firm_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            case_status,
            server_default=sa.text("'INTAKE'"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["assigned_firm_id"], ["law_firms.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lead_id", name="uq_cases_lead_id"),
    )
    op.create_index("ix_cases_assigned_firm_id", "cases", ["assigned_firm_id"])
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
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
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_case_id", "documents", ["case_id"])
    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("author_firm_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["author_firm_id"], ["law_firms.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notes_case_id_author_firm_id",
        "notes",
        ["case_id", "author_firm_id"],
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("previous_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_logs_entity_type_entity_id_created_at",
        "audit_logs",
        ["entity_type", "entity_id", "created_at"],
    )


def downgrade() -> None:
    """Drop the schema objects created by this revision."""
    op.drop_index(
        "ix_audit_logs_entity_type_entity_id_created_at", table_name="audit_logs"
    )
    op.drop_table("audit_logs")
    op.drop_index("ix_notes_case_id_author_firm_id", table_name="notes")
    op.drop_table("notes")
    op.drop_index("ix_documents_case_id", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_cases_assigned_firm_id", table_name="cases")
    op.drop_table("cases")
    op.drop_index("ix_leads_assigned_firm_id_status", table_name="leads")
    op.drop_table("leads")
    op.drop_index("ix_routing_rules_region", table_name="routing_rules")
    op.drop_index("ix_routing_rules_category", table_name="routing_rules")
    op.drop_table("routing_rules")
    op.drop_table("users")
    op.drop_table("law_firms")
    case_status.drop(op.get_bind(), checkfirst=True)
    lead_status.drop(op.get_bind(), checkfirst=True)
    user_role.drop(op.get_bind(), checkfirst=True)
