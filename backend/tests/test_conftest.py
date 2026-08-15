import pytest

from tests.conftest import validate_test_db_url


def test_validate_db_url_empty():
    with pytest.raises(Exception, match="TEST_DATABASE_URL is not set"):
        validate_test_db_url("", "dev_url")


def test_validate_db_url_equal_dev():
    with pytest.raises(Exception, match="is equivalent to DATABASE_URL"):
        validate_test_db_url(
            "postgresql://postgres:postgres@localhost:5432/booking_test",
            "postgresql://postgres:postgres@localhost:5432/booking_test",
        )


def test_validate_db_url_equivalent_dev():
    with pytest.raises(Exception, match="is equivalent to DATABASE_URL"):
        validate_test_db_url(
            "postgresql+psycopg://postgres:postgres@localhost:5432/booking_test",
            "postgresql://postgres:postgres@localhost:5432/booking_test",
        )


def test_validate_db_url_invalid():
    with pytest.raises(Exception, match="TEST_DATABASE_URL is not a valid SQLAlchemy URL"):
        validate_test_db_url("not a url", "dev")


def test_validate_db_url_wrong_name():
    with pytest.raises(Exception, match="database must be exactly 'booking_test'"):
        validate_test_db_url(
            "postgresql+psycopg://postgres:postgres@localhost:5432/booking_other",
            "postgresql://postgres:postgres@localhost:5432/booking_dev",
        )


def test_validate_db_url_success():
    res = validate_test_db_url(
        "postgresql+psycopg://postgres:postgres@localhost:5432/booking_test",
        "postgresql://postgres:postgres@localhost:5432/booking_dev",
    )
    assert res == "postgresql+psycopg://postgres:postgres@localhost:5432/booking_test"


def test_config_fails_early_production_empty_session_secret():
    from app.core.config import Settings

    with pytest.raises(ValueError, match="SESSION_SECRET must be set in production environment"):
        Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            BUSINESS_ID="00000000-0000-0000-0000-000000000000",
            FRONTEND_URL="http://localhost:3000",
            APP_ENV="production",
            SESSION_SECRET="",
        )


def test_config_fails_early_invalid_ttl():
    from app.core.config import Settings

    with pytest.raises(ValueError, match="ADMIN_SESSION_TTL_HOURS must be greater than 0"):
        Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            BUSINESS_ID="00000000-0000-0000-0000-000000000000",
            FRONTEND_URL="http://localhost:3000",
            APP_ENV="development",
            ADMIN_SESSION_TTL_HOURS=0,
            RATE_LIMIT_SECRET="secret",
        )


def test_validate_test_db_url_rejects_equivalent_dev_url():
    """Verify that validate_test_db_url strictly guards against running tests against dev DB."""
    with pytest.raises(Exception, match="is equivalent to DATABASE_URL"):
        validate_test_db_url(
            "postgresql+psycopg://booking_test_user:booking_test_password@127.0.0.1:5433/booking_test",
            "postgresql+psycopg://booking_test_user:booking_test_password@127.0.0.1:5433/booking_test",
        )


def test_ci_environment_simulation_binds_session_local_to_booking_test():
    """
    Verify that in CI environment (where initial DATABASE_URL is a placeholder):
    1. validate_test_db_url succeeds without triggering the safety guard.
    2. settings.DATABASE_URL and app.core.db.SessionLocal point strictly to booking_test on 5433.
    """
    from sqlalchemy.engine import make_url

    from app.core.config import settings
    from app.core.db import SessionLocal

    ci_placeholder_url = "postgresql+psycopg://ci_user:ci_password@127.0.0.1:5499/ci_placeholder_db"
    ci_test_url = "postgresql+psycopg://booking_test_user:booking_test_password@127.0.0.1:5433/booking_test"

    # Step 1: Validation succeeds
    validated = validate_test_db_url(ci_test_url, ci_placeholder_url)
    assert validated == ci_test_url

    # Step 2: In test runtime, settings.DATABASE_URL must be the validated test DB
    current_settings_url = make_url(settings.DATABASE_URL)
    assert current_settings_url.database == "booking_test"
    assert current_settings_url.port == 5433
    assert current_settings_url.host in ("127.0.0.1", "localhost")

    # Step 3: SessionLocal must bind to booking_test, never to placeholder port 5499 or dev port 5432
    session = SessionLocal()
    try:
        bind_url = make_url(str(session.bind.url))
        assert bind_url.database == "booking_test"
        assert bind_url.port == 5433
        assert bind_url.host in ("127.0.0.1", "localhost")
        assert bind_url.port != 5499
        assert bind_url.port != 5432
    finally:
        session.close()
