from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.csrf import verify_origin
from app.core.db import get_db
from app.core.dependencies import COOKIE_NAME, get_business_id, get_current_admin_and_session, get_session_factory
from app.core.rate_limit import RateLimiter, RateLimitExceededError, get_subject_hash
from app.models.admin_session import AdminSession
from app.models.admin_user import AdminUser
from app.models.business import Business
from app.schemas.admin import AdminInfo, AuthResponse, AuthResponseData, BusinessInfo, LoginRequest
from app.services.auth_service import AuthError, AuthService

router = APIRouter(prefix="/auth", tags=["Admin Auth"])


def _set_session_cookie(response: Response, raw_token: str) -> None:
    is_prod = settings.APP_ENV.lower() == "production"
    max_age = settings.ADMIN_SESSION_TTL_HOURS * 3600
    response.set_cookie(
        key=COOKIE_NAME,
        value=raw_token,
        max_age=max_age,
        path="/api/admin",
        httponly=True,
        samesite="lax",
        secure=is_prod,
    )


def _clear_session_cookie(response: Response) -> None:
    is_prod = settings.APP_ENV.lower() == "production"
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/api/admin",
        httponly=True,
        samesite="lax",
        secure=is_prod,
    )


@router.post("/login", response_model=AuthResponse, dependencies=[Depends(verify_origin)])
def login(
    payload: LoginRequest,
    response: Response,
    http_request: Request,
    db: Annotated[Session, Depends(get_db)],
    session_factory: Annotated[Callable[[], Session], Depends(get_session_factory)],
) -> AuthResponse:
    # 1. Rate limiting before credentials evaluation
    client_ip = http_request.client.host if http_request.client else None
    subject_hash = get_subject_hash(client_ip, settings.RATE_LIMIT_SECRET)
    limiter = RateLimiter(session_factory=session_factory, secret=settings.RATE_LIMIT_SECRET)
    is_allowed, _, retry_after = limiter.consume(
        endpoint="admin_login",
        subject_hash=subject_hash,
        limit=10,
        window_seconds=900,
    )
    if not is_allowed:
        raise RateLimitExceededError(retry_after=retry_after)

    business_id = get_business_id()
    business = db.query(Business).filter(Business.id == business_id).first()

    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "business_not_found", "message": "El negocio configurado no existe."},
        )

    auth_service = AuthService(db)
    try:
        admin_user, raw_token = auth_service.authenticate(
            email=payload.email,
            password=payload.password,
            business_id=business_id,
        )
    except AuthError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"code": e.code, "message": e.message},
        )

    _set_session_cookie(response, raw_token)

    return AuthResponse(
        data=AuthResponseData(
            admin=AdminInfo(
                id=admin_user.id,
                display_name=admin_user.display_name,
                email=admin_user.email,
            ),
            business=BusinessInfo(
                name=business.name,
                timezone=business.timezone,
                locale=business.locale,
            ),
        )
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_origin)])
def logout(
    response: Response,
    admin_and_session: Annotated[tuple[AdminUser, AdminSession], Depends(get_current_admin_and_session)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    _admin_user, session = admin_and_session
    business_id = get_business_id()

    auth_service = AuthService(db)
    auth_service.revoke_session(session_id=session.id, business_id=business_id)

    _clear_session_cookie(response)


@router.get("/me", response_model=AuthResponse)
def me(
    admin_and_session: Annotated[tuple[AdminUser, AdminSession], Depends(get_current_admin_and_session)],
    db: Annotated[Session, Depends(get_db)],
) -> AuthResponse:
    admin_user, _session = admin_and_session
    business_id = get_business_id()

    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "business_not_found", "message": "El negocio configurado no existe."},
        )

    return AuthResponse(
        data=AuthResponseData(
            admin=AdminInfo(
                id=admin_user.id,
                display_name=admin_user.display_name,
                email=admin_user.email,
            ),
            business=BusinessInfo(
                name=business.name,
                timezone=business.timezone,
                locale=business.locale,
            ),
        )
    )
