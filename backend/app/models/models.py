"""SQLAlchemy ORM models for legal lead and case management."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import CaseStatus, LeadStatus, UserRole


def enum_values(
    enum_class: type[UserRole] | type[LeadStatus] | type[CaseStatus],
) -> list[str]:
    """Return enum values for storage rather than Python enum member names."""
    return [member.value for member in enum_class]


class LawFirm(Base):
    """A law firm that can receive leads and own case activity."""

    __tablename__ = "law_firms"
    __table_args__ = (
        UniqueConstraint("name", name="uq_law_firms_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    users: Mapped[list[User]] = relationship(back_populates="law_firm")
    routing_rules: Mapped[list[RoutingRule]] = relationship(
        back_populates="law_firm", cascade="all, delete-orphan"
    )
    assigned_leads: Mapped[list[Lead]] = relationship(
        back_populates="assigned_firm"
    )
    assigned_cases: Mapped[list[Case]] = relationship(
        back_populates="assigned_firm"
    )
    notes: Mapped[list[Note]] = relationship(back_populates="author_firm")


class User(Base):
    """A plaintiff, law-firm staff member, or system administrator."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    law_firm_id: Mapped[int | None] = mapped_column(
        ForeignKey("law_firms.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    law_firm: Mapped[LawFirm | None] = relationship(back_populates="users")
    leads: Mapped[list[Lead]] = relationship(
        back_populates="plaintiff", foreign_keys="Lead.plaintiff_id"
    )
    uploaded_documents: Mapped[list[Document]] = relationship(
        back_populates="uploaded_by", foreign_keys="Document.uploaded_by_id"
    )
    authored_notes: Mapped[list[Note]] = relationship(
        back_populates="author", foreign_keys="Note.author_id"
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        back_populates="actor", foreign_keys="AuditLog.actor_id"
    )


    @property
    def law_firm_name(self) -> str | None:
        """Return the uploader's firm name when a firm relationship exists."""
        return self.law_firm.name if self.law_firm is not None else None


class RoutingRule(Base):
    """A deterministic category-and-region-to-firm routing rule."""

    __tablename__ = "routing_rules"
    __table_args__ = (
        UniqueConstraint("category", "region", name="uq_routing_rules_category_region"),
        Index("ix_routing_rules_category", "category"),
        Index("ix_routing_rules_region", "region"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    law_firm_id: Mapped[int] = mapped_column(
        ForeignKey("law_firms.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    law_firm: Mapped[LawFirm] = relationship(back_populates="routing_rules")


class Lead(Base):
    """A plaintiff's legal inquiry before or after firm routing."""

    __tablename__ = "leads"
    __table_args__ = (
        Index(
            "ix_leads_assigned_firm_status_created",
            "assigned_firm_id",
            "status",
            "created_at",
            "id",
        ),
        Index(
            "ix_leads_plaintiff_created",
            "plaintiff_id",
            "created_at",
            "id",
        ),
        Index("ix_leads_status_created", "status", "created_at", "id"),
        Index("ix_leads_created", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plaintiff_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default="Legal inquiry",
        server_default=text("'Legal inquiry'"),
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[LeadStatus] = mapped_column(
        Enum(
            LeadStatus,
            name="lead_status",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=LeadStatus.UNASSIGNED,
        server_default=text("'UNASSIGNED'"),
    )
    assigned_firm_id: Mapped[int | None] = mapped_column(
        ForeignKey("law_firms.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    plaintiff: Mapped[User] = relationship(
        back_populates="leads", foreign_keys=[plaintiff_id]
    )
    assigned_firm: Mapped[LawFirm | None] = relationship(
        back_populates="assigned_leads", foreign_keys=[assigned_firm_id]
    )
    case: Mapped[Case | None] = relationship(
        back_populates="lead",
        cascade="all, delete-orphan",
        uselist=False,
    )
    attachments: Mapped[list[LeadAttachment]] = relationship(
        back_populates="lead", cascade="all, delete-orphan"
    )


class Case(Base):
    """A case created from an accepted lead and assigned to a law firm."""

    __tablename__ = "cases"
    __table_args__ = (
        UniqueConstraint("lead_id", name="uq_cases_lead_id"),
        Index(
            "ix_cases_firm_status_updated",
            "assigned_firm_id",
            "status",
            "updated_at",
            "id",
        ),
        Index("ix_cases_firm_updated", "assigned_firm_id", "updated_at", "id"),
        Index("ix_cases_status_updated", "status", "updated_at", "id"),
        Index("ix_cases_updated", "updated_at", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    assigned_firm_id: Mapped[int] = mapped_column(
        ForeignKey("law_firms.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[CaseStatus] = mapped_column(
        Enum(
            CaseStatus,
            name="case_status",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=CaseStatus.INTAKE,
        server_default=text("'INTAKE'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    lead: Mapped[Lead] = relationship(back_populates="case")
    assigned_firm: Mapped[LawFirm] = relationship(
        back_populates="assigned_cases"
    )
    documents: Mapped[list[Document]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    notes: Mapped[list[Note]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )


class Document(Base):
    """Document metadata; binary content is stored outside the database."""

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_case_created", "case_id", "created_at", "id"),
        Index(
            "ix_documents_case_uploader_firm_created",
            "case_id",
            "uploaded_by_firm_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), nullable=False
    )
    uploaded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    uploaded_by_firm_id: Mapped[int | None] = mapped_column(
        ForeignKey("law_firms.id", ondelete="SET NULL"), nullable=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="application/pdf",
        server_default=text("'application/pdf'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    case: Mapped[Case] = relationship(back_populates="documents")
    uploaded_by: Mapped[User | None] = relationship(
        back_populates="uploaded_documents", foreign_keys=[uploaded_by_id]
    )
    uploaded_by_firm: Mapped[LawFirm | None] = relationship()


class LeadAttachment(Base):
    """PDF metadata attached to a lead before or after case acceptance."""

    __tablename__ = "lead_attachments"
    __table_args__ = (
        Index("ix_lead_attachments_lead_created", "lead_id", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    uploaded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="application/pdf",
        server_default=text("'application/pdf'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    lead: Mapped[Lead] = relationship(back_populates="attachments")
    uploaded_by: Mapped[User | None] = relationship(foreign_keys=[uploaded_by_id])


class Note(Base):
    """A case note visible only within its authoring law firm."""

    __tablename__ = "notes"
    __table_args__ = (
        Index(
            "ix_notes_case_firm_created",
            "case_id",
            "author_firm_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    author_firm_id: Mapped[int] = mapped_column(
        ForeignKey("law_firms.id", ondelete="RESTRICT"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    case: Mapped[Case] = relationship(back_populates="notes")
    author: Mapped[User | None] = relationship(
        back_populates="authored_notes", foreign_keys=[author_id]
    )
    author_firm: Mapped[LawFirm] = relationship(back_populates="notes")


class AuditLog(Base):
    """Immutable state-change history for lead and case entities."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index(
            "ix_audit_logs_entity_type_entity_id_created_at",
            "entity_type",
            "entity_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    previous_state: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    new_state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    actor: Mapped[User | None] = relationship(
        back_populates="audit_logs", foreign_keys=[actor_id]
    )


Index("ix_users_email_lower", func.lower(User.email))
