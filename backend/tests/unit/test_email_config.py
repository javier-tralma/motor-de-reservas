import pytest

from app.core.config import Settings
from app.integrations.email.factory import get_email_service
from app.integrations.email.resend import ResendEmailService
from app.integrations.email.service import ConsoleEmailService, NoOpEmailService


def test_settings_email_validation_invalid_provider():
    with pytest.raises(ValueError, match="EMAIL_PROVIDER must be one of"):
        Settings(
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
            BUSINESS_ID="00000000-0000-0000-0000-000000000001",
            FRONTEND_URL="http://localhost:5173",
            EMAIL_PROVIDER="sendgrid",
        )


def test_settings_production_rejects_console_provider():
    with pytest.raises(ValueError, match="EMAIL_PROVIDER must be 'resend' in production environment"):
        Settings(
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
            BUSINESS_ID="00000000-0000-0000-0000-000000000001",
            FRONTEND_URL="http://localhost:5173",
            APP_ENV="production",
            SESSION_SECRET="super-secret-session-key",
            EMAIL_PROVIDER="console",
            RESEND_API_KEY="re_12345",
            EMAIL_FROM="reservas@test.cl",
        )


def test_settings_production_rejects_noop_provider():
    with pytest.raises(ValueError, match="EMAIL_PROVIDER must be 'resend' in production environment"):
        Settings(
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
            BUSINESS_ID="00000000-0000-0000-0000-000000000001",
            FRONTEND_URL="http://localhost:5173",
            APP_ENV="production",
            SESSION_SECRET="super-secret-session-key",
            EMAIL_PROVIDER="noop",
            RESEND_API_KEY="re_12345",
            EMAIL_FROM="reservas@test.cl",
        )


def test_settings_production_requires_resend_api_key():
    with pytest.raises(ValueError, match="RESEND_API_KEY must be set"):
        Settings(
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
            BUSINESS_ID="00000000-0000-0000-0000-000000000001",
            FRONTEND_URL="http://localhost:5173",
            APP_ENV="production",
            SESSION_SECRET="super-secret-session-key",
            EMAIL_PROVIDER="resend",
            RESEND_API_KEY="",
            EMAIL_FROM="reservas@test.cl",
        )


def test_settings_production_requires_email_from():
    with pytest.raises(ValueError, match="EMAIL_FROM must be set"):
        Settings(
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
            BUSINESS_ID="00000000-0000-0000-0000-000000000001",
            FRONTEND_URL="http://localhost:5173",
            APP_ENV="production",
            SESSION_SECRET="super-secret-session-key",
            EMAIL_PROVIDER="resend",
            RESEND_API_KEY="re_12345",
            EMAIL_FROM="",
        )


def test_settings_production_valid():
    s = Settings(
        DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
        BUSINESS_ID="00000000-0000-0000-0000-000000000001",
        FRONTEND_URL="http://localhost:5173",
        APP_ENV="production",
        SESSION_SECRET="super-secret-session-key",
        EMAIL_PROVIDER="resend",
        RESEND_API_KEY="re_12345",
        EMAIL_FROM="reservas@test.cl",
    )
    assert s.APP_ENV == "production"
    assert s.EMAIL_PROVIDER == "resend"


def test_get_email_service_factory():
    s_console = Settings(
        DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
        BUSINESS_ID="00000000-0000-0000-0000-000000000001",
        FRONTEND_URL="http://localhost:5173",
        EMAIL_PROVIDER="console",
    )
    assert isinstance(get_email_service(s_console), ConsoleEmailService)

    s_noop = Settings(
        DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
        BUSINESS_ID="00000000-0000-0000-0000-000000000001",
        FRONTEND_URL="http://localhost:5173",
        EMAIL_PROVIDER="noop",
    )
    assert isinstance(get_email_service(s_noop), NoOpEmailService)

    s_resend = Settings(
        DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
        BUSINESS_ID="00000000-0000-0000-0000-000000000001",
        FRONTEND_URL="http://localhost:5173",
        EMAIL_PROVIDER="resend",
        RESEND_API_KEY="re_abc123",
        EMAIL_FROM="reservas@test.cl",
    )
    svc = get_email_service(s_resend)
    assert isinstance(svc, ResendEmailService)
    assert svc.api_key == "re_abc123"
    assert svc.from_email == "reservas@test.cl"
