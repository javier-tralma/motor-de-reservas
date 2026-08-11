import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.auth import hash_password, verify_password
from app.core.config import settings
from app.models.admin_session import AdminSession
from app.models.admin_user import AdminUser
from app.models.business import Business
from app.services.auth_service import AuthError, AuthService


@pytest.fixture
def test_business(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Business:
    biz_id = uuid.uuid4()
    monkeypatch.setattr(settings, "BUSINESS_ID", str(biz_id))
    biz = Business(
        id=biz_id,
        name="Estudio Nómada",
        slug=f"estudio-nomada-{uuid.uuid4().hex[:6]}",
        timezone="America/Santiago",
        locale="es-CL",
        email="contacto@estudionomada.cl",
    )
    db_session.add(biz)
    db_session.commit()
    return biz


@pytest.fixture
def test_admin_user(db_session: Session, test_business: Business) -> AdminUser:
    admin = AdminUser(
        business_id=test_business.id,
        email="admin@estudionomada.cl",
        password_hash=hash_password("SuperSecret123"),
        display_name="Javier",
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


def test_password_hashing_and_verification():
    plain = "Password123!"
    hashed = hash_password(plain)

    assert hashed.startswith("$argon2id$")
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_auth_service_authenticate_success(db_session: Session, test_admin_user: AdminUser):
    auth_service = AuthService(db_session)
    admin, raw_token = auth_service.authenticate(
        email="ADMIN@ESTUDIONOMADA.CL ",
        password="SuperSecret123",
        business_id=test_admin_user.business_id,
    )

    assert admin.id == test_admin_user.id
    assert admin.last_login_at is not None
    assert len(raw_token) > 20

    # Ensure raw token is NEVER persisted in DB
    session_db = db_session.query(AdminSession).filter(AdminSession.admin_user_id == admin.id).first()
    assert session_db is not None
    assert session_db.token_hash != raw_token


def test_auth_service_authenticate_invalid_credentials(db_session: Session, test_admin_user: AdminUser):
    auth_service = AuthService(db_session)

    # Email wrong
    with pytest.raises(AuthError) as exc_info:
        auth_service.authenticate(
            email="nonexistent@estudionomada.cl",
            password="SuperSecret123",
            business_id=test_admin_user.business_id,
        )
    assert exc_info.value.code == "invalid_credentials"
    assert exc_info.value.status_code == 401

    # Password wrong
    with pytest.raises(AuthError) as exc_info2:
        auth_service.authenticate(
            email="admin@estudionomada.cl",
            password="WrongPassword",
            business_id=test_admin_user.business_id,
        )
    assert exc_info2.value.code == "invalid_credentials"


def test_auth_service_validate_session_and_expiration(db_session: Session, test_admin_user: AdminUser):
    fixed_now = datetime(2026, 8, 10, 12, 0, 0, tzinfo=timezone.utc)
    auth_service = AuthService(db_session, now=fixed_now)

    admin, raw_token = auth_service.authenticate(
        email="admin@estudionomada.cl",
        password="SuperSecret123",
        business_id=test_admin_user.business_id,
    )

    # Valid token
    validated_user, session = auth_service.validate_session(token=raw_token, business_id=admin.business_id)
    assert validated_user.id == admin.id
    assert session.revoked_at is None

    # Expired token (after 8 hours)
    future_now = fixed_now + timedelta(hours=9)
    future_auth_service = AuthService(db_session, now=future_now)
    with pytest.raises(AuthError) as exc_info:
        future_auth_service.validate_session(token=raw_token, business_id=admin.business_id)
    assert exc_info.value.code == "session_expired"


def test_auth_service_revoke_session(db_session: Session, test_admin_user: AdminUser):
    auth_service = AuthService(db_session)
    admin, raw_token = auth_service.authenticate(
        email="admin@estudionomada.cl",
        password="SuperSecret123",
        business_id=test_admin_user.business_id,
    )

    _user, session = auth_service.validate_session(token=raw_token, business_id=admin.business_id)
    auth_service.revoke_session(session_id=session.id, business_id=admin.business_id)

    with pytest.raises(AuthError) as exc_info:
        auth_service.validate_session(token=raw_token, business_id=admin.business_id)
    assert exc_info.value.code == "session_expired"


def test_auth_service_scoping_other_business(db_session: Session, test_admin_user: AdminUser):
    other_business_id = uuid.uuid4()
    auth_service = AuthService(db_session)

    # Try authenticating with different business_id
    with pytest.raises(AuthError) as exc_info:
        auth_service.authenticate(
            email="admin@estudionomada.cl",
            password="SuperSecret123",
            business_id=other_business_id,
        )
    assert exc_info.value.code == "invalid_credentials"
