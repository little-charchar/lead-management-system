"""Authentication and role-based authorization dependencies."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole

DatabaseSession = Annotated[Session, Depends(get_db)]


def _find_user(email: str | None, db: Session) -> User:
    """Resolve a demo persona by email or reject an unknown identity."""
    if email is None or not email.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid X-Demo-User-Email header is required.",
            headers={"WWW-Authenticate": "X-Demo-User-Email"},
        )
    user = db.scalar(
        select(User).where(func.lower(User.email) == email.strip().lower())
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown demo user.",
            headers={"WWW-Authenticate": "X-Demo-User-Email"},
        )
    return user


def get_current_user(
    x_demo_user_email: Annotated[str, Header()],
    db: DatabaseSession,
) -> User:
    """Authenticate a request using the X-Demo-User-Email persona header."""
    return _find_user(x_demo_user_email, db)


def get_optional_current_user(
    x_demo_user_email: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> User | None:
    """Resolve an optional persona header for the public intake endpoint."""
    if x_demo_user_email is None:
        return None
    return _find_user(x_demo_user_email, db)


def get_current_plaintiff(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require the authenticated user to be a plaintiff."""
    if current_user.role != UserRole.PLAINTIFF:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Plaintiff access is required.",
        )
    return current_user


def get_current_firm_staff(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require attorney or paralegal membership in a law firm."""
    if current_user.role not in {UserRole.ATTORNEY, UserRole.PARALEGAL}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Law-firm staff access is required.",
        )
    if current_user.law_firm_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The staff account is not associated with a law firm.",
        )
    return current_user


def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require the authenticated user to be an administrator."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required.",
        )
    return current_user


require_plaintiff = get_current_plaintiff
require_firm_staff = get_current_firm_staff
require_admin = get_current_admin
