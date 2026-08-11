import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import DUMMY_HASH, generate_session_token, hash_session_token, verify_password
from app.core.config import settings
from app.models.admin_session import AdminSession
from app.models.admin_user import AdminUser


class AuthError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 401):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthService:
    def __init__(self, db: Session, *, now: datetime | None = None):
        self.db = db
        self.now = now or datetime.now(timezone.utc)

    def _get_session_secret(self) -> str:
        secret = settings.SESSION_SECRET
        if not secret:
            raise ValueError("SESSION_SECRET no está configurado.")
        return secret

    def authenticate(
        self,
        *,
        email: str,
        password: str,
        business_id: uuid.UUID,
    ) -> tuple[AdminUser, str]:
        normalized_email = email.strip().lower()
        secret = self._get_session_secret()

        # Buscar dentro del business_id
        admin_user = (
            self.db.query(AdminUser)
            .filter(
                AdminUser.business_id == business_id,
                func.lower(AdminUser.email) == normalized_email,
            )
            .first()
        )

        if not admin_user:
            # Timing dummy check
            verify_password(password, DUMMY_HASH)
            raise AuthError(
                code="invalid_credentials",
                message="Credenciales inválidas.",
                status_code=401,
            )

        if not verify_password(password, admin_user.password_hash):
            raise AuthError(
                code="invalid_credentials",
                message="Credenciales inválidas.",
                status_code=401,
            )

        if not admin_user.is_active:
            raise AuthError(
                code="invalid_credentials",
                message="Credenciales inválidas.",
                status_code=401,
            )

        # Crear sesión nueva
        raw_token = generate_session_token()
        token_hash = hash_session_token(raw_token, secret)
        expires_at = self.now + timedelta(hours=settings.ADMIN_SESSION_TTL_HOURS)

        session = AdminSession(
            business_id=business_id,
            admin_user_id=admin_user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        admin_user.last_login_at = self.now

        self.db.add(session)
        self.db.commit()
        self.db.refresh(admin_user)

        return admin_user, raw_token

    def validate_session(self, *, token: str, business_id: uuid.UUID) -> tuple[AdminUser, AdminSession]:
        secret = self._get_session_secret()
        token_hash = hash_session_token(token, secret)

        session = (
            self.db.query(AdminSession)
            .filter(
                AdminSession.token_hash == token_hash,
                AdminSession.business_id == business_id,
                AdminSession.revoked_at.is_(None),
                AdminSession.expires_at > self.now,
            )
            .first()
        )

        if not session:
            raise AuthError(
                code="session_expired",
                message="La sesión no existe o ha expirado.",
                status_code=401,
            )

        admin_user = (
            self.db.query(AdminUser)
            .filter(
                AdminUser.id == session.admin_user_id,
                AdminUser.business_id == business_id,
            )
            .first()
        )

        if not admin_user or not admin_user.is_active:
            raise AuthError(
                code="session_expired",
                message="El usuario no existe o está inactivo.",
                status_code=401,
            )

        return admin_user, session

    def revoke_session(self, *, session_id: uuid.UUID, business_id: uuid.UUID) -> None:
        session = (
            self.db.query(AdminSession)
            .filter(
                AdminSession.id == session_id,
                AdminSession.business_id == business_id,
            )
            .first()
        )

        if session and session.revoked_at is None:
            session.revoked_at = self.now
            self.db.commit()
