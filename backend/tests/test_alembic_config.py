import os

from app.core.config import settings
from app.core.db import resolve_migration_database_url


def test_1_explicit_test_database_url_preserved():
    explicit_test_url = "postgresql+psycopg://user:pass@localhost:5433/booking_test"
    resolved = resolve_migration_database_url(explicit_test_url, settings.DATABASE_URL)
    assert resolved == explicit_test_url


def test_2_placeholder_url_replaced_by_settings_database_url():
    placeholder = "driver://user:pass@localhost/dbname"
    resolved = resolve_migration_database_url(placeholder, settings.DATABASE_URL)
    assert resolved == settings.DATABASE_URL


def test_3_empty_or_none_url_replaced_by_settings_database_url():
    assert resolve_migration_database_url("", settings.DATABASE_URL) == settings.DATABASE_URL
    assert resolve_migration_database_url(None, settings.DATABASE_URL) == settings.DATABASE_URL


def test_4_explicit_test_url_cannot_equal_default_database_url():
    test_db_url = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5433/booking_test")
    resolved = resolve_migration_database_url(test_db_url, settings.DATABASE_URL)
    assert resolved != settings.DATABASE_URL, "Explicit test migration URL must never equal development DATABASE_URL"
