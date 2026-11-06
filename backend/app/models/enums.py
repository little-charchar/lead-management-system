"""String enums used by the database models."""

from enum import StrEnum


class UserRole(StrEnum):
    """Roles available to system users."""

    PLAINTIFF = "PLAINTIFF"
    ATTORNEY = "ATTORNEY"
    PARALEGAL = "PARALEGAL"
    ADMIN = "ADMIN"


class LeadStatus(StrEnum):
    """Lifecycle states for submitted leads."""

    UNASSIGNED = "UNASSIGNED"
    PENDING_REVIEW = "PENDING_REVIEW"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"


class CaseStatus(StrEnum):
    """Lifecycle states for accepted cases."""

    INTAKE = "INTAKE"
    INVESTIGATION = "INVESTIGATION"
    DISCOVERY = "DISCOVERY"
    SETTLED = "SETTLED"
    CLOSED = "CLOSED"


class AuditAction(StrEnum):
    """Supported audit-log actions."""

    AUTO_ROUTED = "AUTO_ROUTED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    REASSIGNED = "REASSIGNED"
    STATUS_CHANGED = "STATUS_CHANGED"
