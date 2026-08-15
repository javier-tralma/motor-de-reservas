import os
import sys

import pytest
from alembic.config import Config
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from alembic import command

load_dotenv()

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SESSION_SECRET", "test-session-secret-key-32-bytes-long")
os.environ.setdefault("RATE_LIMIT_SECRET", "test-rate-limit-secret-key-32-bytes")
from app.core.config import settings  # noqa: E402

settings.APP_ENV = "test"
settings.SESSION_SECRET = "test-session-secret-key-32-bytes-long"
settings.RATE_LIMIT_SECRET = "test-rate-limit-secret-key-32-bytes"


def validate_test_db_url(test_url_str: str, dev_url_str: str) -> str:
    if not test_url_str:
        pytest.exit("TEST_DATABASE_URL is not set. Aborting tests.")

    try:
        test_url = make_url(test_url_str)
    except Exception:
        pytest.exit("TEST_DATABASE_URL is not a valid SQLAlchemy URL.")

    if test_url.database != "booking_test":
        pytest.exit(f"TEST_DATABASE_URL database must be exactly 'booking_test', got '{test_url.database}'")

    if dev_url_str:
        dev_url = None
        try:
            dev_url = make_url(dev_url_str)
        except Exception:
            pass

        if dev_url:
            # Compare normalized components
            if (
                test_url.database == dev_url.database
                and test_url.host == dev_url.host
                and test_url.port == dev_url.port
                and test_url.username == dev_url.username
            ):
                pytest.exit(
                    "TEST_DATABASE_URL is equivalent to DATABASE_URL. Aborting tests to protect development DB."
                )

    return test_url_str


def get_test_db_url():
    if getattr(sys, "_test_db_validated", False):
        return os.environ.get("TEST_DATABASE_URL", "")

    test_db_url = os.environ.get("TEST_DATABASE_URL", "")
    db_url = os.environ.get("DATABASE_URL", "")

    validated = validate_test_db_url(test_db_url, db_url)
    os.environ["DATABASE_URL"] = validated
    sys._test_db_validated = True
    return validated


test_db_url = get_test_db_url()

engine = create_engine(test_db_url)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Configurar el esquema usando Alembic para test
alembic_cfg = Config(os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini"))
alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)
command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="function")
def db_session() -> Session:
    """Fixture that provides a clean database session for each test via rollback."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def clean_rate_limits():
    import sqlalchemy as sa

    with engine.connect() as conn:
        conn.execute(sa.text("DELETE FROM rate_limits"))
        conn.commit()
    yield
    with engine.connect() as conn:
        conn.execute(sa.text("DELETE FROM rate_limits"))
        conn.commit()


@pytest.fixture(scope="function")
def client(db_session):
    """Fixture to provide a TestClient with overridden get_db and get_session_factory."""
    from app.core.db import get_db
    from app.core.dependencies import get_session_factory
    from app.main import app

    def override_get_db():
        yield db_session

    def override_get_session_factory():
        return TestingSessionLocal

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session_factory] = override_get_session_factory
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
