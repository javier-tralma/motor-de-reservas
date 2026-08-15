import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal, get_db
from app.core.rate_limit import RateLimiter
from app.models.admin_session import AdminSession
from app.models.admin_user import AdminUser
from app.services.auth_service import AuthError, AuthService

COOKIE_NAME = "booking_admin_session"


def get_session_factory() -> Callable[[], Session]:
    """Dependency providing a factory for creating independent database sessions."""
    return SessionLocal


def get_rate_limiter(
    session_factory: Annotated[Callable[[], Session], Depends(get_session_factory)],
) -> RateLimiter:
    """Dependency providing a RateLimiter backed by independent session lifecycle."""
    return RateLimiter(session_factory=session_factory, secret=settings.RATE_LIMIT_SECRET)


def get_business_id() -> uuid.UUID:
    """Return configured BUSINESS_ID as UUID."""
    return uuid.UUID(settings.BUSINESS_ID)


def get_current_admin_and_session(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> tuple[AdminUser, AdminSession]:
    """Dependency that extracts cookie and validates session."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "session_required",
                "message": "Se requiere autenticación para acceder a este recurso.",
            },
        )

    business_id = get_business_id()
    auth_service = AuthService(db)

    try:
        admin_user, session = auth_service.validate_session(token=token, business_id=business_id)
        return admin_user, session
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": e.code,
                "message": e.message,
            },
        )


def get_current_admin(
    admin_and_session: Annotated[tuple[AdminUser, AdminSession], Depends(get_current_admin_and_session)],
) -> AdminUser:
    """Dependency returning only the authenticated AdminUser."""
    return admin_and_session[0]


def get_utc_now() -> datetime:
    """Injectable UTC current time."""
    return datetime.now(timezone.utc)
