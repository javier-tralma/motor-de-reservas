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
